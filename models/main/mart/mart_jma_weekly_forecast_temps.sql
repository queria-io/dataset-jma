{{ config(materialized='view') }}

-- forecast_datetime は日本標準時のオフセット付き文字列なので、先頭 10 文字が JST の日付になる
select
    office_code,
    report_datetime::timestamptz as report_datetime,
    station_id,
    station_name,
    left(forecast_datetime, 10)::date as forecast_date,
    try_cast(nullif(temp_min, '') as integer) as temp_min_c,
    try_cast(nullif(temp_min_lower, '') as integer) as temp_min_lower_c,
    try_cast(nullif(temp_min_upper, '') as integer) as temp_min_upper_c,
    try_cast(nullif(temp_max, '') as integer) as temp_max_c,
    try_cast(nullif(temp_max_lower, '') as integer) as temp_max_lower_c,
    try_cast(nullif(temp_max_upper, '') as integer) as temp_max_upper_c,
    try_cast(nullif(normal_temp_min, '') as double) as normal_temp_min_c,
    try_cast(nullif(normal_temp_max, '') as double) as normal_temp_max_c,
    try_cast(nullif(normal_precip_lower, '') as double) as normal_precip_lower_mm,
    try_cast(nullif(normal_precip_upper, '') as double) as normal_precip_upper_mm
from {{ ref('raw_jma_weekly_forecast_temps') }}
