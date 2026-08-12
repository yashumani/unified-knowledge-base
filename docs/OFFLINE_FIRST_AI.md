# Offline-First AI Brain

## Decision

The AI Brain must be useful even when hosted AI and internet access are unavailable.

AI should be a pluggable accelerator, not a hard dependency.

## Modes

### 1. Offline, no model

Works with:

- YAML/Markdown brain objects
- deterministic validation
- rule-based classification
- local review workflow
- keyword retrieval
- context-pack generation from approved objects

This mode is enough for governance, documentation, and basic retrieval.

### 2. Offline, local AI

Uses local model services running inside the user's machine or internal server.

Potential uses:

- classify documents
- summarize source evidence
- extract candidate metrics and rules
- generate embeddings
- rerank search results
- draft review notes

### 3. Hosted AI

Uses approved hosted model providers only when policy allows it.

Potential uses:

- higher-quality extraction
- conflict explanation
- narrative generation
- advanced reasoning over context packs

### 4. Hybrid

Uses local AI for default work and hosted AI only for approved tasks.

## Local AI provider abstraction

The runtime should call an internal interface, not a specific vendor:

```text
AIProvider
  summarize(text) -> summary
  classify(text) -> labels
  extract(text, schema) -> candidates
  embed(texts) -> vectors
  rerank(query, candidates) -> ranked candidates
```

Implementations can include:

```text
NoopProvider        deterministic fallback
OllamaProvider      local LLM/embedding service
LlamaCppProvider    local model runtime
HostedProvider      approved enterprise model endpoint
```

## Important product rule

The brain must distinguish between:

```text
approved knowledge
candidate knowledge
AI-generated suggestion
human-authored source evidence
```

A local model may help create candidates, but it should not publish official knowledge.

## Why local AI matters

For many enterprises, the limiting factor is not model quality. It is data governance, network restrictions, and approval workflow.

Local AI support lets teams prototype inside constrained environments while keeping the architecture compatible with hosted AI later.

## Suggested local stack

MVP local stack:

```text
FastAPI runtime
Postgres or SQLite for metadata
local filesystem/object store for evidence
keyword retrieval first
optional Ollama for local generation and embeddings
```

Ollama's embedding documentation describes local embedding generation through its CLI and HTTP API, which makes it a practical optional adapter for local semantic retrieval experiments.

## Configuration example

```yaml
runtime:
  mode: offline_first
  ai:
    local:
      enabled: true
      provider: ollama
      endpoint: http://localhost:11434
      chat_model: llama3.1
      embedding_model: embeddinggemma
    hosted:
      enabled: false
```

## Failure behavior

If local or hosted AI is unavailable:

```text
continue deterministic validation
continue manual review
continue serving approved context packs
mark AI classification as unavailable
never silently downgrade governance
```

## Deployment inside GitLab/Linux constraints

```text
GitLab repo
  -> GitLab CI
  -> Docker image
  -> internal Linux server
  -> API service
  -> optional MCP service
  -> optional local AI sidecar
```

The local AI sidecar should be optional. The API should start without it.
