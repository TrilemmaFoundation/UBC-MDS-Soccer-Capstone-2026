# Final Presentation

**Branch:** `docs/presentation`  
**Format:** Quarto Reveal.js (`final_presentation.qmd`)  
**Time budget:** 22 min total · ~5 min Quan · ~5.5 min each (Li, Rabin, Teem) · 7 min Q&A

## Design rules (from mentor feedback)

1. **One image per slide** — never pack multiple screenshots side-by-side
2. **Crop screenshots tight** — numbers, labels, and player names must be readable from the back of the room
3. **Roadmap on slide 2** — RQ → presenter table
4. **Readable but fits** — base font 38px; dense slides use `{.compact}`; one image per slide

## Render the deck

```bash
quarto render presentation/final_presentation.qmd
open presentation/final_presentation.html
```

Press `s` in the browser for **Presenter View** (speaker notes).

## Slide map

| Slides | Owner | Topic |
|--------|-------|-------|
| 1 | **Quan** | Title + team intro |
| 2 | **Quan** | Problem & roadmap |
| 3 | **Quan** | Data pipeline — dbt |
| 4 | **Quan** | Pipeline orchestration — Dagster |
| 5–7 | **Quan** | Key results — one screenshot each (RQ2, RQ3, chatbot) |
| 8 | **Li** | Clustering pipeline (compact table) |
| 9 | **Li** | 5 archetypes table |
| 10–12 | **Li** | Cluster scatter + dashboard (one image per slide) |
| 13 | **Rabin** | Consistency pipeline (RQ3) |
| 14–15 | **Rabin** | Formulas & results + quadrant definitions |
| 16–18 | **Rabin** | Consistency Explorer (one image per slide) |
| 19–28 | **Teem** | Architecture, dbt, Dagster, chatbot, handover |
| 29 | All | Thank you / Q&A |

### Quan time budget (~5 min)

| Slide | Time |
|-------|------|
| Title + team intro | ~30 sec |
| Problem & roadmap | ~1 min |
| dbt + Dagster | ~1 min 15 sec |
| Key results (3 slides) | ~2 min |

## Screenshots to add

Crop every image before adding. **One file = one slide.**

### Quan (key results)

| File | Crop for |
|------|----------|
| `key-results-cluster.png` | Archetype labels + counts |
| `key-results-consistency.png` | Quadrant labels + player names |
| `key-results-chatbot.png` | Full query + answer text |

### Li (clustering dashboard)

| File | Crop for |
|------|----------|
| `looker-cluster-scatter.png` | PCA axes, colours, legend |
| `looker-cluster-page1.png` | Player counts, archetype breakdown |
| `looker-cluster-page2.png` | Top players table, names + stats |

### Rabin (consistency dashboard)

| File | Crop for |
|------|----------|
| `looker-consistency-p1.png` | 493 players, 58 countries (slide 1) |
| `looker-quadrant-scatter.png` | Axes, quadrants, example players (slide 2) |
| `looker-consistency-p2.png` | Country names + scores (slide 3) |

### Teem (infra + chatbot)

| File | Crop for |
|------|----------|
| `architecture-diagram.png` | StatsBomb → GCS → BigQuery → dbt → ML → serving |
| `dagster-asset-graph.png` | Asset names + weekly schedule |
| `chatbot-demo.png` | Query + answer text |
| `handover-readme.png` | README or HANDOVER.md header |

Replace a `TODO` placeholder with:

```markdown
::: {.slide-image}
![](assets/your-screenshot.png)
:::
```

## Handoff lines

- **Quan → Li:** *"Li will walk through RQ1 and RQ2 — clustering and the Player Archetypes dashboard."*
- **Li → Rabin:** *"Rabin covers RQ3 — consistency scoring next."*
- **Rabin → Teem:** *"Everything in Looker is queryable through our chatbot — Teem covers that next."*
- **Teem → Q&A:** *"That concludes our presentation. Thank you, and we'll open the floor to questions."*

## Number reconciliation

Quan/Rabin slides use **493** dual-context players. Update if your dashboard shows a different count.
