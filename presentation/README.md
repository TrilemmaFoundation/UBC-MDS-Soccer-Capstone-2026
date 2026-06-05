# Final Presentation

**Branch:** `docs/presentation`  
**Format:** Quarto Reveal.js (`final_presentation.qmd`)  
**Time budget:** 22 min total · ~5.5 min per person · 7 min Q&A

## Render the deck

```bash
# From repo root (requires Quarto)
quarto render presentation/final_presentation.qmd

# Output: presentation/final_presentation.html
# Optional PDF:
quarto render presentation/final_presentation.qmd --to pdf
```

Open `final_presentation.html` in a browser for the dry run. Use **Presenter View** (press `s` in Reveal.js) to see speaker notes.

## Slide assignments

| Slides | Owner | Topic | Status |
|--------|-------|-------|--------|
| 1–3 | **Quan** | Title, problem, key results | ✅ Draft complete |
| 4–6 | **Li** | Clustering methodology, results, dashboard | 📝 Draft — add screenshots |
| 7–13 | **Rabin** | Consistency scoring, results, dashboard (4 Looker pages) | ✅ Draft complete — add screenshots |
| 14–19 | **Teem** | Architecture, pipeline, Dagster, chatbot, handover | ✅ Draft complete — add screenshots |

## Deadlines

| Milestone | Date |
|-----------|------|
| Shared deck created + slides assigned | Tomorrow |
| Each person finishes their slides | Wed Jun 10 |
| Full dry run (slides + live demo) | Thu Jun 11 evening |

## Screenshots to add

Drop images into `presentation/assets/` using these exact filenames so slides render automatically:

### Li (clustering dashboard)

| File | Content |
|------|---------|
| `looker-cluster-scatter.png` | PCA scatter with 5 archetype colors |
| `looker-cluster-page1.png` | Player Archetypes — overview page |
| `looker-cluster-page2.png` | Player Archetypes — explorer / top players |

### Rabin (consistency dashboard)

| File | Content |
|------|---------|
| `looker-quadrant-scatter.png` | Quadrant scatter — main view (Page 3) |
| `looker-consistency-p1.png` | Overview — 493 players, 58 countries |
| `looker-consistency-p2.png` | Country rankings |
| `looker-consistency-p4.png` | Context shift page |

### Teem (infra + chatbot)

| File | Content |
|------|---------|
| `dagster-asset-graph.png` | Dagster asset graph — highlight weekly schedule |
| `chatbot-demo.png` | Chatbot answering a tactical plain-English question |
| `handover-readme.png` | GitHub README and/or top of `HANDOVER.md` |

## Handoff lines

- **Li → Rabin:** *"We showed how we cluster players into tactical archetypes. Our second objective is consistency scoring…"*
- **Rabin → Teem:** *"Everything you saw in Looker is also queryable through our natural-language chatbot. Next we'll demo the chatbot and walk through the system architecture."*
- **Teem → Q&A:** *"That concludes our presentation. Thank you, and we'll now open the floor to any questions."*

## Mentor name

Slide 1 has `[Mentor name]` — replace once confirmed.

## Number reconciliation

Quan/Rabin slides use **493** dual-context players (per latest pipeline run). Update Slide 3 if your dashboard shows a different count.
