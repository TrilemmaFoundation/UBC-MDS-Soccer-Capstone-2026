# UBC-MDS-Soccer-Capstone-2026

Football analytics platform for the UBC MDS Capstone 2026 (Trilemma Foundation).

Ingests StatsBomb open event data, transforms it through a 3-layer dbt pipeline, clusters players into tactical archetypes using PCA + KMeans, scores club vs international consistency, and serves results through an LLM chatbot and Looker Studio dashboard.

---

## Quick Start (Docker)

```bash
# 1. Clone
git clone https://github.com/TrilemmaFoundation/UBC-MDS-Soccer-Capstone-2026.git
cd UBC-MDS-Soccer-Capstone-2026

# 2. Add credentials (get from team)
cp .env.example .env          # fill in GROQ_API_KEY
cp service-account-key.json . # GCP service account key — never commit this

# 3. Run
docker compose up

# 4. Open
# Chatbot + Dashboard → http://localhost:8000
# Dagster pipeline UI  → http://localhost:3000
# Jupyter notebooks    → http://localhost:8888
```

---

## Architecture

```
StatsBomb API (open data or paid — see INGESTION_GCS_BUCKET in .env)
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
| `src/ml/cluster.py` | PCA + KMeans clustering script → BigQuery |
| `src/ml/consistency.py` | Club vs national consistency scoring → BigQuery |
| `notebooks/` | Databricks analysis notebooks (EDA, clustering, consistency) |
| `report/` | Final report (Quarto) |
| `docs/` | Component documentation and setup guides |
| `scripts/` | Utility scripts (issue creation, etc.) |
| `dbt_project.yml` | dbt project configuration |
| `docker-compose.yml` | Runs django-env, dagster-env, jupyter-env containers |
| `.env.example` | All required environment variables (copy to `.env`) |
| `HANDOVER.md` | Full partner handover guide |

---

## Environment Setup (Conda — for dbt / ML work)

```bash
conda env create -f environment.yml
conda activate soccer_capstone
export GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
```

---

## Running the Pipeline Manually

```bash
# Staging + intermediate dbt models
dbt run --select staging intermediate

# Clustering (reads int_player_season_stats)
python src/ml/cluster.py

# Consistency scoring (reads int_player_club_vs_national + analytics.pca_loadings)
python src/ml/consistency.py

# Refresh marts with new ML outputs
dbt run --select mart_player_clusters mart_player_performance

# Run all dbt tests
dbt test
```

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
- `docs/ml_pipeline.md` — clustering notebook and cluster.py
- `docs/consistency.md` — consistency scoring
- `docs/dagster.md` — Dagster pipeline operation
- `docs/chatbot.md` — Django chatbot maintenance
- `docs/dashboard.md` — Looker Studio dashboard
- `docs/databricks_bigquery_setup.md` — Databricks + BigQuery connection
