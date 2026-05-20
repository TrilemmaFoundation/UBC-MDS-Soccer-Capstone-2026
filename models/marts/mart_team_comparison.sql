{{ config(
    materialized='table'
) }}

WITH team_season_base AS (
    -- Pull overall season performance aggregates
    SELECT * FROM {{ ref('int_team_season_stats') }}
),

rolling_form_base AS (
    -- Pull match-by-match rolling performance figures
    SELECT * FROM {{ ref('int_team_rolling_form') }}
),

int_match_metadata AS (
    -- Pull match stats to link rolling match dates to season/competition identifiers
    SELECT 
        match_id,
        team,
        competition_name,
        season_name
    FROM {{ ref('int_match_stats') }}
),

rolling_with_metadata AS (
    -- Associate competition/season context onto match-level rolling form rows
    SELECT 
        r.*,
        m.competition_name,
        m.season_name
    FROM rolling_form_base r
    INNER JOIN int_match_metadata m
        ON r.match_id = m.match_id
        AND r.team = m.team
),

latest_rolling_form AS (
    -- Deduplicate and extract each team's most recent rolling form numbers per competition season
    SELECT
        team,
        competition_name,
        season_name,
        rolling_avg_xg,
        rolling_avg_points,
        rolling_avg_possession_pct,
        rolling_avg_pressures,
        rolling_avg_pass_completion_pct
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY team, competition_name, season_name 
                ORDER BY match_date DESC
            ) AS rn
        FROM rolling_with_metadata
    )
    WHERE rn = 1
)

SELECT
    -- Team & Campaign Metadata
    s.team,
    s.competition_id,
    s.competition_name,
    s.season_id,
    s.season_name,
    s.matches_played,

    -- Long-Term Seasonal Performance Metrics
    s.wins,
    s.draws,
    s.losses,
    s.total_points,
    s.total_xg                  AS seasonal_total_xg,
    s.avg_xg_per_match          AS seasonal_avg_xg,
    s.avg_possession_share      AS seasonal_avg_possession,
    s.total_pressures           AS seasonal_total_pressures,
    s.avg_pressures_per_match   AS seasonal_avg_pressures,

    -- Short-Term Momentum Metrics (Latest Form From Season Outset)
    r.rolling_avg_xg            AS latest_rolling_xg,
    r.rolling_avg_points        AS latest_rolling_points,
    r.rolling_avg_possession_pct AS latest_rolling_possession,
    r.rolling_avg_pressures     AS latest_rolling_pressures,
    r.rolling_avg_pass_completion_pct AS latest_rolling_pass_accuracy

FROM team_season_base s
LEFT JOIN latest_rolling_form r
    ON s.team = r.team
    AND s.competition_name = r.competition_name
    AND s.season_name = r.season_name