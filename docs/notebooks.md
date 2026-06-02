# Analysis notebooks (Databricks)

Partner guide for running exploration and report notebooks in **Databricks** against **BigQuery** data.

Related docs:

- [Databricks + BigQuery setup](./databricks_bigquery_setup.md) (connection and catalog)
- [Consistency scoring](./consistency.md) (`consistency.py` and `analytics.consistency_scores`)
- [Dashboard appendix](./appendix/README.md) (Looker formulas)

---

## Before you start

### 1. Connect Databricks to BigQuery

Follow [databricks_bigquery_setup.md](./databricks_bigquery_setup.md) to create:

- Connection: `bq_raw_statsbomb_sa` (or your team name)
- Foreign catalog: `bq_raw_statsbomb_sa_catalog` (default in notebooks)

Verify with SQL:

```sql
SELECT * FROM bq_raw_statsbomb_sa_catalog.raw_statsbomb.matches LIMIT 10;
```

**Note:** Setup doc may list an older GCP project id. Notebooks use whatever project owns the foreign catalog. Confirm schemas exist:

```sql
SHOW SCHEMAS IN bq_raw_statsbomb_sa_catalog;
```

You should see at least `raw_statsbomb`, `dbt_intermediate`, and `analytics` (names may vary slightly by environment).

### 2. Ensure dbt and ML tables exist

Notebooks read **transformed** and **ML** tables, not raw Parquet alone.

| Need | Typical table path |
|------|-------------------|
| Matches / events | `{catalog}.raw_statsbomb.matches` |
| Player-season stats | `{catalog}.dbt_intermediate.int_player_season_stats` |
| Club vs national z-scores | `{catalog}.dbt_intermediate.int_player_club_vs_national` |
| Cluster assignments | `{catalog}.analytics.cluster_assignments` |
| PCA loadings | `{catalog}.analytics.pca_loadings` |
| Consistency scores | `{catalog}.analytics.consistency_scores` |

Run locally or via Dagster if tables are missing:

```bash
dbt run --select staging intermediate
python src/ml/cluster.py
python src/ml/consistency.py
dbt run --select mart_player_clusters mart_player_performance
```

### 3. Open notebooks in Databricks

1. Clone or sync this repo to Databricks (Repos or workspace files).
2. Open notebooks under `notebooks/` (`.ipynb` or `.py` Databricks notebooks).
3. Attach a cluster (SQL warehouse or interactive cluster with Python).
4. Run cells **top to bottom** unless a section says otherwise.

### 4. Catalog variable

Most analysis notebooks set:

```python
BQ_CATALOG = os.environ.get("BQ_CATALOG", "bq_raw_statsbomb_sa_catalog")
```

To point at another catalog, set environment variable `BQ_CATALOG` on the cluster or edit the default in the first code cell.

**Schema naming:** Notebooks **07** and **08** use `{catalog}.dbt_intermediate.*`. Notebook **03** may reference `raw_statsbomb_intermediate` in older cells. If queries fail, change the intermediate schema to `dbt_intermediate` to match your BigQuery layout.

---

## Recommended run order

```text
01 (EDA)  →  optional background
05 / player_clustering  →  clustering design (optional)
02  →  feature engineering experiments (optional)
03  →  consistency formula + optional export
04  →  specialist feature gaps (after 03 or production scores)
07  →  RQ1 report tables
08  →  RQ3 report tables
06  →  export artifacts (if used)
```

For **production** dashboard data, prefer **`src/ml/consistency.py`** and **`src/ml/cluster.py`** over notebook exports unless you are deliberately replicating or validating.

---

## Notebook catalog

| Notebook | Issue / topic | Main inputs | What it produces | Where outputs go |
|----------|---------------|-------------|------------------|------------------|
| `01_data_exploration.py.ipynb` | EDA | Raw / staged BigQuery tables | Summary stats, plots | Notebook display only |
| `02_feature_engineering.py.ipynb` | RQ2 features | Events, matches | Engineered feature tables | `main.football_rq2` (Databricks schema; team-specific) |
| `03_consistency_score.ipynb` | #83 formula | `int_player_club_vs_national`, `pca_loadings` | Scores, quadrants, plots | Optional: GCS `models/consistency/consistency_scores.parquet` + `analytics.consistency_scores` (chunk 8) |
| `04_feature_importance.ipynb` | #85 specialists | `int_player_club_vs_national`, `consistency_scores`, loadings | Bar charts, top separating features, example players | Notebook display; informs report |
| `05_player_clustering.py.ipynb` | Clustering design | `int_player_season_stats` or raw paths | k selection, archetype notes | Notebook display |
| `06_export_artifacts.py.ipynb` | Artifacts | Varies | Exports for handoff | GCS / Delta (check notebook cells) |
| `07_rq1_role_distribution.py.ipynb` | #118 RQ1 | `int_player_season_stats`, `cluster_assignments`, matches | Chi-square tables, heatmaps, report summary | Notebook display → copy to `report/final_report.qmd` |
| `08_rq3_four_quadrant_consistency.py.ipynb` | #117 RQ3 | `int_player_club_vs_national`, `pca_loadings`, optional `consistency_scores` | Quadrant table, scatter, position/comp breakdown | Notebook display → copy to final report |
| `player_clustering.ipynb` | Legacy / local | Parquet or sample data | Clustering experiments | Local files |
| `player_profiles_international_eda.ipynb` | International EDA | Match / player data | EDA plots | Notebook display only |
| `Data Validation & research question 3.ipynb` | RQ3 validation | Consistency-related tables | Validation checks | Notebook display |

