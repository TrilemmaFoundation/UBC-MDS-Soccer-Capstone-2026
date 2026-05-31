# Partner Handover Guide
# UBC MDS Soccer Capstone 2026 — Trilemma Foundation Football Analytics

> **Last updated:** May 2026  
> **Outgoing team:** Quan Hoang, Li (Coachyyds), Teem Kwong, Rabin Duran  
> **For questions contact:** quandothoang (GitHub)

---

## Table of Contents
1. [What This System Does](#1-what-this-system-does)
2. [Architecture Overview](#2-architecture-overview)
3. [Repository Structure](#3-repository-structure)
4. [Infrastructure & Credentials](#4-infrastructure--credentials)
5. [Development Environment Setup](#5-development-environment-setup)
6. [Running the Full Pipeline](#6-running-the-full-pipeline)
7. [Component Guides](#7-component-guides)
   - [7a. Data Ingestion](#7a-data-ingestion)
   - [7b. dbt Models](#7b-dbt-models)
   - [7c. Clustering (cluster.py)](#7c-clustering-clusterpy)
   - [7d. Consistency Scoring (consistency.py)](#7d-consistency-scoring-consistencypy)
   - [7e. Dagster Orchestration](#7e-dagster-orchestration)
   - [7f. Django Chatbot](#7f-django-chatbot)
   - [7g. Looker Studio Dashboard](#7g-looker-studio-dashboard)
8. [BigQuery Schema Reference](#8-bigquery-schema-reference)
9. [How to Add New Data](#9-how-to-add-new-data)
10. [How to Maintain Each Component](#10-how-to-maintain-each-component)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. What This System Does

This platform answers football analytics questions using StatsBomb open event data. It:

- **Ingests** StatsBomb match and event data into Google Cloud Storage and BigQuery
- **Transforms** raw data through a 3-layer dbt pipeline into analytics-ready mart tables
- **Clusters** players into 5 tactical archetypes (Creative Winger, Creative Playmaker, Defensive Anchor, Pressing Forward, Low Activity) using PCA + KMeans on 13 per-90 metrics
- **Scores** player consistency between club and international competition
- **Serves** results through two products:
  - A **Django LLM chatbot** (Groq + BigQuery) for natural language football analytics queries
  - A **Looker Studio dashboard** for visual exploration of player clusters, team comparisons, and consistency scores

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA PIPELINE                            │
│                                                                 │
│  StatsBomb API                                                  │
│      │                                                          │
│      ▼                                                          │
│  GCS (gs://football-analytics-mds496219/)                       │
│  └── raw/statsbomb/{matches,events,lineups}/  ← Parquet files   │
│      │                                                          │
│      ▼                                                          │
│  BigQuery: raw_statsbomb dataset                                │
│  └── matches, events, lineups (raw tables)                      │
│      │                                                          │
│      ▼  dbt run                                                 │
│  BigQuery: dbt_staging dataset                                  │
│  └── stg_statsbomb__matches                                     │
│  └── stg_statsbomb__events                                      │
│  └── stg_statsbomb__lineups                                     │
│      │                                                          │
│      ▼  dbt run                                                 │
│  BigQuery: dbt_intermediate dataset                             │
│  └── int_player_match_stats   (per-match player stats)          │
│  └── int_player_season_stats  (per-season player stats, men)    │
│  └── int_player_club_vs_national (club vs intl comparison)      │
│  └── int_match_stats          (per-match team stats, men)       │
│  └── int_team_season_stats    (per-season team stats)           │
│  └── int_team_rolling_form    (5-match rolling averages)        │
│      │                                                          │
│      ▼  Python ML scripts                                       │
│  BigQuery: analytics dataset                                    │
│  └── cluster_assignments  ← cluster.py output                   │
│  └── pca_loadings         ← cluster.py output                   │
│  └── consistency_scores   ← consistency.py output               │
│      │                                                          │
│      ▼  dbt run                                                 │
│  BigQuery: dbt_marts dataset  ← PRODUCTS READ FROM HERE         │
│  └── mart_player_clusters     (player + archetype + per-90)     │
│  └── mart_player_performance  (player + archetype + consistency) │
│  └── mart_match_analysis      (match results + team metrics)    │
│  └── mart_team_comparison     (team season + rolling form)      │
│  └── mart_match_prediction_features (ML feature matrix)         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       ORCHESTRATION                             │
│                                                                 │
│  Dagster (port 3000)                                            │
│  Asset graph (in dependency order):                             │
│    raw_statsbomb                                                │
│      → football_analytics_dbt_assets  (staging + intermediate)  │
│        → cluster_assignments          (runs cluster.py)         │
│          → consistency_score          (runs consistency.py)     │
│            → dbt_mart_refresh         (refreshes marts)         │
│                                                                 │
│  Schedule: every Monday 6am UTC                                 │
│  Sensor:   triggers dbt when new files land in GCS              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         PRODUCTS                                │
│                                                                 │
│  Django chatbot  (port 8000)                                    │
│  └── Groq LLM (llama-3.1-8b-instant) + tool calling            │
│  └── Queries dbt_marts tables via BigQuery API                  │
│  └── Advanced Mode: shows SQL + raw data for debugging          │
│                                                                 │
│  Looker Studio dashboard (embedded in Django at /dashboard/)    │
│  └── 4 pages: Player Clusters, Consistency Explorer,            │
│               Team Comparison, Competition Breakdown            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Repository Structure

```
.
├── app/                          # Django web application
│   ├── chatbot/                  # LLM chatbot app (Groq + BigQuery)
│   │   ├── llm_engine.py         # Core: tool-calling, SQL generation, BQ query
│   │   ├── table_schema.py       # Schema context fed to the LLM
│   │   ├── views.py              # HTMX request handler
│   │   └── templates/            # chat.html, chat_message.html
│   ├── dashboard/                # Looker Studio embed app
│   └── config/                   # Django settings, URLs, WSGI
│
├── models/                       # dbt models (SQL transformations)
│   ├── staging/                  # 1:1 mirror of raw BigQuery tables
│   ├── intermediate/             # Filtered, aggregated business logic
│   └── marts/                    # Analytics-ready final tables
│
├── src/
│   ├── dagster/                  # Dagster orchestration
│   │   ├── assets/
│   │   │   ├── ingestion.py      # raw_statsbomb, raw_polymarket assets
│   │   │   ├── dbt_assets.py     # dbt asset group
│   │   │   └── ml_assets.py      # cluster_assignments, consistency_score assets
│   │   └── definitions.py        # Asset graph, jobs, schedules, sensors
│   │
│   └── ml/                       # ML pipeline scripts
│       ├── cluster.py            # PCA + KMeans clustering → BQ
│       └── consistency.py        # Club vs national consistency scoring → BQ
│
├── notebooks/                    # Databricks analysis notebooks
│   ├── player_clustering.ipynb   # Li's clustering notebook (source of truth for ML)
│   └── consistency_analysis.ipynb
│
├── docs/                         # Additional documentation
│   └── databricks_bigquery_setup.md
│
├── report/                       # Final report (Quarto)
│   └── final_report.qmd
│
├── dbt_project.yml               # dbt project config
├── docker-compose.yml            # Runs django-env, jupyter-env, dagster-env
├── Dockerfile.django             # Django container
├── Dockerfile.dagster            # Dagster container
├── Dockerfile.jupyter            # Jupyter/Databricks container
└── environment.yml               # Conda environment
```

---

## 4. Infrastructure & Credentials

### GCP Project
| Item | Value |
|---|---|
| Project ID | `football-capstone-mds-496219` |
| Service Account | `football-analytics-sa@football-capstone-mds-496219.iam.gserviceaccount.com` |
| GCS Bucket | `gs://football-analytics-mds496219/` |

### BigQuery Datasets
| Dataset | Contents | Who writes |
|---|---|---|
| `raw_statsbomb` | Raw ingested StatsBomb data | `ingestion.py` |
| `raw_polymarket` | Raw Polymarket data | `ingestion.py` |
| `dbt_staging` | 1:1 staged tables | dbt |
| `dbt_intermediate` | Filtered/aggregated intermediate models | dbt |
| `dbt_marts` | Final analytics tables (chatbot + dashboard read here) | dbt |
| `analytics` | ML model outputs (cluster_assignments, pca_loadings, consistency_scores) | cluster.py, consistency.py |

### Required credentials
1. **`service-account-key.json`** — GCP service account key. Place in project root. **Never commit this file.**
2. **`.env`** — copy from `.env.example` and fill in values

### `.env` variables
```
GCP_PROJECT_ID=football-capstone-mds-496219
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
GROQ_API_KEY=<get from Groq console at console.groq.com>
ML_GCS_BUCKET=football-analytics-mds496219
DBT_INTERMEDIATE_DATASET=dbt_intermediate
ML_BQ_DATASET=analytics
LOOKER_STUDIO_URL=https://lookerstudio.google.com/embed/reporting/00c26aba-1328-4c33-aa11-c3cff2b64c53/page/If9xF
```

---

## 5. Development Environment Setup

### Option A — Conda (recommended for ML/dbt work)
```bash
# Clone the repo
git clone https://github.com/TrilemmaFoundation/UBC-MDS-Soccer-Capstone-2026.git
cd UBC-MDS-Soccer-Capstone-2026

# Create environment
conda env create -f environment.yml
conda activate soccer_capstone

# Place credentials
cp service-account-key.json .          # get this from the outgoing team
cp .env.example .env && nano .env      # fill in GROQ_API_KEY

# Authenticate with GCP
export GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
```

### Option B — Docker (recommended for running the full stack)
```bash
cp .env.example .env && nano .env      # fill in GROQ_API_KEY
docker compose up
```

Docker exposes:
- `http://localhost:8000` — Django chatbot + dashboard
- `http://localhost:3000` — Dagster UI
- `http://localhost:8888` — Jupyter notebooks

### Verify setup
```bash
# Test BigQuery access
python -c "from google.cloud import bigquery; c = bigquery.Client(); print('BQ OK')"

# Test dbt connection
dbt debug

# Test Groq key
python -c "from groq import Groq; Groq().chat.completions.create(model='llama-3.1-8b-instant', messages=[{'role':'user','content':'hi'}]); print('Groq OK')"
```

---

## 6. Running the Full Pipeline

### Automated (Dagster — recommended)
```bash
# Start Dagster
dagster dev -f src/dagster/definitions.py
# Open http://localhost:3000
# Go to Assets → Select All → Materialize All
```

The weekly schedule runs automatically every Monday at 6am UTC. The GCS sensor triggers dbt whenever new files land in `raw/statsbomb/matches/`.

### Manual (step-by-step)
Run these in order if Dagster is unavailable:

```bash
# Step 1: Ingest StatsBomb data to GCS + BigQuery
python src/dagster/assets/ingestion.py

# Step 2: Run dbt (staging + intermediate layers)
dbt run --select staging intermediate

# Step 3: Train clustering model (reads int_player_season_stats, men only)
python src/ml/cluster.py
# Outputs: analytics.cluster_assignments, analytics.pca_loadings

# Step 4: Run consistency scoring
python src/ml/consistency.py
# Outputs: analytics.consistency_scores

# Step 5: Refresh dbt marts (picks up new ML outputs)
dbt run --select mart_player_clusters mart_player_performance

# Step 6: Refresh remaining marts
dbt run --select mart_match_analysis mart_team_comparison mart_match_prediction_features

# Step 7 (optional): Run dbt tests
dbt test
```

### Expected row counts after a successful run
| Table | Expected rows | Notes |
|---|---|---|
| `dbt_intermediate.int_player_season_stats` | ~5,800 | Men's competitions only |
| `dbt_intermediate.int_player_club_vs_national` | ~979 | Players with 270+ min in BOTH club and international |
| `dbt_intermediate.int_match_stats` | ~5,800 | Men's matches only |
| `analytics.cluster_assignments` | ~5,800 | One row per player-season |
| `analytics.pca_loadings` | ~52 | 13 features × 4 PCs (long format) |
| `analytics.consistency_scores` | ~979 | One row per player |
| `dbt_marts.mart_player_clusters` | ~5,800 | No duplicate player-seasons |
| `dbt_marts.mart_player_performance` | ~5,800 | One row per player-season |

---

## 7. Component Guides

### 7a. Data Ingestion

**File:** `src/dagster/assets/ingestion.py`

Pulls StatsBomb open data from the `statsbomb` Python library and writes Parquet files to GCS, then loads them into BigQuery using `WRITE_TRUNCATE` (idempotent — safe to re-run).

**To add a new competition or season:**
1. Check available competitions: `from statsbomb import StatsBombAPI; StatsBombAPI().competitions()`
2. Update the competition/season filter in `ingestion.py`
3. Re-run the ingestion asset in Dagster

**GCS structure:**
```
gs://football-analytics-mds496219/
├── raw/statsbomb/
│   ├── matches/      ← one Parquet per competition-season
│   ├── events/       ← one Parquet per match
│   └── lineups/      ← one Parquet per match
└── models/
    ├── clustering/   ← cluster_assignments.parquet, pca_loadings.parquet
    └── consistency/  ← consistency_scores.parquet
```

---

### 7b. dbt Models

**Config file:** `dbt_project.yml`  
**Models:** `models/` directory  
**Tests + schema:** `models/*/schema.yml`

#### Layer conventions
| Layer | Dataset | Rule |
|---|---|---|
| Staging | `dbt_staging` | 1:1 mirror of raw. Type casts only, no business logic. Never filter rows. |
| Intermediate | `dbt_intermediate` | Business logic, aggregation. **Filter `WHERE m.gender = 'male'`** to scope to men's football. |
| Marts | `dbt_marts` | Analytics-ready. Join ML outputs from `analytics` dataset. |

#### Key design decisions
- **270-minute threshold:** All player-level models filter `HAVING SUM(minutes_played) >= 270` to ensure statistical stability. Change this in the intermediate models if requirements change.
- **Gender filter at intermediate layer:** Staging stays neutral (1:1 source mirror). Women's analysis would use separate intermediate models.
- **`SAFE_DIVIDE`:** Used everywhere instead of `/` to avoid division-by-zero errors.

#### Running dbt
```bash
# Run specific model and all its dependencies
dbt run --select +mart_player_clusters

# Run all models
dbt run

# Run tests
dbt test

# See model lineage
dbt docs generate && dbt docs serve
```

---

### 7c. Clustering (cluster.py)

**File:** `src/ml/cluster.py`  
**Source:** `dbt_intermediate.int_player_season_stats` (men's only, 270+ min)  
**Output:** `analytics.cluster_assignments`, `analytics.pca_loadings` (also written to GCS)

#### What it does
1. Fetches 13 per-90 features for each player-season
2. Median imputation for nulls → 99th-percentile outlier clipping → StandardScaler
3. PCA: uses enough components to explain ≥80% variance
4. KMeans with k=5 → assigns each player-season to a cluster
5. Maps cluster IDs to archetype labels via `CLUSTER_LABELS` dict
6. Exports cluster_assignments (player_id, competition_id, season_id, cluster, archetype, pc1, pc2)

#### ⚠️ Important: cluster label recalibration
KMeans cluster IDs (0–4) are assigned arbitrarily each run. After any re-training, you must verify the `CLUSTER_LABELS` mapping is still correct:

```python
# In a notebook or script, after fitting KMeans:
cluster_profiles = df.groupby('cluster')[FEATURES].mean()
print(cluster_profiles.T)
```

Then update `CLUSTER_LABELS` in `cluster.py` based on the centroid profiles:
- High `xg_per_90` + `shots_per_90` + `dribbles_per_90` → **Creative Winger**
- High `passes_per_90` + `pass_completion_pct` + `passes_att_third_per_90` → **Creative Playmaker**
- High `pressures_per_90` + `interceptions_per_90` → **Defensive Anchor**
- High `pressures_per_90` + `shots_per_90` → **Pressing Forward**
- Low everything → **Low Activity**

#### The 13 PCA features (must match Li's notebook)
`xg_per_90, shots_per_90, passes_per_90, passes_att_third_per_90, pressures_per_90, carries_per_90, dribbles_per_90, interceptions_per_90, blocks_per_90, clearances_per_90, duels_per_90, xg_per_shot, pass_completion_pct`

---

### 7d. Consistency Scoring (consistency.py)

**File:** `src/ml/consistency.py`  
**Source:** `dbt_intermediate.int_player_club_vs_national` (players with 270+ min in BOTH contexts)  
**Source (weights):** `analytics.pca_loadings` (from cluster.py)  
**Output:** `analytics.consistency_scores`

#### What it does
1. Reads z-scored per-90 metrics for each player in both club and international context
2. Uses PCA loadings as feature weights
3. Computes weighted performance scores for club and international contexts
4. `consistency_score = 1 - mean(|z_club - z_national|)` across features
5. Assigns `performance_quadrant` based on median splits:
   - **Elite**: high club + high international
   - **Club Specialist**: high club + low international
   - **International Specialist**: low club + high international
   - **Underperformer**: low club + low international

#### Running consistency.py
```bash
# Must run AFTER cluster.py (needs analytics.pca_loadings)
python src/ml/consistency.py
```

---

### 7e. Dagster Orchestration

**Files:** `src/dagster/definitions.py`, `src/dagster/assets/`

#### Starting Dagster
```bash
dagster dev -f src/dagster/definitions.py
# UI at http://localhost:3000
```

#### Asset graph
```
raw_statsbomb          (ingestion.py)
raw_polymarket         (ingestion.py)
football_analytics_dbt_assets  (runs all dbt models)
cluster_assignments    (runs src/ml/cluster.py)
consistency_score      (runs src/ml/consistency.py)
dbt_mart_refresh       (runs mart_player_clusters + mart_player_performance)
```

#### Adding a new asset
```python
# In src/dagster/assets/ml_assets.py
@asset(
    group_name="ml",
    deps=[AssetKey(["cluster_assignments"])],  # declare dependencies
)
def my_new_asset():
    result = subprocess.run(["python", "src/ml/my_script.py"], ...)
    if result.returncode != 0:
        raise Exception(result.stderr)
    return Output(value=None, metadata={"stdout": MetadataValue.text(result.stdout)})
```

Then register it in `src/dagster/definitions.py`:
```python
defs = Definitions(
    assets=[..., my_new_asset],
    ...
)
```

#### Schedule and sensor
- **Weekly schedule:** Every Monday 6am UTC — triggers `full_pipeline_job` (all assets)
- **GCS sensor:** Checks `raw/statsbomb/matches/` hourly — triggers `dbt_refresh_job` if new files appear

---

### 7f. Django Chatbot

**Directory:** `app/`

#### Running locally (without Docker)
```bash
cd app
python manage.py runserver
# Visit http://localhost:8000
```

#### Running with Docker
```bash
docker compose up django-env
# Visit http://localhost:8000
```

#### How the chatbot works
1. User submits a natural language question
2. `views.py` calls `ask_football_chatbot()` in `llm_engine.py`
3. LLM (Groq `llama-3.1-8b-instant`) generates a BigQuery SQL query using tool-calling
4. `query_bigquery()` validates the SQL (blocks any non-SELECT statements) and executes it
5. LLM formats the results into a human-readable response
6. Response rendered via HTMX into `chat_message.html`

#### Updating the chatbot to add new tables or columns
Edit `app/chatbot/table_schema.py` — this is the schema context fed to the LLM. Add new tables or columns following the existing format.

#### Updating the system prompt
Edit `llm_engine.py` lines 88–96 (the CRITICAL RULES section). Keep rules numbered and specific.

#### Advanced Mode
Checkbox in the UI that shows the executed SQL and raw BigQuery JSON for debugging. Useful when responses look wrong — check what SQL the LLM generated.

#### Security
- `is_safe_sql()` blocks all non-SELECT statements (DROP, DELETE, INSERT, etc.)
- 50 MB BigQuery bytes-billed limit per query
- Query cache enabled to reduce costs

---

### 7g. Looker Studio Dashboard

**URL:** https://lookerstudio.google.com/reporting/00c26aba-1328-4c33-aa11-c3cff2b64c53

**Embedded at:** `/dashboard/` in the Django app (iframe)

#### Pages
| Page | Source table | Description |
|---|---|---|
| 1. Player Clusters | `mart_player_clusters` | Scatter plot of PC1/PC2, filter by archetype |
| 2. Consistency Explorer | `mart_player_performance` | Club vs international performance quadrant |
| 3. Team Comparison | `mart_team_comparison` | xG trends, goals vs xG, possession vs pressing |
| 4. Competition Breakdown | `mart_player_clusters` + `mart_player_performance` | Cluster distribution per competition |

#### Updating the dashboard after a pipeline run
1. Open Looker Studio
2. Resource → Manage added data sources
3. For each data source: click Edit → Refresh fields
4. The dashboard will automatically reflect new data (BigQuery connection is live)

#### Sharing access
The dashboard is shared via the Looker Studio link. To give a new user editor access: Share → Add people → Editor role.

---

## 8. BigQuery Schema Reference

### `dbt_marts.mart_player_clusters`
One row per player-season. Joined grain: `(player_id, competition_id, season_id)`.

| Column | Type | Description |
|---|---|---|
| `player_id` | INT64 | StatsBomb player identifier |
| `player_name` | STRING | Player display name |
| `competition_id` | INT64 | Competition identifier |
| `competition_name` | STRING | e.g. "La Liga", "World Cup" |
| `season_id` | INT64 | Season identifier |
| `season_name` | STRING | e.g. "2020/2021" |
| `total_minutes` | FLOAT64 | Total minutes played in this season |
| `cluster_id` | INT64 | KMeans cluster index (0–4), -1 if unassigned |
| `cluster_label` | STRING | Archetype name |
| `pc1`, `pc2` | FLOAT64 | PCA coordinates for scatter plot visualization |
| `xg_per_90` … `pass_completion_pct` | FLOAT64 | All 13 PCA input features (per-90) |
| `goals_per_90`, `assists_per_90` | FLOAT64 | Supplementary traditional metrics |

### `dbt_marts.mart_player_performance`
One row per player-season with consistency scores joined.

| Column | Type | Description |
|---|---|---|
| *(all mart_player_clusters columns)* | | |
| `total_goals` … `total_aerial_duels` | INT64 | Raw season totals |
| `club_performance_score` | FLOAT64 | Weighted performance score at club level |
| `national_performance_score` | FLOAT64 | Weighted performance score at national level |
| `consistency_score` | FLOAT64 | 1 - mean absolute z-score difference (higher = more consistent) |
| `performance_quadrant` | STRING | Elite / Club Specialist / International Specialist / Underperformer |

### `dbt_marts.mart_match_analysis`
One row per match.

### `dbt_marts.mart_team_comparison`
One row per team-season (campaigns with ≥10 matches).

### `analytics.cluster_assignments`
One row per player-season. Written by `cluster.py`. Used by `mart_player_clusters` and `mart_player_performance`.

### `analytics.pca_loadings`
Long format: 52 rows (13 features × 4 PCs). Columns: `component`, `feature`, `loading`. Used by `consistency.py` as feature weights.

### `analytics.consistency_scores`
One row per player (players with 270+ min in BOTH club and international contexts). Written by `consistency.py`.

---

## 9. How to Add New Data

### New StatsBomb season/competition
1. Check available competitions in the StatsBomb library
2. Update `src/dagster/assets/ingestion.py` to include the new competition/season IDs
3. Re-run the `raw_statsbomb` Dagster asset
4. Re-run the full pipeline (dbt → cluster.py → consistency.py → dbt marts)

### New metric
1. Add the raw extraction in the relevant staging model (`models/staging/stg_statsbomb__events.sql`)
2. Aggregate it in `int_player_match_stats.sql`
3. Sum it in `int_player_season_stats.sql`
4. Expose as per-90 in `int_player_season_stats.sql`
5. Add to mart columns in `mart_player_clusters.sql` and/or `mart_player_performance.sql`
6. If adding to clustering: add to `FEATURES` list in `cluster.py` AND update Li's notebook
7. Update `app/chatbot/table_schema.py` so the LLM knows about the new column

---

## 10. How to Maintain Each Component

### Re-training clusters (e.g. after new season data added)
```bash
python src/ml/cluster.py
# IMPORTANT: verify cluster labels after every re-train
# KMeans cluster IDs are not stable between runs — see §7c above
dbt run --select mart_player_clusters mart_player_performance
```

### Updating the chatbot for new archetypes or tables
1. Edit `app/chatbot/table_schema.py` — add new columns/tables to the TABLE_CONTEXT string
2. If new cluster labels: update the `cluster_label` enum in `table_schema.py`
3. Restart the Django server (or Docker container)

### Updating dbt models
```bash
# After editing a .sql file
dbt run --select <model_name>+  # + runs downstream dependents too
dbt test --select <model_name>
```

### Adding a new Looker Studio page
1. Open the dashboard in Looker Studio edit mode
2. Add a new page
3. Add charts sourced from the relevant `dbt_marts` table
4. The Django embed at `/dashboard/` will automatically show the new page

---

## 11. Troubleshooting

### "cluster_assignments fan-out — duplicate players in chatbot results"
**Cause:** `mart_player_clusters.sql` join is on the wrong grain.  
**Fix:** Ensure the join uses `ON p.player_id = c.player_id AND p.competition_id = c.competition_id AND p.season_id = c.season_id` (3-column join, not just `player_id`).

### "Chatbot shows unknown players as top Creative Wingers"
**Cause:** KMeans cluster IDs shifted after re-training. `CLUSTER_LABELS` mapping is wrong.  
**Fix:** Print cluster centroids, re-identify archetypes, update `CLUSTER_LABELS` in `cluster.py`, re-run.

### "xG/90 values are unrealistically high (>0.5)"
**Cause:** Women's competition players mixed in, or players with very few minutes (near 270-min floor) in high-quality cup games.  
**Fix:** Check `WHERE m.gender = 'male'` is present in all 3 intermediate models. Raise the 270-min threshold if needed.

### "mart_player_performance has NULL consistency_score"
**Cause:** `consistency.py` hasn't been run yet, or `mart_player_performance.sql` hasn't been updated to join `analytics.consistency_scores`.  
**Fix:** Run `python src/ml/consistency.py` then `dbt run --select mart_player_performance`.

### "Dagster asset fails with dbt not found"
**Cause:** dbt is not in the PATH inside the Dagster process.  
**Fix:** Use the full path: `/path/to/conda/envs/soccer_capstone/bin/dbt` or ensure the conda env is activated before starting Dagster.

### "BigQuery query rejected by is_safe_sql()"
**Cause:** The LLM generated a query containing a forbidden keyword (e.g. REPLACE, MERGE).  
**Fix:** Usually a model quality issue. The CRITICAL RULES system prompt should prevent this. If persistent, add the specific pattern to the forbidden keywords list in `llm_engine.py`.

### "GCS sensor not triggering"
**Cause:** No new files in `raw/statsbomb/matches/` since last check, or GCS credentials issue.  
**Fix:** Check sensor logs in Dagster UI. Verify `ML_GCS_BUCKET` env var is set correctly. The sensor polls hourly — it may just not have fired yet.

---

*This document covers the system as of May 2026. For questions about specific components, see the individual team member documentation in `docs/`.*
