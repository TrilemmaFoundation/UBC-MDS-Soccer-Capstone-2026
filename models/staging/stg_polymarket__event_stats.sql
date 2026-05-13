{{ config(materialized='table') }}

WITH source AS (
    SELECT * FROM {{ source('polymarket', 'soccer_event_stats') }}
),

renamed AS (
    SELECT
        CAST(event_slug AS STRING)                          AS event_slug,
        SAFE_CAST(market_count AS INT64)                    AS market_count,
        SAFE_CAST(total_volume AS FLOAT64)                  AS total_volume_usd,
        CAST(first_market_start AS TIMESTAMP)               AS first_market_start,
        CAST(last_market_end AS TIMESTAMP)                  AS last_market_end,
        REGEXP_EXTRACT(event_slug, r'^([a-z]+)-')           AS competition_prefix
    FROM source
)

SELECT * FROM renamed