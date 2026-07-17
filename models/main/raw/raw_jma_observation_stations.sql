{# 気象官署の観測所レジストリ（過去の気象データ検索の観測所選択ページを整形したもの）
   元データ: https://www.data.jma.go.jp/stats/etrn/index.php
   main.py が prec_no ごとの選択ページから気象官署（type s）の block_no・地点名・位置を
   取り出して .fdl/jma_observation_stations.ndjson に保存する #}

{{
    config(
        materialized='table'
    )
}}

select *
from read_json(
    '.fdl/jma_observation_stations.ndjson',
    format='newline_delimited',
    columns={
        'block_no': 'VARCHAR',
        'prec_no': 'VARCHAR',
        'station_name': 'VARCHAR',
        'station_kana': 'VARCHAR',
        'lat': 'DOUBLE',
        'lon': 'DOUBLE'
    }
)
