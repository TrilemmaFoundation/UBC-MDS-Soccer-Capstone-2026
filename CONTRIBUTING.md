# Contributing Guide

Thank you for contributing to the UBC MDS Soccer Capstone 2026 — Trilemma Foundation Football Analytics platform.

---

## Development Environment Setup

```bash
# Clone the repo
git clone https://github.com/TrilemmaFoundation/UBC-MDS-Soccer-Capstone-2026.git
cd UBC-MDS-Soccer-Capstone-2026

# Create and activate the conda environment
conda env create -f environment.yml
conda activate soccer_capstone

# Add credentials
cp .env.example .env        # fill in GROQ_API_KEY
cp service-account-key.json .  # get from the team — never commit this file

# Authenticate with GCP
export GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
```

See `README.md` for Docker-based setup and `HANDOVER.md` for full component guides.

---

## Branch Naming Conventions

| Type | Pattern | Example |
|---|---|---|
| Feature | `feat/<short-description>` | `feat/goalkeeper-filter` |
| Bug fix | `fix/<short-description>` | `fix/mart-fan-out` |
| Documentation | `docs/<short-description>` | `docs/handover-guide` |
| Data/dbt | `dbt/<short-description>` | `dbt/int-player-season-stats` |
| ML | `ml/<short-description>` | `ml/cluster-labels` |

---

## Pull Request Process

1. Create a branch from `main` using the naming convention above.
2. Make your changes and push to the branch.
3. Open a pull request against `main` with a clear title and description.
4. Link the relevant GitHub issue using `Closes #<issue-number>` in the PR body.
5. Request a review from at least one other team member.
6. **Do not merge your own PR** — someone else must review and merge it.
7. Delete the branch after merging.

---

## Commit Message Style

Use the format: `<type>: <short description>`

```
feat: add goalkeeper filter to cluster.py
fix: correct mart_player_clusters join grain
docs: update HANDOVER.md with Databricks section
dbt: add position_name to int_player_season_stats
test: add unit tests for preprocess()
```

Keep the subject line under 72 characters. Add a body if the change needs more explanation.

---

## Running Tests

```bash
# Python unit tests
pytest tests/

# dbt data tests
dbt test

# dbt tests for specific model
dbt test --select int_player_season_stats
```

All new functions in `src/ml/` should have corresponding unit tests in `tests/`.

---

## Code Style

- Python: follow PEP 8. Use `SAFE_DIVIDE` in SQL instead of `/` to avoid division by zero.
- SQL (dbt): one CTE per logical step, descriptive CTE names, comments on non-obvious logic.
- Keep functions small and single-purpose (DRY principle).
- No hardcoded credentials — use environment variables from `.env`.

---

## Reporting Issues

Open a GitHub issue with:
- A clear title describing the problem
- Steps to reproduce (if a bug)
- Expected vs actual behaviour
- Relevant logs or screenshots

Assign yourself to the issue and add it to the project board.
