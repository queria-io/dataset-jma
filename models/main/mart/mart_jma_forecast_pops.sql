{{ config(materialized='view') }}

select
    office_code,
    report_datetime::timestamptz as report_datetime,
    area_code,
    area_name,
    forecast_datetime::timestamptz as forecast_datetime,
    try_cast(nullif(pop, '') as integer) as pop_pct
from {{ ref('raw_jma_forecast_pops') }}
