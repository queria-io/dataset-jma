{{ config(materialized='view') }}

with stations as (
    select
        block_no,
        -- 過去の気象データ検索では南大東島だけ地点名の表記が違う。
        case station_name
            when '南大東（南大東島）' then '南大東島'
            else station_name
        end as station_name
    from {{ ref('raw_jma_observation_stations') }}
)

select
    p.station_name,
    s.block_no,
    p.species,
    p.phenomenon,
    p.year,
    p.observed_date,
    (date_diff('day', make_date(p.year, 1, 1), p.observed_date) + 1)::integer as day_of_year,
    p.normal_month,
    p.normal_day,
    date_diff('day', make_date(p.year, p.normal_month, p.normal_day), p.observed_date)::integer
        as days_from_normal,
    p.is_current_station
from {{ ref('raw_jma_sakura_phenology') }} as p
left join stations as s
    on p.station_name = s.station_name
