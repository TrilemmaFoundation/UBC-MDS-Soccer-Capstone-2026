{{ config(materialized='table') }}

WITH source AS (
    SELECT * FROM {{ source('polymarket', 'soccer_markets') }}
),

renamed AS (
    SELECT
        CAST(market_id AS STRING)               AS market_id,
        CAST(question AS STRING)                AS question,
        CAST(slug AS STRING)                    AS slug,
        CAST(event_slug AS STRING)              AS event_slug,
        CAST(category AS STRING)                AS category,
        SAFE_CAST(volume AS FLOAT64)            AS volume_usd,
        CAST(active AS BOOL)                    AS is_active,
        CAST(closed AS BOOL)                    AS is_closed,
        CAST(created_at AS TIMESTAMP)           AS created_at,
        CAST(end_date AS TIMESTAMP)             AS end_date
    FROM source
)

SELECT * FROM renamed