import os
from datetime import date
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BUCKET_NAME = "football-analytics-mds2026"
DATASET = "raw_statsbomb"
DATE_PREFIX = date.today().strftime("%Y-%m-%d")


def load_table(client, gcs_uri, table_name):
    table_ref = f"{PROJECT_ID}.{DATASET}.{table_name}"
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )
    print(f"Loading {gcs_uri} -> {table_ref}")
    job = client.load_table_from_uri(gcs_uri, table_ref, job_config=job_config)
    job.result()  # wait for job to finish
    table = client.get_table(table_ref)
    print(f"Loaded {table.num_rows} rows into {table_ref}")


def load_all():
    client = bigquery.Client(project=PROJECT_ID)

    tables = {
        f"gs://{BUCKET_NAME}/raw/statsbomb/matches/{DATE_PREFIX}/matches.parquet": "matches",
        f"gs://{BUCKET_NAME}/raw/statsbomb/events/{DATE_PREFIX}/events.parquet": "events",
        f"gs://{BUCKET_NAME}/raw/statsbomb/lineups/{DATE_PREFIX}/lineups.parquet": "lineups",
    }

    for gcs_uri, table_name in tables.items():
        load_table(client, gcs_uri, table_name)


if __name__ == "__main__":
    load_all()
    print("Done. All tables loaded into BigQuery.")
