{{ config(
    materialized='table'
) }}

WITH player_season_stats AS (
    SELECT * FROM {{ ref('int_player_season_stats') }}
),

cluster_assignments AS (
    -- Reference your pre-created BigQuery analytics table source cleanly
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

        -- PCA Coordinates (Placeholders for 2D scatter plots)
        CAST(NULL AS FLOAT64) AS pc1,
        CAST(NULL AS FLOAT64) AS pc2,

        -- Per-90 Performance Metrics (For Heatmaps)
        p.goals_per_90,
        p.assists_per_90,
        p.shots_per_90,
        p.xg_per_90,
        p.passes_attempted_per_90,
        p.passes_completed_per_90,
        p.pass_completion_pct,
        p.pressures_per_90,
        p.tackles_per_90,
        p.interceptions_per_90,
        p.carries_per_90,
        p.aerial_duels_per_90

    FROM player_season_stats p
    LEFT JOIN cluster_assignments c
        ON p.player_id = c.player_id
)

SELECT * FROM final_mart