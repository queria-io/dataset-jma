{{ config(materialized='view') }}

select
    international_id,
    season,
    serial_number,
    name,
    analysis_time,
    analysis_time_utc,
    grade_code,
    case grade_code
        when '2' then '熱帯低気圧'
        when '3' then '台風（TS）'
        when '4' then '台風（STS）'
        when '5' then '台風（TY）'
        when '6' then '温帯低気圧'
        when '7' then '責任領域に入った直後'
        when '9' then 'TS以上の熱帯低気圧'
    end as grade,
    latitude,
    longitude,
    central_pressure_hpa,
    max_wind_speed_kt,
    round(max_wind_speed_kt * 0.514444, 1)::double as max_wind_speed_ms,
    wind50_direction_code,
    case wind50_direction_code
        when '0' then 'なし'
        when '1' then '北東'
        when '2' then '東'
        when '3' then '南東'
        when '4' then '南'
        when '5' then '南西'
        when '6' then '西'
        when '7' then '北西'
        when '8' then '北'
        when '9' then '同心円'
    end as wind50_direction,
    wind50_longest_radius_nm,
    wind50_shortest_radius_nm,
    wind30_direction_code,
    case wind30_direction_code
        when '0' then 'なし'
        when '1' then '北東'
        when '2' then '東'
        when '3' then '南東'
        when '4' then '南'
        when '5' then '南西'
        when '6' then '西'
        when '7' then '北西'
        when '8' then '北'
        when '9' then '同心円'
    end as wind30_direction,
    wind30_longest_radius_nm,
    wind30_shortest_radius_nm,
    is_landfall
from {{ ref('raw_jma_typhoon_tracks') }}
