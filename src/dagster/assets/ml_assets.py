import subprocess
from dagster import asset, Output, MetadataValue, AssetKey


@asset(
    group_name="ml",
    description="Runs PCA + KMeans clustering on int_player_season_stats. Exports cluster_assignments and pca_loadings to GCS and BigQuery analytics dataset.",
    metadata={
        "bq_table": MetadataValue.text("analytics.cluster_assignments"),
        "gcs_path": MetadataValue.text("gs://football-analytics-mds496219/models/clustering/"),
    }
)
def cluster_assignments():
    result = subprocess.run(
        ["python", "src/ml/cluster.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise Exception(f"Clustering failed:\n{result.stderr}")
    return Output(
        value=None,
        metadata={"stdout": MetadataValue.text(result.stdout)}
    )


@asset(
    group_name="ml",
    deps=[
        AssetKey(["int_player_club_vs_national"]),
        AssetKey(["cluster_assignments"]),
    ],
    description=(
        "Runs club-vs-national consistency scoring on int_player_club_vs_national "
        "using PCA feature weights from analytics.pca_loadings. "
        "Exports consistency_scores to GCS and BigQuery analytics dataset."
    ),
    metadata={
        "bq_table": MetadataValue.text("analytics.consistency_scores"),
        "gcs_path": MetadataValue.text("gs://football-analytics-mds496219/models/consistency/"),
    }
)
def consistency_score():
    result = subprocess.run(
        ["python", "src/ml/consistency.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise Exception(f"Consistency scoring failed:\n{result.stderr}")
    return Output(
        value=None,
        metadata={"stdout": MetadataValue.text(result.stdout)}
    )
