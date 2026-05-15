from dagster import asset, Output, MetadataValue, AssetKey
import subprocess

@asset(
    group_name="ingestion",
    description="Runs StatsBomb incremental ingestion: API -> Parquet -> GCS -> BigQuery",
    metadata={
        "gcs_bucket": MetadataValue.text("gs://football-analytics-mds2026/raw/statsbomb/"),
        "bq_dataset": MetadataValue.text("football-capstone-mds-495504.raw_statsbomb"),
    }
)
def raw_statsbomb():
    result = subprocess.run(
        ["python", "src/ingestion/statsbomb.py"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise Exception(f"Ingestion failed:\n{result.stderr}")
    return Output(
        value=None,
        metadata={"stdout": MetadataValue.text(result.stdout)}
    )

@asset(
    group_name="ingestion",
    description="Uploads Polymarket parquet files from GCS to BigQuery",
    metadata={
        "bq_dataset": MetadataValue.text("football-capstone-mds-495504.raw_polymarket"),
    }
)
def raw_polymarket():
    result = subprocess.run(
        ["python", "src/ingestion/upload_gcs.py"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise Exception(f"Polymarket upload failed:\n{result.stderr}")
    return Output(value=None)