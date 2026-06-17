# Club vs national consistency scoring

Partner guide for `src/ml/consistency.py`, the dbt model `int_player_club_vs_national`, and the BigQuery table `analytics.consistency_scores`.

Related docs:

- [Analysis notebooks](./notebooks.md) (Databricks)
- [Dashboard formulas](./appendix/consistency-explorer.md)
- [Final report appendix](../report/final_report.qmd) (data dictionary)

---

## What problem this solves

Many players appear for both a **club** and a **national team**. This pipeline asks two separate questions:

1. **Performance by context:** Compared to other players in the same setting, does the player rank higher at club or for their country?
2. **Profile consistency:** Do their per-90 playing-style metrics look similar in both settings, after standardizing within each context?

Answers feed the Looker **Consistency Explorer**, `mart_player_performance`, and the Django chatbot.

---

## Pipeline overview

```text
dbt run (intermediate)  →  int_player_club_vs_national  (2 rows per dual-context player)
        ↓
python src/ml/cluster.py  →  analytics.pca_loadings  (required for feature weights)
        ↓
python src/ml/consistency.py  →  analytics.consistency_scores
        ↓
dbt run (marts)  →  mart_player_performance
```

**Run order matters.** `consistency.py` reads `analytics.pca_loadings`, which is created by `cluster.py`. If loadings are missing or stale, consistency scoring will fail or use wrong weights.

Dagster runs this order automatically: `cluster_assignments` → `consistency_score` → `dbt_mart_refresh` (see `src/dagster/assets/ml_assets.py`).

---

## Source table: `int_player_club_vs_national`

**Location:** `{GCP_PROJECT}.dbt_intermediate.int_player_club_vs_national`  
**SQL:** `models/intermediate/int_player_club_vs_national.sql`

### Grain

One row per **player** per **context**:

| Column | Meaning |
|--------|---------|
| `player_id`, `player_name` | Player identity |
| `is_international` | `false` = club matches, `true` = national team matches |
| `total_minutes` | Minutes in that context only |
| `matches_played` | Distinct matches in that context |
| Per-90 columns | e.g. `xg_per_90`, `passes_per_90`, … (13 PCA features) |
| `z_*` columns | Z-scored versions of the 13 features (see below) |

### 270-minute rule (per context)

During dbt aggregation, any player-context with **fewer than 270 total minutes** is dropped:

```sql
HAVING SUM(minutes_played) >= 270
```

270 minutes is roughly three full matches. Below that, per-90 rates are too noisy for fair comparison.

### Dual-context filter

After z-scoring, dbt keeps only players who have **both** a club row and a national row:

```sql
HAVING COUNT(DISTINCT is_international) = 2
```

So the table has **two rows per eligible player** (one club, one national). A full pipeline run typically yields **978 context rows** (489 dual-context players × 2).

`consistency.py` applies the same 270-minute and dual-context rules again when reading from BigQuery (defensive check).

---

## Z-score partitioning (club vs club, national vs national)

Z-scores are computed in **dbt**, not in `consistency.py`. For each of the 13 PCA features, BigQuery uses a window partitioned by `is_international`:

```text
z = (player_value - mean_in_that_context) / stddev_in_that_context
```

| Context | Players compared to |
|---------|---------------------|
| Club (`is_international = false`) | All other club-context players in the table |
| National (`is_international = true`) | All other national-context players in the table |

**Why this matters:** A high `z_xg_per_90` at club means “above average for club football in our sample,” not “above average globally.” National-team xG and shot volumes are on a different scale, so national z-scores use national baselines only.

The 13 features (must match `src/ml/cluster.py`):

`xg_per_90`, `shots_per_90`, `passes_per_90`, `passes_att_third_per_90`, `pressures_per_90`, `carries_per_90`, `dribbles_per_90`, `interceptions_per_90`, `blocks_per_90`, `clearances_per_90`, `duels_per_90`, `xg_per_shot`, `pass_completion_pct`

---

## What `consistency_score` measures

**Formula** (in `consistency.py`):

```text
consistency_score = 1 - mean(|z_club,f - z_national,f|)   over all 13 features f
```

For each feature, take the absolute gap between the player’s club z-score and national z-score, average across features, then subtract from 1.

### How to interpret

| Score (typical range) | Meaning |
|-----------------------|---------|
| **Closer to 1** | Similar tactical profile in both contexts (small z-gaps on the 13 metrics) |
| **Lower** | Larger shift between club and national on these dimensions |

**Important:**

- This is **not** a “good player” score. A player can be consistently below average in both contexts.
- It does **not** use raw per-90 totals. It uses **z-scores** (peer-relative within each context).
- It is **not** the same as the Looker **context shift score** (raw per-90 differences). See [context-shift-score.md](./appendix/context-shift-score.md).

---

## Context performance scores

Before consistency, the script builds a weighted **performance score** per context:

```text
performance_score = sum over features f of (z_f * w_f)
```

Weights `w_f` come from `analytics.pca_loadings` (absolute loadings summed across PCs, normalized to sum to 1). The same weights are used for club and national.

| Output column | Source row |
|---------------|------------|
| `club_performance_score` | `is_international = false` |
| `national_performance_score` | `is_international = true` |

**Higher** = stronger profile **relative to peers in that same context** (not raw StatsBomb totals).

---

## What `performance_quadrant` means

