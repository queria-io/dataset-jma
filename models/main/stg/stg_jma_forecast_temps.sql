{{ config(materialized='ephemeral') }}

-- raw_jma_forecast_temps を mart から読むための stg。列は raw のまま
SELECT * FROM {{ ref('raw_jma_forecast_temps') }}
