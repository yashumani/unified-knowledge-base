# Unified Knowledge Base

A starter platform for building a governed **AI Brain**: a secure, reviewable, reusable knowledge runtime that converts messy enterprise context into structured context packs for AI applications.

This repository is intentionally designed to run on a self-hosted GitLab/Linux/Docker environment while still being easy to develop in GitHub first.

> Important: do not commit real company data, proprietary documents, customer data, credentials, or workplace-only context into this public/personal repository. Use synthetic examples here. Mirror or port the scaffold into a private enterprise GitLab environment before connecting real sources.

## What this is

Most AI apps fail because they connect a model to raw documents or data and expect intelligence. A data query can return a number, but the model still needs definitions, lineage, ownership, caveats, business rules, prior decisions, security policy, and source evidence.

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

AI applications
  BI copilots, chatbots, agents, executive insight generators, report explainers
```

## Product principle

The AI Brain should not store only generated answers.

It should store reusable, governed context:

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

## Architecture in one sentence

`Core Brain Runtime` is the source of truth. `REST API`, `Python SDK`, and `MCP server` are adapters over the same runtime.

```text
                         ┌────────────────────────────┐
                         │ Admin / Governance UI       │
                         │ submit, review, approve     │
                         └──────────────┬─────────────┘
                                        │ REST
┌────────────────────┐      ┌───────────▼───────────┐      ┌─────────────────────┐
│ Enterprise Sources  │ ---> │ Brain Compiler         │ ---> │ Governed Brain Store │
│ docs, data, SQL     │      │ AI classify + normalize│      │ objects + evidence   │
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
                                REST/SDK consumers              MCP clients                  BI/chat apps
```

## API vs MCP

Use both, but for different jobs.

- **REST API**: best for product UI, ingestion workflows, governance actions, admin consoles, CI/CD, integrations, and enterprise services.
- **MCP server**: best for exposing the approved brain to LLM agents as tools/resources/prompts.
- **SDK**: best for developers who want to consume context packs from Python notebooks, BI automation, or backend services.

Recommended design:

```text
BrainService / Store / Governance / Compiler
              │
        shared core logic
              │
   ┌──────────┼──────────┐
   ▼          ▼          ▼
REST API   MCP Adapter  Python SDK
```

Do not build the MCP server as the only backend. MCP should be an adapter, not the whole platform.

## Starter features in this repo

- FastAPI service with health, ingestion, review, and context-pack endpoints
- MCP server adapter exposing brain tools
- In-memory store for local development
- Sample ontology, access roles, metric object, and narrative template files
- Human review workflow before publishing knowledge
- Context pack schema
- Docker and Docker Compose
- GitLab CI starter pipeline
- Security and governance documentation

## Quick start

### 1. Create a virtual environment

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
    "title": "Device Revenue Definition",
    "source_type": "document",
    "submitted_by": "demo.user",
    "domain": "finance",
    "content": "Device Revenue is revenue generated from device sales, excluding service revenue. It appears in the CFO KPI dashboard and is owned by Finance BI."
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
  -d '{"reviewed_by": "domain.reviewer", "comment": "Approved for demo."}'
```

### 6. Request a context pack

```bash
curl -X POST http://localhost:8000/brain/context-pack \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Why is device revenue down?",
    "user_id": "demo.user",
    "domains": ["finance"],
    "mode": "executive_insight"
  }'
```

## Run with Docker

```bash
docker compose up --build
```

## Run the MCP server

```bash
python -m ukb.mcp.server
```

The MCP server currently runs as a thin adapter over the same local brain runtime. For enterprise deployment, expose MCP through a secured internal endpoint or run it as a local stdio gateway depending on the client environment.

## Repository map

```text
src/ukb/
  api/                 FastAPI application
  mcp/                 MCP adapter
  services/            compiler, governance, retrieval, context-pack logic
  models.py            Pydantic contracts
  store.py             development store

knowledge/
  ontology/            brain object schema and relationship grammar
  domains/             domain-specific knowledge examples
  templates/           narrative templates
  access/              role and policy examples
  evals/               golden questions

docs/
  ARCHITECTURE.md
  API_VS_MCP.md
  GOVERNANCE_WORKFLOW.md
  CONTEXT_PACK.md
  GITLAB_DEPLOYMENT.md
  SECURITY_MODEL.md
  ROADMAP.md
```

## Current maturity

This is a scaffold, not a production system yet. The next real build steps are:

1. Replace in-memory store with Postgres.
2. Add object storage for source evidence.
3. Add vector/hybrid search.
4. Add graph relationships.
5. Add real auth and ACL filtering.
6. Add admin review UI.
7. Add GitLab deployment variables and environment-specific secrets.
8. Add source connectors one by one.
