{# 気象官署の日別観測値（過去の気象データ検索の日別値ページ daily_s1.php を整形したもの）
   元データ: https://www.data.jma.go.jp/stats/etrn/index.php
   main.py が気象官署ごとに直近数か月分の日別値を取得し、平年値と対になる中核要素
   （気温・降水量・日照時間・降雪・積雪）を観測所×日で .fdl/jma_daily_observations.ndjson に保存する #}

{{
    config(
        materialized='table'
    )
}}

select *
from read_json(
    '.fdl/jma_daily_observations.ndjson',
    format='newline_delimited',
    columns={
        'block_no': 'VARCHAR',
        'observed_date': 'DATE',
        'precipitation_mm': 'DOUBLE',
        'temp_avg_c': 'DOUBLE',
        'temp_max_c': 'DOUBLE',
        'temp_min_c': 'DOUBLE',
        'sunshine_hours': 'DOUBLE',
        'snowfall_cm': 'INTEGER',
        'snow_depth_cm': 'INTEGER'
    }
)
