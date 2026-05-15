{{ config(materialized='table') }}

WITH source AS (
    SELECT * FROM {{ source('polymarket', 'soccer_odds_history') }}
),

renamed AS (
    SELECT
        CAST(market_id AS STRING)               AS market_id,
        CAST(token_id AS STRING)                AS token_id,
        CAST(timestamp AS TIMESTAMP)            AS recorded_at,
        SAFE_CAST(price AS FLOAT64)             AS implied_probability
    FROM source
    WHERE SAFE_CAST(price AS FLOAT64) BETWEEN 0 AND 1
)

SELECT * FROM renamed