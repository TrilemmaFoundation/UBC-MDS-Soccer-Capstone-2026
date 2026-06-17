# Dagster Pipeline Guide

This guide covers how to operate, update, and debug the Dagster orchestration pipeline for the Football Analytics platform.

## 1. How to Start Dagster

To run Dagster, you will need a GCP service account key named `dagster-service-account-key.json` with the following IAM roles:
*   BigQuery Data Editor
*   BigQuery Job User
*   Storage Admin

You can run Dagster either locally using Conda or via Docker. The Dagster UI will be served at `http://localhost:3000`.

### Running via Docker (Recommended)
This method is recommended as it ensures all environment variables, Python dependencies, and networking are correctly isolated.
```bash
# Ensure .env and dagster-service-account-key.json are properly set in the root directory
docker compose up dagster-env
```

### Running Locally (Without Docker)
Make sure you have your conda environment activated and your credentials exported before starting the server.
```bash
conda activate soccer_capstone
export GOOGLE_APPLICATION_CREDENTIALS=./dagster-service-account-key.json
dagster dev -f src/dagster/definitions.py
```

## 2. How to Trigger a Full Pipeline Run

To manually trigger a full end-to-end run (Ingestion → dbt → ML → Marts):

1. Open the Dagster UI at `http://localhost:3000`.
2. Navigate to the **Assets** tab in the top navigation bar.
3. Click the **Reload definitions** button if you've made recent code changes.
4. Click **Select All** to highlight all assets in the graph.
5. Click the **Materialize all** button in the top right corner.

Alternatively, you can go to **Overview** > **Jobs** > `full_pipeline_job` and click **Launchpad** > **Launch Run**.

## 3. How to Add a New Dagster Asset

To add a new step to the pipeline, you need to define a new asset and then register it in your Definitions.

1. Open (or create) the appropriate file in `src/dagster/assets/` (e.g., `src/dagster/assets/ml_assets.py`).
2. Define the new asset using the `@asset` decorator. Use the `deps` argument to specify which assets must run before it.

```python
import subprocess
from dagster import asset, AssetKey, Output, MetadataValue

@asset(
    group_name="ml",
    deps=[AssetKey(["cluster_assignments"])] # Runs after cluster_assignments completes
)
def my_new_asset():
    result = subprocess.run(
        ["python", "src/ml/my_script.py"],
        capture_output=True, 
        text=True
    )
    if result.returncode != 0:
        raise Exception(result.stderr)
        
    return Output(
        value=None, 
        metadata={"stdout": MetadataValue.text(result.stdout)}
    )
```

3. Ensure your asset is imported and registered in `src/dagster/definitions.py`.

## 4. How the Weekly Schedule and GCS Sensor Work

Dagster handles automation through two primary mechanisms:

*   **Weekly Schedule (`full_pipeline_job`)**: This schedule runs automatically every Monday at 6:00 AM UTC. It executes the entire pipeline, starting from StatsBomb data ingestion (`raw_statsbomb`) all the way down to refreshing the final dbt marts.
*   **GCS Sensor (`post_ingestion_job`)**: The sensor checks the `gs://$INGESTION_GCS_BUCKET/raw/statsbomb/matches/` directory every hour for new files. If new files are detected, it triggers the `post_ingestion_job`. 
    *   *Note*: This job intentionally skips the `raw_statsbomb` ingestion step. It only runs the dbt staging/intermediate models, the ML models, and the final mart refreshes. If it triggered the ingestion step instead, it would create new files, which would re-trigger the sensor and cause an infinite loop.

## 5. How to Re-run a Single Failed Asset

If a pipeline run fails midway through execution, you do not need to re-run the entire pipeline from scratch.

1. Open the Dagster UI and navigate to the **Runs** tab.
2. Click on the ID of the failed run.
3. In the top right corner of the run details page, click the dropdown arrow next to the **Re-execute** button.
4. Select **From failure**. This will spawn a new run that resumes exactly from the asset that failed, using the already-computed outputs of the successful upstream assets.

Alternatively, you can go to the **Assets** view, select *only* the specific asset that failed (and its downstream dependencies by Shift-clicking), and click **Materialize selected**.