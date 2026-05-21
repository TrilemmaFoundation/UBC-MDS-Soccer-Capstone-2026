"""Cluster players with PCA + KMeans on per-90 stats from int_player_season_stats.

Writes cluster_assignments and pca_loadings parquet to GCS, then loads both into
BigQuery under the analytics dataset.
"""
import os
import tempfile

import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery, storage
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "football-capstone-mds-496219")
BUCKET_NAME = os.getenv("ML_GCS_BUCKET", "football-analytics-mds496219")
INTERMEDIATE_DATASET = os.getenv("DBT_INTERMEDIATE_DATASET", "dbt_intermediate")
TARGET_DATASET = os.getenv("ML_BQ_DATASET", "analytics")
SOURCE_TABLE = f"{PROJECT_ID}.{INTERMEDIATE_DATASET}.int_player_season_stats"
GCS_PREFIX = "models/clustering"

FEATURES = [
    "goals_per_90",
    "xg_per_90",
    "xg_per_shot",
    "passes_attempted_per_90",
    "pass_completion_pct",
    "pressures_per_90",
    "tackles_per_90",
    "interceptions_per_90",
    "carries_per_90",
]

N_COMPONENTS = 2
N_CLUSTERS = 6
RANDOM_STATE = 42


def fetch_player_features(bq_client):
    sql = f"""
        SELECT
            player_id,
            player_name,
            competition_id,
            season_id,
            total_minutes,
            goals_per_90,
            xg_per_90,
            SAFE_DIVIDE(total_xg, total_shots) AS xg_per_shot,
            passes_attempted_per_90,
            pass_completion_pct,
            pressures_per_90,
            tackles_per_90,
            interceptions_per_90,
            carries_per_90
        FROM `{SOURCE_TABLE}`
    """
    print(f"Querying {SOURCE_TABLE}")
    return bq_client.query(sql).to_dataframe()


def run_clustering(df):
    # TODO: filling missing features with zero biases clustering toward the origin
    # (zero-shot players look like the "average" cluster centroid in scaled space).
    # Before production use, replace with per-feature median imputation or filter
    # rows with NaN in any feature explicitly.
    feature_matrix = df[FEATURES].fillna(0.0).to_numpy()
    scaled = StandardScaler().fit_transform(feature_matrix)

    pca = PCA(n_components=N_COMPONENTS, random_state=RANDOM_STATE)
    components = pca.fit_transform(scaled)

    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=10)
    cluster_ids = kmeans.fit_predict(scaled)

    assignments = df[
        ["player_id", "player_name", "competition_id", "season_id", "total_minutes"]
    ].copy()
    assignments["cluster"] = cluster_ids.astype("int64")
    assignments["archetype"] = [f"Cluster {c}" for c in cluster_ids]
    assignments["pc1"] = components[:, 0]
    assignments["pc2"] = components[:, 1]

    loadings_wide = pd.DataFrame(
        pca.components_,
        columns=FEATURES,
        index=[f"PC{i + 1}" for i in range(N_COMPONENTS)],
    ).reset_index().rename(columns={"index": "component"})
    loadings = loadings_wide.melt(
        id_vars="component", var_name="feature", value_name="loading"
    )

    return assignments, loadings


def upload_to_gcs(storage_client, local_path, gcs_path):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(local_path)
    print(f"Uploaded {local_path} -> gs://{BUCKET_NAME}/{gcs_path}")


def load_to_bigquery(bq_client, gcs_uri, table_name):
    table_ref = f"{PROJECT_ID}.{TARGET_DATASET}.{table_name}"
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )
    print(f"Loading {gcs_uri} -> {table_ref}")
    job = bq_client.load_table_from_uri(gcs_uri, table_ref, job_config=job_config)
    job.result()
    table = bq_client.get_table(table_ref)
    print(f"Loaded {table.num_rows} rows into {table_ref}")


def main():
    bq_client = bigquery.Client(project=PROJECT_ID)
    storage_client = storage.Client(project=PROJECT_ID)

    df = fetch_player_features(bq_client)
    print(f"Fetched {len(df)} player-season rows")

    assignments, loadings = run_clustering(df)

    with tempfile.TemporaryDirectory() as tmp:
        assignments_local = os.path.join(tmp, "cluster_assignments.parquet")
        loadings_local = os.path.join(tmp, "pca_loadings.parquet")
        assignments.to_parquet(assignments_local, index=False)
        loadings.to_parquet(loadings_local, index=False)

        assignments_gcs = f"{GCS_PREFIX}/cluster_assignments.parquet"
        loadings_gcs = f"{GCS_PREFIX}/pca_loadings.parquet"
        upload_to_gcs(storage_client, assignments_local, assignments_gcs)
        upload_to_gcs(storage_client, loadings_local, loadings_gcs)

        load_to_bigquery(
            bq_client, f"gs://{BUCKET_NAME}/{assignments_gcs}", "cluster_assignments"
        )
        load_to_bigquery(
            bq_client, f"gs://{BUCKET_NAME}/{loadings_gcs}", "pca_loadings"
        )


if __name__ == "__main__":
    main()
    print("Done.")
