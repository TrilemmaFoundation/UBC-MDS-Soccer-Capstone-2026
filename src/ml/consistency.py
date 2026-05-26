"""Compute club-vs-national consistency scores and export to GCS + BigQuery.

Pipeline:
- Read player-context rows from int_player_club_vs_national (has is_international;
  int_player_season_stats does not — same source as notebooks/03_consistency_score.ipynb).
- Keep players with >=270 minutes in both contexts (club and national).
- Derive PCA feature weights from analytics.pca_loadings.
- Weighted performance scores from dbt per-context z-scores (z_*).
- consistency_score = 1 - mean(|z_club - z_nat|) across features (notebook).
- Quadrants from median splits on club vs national performance scores.
- Export parquet to GCS and load analytics.consistency_scores in BigQuery.
"""

import os
import tempfile

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery, storage

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "football-capstone-mds-496219")
BUCKET_NAME = os.getenv("ML_GCS_BUCKET", "football-analytics-mds496219")
TARGET_DATASET = os.getenv("ML_BQ_DATASET", "analytics")
SOURCE_DATASET = os.getenv("CONSISTENCY_SOURCE_DATASET", "raw_statsbomb_intermediate")
SOURCE_TABLE = f"{PROJECT_ID}.{SOURCE_DATASET}.int_player_club_vs_national"
PCA_LOADINGS_TABLE = f"{PROJECT_ID}.{TARGET_DATASET}.pca_loadings"
MIN_MINUTES = 270
GCS_OBJECT = "models/consistency/consistency_scores.parquet"

# Keep in sync with clustering feature space / pca_loadings.
FEATURES = [
    "shots_per_90",
    "xg_per_90",
    "xg_per_shot",
    "dribbles_per_90",
    "carries_att_third_per_90",
    "passes_att_third_per_90",
    "pass_completion_pct",
    "pressures_per_90",
    "interceptions_per_90",
    "clearances_per_90",
    "aerial_duels_per_90",
]

Z_COLS = [f"z_{f}" for f in FEATURES]


def fetch_context_rows(bq_client: bigquery.Client) -> pd.DataFrame:
    sql = f"""
        SELECT
            player_id,
            player_name,
            is_international,
            total_minutes,
            {", ".join(Z_COLS)}
        FROM `{SOURCE_TABLE}`
    """
    print(f"Querying {SOURCE_TABLE}")
    return bq_client.query(sql).to_dataframe()


def normalize_is_international(value) -> bool:
    """Map bool/int/string-like values to True (national) / False (club)."""
    if pd.isna(value):
        raise ValueError("is_international is null.")
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        if int(value) in (0, 1):
            return bool(value)
    s = str(value).strip().lower()
    if s in ("true", "1", "t", "yes", "national"):
        return True
    if s in ("false", "0", "f", "no", "club"):
        return False
    raise ValueError(f"Unrecognized is_international value: {value!r}")


def filter_dual_context(players: pd.DataFrame) -> pd.DataFrame:
    players = players.copy()
    players["is_international"] = players["is_international"].apply(normalize_is_international)
    players = players.loc[players["total_minutes"] >= MIN_MINUTES].copy()

    context_counts = players.groupby("player_id")["is_international"].nunique()
    dual_ids = context_counts.loc[context_counts == 2].index
    players = players.loc[players["player_id"].isin(dual_ids)].copy()

    # If multiple rows exist within a player-context, keep the highest-minute row.
    players = players.sort_values("total_minutes", ascending=False)
    players = players.drop_duplicates(subset=["player_id", "is_international"], keep="first")
    return players.reset_index(drop=True)


def fetch_feature_weights(bq_client: bigquery.Client) -> pd.Series:
    sql = f"SELECT component, feature, loading FROM `{PCA_LOADINGS_TABLE}`"
    loadings = bq_client.query(sql).to_dataframe()
    print(f"Queried {len(loadings)} loading rows from {PCA_LOADINGS_TABLE}")

    missing = set(FEATURES) - set(loadings["feature"].unique())
    if missing:
        raise ValueError(f"pca_loadings missing required features: {sorted(missing)}")

    weights = (
        loadings.loc[loadings["feature"].isin(FEATURES)]
        .groupby("feature")["loading"]
        .apply(lambda s: s.abs().sum())
    )
    denom = float(weights.sum())
    if denom == 0:
        raise ValueError("All feature loading weights are zero.")
    weights = weights / denom
    return weights


