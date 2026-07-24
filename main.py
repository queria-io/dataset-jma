"""気象庁データ取得 + dbt ビルド + メタデータ生成パイプライン。

非公式 JSON API からマスタ（観測所一覧・地域コード）と府県予報区ごとの短期天気予報を
取得し、地震月報（カタログ編）の震源データ（96 バイト固定長）と平年値ダウンロードの
アメダス日別平年値（1991〜2020 年）を取得・整形して、DuckDB が読みやすい NDJSON に
整形して .fdl/ に保存してから dbt を実行する。
"""

import calendar
import io
import json
import re
import time
from datetime import date, timedelta
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from dbt.cli.main import dbtRunner

AMEDAS_TABLE_URL = "https://www.jma.go.jp/bosai/amedas/const/amedastable.json"
AREA_URL = "https://www.jma.go.jp/bosai/common/const/area.json"

# アメダス（地域気象観測）日別平年値（統計期間：1991〜2020 年、2020 年平年値）。
# 観測所別の ZIP（Shift-JIS の固定長 CSV）で配布される。
# https://www.data.jma.go.jp/stats/data/mdrr/normal/index.html
NORMALS_DAILY_URL = (
    "https://www.data.jma.go.jp/stats/data/mdrr/normal/2020/data/normal_amedas_daily.zip"
)

# 地震月報（カタログ編）の震源データ。年別 ZIP（96 バイト固定長レコード）で配布される。
# https://www.data.jma.go.jp/eqev/data/bulletin/hypo.html
HYPOCENTER_BASE_URL = "https://www.data.jma.go.jp/eqev/data/bulletin/data/hypo"

# 取り込む年（直近の確定済み年から 5 年）。カタログは確定までに数年のラグがあり、
# 現時点の最新確定年は 2023 年。年を追加すれば取り込み範囲を拡張できる。
HYPOCENTER_YEARS = [2019, 2020, 2021, 2022, 2023]

# 府県予報区ごとの天気予報 JSON。area.json の offices（府県予報区）コードを URL に埋める。
# 各ファイルの先頭要素が短期予報（今日・明日・明後日）で、その timeSeries[0] が
# 一次細分区域（class10）別の天気・風・波。ビルド時点の最新発表を 1 スナップショット取得する。
# https://www.jma.go.jp/bosai/forecast/
FORECAST_BASE_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast"

# 過去の気象データ検索の観測所選択ページと、気象官署の日別値ページ（daily_s1.php）。
# 観測所選択ページ（prec_no ごと）で気象官署の一覧・位置を取得し、日別値ページを
# prec_no × block_no × 年月で取得する。1 ページ＝1 観測所の 1 か月分（UTF-8 の HTML 表）。
# https://www.data.jma.go.jp/stats/etrn/index.php
ETRN_PREF_URL = "https://www.data.jma.go.jp/stats/etrn/select/prefecture.php"
ETRN_DAILY_S1_URL = "https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php"

# 気象官署の時別値ページ（hourly_s1.php）。1 ページ＝1 観測所の 1 日分（毎正時の UTF-8 HTML 表）。
# 主要観測所 × prec_no × block_no × 年月日で取得する。
# https://www.data.jma.go.jp/stats/etrn/index.php
ETRN_HOURLY_S1_URL = "https://www.data.jma.go.jp/stats/etrn/view/hourly_s1.php"

# 都府県・地方の区分コード（prec_no）。北海道などは複数に分かれるため 47 都道府県より多い。
# 全国の観測所選択ページを列挙する起点。
OBS_PREC_NOS = [
    "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22",
    "23", "24", "31", "32", "33", "34", "35", "36", "40", "41", "42", "43",
    "44", "45", "46", "48", "49", "50", "51", "52", "53", "54", "55", "56",
    "57", "60", "61", "62", "63", "64", "65", "66", "67", "68", "69", "71",
    "72", "73", "74", "81", "82", "83", "84", "85", "86", "87", "88", "91",
    "99",
]

