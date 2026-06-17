{{ config(
    materialized='table'
) }}

WITH player_season_stats AS (
    SELECT * FROM {{ ref('int_player_season_stats') }}
),

cluster_assignments AS (
    SELECT 
        CAST(ca.player_id AS INT64)     AS player_id,
        CAST(cluster AS INT64)       AS cluster_id,
        CAST(archetype AS STRING)    AS cluster_label
    FROM {{ source('ml_models', 'cluster_assignments') }} ca
    -- Join to int_player_season_stats to get total_minutes for ordering
    INNER JOIN {{ ref('int_player_season_stats') }} pss
        ON ca.player_id = pss.player_id
        AND ca.competition_id = pss.competition_id
        AND ca.season_id = pss.season_id
    QUALIFY ROW_NUMBER() OVER (PARTITION BY ca.player_id ORDER BY pss.total_minutes DESC) = 1
),

pca_loadings AS (
    SELECT 
        CAST(component AS STRING) AS component,
        CAST(feature AS STRING)   AS feature,
        CAST(loading AS FLOAT64)  AS loading
    FROM {{ source('ml_models', 'pca_loadings') }}
),

unpivoted_features AS (
    SELECT 
        player_id, 
        competition_id, 
        season_id, 
        feature, 
        value
    FROM (
        SELECT 
            player_id, competition_id, season_id,
            CAST(xg_per_90 AS FLOAT64) AS xg_per_90,
            CAST(shots_per_90 AS FLOAT64) AS shots_per_90,
            CAST(passes_per_90 AS FLOAT64) AS passes_per_90,
            CAST(passes_att_third_per_90 AS FLOAT64) AS passes_att_third_per_90,
            CAST(pressures_per_90 AS FLOAT64) AS pressures_per_90,
            CAST(carries_per_90 AS FLOAT64) AS carries_per_90,
            CAST(dribbles_per_90 AS FLOAT64) AS dribbles_per_90,
            CAST(interceptions_per_90 AS FLOAT64) AS interceptions_per_90,
            CAST(blocks_per_90 AS FLOAT64) AS blocks_per_90,
            CAST(clearances_per_90 AS FLOAT64) AS clearances_per_90,
            CAST(duels_per_90 AS FLOAT64) AS duels_per_90,
            CAST(xg_per_shot AS FLOAT64) AS xg_per_shot,
            CAST(pass_completion_pct AS FLOAT64) AS pass_completion_pct
        FROM player_season_stats
    )
    UNPIVOT (
        value FOR feature IN (
            xg_per_90, shots_per_90, passes_per_90, passes_att_third_per_90,
            pressures_per_90, carries_per_90, dribbles_per_90, interceptions_per_90,
            blocks_per_90, clearances_per_90, duels_per_90, xg_per_shot, pass_completion_pct
        )
    )
),

standardized_features AS (
    SELECT
        player_id,
        competition_id,
        season_id,
        feature,
        -- PCA requires standardized features to prevent magnitude bias and extreme outliers
        SAFE_DIVIDE(
            value - AVG(value) OVER (PARTITION BY feature),
            NULLIF(STDDEV(value) OVER (PARTITION BY feature), 0)
        ) AS z_value
    FROM unpivoted_features
),

pca_scores AS (
    SELECT
        f.player_id,
        f.competition_id,
        f.season_id,
        -- Compute the dot product against component loadings
        SUM(CASE WHEN l.component = 'PC1' THEN f.z_value * l.loading ELSE 0 END) AS pc1,
        SUM(CASE WHEN l.component = 'PC2' THEN f.z_value * l.loading ELSE 0 END) AS pc2
    FROM standardized_features f
    INNER JOIN pca_loadings l 
        ON f.feature = l.feature
    GROUP BY 1, 2, 3
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
        pca.pc1,
        pca.pc2,

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
        ON p.player_id = c.player_id
    LEFT JOIN pca_scores pca
        ON p.player_id = pca.player_id
        AND p.competition_id = pca.competition_id
        AND p.season_id = pca.season_id
)

SELECT * FROM final_mart