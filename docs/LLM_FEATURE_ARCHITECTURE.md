# LLM Feature Architecture

## Purpose

The LLM feature is an **AI Enrichment Layer** for the governed AI Brain runtime.

It helps the platform classify, extract, validate, and summarize context, but it does not approve or publish official knowledge.

```text
source context
  -> deterministic compiler
  -> AI enrichment layer
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

## What the LLM should do

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

### Candidate extraction

Produce candidate knowledge objects, such as:

```text
Metric
Report
BusinessRule
Dataset
Process
Decision
NarrativeTemplate
GlossaryTerm
```

The candidate remains unapproved until a reviewer acts.

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

The LLM must not invent facts that are absent from approved objects or source evidence.

## What the LLM must not do

```text
approve knowledge
publish knowledge
make final access-control decisions
see restricted data before policy filtering
invent evidence
silently resolve conflicting definitions
override human reviewers
store API keys in the frontend
call hosted APIs from the browser
```

## Provider modes

### offline_no_model

Default mode.

```text
Provider: noop
Network: none
Secrets: none
Behavior: deterministic enrichment and validation only
```

### local_ai

For internal/local model use.

```text
Provider: ollama
Network: local/internal
Default base URL: http://localhost:11434
Use cases: extraction, review briefs, context-pack guidance, embeddings later
```

### hosted_ai

For approved hosted providers.

```text
Provider: openai
Network: hosted API
Secrets: server-side environment variables only
Use cases: higher-quality extraction, summaries, review questions
```

### hybrid

Future policy-aware mode.

```text
local AI by default
hosted AI only for approved sources/tasks
restricted sources stay local or deterministic unless explicitly allowed
```

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

`ReviewItem` now has:

```text
ai_enrichment: AIEnrichmentResult | None
```

`ContextPack` now has:

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
  attaches AI enrichment to review item

POST /brain/context-pack
  builds normal context pack
  adds AI guidance and missing-context warnings
```

## Configuration

Default offline-safe settings:

```bash
UKB_AI_ENRICHMENT_ENABLED=true
UKB_AI_MODE=offline_no_model
UKB_AI_PROVIDER=noop
UKB_AI_CHAT_MODEL=deterministic
```

Local Ollama example:

```bash
UKB_AI_PROVIDER=ollama
UKB_AI_MODE=local_ai
UKB_AI_BASE_URL=http://localhost:11434
UKB_AI_CHAT_MODEL=qwen3
UKB_AI_EMBEDDING_MODEL=embeddinggemma
```

Hosted OpenAI example:

```bash
UKB_AI_PROVIDER=openai
UKB_AI_MODE=hosted_ai
UKB_OPENAI_MODEL=gpt-4o-mini
UKB_OPENAI_API_KEY=server-side-secret
UKB_ALLOW_HOSTED_AI_FOR_RESTRICTED=false
```

## UI behavior

The React console now shows:

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

### Keys stay server-side

The React app never receives hosted provider API keys. Hosted API configuration is read from backend environment variables only.

### Restricted-source blocking

Hosted AI is blocked for `confidential` or `restricted` sources unless:

```bash
UKB_ALLOW_HOSTED_AI_FOR_RESTRICTED=true
```

Default is false.

### Safe fallback

If an AI provider fails:

```text
fallback to NoopProvider
record provider_fallback in risk flags
keep review workflow operational
never silently approve knowledge
```

## Acceptance criteria

The LLM feature is working when:

```text
1. User submits support context through the UI or API.
2. Backend saves source evidence.
3. Baseline compiler creates a candidate.
4. AI enrichment attaches classification, review brief, findings, and suggested relationships.
5. Reviewer sees AI guidance but still approves/rejects manually.
6. Approved object appears in the brain store.
7. Context pack includes approved evidence plus AI guidance/missing-context warnings.
8. Graph projection shows AI enrichment as review-supporting metadata.
```

## Future work

```text
persistent AI task table
structured-output schemas per provider
embedding generation and semantic duplicate detection
policy-aware hosted/local routing
reviewer-editable extracted fields
AI-generated documentation from approved objects
LLM evaluation suite with golden questions
streaming task status for long document enrichment
```
