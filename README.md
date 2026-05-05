# UBC-MDS-Soccer-Capstone-2026

Shared project repo for the UBC MDS Soccer Capstone 2026 (Trilemma Foundation football analytics).

## Repository layout

| Path | Purpose |
|------|---------|
| `data/` | Local datasets (`Statsbomb/`, `Polymarket/`). Parquet files are gitignored. Obtain or generate data separately and place files here to match the paths expected in notebooks. |
| `notebooks/` | Analysis notebooks (EDA, club vs national team, player clustering). Figures can be written to `results/figures/` when cells are run. |
| `report/` | Quarto proposal report (`proposal_report.qmd`) and rendered PDF. |
| `results/figures/` | Exported plots used by the report and notebooks (created when you run the notebooks, required for images embedded in the Quarto PDF). |
| `environment.yml` | Conda environment specification for Python dependencies. |
| `Makefile` | Shortcuts for common tasks (e.g. building the report). |

## Environment

Create and activate the conda environment:

```bash
conda env create -f environment.yml
conda activate soccer_capstone
```

## Building the proposal report (PDF)

The report is a Quarto project under `report/`. From the **repository root**:

```bash
make report
```

This runs `quarto render report/proposal_report.qmd --to pdf` and writes `report/proposal_report.pdf`.

**Requirements:** [Quarto](https://quarto.org/docs/get-started/) and a LaTeX distribution (for example TeX Live) so PDF rendering can run `xelatex`.
