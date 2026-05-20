{{ config(
    materialized='table'
) }}

WITH match_features AS (
    -- Pull pre-calculated match features and historical analytics proxies
    SELECT * FROM {{ ref('int_match_features') }}
)

SELECT
    -- Identifiers & Core Metadata
    match_id,
    match_date,
    competition_name,
    season_name,
    home_team,
    away_team,
    
    -- Target Variable (Ground Truth Label for XGBoost)
    match_result,

    -- Home Team 5-Match Rolling Features
    home_rolling_xg,
    home_rolling_points,
    home_rolling_possession,
    home_rolling_pressures,
    home_rolling_pass_accuracy,

    -- Away Team 5-Match Rolling Features
    away_rolling_xg,
    away_rolling_points,
    away_rolling_possession,
    away_rolling_pressures,
    away_rolling_pass_accuracy,

    -- Historical Head-to-Head Feature
    h2h_home_win_pct

FROM match_features