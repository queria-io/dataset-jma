{# 気象庁 生物季節観測のさくらの開花日・満開日（累年表のページを整形したもの）
   元データ: https://www.data.jma.go.jp/sakura/data/index.html
   main.py が現象ごとに年代別のページをたどり、地点 × 年の観測日を取り出して
   .queria/jma_sakura_phenology.ndjson に保存する（観測値なしの年は含めない） #}

{{
    config(
        materialized='table'
    )
}}

select *
from read_json(
    '.queria/jma_sakura_phenology.ndjson',
    format='newline_delimited',
    columns={
        'phenomenon': 'VARCHAR',
        'station_name': 'VARCHAR',
        'is_current_station': 'BOOLEAN',
        'species': 'VARCHAR',
        'year': 'INTEGER',
        'observed_date': 'DATE',
        'normal_month': 'INTEGER',
        'normal_day': 'INTEGER'
    }
)
