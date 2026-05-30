"""Cluster players with PCA + KMeans on per-90 stats from int_player_season_stats.

Features and preprocessing match Li's pca_loadings.parquet exactly:
- 13 per-90 features (aligned to int_player_season_stats after PR #124)
- Median imputation for nulls
- 99th percentile outlier clipping
- StandardScaler -> PCA (80% variance threshold) -> KMeans k=5

Writes cluster_assignments and pca_loadings to GCS and BigQuery analytics dataset.
"""
import os
import tempfile

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery, storage
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

load_dotenv()

PROJECT_ID           = os.getenv("GCP_PROJECT_ID", "football-capstone-mds-496219")
BUCKET_NAME          = os.getenv("ML_GCS_BUCKET", "football-analytics-mds496219")
INTERMEDIATE_DATASET = os.getenv("DBT_INTERMEDIATE_DATASET", "dbt_intermediate")
TARGET_DATASET       = os.getenv("ML_BQ_DATASET", "analytics")
SOURCE_TABLE         = f"{PROJECT_ID}.{INTERMEDIATE_DATASET}.int_player_season_stats"
GCS_PREFIX           = "models/clustering"

# 13 features aligned to Li's pca_loadings.parquet and int_player_season_stats
FEATURES = [
    "xg_per_90",
    "shots_per_90",
    "passes_per_90",
    "passes_att_third_per_90",
    "pressures_per_90",
    "carries_per_90",
    "dribbles_per_90",
    "interceptions_per_90",
    "blocks_per_90",
    "clearances_per_90",
    "duels_per_90",
    "xg_per_shot",
    "pass_completion_pct",
]

N_CLUSTERS   = 5
RANDOM_STATE = 42

# Archetypes aligned to Li's notebook archetype_map (outfield only; GK handled separately)
CLUSTER_LABELS = {
    0: "Low Activity",
    1: "Creative Winger",
    2: "Creative Playmaker",
    3: "Defensive Anchor",
    4: "Pressing Forward",
}


def fetch_player_features(bq_client: bigquery.Client) -> pd.DataFrame:
    sql = f"""
        SELECT
            player_id,
            player_name,
            competition_id,
            season_id,
            total_minutes,
            xg_per_90,
            shots_per_90,
            passes_per_90,
            passes_att_third_per_90,
            pressures_per_90,
            carries_per_90,
            dribbles_per_90,
            interceptions_per_90,
            blocks_per_90,
            clearances_per_90,
            duels_per_90,
            xg_per_shot,
            pass_completion_pct
        FROM `{SOURCE_TABLE}`
    """
    print(f"Querying {SOURCE_TABLE}")
    return bq_client.query(sql).to_dataframe()


def preprocess(df: pd.DataFrame) -> np.ndarray:
    """Median imputation -> 99th-pct clipping -> StandardScaler (matches notebook)."""
    X = df[FEATURES].copy()

    # Median imputation
    null_counts = X.isna().sum()
    if null_counts.any():
        print("Null counts before imputation:")
        print(null_counts[null_counts > 0])
    X = X.fillna(X.median())

    # Clip outliers at 99th percentile
    for col in X.columns:
        cap = X[col].quantile(0.99)
        X[col] = X[col].clip(upper=cap)

    return StandardScaler().fit_transform(X)


def run_clustering(df: pd.DataFrame, X_scaled: np.ndarray):
    # PCA: use enough components to explain 80%+ variance
    pca_full = PCA(random_state=RANDOM_STATE)
    pca_full.fit(X_scaled)
    cumvar = pca_full.explained_variance_ratio_.cumsum()
    n_components = int((cumvar >= 0.80).argmax() + 1)
    print(f"Using {n_components} PCA components ({cumvar[n_components-1]:.1%} variance)")

    pca = PCA(n_components=n_components, random_state=RANDOM_STATE)
    X_pca = pca.fit_transform(X_scaled)

    # Always keep 2D projection for visualization
    pca_2d = PCA(n_components=2, random_state=RANDOM_STATE)
    X_2d = pca_2d.fit_transform(X_scaled)

    # KMeans
    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=10)
    cluster_ids = kmeans.fit_predict(X_pca)

    # Build cluster_assignments
    assignments = df[
        ["player_id", "player_name", "competition_id", "season_id", "total_minutes"]
    ].copy()
    assignments["cluster"]   = cluster_ids.astype("int64")
    assignments["archetype"] = assignments["cluster"].map(CLUSTER_LABELS)
    assignments["pc1"]       = X_2d[:, 0]
    assignments["pc2"]       = X_2d[:, 1]

    print(f"\nCluster sizes:\n{assignments['cluster'].value_counts().sort_index()}")

    # Build pca_loadings (long format for BigQuery)
    loadings_wide = pd.DataFrame(
        pca.components_,
        columns=FEATURES,
        index=[f"PC{i+1}" for i in range(n_components)],
    ).reset_index().rename(columns={"index": "component"})
    loadings = loadings_wide.melt(
        id_vars="component", var_name="feature", value_name="loading"
    )

    return assignments, loadings


def upload_to_gcs(storage_client: storage.Client, local_path: str, gcs_path: str):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(local_path)
    print(f"Uploaded {local_path} -> gs://{BUCKET_NAME}/{gcs_path}")


def load_to_bigquery(bq_client: bigquery.Client, gcs_uri: str, table_name: str):
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
    bq_client      = bigquery.Client(project=PROJECT_ID)
    storage_client = storage.Client(project=PROJECT_ID)

    df = fetch_player_features(bq_client)
    print(f"Fetched {len(df)} player-season rows")

    X_scaled = preprocess(df)
    assignments, loadings = run_clustering(df, X_scaled)

    with tempfile.TemporaryDirectory() as tmp:
        assignments_local = os.path.join(tmp, "cluster_assignments.parquet")
        loadings_local    = os.path.join(tmp, "pca_loadings.parquet")
        assignments.to_parquet(assignments_local, index=False)
        loadings.to_parquet(loadings_local, index=False)

        assignments_gcs = f"{GCS_PREFIX}/cluster_assignments.parquet"
        loadings_gcs    = f"{GCS_PREFIX}/pca_loadings.parquet"
        upload_to_gcs(storage_client, assignments_local, assignments_gcs)
        upload_to_gcs(storage_client, loadings_local, loadings_gcs)

        load_to_bigquery(
            bq_client,
            f"gs://{BUCKET_NAME}/{assignments_gcs}",
            "cluster_assignments",
        )
        load_to_bigquery(
            bq_client,
            f"gs://{BUCKET_NAME}/{loadings_gcs}",
            "pca_loadings",
        )


if __name__ == "__main__":
    main()
    print("Done.")
