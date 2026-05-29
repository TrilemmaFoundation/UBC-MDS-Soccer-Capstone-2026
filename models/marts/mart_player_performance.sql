{{ config(
    materialized='table'
) }}

WITH player_season_stats AS (
    SELECT * FROM {{ ref('int_player_season_stats') }}
),

cluster_assignments AS (
    SELECT 
        CAST(ca.player_id AS INT64)     AS player_id,
        CAST(ca.cluster AS INT64)       AS cluster_id,
        CAST(ca.archetype AS STRING)    AS cluster_label
    FROM {{ source('ml_models', 'cluster_assignments') }} ca
    INNER JOIN {{ ref('int_player_season_stats') }} pss
        ON ca.player_id = pss.player_id
        AND ca.competition_id = pss.competition_id
        AND ca.season_id = pss.season_id
    QUALIFY ROW_NUMBER() OVER (PARTITION BY ca.player_id ORDER BY pss.total_minutes DESC) = 1
),

consistency_scores AS (
    SELECT 
        CAST(player_id AS INT64)                    AS player_id,
        CAST(club_performance_score AS FLOAT64)     AS club_performance_score,
        CAST(national_performance_score AS FLOAT64) AS national_performance_score,
        CAST(consistency_score AS FLOAT64)          AS consistency_score,
        CAST(performance_quadrant AS STRING)        AS performance_quadrant
    FROM {{ source('ml_models', 'consistency_scores') }}
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

        -- Consistency Metrics (from Rabin's ML pipeline)
        cs.club_performance_score,
        cs.national_performance_score,
        cs.consistency_score,
        cs.performance_quadrant

    FROM player_season_stats p
    LEFT JOIN cluster_assignments c
        ON p.player_id = c.player_id
    LEFT JOIN consistency_scores cs
        ON p.player_id = cs.player_id
)

SELECT * FROM joined