# Rabin's Technical Brief — Consistency Scoring, dbt, Databricks

## 1. What It Does and Why

My part answers **Research Question 3**: do players perform differently for club vs national teams, and how consistent is their playing profile across both contexts?

The pipeline produces three things the rest of the platform depends on:

- **dbt model** — `int_player_club_vs_national` aggregates per-90 stats and z-scores by context (club vs national), with eligibility rules baked in
- **Production scorer** — `consistency.py` reads those z-scores, applies PCA feature weights, computes performance scores, consistency scores, and four quadrants
- **Databricks notebooks** — where the formula was designed, validated, and turned into report figures (RQ3)

Downstream consumers:

- **`analytics.consistency_scores`** in BigQuery (one row per dual-context player)
- **`mart_player_performance`** (dbt mart joins consistency fields onto every player-season)
- **Looker Consistency Explorer** and the **Django chatbot**

---

## 2. Pipeline Overview

```text
dbt run (intermediate)  →  int_player_club_vs_national   (2 rows per eligible player)
        ↓
python src/ml/cluster.py  →  analytics.pca_loadings        (PCA feature weights — Li's work)
        ↓
python src/ml/consistency.py  →  analytics.consistency_scores
        ↓
dbt run (marts)  →  mart_player_performance
```

**Run order matters.** `consistency.py` needs both `int_player_club_vs_national` and `analytics.pca_loadings`. Dagster runs this automatically: `cluster_assignments` → `consistency_score` → `dbt_mart_refresh`.

---

## 3. dbt Model: `int_player_club_vs_national`

**File:** `models/intermediate/int_player_club_vs_national.sql`  
**Location:** `{GCP_PROJECT}.dbt_intermediate.int_player_club_vs_national`

### Row level

One row per **player** per **context**:

| Column | Meaning |
|---|---|
| `player_id`, `player_name` | Player identity |
| `is_international` | `false` = club, `true` = national team |
| `total_minutes`, `matches_played` | Aggregated within that context only |
| 13 per-90 columns | e.g. `xg_per_90`, `passes_per_90`, … (aligned with PCA) |
| `z_*` columns | Z-scored versions of the 13 features |

### Eligibility: 270-minute rule (per context)

During aggregation, any player-context with fewer than 270 total minutes is dropped:

```sql
HAVING SUM(minutes_played) >= 270
```

270 minutes ≈ three full matches. Below that, per-90 rates are too noisy.

### Dual-context filter

After z-scoring, dbt keeps only players who appear in **both** contexts:

```sql
HAVING COUNT(DISTINCT is_international) = 2
```

Result: **two rows per eligible player** (~670 players × 2 ≈ 1,300+ context rows).

### Z-score partitioning

Z-scores are computed **in dbt**, not in Python. For each of the 13 PCA features:

```text
z = (player_value - mean_in_that_context) / stddev_in_that_context
```

Window partitioned by `is_international`:

| Context | Compared to |
|---|---|
| Club (`is_international = false`) | All other club-context players |
| National (`is_international = true`) | All other national-context players |

**Why:** National-team xG and shot volumes sit on a different scale than club football. Club z-scores use club baselines only; national z-scores use national baselines only.

### 13 PCA features (must match `cluster.py`)

`xg_per_90`, `shots_per_90`, `passes_per_90`, `passes_att_third_per_90`, `pressures_per_90`, `carries_per_90`, `dribbles_per_90`, `interceptions_per_90`, `blocks_per_90`, `clearances_per_90`, `duels_per_90`, `xg_per_shot`, `pass_completion_pct`

### Run commands

```bash
conda activate soccer_capstone
dbt run --select int_player_club_vs_national
# or with dependencies:
dbt run --select +int_player_club_vs_national
```

### Common issues

- **Empty table** → upstream `int_player_match_stats` not built; run `dbt run --select intermediate`
- **Few dual-context players** → 270-min threshold is strict; check minutes distribution in raw data
- **Z-scores all NULL** → zero stddev for a feature in one context; `SAFE_DIVIDE` + `NULLIF` handles this in SQL

---

## 4. Production Scorer: `consistency.py`

**File:** `src/ml/consistency.py`  
**Output:** `analytics.consistency_scores` + GCS backup at `gs://football-analytics-mds496219/models/consistency/consistency_scores.parquet`

### What it does (step by step)

1. **Read** context rows from `int_player_club_vs_national` (player, context, 13 `z_*` columns)
2. **Filter** to dual-context players with ≥270 min in each context (defensive re-check)
3. **Load PCA weights** from `analytics.pca_loadings` absolute loadings summed across PCs, normalized to sum to 1
4. **Compute performance scores** per context:

   ```text
   performance_score = Σ (z_f × w_f)   over 13 features
   ```

