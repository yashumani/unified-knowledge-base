# GitHub Hosting Model

## Purpose

This document explains how to use GitHub as the control plane for Unified Knowledge Base without pretending GitHub can host the whole runtime.

GitHub can host:

```text
source code
issues and pull requests
documentation
GitHub Pages static React UI
GitHub Actions workflows
GitHub Container Registry images
```

GitHub should not be treated as the host for:

```text
FastAPI backend runtime
Ollama local LLM service
model files
Postgres or durable runtime state
background workers
private source evidence
```

The correct split is:

```text
GitHub
  ├── repository
  ├── GitHub Pages UI
  ├── GitHub Actions CI/CD
  └── GHCR API image

Your runtime machine
  ├── UKB FastAPI backend
  ├── Ollama local LLM
  ├── model files
  └── database/object storage later
```

## Recommended architecture

```text
Browser
  -> GitHub Pages React UI
    -> HTTPS UKB API endpoint on your machine/server
      -> private Ollama service
        -> local model enrichment
```

The browser should never call Ollama directly.

```text
Good:
React UI -> UKB backend -> Ollama

Bad:
React UI -> Ollama directly
```

The backend owns prompt construction, provider settings, sensitivity checks, fallback behavior, audit metadata, and governance boundaries.

## Current repository automation

### Static UI hosting

The existing workflow deploys the React UI to GitHub Pages:

```text
.github/workflows/pages.yml
```

It builds:

```text
apps/web/dist
```

and serves it at the repository Pages URL.

### API image publishing

The API image workflow is:

```text
.github/workflows/docker-publish.yml
```

It publishes the API image to GitHub Container Registry:

```text
ghcr.io/yashumani/unified-knowledge-base-api:<tag>
ghcr.io/yashumani/unified-knowledge-base-api:latest
```

This workflow is manual/tag-driven so normal UI and documentation changes do not publish runtime images by accident.

Run it from GitHub Actions:

```text
Actions -> Publish UKB API image to GHCR -> Run workflow
```

or push a tag matching:

```text
ukb-api-v*
```

### Self-hosted deployment

The runtime deployment workflow is:

```text
.github/workflows/deploy-self-hosted.yml
```

It runs only when manually triggered and only on a runner labeled:

```text
self-hosted
linux
ukb
```

This workflow does not make GitHub host the backend. It tells a machine you control to update the Docker Compose runtime.

## Runtime machine setup

Use one of these machines:

```text
local workstation
home lab Linux server
private VPS
internal enterprise Linux server
GitHub self-hosted runner machine
```

Required software:

```text
Docker
Docker Compose plugin
GitHub self-hosted runner, for GitHub-triggered deployment
sufficient disk space for Ollama models
CPU or GPU capacity for the selected local model
```

## Production Compose

The production Compose file is:

```text
deploy/docker-compose.prod.yml
```

It runs:

```text
api
ollama
```

The API is published on the configured API port. Ollama is **not** published to the host network; it is private on the Compose network.

```text
api -> http://ollama:11434
```

That keeps local LLM access behind the UKB backend.

## Environment file

Copy this file on the runtime machine:

```text
deploy/prod.env.example -> /opt/unified-knowledge-base/.env
```

Then edit the `.env` file on the runtime machine.

Important values:

```bash
UKB_ENVIRONMENT=prod
UKB_API_PORT=8000
UKB_CORS_ALLOW_ORIGINS=https://yashumani.github.io
UKB_AI_MODE=local_ai
UKB_AI_PROVIDER=ollama
UKB_AI_BASE_URL=http://ollama:11434
UKB_AI_CHAT_MODEL=llama3.1
UKB_AI_EMBEDDING_MODEL=embeddinggemma
```

Do not commit the runtime `.env` file.

## Deployment flow

### 1. Publish API image

Run:

```text
Actions -> Publish UKB API image to GHCR -> Run workflow
```

Use `latest` or a commit/tag value.

### 2. Prepare runtime server

Install and register the GitHub self-hosted runner on your Linux server.

Label it:

```text
self-hosted
linux
ukb
```

Create the deploy path:

```bash
sudo mkdir -p /opt/unified-knowledge-base
sudo chown "$USER:$USER" /opt/unified-knowledge-base
```

### 3. Deploy from GitHub Actions

Run:

```text
Actions -> Deploy UKB runtime on self-hosted runner -> Run workflow
```

Inputs:

```text
image_tag: latest or a specific tag/SHA
deploy_path: /opt/unified-knowledge-base
```

The workflow copies the production Compose file, creates `.env` if it does not exist, pulls images, and runs:

```bash
docker compose --env-file .env up -d
```

### 4. Pull Ollama models

After the Ollama container is running:

```bash
docker exec ukb-ollama ollama pull llama3.1
docker exec ukb-ollama ollama pull embeddinggemma
```

### 5. Smoke test

From the runtime server:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ai/providers
curl http://localhost:8000/ai/health
```

Expected model path:

```text
provider: ollama
mode: local_ai
base_url: http://ollama:11434
```

## Connecting GitHub Pages to the API

GitHub Pages can serve the UI, but the browser still needs a reachable backend URL.

When the API is available through HTTPS, configure a repository variable:

```text
UKB_API_BASE_URL=https://your-api-domain.example.com
```

Then the Pages workflow can build the React UI with:

```text
VITE_UKB_API_BASE_URL=${{ vars.UKB_API_BASE_URL }}
```

If this variable is not configured, the UI remains useful as a static demo and local-development frontend, but real Ollama enrichment requires a running backend.

## Security boundary

Do not expose Ollama publicly.

```text
Public internet -> UKB API only, behind HTTPS and auth later
Private network -> Ollama
```

Do not commit:

```text
real source evidence
model prompts containing private data
runtime .env files
API tokens
workplace-specific examples
private model files
```

## What GitHub is doing here

GitHub is the product and deployment control plane:

```text
version control
review
static UI hosting
image registry
manual deployment trigger
release traceability
```

Your own server remains the runtime plane:

```text
backend process
local LLM
models
data
future database
```

That is the correct split for a local-LLM Unified Knowledge Base.
