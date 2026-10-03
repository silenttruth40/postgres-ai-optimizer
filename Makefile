PYTHON ?= python3
PIP ?= pip3

.PHONY: install test lint run docker-up docker-down demo train

install:
	$(PIP) install -r requirements.txt

test:
	$(PYTHON) -m pytest tests -q

lint:
	$(PYTHON) -m compileall backend ingestion privacy optimizer rl gnn sandbox dashboard scripts tests

run:
	PYTHONPATH=. uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

docker-up:
	docker compose up --build

docker-down:
	docker compose down

demo:
	PYTHONPATH=. $(PYTHON) scripts/run_demo.py

train:
	PYTHONPATH=. $(PYTHON) scripts/train_models.py