5. **Compute consistency score**:

   ```text
   consistency_score = 1 - mean(|z_club,f - z_national,f|)   over 13 features
   ```

6. **Assign quadrants** via median splits on `club_performance_score` and `national_performance_score`
7. **Export** parquet to GCS, load into BigQuery with `WRITE_TRUNCATE`

### Output columns

| Column | Description |
|---|---|
| `club_performance_score` | Weighted z-score sum, club context |
| `national_performance_score` | Weighted z-score sum, national context |
| `consistency_score` | Profile similarity (closer to 1 = more similar) |
| `performance_quadrant` | Elite / Club Specialist / International Specialist / Underperformer |
| `club_minutes`, `national_minutes` | Minutes used in each context |

### Quadrant logic

Medians are recomputed every run on the dual-context cohort:

| Quadrant | Condition |
|---|---|
| **Elite** | Club ≥ median AND national ≥ median |
| **Club Specialist** | Club ≥ median AND national < median |
| **International Specialist** | Club < median AND national ≥ median |
| **Underperformer** | Both below median |

Roughly 25% of players per quadrant (~167 of ~670).

### How to interpret

| Metric | What it measures | What it does NOT measure |
|---|---|---|
| `consistency_score` | How similar the player's z-profile is across contexts | Whether the player is "good" |
| `club/national_performance_score` | Strength vs peers **within that context** | Raw StatsBomb totals |
| `performance_quadrant` | Relative strength in each context | Absolute skill level |

**Not the same as Looker's context shift score** as that uses raw per-90 gaps, not z-scores. See `docs/appendix/context-shift-score.md`.

### Run manually

```bash
conda activate soccer_capstone
export GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json

# Prerequisites
dbt run --select int_player_club_vs_national
python src/ml/cluster.py          # creates analytics.pca_loadings

# Score
python src/ml/consistency.py

# Refresh mart
dbt run --select mart_player_performance
```

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `GCP_PROJECT_ID` | `football-capstone-mds-496219` | BigQuery project |
| `ML_GCS_BUCKET` | `football-analytics-mds496219` | Parquet upload bucket |
| `ML_BQ_DATASET` | `analytics` | Target dataset |
| `DBT_INTERMEDIATE_DATASET` | `dbt_intermediate` | Source for `int_player_club_vs_national` |

### Tests

```bash
pytest tests/test_consistency.py -v
```

Tests cover: weighted performance score, consistency formula (`1 - mean|z_gap|`), quadrant labels, median-boundary behaviour, and exclusion of single-context players.

### Common issues

| Error | Cause | Fix |
|---|---|---|
| `pca_loadings missing required features` | `cluster.py` not run | Run `cluster.py` first |
| `No dual-context players found` | Stale/empty intermediate table | Re-run dbt intermediate |
| Scores differ from dashboard | Marts not refreshed after re-score | `dbt run --select mart_player_performance` |
| NULL consistency in mart | Join is on `player_id` only (one score per player, not per season) | Expected as not every player-season has dual-context data |

---

## 5. Databricks: Notebooks + BigQuery Connection

### Why Databricks

Used during development to explore the club-vs-national question, validate the formula, and produce report figures. Production scores come from `consistency.py`; notebooks are the **methodology source of truth**.

### BigQuery connection setup

Follow `docs/databricks_bigquery_setup.md`:

1. Create connection `bq_raw_statsbomb_sa` (Google BigQuery + service account JSON)
2. Create foreign catalog `bq_raw_statsbomb_sa_catalog`
3. Verify:

```sql
SELECT * FROM bq_raw_statsbomb_sa_catalog.raw_statsbomb.matches LIMIT 10;
SHOW SCHEMAS IN bq_raw_statsbomb_sa_catalog;
```

Notebooks read transformed tables via Spark SQL:

```python
BQ_CATALOG = os.environ.get("BQ_CATALOG", "bq_raw_statsbomb_sa_catalog")
INT_TABLE = f"{BQ_CATALOG}.dbt_intermediate.int_player_club_vs_national"
```

**Schema naming:** Notebook 03 may reference `raw_statsbomb_intermediate` in older cells. If queries fail, switch to `dbt_intermediate`.

### Key notebooks

