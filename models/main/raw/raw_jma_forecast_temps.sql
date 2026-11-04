{# 府県予報区ごとの短期予報の予想気温（forecast JSON をアメダス地点×対象日時に展開したもの）
   元データ: https://www.jma.go.jp/bosai/forecast/
   main.py が offices ごとの予報の先頭要素・timeSeries[2]（temps）を
   地点×timeDefines に展開して .queria/jma_forecast_temps.ndjson に保存する #}

{{
    config(
        materialized='table'
    )
}}

select *
from read_json(
    '.queria/jma_forecast_temps.ndjson',
    format='newline_delimited',
    columns={
        'office_code': 'VARCHAR',
        'report_datetime': 'VARCHAR',
        'area_code': 'VARCHAR',
        'area_name': 'VARCHAR',
        'forecast_datetime': 'VARCHAR',
        'temp': 'VARCHAR'
    }
)
