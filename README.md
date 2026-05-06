# UBC-MDS-Soccer-Capstone-2026

Shared project repo for the UBC MDS Soccer Capstone 2026 (Trilemma Foundation football analytics).

## Repository layout

| Path | Purpose |
|------|---------|
| `data/` | Local datasets (`Statsbomb/`, `Polymarket/`). Parquet files are gitignored. Obtain or generate data separately and place files here to match the paths expected in notebooks. |
| `notebooks/` | Analysis notebooks (EDA, club vs national team, player clustering). Figures can be written to `results/figures/` when cells are run. |
| `report/` | Quarto proposal report (`proposal_report.qmd`) and rendered PDF. |
| `results/figures/` | Exported plots used by the report and notebooks (created when you run the notebooks, required for images embedded in the Quarto PDF). |
| `environment.yml` | Conda environment specification for Python dependencies. |
| `Makefile` | Shortcuts for common tasks (e.g. building the report). |

## Environment

Create and activate the conda environment:

```bash
conda env create -f environment.yml
conda activate soccer_capstone
```

## GCP Setup

### Project
- **Project ID:** football-capstone-mds-495504
- **Service Account:** football-analytics-sa@football-capstone-mds-495504.iam.gserviceaccount.com

### Cloud Storage
- **Bucket:** `gs://football-analytics-mds2026/`
- **Folder structure:**
  - `raw/statsbomb/matches/` — raw match data from StatsBomb
  - `raw/statsbomb/events/` — raw event data from StatsBomb
  - `raw/statsbomb/lineups/` — raw lineup data from StatsBomb
  - `models/xgboost/` — trained XGBoost model artifacts
  - `models/clustering/` — trained clustering model artifacts

### BigQuery
- **Dataset:** `raw_statsbomb`

### Local Setup
1. Place `service-account-key.json` in the project root (do not commit)
2. Copy `.env.example` to `.env` and fill in values
3. Authenticate: `gcloud auth activate-service-account --key-file=service-account-key.json`

## Building the proposal report (PDF)

The report is a Quarto project under `report/`. From the **repository root**:

```bash
make report
```

This runs `quarto render report/proposal_report.qmd --to pdf` and writes `report/proposal_report.pdf`.

**Requirements:** [Quarto](https://quarto.org/docs/get-started/) and a LaTeX distribution (for example TeX Live) so PDF rendering can run `xelatex`.
