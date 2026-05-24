import subprocess
from dagster import asset, Output, MetadataValue

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
