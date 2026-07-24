{# 気象官署の時別観測値（過去の気象データ検索の時別値ページ hourly_s1.php を整形したもの）
   元データ: https://www.data.jma.go.jp/stats/etrn/index.php
   main.py が主要な気象官署ごとに直近数日分の時別値を取得し、気圧・降水量・気温・湿度・
   風・日照・積雪を観測所×日時で .fdl/jma_hourly_observations.ndjson に保存する #}

{{
    config(
        materialized='table'
    )
}}

select *
from read_json(
    '.fdl/jma_hourly_observations.ndjson',
    format='newline_delimited',
    columns={
        'block_no': 'VARCHAR',
        'observed_date': 'DATE',
        'hour': 'INTEGER',
        'pressure_local_hpa': 'DOUBLE',
        'pressure_sea_hpa': 'DOUBLE',
        'precipitation_mm': 'DOUBLE',
        'temp_c': 'DOUBLE',
        'humidity_pct': 'INTEGER',
        'wind_speed_ms': 'DOUBLE',
        'wind_direction': 'VARCHAR',
        'sunshine_hours': 'DOUBLE',
        'snow_depth_cm': 'INTEGER'
    }
)
