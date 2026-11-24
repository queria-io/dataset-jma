{{ config(materialized='ephemeral') }}

-- raw_jma_observation_stations を mart から読むための stg。列は raw のまま
SELECT * FROM {{ ref('raw_jma_observation_stations') }}
