{{ config(materialized='table') }}

WITH source AS (
    SELECT * FROM {{ source('statsbomb', 'lineups') }}
),

renamed AS (
    SELECT
        CAST(match_id AS INT64)                                     AS match_id,
        CAST(player_id AS INT64)                                    AS player_id,
        CAST(player_name AS STRING)                                 AS player_name,
        CAST(team_name AS STRING)                                   AS team_name,
        CAST(jersey_number AS INT64)                                AS jersey_number,
        COALESCE(CAST(position_name AS STRING), 'Unknown')          AS position_name,
        SAFE_CAST(from_time AS INT64)                               AS from_time,
        SAFE_CAST(to_time AS INT64)                                 AS to_time,
        COALESCE(SAFE_CAST(to_time AS INT64), 90)
            - COALESCE(SAFE_CAST(from_time AS INT64), 0)            AS minutes_played,
        CAST(card_type AS STRING)                                   AS card_type

    FROM source
	WHERE match_id IN (SELECT CAST(match_id AS INT64) FROM {{ ref('stg_statsbomb__matches') }})
)

SELECT * FROM renamed