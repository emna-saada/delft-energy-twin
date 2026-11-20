.PHONY: install data portfolio run maps report app video demo test lint clean

PY := uv run

install:            ## create the environment from the lock file
	uv sync --all-extras

data:               ## download open data (AWS Open Data, geoBoundaries, WorldPop, Natural Earth)
	$(PY) python scripts/fetch_static.py
	$(PY) python scripts/fetch_landcover.py
	$(PY) python scripts/fetch_flood.py
	$(PY) python scripts/fetch_cmip6.py --workers 8

portfolio:
	$(PY) climarisk portfolio

run:                ## full pipeline -> outputs/kpis.json
	$(PY) climarisk run

maps:
	$(PY) climarisk maps

report:             ## PDF report -> docs/report.pdf
	$(PY) climarisk report

app:                ## Streamlit dashboard on http://localhost:8501
	$(PY) streamlit run app/streamlit_app.py

video:              ## dashboard capture + animated MP4 -> video/out/climarisk_demo.mp4
	cd video && npm install && npm run build

demo: run maps report   ## reproduce the demo end-to-end (after `make data`)

test:
	$(PY) pytest -q

lint:
	$(PY) ruff check src tests app

clean:
	rm -rf outputs/*.parquet outputs/*.csv outputs/*.json outputs/maps
