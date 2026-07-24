{{ config(materialized='view') }}

select
    block_no,
    observed_date,
    hour,
    temp_c,
    precipitation_mm,
    humidity_pct,
    wind_speed_ms,
    wind_direction,
    sunshine_hours,
    pressure_local_hpa,
    pressure_sea_hpa,
    snow_depth_cm
from {{ ref('raw_jma_hourly_observations') }}
