# Quan's Technical Brief — Data Pipeline, GCP, dbt, Dagster, Docker

## 1. What It Does and Why

My part is the **entire data backbone** of the platform. Nothing else works without it:

- **Ingestion** — pulls StatsBomb open event data (matches, events, lineups), uploads to Google Cloud Storage, loads into BigQuery
- **dbt transformation** — cleans and aggregates raw data through 3 layers (staging → intermediate → marts)
- **Dagster orchestration** — automates the full pipeline end-to-end on a weekly schedule, and triggers a partial run when new data lands in GCS
- **GCP infrastructure** — two GCS buckets, five BigQuery datasets, one service account
- **Docker** — runs all three services (Django, Dagster, Jupyter) with a single `docker compose up`

---

## 2. GCP Setup

### Credentials
You need two things to run anything:
- `dagster-service-account-key.json` — GCP service account key for pipeline/dbt work. Get this from the team. Place it in the project root. **Never commit it.**
- `chatbot-service-account-key.json` — read-only GCP key for the Django chatbot. **Never commit it.**
- `.env` — copy from `.env.example`, fill in at minimum `GROQ_API_KEY`. All GCP resource names (`GCP_PROJECT_ID`, `INGESTION_GCS_BUCKET`, `ML_GCS_BUCKET`) are read from this file — do not hardcode them anywhere.

```bash
cp .env.example .env
export GOOGLE_APPLICATION_CREDENTIALS=./dagster-service-account-key.json
```

### GCP Resources

All values below are set via `.env` (copy from `.env.example`). The env var name is shown in parentheses.

| Resource | Env var | Purpose |
|---|---|---|
| GCP Project | `GCP_PROJECT_ID` | Everything lives here |
| Service Account | `GOOGLE_APPLICATION_CREDENTIALS` | All GCP API calls |
| GCS bucket | `INGESTION_GCS_BUCKET` | Raw ingestion (StatsBomb parquet files) |
| GCS bucket | `ML_GCS_BUCKET` | ML outputs (cluster_assignments, pca_loadings, consistency_scores) |
| BigQuery dataset | `INGESTION_BQ_DATASET` | Raw ingested tables (default: `raw_statsbomb`) |
| BigQuery dataset | — | `dbt_staging` — 1:1 mirror of raw |
| BigQuery dataset | `DBT_INTERMEDIATE_DATASET` | Filtered + aggregated business logic (default: `dbt_intermediate`) |
| BigQuery dataset | — | `dbt_marts` — final analytics tables (chatbot + dashboard read from here) |
| BigQuery dataset | `ML_BQ_DATASET` | ML script outputs (default: `analytics`) |

### Test GCP access
```bash
python -c "from google.cloud import bigquery; c = bigquery.Client(); print('BQ OK')"
```

---

## 3. Data Ingestion

Three scripts run in sequence:

| Script | Does |
|---|---|
| `src/ingestion/statsbomb.py` | Calls StatsBomb Python library, extracts matches/events/lineups, saves to `data/parquet/` locally |
| `src/ingestion/upload_gcs.py` | Uploads local parquet files to `gs://$INGESTION_GCS_BUCKET/raw/statsbomb/YYYY-MM-DD/` |
| `src/ingestion/load_bq.py` | Loads from GCS into BigQuery `$INGESTION_BQ_DATASET.{matches,events,lineups}` using `WRITE_TRUNCATE` (safe to re-run) |

Competitions ingested are defined in `TARGET_COMPETITIONS` in `statsbomb.py`: La Liga, Premier League, Ligue 1, Serie A, Bundesliga, Champions League, World Cup, Euros, AFCON, Copa America and more. Men's only, from 1970 onwards.

### StatsBomb data access

The pipeline supports two modes, selected automatically based on environment variables:

| Mode | When | Data coverage |
|---|---|---|
| **Open data** (default) | `SB_USERNAME`/`SB_PASSWORD` not set | Free StatsBomb data hosted on GitHub — limited seasons per competition |
| **Paid API** | Both `SB_USERNAME` and `SB_PASSWORD` set in `.env` | Full historical coverage |

