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

final_mart AS (
    SELECT
        p.player_id,
        p.player_name,
        p.competition_id,
        p.competition_name,
        p.season_id,
        p.season_name,
        p.total_minutes,

        -- Tactical Cluster Properties
        COALESCE(c.cluster_id, -1)          AS cluster_id,
        COALESCE(c.cluster_label, 'Unknown') AS cluster_label,

        -- PCA Coordinates (Placeholders for cluster.py coordinate exports)
        CAST(NULL AS FLOAT64) AS pc1,
        CAST(NULL AS FLOAT64) AS pc2,

        -- All 11 Clustering features exposed for radar charts / heatmaps
        p.shots_per_90,
        p.xg_per_90,
        p.xg_per_shot,
        p.dribbles_per_90,
        p.carries_att_third_per_90,
        p.passes_att_third_per_90,
        p.pass_completion_pct,
        p.pressures_per_90,
        p.interceptions_per_90,
        p.clearances_per_90,
        p.duels_per_90,

        -- Supplementary Traditional Metrics
        p.goals_per_90,
        p.assists_per_90

    FROM player_season_stats p
    LEFT JOIN cluster_assignments c
        ON p.player_id = c.player_id
)

SELECT * FROM final_mart