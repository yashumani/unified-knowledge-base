# GitHub Pages Deployment for the React UI

## What gets deployed

The repository contains a React + TypeScript + Vite frontend in:

```text
apps/web/
```

The GitHub Pages workflow builds that app and uploads:

```text
apps/web/dist
```

## Workflow

The deployment workflow is located at:

```text
.github/workflows/pages.yml
```

It runs on:

```text
push to main when apps/web, package.json, or the workflow changes
manual workflow_dispatch
```

## Build command

The workflow runs from the repository root:

```bash
npm install --no-audit --no-fund
npm run web:build
```

The root script delegates to the `apps/web` workspace.

## Vite base path

The Vite config uses this base path when building for GitHub Pages:

```text
/unified-knowledge-base/
```

That matches the expected project Pages URL shape:

```text
https://yashumani.github.io/unified-knowledge-base/
```

## Backend connection

GitHub Pages hosts only the static frontend. The FastAPI backend must run somewhere else.

The frontend is designed to work in two modes:

```text
Demo mode
  Uses bundled synthetic support-operations data when no backend URL is configured.

Backend-connected mode
  Calls the API when VITE_UKB_API_BASE_URL is set at build time.
```

To connect a hosted backend, add this environment variable to the workflow or repository environment:

```text
VITE_UKB_API_BASE_URL=https://your-approved-api-host.example.com
```

The backend must allow CORS from the GitHub Pages origin.

## Obsidian graph view boundary

The UI includes an Obsidian-style graph view built in React. It is not an embedded Obsidian desktop component.

This keeps the graph deployable as a static GitHub Pages site and allows it to render either synthetic graph data or backend graph projections from the UKB runtime.

## Deployment sequence

```text
1. Merge the PR into main.
2. Ensure Settings -> Pages uses GitHub Actions as the publishing source.
3. The Pages workflow builds the React app.
4. The workflow uploads apps/web/dist.
5. GitHub Pages serves the deployed UI.
```

## Previewing the Pages build locally

`vite.config.ts` derives `base` from the `GITHUB_PAGES` environment variable,
and `vite preview` reads the same config. Set it for **both** commands:

```bash
GITHUB_PAGES=true npm run web:build
cd apps/web && GITHUB_PAGES=true npx vite preview
```

Then open:

```text
http://localhost:4173/unified-knowledge-base/
```

If the preview is started without the variable it serves with base `/`, so every
request under `/unified-knowledge-base/assets/` hits the SPA fallback and gets
`index.html` back with `Content-Type: text/html`. The browser refuses the module
script and the page renders blank. That looks like a broken build and is not —
check the variable before investigating anything else.

This preview is the check worth running before every Pages deploy: it is the
only local step that exercises the subpath the workflow actually publishes to.

## Safety note

Keep public GitHub Pages data synthetic. Do not build real enterprise documents, metrics, dashboards, credentials, employer-specific examples, carrier or telecom workflows, finance-planning examples, customer data, or proprietary screenshots into the static bundle.

The approved public demo domain is documented in `docs/EXAMPLE_DOMAIN.md`.
