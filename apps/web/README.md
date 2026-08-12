# UKB Web Console

React/Vite UI for the Unified Knowledge Base AI Brain backend.

## What it provides

- Context submission form
- Human review queue
- Published knowledge object browser
- Context-pack explorer
- Obsidian-style graph view for sources, candidates, approved objects, and relationships
- Offline demo mode when the API is unavailable

## Local development

From the repository root:

```bash
npm install
npm run web:dev
```

Run the API separately:

```bash
source .venv/bin/activate
make run
```

Open:

```text
http://localhost:5173
```

## API configuration

The UI reads:

```text
VITE_UKB_API_BASE_URL=http://localhost:8000
```

Copy `.env.example` to `.env.local` inside `apps/web/` to override the API base URL.

## Graph view boundary

This app does not embed Obsidian's desktop graph internals. It implements an Obsidian-style graph projection from UKB backend data: source evidence, review items, candidate objects, approved knowledge objects, and typed relationships.
