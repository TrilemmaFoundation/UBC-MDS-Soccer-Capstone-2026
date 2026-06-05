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
from src.dagster.assets.ml_assets import cluster_assignments, consistency_score, dbt_mart_refresh

DBT_PROJECT_DIR = Path(__file__).parent.parent.parent

# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

# Full end-to-end pipeline: ingestion → dbt → ML → mart refresh
full_pipeline_job = define_asset_job(
    name="full_pipeline_job",
    selection=AssetSelection.all(),
)

# Post-ingestion job: dbt → ML → mart refresh (no ingestion step)
# Used by the GCS sensor so it doesn't re-trigger ingestion and cause a loop.
post_ingestion_job = define_asset_job(
    name="post_ingestion_job",
    selection=AssetSelection.assets(
        football_analytics_dbt_assets,
        cluster_assignments,
        consistency_score,
        dbt_mart_refresh,
    ),
)

# ---------------------------------------------------------------------------
# Schedules
# ---------------------------------------------------------------------------

# Full pipeline every Monday at 6 AM UTC
ingestion_schedule = ScheduleDefinition(
    name="weekly_ingestion_schedule",
    cron_schedule="0 6 * * 1",
    job=full_pipeline_job,
)

# ---------------------------------------------------------------------------
# Sensors
# ---------------------------------------------------------------------------

@sensor(
    job=post_ingestion_job,
    minimum_interval_seconds=3600,
)
def gcs_new_file_sensor(context):
    """
    Watches the raw StatsBomb GCS bucket for new match files.
    When new data lands (e.g. manual upload between weekly runs),
    triggers the post-ingestion pipeline: dbt → ML → mart refresh.
    Does NOT re-run ingestion to avoid an infinite trigger loop.
    """
    bucket_name = os.getenv("INGESTION_GCS_BUCKET")
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


# ---------------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------------

defs = Definitions(
    assets=[
        raw_statsbomb,
        raw_polymarket,
        football_analytics_dbt_assets,
        cluster_assignments,
        consistency_score,
        dbt_mart_refresh,
    ],
    jobs=[full_pipeline_job, post_ingestion_job],
    schedules=[ingestion_schedule],
    sensors=[gcs_new_file_sensor],
    resources={
        "dbt": DbtCliResource(project_dir=str(DBT_PROJECT_DIR)),
    },
)
