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
        COALESCE(CAST(position_name AS STRING), 'Unknown')  AS position_name,
        CAST(from_time AS STRING)                           AS from_time,
        CAST(to_time AS STRING)                             AS to_time,
        CAST(card_type AS STRING)                           AS card_type

    FROM source
    WHERE CAST(match_id AS INT64) IN (
        SELECT match_id FROM {{ ref('stg_statsbomb__matches') }}
    )
)

SELECT * FROM renamed