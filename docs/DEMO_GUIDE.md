# Demo Guide

## Demo goal

Show that Unified Knowledge Base is not a generic chatbot. It is a governed AI Brain runtime that converts submitted context into candidate knowledge, requires human review, and then serves approved context to API, SDK, or MCP consumers.

## Workplace-safe example policy

Use synthetic data only. Do not use employer documents, proprietary metric definitions, internal screenshots, customer data, credentials, private dashboard exports, telecom examples, or finance-planning examples that could resemble workplace reporting.

This demo uses one neutral scenario:

```text
Domain: support
Metric: Incident Resolution Time
Report: SLA Review Dashboard
Rule: SLA Review Window
Owner: Support Operations
```

## Audience

Use this demo for:

- engineering leads evaluating the architecture
- data teams evaluating governed metric-context use cases
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
node packages/create-ukb-brain/bin/create-ukb-brain.mjs demo-support-brain --offline
```

Expected result:

```text
Created Demo Support Brain at .../demo-support-brain
Next steps:
  cd demo-support-brain
  review brain.config.yaml
  add synthetic or approved context only
```

Show the generated structure:

```bash
find demo-support-brain -maxdepth 3 -type f | sort
```

Point out:

```text
brain.config.yaml
plugins/context_source.py
domains/support/metrics/metric_template.yaml
```

### 2. Run the API

```bash
uvicorn ukb.api.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000/docs
```

The API is the platform backend for ingestion, review, object browsing, audit, graph projection, and context packs.

### 3. Submit context

```bash
curl -X POST http://localhost:8000/ingestion/submissions \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Incident Resolution Time Definition",
    "source_type": "document",
    "submitted_by": "demo.user",
    "domain": "support",
    "content": "Incident Resolution Time is the average elapsed time from incident creation to resolved status for product support cases, excluding duplicate incidents and customer-wait periods. It appears in the SLA Review Dashboard and is owned by Support Operations. Recently resolved incidents may need 24 hours for quality review tags to settle."
  }'
```

### 4. Review queue

```bash
curl http://localhost:8000/review/queue
```

The candidate should be classified as a metric-like knowledge object and require human review.

### 5. Approve the candidate

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

Expected point to explain:

```text
The response should include approved knowledge, source evidence, confidence, caveats, and recommended follow-ups. It should not invent unsupported operational causes.
```

### 7. Run the React UI

```bash
npm install
npm run web:dev
```

Open:

```text
http://localhost:5173
```

The React console includes context submission, review queue, context-pack explorer, and an Obsidian-style graph view over the AI Brain objects.

## Fallback demo

If the API is not running, the React UI falls back to synthetic local demo data using the same neutral support scenario.

## Demo close

The product claim is not "chat with documents." The product claim is:

```text
Convert scattered context into governed, reviewable, reusable brain objects that AI applications can safely consume.
```
