# app/chatbot/table_schema.py
import os

_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")

# Ensure this name is exactly TABLE_CONTEXT
TABLE_CONTEXT = f"""
You are querying the '{_PROJECT_ID}' BigQuery project under the 'dbt_marts' dataset.
Always use the full path: `{_PROJECT_ID}.dbt_marts.table_name` when writing SQL.

IMPORTANT GRAIN RULE: All player tables have one row per (player, competition, season). The same player will appear multiple times across different seasons or competitions.
- When ranking or comparing players by a per-90 rate (xg_per_90, shots_per_90, passes_per_90, etc.), ALWAYS use mart_player_performance and compute a minutes-weighted rate from raw totals to avoid inflation from short high-intensity seasons. Example for xG: SELECT player_name, SUM(total_xg) / NULLIF(SUM(total_minutes), 0) * 90 AS xg_per_90 FROM `{_PROJECT_ID}.dbt_marts.mart_player_performance` WHERE cluster_label = 'Creative Winger' GROUP BY player_name ORDER BY xg_per_90 DESC LIMIT 5
- For counting stats (total_goals, total_interceptions, etc.) use SUM() with GROUP BY player_name on mart_player_performance.
- Only skip GROUP BY when the user explicitly asks for a specific season or competition.

Available BigQuery Tables:

1. `{_PROJECT_ID}.dbt_marts.mart_match_analysis`
   - Description: Comprehensive match-level analytics, scores, and team metrics. Main source for match overview dashboards.
   - Core Columns:
     * `match_id` (INT64) - Unique match identifier
     * `match_date` (DATE) - The date played (Partition Key)
     * `competition_id` (INT64) - Competition identifier (Cluster Key)
     * `competition_name` (STRING) - e.g., 'La Liga', 'World Cup'
     * `season_id` (INT64) - Unique identifier for the specific season
     * `season_name` (STRING) - Name or year designation of the season
     * `home_team` (STRING), `away_team` (STRING)
     * `home_score` (INT64), `away_score` (INT64)
     * `match_result` (STRING) - Outcomes relative to venue: 'home_win', 'away_win', or 'draw'
     * `home_xg` (FLOAT64), `away_xg` (FLOAT64) - Expected Goals
     * `home_possession_proxy` (FLOAT64), `away_possession_proxy` (FLOAT64) - Possession shares derived from pass volumes
     * `home_pass_completion_pct` (FLOAT64), `away_pass_completion_pct` (FLOAT64)
     * `home_shots` (INT64), `away_shots` (INT64)
     * `home_total_pressures` (INT64), `away_total_pressures` (INT64)
     * `home_total_carries` (INT64), `away_total_carries` (INT64)

2. `{_PROJECT_ID}.dbt_marts.mart_player_clusters`
   - Description: Player seasonal profiles paired with machine learning K-Means cluster archetypes. Filtered for players with >= 270 minutes.
   - Core Columns:
     * `player_id` (INT64), `player_name` (STRING)
     * `competition_id` (INT64), `competition_name` (STRING)
     * `season_id` (INT64), `season_name` (STRING)
     * `total_minutes` (FLOAT64) - Total minutes played in the season
     * `cluster_id` (INT64) - Cluster index (Defaults to -1 if unassigned)
     * `cluster_label` (STRING) - Archetypes: 'Goalkeeper', 'Low Activity', 'Creative Winger', 'Creative Playmaker', 'Defensive Anchor', 'Pressing Forward', 'Unknown'
     * `pc1` (FLOAT64), `pc2` (FLOAT64) - Principal component dimensions for 2D visualization scatter plots
     * PCA Input Metrics (per-90): `xg_per_90`, `shots_per_90`, `passes_per_90`, `passes_att_third_per_90`, `pressures_per_90`, `carries_per_90`, `dribbles_per_90`, `interceptions_per_90`, `blocks_per_90`, `clearances_per_90`, `duels_per_90`, `xg_per_shot`, `pass_completion_pct`
     * Traditional Rates: `goals_per_90`, `assists_per_90`
     * NOTE: This table does NOT have `performance_quadrant` or `consistency_score`. Use mart_player_performance for those.

3. `{_PROJECT_ID}.dbt_marts.mart_player_performance`
   - Description: Deep player seasonal analytics totals combined with tactical labels and normalized Per-90 metrics.
   - Core Columns:
     * Metadata & Archetypes: `player_id`, `player_name`, `competition_id`, `competition_name`, `season_id`, `season_name`, `total_minutes`, `cluster_id`, `cluster_label`
     * Absolute Cumulative Totals: `total_goals`, `total_assists`, `total_shots`, `total_xg`, `total_passes_attempted`, `total_passes_completed`, `pass_completion_pct`, `total_pressures`, `total_tackles`, `total_interceptions`, `total_carries`, `total_duels`, `total_aerial_duels`
     * Per-90 Normalized Metrics: `goals_per_90`, `assists_per_90`, `shots_per_90`, `xg_per_90`, `xg_per_shot`, `pressures_per_90`, `tackles_per_90`, `interceptions_per_90`, `carries_per_90`, `duels_per_90`, `aerial_duels_per_90`
     * Consistency Metrics (populated — query directly): consistency_score (FLOAT64, higher = more consistent between club and international; range 0–1), club_performance_score (FLOAT64), national_performance_score (FLOAT64), performance_quadrant (STRING: 'Elite', 'Club Specialist', 'International Specialist', 'Underperformer'). Example: SELECT player_name, AVG(consistency_score) FROM mart_player_performance WHERE consistency_score IS NOT NULL GROUP BY player_name ORDER BY consistency_score DESC LIMIT 10

4. `{_PROJECT_ID}.dbt_marts.mart_team_comparison`
   - Description: Team seasonal baseline statistics joined with short-term 5-match rolling tactical form. Filtered for campaigns with >= 10 matches.
   - Core Columns:
     * Identifiers & Metadata: `team` (STRING), `competition_id` (INT64), `competition_name` (STRING), `season_id` (INT64), `season_name` (STRING), `matches_played` (INT64)
     * Seasonal Baseline Metrics: `wins`, `draws`, `losses`, `total_points`, `seasonal_total_xg`, `seasonal_avg_xg`, `seasonal_avg_possession`, `seasonal_total_pressures`, `seasonal_avg_pressures`
     * Latest Rolling Form (5-Match Momentum): `latest_rolling_xg`, `latest_rolling_points`, `latest_rolling_possession`, `latest_rolling_pressures`, `latest_rolling_pass_accuracy`

5. `{_PROJECT_ID}.dbt_marts.mart_match_prediction_features`
   - Description: Flattened feature matrix explicitly structured for XGBoost machine learning model training, evaluation, and inference scoring.
   - Note: This table is not yet fully populated. Avoid querying specific feature columns until confirmed available.
   - Core Columns:
     * Identifiers & Targets: `match_id` (INT64), `match_date` (DATE), `competition_id` (INT64), `competition_name` (STRING), `season_name` (STRING), `home_team` (STRING), `away_team` (STRING), `match_result` (STRING)
     * Home Team 5-Match Rolling Features: `home_rolling_xg`, `home_rolling_points`, `home_rolling_possession`, `home_rolling_pressures`, `home_rolling_pass_accuracy`
     * Away Team 5-Match Rolling Features: `away_rolling_xg`, `away_rolling_points`, `away_rolling_possession`, `away_rolling_pressures`, `away_rolling_pass_accuracy`
     * Head-to-Head Analytics: `h2h_home_win_pct`
"""
