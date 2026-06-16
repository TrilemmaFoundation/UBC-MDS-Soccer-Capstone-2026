# UBC-MDS-Soccer-Capstone-2026

Football analytics platform for the UBC MDS Capstone 2026 (Trilemma Foundation).

Ingests StatsBomb open event data, transforms it through a 3-layer dbt pipeline, clusters players into tactical archetypes using PCA + KMeans, scores club vs international consistency, and serves results through an LLM chatbot and Looker Studio dashboard.

---

## Prerequisites

| Tool | Used for |
|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) (ARM64) | Running the full app stack |
| [Conda](https://docs.conda.io/en/latest/miniconda.html) | Local dbt, ML, and pipeline work |
| GCP service account key | BigQuery, GCS, and Django chatbot |
| [Groq API key](https://console.groq.com) | LLM chatbot |
| [Quarto](https://quarto.org/docs/get-started/) + LaTeX | Rendering the final report PDF |

Copy `.env.example` to `.env` and fill in all values before running anything. Never commit `.env` or `service-account-key.json`.

---

## Quick Start (Docker)

```bash
# 1. Clone
git clone https://github.com/TrilemmaFoundation/UBC-MDS-Soccer-Capstone-2026.git
cd UBC-MDS-Soccer-Capstone-2026

# 2. Add credentials (get from team)
cp .env.example .env          # fill in GCP vars, GROQ_API_KEY, LOOKER_STUDIO_URL, etc.
cp service-account-key.json . # GCP service account key — never commit this

# 3. Pull pre-built images and start
docker compose pull
docker compose run --rm django-env python app/manage.py migrate   # first time only
docker compose up

# 4. Open
# Chatbot + Dashboard → http://localhost
# Dagster pipeline UI  → http://localhost:3000
# Jupyter notebooks    → http://localhost:8888
```

> **Note:** If `docker compose pull` fails with "not found", the image tags in `docker-compose.yml` may be out of sync with Docker Hub. Ask the team to re-run the **Publish Docker Images** GitHub Action, or temporarily switch the three `image:` lines to `latest-django`, `latest-jupyter`, and `latest-dagster`.

---

## Architecture

```
StatsBomb API (open data or paid — set SB_USERNAME/SB_PASSWORD in .env)
    │
    ▼
GCS ($INGESTION_GCS_BUCKET/raw/statsbomb/)
    │
    ▼
BigQuery: $INGESTION_BQ_DATASET  (default: raw_statsbomb)
    │
    ▼  dbt (staging layer)
BigQuery: dbt_staging
└── stg_statsbomb__matches / events / lineups
    │
    ▼  dbt (intermediate layer — men's competitions only)
BigQuery: dbt_intermediate
└── int_player_match_stats       per-match player events
└── int_player_season_stats      per-season aggregates (270-min threshold)
└── int_player_club_vs_national  club vs international comparison
└── int_match_stats              per-match team metrics
└── int_team_season_stats        per-season team aggregates
└── int_team_rolling_form        5-match rolling averages
    │
    ▼  cluster.py + consistency.py
BigQuery: analytics
└── cluster_assignments    PCA + KMeans results (k=5 archetypes)
└── pca_loadings           13-feature loadings (long format)
└── consistency_scores     club vs national consistency per player
    │
    ▼  dbt (marts layer)
BigQuery: dbt_marts              ← chatbot and dashboard read from here
└── mart_player_clusters         player + archetype + per-90 metrics
└── mart_player_performance      player + archetype + consistency scores
└── mart_match_analysis          match results + team metrics
└── mart_team_comparison         team season + rolling form
└── mart_match_prediction_features  XGBoost feature matrix
```

**Orchestration:** Dagster runs the full pipeline on a weekly schedule and via a GCS sensor when new data lands.

---

## Repository Layout

| Path | Purpose |
|---|---|
| `app/` | Django web application (chatbot + dashboard) |
| `app/chatbot/` | Groq LLM tool-calling chatbot wired to BigQuery |
| `app/dashboard/` | Looker Studio embed |
| `models/staging/` | dbt staging models (1:1 raw mirror, type casts only) |
| `models/intermediate/` | dbt intermediate models (business logic, aggregations) |
| `models/marts/` | dbt mart models (analytics-ready, joined with ML outputs) |
| `src/dagster/` | Dagster asset graph, schedules, and sensors |
| `src/ingestion/` | StatsBomb → Parquet → GCS → BigQuery ingestion scripts |
| `src/ml/cluster.py` | PCA + KMeans clustering script → BigQuery |
| `src/ml/consistency.py` | Club vs national consistency scoring → BigQuery |
| `notebooks/` | Databricks analysis notebooks (EDA, clustering, consistency) |
| `report/` | Final report (Quarto) |
| `presentation/` | Capstone presentation deck (Quarto Reveal.js) |
| `tests/` | Python unit tests (`test_cluster.py`, `test_consistency.py`, etc.) |
| `docs/` | Component documentation and setup guides |
| `dbt_project.yml` | dbt project configuration |
| `docker-compose.yml` | Runs django-env, dagster-env, jupyter-env containers |
| `.env.example` | All required environment variables (copy to `.env`) |
| `HANDOVER.md` | Full partner handover guide |

---

## Environment Setup (Conda — for dbt / ML work)

```bash
conda env create -f environment.yml
conda activate soccer_capstone
cp .env.example .env            # fill in values
export GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json

# Install dbt packages (first time only)
dbt deps
```

Create a dbt profile at `~/.dbt/profiles.yml`:

```bash
mkdir -p ~/.dbt
cat > ~/.dbt/profiles.yml << 'EOF'
football_analytics:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: service-account
      project: "{{ env_var('GCP_PROJECT_ID') }}"
      dataset: dbt_intermediate
      keyfile: "{{ env_var('GOOGLE_APPLICATION_CREDENTIALS') }}"
      threads: 4
      timeout_seconds: 300
      location: US
      priority: interactive
EOF

dbt debug   # should print "All checks passed!"
```

---

## Running the Pipeline Manually

Run in order if Dagster is unavailable:

```bash
# Step 1: Ingest StatsBomb data → local Parquet → GCS → BigQuery
python src/ingestion/statsbomb.py    # saves to data/parquet/
python src/ingestion/upload_gcs.py   # upload to GCS
python src/ingestion/load_bq.py      # load into BigQuery

# Step 2: dbt staging + intermediate
dbt run --select staging intermediate

# Step 3: ML scripts
python src/ml/cluster.py             # → analytics.cluster_assignments, pca_loadings
python src/ml/consistency.py         # → analytics.consistency_scores

# Step 4: Refresh marts
dbt run --select mart_player_clusters mart_player_performance
dbt run --select mart_match_analysis mart_team_comparison mart_match_prediction_features

# Step 5: Verify
dbt test
```

Or trigger the full graph from the Dagster UI at `http://localhost:3000` (Assets → Materialize All).

---

## Reproducing the Final Report

The report source is `report/final_report.qmd`. It includes section files from `report/final_report/` and figures from `presentation/assets/`. A pre-built PDF is committed at `report/final_report.pdf`.

### Requirements

- Quarto CLI ([install guide](https://quarto.org/docs/get-started/))
- A LaTeX distribution (TeX Live). On macOS: `brew install --cask mactex-no-gui` or install via the conda env if available.

### Render

```bash
conda activate soccer_capstone   # optional — not required unless running embedded code
quarto render report/final_report.qmd
open report/final_report.pdf
```

The PDF is written to `report/final_report.pdf`. No BigQuery or GCP credentials are needed — the report uses static markdown includes and committed images.

To render the capstone presentation deck separately:

```bash
quarto render presentation/final_presentation.qmd
open presentation/final_presentation.html
```

See [`presentation/README.md`](./presentation/README.md) for slide map and presenter notes.

---

## GCP Setup

All GCP resource names are configured via `.env` (copy from `.env.example`). No values are hardcoded.

| Item | Env var |
|---|---|
| Project ID | `GCP_PROJECT_ID` |
| Service Account key | `GOOGLE_APPLICATION_CREDENTIALS` |
| Ingestion GCS bucket | `INGESTION_GCS_BUCKET` |
| ML outputs GCS bucket | `ML_GCS_BUCKET` |

BigQuery datasets (env vars): `INGESTION_BQ_DATASET` (raw), `DBT_INTERMEDIATE_DATASET`, `ML_BQ_DATASET`, plus `dbt_staging` and `dbt_marts` (managed by dbt).

---

## Testing

```bash
conda activate soccer_capstone
pytest tests/test_cluster.py -v
pytest tests/test_consistency.py -v
```

---

## Key Design Decisions

- **Gender filter at intermediate layer** — staging is a neutral 1:1 mirror; `WHERE m.gender = 'male'` is applied in intermediate models. Women's analysis would use separate intermediate models.
- **270-minute threshold** — all player-level models require `SUM(minutes_played) >= 270` for statistical stability.
- **13 PCA features** — `xg_per_90, shots_per_90, passes_per_90, passes_att_third_per_90, pressures_per_90, carries_per_90, dribbles_per_90, interceptions_per_90, blocks_per_90, clearances_per_90, duels_per_90, xg_per_shot, pass_completion_pct`
- **Cluster label recalibration** — KMeans cluster IDs shift after every re-train. Always verify `CLUSTER_LABELS` in `src/ml/cluster.py` against cluster centroids after re-running.
- **mart join grain** — `mart_player_clusters` and `mart_player_performance` join `cluster_assignments` on `(player_id, competition_id, season_id)` — not just `player_id` — to avoid fan-out.

---

## Documentation

See [`HANDOVER.md`](./HANDOVER.md) for the full partner handover guide including:
- Component runbooks (how to run and maintain each piece)
- BigQuery schema reference
- How to add new data or metrics
- Troubleshooting guide

See [`docs/`](./docs/) for component-specific documentation:

| Doc | Topic |
|---|---|
| [`docs/consistency.md`](./docs/consistency.md) | Consistency scoring pipeline |
| [`docs/notebooks.md`](./docs/notebooks.md) | Databricks notebook catalog and run order |
| [`docs/marts_data_dict.md`](./docs/marts_data_dict.md) | Mart table column reference |
| [`docs/databricks_bigquery_setup.md`](./docs/databricks_bigquery_setup.md) | Databricks + BigQuery connection |
| [`docs/briefings/quan_pipeline.md`](./docs/briefings/quan_pipeline.md) | Full pipeline, dbt, and Dagster briefing |
| [`docs/appendix/`](./docs/appendix/) | Extended methodology (consistency explorer, context shift score) |
