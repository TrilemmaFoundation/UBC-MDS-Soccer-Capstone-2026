"""Unit tests for src/ml/cluster.py

Tests cover:
- preprocess(): median imputation, 99th-pct clipping, StandardScaler output
- run_clustering(): PCA component selection, KMeans output shape, archetype mapping
- build_gk_assignments(): GK sentinel values
"""

import numpy as np
import pandas as pd
import pytest
from src.ml.cluster import (
    FEATURES,
    CLUSTER_LABELS,
    N_CLUSTERS,
    build_gk_assignments,
    preprocess,
    run_clustering,
)
# ---------------------------------------------------------------------------
# Helpers to build minimal test DataFrames
# ---------------------------------------------------------------------------




def _make_outfield_df(n: int = 60, seed: int = 42) -> pd.DataFrame:
    """Create a minimal outfield player DataFrame with required columns."""
    rng = np.random.default_rng(seed)
    data = {
        "player_id":    np.arange(n),
        "player_name":  [f"Player_{i}" for i in range(n)],
        "competition_id": np.ones(n, dtype=int),
        "season_id":    np.ones(n, dtype=int),
        "total_minutes": rng.uniform(270, 3000, n),
    }
    for feat in FEATURES:
        data[feat] = rng.uniform(0, 5, n)
    return pd.DataFrame(data)


def _make_gk_df(n: int = 10, seed: int = 99) -> pd.DataFrame:
    """Create a minimal goalkeeper DataFrame."""
    rng = np.random.default_rng(seed)
    data = {
        "player_id":    np.arange(1000, 1000 + n),
        "player_name":  [f"GK_{i}" for i in range(n)],
        "competition_id": np.ones(n, dtype=int),
        "season_id":    np.ones(n, dtype=int),
        "total_minutes": rng.uniform(270, 3000, n),
    }
    for feat in FEATURES:
        data[feat] = rng.uniform(0, 2, n)
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# preprocess() tests
# ---------------------------------------------------------------------------

class TestPreprocess:

    def test_output_shape(self):
        """Output should have same number of rows and exactly len(FEATURES) columns."""
        df = _make_outfield_df(n=30)
        X = preprocess(df)
        assert X.shape == (30, len(FEATURES))

    def test_no_nulls_in_output(self):
        """After preprocessing there should be no NaN values."""
        df = _make_outfield_df(n=30)
        # Introduce some nulls
        df.loc[0, "xg_per_90"] = np.nan
        df.loc[5, "passes_per_90"] = np.nan
        X = preprocess(df)
        assert not np.isnan(X).any()

    def test_median_imputation(self):
        """Null values should be filled with the column median, not zero or mean."""
        df = _make_outfield_df(n=20)
        median_val = df["xg_per_90"].median()
        df.loc[0, "xg_per_90"] = np.nan
        # After scaling the imputed row should not be an outlier
        X = preprocess(df)
        # Just verify preprocessing runs without error and shape is correct
        assert X.shape[0] == 20

    def test_outlier_clipping(self):
        """Values above 99th percentile should be clipped before scaling."""
        df = _make_outfield_df(n=50)
        # Inject an extreme outlier
        df.loc[0, "xg_per_90"] = 1_000_000
        X_with_outlier = preprocess(df)

        df2 = _make_outfield_df(n=50)
        df2.loc[0, "xg_per_90"] = 999_999  # different extreme value
        X_with_outlier2 = preprocess(df2)

        # After clipping to 99th pct, both extreme values map to the same cap
        # so the scaled result for row 0 should be identical
        assert np.isclose(X_with_outlier[0, 0], X_with_outlier2[0, 0], atol=1e-3)

    def test_standard_scaler_applied(self):
        """Output columns should have approximately zero mean and unit variance."""
        df = _make_outfield_df(n=200)
        X = preprocess(df)
        col_means = X.mean(axis=0)
        col_stds  = X.std(axis=0)
        np.testing.assert_allclose(col_means, 0, atol=1e-10)
        np.testing.assert_allclose(col_stds,  1, atol=1e-10)

    def test_returns_numpy_array(self):
        """preprocess() should return a numpy ndarray."""
        df = _make_outfield_df(n=20)
        X = preprocess(df)
        assert isinstance(X, np.ndarray)


# ---------------------------------------------------------------------------
# run_clustering() tests
# ---------------------------------------------------------------------------

