# Supplementary documentation

Extended methodology, formulas, and analysis detail referenced by the [final report](../../report/final_report.qmd). The report summarises main results; use these documents for full definitions, pipeline steps, and reproducible notebooks.

## Dashboard methodology

| Document | Dashboard | Topics |
|----------|-----------|--------|
| [Context shift score](./context-shift-score.md) | Top players by context shift score | Raw per-90 gap, minute-balance weight, eligibility |
| [Consistency Explorer](./consistency-explorer.md) | Consistency Explorer | Z-scores, performance scores, consistency score, quadrants |

## Pipelines and models

| Document | Topics |
|----------|--------|
| [Club vs national consistency](../consistency.md) | `consistency.py`, dbt model, BigQuery table, run order |
| [Analysis notebooks](../notebooks.md) | RQ1 chi-square / heatmaps (Notebook 07), RQ2 quadrants (Notebook 08), clustering design (Notebook 05) |
| [Partner handover](../../HANDOVER.md) | Full ELT architecture, dbt layers, Dagster, chatbot, deployment |
| [Mart data dictionary](../marts_data_dict.md) | Looker / chatbot table schemas |

**Data flow:** StatsBomb → dbt [`int_player_club_vs_national`](../../models/intermediate/int_player_club_vs_national.sql) → BigQuery `analytics.*` → Looker / chatbot.

**GitHub:** [docs/appendix](https://github.com/TrilemmaFoundation/UBC-MDS-Soccer-Capstone-2026/tree/main/docs/appendix)
