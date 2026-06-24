"""Load exported report metrics and formatting helpers for Quarto inline code."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results" / "report"
METRICS_PATH = RESULTS_DIR / "metrics.json"
CSV_DIR = RESULTS_DIR / "csv"


def load_metrics() -> dict:
    with METRICS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def fmt_int(n: int) -> str:
    return f"{int(n):,}"


def fmt_pct(x: float, decimals: int = 1) -> str:
    return f"{float(x):.{decimals}f}%"


def fmt_millions(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} million"
    return str(n)


def pct_round(metrics: dict, key: str) -> str:
    return str(int(round(metrics[key])))
