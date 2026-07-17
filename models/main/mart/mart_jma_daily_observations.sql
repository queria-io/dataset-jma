{{ config(materialized='view') }}

select
    block_no,
    observed_date,
    temp_avg_c,
    temp_max_c,
    temp_min_c,
    precipitation_mm,
    sunshine_hours,
    snowfall_cm,
    snow_depth_cm
from {{ ref('raw_jma_daily_observations') }}
