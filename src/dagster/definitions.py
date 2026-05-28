import os
from pathlib import Path

from dagster import (
    Definitions,
    AssetSelection,
    define_asset_job,
    ScheduleDefinition,
    sensor,
    RunRequest,
    SkipReason,
)
from dagster_dbt import DbtCliResource
from google.cloud import storage

from src.dagster.assets.ingestion import raw_statsbomb, raw_polymarket
from src.dagster.assets.dbt_assets import football_analytics_dbt_assets
from src.dagster.assets.ml_assets import cluster_assignments, consistency_score

DBT_PROJECT_DIR = Path(__file__).parent.parent.parent

# jobs
full_pipeline_job = define_asset_job(
    name="full_pipeline_job",
    selection=AssetSelection.all(),
)

dbt_refresh_job = define_asset_job(
    name="dbt_refresh_job",
    selection=AssetSelection.assets(football_analytics_dbt_assets),
)

# weekly schedule -- every Monday at 6am
ingestion_schedule = ScheduleDefinition(
    name="weekly_ingestion_schedule",
    cron_schedule="0 6 * * 1",
    job=full_pipeline_job,
)

# sensor -- triggers dbt when new files land in GCS
@sensor(
    job=dbt_refresh_job,
    minimum_interval_seconds=3600,
)
def gcs_new_file_sensor(context):
    bucket_name = os.getenv("ML_GCS_BUCKET", "football-analytics-mds496219")
    prefix = "raw/statsbomb/matches/"

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=prefix))
    except Exception as e:
        return SkipReason(f"Could not connect to GCS: {e}")

    if not blobs:
        return SkipReason("No files found in GCS")

    latest = max(blobs, key=lambda b: b.updated)
    last_seen = context.cursor or ""
    current = str(latest.updated)

    if current == last_seen:
        return SkipReason("No new files since last run")

    context.update_cursor(current)
    return RunRequest(run_key=current)


defs = Definitions(
    assets=[
        raw_statsbomb,
        raw_polymarket,
        football_analytics_dbt_assets,
        cluster_assignments,
        consistency_score,
    ],
    jobs=[full_pipeline_job, dbt_refresh_job],
    schedules=[ingestion_schedule],
    sensors=[gcs_new_file_sensor],
    resources={
        "dbt": DbtCliResource(project_dir=str(DBT_PROJECT_DIR)),
    },
)
