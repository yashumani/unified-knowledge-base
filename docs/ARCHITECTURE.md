# Architecture

## Goal

Build a platform that converts scattered enterprise knowledge into an approved, reusable, permission-aware AI Brain.

The AI Brain is not a chatbot. It is the context layer used by chatbots, BI copilots, agents, report automation, notebooks, and insight engines.

## Core idea

```text
Raw source material -> Evidence -> Candidate knowledge -> Human review -> Published brain object -> Context pack
```

## Logical components

### 1. Source Connector Hub

Connectors fetch or receive source material.

Initial connector types:

- file upload
- Markdown / Obsidian-style vaults
- Git repositories
- SQL files
- dashboard metadata exports
- Google Sheets / Excel extracts
- BigQuery / Snowflake / Databricks metadata later
- SharePoint / Confluence / Drive later

The connector should capture metadata before content is parsed:

```text
source_id
source_type
source_uri
owner
submitted_by
created_at
modified_at
access_policy
sensitivity
hash
version
```

### 2. Evidence Store

The evidence layer preserves what was actually provided.

This prevents the system from becoming an untraceable generated knowledge dump.

Evidence object examples:

```text
SourceDocument
EvidenceChunk
TableArtifact
MediaAsset
SqlArtifact
DashboardArtifact
MetricDefinitionArtifact
```

### 3. Brain Compiler

The compiler turns messy content into candidate objects.

Pipeline:

```text
parse
classify
extract entities
extract relationships
normalize to ontology
detect conflicts
score confidence
create review items
```

In the scaffold, this is intentionally simple and heuristic. In production, this layer can call LLMs, OCR, table parsers, lineage scanners, data catalogs, and schema extractors.

### 4. Ontology Manager

The ontology defines the grammar of the brain.

Example entity types:

```text
Metric
Dimension
Dataset
Table
Column
Report
Dashboard
BusinessRule
Process
Owner
System
Decision
NarrativeTemplate
```

Example relationships:

```text
Metric appears_in Report
Metric calculated_from Dataset
Metric owned_by Owner
Metric governed_by BusinessRule
Dataset contains Column
Report consumed_by Team
Metric related_to Metric
BusinessRule applies_to Metric
```

### 5. Review Queue

AI should classify and prepare knowledge, but humans approve it.

Review states:

```text
draft
submitted
ai_classified
human_review_required
approved
rejected
published
deprecated
```

### 6. Governed Brain Store

The store contains only approved or explicitly draft/candidate objects with state metadata.

For MVP:

- in-memory Python store

Near-term:

- Postgres for source/evidence/review/object metadata
- object storage for raw evidence
- vector index for hybrid retrieval
- graph store or graph tables for relationships

### 7. Context Runtime

The runtime composes context packs for consumers.

A context pack should include:

```text
answer guidance
relevant knowledge objects
source evidence
definitions
lineage
rules
caveats
related objects
access decision
confidence
freshness
```

### 8. Consumption Adapters

The same brain runtime is exposed through multiple adapters:

```text
REST API        product UI, services, ingestion, review, automation
Python SDK      BI notebooks, report pipelines, backend integration
MCP server      LLM agents and AI tools
CLI             local development and GitLab jobs
```

## Data flow

```text
[Submit source/context]
        |
        v
[Source metadata + raw evidence]
        |
        v
[Compiler creates candidate objects]
        |
        v
[Review item created]
        |
        v
[Human reviewer approves/rejects/requests changes]
        |
        v
[Approved object published to AI Brain]
        |
        v
[Context pack served to API/MCP/SDK consumers]
```

## Runtime boundaries

### Core logic

The core logic should live in services:

```text
CompilerService
GovernanceService
RetrievalService
ContextPackService
BrainStore
```

### Adapters

Adapters should be thin.

```text
FastAPI route -> service call
MCP tool -> service call
CLI command -> service call
SDK method -> REST call or service call
```

Do not duplicate business logic in API routes and MCP tools.

## Deployment model

For a GitLab-hosted workplace environment:

```text
GitLab repo
  -> GitLab CI
  -> container image
  -> internal container registry
  -> Docker Compose / Kubernetes on Linux server
  -> internal URL for API and MCP
```

External SaaS services are optional and should not be required for the core platform.

## Suggested production stores

MVP:

```text
Postgres + pgvector + object storage
```

Larger deployment:

```text
Postgres       metadata, review state, governance
Object store   raw documents, parsed artifacts
OpenSearch     keyword + hybrid retrieval
Vector DB      semantic retrieval
Graph DB       lineage and relationship traversal
Redis          cache / queue state
```

## Security boundary

Security filtering must happen before the LLM receives context.

Bad:

```text
retrieve everything -> ask model not to reveal restricted content
```

Good:

```text
user identity -> policy check -> retrieve only allowed content -> compose context pack
```
