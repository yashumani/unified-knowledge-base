# React UI Console

## Purpose

The React UI gives the governed AI Brain a human-facing console. It is intentionally separate from the FastAPI backend so the backend remains the runtime source of truth and the UI remains an adapter.

## Location

```text
apps/web/
```

## Stack

```text
React
TypeScript
Vite
Custom SVG graph renderer
FastAPI backend
Local Ollama enrichment through the backend
```

The app is intentionally light on dependencies. The first graph view is a custom SVG implementation rather than a graph-library dependency so the project stays easy to run inside constrained GitLab/Linux environments.

## Design direction

The current UI uses a Framer-inspired dark SaaS command-center design: side navigation, bento cards, a product-grade hero, glass panels, graph-first storytelling, and clearer demo/connected state separation.

See:

```text
docs/UI_FRAMER_REDESIGN.md
```

## Features

- API connection status
- Local Ollama enrichment provider status
- Offline demo fallback when the backend is unavailable
- Context submission form
- Human review queue
- AI review brief and validation findings
- Approve/reject reviewer actions
- Published object browser
- Context-pack explorer with AI guidance and missing-context warnings
- Obsidian-style graph visualization

## Local LLM / AI enrichment integration

The UI surfaces local Ollama enrichment as reviewer support, not as automatic approval.

```text
React UI -> FastAPI backend -> Ollama local/internal API
```

Visible AI elements include:

```text
provider mode and model in the side rail
AI-enriched review count
AI review brief per candidate
validation findings and severity
reviewer questions
AI context-pack guidance
missing-context warnings
AI enrichment nodes in graph metadata
```

See:

```text
docs/OLLAMA_LOCAL_LLM.md
docs/LLM_FEATURE_ARCHITECTURE.md
```

## End-to-end workflow guide

Use the dedicated walkthrough when showing the UI console from submission to approved context pack:

```text
docs/UI_CONSOLE_END_TO_END.md
```

That guide covers both static GitHub Pages demo mode and backend-connected local mode, using only the neutral support-operations sample domain.

## Graph view

The graph is not an embedded Obsidian desktop component. It is an Obsidian-style graph projection over UKB data.

Nodes can represent:

```text
source_evidence
review_item
ai_enrichment
candidate_object
Metric
Report
BusinessRule
Dataset
```

Edges can represent:

```text
evidence_for
submitted_as
reviews
enriches_review
appears_in
governed_by
related_to
calculated_from
```

The UI supports:

```text
search/filter
published-only view
review/candidate view
source-only view
local graph mode
zoom
pan
node detail inspection
active relationship highlighting
```

## Backend support

The backend exposes:

```text
GET  /brain/graph
GET  /ai/providers
POST /review/items/{review_item_id}/enrich
GET  /review/items/{review_item_id}/ai-enrichment
```

The graph endpoint returns a UI-oriented graph projection generated from the in-memory store for now. Later this should be backed by the durable graph/relationship store.

## Running locally with Ollama

Pull the local models first:

```bash
ollama pull llama3.1
ollama pull embeddinggemma
```

From the repository root:

```bash
npm install
npm run web:dev
```

In another shell:

```bash
cp .env.example .env
source .venv/bin/activate
make run
```

Open:

```text
http://localhost:5173
```

## Docker Compose

```bash
docker compose up --build
```

This starts:

```text
api     -> http://localhost:8000
web     -> http://localhost:5173
ollama  -> http://localhost:11434
```

Pull models into the running container:

```bash
docker exec unified-knowledge-base-ollama ollama pull llama3.1
docker exec unified-knowledge-base-ollama ollama pull embeddinggemma
```

## Design boundary

The UI must not bypass governance. Review actions, graph data, AI enrichment, and context packs come from the backend APIs. The graph can visualize candidate knowledge and AI review briefs, but official runtime answers should still use approved knowledge by default.

The UI does not call Ollama directly; the backend calls Ollama and returns only review-safe enrichment payloads.

## Pipeline structure

The console is organised around the five governed steps, in order:

```text
1 Submit    #context-ingestion   compiler creates a candidate
2 Enrich    #enrichment-lab      provider produces a reviewer brief
3 Review    #review-queue        a human approves, rejects, or requests changes
4 Publish   #published-objects   approved objects become official context
5 Compose   #context-pack        a governed pack for an AI app
```

Then `#brain-map` and `#activity`.

`src/pipeline/steps.ts` is the only place these labels, their order and their
anchors are defined. The stepper, the side navigation and every section heading
render from it. Adding or renaming a step means editing that file and nothing
else — do not reintroduce a parallel list.

Each step derives `locked | available | complete` from live state, and pairs a
what-just-happened line with a fixed governance statement.

## Demo mode

The GitHub Pages build has no API token, so it always runs in demo mode. Demo
mode is not a set of canned screens: `src/demo` is a browser port of
`ukb.ai.providers.noop`, `BrainCompiler`, and the retrieval and context-pack
services, so classification, enrichment and pack composition all really run.
Nothing in `src/demo` may import from `src/api`.

Artifacts produced this way are labelled with their provenance. Keep it that
way — demo mode must never be mistaken for connected mode.

## Next UI iterations

1. Add authentication-aware user identity.
2. Add reviewer assignment and filters.
3. Add edit-before-approval flow.
4. Add source evidence viewer with diff support.
5. Add persistent graph layout positions.
6. Add real graph traversal once the backend has a graph store.
7. Add visual conflict detection between definitions.
8. Add reviewer-editable AI extracted fields.
9. Add AI task history and provider-fallback warnings.
10. Add Ollama model availability and provider-health details.