# 日別値を取り込む直近の月数（MVP の取得範囲）。取得ページ数＝気象官署数×月数のため、
# ここで期間を絞る。過去月の確定値は変わらないので、必要に応じて拡張・増分化できる。
OBS_MONTHS = 6

# daily_s1.php（気象官署の日別値）テーブルの列位置 → (出力カラム名, 型)。
# 平年値テーブル mart_jma_normals_daily と対になる中核要素に絞る。
# 列: 0=日 1=現地気圧 2=海面気圧 3=降水量合計 4=最大1時間降水量 5=最大10分間降水量
#     6=平均気温 7=最高気温 8=最低気温 9=平均湿度 10=最小湿度 11=平均風速 …
#     16=日照時間 17=降雪合計 18=最深積雪 19=昼の天気概況 20=夜の天気概況
OBS_COLUMNS = {
    3: ("precipitation_mm", "float"),
    6: ("temp_avg_c", "float"),
    7: ("temp_max_c", "float"),
    8: ("temp_min_c", "float"),
    16: ("sunshine_hours", "float"),
    17: ("snowfall_cm", "int"),
    18: ("snow_depth_cm", "int"),
}

# 時別値を取り込む直近の日数（MVP の取得範囲）。時別値は 1 ページ＝1 観測所の 1 日分で、
# 日数×観測所ぶんのページを取得する。日別値（1 ページ＝1 か月）より嵩むため、対象を
# 主要地点かつ短期間に絞る。過去日の確定値は変わらないので、必要に応じて拡張・増分化できる。
OBS_HOURLY_DAYS = 14

# 時別値を取り込む主要観測所（各都道府県の地方・管区気象台がある地点名）。全気象官署だと
# 日数×官署でページ数が過大になるため代表 47 地点に絞る。観測所レジストリ
# （raw_jma_observation_stations）から地点名がこの集合に一致するものを選ぶ。
MAJOR_STATION_NAMES = {
    "札幌", "青森", "盛岡", "仙台", "秋田", "山形", "福島", "水戸", "宇都宮",
    "前橋", "熊谷", "千葉", "東京", "横浜", "新潟", "富山", "金沢", "福井",
    "甲府", "長野", "岐阜", "静岡", "名古屋", "津", "彦根", "京都", "大阪",
    "神戸", "奈良", "和歌山", "鳥取", "松江", "岡山", "広島", "下関", "徳島",
    "高松", "松山", "高知", "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎",
    "鹿児島", "那覇",
}

# hourly_s1.php（気象官署の時別値）テーブルの列位置 → (出力カラム名, 型)。
# 列: 0=時 1=現地気圧 2=海面気圧 3=降水量 4=気温 5=露点温度 6=蒸気圧 7=湿度
#     8=風速 9=風向 10=日照時間 11=全天日射量 12=降雪 13=積雪 14=天気 15=雲量 16=視程
HOURLY_OBS_COLUMNS = {
    1: ("pressure_local_hpa", "float"),
    2: ("pressure_sea_hpa", "float"),
    3: ("precipitation_mm", "float"),
    4: ("temp_c", "float"),
    7: ("humidity_pct", "int"),
    8: ("wind_speed_ms", "float"),
    9: ("wind_direction", "str"),
    10: ("sunshine_hours", "float"),
    13: ("snow_depth_cm", "int"),
}

# 気象庁サーバーへの配慮。連続リクエストの最小間隔（秒）と識別用 User-Agent。
# 時間をかけてでもゆったりアクセスする方針。obsdl 等のバッチ取得でも同じ間隔を使う。
REQUEST_INTERVAL_SEC = 3.0

# etrn の静的 HTML ページ（観測所選択・日別値）の取得間隔（秒）。bosai の JSON API より
# 軽い静的ページだが、観測所×月で多数取得するため配慮して間隔を空ける。
ETRN_INTERVAL_SEC = 1.0

USER_AGENT = "queria-dataset-jma/0.1 (+https://github.com/queria-io/dataset-jma)"

_last_request_at = 0.0

