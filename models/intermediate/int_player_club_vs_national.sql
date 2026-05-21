{{ config(materialized='table') }}

WITH player_match_stats AS (
    SELECT * FROM {{ ref('int_player_match_stats') }}
),

matches AS (
    SELECT * FROM {{ ref('stg_statsbomb__matches') }}
),

player_match_with_meta AS (
    SELECT
        pms.*,
        m.competition_id,
        m.season_id,
        m.competition_name,
        m.season_name,
        m.is_international
    FROM player_match_stats pms
    INNER JOIN matches m ON pms.match_id = m.match_id
),

-- Aggregate by player + context (club vs national), apply 270-minute threshold
aggregated AS (
    SELECT
        player_id,
        player_name,
        is_international,
        SUM(minutes_played)        AS total_minutes,
        COUNT(DISTINCT match_id)   AS matches_played,
        SUM(goals)                 AS total_goals,
        SUM(assists)               AS total_assists,
        SUM(shots)                 AS total_shots,
        SUM(total_xg)              AS total_xg,
        SUM(passes_attempted)      AS total_passes_attempted,
        SUM(passes_completed)      AS total_passes_completed,
        SUM(pressures)             AS total_pressures,
        SUM(tackles)               AS total_tackles,
        SUM(interceptions)         AS total_interceptions,
        SUM(carries)               AS total_carries,
        SUM(aerial_duels)          AS total_aerial_duels
    FROM player_match_with_meta
    GROUP BY 1, 2, 3
    HAVING SUM(minutes_played) >= 270
),

-- Per-90 normalization
per90 AS (
    SELECT
        *,
        SAFE_DIVIDE(total_goals, total_minutes) * 90            AS goals_per_90,
        SAFE_DIVIDE(total_assists, total_minutes) * 90          AS assists_per_90,
        SAFE_DIVIDE(total_shots, total_minutes) * 90            AS shots_per_90,
        SAFE_DIVIDE(total_xg, total_minutes) * 90               AS xg_per_90,
        SAFE_DIVIDE(total_passes_attempted, total_minutes) * 90 AS passes_attempted_per_90,
        SAFE_DIVIDE(total_passes_completed, total_minutes) * 90 AS passes_completed_per_90,
        SAFE_DIVIDE(total_pressures, total_minutes) * 90        AS pressures_per_90,
        SAFE_DIVIDE(total_tackles, total_minutes) * 90          AS tackles_per_90,
        SAFE_DIVIDE(total_interceptions, total_minutes) * 90    AS interceptions_per_90,
        SAFE_DIVIDE(total_carries, total_minutes) * 90          AS carries_per_90,
        SAFE_DIVIDE(total_aerial_duels, total_minutes) * 90     AS aerial_duels_per_90,
        SAFE_DIVIDE(total_passes_completed, total_passes_attempted) AS pass_completion_pct
    FROM aggregated
),

-- Z-score each metric within context (club players compared to club players,
-- national players compared to national players)
z_scored AS (
    SELECT
        player_id,
        player_name,
        is_international,
        total_minutes,
        matches_played,

        -- raw per-90
        goals_per_90,
        assists_per_90,
        shots_per_90,
        xg_per_90,
        passes_attempted_per_90,
        pass_completion_pct,
        pressures_per_90,
        tackles_per_90,
        interceptions_per_90,
        carries_per_90,
        aerial_duels_per_90,

        -- z-scored per-90 (partitioned by context)
        SAFE_DIVIDE(
            goals_per_90 - AVG(goals_per_90) OVER (PARTITION BY is_international),
            NULLIF(STDDEV(goals_per_90) OVER (PARTITION BY is_international), 0)
        ) AS z_goals_per_90,

        SAFE_DIVIDE(
            xg_per_90 - AVG(xg_per_90) OVER (PARTITION BY is_international),
            NULLIF(STDDEV(xg_per_90) OVER (PARTITION BY is_international), 0)
        ) AS z_xg_per_90,

        SAFE_DIVIDE(
            shots_per_90 - AVG(shots_per_90) OVER (PARTITION BY is_international),
            NULLIF(STDDEV(shots_per_90) OVER (PARTITION BY is_international), 0)
        ) AS z_shots_per_90,

        SAFE_DIVIDE(
            passes_attempted_per_90 - AVG(passes_attempted_per_90) OVER (PARTITION BY is_international),
            NULLIF(STDDEV(passes_attempted_per_90) OVER (PARTITION BY is_international), 0)
        ) AS z_passes_attempted_per_90,

        SAFE_DIVIDE(
            pass_completion_pct - AVG(pass_completion_pct) OVER (PARTITION BY is_international),
            NULLIF(STDDEV(pass_completion_pct) OVER (PARTITION BY is_international), 0)
        ) AS z_pass_completion_pct,

        SAFE_DIVIDE(
            pressures_per_90 - AVG(pressures_per_90) OVER (PARTITION BY is_international),
            NULLIF(STDDEV(pressures_per_90) OVER (PARTITION BY is_international), 0)
        ) AS z_pressures_per_90,

        SAFE_DIVIDE(
            tackles_per_90 - AVG(tackles_per_90) OVER (PARTITION BY is_international),
            NULLIF(STDDEV(tackles_per_90) OVER (PARTITION BY is_international), 0)
        ) AS z_tackles_per_90,

        SAFE_DIVIDE(
            interceptions_per_90 - AVG(interceptions_per_90) OVER (PARTITION BY is_international),
            NULLIF(STDDEV(interceptions_per_90) OVER (PARTITION BY is_international), 0)
        ) AS z_interceptions_per_90,

        SAFE_DIVIDE(
            carries_per_90 - AVG(carries_per_90) OVER (PARTITION BY is_international),
            NULLIF(STDDEV(carries_per_90) OVER (PARTITION BY is_international), 0)
        ) AS z_carries_per_90,

        SAFE_DIVIDE(
            aerial_duels_per_90 - AVG(aerial_duels_per_90) OVER (PARTITION BY is_international),
            NULLIF(STDDEV(aerial_duels_per_90) OVER (PARTITION BY is_international), 0)
        ) AS z_aerial_duels_per_90

    FROM per90
),

-- Filter to only players who appear in BOTH contexts
dual_context AS (
    SELECT player_id
    FROM z_scored
    GROUP BY player_id
    HAVING COUNT(DISTINCT is_international) = 2
)

SELECT z.*
FROM z_scored z
INNER JOIN dual_context d ON z.player_id = d.player_id