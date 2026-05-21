{{ config(materialized='table') }}

WITH match_stats AS (
    SELECT * FROM {{ ref('int_match_stats') }}
),

matches AS (
    SELECT * FROM {{ ref('stg_statsbomb__matches') }}
),

-- Combine match-level stats with match metadata to determine win/loss/draw
match_results AS (
    SELECT
        ms.*,
        CASE
            WHEN ms.side = 'home' AND m.match_result = 'home_win' THEN 'win'
            WHEN ms.side = 'away' AND m.match_result = 'away_win' THEN 'win'
            WHEN m.match_result = 'draw' THEN 'draw'
            ELSE 'loss'
        END AS result
    FROM match_stats ms
    INNER JOIN matches m ON ms.match_id = m.match_id
),

-- Aggregate to team-season level and apply the 10-match minimum filter
final AS (
    SELECT
        team,
        competition_id,
        competition_name,
        season_id,
        season_name,
        COUNT(match_id) AS matches_played,
        
        -- Points and Results
        COUNT(CASE WHEN result = 'win' THEN 1 END) AS wins,
        COUNT(CASE WHEN result = 'draw' THEN 1 END) AS draws,
        COUNT(CASE WHEN result = 'loss' THEN 1 END) AS losses,
        SUM(CASE 
            WHEN result = 'win' THEN 3 
            WHEN result = 'draw' THEN 1 
            ELSE 0 
        END) AS total_points,
        
        -- Performance Metrics
        SUM(total_xg) AS total_xg,
        AVG(total_xg) AS avg_xg_per_match,
        AVG(possession_share) AS avg_possession_share,
        SUM(total_pressures) AS total_pressures,
        AVG(total_pressures) AS avg_pressures_per_match
    FROM match_results
    GROUP BY 1, 2, 3, 4, 5
    HAVING COUNT(match_id) >= 10
)

SELECT * FROM final