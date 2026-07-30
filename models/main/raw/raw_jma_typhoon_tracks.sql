{# 気象庁 RSMC 東京・台風センターのベストトラック（80 桁固定長のテキストを整形したもの）
   元データ: https://www.jma.go.jp/jma/jma-eng/jma-center/rsmc-hp-pub-eg/Besttracks/
   main.py が全期間の ZIP を取得し、ヘッダ行の台風属性を各解析行に展開して
   位置を十進度に直し .queria/jma_typhoon_tracks.ndjson に保存 #}

{{
    config(
        materialized='table'
    )
}}

select *
from read_json(
    '.queria/jma_typhoon_tracks.ndjson',
    format='newline_delimited',
    columns={
        'international_id': 'VARCHAR',
        'season': 'INTEGER',
        'serial_number': 'INTEGER',
        'name': 'VARCHAR',
        'analysis_time': 'TIMESTAMP',
        'analysis_time_utc': 'TIMESTAMP',
        'grade_code': 'VARCHAR',
        'latitude': 'DOUBLE',
        'longitude': 'DOUBLE',
        'central_pressure_hpa': 'INTEGER',
        'max_wind_speed_kt': 'INTEGER',
        'wind50_direction_code': 'VARCHAR',
        'wind50_longest_radius_nm': 'INTEGER',
        'wind50_shortest_radius_nm': 'INTEGER',
        'wind30_direction_code': 'VARCHAR',
        'wind30_longest_radius_nm': 'INTEGER',
        'wind30_shortest_radius_nm': 'INTEGER',
        'is_landfall': 'BOOLEAN'
    }
)
