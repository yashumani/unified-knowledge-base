.PHONY: install install-dev run test lint docker-up mcp web-install web-dev web-build web-preview ollama-models ollama-status db-upgrade db-current

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,mcp]"

run:
	uvicorn ukb.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest

lint:
	ruff check src tests

docker-up:
	docker compose up --build

mcp:
	python -m ukb.mcp.server

web-install:
	npm install

web-dev:
	npm run web:dev

web-build:
	npm run web:build

web-preview:
	npm run web:preview

ollama-models:
	bash scripts/ollama_pull_models.sh

ollama-status:
	curl http://localhost:8000/ai/providers

db-upgrade:
	alembic upgrade head

db-current:
	alembic current