FDL_DIR = Path(".fdl")
STATIONS_PATH = FDL_DIR / "jma_stations.ndjson"
AREAS_PATH = FDL_DIR / "jma_areas.ndjson"
NORMALS_DAILY_PATH = FDL_DIR / "jma_normals_daily.ndjson"
HYPOCENTERS_PATH = FDL_DIR / "jma_hypocenters.ndjson"
FORECASTS_PATH = FDL_DIR / "jma_forecasts.ndjson"
OBS_STATIONS_PATH = FDL_DIR / "jma_observation_stations.ndjson"
DAILY_OBS_PATH = FDL_DIR / "jma_daily_observations.ndjson"
HOURLY_OBS_PATH = FDL_DIR / "jma_hourly_observations.ndjson"

# 気象官署（管区・地方気象台や測候所相当）の観測所種別。
# amedas のうち type A/B が気象官署に相当する。
OFFICE_TYPES = {"A", "B"}

# area.json の階層キー → level ラベル
AREA_LEVELS = {
    "centers": "center",
    "offices": "office",
    "class10s": "class10",
    "class15s": "class15",
    "class20s": "class20",
}

# 日別平年値ファイルから取り込む要素番号 → (出力カラム名, スケール係数)。
# 値はスケール係数で割って実単位に直す（係数 1 はそのまま）。
# 気温は 0.1℃・日照時間は 0.1 時間・降水量は 0.1mm・積雪の深さは 1cm。
# 標準偏差・階級区分・時刻別気温も同ファイルに含まれるが、本テーブルでは
# 日別気候値の中核 6 要素に絞る。
NORMALS_DAILY_ELEMENTS = {
    "0500": ("temp_avg_c", 10.0),
    "0600": ("temp_max_c", 10.0),
    "0700": ("temp_min_c", 10.0),
    "3500": ("sunshine_hours", 10.0),
    "4000": ("precipitation_mm", 10.0),
    "6200": ("snow_depth_cm", 1.0),
}

# 観測値のリマーク（RMK）。8=正常値のみ採用し、0=統計値なしは欠損とする。
NORMALS_VALID_RMK = "8"

# 震源レコードのレコード種別ヘッダ（欄 01）。
HYPOCENTER_RECORD_TYPES = {
    "J": "気象庁",
    "U": "USGS",
    "I": "国際機関",
}

# 0 未満のマグニチュードの特殊表記（欄 53-54 の先頭文字）。
# A0=-1.0, A9=-1.9, B0=-2.0, C0=-3.0 のように 10 の位を表す。
MAG_NEGATIVE_PREFIX = {"A": -1, "B": -2, "C": -3}


def main() -> None:
    FDL_DIR.mkdir(exist_ok=True)
    _build_stations()
    _build_areas()
    _build_normals_daily()
    _build_hypocenters()
    _build_forecasts()
    stations = _build_observation_stations()
    _build_daily_observations(stations)
    _build_hourly_observations()

    dbt = dbtRunner()

    result = dbt.invoke(["deps"])
    if not result.success:
        raise SystemExit("dbt deps failed")

    result = dbt.invoke(["run"])
    if not result.success:
        raise SystemExit("dbt run failed")

    result = dbt.invoke(["docs", "generate"])
    if not result.success:
        raise SystemExit("dbt docs generate failed")