| Notebook | Purpose | Main inputs |
|---|---|---|
| `03_consistency_score.ipynb` | Formula design + validation (#83) | `int_player_club_vs_national`, `pca_loadings` |
| `04_feature_importance.ipynb` | Why specialists differ (#85) | Same + `consistency_scores` |
| `08_rq3_four_quadrant_consistency.py.ipynb` | Report-ready RQ3 analysis (#117) | Same tables, quadrant plots |

### Running in Databricks

1. Clone repo to Databricks Repos
2. Attach a cluster (Python + Spark SQL)
3. Set `BQ_CATALOG` if your catalog name differs
4. Run cells top to bottom

**Two access paths:**

- **Read data** → foreign catalog (`spark.sql(...).toPandas()`): no extra credentials
- **Write to GCS/BQ** (notebook 03 §8 only) → needs `GOOGLE_APPLICATION_CREDENTIALS` on the cluster, same JSON key as local runs

### Notebook flags

```python
USE_PRECOMPUTED_SCORES = True   # read analytics.consistency_scores (matches production)
USE_PRECOMPUTED_SCORES = False  # recompute in pandas (should match consistency.py)
```

For dashboard data, always prefer **`consistency.py`** or Dagster over notebook exports.

### Common issues

| Symptom | Fix |
|---|---|
| `Table not found: ...dbt_intermediate...` | dbt not deployed; wrong catalog name |
| Empty consistency results | No dual-context players; re-run dbt |
| Scores differ from dashboard | Notebook recomputed vs precomputed; or marts not refreshed |
| BigQuery export fails on Serverless | Use pandas → GCS → load job (notebook 03 cell 8), not Spark-BigQuery connector |

---

## 6. Key Files

| File | Purpose |
|---|---|
| `models/intermediate/int_player_club_vs_national.sql` | Club/national aggregates, z-scores, eligibility |
| `src/ml/consistency.py` | Production scorer (weights, scores, quadrants, export) |
| `tests/test_consistency.py` | Unit tests for scoring logic |
| `notebooks/03_consistency_score.ipynb` | Formula walkthrough + optional export |
| `notebooks/04_feature_importance.ipynb` | Specialist feature-gap analysis |
| `notebooks/08_rq3_four_quadrant_consistency.py.ipynb` | RQ3 report tables and plots |
| `models/marts/mart_player_performance.sql` | Joins consistency scores onto player-seasons |
| `src/dagster/assets/ml_assets.py` | `consistency_score` Dagster asset |
| `docs/consistency.md` | Full scoring definitions and runbook |
| `docs/databricks_bigquery_setup.md` | Catalog connection steps |
| `docs/notebooks.md` | Notebook catalog and run order |

---

## 7. Interview Talking Points

**"Walk me through the consistency scoring pipeline."**

We wanted to know whether players who appear for both club and country perform differently in each setting. In dbt, I built `int_player_club_vs_national`, which aggregates per-90 stats separately for club and national contexts, z-scores each metric within its context, and filters to players with at least 270 minutes in both. Then `consistency.py` reads those z-scores, weights them using PCA loadings from the clustering pipeline, and produces two performance scores (club vs national), a consistency score measuring profile similarity, and a four-quadrant classification. Results land in BigQuery and flow into the dashboard mart.

**"Why z-score within context instead of comparing raw per-90?"**

Club and international football have different baselines. Shot volumes, pressing intensity, and xG rates aren't on the same scale. Z-scoring within each context answers "how does this player compare to peers in this setting?" rather than "are their raw numbers similar?" That makes the club-vs-national comparison fair.

**"What does consistency_score actually measure?"**

It's `1 minus the average absolute z-gap across 13 playing-style features`. A score near 1 means the player's tactical profile looks similar at club and for their country. It's not a quality score since a player can be consistently below average in both contexts. The quadrant labels capture relative performance: Elite players beat the median in both settings; Club Specialists and International Specialists excel in one context but not the other.

**"Why 270 minutes?"**

It's roughly three full matches. Below that threshold, per-90 rates are too volatile for meaningful comparison. We apply it per context, so a player needs 270+ club minutes AND 270+ national minutes to enter the analysis.

**"How does Databricks fit in?"**

Databricks was our analysis environment connected to BigQuery via a foreign catalog. I developed and validated the scoring formula in notebook 03, explored why specialists differ in notebook 04, and produced the RQ3 report figures in notebook 08. Once the logic was stable, I productionised it in `consistency.py` so Dagster could run it automatically and the dashboard always gets the same results.

**"What would you improve?"**

The consistency score is player-level, not player-season-level, so it doesn't capture how a player's club-vs-national gap changes over time. A season-aware version would be more useful for tracking development. Also, the 270-minute threshold is a blunt instrument and a minutes-weighted confidence interval or Bayesian shrinkage would handle small samples better.
