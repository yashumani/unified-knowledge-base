.PHONY: install install-dev run test lint docker-up mcp

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