`statsbombpy` handles authentication automatically — no code change is needed to switch modes. The script logs which mode is active at startup.

### Run manually
```bash
python src/ingestion/statsbomb.py   # ~10-30 min
python src/ingestion/upload_gcs.py
python src/ingestion/load_bq.py
```

### Add a new competition
1. Check available: `from statsbombpy import sb; print(sb.competitions())`
2. Add the name to `TARGET_COMPETITIONS` in `statsbomb.py`
3. Re-run all 3 scripts

### Common issues
- **DefaultCredentialsError** → `export GOOGLE_APPLICATION_CREDENTIALS=./dagster-service-account-key.json`
- **Missing parquet file** → `statsbomb.py` failed mid-run; check stdout for which competition errored
- **StatsBomb rate limit** → the library handles it automatically; just let it run
- **`NoAuthWarning: credentials were not supplied`** → expected when running on open data; not an error. Set `SB_USERNAME` and `SB_PASSWORD` in `.env` to use the paid API instead.
- **`INGESTION_GCS_BUCKET` not set** → `upload_gcs.py` and `load_bq.py` will fail with a `None` bucket error. Make sure `.env` is populated and `load_dotenv()` has run.

---

## 4. dbt Models

### Layer conventions

| Layer | Dataset | Rule |
|---|---|---|
| Staging | `dbt_staging` | 1:1 mirror of raw. Type casts only. Never filter rows. |
| Intermediate | `dbt_intermediate` | Business logic + aggregation. Always filter `WHERE m.gender = 'male'`. |
| Marts | `dbt_marts` | Analytics-ready. Joins ML outputs from `analytics` dataset. |

### Key design decisions
- **270-minute threshold** — `HAVING SUM(minutes_played) >= 270` in all player-level intermediate models. Change in `int_player_season_stats.sql` if needed.
- **Gender filter at intermediate** — staging stays a neutral 1:1 source mirror. Women's analysis would need separate intermediate models.
- **`SAFE_DIVIDE` everywhere** — never use bare `/` in dbt SQL to avoid division-by-zero errors.
- **Mart join grain** — `mart_player_clusters` and `mart_player_performance` join on `(player_id, competition_id, season_id)`. Joining on `player_id` alone causes fan-out (duplicate rows).

### Run commands
```bash
conda activate soccer_capstone

dbt deps                                    # install dbt_utils package (first time only)
dbt seed                                    # load seeds/cluster_labels.csv etc.
dbt run                                     # run everything
dbt run --select staging                    # run one layer
dbt run --select +mart_player_clusters      # run model + all its dependencies
dbt test                                    # run all schema tests
dbt docs generate && dbt docs serve         # view lineage in browser (localhost:8080)
```

### Maintenance
- After new data → `dbt run`
- After ML outputs change → `dbt run --select mart_player_clusters mart_player_performance`
- After updating cluster labels → update `seeds/cluster_labels.csv` then `dbt seed`
- Schema tests failing → check `models/*/schema.yml` — test expectation may be outdated

### Common issues
- **"Relation not found"** → use `+model_name` to run with dependencies: `dbt run --select +int_player_match_stats`
- **`dbt deps` error** → run `dbt deps` first to install packages from `packages.yml`
- **BigQuery quota error** → add `--threads 2` flag to limit concurrent queries

---

## 5. Dagster Orchestration

### Asset graph (runs in this order)
```
raw_statsbomb
    → football_analytics_dbt_assets   (all dbt models)
        → cluster_assignments          (runs cluster.py)
            → consistency_score        (runs consistency.py)
                → dbt_mart_refresh     (refreshes mart_player_clusters + mart_player_performance)
```

### Two jobs

| Job | Runs | Triggered by |
|---|---|---|
| `full_pipeline_job` | Everything (ingestion → dbt → ML → marts) | Weekly schedule (Mon 6am UTC) |
| `post_ingestion_job` | dbt + ML + marts only (no ingestion) | GCS sensor — avoids infinite loop |