def compute_scores(players: pd.DataFrame, weights: pd.Series) -> pd.DataFrame:
    df = players.copy()

    # dbt z-scores; NULL / zero-weight * NaN would poison sums — neutralize missing z as 0.
    df[Z_COLS] = df[Z_COLS].apply(pd.to_numeric, errors="coerce").fillna(0.0)

    weight_vec = np.array([weights[f] for f in FEATURES], dtype=float)
    z_matrix = df[Z_COLS].to_numpy(dtype=float)
    df["performance_score"] = (z_matrix * weight_vec).sum(axis=1)

    club = (
        df.loc[~df["is_international"], ["player_id", "player_name", "performance_score", "total_minutes"]]
        .rename(
            columns={
                "performance_score": "club_performance_score",
                "total_minutes": "club_minutes",
            }
        )
    )
    national = (
        df.loc[df["is_international"], ["player_id", "player_name", "performance_score", "total_minutes"]]
        .rename(
            columns={
                "performance_score": "national_performance_score",
                "total_minutes": "national_minutes",
            }
        )
    )

    scores = club.merge(
        national.drop(columns=["player_name"]),
        on="player_id",
        how="inner",
        validate="one_to_one",
    )

    # Notebook: 1 - mean(|z_club - z_nat|) across FEATURES
    club_z = df.loc[~df["is_international"]].set_index("player_id")[Z_COLS]
    nat_z = df.loc[df["is_international"]].set_index("player_id")[Z_COLS]
    common_ids = club_z.index.intersection(nat_z.index)
    z_gap = (club_z.loc[common_ids] - nat_z.loc[common_ids]).abs().mean(axis=1)
    scores["consistency_score"] = scores["player_id"].map(1.0 - z_gap)

    club_med = scores["club_performance_score"].median()
    nat_med = scores["national_performance_score"].median()
    high_club = scores["club_performance_score"] >= club_med
    high_nat = scores["national_performance_score"] >= nat_med
    scores["performance_quadrant"] = np.select(
        [
            high_club & high_nat,
            high_club & ~high_nat,
            ~high_club & high_nat,
        ],
        [
            "Elite",
            "Club Specialist",
            "International Specialist",
        ],
        default="Underperformer",
    )

    out_cols = [
        "player_id",
        "player_name",
        "club_performance_score",
        "national_performance_score",
        "consistency_score",
        "performance_quadrant",
        "club_minutes",
        "national_minutes",
    ]
    return scores[out_cols].sort_values("consistency_score", ascending=True).reset_index(drop=True)


def upload_to_gcs(storage_client: storage.Client, local_path: str, gcs_path: str):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(local_path)
    print(f"Uploaded {local_path} -> gs://{BUCKET_NAME}/{gcs_path}")


def load_to_bigquery(bq_client: bigquery.Client, gcs_uri: str):
    table_ref = f"{PROJECT_ID}.{TARGET_DATASET}.consistency_scores"
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

    raw = fetch_context_rows(bq_client)
    print(f"Fetched {len(raw)} context rows")
    players = filter_dual_context(raw)
    print(f"Eligible dual-context players: {players['player_id'].nunique()}")
    if players.empty:
        raise ValueError("No dual-context players found after filtering.")

    weights = fetch_feature_weights(bq_client)
    print("Feature weights:")
    print(weights.sort_values(ascending=False))

    scores = compute_scores(players, weights)
    print(f"Computed {len(scores)} consistency scores")
    print(scores["performance_quadrant"].value_counts(dropna=False))

    with tempfile.TemporaryDirectory() as tmp:
        local_path = os.path.join(tmp, "consistency_scores.parquet")
        scores.to_parquet(local_path, index=False)
        upload_to_gcs(storage_client, local_path, GCS_OBJECT)
        load_to_bigquery(bq_client, f"gs://{BUCKET_NAME}/{GCS_OBJECT}")


if __name__ == "__main__":
    main()
    print("Done.")
