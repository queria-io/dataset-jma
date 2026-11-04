{# 府県予報区ごとの短期予報の降水確率（forecast JSON を class10 区域×6時間ごとの時点に展開したもの）
   元データ: https://www.jma.go.jp/bosai/forecast/
   main.py が offices ごとの予報の先頭要素・timeSeries[1]（pops）を
   一次細分区域×timeDefines に展開して .queria/jma_forecast_pops.ndjson に保存する #}

{{
    config(
        materialized='table'
    )
}}

select *
from read_json(
    '.queria/jma_forecast_pops.ndjson',
    format='newline_delimited',
    columns={
        'office_code': 'VARCHAR',
        'report_datetime': 'VARCHAR',
        'area_code': 'VARCHAR',
        'area_name': 'VARCHAR',
        'forecast_datetime': 'VARCHAR',
        'pop': 'VARCHAR'
    }
)