### Run Dagster
```bash
# Conda
dagster dev -f src/dagster/definitions.py
# Open http://localhost:3000 → Assets → Select All → Materialize All

# Docker
docker compose up dagster-env
```

### Key files

| File | Purpose |
|---|---|
| `src/dagster/definitions.py` | Asset graph, jobs, schedule, sensor — main config |
| `src/dagster/assets/ingestion.py` | `raw_statsbomb` asset (runs 3 ingestion scripts) |
| `src/dagster/assets/dbt_assets.py` | `football_analytics_dbt_assets` (runs all dbt models) |
| `src/dagster/assets/ml_assets.py` | `cluster_assignments`, `consistency_score`, `dbt_mart_refresh` |

### Maintenance
- **Add a new asset** → add `@asset` function in `ml_assets.py`, register it in `definitions.py`
- **Change the schedule** → edit `cron_schedule` in `definitions.py`
- **Sensor not firing** → verify `INGESTION_GCS_BUCKET` is set in `.env`

### Common issues
- **"dbt not found"** → activate conda env before starting Dagster
- **Sensor causes infinite loop** → sensor must use `job=post_ingestion_job`, not `full_pipeline_job`. Running ingestion uploads to GCS which would re-trigger the sensor endlessly.

---

## 6. Docker

### Containers

| Container | Port | Runs |
|---|---|---|
| `django-env` | 8000 | Django chatbot + dashboard |
| `dagster-env` | 3000 | Dagster pipeline UI |
| `jupyter-env` | 8888 | Jupyter notebooks |

### Run
```bash
cp .env.example .env            # fill in GROQ_API_KEY
cp dagster-service-account-key.json .
cp chatbot-service-account-key.json .
docker compose up               # starts all 3 containers
docker compose up django-env    # start one container only
```

### Key files

| File | Purpose |
|---|---|
| `docker-compose.yml` | Defines all 3 services, volumes, environment variables |
| `Dockerfile.django` | Django container |
| `Dockerfile.dagster` | Dagster + dbt container |
| `Dockerfile.jupyter` | Jupyter notebook container |

### Common issues
- **Container can't reach BigQuery** → make sure `chatbot-service-account-key.json` / `dagster-service-account-key.json` are mounted and `GOOGLE_APPLICATION_CREDENTIALS` is set in `docker-compose.yml`
- **Port already in use** → `lsof -i :8000` to find and kill the process
- **Changes not reflected** → rebuild: `docker compose build django-env && docker compose up django-env`

---

## 7. Interview Talking Points

**"Walk me through the data pipeline."**

We built a fully automated ELT pipeline on GCP. StatsBomb open event data is pulled via their Python library, staged in Google Cloud Storage as Parquet files, then loaded into BigQuery. dbt transforms it through three layers — staging is a 1:1 mirror, intermediate applies the business logic and filters to men's competitions with a 270-minute minimum, and marts join in the ML outputs to produce analytics-ready tables. The whole pipeline is orchestrated by Dagster, which runs it weekly and also triggers on new data via a GCS sensor.

**"Why dbt?"**

dbt gives us version-controlled, testable SQL transformations. Every model is a SELECT statement, every transformation is traceable, and we get schema tests, documentation, and lineage for free. It also enforces the layering convention — staging never has business logic, marts never have raw data — which makes the codebase much easier to maintain and hand over.

**"Why Dagster over Airflow?"**

Dagster's asset-based model fits our pipeline perfectly. Instead of defining tasks, you define data assets and their dependencies. The UI shows you exactly which assets are stale. It also integrates natively with dbt via `dagster-dbt`. For a project this size, it was significantly simpler to set up than Airflow.

**"What would you improve?"**

The ingestion is currently a full reload on every run — we download all matches each time. An incremental approach that only pulls new matches would be much more efficient. Also, the Polymarket data ingestion is still manual — automating that would close the last remaining gap in the pipeline.
