"""Tests for src/report/export_metrics.py."""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results" / "report"


def test_from_cache_rebuilds_metrics_json():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "src" / "report" / "export_metrics.py"), "--from-cache"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    metrics = json.loads((RESULTS_DIR / "metrics.json").read_text())
    assert metrics["n_player_seasons"] == 5759
    assert metrics["n_dual_context_players"] == 489
    assert sum(metrics["archetype_counts"].values()) == 5759
    assert sum(metrics["quadrant_counts"].values()) == 489
