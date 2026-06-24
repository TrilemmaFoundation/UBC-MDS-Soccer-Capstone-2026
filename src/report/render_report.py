#!/usr/bin/env python3
"""Render the final report PDF from committed results/report/metrics.json.

Does not query BigQuery or rewrite metrics. Use export_metrics.py first if
results/report/ is missing or stale.

Usage (from repository root):
  python src/report/render_report.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
METRICS_PATH = REPO_ROOT / "results" / "report" / "metrics.json"
REPORT_DIR = REPO_ROOT / "report"
QMD = REPORT_DIR / "final_report.qmd"


def main() -> int:
    if not METRICS_PATH.exists():
        print(
            f"Missing {METRICS_PATH.relative_to(REPO_ROOT)}.\n"
            "Run: python src/report/export_metrics.py",
            file=sys.stderr,
        )
        return 1

    print(f"Rendering {QMD.relative_to(REPO_ROOT)} (using committed metrics)")
    result = subprocess.run(
        ["quarto", "render", "final_report.qmd", "--to", "pdf"],
        cwd=REPORT_DIR,
    )
    if result.returncode == 0:
        print(f"Wrote {REPORT_DIR / 'final_report.pdf'}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
