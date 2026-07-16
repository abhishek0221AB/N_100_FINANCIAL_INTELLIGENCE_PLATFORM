.PHONY: load validate check test queries ratios report dashboard api clean

load:
	python -m src.etl.loader

validate:
	python -m src.etl.validator

check:
	python -m src.etl.check_db

test:
	pytest

queries:
	python -m src.etl.run_exploratory_queries

ratios:
	python -m src.analytics.ratios

report:
	python -m src.reports.tearsheet

dashboard:
	streamlit run src/dashboard/app.py

api:
	uvicorn src.api.main:app --reload --port 8000

clean:
	python -c "from pathlib import Path; files=[Path('data/nifty100.db'),Path('output/load_audit.csv'),Path('output/load_rejections.csv'),Path('output/validation_failures.csv'),Path('output/out_of_scope_rows.csv')]; [f.unlink() for f in files if f.exists()]; print('Generated Sprint 1 files removed.')"