Quadrants split the dual-context cohort by **medians** of `club_performance_score` and `national_performance_score` (recomputed every pipeline run).

| Quadrant | Condition | Plain-language meaning |
|----------|-----------|-------------------------|
| **Elite** | Club ≥ median **and** national ≥ median | Strong vs peers in both settings |
| **Club Specialist** | Club ≥ median **and** national < median | Better relative to club peers than national peers |
| **International Specialist** | Club < median **and** national ≥ median | Better relative to national peers than club peers |
| **Underperformer** | Both below median | Below median vs peers in both settings |

Median splits target roughly **25% of players per quadrant** (~122 of 489), with small variation when many players sit exactly on the median.

**Club Specialist** and **International Specialist** together are the players who “perform better” in **one** context only (about half the cohort).

---

## Output table: `analytics.consistency_scores`

**Location:** `{GCP_PROJECT}.analytics.consistency_scores`  
**GCS backup:** `gs://{ML_GCS_BUCKET}/models/consistency/consistency_scores.parquet`  
**Grain:** One row per **player** (dual-context only)

| Column | Type | Description |
|--------|------|-------------|
| `player_id` | ID | StatsBomb player id |
| `player_name` | string | Display name |
| `club_performance_score` | float | Weighted z-score sum, club context |
| `national_performance_score` | float | Weighted z-score sum, national context |
| `consistency_score` | float | Profile similarity (see above) |
| `performance_quadrant` | string | Elite / Club Specialist / International Specialist / Underperformer |
| `club_minutes` | float | Total club minutes used |
| `national_minutes` | float | Total national minutes used |

### How to use the output

```sql
-- Example: top 10 most consistent dual-context players
SELECT player_name, consistency_score, performance_quadrant,
       club_performance_score, national_performance_score
FROM `football-capstone-mds-496219.analytics.consistency_scores`
ORDER BY consistency_score DESC
LIMIT 10;
```

```sql
-- Quadrant counts
SELECT performance_quadrant, COUNT(*) AS n
FROM `football-capstone-mds-496219.analytics.consistency_scores`
GROUP BY 1
ORDER BY n DESC;
```

Downstream:

- **`mart_player_performance`** left-joins this table on `player_id` (one consistency row per player, not per season).
- **Looker** Consistency Explorer reads mart or BigQuery fields exposed in the semantic layer.
- **Chatbot** can query `mart_player_performance` for quadrant and scores.

Replace the project id with your `GCP_PROJECT_ID` if different.

---

## How to run `consistency.py`

### Prerequisites

1. **GCP auth:** `export GOOGLE_APPLICATION_CREDENTIALS=./dagster-service-account-key.json`
2. **dbt intermediate** models built, especially `int_player_club_vs_national`:

   ```bash
   dbt run --select int_player_club_vs_national
   ```

3. **`cluster.py` completed** so `analytics.pca_loadings` exists:

   ```bash
   python src/ml/cluster.py
   ```

### Run

```bash
conda activate soccer_capstone   # or your env with google-cloud-bigquery, pandas, pyarrow
export GOOGLE_APPLICATION_CREDENTIALS=./dagster-service-account-key.json
python src/ml/consistency.py
```

Expected console output includes:

- Row count fetched from `int_player_club_vs_national`
- Eligible dual-context player count
- Feature weights printed
- `performance_quadrant` value counts
- Upload to GCS and load into `analytics.consistency_scores`

### Refresh marts

```bash
dbt run --select mart_player_performance
```

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `GCP_PROJECT_ID` | `football-capstone-mds-496219` | BigQuery project |
| `ML_GCS_BUCKET` | `football-analytics-mds496219` | Parquet upload bucket |
| `ML_BQ_DATASET` | `analytics` | Target dataset for `consistency_scores` |
| `DBT_INTERMEDIATE_DATASET` | `dbt_intermediate` | Source dataset for `int_player_club_vs_national` |
| `CONSISTENCY_SOURCE_DATASET` | same as intermediate | Override source dataset if needed |

### Failure modes

| Error | Likely cause | Fix |
|-------|----------------|-----|
| `pca_loadings missing required features` | `cluster.py` not run or wrong feature names | Run `cluster.py` after dbt |
| `No dual-context players found` | Empty or stale `int_player_club_vs_national` | Re-run dbt intermediate |
| Wrong row counts | Old `WRITE_TRUNCATE` load | Re-run script; check BigQuery table |

---

## Re-running in Databricks (notebooks)

Exploratory and report notebooks can **recompute** the same logic or **read** precomputed `analytics.consistency_scores`. See [notebooks.md](./notebooks.md):

- **03** – formula walkthrough and optional export to GCS/BigQuery
- **04** – feature gaps between Club vs International specialists
- **08** – RQ3 quadrant analysis for the final report

Production scores for the dashboard should come from **`consistency.py`** (or Dagster) so results match `mart_player_performance`.

---

## Quick reference: consistency vs context shift

| Metric | Built in | Question it answers |
|--------|----------|---------------------|
| `consistency_score` | `consistency.py` | How similar is the player’s z-profile across contexts? |
| `club_performance_score` / `national_performance_score` | `consistency.py` | How strong is the player vs peers in each context? |
| `performance_quadrant` | `consistency.py` | Elite / specialist / underperformer (median splits) |
| `context_shift_score` | Looker calculated field | Raw per-90 gap (national minus club) on 8 metrics |
