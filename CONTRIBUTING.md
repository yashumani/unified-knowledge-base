# Contributing to Unified Knowledge Base

Unified Knowledge Base is a governed context runtime. Contributions must preserve the distinction between source evidence, AI-generated suggestions, human approval, and published organizational knowledge.

## Non-negotiable product boundary

```text
LLM output = suggestion
Human review = approval
Published brain object = official context
```

No connector, plugin, API route, MCP tool, background job, or UI action may silently bypass this boundary.

## Data-safety rule

This public repository accepts only synthetic or fully sanitized examples. Do not commit or paste:

- employer or client documents
- customer, employee, or personal data
- internal dashboards, metrics, screenshots, SQL, URLs, or credentials
- proprietary operating procedures or business definitions
- secrets, tokens, certificates, or service-account files

Use the neutral support-operations examples already present in the repository.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,mcp]"

npm install
```

For local Ollama enrichment:

```bash
ollama pull llama3.1
ollama pull embeddinggemma
cp .env.example .env
```

Run the backend and frontend in separate shells:

```bash
make run
npm run web:dev
```

## Required validation

Before opening a pull request, run the checks relevant to your change:

```bash
ruff check src tests
mypy src/ukb
pytest -q --cov=ukb --cov-report=term-missing
python -m compileall -q src tests
npm run web:build
docker compose -f docker-compose.yml config --quiet
```

Changes to production deployment assets should also validate:

```bash
cp deploy/prod.env.example deploy/.env
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env config --quiet
```

## Branch and pull-request workflow

1. Start from the latest `main`.
2. Create a focused branch named `agent/<description>` or `feature/<description>`.
3. Keep unrelated changes out of the same pull request.
4. Complete the pull-request template.
5. Wait for Continuous Integration and CodeQL checks.
6. Resolve review comments and update documentation when behavior changes.
7. Use squash merge for a focused feature or fix unless preserving commit history is important.

## Architecture expectations

- Keep FastAPI routes, MCP tools, CLI commands, and React components as thin adapters over shared services.
- Apply authorization and sensitivity filtering before content reaches retrieval or Ollama.
- Return structured, schema-validated model output.
- Preserve source evidence and confidence metadata.
- Keep Ollama private behind the backend; never call it directly from the public browser.
- Add tests for every new governance transition, API contract, or model-output schema.

## Documentation

Update the relevant guide in `docs/` when changing architecture, configuration, deployment, API behavior, or the UI workflow.
