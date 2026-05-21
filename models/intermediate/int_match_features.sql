{{ config(materialized='table') }}

WITH matches AS (
    SELECT 
        match_id,
        match_date,
        CAST(competition_id AS INT64) AS competition_id,
        competition_name,
        season_name,
        home_team,
        away_team,
        match_result
    FROM {{ ref('stg_statsbomb__matches') }}
),

rolling_form AS (
    SELECT * FROM {{ ref('int_team_rolling_form') }}
),

-- Calculate historical Head-to-Head (H2H) win percentage for the home team
h2h_history AS (
    SELECT
        m1.match_id,
        m1.home_team,
        m1.away_team,
        m1.match_date,
        -- Count home team wins in previous encounters (any venue)
        COUNT(CASE 
            WHEN (m2.home_team = m1.home_team AND m2.away_team = m1.away_team AND m2.match_result = 'home_win')
              OR (m2.home_team = m1.away_team AND m2.away_team = m1.home_team AND m2.match_result = 'away_win')
            THEN 1 
        END) OVER (
            PARTITION BY m1.home_team, m1.away_team 
            ORDER BY m1.match_date 
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS h2h_home_wins,
        
        COUNT(m2.match_id) OVER (
            PARTITION BY m1.home_team, m1.away_team 
            ORDER BY m1.match_date 
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS h2h_total_matches
    FROM matches m1
    LEFT JOIN matches m2 
        ON ((m1.home_team = m2.home_team AND m1.away_team = m2.away_team) 
         OR (m1.home_team = m2.away_team AND m1.away_team = m2.home_team))
        AND m2.match_date < m1.match_date
),

final AS (
    SELECT
        m.match_id,
        m.match_date,
        m.competition_id,
        m.competition_name,
        m.season_name,
        m.home_team,
        m.away_team,
        
        -- Target Variable for ML
        m.match_result,

        -- Home Team Rolling Features (Filtered strictly to side = 'home' to block fan-out)
        h_form.rolling_avg_xg AS home_rolling_xg,
        h_form.rolling_avg_points AS home_rolling_points,
        h_form.rolling_avg_possession_pct AS home_rolling_possession,
        h_form.rolling_avg_pressures AS home_rolling_pressures,
        h_form.rolling_avg_pass_completion_pct AS home_rolling_pass_accuracy,

        -- Away Team Rolling Features (Filtered strictly to side = 'away' to block fan-out)
        a_form.rolling_avg_xg AS away_rolling_xg,
        a_form.rolling_avg_points AS away_rolling_points,
        a_form.rolling_avg_possession_pct AS away_rolling_possession,
        a_form.rolling_avg_pressures AS away_rolling_pressures,
        a_form.rolling_avg_pass_completion_pct AS away_rolling_pass_accuracy,

        -- Head-to-Head Feature
        SAFE_DIVIDE(h2h.h2h_home_wins, h2h.h2h_total_matches) AS h2h_home_win_pct

    FROM matches m
    -- Join home team form and isolate to home side
    INNER JOIN rolling_form h_form 
        ON m.match_id = h_form.match_id 
        AND m.home_team = h_form.team
        AND h_form.side = 'home'
    -- Join away team form and isolate to away side
    INNER JOIN rolling_form a_form 
        ON m.match_id = a_form.match_id 
        AND m.away_team = a_form.team
        AND a_form.side = 'away'
    -- Join H2H stats
    LEFT JOIN h2h_history h2h
        ON m.match_id = h2h.match_id
)

SELECT * FROM final