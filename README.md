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
      -> local Ollama enrichment
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

## Local LLM principle

Unified Knowledge Base uses **local Ollama** for this LLM enrichment use case.

```text
React UI -> FastAPI backend -> local/internal Ollama -> reviewable enrichment
```

Ollama can help classify, summarize, enrich, validate, and generate reviewer questions, but it cannot approve or publish official knowledge.

```text
LLM output = suggestion
Human review = approval
Published brain object = official context
```

See:

```text
docs/OLLAMA_LOCAL_LLM.md
docs/LLM_FEATURE_ARCHITECTURE.md
```

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
│ docs, data, SQL     │      │ classify + enrich      │      │ objects + evidence   │
└────────────────────┘      └───────────┬───────────┘      └─────────┬───────────┘
                                        │                            │
                              local Ollama enrichment                │
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

## Quick start with local Ollama

### 1. Pull local models

Install Ollama, then pull the default models:

```bash
ollama pull llama3.1
ollama pull embeddinggemma
```

### 2. Install Python dependencies

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,mcp]"
```

### 3. Run the API

```bash
uvicorn ukb.api.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000/docs
```

Every route except `/health` requires the API token from `.env`. Export it once:

```bash
export UKB_API_TOKEN=dev-token-change-me
```

Check the local LLM provider:

```bash
curl -H "Authorization: Bearer $UKB_API_TOKEN" http://localhost:8000/ai/providers
```

Expected provider:

```text
ollama
```

### 4. Run the React UI

```bash
cp apps/web/.env.example apps/web/.env
npm install
npm run web:dev
```

`VITE_UKB_API_TOKEN` must match the backend `UKB_API_TOKEN`, or the console falls
back to demo mode.

Open:

```text
http://localhost:5173
```

### 5. Submit sample context

```bash
curl -X POST http://localhost:8000/ingestion/submissions \
  -H "Authorization: Bearer $UKB_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Incident Resolution Time Definition",
    "source_type": "document",
    "submitted_by": "demo.user",
    "domain": "support",
    "content": "Incident Resolution Time is the average elapsed time from incident creation to resolved status for product support cases, excluding duplicate incidents and customer-wait periods. It appears in the SLA Review Dashboard and is owned by Support Operations."
  }'
```

The review item should include an `ai_enrichment` payload. If Ollama is unavailable, UKB falls back to deterministic enrichment and the review workflow still works.

### 6. Review queue

```bash
curl -H "Authorization: Bearer $UKB_API_TOKEN" http://localhost:8000/review/queue
```

### 7. Approve a review item

Replace `{review_item_id}` with the ID from the queue.

```bash
curl -X POST http://localhost:8000/review/items/{review_item_id}/approve \
  -H "Authorization: Bearer $UKB_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reviewed_by": "domain.reviewer", "comment": "Approved for synthetic demo."}'
```

### 8. Request a context pack

```bash
curl -X POST http://localhost:8000/brain/context-pack \
  -H "Authorization: Bearer $UKB_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Why did incident resolution time increase?",
    "user_id": "demo.user",
    "domains": ["support"],
    "mode": "executive_insight"
  }'
```

## Access model

Two controls run before any context reaches a consumer.

**Transport auth.** Every route except `/health` requires `UKB_API_TOKEN`, sent as
`Authorization: Bearer <token>` or `X-API-Token: <token>`. This is a single shared
secret, not user identity; it gates access to the service, not between users.

**Clearance filtering.** Knowledge objects and source evidence carry a sensitivity
(`public` < `internal` < `confidential` < `restricted`). Anything above the caller's
clearance is dropped during retrieval, before a context pack is composed, and the
same filter applies to `/brain/objects`, `/brain/graph`, and the MCP adapter.

`access_decision` reports what the policy actually did:

```text
allowed   nothing was blocked, or some matches were returned
          (caveats state how many were withheld)
denied    matches existed but every one was above the caller's clearance
```

An empty result with nothing blocked stays `allowed` — that is missing context,
not a denial.

Clearance follows the authenticated principal, never `user_id` in the request
body. The body field is client-asserted and is recorded for audit attribution
only; honoring it would let any caller pick their own clearance.

Until SSO/OIDC lands, every token holder shares `UKB_DEFAULT_USER_CLEARANCE`.
Set it to the least-privileged consumer level and grant specific principals
upward through `UKB_USER_CLEARANCES`.

## Docker Compose with Ollama

```bash
docker compose up --build
```

Pull models into the running Ollama container:

```bash
docker exec unified-knowledge-base-ollama ollama pull llama3.1
docker exec unified-knowledge-base-ollama ollama pull embeddinggemma
```

Services:

```text
api     -> http://localhost:8000
web     -> http://localhost:5173
ollama  -> http://localhost:11434
```

Inside Docker Compose, the API reaches Ollama at `http://ollama:11434`.

## GitHub hosting model

GitHub is the control plane, not the full runtime host.

GitHub hosts:

```text
source code
pull requests and issues
GitHub Pages static React UI
GitHub Actions workflows
GitHub Container Registry API images
```

Your machine or private server hosts:

```text
UKB FastAPI backend
Ollama local LLM
model files
future database and object storage
```

The deployment assets are:

```text
.github/workflows/pages.yml              Static React UI to GitHub Pages
.github/workflows/docker-publish.yml     API image to GHCR
.github/workflows/deploy-self-hosted.yml Runtime update through self-hosted runner
deploy/docker-compose.prod.yml           API + private Ollama production Compose
deploy/prod.env.example                  Runtime environment template
```

See:

```text
docs/GITHUB_HOSTING_MODEL.md
```

## Run the MCP server

```bash
python -m ukb.mcp.server
```

MCP clients are LLM agents, so they submit and read but cannot approve. The
`approve_review_item` tool returns a refusal unless an operator sets
`UKB_MCP_ALLOW_APPROVAL=true` for a supervised environment. Agents are treated as
a single `mcp-client` principal for clearance, so naming a different user in a
tool argument does not widen access.

## Repository map

```text
src/ukb/
  ai/                  local Ollama enrichment providers and service facade
  api/                 FastAPI application
  mcp/                 MCP adapter
  services/            compiler, governance, retrieval, graph, context-pack logic
  models.py            Pydantic contracts
  store.py             development store

apps/web/              React console

deploy/                production Compose and environment templates

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
  GITHUB_HOSTING_MODEL.md
  GITHUB_PAGES_DEPLOYMENT.md
  LLM_FEATURE_ARCHITECTURE.md
  OLLAMA_LOCAL_LLM.md
  REACT_UI.md
  WORKPLACE_SAFE_EXAMPLES.md
```

## Current maturity

This is a scaffold, not a production system yet. The next real build steps are:

1. Replace in-memory store with Postgres.
2. Add object storage for source evidence.
3. Add vector/hybrid search using local embeddings.
4. Add graph relationships.
5. Replace the shared API token with SSO/OIDC and per-user roles. Sensitivity
   filtering already runs at retrieval time; what is missing is real identity to
   drive it, so today every token holder shares one clearance.
6. Add persistent review UI flows.
7. Harden local Ollama deployment for private GitLab/Linux environments.
8. Add source connectors one by one.
