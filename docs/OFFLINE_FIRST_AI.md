# Offline-First AI Brain

## Decision

The AI Brain must be useful even when hosted AI and internet access are unavailable.

AI should be a pluggable accelerator, not a hard dependency. For this Unified Knowledge Base use case, the default local AI provider is **Ollama**.

## Modes

### 1. Offline, local AI

Default UKB development mode.

Uses a local Ollama service running on the user's machine or internal server.

Uses:

- classify documents
- summarize source evidence
- enrich candidate metrics and rules
- generate reviewer questions
- produce context-pack guidance
- generate embeddings later

### 2. Offline, no model

Fallback mode for locked-down machines, CI, or environments where Ollama is not installed yet.

Works with:

- YAML/Markdown brain objects
- deterministic validation
- rule-based classification
- local review workflow
- keyword retrieval
- context-pack generation from approved objects

This mode is enough for governance, documentation, and basic retrieval.

### 3. Hosted AI

Not the default path for this repository.

Hosted providers should be used only in approved private deployments with explicit policy, network, and data-sensitivity controls.

### 4. Hybrid

Future policy-aware mode.

Uses local AI by default and hosted AI only for approved tasks.

## Local AI provider abstraction

The runtime calls an internal interface, not the frontend and not a browser-side model endpoint:

```text
AIProvider
  enrich_source(source, content, baseline_candidate) -> AIEnrichmentResult
  enrich_context_pack(context_pack) -> ContextPack
  embed(texts) -> vectors later
```

Implementations can include:

```text
OllamaProvider      local LLM/embedding service, default for UKB
NoopProvider        deterministic fallback
HostedProvider      future/private extension point only
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

## Why local Ollama matters

For many enterprise-like environments, the limiting factor is not model quality. It is data governance, network restrictions, and approval workflow.

Local Ollama support lets teams prototype inside constrained environments while keeping prompts and context inside the local/internal runtime boundary.

## Suggested local stack

MVP local stack:

```text
FastAPI runtime
React UI
Ollama local LLM service
Postgres or SQLite for metadata later
local filesystem/object store for evidence
keyword retrieval first
local embeddings later
```

## Configuration example

```yaml
runtime:
  mode: local_ai
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

Environment equivalent:

```bash
UKB_AI_ENRICHMENT_ENABLED=true
UKB_AI_MODE=local_ai
UKB_AI_PROVIDER=ollama
UKB_AI_BASE_URL=http://localhost:11434
UKB_AI_CHAT_MODEL=llama3.1
UKB_AI_EMBEDDING_MODEL=embeddinggemma
```

## Failure behavior

If Ollama is unavailable:

```text
continue deterministic validation
continue manual review
continue serving approved context packs
mark enrichment with fallback risk flags
never silently downgrade governance
```

## Deployment inside GitLab/Linux constraints

```text
GitLab repo
  -> GitLab CI
  -> Docker image
  -> internal Linux server
  -> API service
  -> MCP service
  -> Ollama sidecar or internal Ollama host
```

The API should still start if Ollama is unavailable, but local Ollama is the preferred enrichment path for this use case.
