{{ config(materialized='table') }}

WITH source AS (
    SELECT * FROM {{ source('statsbomb', 'matches') }}
),

renamed AS (
    SELECT
        CAST(match_id AS INT64)                          AS match_id,
        CAST(match_date AS DATE)                         AS match_date,
		CAST(kickoff AS STRING) 						 AS kickoff,
        CAST(competition_id AS INT64)                    AS competition_id,
        CAST(season_id AS INT64)                         AS season_id,
        TRIM(home_team) AS home_team,
        TRIM(away_team) AS away_team,
        CAST(home_score AS INT64)                        AS home_score,
        CAST(away_score AS INT64)                        AS away_score,
        CAST(competition_name AS STRING)                 AS competition_name,
        CAST(season_name AS STRING)                      AS season_name,
        CAST(is_international AS BOOL)                   AS is_international,
		CAST(is_international AS BOOL)  				 AS is_international,
		CAST(gender AS STRING)           				 AS gender,
		CAST(is_youth AS BOOL)           				 AS is_youth,
        CASE
            WHEN CAST(home_score AS INT64) > CAST(away_score AS INT64) THEN 'home_win'
            WHEN CAST(home_score AS INT64) < CAST(away_score AS INT64) THEN 'away_win'
            ELSE 'draw'
        END AS match_result

    FROM source
    WHERE CAST(season_name AS STRING) >= '2000'
)

SELECT * FROM renamed