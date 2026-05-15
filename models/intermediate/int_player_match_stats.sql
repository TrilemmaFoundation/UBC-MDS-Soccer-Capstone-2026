{{ config(materialized='table') }}

WITH events AS (
    SELECT * FROM {{ ref('stg_statsbomb__events') }}
),

lineups AS (
    -- Parse strings like '45:30' into float minutes for duration calculations
    SELECT 
        *,
        COALESCE(
            SAFE_CAST(SPLIT(from_time, ':')[OFFSET(0)] AS FLOAT64) 
            + SAFE_CAST(SPLIT(from_time, ':')[OFFSET(1)] AS FLOAT64) / 60, 
            0
        ) AS from_min,
        LEAST(COALESCE(
            SAFE_CAST(SPLIT(to_time, ':')[OFFSET(0)] AS FLOAT64) 
            + SAFE_CAST(SPLIT(to_time, ':')[OFFSET(1)] AS FLOAT64) / 60, 
            90
        ), 120) AS to_min
    FROM {{ ref('stg_statsbomb__lineups') }}
),

player_match_aggregates AS (
    SELECT
        match_id,
        player AS player_name,
        team AS team_name,
        -- Attacking
        COUNT(CASE WHEN event_type = 'Shot' THEN 1 END) AS shots,
        SUM(CASE WHEN event_type = 'Shot' THEN shot_statsbomb_xg ELSE 0 END) AS total_xg,
        COUNT(CASE WHEN event_type = 'Shot' AND pass_outcome IS NULL THEN 1 END) AS goals,
        
        -- Passing & Playmaking
        COUNT(CASE WHEN event_type = 'Pass' THEN 1 END) AS passes_attempted,
        COUNT(CASE WHEN event_type = 'Pass' AND pass_outcome IS NULL THEN 1 END) AS passes_completed,
        -- Assists and SCA would typically involve looking at event sequences or specific tags
        COUNT(CASE WHEN event_type = 'Pass' AND pass_outcome = 'Assist' THEN 1 END) AS assists,
        
        -- Defensive & Physical
        COUNT(CASE WHEN event_type = 'Pressure' THEN 1 END) AS pressures,
        COUNT(CASE WHEN event_type = 'Tackle' THEN 1 END) AS tackles,
        COUNT(CASE WHEN event_type = 'Interception' THEN 1 END) AS interceptions,
        COUNT(CASE WHEN event_type = 'Carry' THEN 1 END) AS carries,
        COUNT(CASE WHEN event_type = 'Duel' AND play_pattern = 'Aerial' THEN 1 END) AS aerial_duels

    FROM events
    WHERE player IS NOT NULL
    GROUP BY 1, 2, 3
),

final AS (
    SELECT
        l.match_id,
        l.player_id,
        l.player_name,
        l.team_name,
        l.position_name,
        -- Minutes Calculation
        (l.to_min - l.from_min) AS minutes_played,
        -- Event Metrics
        COALESCE(pma.shots, 0) AS shots,
        COALESCE(pma.total_xg, 0) AS total_xg,
        COALESCE(pma.goals, 0) AS goals,
        COALESCE(pma.assists, 0) AS assists,
        COALESCE(pma.passes_attempted, 0) AS passes_attempted,
        COALESCE(pma.passes_completed, 0) AS passes_completed,
        SAFE_DIVIDE(pma.passes_completed, pma.passes_attempted) AS pass_completion_pct,
        COALESCE(pma.pressures, 0) AS pressures,
        COALESCE(pma.tackles, 0) AS tackles,
        COALESCE(pma.interceptions, 0) AS interceptions,
        COALESCE(pma.carries, 0) AS carries,
        COALESCE(pma.aerial_duels, 0) AS aerial_duels
    FROM lineups l
    LEFT JOIN player_match_aggregates pma 
        ON l.match_id = pma.match_id 
        AND l.player_name = pma.player_name
)

SELECT * FROM final