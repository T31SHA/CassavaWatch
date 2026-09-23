PY ?= .venv/bin/python
HOST ?= 0.0.0.0
PORT ?= 8000

.PHONY: setup setup-train run test train seed fetch

setup:
	uv venv -p 3.11 .venv && uv pip install -p $(PY) -r requirements.txt

setup-train: setup
	uv pip install -p $(PY) -r requirements-train.txt

run:
	$(PY) -m uvicorn app.main:app --host $(HOST) --port $(PORT)

test:
	$(PY) -m pytest -q tests

fetch:
	$(PY) ml/fetch_icassava.py 300 100

train:
	$(PY) ml/train.py

seed:
	$(PY) scripts/seed_demo.py
