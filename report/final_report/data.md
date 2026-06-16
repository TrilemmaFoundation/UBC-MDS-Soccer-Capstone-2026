# Source

All data in this project comes from the StatsBomb open dataset, accessed via the `statsbombpy` Python library [@statsbomb2024]. Like other public spatio-temporal event repositories [@pappalardo2019], StatsBomb collects match event data by manually tracking every on-ball action in a match, assigning it a type, timestamp, location (x, y coordinates on a 120 × 80 pitch grid), and a rich set of type-specific attributes. Our per-90 feature set follows the action-based profiling tradition in football analytics [@decroos2019]. The open tier covers 16 competitions spanning men's senior football across Europe, South America, North America, and international tournaments.

# Dataset Structure

Three tables are ingested from the API (\autoref{tbl-data-overview}):

| Table | Grain | Scale |
|-------|-------|-------|
| `matches` | One row per match | 3,464 matches |
| `events` | One row per on-ball action | ~12.2 million rows |
| `lineups` | One row per player appearance | 165,820 rows |

: Overview of ingested StatsBomb tables. {#tbl-data-overview}

The `events` table is the analytical backbone. Action types are dominated by Pass (~3.4M), Ball Receipt (~3.2M), Carry (~2.6M), and Pressure (~1.1M). There are 88,023 Shot events with non-null StatsBomb xG values (mean xG per shot: 0.107). The dataset covers 10,808 distinct players across 308 teams. Primary model outputs are **cluster labels** (RQ1), **performance quadrants**, and **consistency scores** (RQ2). Player-level modelling is limited to **men's senior** competitions, which bounded project scope.

# Data Quality and Limitations

Several quality issues and constraints shaped the project:

- **Missing lineup times.** Substitution `to_time` is missing for 110,917 lineup rows, corresponding to starters who played the full match and bench players who never appeared. Minutes played are inferred as 90 (or 120 for extra time) when the field is null.
- **Missing positions.** `position_name` is absent for 34,179 lineup rows, consistent with bench entries with unconfirmed roles. These rows are excluded from per-position analyses.
- **Uneven competition coverage.** La Liga contributes 868 matches with complete seasonal coverage. The UEFA Champions League has scattered single-match history. Analysts should treat early-season or low-coverage competitions as smaller sub-samples.
- **Open data scope.** The free tier does not include all competitions or all seasons available in the paid StatsBomb API. Coverage is curated by StatsBomb and may change with new releases.

# How Data Shaped Design Decisions

The minimum 270-minute playing time threshold (equivalent to three full matches) was introduced to address the instability of per-90 rates for players with very few appearances. Below this threshold, a single exceptional match can dominate a player-season's metrics and produce unrepresentative rate statistics. This threshold is applied consistently across all intermediate dbt models, the clustering pipeline, and the consistency scoring pipeline. The choice of 270 minutes was validated against the distribution of player-season minute totals: it retains the majority of regular contributors while removing statistical noise from small samples.

The nested JSON structure of the `events` table required flattening at ingestion time. Columns containing dictionary objects are normalized using `pd.json_normalize` before writing to Parquet, and all object-type columns are cast to strings to ensure compatibility with the Apache Arrow schema expected by BigQuery.
