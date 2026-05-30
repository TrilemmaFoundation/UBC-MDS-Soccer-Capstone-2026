{{ config(
    materialized='table'
) }}

WITH player_season_stats AS (
    SELECT * FROM {{ ref('int_player_season_stats') }}
),

cluster_assignments AS (
    SELECT
        CAST(player_id AS INT64)      AS player_id,
        CAST(competition_id AS INT64) AS competition_id,
        CAST(season_id AS INT64)      AS season_id,
        CAST(cluster AS INT64)        AS cluster_id,
        CAST(archetype AS STRING)     AS cluster_label,
        CAST(pc1 AS FLOAT64)          AS pc1,
        CAST(pc2 AS FLOAT64)          AS pc2
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
        COALESCE(c.cluster_id, -1)           AS cluster_id,
        COALESCE(c.cluster_label, 'Unknown') AS cluster_label,

        -- PCA Coordinates (from cluster.py output)
        c.pc1,
        c.pc2,

        -- All 13 PCA clustering features (aligned to Li's pca_loadings.parquet)
        p.xg_per_90,
        p.shots_per_90,
        p.passes_per_90,
        p.passes_att_third_per_90,
        p.pressures_per_90,
        p.carries_per_90,
        p.dribbles_per_90,
        p.interceptions_per_90,
        p.blocks_per_90,
        p.clearances_per_90,
        p.duels_per_90,
        p.xg_per_shot,
        p.pass_completion_pct,

        -- Supplementary Traditional Metrics
        p.goals_per_90,
        p.assists_per_90

    FROM player_season_stats p
    LEFT JOIN cluster_assignments c
        ON  p.player_id      = c.player_id
        AND p.competition_id = c.competition_id
        AND p.season_id      = c.season_id
)

SELECT * FROM final_mart