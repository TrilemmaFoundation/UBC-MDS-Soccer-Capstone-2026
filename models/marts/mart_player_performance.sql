{{ config(
    materialized='table'
) }}

WITH player_season_stats AS (
    SELECT * FROM {{ ref('int_player_season_stats') }}
),

cluster_assignments AS (
    SELECT 
        CAST(player_id AS INT64)     AS player_id,
        CAST(cluster AS INT64)       AS cluster_id,
        CAST(archetype AS STRING)    AS cluster_label
    FROM {{ source('ml_models', 'cluster_assignments') }}
),

joined AS (
    SELECT
        -- Player & Season Metadata
        p.player_id,
        p.player_name,
        p.competition_id,
        p.competition_name,
        p.season_id,
        p.season_name,
        p.total_minutes,
        
        -- Cluster Assignments mapped from the ML table
        COALESCE(c.cluster_id, -1)          AS cluster_id,
        COALESCE(c.cluster_label, 'Unknown') AS cluster_label,

        -- Core Raw Totals
        p.total_goals,
        p.total_assists,
        p.total_shots,
        p.total_xg,
        p.total_passes_attempted,
        p.total_passes_completed,
        p.pass_completion_pct,
        p.total_pressures,
        p.total_tackles,
        p.total_interceptions,
        p.total_carries,
        p.total_duels,
        p.total_aerial_duels,

        -- Performance Metrics (Notebook Aligned)
        p.goals_per_90,
        p.assists_per_90,
        p.shots_per_90,
        p.xg_per_90,
        p.xg_per_shot,
        p.pressures_per_90,
        p.tackles_per_90,
        p.interceptions_per_90,
        p.carries_per_90,
        p.duels_per_90,
        p.aerial_duels_per_90,

        -- PLACEHOLDERS: Waiting for Rabin's formula to calculate these fields
        CAST(NULL AS FLOAT64) AS club_performance_score,
        CAST(NULL AS FLOAT64) AS national_performance_score,
        CAST(NULL AS FLOAT64) AS consistency_score,
        CAST(NULL AS STRING)  AS performance_quadrant

    FROM player_season_stats p
    LEFT JOIN cluster_assignments c
        ON p.player_id = c.player_id
)

SELECT * FROM joined