{{ config(materialized='table') }}

WITH source AS (
    SELECT * FROM {{ source('statsbomb', 'lineups') }}
),

renamed AS (
    SELECT
        CAST(match_id AS INT64)                             AS match_id,
        CAST(player_id AS INT64)                            AS player_id,
        CAST(player_name AS STRING)                         AS player_name,
        CAST(team_name AS STRING)                           AS team_name,
        CAST(jersey_number AS INT64)                        AS jersey_number,
        COALESCE(REGEXP_EXTRACT(CAST(positions AS STRING), "'position': '([^']+)'"), 'Unknown') AS position_name,
        REGEXP_EXTRACT(CAST(positions AS STRING), "'from': '([^']+)'")                       AS from_time,
        REGEXP_EXTRACT(CAST(positions AS STRING), "'to': '([^']+)'")                         AS to_time,
        REGEXP_EXTRACT(CAST(cards AS STRING), "'card_type': '([^']+)'")                      AS card_type

    FROM source
    WHERE CAST(match_id AS INT64) IN (
        SELECT match_id FROM {{ ref('stg_statsbomb__matches') }}
    )
)

SELECT * FROM renamed