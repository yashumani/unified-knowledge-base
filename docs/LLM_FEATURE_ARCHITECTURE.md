# LLM Feature Architecture

## Purpose

The LLM feature is an **AI Enrichment Layer** for the Unified Knowledge Base runtime.

For this use case, the active LLM path is **local Ollama**. Hosted providers are not part of the default workflow.

```text
source context
  -> deterministic compiler
  -> local Ollama enrichment
  -> candidate + review brief + validation findings
  -> human review
  -> approved brain object
  -> context pack
```

## Core rule

```text
LLM output = suggestion
Human review = approval
Published brain object = official context
```

The LLM must never bypass governance, access control, or human review.

## Local Ollama boundary

Unified Knowledge Base should call Ollama from the backend only.

```text
React UI  -> FastAPI backend -> Ollama local/internal API
```

Do not call Ollama directly from the browser. The backend owns:

```text
provider configuration
prompt construction
source sensitivity checks
fallback behavior
review-item enrichment
context-pack enrichment
audit metadata
```

## What Ollama should do

### Source classification

Detect what the submitted source appears to be:

```text
metric definition
report or dashboard context
business rule
SQL or lineage context
general context
```

Outputs:

```text
source kind
domain
topics
suggested tags
summary
confidence
```

### Candidate enrichment

Ollama enriches the baseline deterministic candidate with reviewer-facing metadata.

It can suggest:

```text
better source summary
candidate object type
candidate topics
relationship hints
review brief
reviewer questions
validation findings
missing context warnings
```

It does not publish the candidate.

### Relationship suggestion

Identify possible graph edges:

```text
appears_in
governed_by
related_to
calculated_from
owned_by
```

These are suggestions for review, not official graph truth.

### Validation findings

Generate reviewer-facing checks:

```text
missing owner
ambiguous definition
incomplete formula
exclusion rule needs review
freshness caveat detected
possible duplicate
missing evidence
sensitivity concern
```

### Review brief

Generate a short reviewer summary:

```text
what was extracted
why it matters
what is missing
what questions the reviewer should ask
recommended reviewer action
```

### Context-pack enrichment

For approved context only, enrich context packs with:

```text
AI guidance
missing context warnings
follow-up questions
retrieval hints
```

Ollama must not invent facts that are absent from approved objects or source evidence.

## What the LLM must not do

```text
approve knowledge
publish knowledge
make final access-control decisions
see restricted data before policy filtering
invent evidence
silently resolve conflicting definitions
override human reviewers
store secrets in the frontend
call hosted APIs from the browser
```

## Provider modes

### local_ai

Default mode for this repository.

```text
Provider: ollama
Network: local/internal only
Default base URL: http://localhost:11434
Default model: llama3.1
Default embedding model: embeddinggemma
Use cases: extraction, review briefs, context-pack guidance, embeddings later
```

### offline_no_model

Fallback mode for locked-down environments, CI, or machines without Ollama.

```text
Provider: noop
Network: none
Secrets: none
Behavior: deterministic enrichment and validation only
```

### hosted_ai

Not part of the default UKB local path.

The hosted adapter remains a future/private extension point, but public demos and local development should use Ollama or the deterministic fallback.

## Current implementation

### Backend models

Added to `src/ukb/models.py`:

```text
AIProviderName
AIEnrichmentMode
AITaskStatus
ValidationSeverity
SourceClassification
SuggestedRelationship
ValidationFinding
AIReviewBrief
AIEnrichmentResult
AIProviderStatus
```

`ReviewItem` has:

```text
ai_enrichment: AIEnrichmentResult | None
```

`ContextPack` has:

```text
ai_guidance: str | None
missing_context: list[str]
```

### Provider adapters

```text
src/ukb/ai/providers/base.py
src/ukb/ai/providers/noop.py
src/ukb/ai/providers/ollama.py
src/ukb/ai/providers/openai_provider.py
```

The active local provider is:

```text
src/ukb/ai/providers/ollama.py
```

### Service facade

```text
src/ukb/ai/service.py
```

The service owns:

```text
provider routing
server-side settings
safe fallback
hosted-provider sensitivity blocking
context-pack enrichment
```

### API endpoints

```text
GET  /ai/providers
POST /review/items/{review_item_id}/enrich
GET  /review/items/{review_item_id}/ai-enrichment
```

Existing endpoints are also enriched:

```text
POST /ingestion/submissions
  saves source evidence
  creates baseline candidate
  attaches local Ollama enrichment to review item

POST /brain/context-pack
  builds normal context pack
  adds AI guidance and missing-context warnings
```

## Configuration

Default local Ollama settings:

```bash
UKB_AI_ENRICHMENT_ENABLED=true
UKB_AI_MODE=local_ai
UKB_AI_PROVIDER=ollama
UKB_AI_BASE_URL=http://localhost:11434
UKB_AI_CHAT_MODEL=llama3.1
UKB_AI_EMBEDDING_MODEL=embeddinggemma
```

Docker Compose overrides the API container's base URL to:

```bash
UKB_AI_BASE_URL=http://ollama:11434
```

Deterministic fallback:

```bash
UKB_AI_MODE=offline_no_model
UKB_AI_PROVIDER=noop
UKB_AI_CHAT_MODEL=deterministic
```

## UI behavior

The React console shows:

```text
AI provider mode and model
AI-enriched review count
AI review brief
validation findings
reviewer questions
AI context-pack guidance
missing-context warnings
AI enrichment nodes in graph projection
```

## Security model

### Local-only default

The default UKB path sends enrichment requests only to the configured local/internal Ollama endpoint.

### No browser-side LLM calls

The React app never receives model credentials and never calls Ollama directly.

### Safe fallback

If Ollama fails or returns invalid JSON:

```text
fallback to NoopProvider
record provider_fallback in risk flags
keep review workflow operational
never silently approve knowledge
```

## Acceptance criteria

The local Ollama feature is working when:

```text
1. Ollama is running locally or as a Docker Compose service.
2. The default chat model is pulled.
3. User submits support context through the UI or API.
4. Backend saves source evidence.
5. Baseline compiler creates a candidate.
6. Ollama enrichment attaches classification, review brief, findings, and suggested relationships.
7. Reviewer sees AI guidance but still approves/rejects manually.
8. Approved object appears in the brain store.
9. Context pack includes approved evidence plus AI guidance/missing-context warnings.
10. Graph projection shows AI enrichment as review-supporting metadata.
```

## Future work

```text
persistent AI task table
provider health checks and model availability checks
structured-output schemas per local model
embedding generation and semantic duplicate detection
reviewer-editable extracted fields
AI-generated documentation from approved objects
LLM evaluation suite with golden questions
streaming task status for long document enrichment
```
