PY ?= .venv/bin/python
HOST ?= 0.0.0.0
PORT ?= 8000

.PHONY: setup run test train seed

setup:
	uv venv -p 3.11 .venv && uv pip install -p $(PY) -r requirements.txt

run:
	$(PY) -m uvicorn app.main:app --host $(HOST) --port $(PORT)

test:
	$(PY) -m pytest -q tests

train:
	$(PY) ml/train.py

seed:
	$(PY) scripts/seed_demo.py
