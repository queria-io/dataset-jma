{{ config(materialized='ephemeral') }}

-- raw_jma_hourly_observations を mart から読むための stg。列は raw のまま
SELECT * FROM {{ ref('raw_jma_hourly_observations') }}
