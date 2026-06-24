"""Build report tables from exported metrics (used at Quarto render time)."""

from __future__ import annotations

from report.load import fmt_int, fmt_millions, fmt_pct, load_metrics

ARCHETYPE_ORDER = [
    "Low Activity",
    "Defensive Anchor",
    "Creative Playmaker",
    "Pressing Forward",
    "Creative Winger",
    "Goalkeeper",
]

TACTICAL_PROFILES = {
    "Low Activity": "Low volume across all metrics. Typical of squad players and limited roles",
    "Defensive Anchor": "High clearances, interceptions, duels. Low attacking output",
    "Creative Playmaker": "High pass completion, progressive passes, carries. Attacking midfielders",
    "Pressing Forward": "High pressures, shots, and xG. High-energy forwards and pressing wingers",
    "Creative Winger": "High dribbles, carries, shots. Direct wide attackers",
    "Goalkeeper": "Assigned by position. Excluded from K-Means",
}

QUADRANT_ORDER = [
    "Elite",
    "Underperformer",
    "Club Specialist",
    "International Specialist",
]


def archetype_table_tex() -> str:
    m = load_metrics()
    lines = [
        r"\begin{table}[htbp]",
        r"\caption{RQ1 archetype distribution across "
        + fmt_int(m["n_player_seasons"])
        + r" player-seasons. Outfield players receive K-Means labels and goalkeepers a fixed label. Low Activity is the largest archetype and Creative Winger the smallest outfield group.}",
        r"\label{tbl-cluster-dist}",
        r"\centering",
        r"\setlength{\tabcolsep}{4pt}",
        r"\renewcommand{\arraystretch}{1.05}",
        r"\begin{tabular}{@{}l r >{\raggedright\arraybackslash}p{0.58\linewidth}@{}}",
        r"\toprule",
        r"Archetype & Seasons & Tactical profile \\",
        r"\midrule",
    ]
    counts = m["archetype_counts"]
    for archetype in ARCHETYPE_ORDER:
        lines.append(
            f"{archetype} & {counts.get(archetype, 0):,} & {TACTICAL_PROFILES[archetype]} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def competition_table_tex() -> str:
    m = load_metrics()
    lines = [
        r"\begin{table}[htbp]",
        r"\caption{Outfield archetype counts by top-five European league (goalkeepers excluded). Defensive Anchor and Low Activity lead in every league, with Serie A showing the highest Low Activity share.}",
        r"\label{tbl-rq1-competition}",
        r"\centering",
        r"\setlength{\tabcolsep}{4pt}",
        r"\renewcommand{\arraystretch}{1.05}",
        r"\begin{tabular}{@{}l l l >{\raggedright\arraybackslash}p{0.36\linewidth}@{}}",
        r"\toprule",
        r"Competition & Largest (seasons) & Second largest & Notable pattern \\",
        r"\midrule",
    ]
    for row in m["competition_summary"]:
        lines.append(
            f"{row['competition']} & {row['largest']} & {row['second_largest']} & {row['notable_pattern']} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def quadrant_table_md() -> str:
    m = load_metrics()
    lines = [
        "| Quadrant | Players | Share |",
        "|----------|---------|-------|",
    ]
    for quadrant in QUADRANT_ORDER:
        players = m["quadrant_counts"][quadrant]
        share = m["quadrant_shares"][quadrant]
        lines.append(f"| {quadrant} | {players} | {fmt_pct(share)} |")
    lines.append("")
    lines.append(
        f": RQ2 quadrant counts for {m['n_dual_context_players']} dual-context players "
        f"with at least {m['min_minutes']} minutes in both settings. "
        "Elite and Underperformer each account for about one third of the cohort. "
        "{#tbl-quadrant-dist}"
    )
    return "\n".join(lines)


def data_overview_table_md() -> str:
    m = load_metrics()
    lines = [
        "| Table | Grain | Scale |",
        "|-------|-------|-------|",
        f"| `matches` | One row per match | {fmt_int(m['n_matches'])} matches |",
        f"| `events` | One row per on-ball action | ~{fmt_millions(m['n_events'])} rows |",
        f"| `lineups` | One row per player appearance | {fmt_int(m['n_lineups'])} rows |",
        "",
        ": StatsBomb tables ingested into BigQuery via `statsbombpy`. "
        "The events table drives per-90 feature engineering, "
        "matches provide competition context, and lineups supply minutes and position. "
        "{#tbl-data-overview}",
    ]
    return "\n".join(lines)