def _throttle(interval: float = REQUEST_INTERVAL_SEC) -> None:
    """直前のリクエストから最低 interval 秒空ける。"""
    global _last_request_at
    wait = interval - (time.monotonic() - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


def _fetch_json(url: str):
    """間隔を空けて JSON を取得する（気象庁サーバーへの配慮）。"""
    _throttle()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def _fetch_bytes(url: str) -> bytes:
    """間隔を空けてバイト列を取得する（気象庁サーバーへの配慮）。"""
    _throttle()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def _fetch_text(url: str, interval: float = ETRN_INTERVAL_SEC) -> str:
    """間隔を空けて UTF-8 の HTML/テキストを取得する（etrn の静的ページ用）。"""
    _throttle(interval)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _dms_to_deg(dms: list[float]) -> float:
    """[度, 分] 形式の座標を十進度に変換する。"""
    return round(dms[0] + dms[1] / 60, 6)


def _build_stations() -> None:
    """amedastable.json を観測所マスタの NDJSON に整形する。"""
    table = _fetch_json(AMEDAS_TABLE_URL)
    with STATIONS_PATH.open("w", encoding="utf-8") as f:
        for station_id, v in table.items():
            station_type = v.get("type")
            row = {
                "station_id": station_id,
                "name": v.get("kjName"),
                "name_kana": v.get("knName"),
                "name_en": v.get("enName"),
                "lat": _dms_to_deg(v["lat"]),
                "lon": _dms_to_deg(v["lon"]),
                "elevation": v.get("alt"),
                "station_type": station_type,
                "is_office": station_type in OFFICE_TYPES,
                "elems": v.get("elems"),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"  jma_stations.ndjson: {len(table)} stations")


def _build_areas() -> None:
    """area.json の階層を level 付きでフラット化した NDJSON に整形する。"""
    area = _fetch_json(AREA_URL)
    count = 0
    with AREAS_PATH.open("w", encoding="utf-8") as f:
        for key, level in AREA_LEVELS.items():
            for area_code, v in area.get(key, {}).items():
                row = {
                    "area_code": area_code,
                    "level": level,
                    "name": v.get("name"),
                    "name_en": v.get("enName"),
                    "name_kana": v.get("kana"),
                    "office_name": v.get("officeName"),
                    "parent_code": v.get("parent"),
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1
    print(f"  jma_areas.ndjson: {count} areas")


def _days_in_month(month: int) -> int:
    """平年値の収録日数。2 月は閏日（29 日）まで含む。"""
    return 29 if month == 2 else calendar.monthrange(2001, month)[1]


def _normals_value(raw: str, rmk: str, scale: float):
    """日別平年値の値欄をパースする。RMK=8（正常値）のみ採用する。
    係数 1.0 の要素（積雪の深さ）は整数 cm、それ以外は実単位に直して返す。"""
    if rmk != NORMALS_VALID_RMK:
        return None
    value = raw.strip()
    if value in ("", "-"):
        return None
    number = int(value)
    if scale == 1.0:
        return number
    return round(number / scale, 1)


def _parse_normals_station(text: io.TextIOWrapper) -> tuple[str | None, dict]:
    """1 観測所分の日別平年値 CSV を {(要素番号, 月): [(値, RMK), ...]} に整形する。

    日別平年値ファイルはカンマ区切りの固定長で、1 行が「要素番号×月」に対応し、
    その月の 1〜31 日の値と RMK が並ぶ（平年値種別 25）。
    """
    station_id = None
    by_element_month: dict[tuple[str, int], list[tuple[str, str]]] = {}
    for line in text:
        fields = [c.strip() for c in line.rstrip("\n").split(",")]
        if len(fields) < 9:
            continue
        station_id = fields[1]
        element_code = fields[2]
        if element_code not in NORMALS_DAILY_ELEMENTS:
            continue
        month = int(fields[6])
        # fields[7] 以降は (1 日値, RMK, 2 日値, RMK, ...) の並び。
        days = []
        for day_index in range(31):
            value_pos = 7 + day_index * 2
            rmk_pos = 8 + day_index * 2
            if rmk_pos < len(fields):
                days.append((fields[value_pos], fields[rmk_pos]))
        by_element_month[(element_code, month)] = days
    return station_id, by_element_month


def _build_normals_daily() -> None:
    """アメダス日別平年値の ZIP を取得し、観測所×月日の NDJSON に整形する。"""
    archive = _fetch_bytes(NORMALS_DAILY_URL)
    count = 0
    stations = 0
    with (
        zipfile.ZipFile(io.BytesIO(archive)) as zf,
        NORMALS_DAILY_PATH.open("w", encoding="utf-8") as out,
    ):
        members = sorted(m for m in zf.namelist() if m.endswith(".csv"))
        for member in members:
            with zf.open(member) as fh:
                text = io.TextIOWrapper(fh, encoding="shift_jis", errors="replace")
                station_id, by_element_month = _parse_normals_station(text)
            if station_id is None:
                continue
            stations += 1
            for month in range(1, 13):
                for day in range(1, _days_in_month(month) + 1):
                    row = {"station_id": station_id, "month": month, "day": day}
                    for element_code, (column, scale) in NORMALS_DAILY_ELEMENTS.items():
                        days = by_element_month.get((element_code, month))
                        value = None
                        if days is not None and day - 1 < len(days):
                            raw, rmk = days[day - 1]
                            value = _normals_value(raw, rmk, scale)
                        row[column] = value
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    count += 1
    print(f"  jma_normals_daily.ndjson: {count} rows / {stations} stations")


def _hypo_int(field: str):
    """符号付き整数欄をパースする（国際機関の震源は緯度経度が負になり得る）。"""
    s = field.strip()
    if s in ("", "-"):
        return None
    digits = re.sub(r"[^0-9]", "", s)
    if digits == "":
        return None
    value = int(digits)
    return -value if "-" in s else value


def _hypo_coord(deg_field: str, min_field: str):
    """度欄（I3/I4）と分欄（F4.2、値÷100）から十進度を組み立てる。"""
    deg = _hypo_int(deg_field)
    if deg is None:
        return None
    minute_raw = min_field.strip()
    minute = int(minute_raw) / 100 if minute_raw not in ("", "-") else 0.0
    if deg < 0:
        return round(deg - minute / 60, 6)
    return round(deg + minute / 60, 6)


def _hypo_magnitude(field: str):
    """マグニチュード欄（F2.1、値÷10）をパースする。0 未満は A0/B0/C0 表記。"""
    if field.strip() == "":
        return None
    head = field[0]
    if head in MAG_NEGATIVE_PREFIX:
        ones = field[1]
        if not ones.isdigit():
            return None
        return round((MAG_NEGATIVE_PREFIX[head] * 10 - int(ones)) / 10, 1)
    try:
        return round(int(field) / 10, 1)
    except ValueError:
        return None


def _hypo_depth(field: str):
    """深さ欄（5 桁）をパースする。末尾 2 桁が空白なら整数 km（固定/刻み）、
    そうでなければ F5.2（値÷100、深さフリー）。"""
    if field.strip() == "":
        return None
    if field[3:5].strip() == "":
        head = field[0:3].strip()
        if head in ("", "-"):
            return None
        return float(int(head))
    try:
        return round(int(field.strip()) / 100, 2)
    except ValueError:
        return None


def _parse_hypocenter(line: str) -> dict | None:
    """震源レコード（96 バイト固定長）を 1 件分の dict にパースする。"""
    record = line.rstrip("\n")
    if record.strip() == "":
        return None
    if len(record) < 96:
        record = record.ljust(96)

    year = record[1:5].strip()
    month = record[5:7].strip()
    day = record[7:9].strip()
    hour = record[9:11].strip()
    minute = record[11:13].strip()
    if not (year and month and day and hour and minute):
        return None
    second_raw = record[13:17].strip()
    second = int(second_raw) / 100 if second_raw != "" else 0.0
    origin_time = (
        f"{int(year):04d}-{int(month):02d}-{int(day):02d} "
        f"{int(hour):02d}:{int(minute):02d}:{second:05.2f}"
    )

    station_count_raw = record[92:95].strip()
    return {
        "record_type": record[0],
        "origin_time": origin_time,
        "latitude": _hypo_coord(record[21:24], record[24:28]),
        "longitude": _hypo_coord(record[32:36], record[36:40]),
        "depth_km": _hypo_depth(record[44:49]),
        "magnitude": _hypo_magnitude(record[52:54]),
        "magnitude_type": record[54].strip() or None,
        "magnitude2": _hypo_magnitude(record[55:57]),
        "magnitude2_type": record[57].strip() or None,
        "subtype_code": record[60].strip() or None,
        "max_intensity_code": record[61].strip() or None,
        "region": record[68:92].strip() or None,
        "station_count": int(station_count_raw) if station_count_raw else None,
        "hypocenter_flag": record[95].strip() or None,
    }


def _build_hypocenters() -> None:
    """地震月報（カタログ編）の年別震源 ZIP を取得し NDJSON に整形する。"""
    count = 0
    with HYPOCENTERS_PATH.open("w", encoding="utf-8") as f:
        for year in HYPOCENTER_YEARS:
            data = _fetch_bytes(f"{HYPOCENTER_BASE_URL}/h{year}.zip")
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                members = zf.namelist()
                year_count = 0
                for member in members:
                    with zf.open(member) as fh:
                        text = io.TextIOWrapper(fh, encoding="utf-8", errors="replace")
                        for line in text:
                            row = _parse_hypocenter(line)
                            if row is None:
                                continue
                            f.write(json.dumps(row, ensure_ascii=False) + "\n")
                            year_count += 1
                count += year_count
                print(f"    h{year}: {year_count} hypocenters")
    print(f"  jma_hypocenters.ndjson: {count} hypocenters")


def _forecast_weather_rows(office_code: str, data: list) -> list[dict]:
    """府県予報区の予報 JSON から短期天気予報（class10 別）の行を取り出す。

    先頭要素が短期予報で、その timeSeries[0] が天気・風・波の時系列。timeSeries[0]
    の各エリア（一次細分区域）× timeDefines（今日・明日・明後日）で 1 行を作る。
    波（waves）は内陸の区域には無いので欠損を許容する。
    """
    if not data:
        return []
    short_term = data[0]
    report_datetime = short_term.get("reportDatetime")
    series = short_term.get("timeSeries") or []
    if not series:
        return []
    weather = series[0]
    time_defines = weather.get("timeDefines") or []
    rows = []
    for area in weather.get("areas") or []:
        area_info = area.get("area") or {}
        area_code = area_info.get("code")
        area_name = area_info.get("name")
        codes = area.get("weatherCodes") or []
        texts = area.get("weathers") or []
        winds = area.get("winds") or []
        waves = area.get("waves") or []
        for i, forecast_datetime in enumerate(time_defines):
            rows.append(
                {
                    "office_code": office_code,
                    "report_datetime": report_datetime,
                    "area_code": area_code,
                    "area_name": area_name,
                    "forecast_datetime": forecast_datetime,
                    "weather_code": codes[i] if i < len(codes) else None,
                    "weather": texts[i] if i < len(texts) else None,
                    "wind": winds[i] if i < len(winds) else None,
                    "wave": waves[i] if i < len(waves) else None,
                }
            )
    return rows


def _build_forecasts() -> None:
    """府県予報区ごとの短期天気予報を取得し、class10 区域×対象日時の NDJSON に整形する。

    予報対象の区域は area.json の offices（府県予報区）。区域コードは area.json の
    class10 と一致し mart_jma_areas と結合できる。ビルド時点の最新発表を取得する。
    """
    area = _fetch_json(AREA_URL)
    office_codes = sorted(area.get("offices", {}).keys())
    count = 0
    offices = 0
    with FORECASTS_PATH.open("w", encoding="utf-8") as f:
        for office_code in office_codes:
            url = f"{FORECAST_BASE_URL}/{office_code}.json"
            try:
                data = _fetch_json(url)
            except urllib.error.HTTPError as exc:
                # 予報を提供しない区域（例: 別区域に統合済み）は 404 になり得る。
                print(f"    forecast {office_code}: skip ({exc.code})")
                continue
            rows = _forecast_weather_rows(office_code, data)
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += len(rows)
            offices += 1
    print(f"  jma_forecasts.ndjson: {count} rows / {offices} offices")


_VIEWPOINT_RE = re.compile(
    r"viewPoint\('([as])','(\d+)','([^']*)','([^']*)',"
    r"'([^']*)','([^']*)','([^']*)','([^']*)'"
)


def _build_observation_stations() -> list[tuple[str, str]]:
    """観測所選択ページを prec_no ごとに巡回し、気象官署（type s）の一覧を整形する。

    各ページの area タグに埋め込まれた viewPoint(type, block_no, 地点名, カナ,
    緯度度, 緯度分, 経度度, 経度分) から気象官署だけを取り出し、位置を十進度に直して
    観測所レジストリ NDJSON に保存する。日別値を取得する (prec_no, block_no) の一覧を返す。
    """
    seen: set[str] = set()
    stations: list[tuple[str, str]] = []
    with OBS_STATIONS_PATH.open("w", encoding="utf-8") as f:
        for prec_no in OBS_PREC_NOS:
            url = (
                f"{ETRN_PREF_URL}?prec_no={prec_no}"
                "&block_no=&year=&month=&day=&view="
            )
            html = _fetch_text(url)
            for m in _VIEWPOINT_RE.finditer(html):
                kind, block_no, name, kana, latd, latm, lond, lonm = m.groups()
                # 気象官署（block_no 5 桁）のみ。アメダス（type a）は対象外。
                if kind != "s" or block_no in seen:
                    continue
                seen.add(block_no)
                row = {
                    "block_no": block_no,
                    "prec_no": prec_no,
                    "station_name": name,
                    "station_kana": kana,
                    "lat": round(int(latd) + float(latm) / 60, 6),
                    "lon": round(int(lond) + float(lonm) / 60, 6),
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                stations.append((prec_no, block_no))
    print(f"  jma_observation_stations.ndjson: {len(stations)} stations")
    return stations


def _recent_year_months(n: int) -> list[tuple[int, int]]:
    """当月から遡って直近 n か月の (年, 月) を古い順に返す。"""
    today = date.today()
    year, month = today.year, today.month
    result: list[tuple[int, int]] = []
    for _ in range(n):
        result.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(result))


def _obs_value(cell: str, kind: str):
    """日別値の値欄をパースする。先頭の符号付き数値のみ採用し、品質記号（")" 準正常値・
    "]" 資料不足値 など）は落とす。"--"（現象なし）・"×"（欠測）・空欄は欠損（None）。"""
    m = re.match(r"-?\d+(?:\.\d+)?", cell.replace("\xa0", " ").strip())
    if m is None:
        return None
    return int(m.group()) if kind == "int" else float(m.group())


def _parse_daily_s1(html: str) -> list[tuple[int, list[str]]]:
    """daily_s1.php（気象官署の日別値）の HTML から (日, セル配列) の並びを取り出す。

    データ行は class="mtx" で、先頭セルが日、以降に気圧・降水量・気温・…の順で並ぶ。
    """
    rows: list[tuple[int, list[str]]] = []
    for tr in re.findall(r'<tr class="mtx"[^>]*>(.*?)</tr>', html, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if not tds:
            continue
        cells = [re.sub(r"<[^>]+>", "", c) for c in tds]
        day = cells[0].strip()
        # 天気概況まで揃った日別値行のみ（ヘッダや観測所情報行を除く）。
        if not day.isdigit() or len(cells) <= max(OBS_COLUMNS):
            continue
        rows.append((int(day), cells))
    return rows


def _build_daily_observations(stations: list[tuple[str, str]]) -> None:
    """気象官署ごとに直近 OBS_MONTHS か月分の日別値ページを取得し、観測所×日の NDJSON に整形する。

    観測値・平年値と対で「実況 vs 平年」の比較ができるよう、平年値テーブルと同じ中核要素
    （気温・降水量・日照時間・積雪など）に絞る。全要素が欠損の日（未観測の将来日など）は除く。
    """
    months = _recent_year_months(OBS_MONTHS)
    count = 0
    with DAILY_OBS_PATH.open("w", encoding="utf-8") as out:
        for prec_no, block_no in stations:
            for year, month in months:
                url = (
                    f"{ETRN_DAILY_S1_URL}?prec_no={prec_no}&block_no={block_no}"
                    f"&year={year}&month={month}&day=&view="
                )
                html = _fetch_text(url)
                for day, cells in _parse_daily_s1(html):
                    values = {
                        column: _obs_value(cells[i], kind)
                        for i, (column, kind) in OBS_COLUMNS.items()
                    }
                    if all(v is None for v in values.values()):
                        continue
                    row = {
                        "block_no": block_no,
                        "observed_date": f"{year:04d}-{month:02d}-{day:02d}",
                        **values,
                    }
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    count += 1
    print(f"  jma_daily_observations.ndjson: {count} rows / {len(stations)} stations")


def _obs_direction(cell: str):
    """時別値の風向欄をテキストで返す。方位（例: 西・北北東）と「静穏」を採用し、
    「×」（欠測）・「--」・空欄は欠損（None）。"""
    text = cell.replace("\xa0", " ").strip()
    return None if text in ("", "--", "×") else text


def _recent_dates(n: int) -> list[tuple[int, int, int]]:
    """前日から遡って直近 n 日の (年, 月, 日) を古い順に返す。当日は観測途中のため含めない。"""
    end = date.today() - timedelta(days=1)
    result = [
        ((end - timedelta(days=i)).year, (end - timedelta(days=i)).month, (end - timedelta(days=i)).day)
        for i in range(n)
    ]
    return list(reversed(result))


def _parse_hourly_s1(html: str) -> list[tuple[int, list[str]]]:
    """hourly_s1.php（気象官署の時別値）の HTML から (時, セル配列) の並びを取り出す。

    データ行は class="mtx" で、先頭セルが時（1〜24）、以降に気圧・降水量・気温・…が並ぶ。
    """
    rows: list[tuple[int, list[str]]] = []
    for tr in re.findall(r'<tr class="mtx"[^>]*>(.*?)</tr>', html, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if not tds:
            continue
        cells = [re.sub(r"<[^>]+>", "", c) for c in tds]
        hour = cells[0].strip()
        # 時別値行のみ（時が 1〜24 の数字で、対象列まで揃っているもの）。
        if not hour.isdigit() or len(cells) <= max(HOURLY_OBS_COLUMNS):
            continue
        rows.append((int(hour), cells))
    return rows


def _major_stations() -> list[tuple[str, str, str]]:
    """観測所レジストリ（daily 取得で保存済み）から主要地点だけを (prec_no, block_no, 地点名) で返す。"""
    stations: list[tuple[str, str, str]] = []
    with OBS_STATIONS_PATH.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row["station_name"] in MAJOR_STATION_NAMES:
                stations.append((row["prec_no"], row["block_no"], row["station_name"]))
    return stations


def _build_hourly_observations() -> None:
    """主要な気象官署ごとに直近 OBS_HOURLY_DAYS 日分の時別値ページを取得し、観測所×日時の NDJSON に整形する。

    時別値は毎正時（日本標準時。時＝1〜24 で、24 は 24 時＝翌日 0 時）の実況値。日別観測値
    （mart_jma_daily_observations）を時間帯まで細かくしたもので、需要予測・電力・小売の
    時間帯分析に使う。全要素が欠測の時（未来の時刻など）は除く。
    """
    stations = _major_stations()
    dates = _recent_dates(OBS_HOURLY_DAYS)
    count = 0
    with HOURLY_OBS_PATH.open("w", encoding="utf-8") as out:
        for prec_no, block_no, _name in stations:
            for year, month, day in dates:
                url = (
                    f"{ETRN_HOURLY_S1_URL}?prec_no={prec_no}&block_no={block_no}"
                    f"&year={year}&month={month}&day={day}&view="
                )
                html = _fetch_text(url)
                for hour, cells in _parse_hourly_s1(html):
                    values = {}
                    for i, (column, kind) in HOURLY_OBS_COLUMNS.items():
                        if kind == "str":
                            values[column] = _obs_direction(cells[i])
                        else:
                            values[column] = _obs_value(cells[i], kind)
                    if all(v is None for v in values.values()):
                        continue
                    row = {
                        "block_no": block_no,
                        "observed_date": f"{year:04d}-{month:02d}-{day:02d}",
                        "hour": hour,
                        **values,
                    }
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    count += 1
    print(f"  jma_hourly_observations.ndjson: {count} rows / {len(stations)} stations")


if __name__ == "__main__":
    main()