---

## Notebook details

### 03 – Consistency score formula

**Purpose:** Document and reproduce the math behind `consistency.py` (weights, performance scores, consistency score, quadrants).

**Key cells:**

- Load `int_player_club_vs_national` and `analytics.pca_loadings`
- Recompute scores in pandas (should match `consistency.py` when `USE_PRECOMPUTED_SCORES = False`)
- Quadrant scatter plot and top players per quadrant

**Export (optional):** Writes the same parquet path as production (`models/consistency/consistency_scores.parquet`) and loads `analytics.consistency_scores` with `WRITE_TRUNCATE`. Requires service account JSON on the cluster (separate from the SQL foreign catalog).

See [consistency.md](./consistency.md) for interpretation.

### 04 – Feature importance

**Purpose:** Explain **why** Club Specialists differ from International Specialists (mean z-gaps on the 13 features).

**Inputs:** Can set `USE_PRECOMPUTED_SCORES = True` to read `analytics.consistency_scores` from BigQuery.

**Outputs:** Specialist comparison charts and narrative bullets for the final report. No required BigQuery write.

### 07 – RQ1 role distribution

**Purpose:** Test whether **position** and **competition** (top-five leagues) predict cluster membership.

**Outputs:**

- Position × cluster counts and row %
- Competition × cluster tests (KQ2a)
- Faceted heatmaps by league (KQ2b)
- `=== RQ1 executive summary ===` table (χ², Cramér's V) for the report

**Scope:** La Liga, EPL, Bundesliga, Serie A, Ligue 1. Position groups: GK, CB, FB, CM, AM, FW.

### 08 – RQ3 four-quadrant consistency

**Purpose:** Report-ready analysis of club vs national performance quadrants.

**Outputs:**

- Quadrant count / percent table
- Scatter: `club_performance_score` vs `national_performance_score`
- Top 10 players per quadrant
- Position and competition breakdowns
- `=== RQ3 executive summary ===` metrics

**Flags:**

- `USE_PRECOMPUTED_SCORES = True` → read `analytics.consistency_scores`
- `USE_PRECOMPUTED_SCORES = False` → recompute (same logic as `consistency.py`)

---

## How to run a notebook in Databricks

1. **Import:** Repos → Add repo → point at `UBC-MDS-Soccer-Capstone-2026` (or upload `notebooks/*.ipynb`).
2. **Open** the notebook (e.g. `08_rq3_four_quadrant_consistency.py.ipynb`).
3. **Select language:** Python (notebooks use `spark.sql` and `toPandas()`).
4. **Run all** or run section by section (Setup → Load → Analysis → Summary).
5. **Fix catalog paths** if `TABLE_OR_VIEW_NOT_FOUND`: run `SHOW SCHEMAS IN bq_raw_statsbomb_sa_catalog` and update `INTERMEDIATE` / `INT_TABLE` paths in the setup cell.

### Python vs SQL cells

- **Spark SQL:** `spark.sql("SELECT ... FROM {catalog}.dbt_intermediate....").toPandas()`
- **Plots:** matplotlib / seaborn on pandas DataFrames returned from Spark

### Service account for exports (notebook 03 cell 8 only)

Foreign catalog SQL does **not** replace GCP credentials for `google.cloud.storage` and `bigquery.Client`. Mount or pass `GOOGLE_APPLICATION_CREDENTIALS` pointing at the team JSON key (same as local `consistency.py`).

---

## Connecting notebook results to production

| Goal | Use |
|------|-----|
| Dashboard / chatbot / marts | `consistency.py`, `cluster.py`, Dagster |
| Validate formula | Notebook **03** |
| Report text and figures | Notebooks **07**, **08**, **04** |
| Ad-hoc exploration | **01**, `player_profiles_international_eda` |

After changing scores in a notebook export, run:

```bash
dbt run --select mart_player_performance
```

so marts pick up the new `analytics.consistency_scores` rows.

---

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| `Table not found: ...dbt_intermediate...` | dbt not deployed to that project; wrong catalog name |
| `Table not found: ...raw_statsbomb_intermediate...` | Update notebook path to `dbt_intermediate` (see notebook 03) |
| Empty consistency results | `int_player_club_vs_national` has no dual-context players; re-run dbt |
| Scores differ from dashboard | Notebook recomputed vs `USE_PRECOMPUTED_SCORES`; or marts not refreshed |
| BigQuery export fails on Serverless | Use notebook 03 cell 8 Option B (pandas → GCS → load job), not Spark-BigQuery connector |

---

## File locations

| Path | Role |
|------|------|
| `notebooks/*.ipynb` | Databricks-compatible analysis |
| `src/ml/consistency.py` | Production consistency scorer |
| `src/ml/cluster.py` | PCA + K-Means + `pca_loadings` |
| `models/intermediate/int_player_club_vs_national.sql` | Club/national aggregates and z-scores |
| `docs/consistency.md` | Scoring definitions and runbook |
| `docs/databricks_bigquery_setup.md` | Catalog connection steps |
