{{
    config(
        materialized='incremental',
        unique_key='event_id',
        incremental_strategy='merge'
    )
}}

WITH source AS (
    SELECT * FROM {{ source('statsbomb', 'events') }}
    {% if is_incremental() %}
        WHERE CAST(match_id AS INT64) IN (
            SELECT CAST(match_id AS INT64)
            FROM {{ source('statsbomb', 'matches') }}
            WHERE CAST(match_date AS DATE) > (
                SELECT MAX(CAST(match_date AS DATE))
                FROM {{ source('statsbomb', 'matches') }}
                WHERE CAST(match_id AS INT64) IN (SELECT DISTINCT match_id FROM {{ this }})
            )
        )
    {% endif %}
),

renamed AS (
    SELECT
        CAST(id AS STRING)                       AS event_id,
        CAST(match_id AS INT64)                  AS match_id,
        CAST(period AS INT64)                    AS period,
        CAST(minute AS INT64)                    AS minute,
        CAST(second AS INT64)                    AS second,
        CAST(type AS STRING)                     AS event_type,
        CAST(team AS STRING)                     AS team,
        CAST(player AS STRING)                   AS player,
        SAFE_CAST(REGEXP_EXTRACT(CAST(location AS STRING), r'\[(-?[\d.]+)') AS FLOAT64)     AS location_x,
        SAFE_CAST(REGEXP_EXTRACT(CAST(location AS STRING), r'\s+(-?[\d.]+)\]') AS FLOAT64)  AS location_y,
        CAST(play_pattern AS STRING)             AS play_pattern,
        SAFE_CAST(shot_statsbomb_xg AS FLOAT64)  AS shot_statsbomb_xg,
        CAST(pass_outcome AS STRING)             AS pass_outcome

    FROM source
    WHERE player IS NOT NULL
      AND CAST(match_id AS INT64) IN (
          SELECT match_id FROM {{ ref('stg_statsbomb__matches') }}
      )
)

SELECT * FROM renamed