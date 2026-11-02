{# 府県予報区ごとの週間予報の予想気温（forecast JSON の 2 要素目をアメダス地点×日に展開したもの）
   元データ: https://www.jma.go.jp/bosai/forecast/
   main.py が offices ごとの予報の 2 要素目・timeSeries[1]（最低・最高気温と予測範囲）を
   地点×timeDefines に展開し、地点ごとの平年値（tempAverage / precipAverage）を付けて
   .queria/jma_weekly_forecast_temps.ndjson に保存する #}

{{
    config(
        materialized='table'
    )
}}

select *
from read_json(
    '.queria/jma_weekly_forecast_temps.ndjson',
    format='newline_delimited',
    columns={
        'office_code': 'VARCHAR',
        'report_datetime': 'VARCHAR',
        'station_id': 'VARCHAR',
        'station_name': 'VARCHAR',
        'forecast_datetime': 'VARCHAR',
        'temp_min': 'VARCHAR',
        'temp_min_upper': 'VARCHAR',
        'temp_min_lower': 'VARCHAR',
        'temp_max': 'VARCHAR',
        'temp_max_upper': 'VARCHAR',
        'temp_max_lower': 'VARCHAR',
        'normal_temp_min': 'VARCHAR',
        'normal_temp_max': 'VARCHAR',
        'normal_precip_lower': 'VARCHAR',
        'normal_precip_upper': 'VARCHAR'
    }
)
