.PHONY: report final-report final-report-export

report:
	quarto render report/proposal_report.qmd --to pdf

final-report:
	python src/report/render_report.py

final-report-export:
	python src/report/export_metrics.py
	python src/report/render_report.py
