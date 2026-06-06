import os
import shutil
import subprocess
from pathlib import Path

from dagster import asset, Output, MetadataValue, AssetKey
from dotenv import load_dotenv

load_dotenv()

# Project root — needed so subprocess dbt commands run from the right directory
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_ml_bucket = os.getenv("ML_GCS_BUCKET", "")


@asset(
    group_name="ml",
    description="Runs PCA + KMeans clustering on int_player_season_stats. Exports cluster_assignments and pca_loadings to GCS and BigQuery analytics dataset.",
    metadata={
        "bq_table": MetadataValue.text("analytics.cluster_assignments"),
        "gcs_path": MetadataValue.text(f"gs://{_ml_bucket}/models/clustering/"),
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
        "gcs_path": MetadataValue.text(f"gs://{_ml_bucket}/models/consistency/"),
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


@asset(
    group_name="ml",
    deps=[
        AssetKey(["cluster_assignments"]),
        AssetKey(["consistency_score"]),
    ],
    description=(
        "Refreshes mart_player_clusters and mart_player_performance after the ML scripts "
        "update analytics.cluster_assignments and analytics.consistency_scores. "
        "Closes the automation gap: marts now reflect the latest clustering run and "
        "consistency scores rather than the pre-ML snapshot."
    ),
    metadata={
        "bq_tables": MetadataValue.text(
            "dbt_marts.mart_player_clusters, dbt_marts.mart_player_performance"
        ),
    }
)
def dbt_mart_refresh():
    """Run dbt on the two marts that depend on ML outputs, after ML scripts complete."""
    dbt_bin = shutil.which("dbt") or "dbt"

    result = subprocess.run(
        [
            dbt_bin, "run",
            "--select", "mart_player_clusters mart_player_performance",
            "--project-dir", str(_PROJECT_ROOT),
        ],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
    )
    if result.returncode != 0:
        raise Exception(f"dbt mart refresh failed:\n{result.stderr}")
    return Output(
        value=None,
        metadata={"stdout": MetadataValue.text(result.stdout)}
    )
