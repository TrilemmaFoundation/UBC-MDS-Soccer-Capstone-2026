{{ config(materialized='table') }}

WITH player_match_stats AS (
    SELECT * FROM {{ ref('int_player_match_stats') }}
),

matches AS (
    SELECT * FROM {{ ref('stg_statsbomb__matches') }}
),

-- Join match metadata to player stats to get competition and season IDs
-- Default scope: male competitions only (filter women's at intermediate, not staging)
player_match_with_meta AS (
    SELECT
        pms.*,
        m.competition_id,
        m.season_id,
        m.competition_name,
        m.season_name
    FROM player_match_stats pms
    INNER JOIN matches m ON pms.match_id = m.match_id
    WHERE m.gender = 'male'
),

-- Aggregate to the season level and apply the 270-minute threshold
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
        SUM(duels) AS total_duels,
        SUM(aerial_duels) AS total_aerial_duels,
        
        -- Tracking metrics totals
        SUM(dribbles) AS total_dribbles,
        SUM(clearances) AS total_clearances,
        SUM(carries_att_third) AS total_carries_att_third,
        SUM(passes_att_third) AS total_passes_att_third,

        -- Consistency metrics totals
        SUM(blocks) AS total_blocks,
        SUM(ball_recoveries) AS total_ball_recoveries,
        SUM(fouls) AS total_fouls
    FROM player_match_with_meta
    GROUP BY 1, 2, 3, 4, 5, 6
    HAVING SUM(minutes_played) >= 270
),

final AS (
    SELECT
        player_id,
        player_name,
        competition_id,
        competition_name,
        season_id,
        season_name,
        total_minutes,
        total_goals,
        total_assists,
        total_shots,
        total_xg,
        total_passes_attempted,
        total_passes_completed,
        total_pressures,
        total_tackles,
        total_interceptions,
        total_carries,
        total_duels,
        total_aerial_duels,
        
        -- Efficiency metrics
        SAFE_DIVIDE(total_passes_completed, total_passes_attempted) AS pass_completion_pct,
        COALESCE(SAFE_DIVIDE(total_xg, total_shots), 0.0) AS xg_per_shot,

        -- Clustering pipeline features aligned to _per_90
        SAFE_DIVIDE(total_dribbles, total_minutes) * 90 AS dribbles_per_90,
        SAFE_DIVIDE(total_carries_att_third, total_minutes) * 90 AS carries_att_third_per_90,
        SAFE_DIVIDE(total_clearances, total_minutes) * 90 AS clearances_per_90,
        SAFE_DIVIDE(total_passes_att_third, total_minutes) * 90 AS passes_att_third_per_90,

        -- Consistency score model features aligned to _per_90
        SAFE_DIVIDE(total_blocks, total_minutes) * 90 AS blocks_per_90,
        SAFE_DIVIDE(total_ball_recoveries, total_minutes) * 90 AS ball_recoveries_per_90,
        SAFE_DIVIDE(total_fouls, total_minutes) * 90 AS fouls_per_90,
        SAFE_DIVIDE(total_duels, total_minutes) * 90 AS duels_per_90,

        -- Standard Per-90 View Metrics
        SAFE_DIVIDE(total_passes_attempted, total_minutes) * 90 AS passes_per_90,
        SAFE_DIVIDE(total_shots, total_minutes) * 90 AS shots_per_90,
        SAFE_DIVIDE(total_xg, total_minutes) * 90 AS xg_per_90,
        SAFE_DIVIDE(total_goals, total_minutes) * 90 AS goals_per_90,
        SAFE_DIVIDE(total_assists, total_minutes) * 90 AS assists_per_90,
        SAFE_DIVIDE(total_pressures, total_minutes) * 90 AS pressures_per_90,
        SAFE_DIVIDE(total_interceptions, total_minutes) * 90 AS interceptions_per_90,
        SAFE_DIVIDE(total_tackles, total_minutes) * 90 AS tackles_per_90,
        SAFE_DIVIDE(total_aerial_duels, total_minutes) * 90 AS aerial_duels_per_90,
        SAFE_DIVIDE(total_carries, total_minutes) * 90 AS carries_per_90
    FROM aggregated
)

SELECT * FROM final