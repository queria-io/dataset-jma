{{ config(materialized='view') }}

-- forecast_datetime は日本標準時のオフセット付き文字列なので、先頭 10 文字が JST の日付になる
select
    office_code,
    report_datetime::timestamptz as report_datetime,
    area_code,
    area_name,
    left(forecast_datetime, 10)::date as forecast_date,
    weather_code,
    try_cast(nullif(pop, '') as integer) as pop_pct,
    nullif(reliability, '') as reliability
from {{ ref('raw_jma_weekly_forecasts') }}
