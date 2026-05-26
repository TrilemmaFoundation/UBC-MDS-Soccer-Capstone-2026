# Consistency Explorer

**Dashboard:** Consistency Explorer  
**Source:** `analytics.consistency_scores` / [`03_consistency_score.ipynb`](../../notebooks/03_consistency_score.ipynb)  
**dbt:** [`int_player_club_vs_national.sql`](../../models/intermediate/int_player_club_vs_national.sql)

## Purpose

Explore how players perform across **club** and **national** contexts:

- **Club / national performance score** — strength vs peers in that context
- **Consistency score** — how similar the tactical profile is across contexts
- **Quadrants** — median splits (Elite both, Club-strong, National-strong, Lower both)

## Eligibility

Same as context shift: **≥ 270 minutes** per context, dual-context players only.

## Z-scores

For each of 11 features, within each context separately:

```
z = (player_value − mean_in_context) / stddev_in_context
```

Club z-scores compare only to club players; national z-scores only to national players.

## Features (11)

| Feature | Description |
|---------|-------------|
| `shots_per_90` | Shots per 90 |
| `xg_per_90` | Expected goals per 90 |
| `xg_per_shot` | xG per shot |
| `dribbles_per_90` | Dribbles per 90 |
| `carries_att_third_per_90` | Carries into attacking third per 90 |
| `passes_att_third_per_90` | Passes into attacking third per 90 |
| `pass_completion_pct` | Pass completion % |
| `pressures_per_90` | Pressures per 90 |
| `interceptions_per_90` | Interceptions per 90 |
| `clearances_per_90` | Clearances per 90 |
| `aerial_duels_per_90` | Aerial duels per 90 |

## PCA feature weights

From PCA loadings (clustering pipeline):

```
w_f = (Σ_i |loading_{i,f}|) / (Σ_{f'} Σ_i |loading_{i,f'}|)
```

Weights sum to 1.

## Club / national performance score

For each player in one context:

```
performance_score = Σ_f (z_f × w_f)
```

- **`club_performance_score`** — `is_international = false`
- **`national_performance_score`** — `is_international = true`

**Higher** = stronger profile **relative to peers in that same context**.

Scatter plot axes use these scores. Dashed lines = cohort medians.

## Consistency score

```
consistency_score = 1 − (1/11) × Σ_f |z_f,club − z_f,national|
```

| Score | Meaning |
|-------|---------|
| **Near 1** | Similar tactical profile in both contexts |
| **Lower** | Larger shift between club and national on these 11 dimensions |

**Not** a quality score — a player can be consistently weak in both contexts.

## Performance quadrants

Median splits on `club_performance_score` and `national_performance_score`:

| Club vs median | National vs median | Label | Color (dashboard) |
|----------------|-------------------|--------|-------------------|
| High | High | Elite both | Brown |
| High | Low | Club-strong | Green |
| Low | High | National-strong | Red |
| Low | Low | Lower both | Light blue |

## How this differs from context shift score

| Metric | Question |
|--------|----------|
| **Context shift score** | Largest raw (national − club) per-90 gap on 8 metrics, minute-weighted |
| **Consistency score** | Similarity of 11-metric z-profiles across contexts |
| **Performance scores** | Strength vs peers within each context |

## Limitations

1. Competition and opponent quality differ by context.
2. PCA weights reflect playing-style variance in the dataset, not tactical “truth.”
3. Median quadrants depend on the filtered cohort.

## See also

- [Context shift score](./context-shift-score.md)
- [`04_feature_importance.ipynb`](../../notebooks/04_feature_importance.ipynb)
