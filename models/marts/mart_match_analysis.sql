{{ config(
    materialized='table',
    partition_by={
      "field": "match_date",
      "data_type": "date"
    },
    cluster_by=["competition_id"]
) }}

WITH match_metadata AS (
    SELECT * FROM {{ ref('stg_statsbomb__matches') }}
),

match_stats AS (
    SELECT * FROM {{ ref('int_match_stats') }}
),

home_stats AS (
    SELECT
        match_id,
        total_shots AS home_shots,
        total_xg AS home_xg,
        pass_completion_pct AS home_pass_completion_pct,
        possession_share AS home_possession_proxy,
        total_pressures AS home_total_pressures,
        total_carries AS home_total_carries
    FROM match_stats
    WHERE side = 'home'
),

away_stats AS (
    SELECT
        match_id,
        total_shots AS away_shots,
        total_xg AS away_xg,
        pass_completion_pct AS away_pass_completion_pct,
        possession_share AS away_possession_proxy,
        total_pressures AS away_total_pressures,
        total_carries AS away_total_carries
    FROM match_stats
    WHERE side = 'away'
)

SELECT
    -- Match Metadata
    m.match_id,
    m.match_date,
    m.competition_id,
    m.competition_name,
    m.season_id,
    m.season_name,
    m.home_team,
    m.away_team,
    m.home_score,
    m.away_score,
    m.match_result,

    -- Home Team Performance Metrics
    h.home_xg,
    h.home_possession_proxy,
    h.home_pass_completion_pct,
    h.home_shots,
    h.home_total_pressures,
    h.home_total_carries,

    -- Away Team Performance Metrics
    a.away_xg,
    a.away_possession_proxy,
    a.away_pass_completion_pct,
    a.away_shots,
    a.away_total_pressures,
    a.away_total_carries

FROM match_metadata m
LEFT JOIN home_stats h ON m.match_id = h.match_id
LEFT JOIN away_stats a ON m.match_id = a.match_id