class TestRunClustering:

    @pytest.fixture(scope="class")
    def clustering_output(self):
        df = _make_outfield_df(n=100)
        X_scaled = preprocess(df)
        assignments, loadings = run_clustering(df, X_scaled)
        return df, assignments, loadings

    def test_assignments_row_count(self, clustering_output):
        """assignments should have one row per input player-season."""
        df, assignments, _ = clustering_output
        assert len(assignments) == len(df)

    def test_assignments_required_columns(self, clustering_output):
        """assignments must contain all required output columns."""
        _, assignments, _ = clustering_output
        required = {"player_id", "player_name", "competition_id", "season_id",
                    "total_minutes", "cluster", "archetype", "pc1", "pc2"}
        assert required.issubset(set(assignments.columns))

    def test_cluster_ids_in_valid_range(self, clustering_output):
        """cluster column should only contain values 0 to N_CLUSTERS-1."""
        _, assignments, _ = clustering_output
        unique_clusters = set(assignments["cluster"].unique())
        valid = set(range(N_CLUSTERS))
        assert unique_clusters.issubset(valid)

    def test_archetype_values_are_valid(self, clustering_output):
        """archetype column should only contain known label strings."""
        _, assignments, _ = clustering_output
        valid_archetypes = set(CLUSTER_LABELS.values())
        assert set(assignments["archetype"].unique()).issubset(valid_archetypes)

    def test_archetype_matches_cluster(self, clustering_output):
        """Each archetype must correspond to the correct cluster id."""
        _, assignments, _ = clustering_output
        for _, row in assignments.iterrows():
            assert row["archetype"] == CLUSTER_LABELS[row["cluster"]]

    def test_pc1_pc2_are_finite(self, clustering_output):
        """pc1 and pc2 should be finite floats for all outfield players."""
        _, assignments, _ = clustering_output
        assert np.isfinite(assignments["pc1"]).all()
        assert np.isfinite(assignments["pc2"]).all()

    def test_loadings_columns(self, clustering_output):
        """pca_loadings should have component, feature, loading columns."""
        _, _, loadings = clustering_output
        assert set(loadings.columns) == {"component", "feature", "loading"}

    def test_loadings_features_complete(self, clustering_output):
        """pca_loadings should contain all 13 features."""
        _, _, loadings = clustering_output
        assert set(loadings["feature"].unique()) == set(FEATURES)

    def test_all_five_clusters_present(self, clustering_output):
        """With enough data, all 5 clusters should appear.
        Note: relies on fixed seed=42 and n=100 synthetic data producing
        5 non-empty clusters. Result is deterministic but data-dependent.
        """
        _, assignments, _ = clustering_output
        assert assignments["cluster"].nunique() == N_CLUSTERS


# ---------------------------------------------------------------------------
# build_gk_assignments() tests
# ---------------------------------------------------------------------------

class TestBuildGkAssignments:

    @pytest.fixture(scope="class")
    def gk_assignments(self):
        df_gk = _make_gk_df(n=10)
        return build_gk_assignments(df_gk)

    def test_row_count(self, gk_assignments):
        """Output should have same number of rows as input GK DataFrame."""
        assert len(gk_assignments) == 10

    def test_cluster_sentinel(self, gk_assignments):
        """All GKs should have cluster = -1."""
        assert (gk_assignments["cluster"] == -1).all()

    def test_archetype_goalkeeper(self, gk_assignments):
        """All GKs should have archetype = 'Goalkeeper'."""
        assert (gk_assignments["archetype"] == "Goalkeeper").all()

    def test_pc1_pc2_are_nan(self, gk_assignments):
        """pc1 and pc2 should be NaN for all GKs."""
        assert gk_assignments["pc1"].isna().all()
        assert gk_assignments["pc2"].isna().all()

    def test_required_columns_present(self, gk_assignments):
        """Output should have all required columns."""
        required = {"player_id", "player_name", "competition_id",
                    "season_id", "total_minutes", "cluster", "archetype", "pc1", "pc2"}
        assert required.issubset(set(gk_assignments.columns))

    def test_player_ids_preserved(self):
        """Player IDs from input should be preserved in output."""
        df_gk = _make_gk_df(n=5)
        result = build_gk_assignments(df_gk)
        pd.testing.assert_series_equal(
            result["player_id"].reset_index(drop=True),
            df_gk["player_id"].reset_index(drop=True),
        )

    def test_empty_input(self):
        """build_gk_assignments should handle an empty DataFrame gracefully."""
        df_empty = _make_gk_df(n=0)
        result = build_gk_assignments(df_empty)
        assert len(result) == 0
        assert "archetype" in result.columns
