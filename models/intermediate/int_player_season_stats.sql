{{ config(materialized='table') }}

WITH player_match_stats AS (
    SELECT * FROM {{ ref('int_player_match_stats') }}
),

matches AS (
    SELECT * FROM {{ ref('stg_statsbomb__matches') }}
),

-- Join match metadata to player stats to get competition and season IDs
player_match_with_meta AS (
    SELECT
        pms.*,
        m.competition_id,
        m.season_id,
        m.competition_name,
        m.season_name
    FROM player_match_stats pms
    INNER JOIN matches m ON pms.match_id = m.match_id
),

-- Aggregate to the season level and apply the 450-minute threshold
aggregated AS (
    SELECT
        player_id,
        player_name,
        competition_id,
        competition_name,
        season_id,
        season_name,
        -- Aggregate raw totals
        SUM(minutes_played) AS total_minutes,
        SUM(goals) AS total_goals,
        SUM(assists) AS total_assists,
        SUM(shots) AS total_shots,
        SUM(total_xg) AS total_xg,
        SUM(passes_attempted) AS total_passes_attempted,
        SUM(passes_completed) AS total_passes_completed,
        SUM(pressures) AS total_pressures,
        SUM(tackles) AS total_tackles,
        SUM(interceptions) AS total_interceptions,
        SUM(carries) AS total_carries,
        SUM(aerial_duels) AS total_aerial_duels,
        
        -- Totals for features
        SUM(dribbles) AS total_dribbles,
        SUM(clearances) AS total_clearances,
        SUM(carries_att_third) AS total_carries_att_third,
        SUM(passes_att_third) AS total_passes_att_third
    FROM player_match_with_meta
    GROUP BY 1, 2, 3, 4, 5, 6
    HAVING SUM(minutes_played) >= 450
),

-- Calculate normalized per-90 metrics
final AS (
    SELECT
        *,
        -- Per-90 Metrics: (Metric / Minutes) * 90
        SAFE_DIVIDE(total_goals, total_minutes) * 90 AS goals_per_90,
        SAFE_DIVIDE(total_assists, total_minutes) * 90 AS assists_per_90,
        SAFE_DIVIDE(total_shots, total_minutes) * 90 AS shots_per_90,
        SAFE_DIVIDE(total_xg, total_minutes) * 90 AS xg_per_90,
        SAFE_DIVIDE(total_passes_attempted, total_minutes) * 90 AS passes_attempted_per_90,
        SAFE_DIVIDE(total_passes_completed, total_minutes) * 90 AS passes_completed_per_90,
        SAFE_DIVIDE(total_pressures, total_minutes) * 90 AS pressures_per_90,
        SAFE_DIVIDE(total_tackles, total_minutes) * 90 AS tackles_per_90,
        SAFE_DIVIDE(total_interceptions, total_minutes) * 90 AS interceptions_per_90,
        SAFE_DIVIDE(total_carries, total_minutes) * 90 AS carries_per_90,
        SAFE_DIVIDE(total_aerial_duels, total_minutes) * 90 AS aerial_duels_per_90,
        
        -- Calculated per-90 metrics for cluster mappings
        SAFE_DIVIDE(total_dribbles, total_minutes) * 90 AS dribbles_per_90,
        SAFE_DIVIDE(total_clearances, total_minutes) * 90 AS clearances_per_90,
        SAFE_DIVIDE(total_carries_att_third, total_minutes) * 90 AS carries_att_third_per_90,
        SAFE_DIVIDE(total_passes_att_third, total_minutes) * 90 AS passes_att_third_per_90,
        
        -- Seasonal efficiency metric
        SAFE_DIVIDE(total_passes_completed, total_passes_attempted) AS pass_completion_pct
    FROM aggregated
)

SELECT * FROM final