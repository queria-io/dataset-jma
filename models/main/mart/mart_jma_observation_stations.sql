{{ config(materialized='view') }}

select
    block_no,
    prec_no,
    station_name,
    station_kana,
    lat,
    lon
from {{ ref('raw_jma_observation_stations') }}
