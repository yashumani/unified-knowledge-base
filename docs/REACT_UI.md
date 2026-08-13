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
```

The app is intentionally light on dependencies. The first graph view is a custom SVG implementation rather than a graph-library dependency so the project stays easy to run inside constrained GitLab/Linux environments.

## Features

- API connection status
- Offline demo fallback when the backend is unavailable
- Context submission form
- Human review queue
- Approve/reject reviewer actions
- Published object browser
- Context-pack explorer
- Obsidian-style graph visualization

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
GET /brain/graph
```

This endpoint returns a UI-oriented graph projection generated from the in-memory store for now. Later this should be backed by the durable graph/relationship store.

## Running locally

From the repository root:

```bash
npm install
npm run web:dev
```

In another shell:

```bash
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
api  -> http://localhost:8000
web  -> http://localhost:5173
```

## Design boundary

The UI must not bypass governance. Review actions, graph data, and context packs come from the backend APIs. The graph can visualize candidate knowledge, but official runtime answers should still use approved knowledge by default.

## Next UI iterations

1. Add authentication-aware user identity.
2. Add reviewer assignment and filters.
3. Add edit-before-approval flow.
4. Add source evidence viewer with diff support.
5. Add persistent graph layout positions.
6. Add real graph traversal once the backend has a graph store.
7. Add visual conflict detection between definitions.
