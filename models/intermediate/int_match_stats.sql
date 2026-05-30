{{ config(materialized='table') }}

WITH events AS (
    SELECT * FROM {{ ref('stg_statsbomb__events') }}
),

matches AS (
    SELECT * FROM {{ ref('stg_statsbomb__matches') }}
),

-- 1. Aggregate core event metrics by match and team
team_match_aggregates AS (
    SELECT
        match_id,
        team,
        COUNT(CASE WHEN event_type = 'Shot' THEN 1 END) AS total_shots,
        SUM(CASE WHEN event_type = 'Shot' THEN shot_statsbomb_xg ELSE 0 END) AS total_xg,
        COUNT(CASE WHEN event_type = 'Pass' THEN 1 END) AS passes_attempted,
        -- StatsBomb success is typically null in pass_outcome
        COUNT(CASE WHEN event_type = 'Pass' AND pass_outcome IS NULL THEN 1 END) AS passes_completed,
        COUNT(CASE WHEN event_type = 'Pressure' THEN 1 END) AS total_pressures,
        COUNT(CASE WHEN event_type = 'Carry' THEN 1 END) AS total_carries
    FROM events
    GROUP BY 1, 2
),

-- 2. Calculate match-level total passes for the possession proxy
match_totals AS (
    SELECT
        match_id,
        SUM(passes_attempted) AS match_total_passes
    FROM team_match_aggregates
    GROUP BY 1
),

-- 3. Final join to integrate match metadata and calculate derived shares
final AS (
    SELECT
        m.match_id,
        m.match_date,
        m.competition_id,
        m.competition_name,
        m.season_id,
        m.season_name,
        m.home_team,
        m.away_team,
        tma.team,
        -- Identify if the team is home or away for separate analysis
        CASE 
            WHEN tma.team = m.home_team THEN 'home' 
            ELSE 'away' 
        END AS side,
        tma.total_shots,
        tma.total_xg,
        tma.passes_attempted,
        tma.passes_completed,
        SAFE_DIVIDE(tma.passes_completed, tma.passes_attempted) AS pass_completion_pct,
        tma.total_pressures,
        tma.total_carries,
        -- Possession proxy: team passes as % of total match passes
        SAFE_DIVIDE(tma.passes_attempted, mt.match_total_passes) AS possession_share
    FROM team_match_aggregates tma
    INNER JOIN matches m ON tma.match_id = m.match_id
    INNER JOIN match_totals mt ON tma.match_id = mt.match_id
    -- Default scope: male competitions only (filter women's at intermediate, not staging)
    WHERE m.gender = 'male'
)

SELECT * FROM final