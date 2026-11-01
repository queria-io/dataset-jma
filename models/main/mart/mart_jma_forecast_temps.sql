{{ config(materialized='view') }}

select
    office_code,
    report_datetime::timestamptz as report_datetime,
    area_code as station_id,
    area_name as station_name,
    forecast_datetime::timestamptz as forecast_datetime,
    try_cast(nullif(temp, '') as integer) as temp_c
from {{ ref('raw_jma_forecast_temps') }}
