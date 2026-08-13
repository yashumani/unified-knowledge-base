# Ollama Local LLM Runbook

## Purpose

Unified Knowledge Base should use a local Ollama runtime for AI enrichment in this use case.

The intended default is:

```text
UKB backend -> local/internal Ollama -> structured enrichment suggestions -> human review
```

The LLM enriches context, but it does not approve or publish knowledge.

```text
LLM output = suggestion
Human review = approval
Published brain object = official context
```

## What Ollama does for UKB

Ollama is used for these UKB tasks:

```text
source classification
review brief generation
reviewer question generation
context-pack guidance
missing-context warnings
local embeddings for future semantic search and duplicate detection
```

It should not be used for:

```text
automatic approval
automatic publication
final access-control decisions
inventing evidence
bypassing source sensitivity rules
```

## Local host setup

Install Ollama, then pull the default models:

```bash
ollama pull llama3.1
ollama pull embeddinggemma
```

Start the UKB backend and UI:

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,mcp]"
make run
```

In another terminal:

```bash
npm install
npm run web:dev
```

The backend expects Ollama at:

```text
http://localhost:11434
```

Ollama's local API uses endpoints under `/api`, including `/api/generate`, `/api/chat`, and `/api/embed`.

## Docker Compose setup

The compose stack includes an `ollama` service.

```bash
docker compose up --build
```

In a separate shell, pull models into the running Ollama container:

```bash
docker exec unified-knowledge-base-ollama ollama pull llama3.1
docker exec unified-knowledge-base-ollama ollama pull embeddinggemma
```

Inside Docker Compose, the API reaches Ollama at:

```text
http://ollama:11434
```

The public browser still calls the API at:

```text
http://localhost:8000
```

## Configuration

Default local settings:

```bash
UKB_AI_ENRICHMENT_ENABLED=true
UKB_AI_MODE=local_ai
UKB_AI_PROVIDER=ollama
UKB_AI_BASE_URL=http://localhost:11434
UKB_AI_CHAT_MODEL=llama3.1
UKB_AI_EMBEDDING_MODEL=embeddinggemma
```

For Docker Compose, `UKB_AI_BASE_URL` is overridden to:

```bash
UKB_AI_BASE_URL=http://ollama:11434
```

## Fallback behavior

If Ollama is unavailable or returns invalid JSON, UKB falls back to deterministic enrichment.

Expected behavior:

```text
review workflow keeps working
review item includes fallback risk flag
knowledge is still not auto-approved
context pack can still be built from approved objects
embedding calls return deterministic fallback vectors
```

This lets local development continue even before the Ollama model is pulled.

## Testing the integration

Check the provider endpoint:

```bash
curl http://localhost:8000/ai/providers
```

Expected provider in local mode:

```json
{
  "provider": "ollama",
  "mode": "local_ai",
  "enabled": true,
  "model": "llama3.1",
  "embedding_model": "embeddinggemma",
  "base_url": "http://localhost:11434",
  "local_only": true
}
```

Check Ollama readiness:

```bash
curl http://localhost:8000/ai/health
```

Possible result before pulling models:

```json
{
  "provider": "ollama",
  "reachable": false,
  "message": "Ollama is reachable, but model(s) need to be pulled: llama3.1, embeddinggemma"
}
```

Possible result after pulling models:

```json
{
  "provider": "ollama",
  "reachable": true,
  "message": "Ollama is reachable and configured models are available."
}
```

Test local embeddings:

```bash
curl -X POST http://localhost:8000/ai/embeddings \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Incident Resolution Time", "SLA Review Dashboard"]}'
```

Expected shape:

```json
{
  "provider": "ollama",
  "model": "embeddinggemma",
  "dimensions": 768,
  "embeddings": [[...], [...]],
  "fallback_used": false
}
```

The exact dimension depends on the embedding model. If Ollama is unavailable, `fallback_used` is true and deterministic scaffold vectors are returned.

Submit context:

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

Then inspect the review queue:

```bash
curl http://localhost:8000/review/queue
```

The review item should include `ai_enrichment` with provider metadata, review brief, validation findings, and reviewer questions.

## Production boundary

For workplace or enterprise deployment:

```text
run Ollama on an internal server
keep the API and Ollama on a private network
block public access to Ollama's port
use only approved local models
log provider failures without logging sensitive prompts unless explicitly allowed
```

GitHub Pages remains only the static frontend. Real Ollama enrichment requires a running backend connected to an internal/local Ollama service.
