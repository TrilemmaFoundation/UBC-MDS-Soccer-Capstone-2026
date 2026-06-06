import os
import subprocess

from dagster import Output, MetadataValue, asset
from dotenv import load_dotenv

load_dotenv()

_ingestion_bucket = os.getenv("INGESTION_GCS_BUCKET", "")
_project_id = os.getenv("GCP_PROJECT_ID", "")


@asset(
    group_name="ingestion",
    description=(
        "Runs the full StatsBomb ingestion pipeline: "
        "StatsBomb API → local Parquet (statsbomb.py) → "
        "GCS (upload_gcs.py) → BigQuery raw_statsbomb (load_bq.py). "
        "Uses paid API if SB_USERNAME/SB_PASSWORD are set, otherwise falls back to open data."
    ),
    metadata={
        "gcs_bucket": MetadataValue.text(f"gs://{_ingestion_bucket}/raw/statsbomb/"),
        "bq_dataset": MetadataValue.text(f"{_project_id}.raw_statsbomb"),
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
        f"Upload parquet files manually to gs://{_ingestion_bucket}/raw/polymarket/ "
        "and load them to BigQuery raw_polymarket before running downstream models."
    ),
    metadata={
        "bq_dataset": MetadataValue.text(f"{_project_id}.raw_polymarket"),
        "status": MetadataValue.text("manual upload required — no automated ingestion script yet"),
    }
)
def raw_polymarket():
    ingestion_bucket = os.getenv("INGESTION_GCS_BUCKET", "")
    print(
        f"WARNING: raw_polymarket has no automated ingestion script. "
        f"Data must be uploaded to gs://{ingestion_bucket}/raw/polymarket/ "
        f"and loaded to BigQuery manually."
    )
    return Output(
        value=None,
        metadata={
            "note": MetadataValue.text(
                "Manual upload required — no automated polymarket ingestion script."
            )
        }
    )
