## データ出典

[気象庁](https://www.jma.go.jp/)が公開している気象・地震データです。観測所一覧（アメダス）・予報区の地域コード、府県予報区ごとの短期天気予報、地震月報（カタログ編）の震源データと、アメダス観測所の日別平年値（1991〜2020年）を収録しています。

観測所一覧・地域コード・天気予報は非公式の JSON 配信（気象庁サイトが内部利用しているエンドポイント）を、日別平年値は平年値ダウンロードの配布ファイルを出典として利用しています。

- 観測所一覧: https://www.jma.go.jp/bosai/amedas/const/amedastable.json
- 地域コード: https://www.jma.go.jp/bosai/common/const/area.json
- 天気予報: https://www.jma.go.jp/bosai/forecast/
- 震源データ（地震月報 カタログ編）: https://www.data.jma.go.jp/eqev/data/bulletin/hypo.html
- 日別平年値: https://www.data.jma.go.jp/stats/data/mdrr/normal/index.html （normal_amedas_daily）

## テーブル: mart_jma_stations

全国のアメダス観測所の一覧です。観測所の位置（緯度経度・標高）と種別を持ちます。

- station_id: 観測所ID（VARCHAR、アメダス番号5桁）
- name / name_kana / name_en: 観測所名 漢字 / カナ / 英語（VARCHAR）
- lat / lon: 緯度 / 経度（DOUBLE、十進度）
- elevation: 標高（INTEGER、メートル）
- station_type: 観測所種別（VARCHAR、A〜G。A/Bが気象官署相当）
- is_office: 気象官署フラグ（BOOLEAN、種別A/B）
- elems: 観測種目フラグ（VARCHAR、気象庁仕様の8桁文字列）

## テーブル: mart_jma_areas

気象庁の予報区の地域コードです。全国〜市区町村までの階層を level 付きで縦持ちにしています。

- area_code: 地域コード（VARCHAR）
- level: 階層（VARCHAR、center / office / class10 / class15 / class20）
- name / name_en: 地域名 / 英語（VARCHAR）
- name_kana: 地域名カナ（VARCHAR、class20のみ）
- office_name: 担当気象台名（VARCHAR、center / office のみ）
- parent_code: 親地域コード（VARCHAR、center は NULL）

## テーブル: mart_jma_normals_daily

アメダス観測所の日別平年値（統計期間1991〜2020年）です。観測所×月日ごとに、気温・日照時間・降水量・積雪の深さの30年平均を持ちます。station_id で mart_jma_stations と結合できます。観測していない要素や統計値なしの日は NULL です（2月は閏日29日まで収録）。

- station_id: 観測所ID（VARCHAR、アメダス番号5桁）
- month / day: 月 / 日（INTEGER、月1〜12・日1〜31）
- temp_avg_c: 日平均気温の平年値（DOUBLE、℃）
- temp_max_c: 日最高気温の平年値（DOUBLE、℃）
- temp_min_c: 日最低気温の平年値（DOUBLE、℃）
- sunshine_hours: 日照時間の平年値（DOUBLE、時間）
- precipitation_mm: 降水量の平年値（DOUBLE、mm）
- snow_depth_cm: 積雪の深さ（日最大）の平年値（INTEGER、cm）

## テーブル: mart_jma_hypocenters

地震月報（カタログ編）の震源データです。1 件 1 地震で、発生日時・震央位置・深さ・マグニチュードを持ちます。直近 5 年（2019〜2023 年）を収録しています（カタログは確定までに数年のラグがあります）。

- origin_time: 震源時（TIMESTAMP、オリジンタイム・日本標準時）
- latitude / longitude: 震央の緯度 / 経度（DOUBLE、十進度）
- depth_km: 震源の深さ（DOUBLE、km）
- magnitude: マグニチュード1（DOUBLE、気象庁マグニチュード等。求まらなかった場合は NULL）
- magnitude_type: マグニチュード1種別（VARCHAR、J/D/d/V/v=気象庁、W=モーメント、B/S=他機関）
- magnitude2 / magnitude2_type: 第2のマグニチュードと種別（DOUBLE / VARCHAR）
- region: 震央地名（VARCHAR、気象庁の震央地名・英字）
- record_source: 震源決定機関（VARCHAR、気象庁 / USGS / 国際機関）
- record_type: レコード種別（VARCHAR、J:気象庁 / U:USGS / I:その他国際機関）
- subtype_code / subtype: 震源補助情報のコードと名称（VARCHAR、1:通常地震 3:人工地震 4:噴火に伴う地震動等 5:低周波イベント）
- max_intensity_code / max_intensity: 最大震度のコードと名称（VARCHAR、震度1〜震度7、震度5弱〜震度6強）
- station_count: 震源決定に使用した観測点数（INTEGER）
- hypocenter_flag: 震源決定フラグ（VARCHAR、K:気象庁震源 S:参考震源 k/s:簡易 A/a:自動 N:震源固定等 F:遠地）

## テーブル: mart_jma_forecast_weather

府県予報区ごとの短期天気予報（今日・明日・明後日）です。一次細分区域（class10）別に、対象日時ごとの天気・風・波を持ちます。area_code で mart_jma_areas（level=class10）と、office_code で mart_jma_areas（level=office）と結合できます。

天気予報は発表のたびに更新されるため、本テーブルはビルド時点の最新発表（report_datetime）の 1 スナップショットです。ビルド（月次）ごとに置き換わります。

- office_code: 府県予報区コード（VARCHAR、発表元。area.json の offices）
- report_datetime: 発表日時（TIMESTAMP WITH TIME ZONE、日本標準時）
- area_code: 区域コード（VARCHAR、一次細分区域 class10）
- area_name: 区域名（VARCHAR）
- forecast_datetime: 予報対象日時（TIMESTAMP WITH TIME ZONE、日本標準時。今日・明日・明後日）
- weather_code: 天気予報コード（VARCHAR、例 100:晴れ 200:くもり）
- weather: 天気の予報文（VARCHAR）
- wind: 風の予報文（VARCHAR）
- wave: 波の予報文（VARCHAR、内陸の区域は NULL）

### データ更新手順

main.py が気象庁の JSON（amedastable.json / area.json / 府県予報区ごとの forecast）、地震月報（カタログ編）の年別震源 ZIP（96 バイト固定長）と平年値ダウンロードの日別平年値 ZIP（normal_amedas_daily）を取得し、緯度経度の十進度化・地域階層のフラット化・天気予報の区域×対象日時への展開・震源レコードの解析・日別平年値の観測所×月日への展開と実単位へのスケールを行って `.fdl/` に NDJSON として保存し、dbt build でテーブルを再生成する。ビルドは `bash scripts/build.sh local` で実行する。震源データの収録年は main.py の `HYPOCENTER_YEARS` で調整する。

## ライセンス

出典は気象庁。[気象庁ホームページ利用規約](https://www.jma.go.jp/jma/kishou/info/coment.html)（政府標準利用規約 第2.0版に準拠）に従う。
