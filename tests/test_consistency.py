"""Unit tests for club-vs-national consistency scoring (src/ml/consistency.py)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.ml.consistency import FEATURES, Z_COLS, compute_scores

EXPECTED_OUT_COLS = [
    "player_id",
    "player_name",
    "club_performance_score",
    "national_performance_score",
    "consistency_score",
    "performance_quadrant",
    "club_minutes",
    "national_minutes",
]


def _uniform_weights() -> pd.Series:
    w = 1.0 / len(FEATURES)
    return pd.Series({f: w for f in FEATURES})


def _player_rows(
    player_id: int,
    player_name: str,
    *,
    club_z: float,
    nat_z: float,
    club_minutes: int = 500,
    nat_minutes: int = 400,
) -> pd.DataFrame:
    """One player: constant z across all features in each context."""
    club = {z: club_z for z in Z_COLS}
    nat = {z: nat_z for z in Z_COLS}
    club_row = {
        "player_id": player_id,
        "player_name": player_name,
        "is_international": False,
        "total_minutes": club_minutes,
        **club,
    }
    nat_row = {
        "player_id": player_id,
        "player_name": player_name,
        "is_international": True,
        "total_minutes": nat_minutes,
        **nat,
    }
    return pd.DataFrame([club_row, nat_row])


def _quad_fixture() -> pd.DataFrame:
    """Four players with scores that map 1:1 to the four quadrants at median 2."""
    frames = [
        _player_rows(1, "Elite", club_z=4.0, nat_z=4.0),
        _player_rows(2, "Club Spec", club_z=4.0, nat_z=0.0),
        _player_rows(3, "Intl Spec", club_z=0.0, nat_z=4.0),
        _player_rows(4, "Under", club_z=0.0, nat_z=0.0),
    ]
    return pd.concat(frames, ignore_index=True)


def test_output_columns_and_shape():
    scores = compute_scores(_quad_fixture(), _uniform_weights())
    assert list(scores.columns) == EXPECTED_OUT_COLS
    assert len(scores) == 4
    assert scores["player_id"].is_unique


def test_performance_score_weighted_sum():
    weights = _uniform_weights()
    w_vec = np.array([weights[f] for f in FEATURES])
    # Non-uniform z across features: performance_score = dot(z, w)
    z_vals = np.linspace(-1.0, 1.0, num=len(FEATURES))
    club = {z: z_vals[i] for i, z in enumerate(Z_COLS)}
    players = pd.DataFrame(
        [
            {
                "player_id": 99,
                "player_name": "Dot Product",
                "is_international": False,
                "total_minutes": 300,
                **club,
            },
            {
                "player_id": 99,
                "player_name": "Dot Product",
                "is_international": True,
                "total_minutes": 300,
                **{z: 0.0 for z in Z_COLS},
            },
        ]
    )
    expected_club = float(np.dot(z_vals, w_vec))
    scores = compute_scores(players, weights)
    row = scores.loc[scores["player_id"] == 99].iloc[0]
    assert row["club_performance_score"] == pytest.approx(expected_club)
    assert row["national_performance_score"] == pytest.approx(0.0)


def test_performance_score_null_z_treated_as_zero():
    weights = _uniform_weights()
    players = _player_rows(7, "Missing Z", club_z=2.0, nat_z=1.0)
    players.loc[players["is_international"] & (players["player_id"] == 7), Z_COLS[0]] = np.nan
    scores = compute_scores(players, weights)
    row = scores.loc[scores["player_id"] == 7].iloc[0]
    # One missing national z (of 13) -> national score uses 12×1 + 0
    w = 1.0 / len(FEATURES)
    assert row["national_performance_score"] == pytest.approx(12 * w * 1.0)


def test_consistency_score_formula():
    weights = _uniform_weights()
    players = pd.concat(
        [
            _player_rows(1, "Perfect", club_z=1.5, nat_z=1.5),
            _player_rows(2, "Shifted", club_z=2.0, nat_z=0.0),
        ],
        ignore_index=True,
    )
    scores = compute_scores(players, weights)
    perfect = scores.loc[scores["player_id"] == 1, "consistency_score"].iloc[0]
    shifted = scores.loc[scores["player_id"] == 2, "consistency_score"].iloc[0]
    assert perfect == pytest.approx(1.0)
    assert shifted == pytest.approx(1.0 - 2.0)


def test_consistency_score_sorted_ascending():
    scores = compute_scores(_quad_fixture(), _uniform_weights())
    assert scores["consistency_score"].is_monotonic_increasing


def test_performance_quadrant_labels():
    scores = compute_scores(_quad_fixture(), _uniform_weights())
    by_name = scores.set_index("player_name")["performance_quadrant"]
    assert by_name["Elite"] == "Elite"
    assert by_name["Club Spec"] == "Club Specialist"
    assert by_name["Intl Spec"] == "International Specialist"
    assert by_name["Under"] == "Underperformer"
    assert set(scores["performance_quadrant"]) == {
        "Elite",
        "Club Specialist",
        "International Specialist",
        "Underperformer",
    }


def test_median_split_at_boundary_counts_as_high():
    """Scores equal to the cohort median are classified as high (>=)."""
    weights = _uniform_weights()
    # Two players only: medians are the average of the two values.
    players = pd.concat(
        [
            _player_rows(1, "High", club_z=3.0, nat_z=3.0),
            _player_rows(2, "Low", club_z=1.0, nat_z=1.0),
        ],
        ignore_index=True,
    )
    scores = compute_scores(players, weights)
    # medians = 2.0; player 1 has club=nat=3 -> Elite
    elite = scores.loc[scores["player_id"] == 1, "performance_quadrant"].iloc[0]
    under = scores.loc[scores["player_id"] == 2, "performance_quadrant"].iloc[0]
    assert elite == "Elite"
    assert under == "Underperformer"

    # Add a third player exactly at median on both axes
    players = pd.concat(
        [players, _player_rows(3, "Median", club_z=2.0, nat_z=2.0)],
        ignore_index=True,
    )
    scores = compute_scores(players, weights)
    median_row = scores.loc[scores["player_id"] == 3, "performance_quadrant"].iloc[0]
    assert median_row == "Elite"


def test_inner_merge_excludes_single_context_players():
    weights = _uniform_weights()
    dual = _player_rows(1, "Dual", club_z=1.0, nat_z=1.0)
    club_only = _player_rows(2, "Club only", club_z=1.0, nat_z=1.0).iloc[:1]
    scores = compute_scores(pd.concat([dual, club_only], ignore_index=True), weights)
    assert set(scores["player_id"]) == {1}
