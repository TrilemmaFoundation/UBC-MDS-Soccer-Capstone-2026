{{ config(materialized='table') }}

WITH match_stats AS (
    -- Get team-level stats from the intermediate match stats model
    SELECT * FROM {{ ref('int_match_stats') }}
),

matches AS (
    -- Get match results to calculate points for form
    SELECT 
        match_id, 
        match_result 
    FROM {{ ref('stg_statsbomb__matches') }}
),

match_results AS (
    SELECT
        ms.*,
        -- Calculate points for each specific team in the match
        CASE
            WHEN ms.side = 'home' AND m.match_result = 'home_win' THEN 3
            WHEN ms.side = 'away' AND m.match_result = 'away_win' THEN 3
            WHEN m.match_result = 'draw' THEN 1
            ELSE 0
        END AS points_earned,
        -- Calculate goals for the team (StatsBomb successes in shots are usually goals)
        -- This logic aligns with your int_match_stats.sql event counting
        ms.total_shots
    FROM match_stats ms
    INNER JOIN matches m ON ms.match_id = m.match_id
),

rolling_metrics AS (
    SELECT
        match_id,
        match_date,
        team,
        side,
        -- Window function: 5-match rolling averages partitioned by team
        AVG(total_xg) OVER (
            PARTITION BY team 
            ORDER BY match_date 
            ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
        ) AS rolling_avg_xg,
        
        -- Rolling points (Form)
        AVG(points_earned) OVER (
            PARTITION BY team 
            ORDER BY match_date 
            ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
        ) AS rolling_avg_points,

        -- Rolling possession share
        AVG(possession_share) OVER (
            PARTITION BY team 
            ORDER BY match_date 
            ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
        ) AS rolling_avg_possession_pct,

        -- Rolling pressure intensity
        AVG(total_pressures) OVER (
            PARTITION BY team 
            ORDER BY match_date 
            ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
        ) AS rolling_avg_pressures,

        -- Rolling passing accuracy
        AVG(pass_completion_pct) OVER (
            PARTITION BY team 
            ORDER BY match_date 
            ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
        ) AS rolling_avg_pass_completion_pct

    FROM match_results
)

SELECT * FROM rolling_metrics