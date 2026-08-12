# Demo Guide

## Demo goal

Show that Unified Knowledge Base is not a generic chatbot. It is a governed AI Brain runtime that converts submitted context into candidate knowledge, requires human review, and then serves approved context to API, SDK, or MCP consumers.

## Audience

Use this demo for:

- engineering leads evaluating the architecture
- data and BI teams evaluating metric-intelligence use cases
- governance reviewers evaluating approval and audit controls
- AI app developers evaluating API/MCP consumption
- enterprise stakeholders evaluating offline-first constraints

## Demo promise

By the end of the walkthrough, the audience should understand this flow:

```text
Create a brain package
  -> run the runtime
  -> submit context
  -> AI/compiler classifies it
  -> human approves it
  -> brain publishes it
  -> app asks for a context pack
```

## What to prepare

Use synthetic data only. Do not use employer documents, proprietary metric definitions, internal screenshots, customer data, credentials, or private dashboard exports in this public scaffold.

Install local dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,mcp]"
```

Optional Node check for the starter package:

```bash
node --version
node packages/create-ukb-brain/bin/create-ukb-brain.mjs --help
```

## Five-minute architecture talk track

1. Enterprises already have documents, metrics, dashboards, SQL, and human knowledge.
2. Most AI apps retrieve fragments but lack business meaning.
3. The AI Brain compiles context into governed brain objects.
4. AI extraction creates candidates, not truth.
5. Human review publishes official knowledge.
6. Context packs expose approved knowledge to API, SDK, and MCP consumers.
7. Plugins allow teams to add sources and validations without forking the runtime.
8. Offline-first mode lets the runtime work even without hosted AI.

## Live demo path

### 1. Generate a domain brain package

Before the npm package is published, run the local initializer:

```bash
node packages/create-ukb-brain/bin/create-ukb-brain.mjs demo-finance-brain --offline
```

Expected result:

```text
Created Demo Finance Brain at .../demo-finance-brain
Next steps:
  cd demo-finance-brain
  review brain.config.yaml
  add synthetic or approved context only
```

Show the generated structure:

```bash
find demo-finance-brain -maxdepth 3 -type f | sort
```

Point out:

```text
brain.config.yaml
plugins/context_source.py
domains/finance/metrics/metric_template.yaml
```

### 2. Run the API

```bash
uvicorn ukb.api.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000/docs
```

The API is the platform backend for ingestion, review, object browsing, audit, and context packs.

### 3. Submit context

```bash
curl -X POST http://localhost:8000/ingestion/submissions \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Device Revenue Definition",
    "source_type": "document",
    "submitted_by": "demo.user",
    "domain": "finance",
    "content": "Device Revenue is a metric for revenue generated from device sales, excluding service revenue. It appears in the CFO KPI dashboard and is owned by Finance BI. Month-end finance adjustments may not be complete before WD4."
  }'
```

Explain what happened:

```text
The compiler preserved source evidence.
It classified the submission.
It created a candidate object.
It placed the object in the human review queue.
```

### 4. Show the review queue

```bash
curl http://localhost:8000/review/queue
```

Point out the governance state:

```text
human_review_required
```

The candidate is useful, but it is not yet official brain knowledge.

### 5. Approve the item

Copy the `id` from the review item and run:

```bash
curl -X POST http://localhost:8000/review/items/{review_item_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"reviewed_by": "domain.reviewer", "comment": "Approved for synthetic demo."}'
```

Explain:

```text
The review decision publishes the candidate object.
The audit log records the approval event.
The object is now available to context-pack consumers.
```

### 6. Request a context pack

```bash
curl -X POST http://localhost:8000/brain/context-pack \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What should I know before explaining Device Revenue?",
    "user_id": "demo.user",
    "domains": ["finance"],
    "mode": "metric_definition"
  }'
```

Point out:

```text
answer_guidance
knowledge_objects
evidence
confidence
caveats
recommended_followups
```

The output is not the final answer. It is the governed context a chatbot, agent, BI copilot, or report generator can use.

### 7. Run the MCP adapter

```bash
python -m ukb.mcp.server
```

Explain:

```text
MCP is the agent interface.
It exposes brain tools and resources to LLM clients.
It calls the same runtime services as the API.
It does not bypass governance.
```

## Animated diagram walkthrough

Open this file in a browser:

```text
docs/demo/animated-diagrams.html
```

Use the four animated scenes:

1. Brain compiler loop
2. Plugin extension mesh
3. Offline-first AI modes
4. Adapter hub: REST, MCP, SDK, npm starter

This file has no external dependencies and can be used in an offline meeting.

## Fallback demo when code cannot run

Use:

1. `docs/demo/demo-slides.html`
2. `docs/demo/animated-diagrams.html`
3. `docs/demo/slides-outline.md`

Narrate the same flow without running commands. A PowerPoint presenter export can be generated separately when needed, but the committed repository deck is the offline HTML file.

## Demo success criteria

A successful demo proves:

- a new brain package can be generated from a template
- submitted context becomes a review item
- human approval publishes the brain object
- context packs include evidence and caveats
- REST and MCP are adapters over the same governance runtime
- offline-first operation remains valid even without hosted AI

## Current limitations to state clearly

The scaffold is not production-ready yet. It currently uses:

- in-memory development storage
- heuristic classification
- basic keyword retrieval
- no production auth
- no persistent audit database
- no review UI yet
- no real vector or graph retrieval yet

The next engineering step is durable storage plus a reviewer interface.
