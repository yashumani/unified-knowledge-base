# Unified Knowledge Base

A starter platform for building a governed **AI Brain**: a secure, reviewable, reusable knowledge runtime that converts messy enterprise context into structured context packs for AI applications.

This repository is intentionally designed to run on a self-hosted GitLab/Linux/Docker environment while still being easy to develop in GitHub first.

> Public scaffold rule: use synthetic examples only. Do not commit employer documents, proprietary dashboards, customer data, credentials, telecom examples, finance-planning examples, or workplace-specific context into this repository.

## What this is

Most AI apps fail because they connect a model to raw documents or data and expect intelligence. A data query can return a number, but the model still needs definitions, lineage, ownership, caveats, business rules, source evidence, and approval state.

This project creates the missing middle layer:

```text
Messy enterprise context
  docs, dashboards, metrics, SQL, wiki pages, tribal knowledge, tickets, files

      -> ingest
      -> parse
      -> classify
      -> normalize
      -> human review
      -> publish

Governed AI Brain
  evidence objects, semantic objects, knowledge graph relationships, review state

      -> REST API
      -> Python SDK
      -> MCP server adapter
      -> React console

AI applications
  copilots, chatbots, agents, report explainers, and insight generators
```

## Product principle

The AI Brain should not store only generated answers. It should store reusable, governed context:

- metric definitions
- source evidence
- lineage
- business rules
- caveats
- owners
- access policy
- approval state
- freshness
- relationships
- narrative templates

Answers are generated from context. Context is the durable product.

## Neutral demo domain

The public demo uses a generic support-operations scenario:

```text
Domain: support
Metric: Incident Resolution Time
Report: SLA Review Dashboard
Rule: SLA Review Window
Owner: Support Operations
```

This example is synthetic and intentionally not based on any employer, carrier, telecom workflow, finance-planning process, or proprietary dashboard.

## Architecture in one sentence

`Core Brain Runtime` is the source of truth. `REST API`, `Python SDK`, `MCP server`, and the `React UI` are adapters over the same runtime.

```text
                         ┌────────────────────────────┐
                         │ Admin / Governance UI       │
                         │ submit, review, approve     │
                         └──────────────┬─────────────┘
                                        │ REST
┌────────────────────┐      ┌───────────▼───────────┐      ┌─────────────────────┐
│ Enterprise Sources  │ ---> │ Brain Compiler         │ ---> │ Governed Brain Store │
│ docs, data, SQL     │      │ classify + normalize   │      │ objects + evidence   │
└────────────────────┘      └───────────┬───────────┘      └─────────┬───────────┘
                                        │                            │
                                        │ human review                │
                                        ▼                            ▼
                                ┌────────────────┐          ┌────────────────────┐
                                │ Review Queue   │          │ Context Runtime API │
                                └────────────────┘          └─────────┬──────────┘
                                                                       │
                                         ┌─────────────────────────────┼─────────────────────────────┐
                                         ▼                             ▼                             ▼
                                REST/SDK consumers              MCP clients                  React/AI apps
```

## API vs MCP

Use both, but for different jobs.

- **REST API**: product UI, ingestion workflows, governance actions, admin consoles, CI/CD, integrations, and enterprise services.
- **MCP server**: exposing the approved brain to LLM agents as tools/resources/prompts.
- **SDK**: developers who want to consume context packs from notebooks, automation, or backend services.
- **React UI**: human-facing console for submission, review, context-pack exploration, and graph visualization.

Do not build the MCP server as the only backend. MCP should be an adapter, not the whole platform.

## Quick start

### 1. Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,mcp]"
```

### 2. Run the API

```bash
uvicorn ukb.api.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000/docs
```

### 3. Submit sample context

```bash
curl -X POST http://localhost:8000/ingestion/submissions \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Incident Resolution Time Definition",
    "source_type": "document",
    "submitted_by": "demo.user",
    "domain": "support",
    "content": "Incident Resolution Time is the average elapsed time from incident creation to resolved status for product support cases, excluding duplicate incidents and customer-wait periods. It appears in the SLA Review Dashboard and is owned by Support Operations."
  }'
```

### 4. Review queue

```bash
curl http://localhost:8000/review/queue
```

### 5. Approve a review item

Replace `{review_item_id}` with the ID from the queue.

```bash
curl -X POST http://localhost:8000/review/items/{review_item_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"reviewed_by": "domain.reviewer", "comment": "Approved for synthetic demo."}'
```

### 6. Request a context pack

```bash
curl -X POST http://localhost:8000/brain/context-pack \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Why did incident resolution time increase?",
    "user_id": "demo.user",
    "domains": ["support"],
    "mode": "executive_insight"
  }'
```

## React UI

```bash
npm install
npm run web:dev
```

Open:

```text
http://localhost:5173
```

The React UI includes a context submission form, review queue, context-pack explorer, published object browser, and an Obsidian-style graph view.

## Run with Docker

```bash
docker compose up --build
```

## Run the MCP server

```bash
python -m ukb.mcp.server
```

## Repository map

```text
src/ukb/
  api/                 FastAPI application
  mcp/                 MCP adapter
  services/            compiler, governance, retrieval, graph, context-pack logic
  models.py            Pydantic contracts
  store.py             development store

apps/web/              React console

knowledge/
  ontology/            brain object schema and relationship grammar
  domains/             synthetic support example
  templates/           narrative templates
  access/              role and policy examples
  evals/               golden questions

docs/
  ARCHITECTURE.md
  API_VS_MCP.md
  GOVERNANCE_WORKFLOW.md
  CONTEXT_PACK.md
  GITHUB_PAGES_DEPLOYMENT.md
  REACT_UI.md
  WORKPLACE_SAFE_EXAMPLES.md
```

## Current maturity

This is a scaffold, not a production system yet. The next real build steps are:

1. Replace in-memory store with Postgres.
2. Add object storage for source evidence.
3. Add vector/hybrid search.
4. Add graph relationships.
5. Add real auth and ACL filtering.
6. Add persistent review UI flows.
7. Add GitLab deployment variables and environment-specific secrets.
8. Add source connectors one by one.
