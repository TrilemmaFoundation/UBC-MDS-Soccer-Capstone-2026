#!/usr/bin/env python3
"""Export reproducible report metrics from BigQuery to results/report/.

Writes:
  results/report/metrics.json
  results/report/csv/*.csv

Usage:
  python src/report/export_metrics.py
  python src/report/export_metrics.py --from-cache

Run from the repository root.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

import pandas as pd
from dotenv import load_dotenv

from report.load import CSV_DIR, METRICS_PATH, RESULTS_DIR, fmt_int, fmt_millions

MIN_MINUTES = 270

TOP5_COMPETITIONS = [
    "La Liga",
    "Serie A",
    "Ligue 1",
    "Premier League",
    "1. Bundesliga",
]

COMP_DISPLAY = {
    "La Liga": "La Liga",
    "Serie A": "Serie A",
    "Ligue 1": "Ligue 1",
    "Premier League": "Premier League",
    "English Premier League": "Premier League",
    "1. Bundesliga": "Bundesliga",
    "Bundesliga": "Bundesliga",
}


def fetch_from_bigquery(project_id: str, raw_dataset: str, intermediate: str, analytics: str) -> dict:
    from google.cloud import bigquery

    bq = bigquery.Client(project=project_id)

    archetype_df = bq.query(
        f"""
        SELECT archetype, COUNT(*) AS seasons
        FROM `{project_id}.{analytics}.cluster_assignments`
        GROUP BY archetype
        """
    ).to_dataframe()

    competition_df = bq.query(
        f"""
        SELECT
            pss.competition_name,
            ca.archetype,
            COUNT(*) AS seasons
        FROM `{project_id}.{analytics}.cluster_assignments` ca
        INNER JOIN `{project_id}.{intermediate}.int_player_season_stats` pss
            ON ca.player_id = pss.player_id
            AND ca.competition_id = pss.competition_id
            AND ca.season_id = pss.season_id
        WHERE ca.archetype != 'Goalkeeper'
          AND pss.competition_name IN ({", ".join(repr(c) for c in TOP5_COMPETITIONS)})
        GROUP BY pss.competition_name, ca.archetype
        """
    ).to_dataframe()

    quadrant_df = bq.query(
        f"""
        SELECT performance_quadrant AS quadrant, COUNT(*) AS players
        FROM `{project_id}.{analytics}.consistency_scores`
        GROUP BY performance_quadrant
        """
    ).to_dataframe()

    overview_row = bq.query(
        f"""
        SELECT
            (SELECT COUNT(*) FROM `{project_id}.{raw_dataset}.matches`) AS n_matches,
            (SELECT COUNT(*) FROM `{project_id}.{raw_dataset}.events`) AS n_events,
            (SELECT COUNT(*) FROM `{project_id}.{raw_dataset}.lineups`) AS n_lineups,
            (SELECT COUNT(DISTINCT pss.competition_id)
             FROM `{project_id}.{analytics}.cluster_assignments` ca
             INNER JOIN `{project_id}.{intermediate}.int_player_season_stats` pss
                ON ca.player_id = pss.player_id
                AND ca.competition_id = pss.competition_id
                AND ca.season_id = pss.season_id) AS n_competitions
        """
    ).to_dataframe().iloc[0]

    return {
        "archetype_distribution": archetype_df,
        "competition_archetype_counts": competition_df,
        "quadrant_distribution": quadrant_df,
        "data_overview": overview_row,
    }


def load_from_cache() -> dict:
    overview_df = pd.read_csv(CSV_DIR / "data_overview.csv").iloc[0]
    return {
        "archetype_distribution": pd.read_csv(CSV_DIR / "archetype_distribution.csv"),
        "competition_archetype_counts": pd.read_csv(CSV_DIR / "competition_archetype_counts.csv"),
        "quadrant_distribution": pd.read_csv(CSV_DIR / "quadrant_distribution.csv"),
        "data_overview": overview_df,
    }


def save_csv_exports(data: dict) -> None:
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    data["archetype_distribution"].to_csv(CSV_DIR / "archetype_distribution.csv", index=False)
    data["competition_archetype_counts"].to_csv(
        CSV_DIR / "competition_archetype_counts.csv", index=False
    )
    data["quadrant_distribution"].to_csv(CSV_DIR / "quadrant_distribution.csv", index=False)
    pd.DataFrame([data["data_overview"]]).to_csv(CSV_DIR / "data_overview.csv", index=False)


def build_competition_summary(competition_df: pd.DataFrame) -> list[dict]:
    rows = []
    league_totals: dict[str, int] = {}

    for comp in TOP5_COMPETITIONS:
        subset = competition_df[competition_df["competition_name"] == comp]
        counts = {row.archetype: int(row.seasons) for row in subset.itertuples(index=False)}
        league_totals[comp] = sum(counts.values())

    max_total = max(league_totals.values()) if league_totals else 0
    low_activity_pcts = {}
    pressing_counts = {}

    for comp in TOP5_COMPETITIONS:
        subset = competition_df[competition_df["competition_name"] == comp]
        counts = {row.archetype: int(row.seasons) for row in subset.itertuples(index=False)}
        total = league_totals[comp] or 1
        low_activity_pcts[comp] = counts.get("Low Activity", 0) / total
        pressing_counts[comp] = counts.get("Pressing Forward", 0)

    max_low_activity_pct = max(low_activity_pcts.values()) if low_activity_pcts else 0
    min_total = min(league_totals.values()) if league_totals else 0

    for comp in TOP5_COMPETITIONS:
        subset = competition_df[competition_df["competition_name"] == comp]
        counts = {row.archetype: int(row.seasons) for row in subset.itertuples(index=False)}
        if not counts:
            continue

        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        largest_name, largest_n = ranked[0]
        second_name, second_n = ranked[1] if len(ranked) > 1 else ("", 0)
        total = league_totals[comp]

        if total == max_total:
            pattern = f"Highest volume. {largest_name}s lead"
        elif low_activity_pcts[comp] == max_low_activity_pct:
            pattern = "Most Low Activity share among top five"
        elif total == min_total and pressing_counts[comp] >= 70:
            pattern = f"Smallest top-five sample. More Pressing Forward ({pressing_counts[comp]})"
        elif abs(largest_n - second_n) <= max(5, int(0.05 * total)):
            pattern = "Near-even top two clusters"
        else:
            pattern = "Similar anchor vs low-activity mix"

        rows.append(
            {
                "competition": COMP_DISPLAY.get(comp, comp),
                "largest": f"{largest_name} ({largest_n})",
                "second_largest": f"{second_name} ({second_n})" if second_name else "",
                "notable_pattern": pattern,
            }
        )

    return rows


def compute_metrics(data: dict) -> dict:
    archetype_df = data["archetype_distribution"].copy()
    archetype_df["seasons"] = archetype_df["seasons"].astype(int)
    counts = dict(zip(archetype_df["archetype"], archetype_df["seasons"]))

    n_player_seasons = int(archetype_df["seasons"].sum())
    n_outfield = n_player_seasons - counts.get("Goalkeeper", 0)

    quadrant_df = data["quadrant_distribution"].copy()
    quadrant_df["players"] = quadrant_df["players"].astype(int)
    quad_counts = dict(zip(quadrant_df["quadrant"], quadrant_df["players"]))
    n_dual_context = int(quadrant_df["players"].sum())

    elite_n = quad_counts.get("Elite", 0)
    under_n = quad_counts.get("Underperformer", 0)
    club_n = quad_counts.get("Club Specialist", 0)
    intl_n = quad_counts.get("International Specialist", 0)

    elite_pct = 100 * elite_n / n_dual_context if n_dual_context else 0
    under_pct = 100 * under_n / n_dual_context if n_dual_context else 0
    club_pct = 100 * club_n / n_dual_context if n_dual_context else 0
    intl_pct = 100 * intl_n / n_dual_context if n_dual_context else 0

    overview = data["data_overview"]
    n_matches = int(overview["n_matches"])
    n_events = int(overview["n_events"])
    n_lineups = int(overview["n_lineups"])
    n_competitions = int(overview["n_competitions"])

    return {
        "n_competitions": n_competitions,
        "n_matches": n_matches,
        "n_events": n_events,
        "n_lineups": n_lineups,
        "n_events_millions": round(n_events / 1_000_000, 1),
        "n_player_seasons": n_player_seasons,
        "n_outfield_player_seasons": n_outfield,
        "n_goalkeeper_seasons": counts.get("Goalkeeper", 0),
        "n_dual_context_players": n_dual_context,
        "min_minutes": MIN_MINUTES,
        "archetype_counts": counts,
        "quadrant_counts": quad_counts,
        "quadrant_shares": {
            "Elite": elite_pct,
            "Underperformer": under_pct,
            "Club Specialist": club_pct,
            "International Specialist": intl_pct,
        },
        "pct_elite": elite_pct,
        "pct_underperformer": under_pct,
        "pct_club_specialist": club_pct,
        "pct_international_specialist": intl_pct,
        "pct_single_context_specialist": club_pct + intl_pct,
        "competition_summary": build_competition_summary(data["competition_archetype_counts"]),
    }


def write_metrics_json(metrics: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")


def export_metrics(data: dict) -> dict:
    metrics = compute_metrics(data)
    write_metrics_json(metrics)
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Export final report metrics from BigQuery.")
    parser.add_argument(
        "--from-cache",
        action="store_true",
        help="Rebuild metrics.json from committed CSV exports (no BigQuery).",
    )
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")

    if args.from_cache:
        if not (CSV_DIR / "archetype_distribution.csv").exists():
            print("No cached CSV exports found. Run without --from-cache first.", file=sys.stderr)
            return 1
        data = load_from_cache()
    else:
        project_id = os.getenv("GCP_PROJECT_ID")
        if not project_id:
            print("GCP_PROJECT_ID is not set in .env", file=sys.stderr)
            return 1
        raw_dataset = os.getenv("INGESTION_BQ_DATASET", "raw_statsbomb")
        intermediate = os.getenv("DBT_INTERMEDIATE_DATASET", "dbt_intermediate")
        analytics = os.getenv("ML_BQ_DATASET", "analytics")
        try:
            data = fetch_from_bigquery(project_id, raw_dataset, intermediate, analytics)
        except Exception as exc:
            print(f"BigQuery export failed: {exc}", file=sys.stderr)
            print("Use --from-cache to rebuild from committed CSVs.", file=sys.stderr)
            return 1
        save_csv_exports(data)

    metrics = export_metrics(data)
    print(f"Wrote report metrics to {RESULTS_DIR}")
    print(f"  player-seasons: {fmt_int(metrics['n_player_seasons'])}")
    print(f"  dual-context players: {metrics['n_dual_context_players']:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
