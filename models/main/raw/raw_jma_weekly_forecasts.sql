{# 府県予報区ごとの週間天気予報（forecast JSON の 2 要素目を週間予報の区域×日に展開したもの）
   元データ: https://www.jma.go.jp/bosai/forecast/
   main.py が offices ごとの予報の 2 要素目・timeSeries[0]（天気コード・降水確率・信頼度）を
   区域×timeDefines に展開して .queria/jma_weekly_forecasts.ndjson に保存する #}

{{
    config(
        materialized='table'
    )
}}

select *
from read_json(
    '.queria/jma_weekly_forecasts.ndjson',
    format='newline_delimited',
    columns={
        'office_code': 'VARCHAR',
        'report_datetime': 'VARCHAR',
        'area_code': 'VARCHAR',
        'area_name': 'VARCHAR',
        'forecast_datetime': 'VARCHAR',
        'weather_code': 'VARCHAR',
        'pop': 'VARCHAR',
        'reliability': 'VARCHAR'
    }
)
