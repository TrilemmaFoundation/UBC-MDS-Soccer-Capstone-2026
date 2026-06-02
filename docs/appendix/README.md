# Dashboard appendix — methodology

Formulas and definitions for Looker dashboards in this project.

| Document | Dashboard | Topics |
|----------|-----------|--------|
| [Context shift score](./context-shift-score.md) | Top players by context shift score | Raw per-90 gap, minute-balance weight, eligibility |
| [Consistency Explorer](./consistency-explorer.md) | Consistency Explorer | Z-scores, performance scores, consistency score, quadrants |

**Data:** StatsBomb → dbt [`int_player_club_vs_national`](../../models/intermediate/int_player_club_vs_national.sql) → BigQuery → Looker.

**Notebooks:** [`03_consistency_score.ipynb`](../../notebooks/03_consistency_score.ipynb), [`04_feature_importance.ipynb`](../../notebooks/04_feature_importance.ipynb)

**GitHub:** [docs/appendix](https://github.com/TrilemmaFoundation/UBC-MDS-Soccer-Capstone-2026/tree/main/docs/appendix)
