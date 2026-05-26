# Context shift score

**Dashboard:** Top players by context shift score  
**Field:** `context_shift_score` (Looker calculated field)

## Purpose

Rank how much a player’s per-90 profile differs between **national team** and **club**.

- **Positive** → relatively stronger combined output for **national team** on the selected metrics
- **Negative** → relatively stronger for **club**

This complements the [Consistency Explorer](./consistency-explorer.md), which measures peer-relative similarity (z-scores), not raw per-90 gaps.

## Eligibility

- **≥ 270 minutes** in club context
- **≥ 270 minutes** in national context
- Player must appear in **both** contexts (dual-context cohort)

## Step 1 — Raw gap (8 metrics)

For each metric, compute **National per 90 − Club per 90**, then sum. Missing values are treated as 0 (`COALESCE`).

| # | Metric |
|---|--------|
| 1 | xG per 90 |
| 2 | Shots per 90 |
| 3 | Passes per 90 |
| 4 | Carries into final third per 90 |
| 5 | Carries per 90 |
| 6 | Passes into final third per 90 |
| 7 | Pressures per 90 |
| 8 | Pass Completion % |

**Note:** Metrics use different units (counts vs %). The sum is an exploratory index, not a formal weighted index.

## Step 2 — Minutes reliability weight (0 to 1)

Down-rank players where national and club minutes are very imbalanced (few international games vs large club sample).

```
weight = (2 × M_nat × M_club) / ((M_nat + M_club) × MAX(M_nat, M_club))
```

- `M_nat` = `total_minutes (National)`
- `M_club` = `total_minutes (Club)`

| Weight | Interpretation |
|--------|----------------|
| Near 1 | Similar minutes in both contexts |
| Near 0 | Heavily imbalanced minutes |

**Do not** multiply by the harmonic mean of minutes alone (without dividing by `MAX`) — that scales scores by thousands and is incorrect.

## Final score

```
context_shift_score = raw_gap × weight
```

## Looker formula (reference)

```sql
(
  (COALESCE(xG per 90 (National), 0) - COALESCE(xG per 90 (Club), 0)) +
  (COALESCE(Shots per 90 (National), 0) - COALESCE(Shots per 90 (Club), 0)) +
  (COALESCE(Passes per 90 (National), 0) - COALESCE(Passes per 90 (Club), 0)) +
  (COALESCE(Carries into final third per 90 (National), 0) - COALESCE(Carries into final third per 90 (Club), 0)) +
  (COALESCE(Carries per 90 (National), 0) - COALESCE(Carries per 90 (Club), 0)) +
  (COALESCE(Passes into final third per 90 (National), 0) - COALESCE(Passes into final third per 90 (Club), 0)) +
  (COALESCE(Pressures per 90 (National), 0) - COALESCE(Pressures per 90 (Club), 0)) +
  (COALESCE(Pass Completion % (National), 0) - COALESCE(Pass Completion % (Club), 0))
)
*
(
  2 * COALESCE(total_minutes (National), 0) * COALESCE(total_minutes (Club), 0)
  / (
    (COALESCE(total_minutes (National), 0) + COALESCE(total_minutes (Club), 0))
    * CASE
        WHEN COALESCE(total_minutes (National), 0) > COALESCE(total_minutes (Club), 0)
        THEN COALESCE(total_minutes (National), 0)
        ELSE COALESCE(total_minutes (Club), 0)
      END
  )
)
```

## Dashboard visuals

- **Brown bars:** top positive scores (national-leaning shift)
- **Green bars:** bottom negative scores (club-leaning shift)

## Limitations

1. Raw sum mixes scales (passes vs %).
2. National minutes can still be noisy at the 270-minute floor.
3. Club and national competitions differ tactically, not only “context.”
4. Position may vary between contexts.

## See also

- [Consistency Explorer](./consistency-explorer.md)
- dbt: [`int_player_club_vs_national.sql`](../../models/intermediate/int_player_club_vs_national.sql)
