import os
from datetime import date
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BUCKET_NAME = os.getenv("INGESTION_GCS_BUCKET")
LOCAL_PARQUET_DIR = "data/parquet"
DATE_PREFIX = date.today().strftime("%Y-%m-%d")


def upload_file(client, local_path, gcs_path):
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(local_path)
    print(f"Uploaded {local_path} -> gs://{BUCKET_NAME}/{gcs_path}")


def upload_all():
    client = storage.Client(project=PROJECT_ID)

    files = {
        f"{LOCAL_PARQUET_DIR}/matches/matches.parquet": f"raw/statsbomb/matches/{DATE_PREFIX}/matches.parquet",
        f"{LOCAL_PARQUET_DIR}/events/events.parquet": f"raw/statsbomb/events/{DATE_PREFIX}/events.parquet",
        f"{LOCAL_PARQUET_DIR}/lineups/lineups.parquet": f"raw/statsbomb/lineups/{DATE_PREFIX}/lineups.parquet",
    }

    for local_path, gcs_path in files.items():
        if os.path.exists(local_path):
            upload_file(client, local_path, gcs_path)
        else:
            print(f"WARNING: {local_path} not found, skipping")


if __name__ == "__main__":
    upload_all()
    print("Done. Files uploaded to GCS.")
