# 気象庁

[気象庁](https://www.jma.go.jp/)が公開している気象・地震のデータを、SQL で検索・集計できるテーブルにしたデータセットです。観測所と予報区のマスタ、短期・週間の天気予報、気象官署の日別・時別の観測値、アメダスの日別平年値、地震の震源、台風の経路（1951 年〜）、さくらの開花日・満開日（1953 年〜）を収録しています。

## 出典と利用条件

観測所一覧・地域コード・天気予報は非公式の JSON 配信（気象庁サイトが内部利用しているエンドポイント）を、日別平年値は平年値ダウンロードの配布ファイルを、気象官署の観測所一覧・日別観測値・時別観測値は過去の気象データ検索のページを、台風の経路は RSMC 東京・台風センターのベストトラック配布ファイルを、さくらの開花日・満開日は生物季節観測の累年表のページを出典として利用しています。

- 観測所一覧: https://www.jma.go.jp/bosai/amedas/const/amedastable.json
- 地域コード: https://www.jma.go.jp/bosai/common/const/area.json
- 天気予報: https://www.jma.go.jp/bosai/forecast/
- 震源データ（地震月報 カタログ編）: https://www.data.jma.go.jp/eqev/data/bulletin/hypo.html
- 日別平年値: https://www.data.jma.go.jp/stats/data/mdrr/normal/index.html （normal_amedas_daily）
- 気象官署の観測所一覧・日別観測値: https://www.data.jma.go.jp/stats/etrn/index.php （過去の気象データ検索）
- 台風の経路（ベストトラック）: https://www.jma.go.jp/jma/jma-eng/jma-center/rsmc-hp-pub-eg/Besttracks/index.html
- さくらの開花日・満開日（生物季節観測）: https://www.data.jma.go.jp/sakura/data/index.html

- [気象庁ホームページ利用規約](https://www.jma.go.jp/jma/kishou/info/coment.html)（政府標準利用規約 第2.0版に準拠）に従います。出典は気象庁です

## テーブル

| テーブル | 内容 |
| --- | --- |
| `main.mart_jma_stations` | アメダス観測所の一覧 |
| `main.mart_jma_areas` | 予報区の地域コード |
| `main.mart_jma_observation_stations` | 気象官署の一覧 |
| `main.mart_jma_daily_observations` | 気象官署の日別観測値（直近数か月） |
| `main.mart_jma_hourly_observations` | 気象官署の時別観測値（主要地点の直近数日） |
| `main.mart_jma_normals_daily` | アメダス観測所の日別平年値（1991〜2020 年） |
| `main.mart_jma_hypocenters` | 地震の震源 |
| `main.mart_jma_typhoon_tracks` | 台風の経路（1951 年〜） |
| `main.mart_jma_sakura_phenology` | さくらの開花日・満開日（1953 年〜） |
| `main.mart_jma_forecast_weather` | 短期天気予報 |
| `main.mart_jma_forecast_pops` | 短期予報の降水確率 |
| `main.mart_jma_forecast_temps` | 短期予報の予想気温 |
| `main.mart_jma_weekly_forecasts` | 週間天気予報 |
| `main.mart_jma_weekly_forecast_temps` | 週間予報の予想気温 |

## 使い方

東京の直近の日最高気温を出す:

```sql
SELECT d.observed_date, d.temp_max_c
FROM jma.main.mart_jma_daily_observations AS d
JOIN jma.main.mart_jma_observation_stations AS s USING (block_no)
WHERE s.station_name = '東京'
ORDER BY d.observed_date DESC;
```

東京のさくらの開花日と、平年との差の推移を出す:

```sql
SELECT year, observed_date, days_from_normal
FROM jma.main.mart_jma_sakura_phenology
WHERE station_name = '東京' AND phenomenon = '開花'
ORDER BY year;
```

## 注意

- 天気予報のテーブルは、ビルド時点の最新の発表だけを持ちます。過去の予報は蓄積していません
- 気象官署（`mart_jma_observation_stations`、ブロック番号）とアメダス観測所（`mart_jma_stations`、観測所 ID）は番号の体系が違います。両者は地点名で対応づけてください
- 観測していない要素、現象のない日、欠測は NULL です

## main.mart_jma_stations

全国のアメダス観測所の一覧です。観測所の位置（緯度経度・標高）と種別を持ちます。

- station_id: 観測所ID（VARCHAR、アメダス番号5桁）
- name / name_kana / name_en: 観測所名 漢字 / カナ / 英語（VARCHAR）
- lat / lon: 緯度 / 経度（DOUBLE、十進度）
- elevation: 標高（INTEGER、メートル）
- station_type: 観測所種別（VARCHAR、A〜G。A/Bが気象官署相当）
- is_office: 気象官署フラグ（BOOLEAN、種別A/B）
- elems: 観測種目フラグ（VARCHAR、気象庁仕様の8桁文字列）

## main.mart_jma_areas

気象庁の予報区の地域コードです。全国〜市区町村までの階層を level 付きで縦持ちにしています。

- area_code: 地域コード（VARCHAR）
- level: 階層（VARCHAR、center / office / class10 / class15 / class20）
- name / name_en: 地域名 / 英語（VARCHAR）
- name_kana: 地域名カナ（VARCHAR、class20のみ）
- office_name: 担当気象台名（VARCHAR、center / office のみ）
- parent_code: 親地域コード（VARCHAR、center は NULL）

## main.mart_jma_normals_daily

アメダス観測所の日別平年値（統計期間1991〜2020年）です。観測所×月日ごとに、気温・日照時間・降水量・積雪の深さの30年平均を持ちます。station_id で mart_jma_stations と結合できます。観測していない要素や統計値なしの日は NULL です（2月は閏日29日まで収録）。

- station_id: 観測所ID（VARCHAR、アメダス番号5桁）
- month / day: 月 / 日（INTEGER、月1〜12・日1〜31）
- temp_avg_c: 日平均気温の平年値（DOUBLE、℃）
- temp_max_c: 日最高気温の平年値（DOUBLE、℃）
- temp_min_c: 日最低気温の平年値（DOUBLE、℃）
- sunshine_hours: 日照時間の平年値（DOUBLE、時間）
- precipitation_mm: 降水量の平年値（DOUBLE、mm）
- snow_depth_cm: 積雪の深さ（日最大）の平年値（INTEGER、cm）

## main.mart_jma_observation_stations

日別観測値（mart_jma_daily_observations）を観測している気象官署の一覧です。観測所の位置（緯度経度）を持ちます。気象官署はアメダス観測所一覧（mart_jma_stations）とは別の観測所番号体系（ブロック番号）のため、両者は地点名で対応づけます。

- block_no: 観測所番号（VARCHAR、気象官署のブロック番号5桁）
- prec_no: 地方区分コード（VARCHAR、都府県・地方の区分。北海道などは複数に分かれる）
- station_name / station_kana: 観測所名 漢字 / カナ（VARCHAR）
- lat / lon: 緯度 / 経度（DOUBLE、十進度・世界測地系）

## main.mart_jma_daily_observations

気象官署の日別観測値（実況値）です。観測所×日ごとに、日平均・日最高・日最低気温、日降水量、日照時間、降雪・最深積雪を持ちます。block_no で mart_jma_observation_stations と結合できます。日別平年値（mart_jma_normals_daily、観測所名で対応づけ）と対にすると「実況 vs 平年」の比較ができます。全国の気象官署を対象に直近数か月分を収録しています（過去月の確定値は変わりません）。観測していない要素や現象のない日（降雪・積雪など）、欠測は NULL です。

- block_no: 観測所番号（VARCHAR、気象官署のブロック番号5桁）
- observed_date: 観測日（DATE、日本標準時）
- temp_avg_c: 日平均気温（DOUBLE、℃）
- temp_max_c: 日最高気温（DOUBLE、℃）
- temp_min_c: 日最低気温（DOUBLE、℃）
- precipitation_mm: 日降水量の合計（DOUBLE、mm。現象のない日・欠測は NULL）
- sunshine_hours: 日照時間（DOUBLE、時間）
- snowfall_cm: 降雪の合計（INTEGER、cm。現象のない日・観測なしは NULL）
- snow_depth_cm: 最深積雪（INTEGER、cm。現象のない日・観測なしは NULL）

## main.mart_jma_hourly_observations

気象官署の時別観測値（実況値）です。観測所×日×時（毎正時）ごとに、気温・降水量・湿度・風速・風向・日照時間・現地/海面気圧・最深積雪を持ちます。時は日本標準時で 1〜24（24 は 24 時＝翌日 0 時）です。block_no で mart_jma_observation_stations と結合できます。日別観測値（mart_jma_daily_observations）を時間帯まで細かくしたもので、需要予測・電力・小売などの時間帯分析に使えます。取得負荷を抑えるため各都道府県の地方・管区気象台がある主要地点（47 地点）に絞り、直近数日分を収録しています（過去日の確定値は変わりません）。観測していない要素や現象のない時（積雪など）、欠測は NULL です。

- block_no: 観測所番号（VARCHAR、気象官署のブロック番号5桁）
- observed_date: 観測日（DATE、日本標準時）
- hour: 時（INTEGER、毎正時・日本標準時の 1〜24。24 は 24 時＝翌日 0 時）
- temp_c: 気温（DOUBLE、℃）
- precipitation_mm: 1時間降水量（DOUBLE、mm。現象のない時・欠測は NULL）
- humidity_pct: 相対湿度（INTEGER、％）
- wind_speed_ms: 風速（DOUBLE、m/s）
- wind_direction: 風向（VARCHAR、16方位。無風時は「静穏」、欠測は NULL）
- sunshine_hours: 1時間あたりの日照時間（DOUBLE、時間）
- pressure_local_hpa: 現地気圧（DOUBLE、hPa）
- pressure_sea_hpa: 海面気圧（DOUBLE、hPa）
- snow_depth_cm: 積雪の深さ（INTEGER、cm。現象のない時・観測なしは NULL）

## main.mart_jma_hypocenters

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

## main.mart_jma_typhoon_tracks

台風の経路（ベストトラック）です。1951年以降に発生した台風について、6時間ごと（上陸前後などは3時間ごと）の中心位置・中心気圧・最大風速・暴風域と強風域の半径を持ちます。事後解析で確定した経路なので、速報の経路とは値が異なります。1台風＝複数行で、international_id（国際番号）で台風を識別します。約1,900個・約7万点を収録しています。

収録期間が要素によって違う点に注意してください。最大風速と暴風域・強風域の半径は1977年以降にしかなく、上陸・通過フラグが付くのは1991年以降の台風だけです（それより前は実際に上陸した台風でも false になるため、上陸数の長期比較には使えません）。階級には台風だけでなく熱帯低気圧・温帯低気圧の期間も含まれるので、台風としての統計を取るときは grade_code in ('3','4','5') で絞ります。

- international_id: 国際番号（VARCHAR、西暦下2桁＋年内の通し番号。例 2604 は2026年の台風4号）
- season: 発生年（INTEGER、国際番号の年。年をまたぐ台風では解析時刻の年と一致しないことがある）
- serial_number: 号数（INTEGER、年内の通し番号）
- name: 国際名（VARCHAR、アジア名または当時の英語名。命名前の台風は NULL）
- analysis_time: 解析時刻（TIMESTAMP、日本標準時）
- analysis_time_utc: 解析時刻（TIMESTAMP、協定世界時。元データの時刻）
- grade_code / grade: 階級のコードと名称（VARCHAR、2:熱帯低気圧 3:台風TS 4:台風STS 5:台風TY 6:温帯低気圧 7:責任領域に入った直後 9:TS以上の熱帯低気圧）
- latitude / longitude: 中心の緯度 / 経度（DOUBLE、十進度・0.1度単位。日付変更線を越えた経度は180を超える値になる）
- central_pressure_hpa: 中心気圧（INTEGER、hPa）
- max_wind_speed_kt: 最大風速（INTEGER、ノット。1977年より前と熱帯低気圧・温帯低気圧の期間は NULL）
- max_wind_speed_ms: 最大風速（DOUBLE、m/s。ノットからの換算値）
- wind50_direction_code / wind50_direction: 暴風域（50ノット以上）の長径方向コードと名称（VARCHAR、0:なし 1:北東 … 8:北 9:同心円）
- wind50_longest_radius_nm / wind50_shortest_radius_nm: 暴風域の長径 / 短径（INTEGER、海里。1海里=1.852km。暴風域がない場合は0、1977年より前は NULL）
- wind30_direction_code / wind30_direction: 強風域（30ノット以上）の長径方向コードと名称（VARCHAR、コード体系は暴風域と同じ）
- wind30_longest_radius_nm / wind30_shortest_radius_nm: 強風域の長径 / 短径（INTEGER、海里。1977年より前は NULL）
- is_landfall: 上陸・通過（BOOLEAN、この解析時刻から1時間以内に日本の陸地へ上陸または通過したか。1991年以降の台風のみ）

## main.mart_jma_sakura_phenology

生物季節観測によるさくらの開花日と満開日です。1953年以降、気象官署で観測した地点×年×現象（開花 / 満開）ごとに、観測日と平年値（1991〜2020年の平均）からの差を持ちます。block_no で mart_jma_observation_stations と結合できます。観測値のない年は行を持ちません。

観測地点は1990年の100地点から2020年代は57〜58地点に減っています。全国平均を年ごとに取ると地点構成の変化が混ざるので、地点ごとの時系列で比べます。種目は地点によって違い、奄美・沖縄のひかんざくらは前年12月に開花することがあります（その場合 day_of_year は0以下）。

- station_name: 地点名（VARCHAR、気象官署名）
- block_no: 観測所番号（VARCHAR、気象官署のブロック番号。地点名で mart_jma_observation_stations と対応づけたもの）
- species: 種目（VARCHAR、そめいよしの / えぞやまざくら / ひかんざくら / ちしまざくら）
- phenomenon: 現象（VARCHAR、開花 / 満開）
- year: 観測年（INTEGER）
- observed_date: 観測日（DATE、前年12月の日付になることがある）
- day_of_year: 年初からの日数（INTEGER、観測年の1月1日を1とした通日）
- normal_month / normal_day: 平年値の月 / 日（INTEGER、平年値の無い地点は NULL）
- days_from_normal: 平年差（INTEGER、日。負なら平年より早い）
- is_current_station: 現在の観測地点（BOOLEAN、現在も観測を続けている地点か）

## main.mart_jma_forecast_weather

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

## main.mart_jma_forecast_pops

府県予報区ごとの短期予報のうち、一次細分区域（class10）別・6 時間ごとの降水確率です。area_code で mart_jma_areas（level=class10）や mart_jma_forecast_weather と結合できます。mart_jma_forecast_weather と同じく、ビルド時点の最新発表の 1 スナップショットです。

- office_code: 府県予報区コード（VARCHAR、発表元。area.json の offices）
- report_datetime: 発表日時（TIMESTAMP WITH TIME ZONE、日本標準時）
- area_code: 区域コード（VARCHAR、一次細分区域 class10）
- area_name: 区域名（VARCHAR）
- forecast_datetime: 6 時間の区切りの開始日時（TIMESTAMP WITH TIME ZONE、日本標準時。00 時・06 時・12 時・18 時）
- pop_pct: 降水確率（INTEGER、%。その 6 時間に 1mm 以上の降水がある確率。値の無い区切りは NULL）

## main.mart_jma_forecast_temps

府県予報区ごとの短期予報のうち、地点別の予想気温です。地点はアメダスの観測所で、station_id で mart_jma_stations と結合できます。発表ごとに 2 時点前後の値を持ち、17 時発表では翌日の 0 時が朝の最低気温、9 時が日中の最高気温に当たります。ビルド時点の最新発表の 1 スナップショットです。

- office_code: 府県予報区コード（VARCHAR、発表元。area.json の offices）
- report_datetime: 発表日時（TIMESTAMP WITH TIME ZONE、日本標準時）
- station_id: 観測所 ID（VARCHAR、アメダス番号 5 桁）
- station_name: 地点名（VARCHAR）
- forecast_datetime: 予報対象日時（TIMESTAMP WITH TIME ZONE、日本標準時）
- temp_c: 予想気温（INTEGER、℃。値の無い時点は NULL）
## main.mart_jma_weekly_forecasts

府県予報区ごとの週間天気予報です。7 日分の天気・降水確率・信頼度を、週間予報の区域×日ごとに持ちます。区域は府県予報区単位か一次細分区域単位で、短期予報より粗くなります。

area_code の多くは府県予報区（level=office）か一次細分区域（level=class10）のコードと一致し、mart_jma_areas と結合できます。一部は週間予報だけの区域コード（例 020200 下北・三八上北）で、mart_jma_areas にはありません。短期予報と同じく、ビルド時点の最新発表の 1 スナップショットです。

- office_code: 府県予報区コード（VARCHAR、発表元。area.json の offices）
- report_datetime: 発表日時（TIMESTAMP WITH TIME ZONE、日本標準時）
- area_code: 区域コード（VARCHAR、週間予報の区域）
- area_name: 区域名（VARCHAR）
- forecast_date: 予報対象日（DATE、日本標準時）
- weather_code: 天気予報コード（VARCHAR、例 100:晴れ 200:くもり）
- pop_pct: 降水確率（INTEGER、%。予報期間の初日は NULL）
- reliability: 信頼度（VARCHAR、A:確度が高い B:確度がやや高い C:確度がやや低い。予報期間の初日と 2 日目は NULL）

## main.mart_jma_weekly_forecast_temps

週間予報のうち、地点別の予想最低気温・最高気温とその予測範囲です。地点はアメダスの観測所で、station_id で mart_jma_stations と結合できます。地点ごとの平年値（最低・最高気温と、7 日間合計降水量の平年並の範囲）も各行に付けています。ビルド時点の最新発表の 1 スナップショットです。

- office_code: 府県予報区コード（VARCHAR、発表元。area.json の offices）
- report_datetime: 発表日時（TIMESTAMP WITH TIME ZONE、日本標準時）
- station_id: 観測所ID（VARCHAR、アメダス番号5桁）
- station_name: 地点名（VARCHAR）
- forecast_date: 予報対象日（DATE、日本標準時）
- temp_min_c / temp_max_c: 予想最低気温 / 予想最高気温（INTEGER、℃。予報期間の初日は NULL）
- temp_min_lower_c / temp_min_upper_c: 予想最低気温の予測範囲の下端 / 上端（INTEGER、℃。予報期間の初日は NULL）
- temp_max_lower_c / temp_max_upper_c: 予想最高気温の予測範囲の下端 / 上端（INTEGER、℃。予報期間の初日は NULL）
- normal_temp_min_c / normal_temp_max_c: 最低気温 / 最高気温の平年値（DOUBLE、℃。地点ごとに 1 つ）
- normal_precip_lower_mm / normal_precip_upper_mm: 7 日間合計降水量の平年並の範囲の下端 / 上端（DOUBLE、mm。地点ごとに 1 つ）
