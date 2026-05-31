from dagster import asset, Output, MetadataValue
import subprocess


@asset(
    group_name="ingestion",
    description=(
        "Runs the full StatsBomb ingestion pipeline: "
        "StatsBomb API → local Parquet (statsbomb.py) → "
        "GCS (upload_gcs.py) → BigQuery raw_statsbomb (load_bq.py)"
    ),
    metadata={
        "gcs_bucket": MetadataValue.text("gs://football-analytics-mds2026/raw/statsbomb/"),
        "bq_dataset": MetadataValue.text("football-capstone-mds-496219.raw_statsbomb"),
    }
)
def raw_statsbomb():
    steps = [
        ("extract",    ["python", "src/ingestion/statsbomb.py"]),
        ("upload_gcs", ["python", "src/ingestion/upload_gcs.py"]),
        ("load_bq",    ["python", "src/ingestion/load_bq.py"]),
    ]
    outputs = []
    for label, cmd in steps:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"StatsBomb ingestion step '{label}' failed:\n{result.stderr}")
        outputs.append(f"[{label}]\n{result.stdout}")
    return Output(
        value=None,
        metadata={"stdout": MetadataValue.text("\n".join(outputs))}
    )


@asset(
    group_name="ingestion",
    description=(
        "Placeholder: Polymarket ingestion is not yet automated. "
        "Upload parquet files manually to gs://football-analytics-mds2026/raw/polymarket/ "
        "and load them to BigQuery raw_polymarket before running downstream models."
    ),
    metadata={
        "bq_dataset": MetadataValue.text("football-capstone-mds-496219.raw_polymarket"),
        "status": MetadataValue.text("manual upload required — no automated ingestion script yet"),
    }
)
def raw_polymarket():
    print(
        "WARNING: raw_polymarket has no automated ingestion script. "
        "Data must be uploaded to GCS and loaded to BigQuery manually."
    )
    return Output(
        value=None,
        metadata={
            "note": MetadataValue.text(
                "Manual upload required — no automated polymarket ingestion script."
            )
        }
    )
