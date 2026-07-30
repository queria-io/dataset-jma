## データ出典

[気象庁](https://www.jma.go.jp/)が公開している気象・地震データです。観測所一覧（アメダス）・予報区の地域コード、府県予報区ごとの短期天気予報、地震月報（カタログ編）の震源データ、アメダス観測所の日別平年値（1991〜2020年）、気象官署の日別観測値・時別観測値（実況値）と、台風の経路（ベストトラック、1951年〜）を収録しています。

観測所一覧・地域コード・天気予報は非公式の JSON 配信（気象庁サイトが内部利用しているエンドポイント）を、日別平年値は平年値ダウンロードの配布ファイルを、気象官署の観測所一覧・日別観測値・時別観測値は過去の気象データ検索のページを、台風の経路は RSMC 東京・台風センターのベストトラック配布ファイルを出典として利用しています。

- 観測所一覧: https://www.jma.go.jp/bosai/amedas/const/amedastable.json
- 地域コード: https://www.jma.go.jp/bosai/common/const/area.json
- 天気予報: https://www.jma.go.jp/bosai/forecast/
- 震源データ（地震月報 カタログ編）: https://www.data.jma.go.jp/eqev/data/bulletin/hypo.html
- 日別平年値: https://www.data.jma.go.jp/stats/data/mdrr/normal/index.html （normal_amedas_daily）
- 気象官署の観測所一覧・日別観測値: https://www.data.jma.go.jp/stats/etrn/index.php （過去の気象データ検索）
- 台風の経路（ベストトラック）: https://www.jma.go.jp/jma/jma-eng/jma-center/rsmc-hp-pub-eg/Besttracks/index.html

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

## テーブル: mart_jma_observation_stations

日別観測値（mart_jma_daily_observations）を観測している気象官署の一覧です。観測所の位置（緯度経度）を持ちます。気象官署はアメダス観測所一覧（mart_jma_stations）とは別の観測所番号体系（ブロック番号）のため、両者は地点名で対応づけます。

- block_no: 観測所番号（VARCHAR、気象官署のブロック番号5桁）
- prec_no: 地方区分コード（VARCHAR、都府県・地方の区分。北海道などは複数に分かれる）
- station_name / station_kana: 観測所名 漢字 / カナ（VARCHAR）
- lat / lon: 緯度 / 経度（DOUBLE、十進度・世界測地系）

## テーブル: mart_jma_daily_observations

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

## テーブル: mart_jma_hourly_observations

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

## テーブル: mart_jma_typhoon_tracks

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

main.py が気象庁の JSON（amedastable.json / area.json / 府県予報区ごとの forecast）、地震月報（カタログ編）の年別震源 ZIP（96 バイト固定長）、平年値ダウンロードの日別平年値 ZIP（normal_amedas_daily）、RSMC 東京・台風センターのベストトラック ZIP（80 桁固定長）と、過去の気象データ検索の観測所選択ページ・気象官署の日別値ページ（daily_s1.php）・時別値ページ（hourly_s1.php）を取得し、緯度経度の十進度化・地域階層のフラット化・天気予報の区域×対象日時への展開・震源レコードの解析・日別平年値の観測所×月日への展開と実単位へのスケール・ベストトラックのヘッダ行（台風の属性）の各解析行への展開・日別観測値の観測所×日への整形・時別観測値の観測所×日時への整形を行って `.queria/` に NDJSON として保存し、dbt build でテーブルを再生成する。ビルドは `bash scripts/build.sh` で実行する（Queria に公開する）。震源データの収録年は main.py の `HYPOCENTER_YEARS` で、日別観測値の収録月数は `OBS_MONTHS` で、時別観測値の収録日数は `OBS_HOURLY_DAYS`・対象地点は `MAJOR_STATION_NAMES` で調整する。

## ライセンス

出典は気象庁。[気象庁ホームページ利用規約](https://www.jma.go.jp/jma/kishou/info/coment.html)（政府標準利用規約 第2.0版に準拠）に従う。
