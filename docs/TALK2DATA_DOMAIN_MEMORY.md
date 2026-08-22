# Talk2Data Tenant Domain Pack and Governed Memory Contract

This document defines the integration boundary between Unified Knowledge Base (UKB) and the separate Talk2Data chatbot.

UKB owns the governed business context. Talk2Data may use the contracts to classify a question, resolve tenant vocabulary, retrieve authorized memory, inspect timelines, and determine whether the relevant memory partitions were actually searched. UKB does **not** implement the Talk2Data chat interface, warehouse query execution, anomaly visualization, or variance analysis.

## Runtime boundary

```text
Talk2Data question
    ↓
Tenant-bound authenticated principal
    ↓
Current effective Domain Pack
    ↓
Vocabulary resolution + domain classification
    ↓
Authorized typed-memory retrieval
    ↓
Optional temporal graph ranking
    ↓
Context Coverage Receipt
    ↓
Talk2Data proceeds, qualifies, requests more evidence, or abstains
```

Authorization is an application and data-layer control. An LLM prompt is never treated as authorization.

## 1. Versioned Tenant Domain Pack

`TenantDomainPack` is the governed description of what belongs to a tenant's business domain. It contains:

- tenant identity;
- industry and subindustries;
- products and services;
- business capabilities;
- organizational domains and subdomains;
- business entities and typed relationships;
- vocabulary, aliases, abbreviations, and synonyms;
- metric and dimension references;
- recognized business processes;
- required and optional knowledge-source references;
- allowed external-context categories;
- explicit domain-adjacency rules;
- explicitly excluded domains;
- calendar, currency, unit, geography, timezone, and terminology defaults;
- classification and access-policy references;
- owner, approval, effective dates, version, checksum, and supersession metadata.

Only an approved pack that is effective for the requested date is considered current. When a new approved version becomes effective, the prior version is marked `superseded`, given an `effective_to`, and retained for historical classification.

### Question-domain decisions

The classifier returns one of:

| Decision | Meaning |
|---|---|
| `in_domain` | Recognized tenant domains, products, entities, metrics, processes, or vocabulary are present. |
| `external_adjacent` | An approved external category is present **and** an approved internal anchor satisfies a Domain Pack adjacency rule. |
| `excluded` | The question matches an explicit exclusion without an internal anchor. |
| `unsupported` | No approved tenant or adjacent domain is recognized. |
| `ambiguous` | Reserved for a caller or future classifier that cannot select a single domain decision. |

The synthetic telecom example is in `examples/talk2data-telecom/domain-pack.yaml`.

Required examples classify as follows:

```text
What was postpaid churn by plan last month?
→ in_domain

What is our restaurant food-cost margin by location?
→ excluded

Did restaurant foot traffic near our stores affect mobile activations?
→ external_adjacent

Did food-delivery application traffic contribute to evening network congestion?
→ external_adjacent
```

The final two are adjacent only because they contain an approved telecom anchor. Restaurant or food-delivery context alone does not become tenant memory.

## 2. Governed typed memory

`GovernedMemoryObject` stores reviewed context as a typed, temporal object rather than an anonymous text chunk.

Required fields include:

```text
memory_id
tenant_id
version
memory_type
source_type
source_id
business_domain
related_metrics
related_entities
created_at
effective_from
effective_to
status
classification
access_policy_id
allowed_roles
denied_roles
authority_level
owner
approved_by
supersedes
superseded_by
content
provenance
checksum
ingestion_timestamp
index_watermark
```

Supported memory types:

```text
business_definition
business_decision
policy
business_event
project_event
investigation
user_approved_preference
metric_context
entity_context
external_intelligence
source_document
meeting_record
hypothesis
recommendation
```

Memory states distinguish `unverified`, `approved`, `published`, `deprecated`, `superseded`, `expired`, `conflicting`, and `rejected` knowledge.

Historical facts are never overwritten. Supersession closes the prior object's effective interval, creates a new version with `supersedes`, and retains the earlier object for an as-of-date query.

## 3. Canonical episodes and provenance

`CanonicalEpisode` is the immutable raw source episode. It is separate from summaries, graph entities, and indexes.

Episode ingestion provides:

- SHA-256 source checksums;
- tenant-scoped idempotency keys;
- duplicate-content protection by source and checksum;
- parent-episode lineage;
- observed and effective dates;
- source classification and access-policy references;
- original raw content and source metadata;
- ingestion timestamps and audit events.

Every governed memory object references a canonical episode through `MemoryProvenance`. Promotion fails when the episode is missing, belongs to another tenant, or its checksum does not match.

Derived graph and search projections are rebuildable from canonical episodes and governed memory. They are not the authoritative store.

## 4. Replaceable Graphiti adapter

`TemporalGraphAdapter` is the provider interface for temporal graph projection and retrieval. It supports:

- source episodes;
- typed memory entities;
- typed relationships;
- effective dates;
- superseded facts;
- tenant and domain filters;
- classification and policy metadata;
- metric and entity links;
- incremental upserts;
- graph-assisted retrieval;
- entity and metric timelines;
- complete rebuilds.

Implementations included:

```text
InMemoryTemporalGraphAdapter
GraphitiTemporalGraphAdapter
```

`GraphitiTemporalGraphAdapter` depends on the small `GraphitiClientProtocol`, allowing a deployment to map the approved Graphiti SDK or API version without hard-coding it through the application.

The canonical SQL store remains independently queryable and auditable. Graph-only results are intersected with authorized canonical memory before anything is returned.

## 5. Obsidian governance contract

Obsidian Markdown uses YAML frontmatter such as:

```yaml
---
id: postpaid-churn-context
tenant_id: synthetic-telecom
type: metric_context
domain: subscriber
status: approved
classification: internal
effective_from: 2026-01-01T00:00:00Z
effective_to:
owner: Synthetic Subscriber Analytics
approved_by: synthetic.domain.reviewer
related_metrics:
  - postpaid_churn_rate
related_entities:
  - subscriber
  - service_plan
source: obsidian://synthetic-telecom/postpaid-churn-context
version: 1
---
```

Safe workflow:

```text
Obsidian authoring
→ frontmatter and body validation
→ authenticated human approval
→ canonical episode
→ governed typed memory
→ graph/index update
```

A malformed note is rejected. A structurally valid draft may be previewed, but it cannot be promoted as authoritative memory until it is approved and has `approved_by`. The authenticated principal—not a frontmatter string—becomes the trusted promotion actor.

Wiki-links are retained as provenance relationships and graph projection edges where practical.

## 6. Authorized retrieval

The memory query supports:

- tenant-bound retrieval;
- query text;
- business domains;
- metric and entity references;
- memory types and statuses;
- effective date;
- current or historical mode;
- role policy;
- classification clearance;
- result limit.

Filtering order is security-first:

```text
tenant
→ classification clearance
→ allowed/denied roles
→ status and temporal validity
→ domain, metric, entity, and type filters
→ lexical relevance
→ optional graph reranking
```

Cross-tenant memory is skipped before scoring and does not appear in counts, IDs, graph hits, timelines, or source metadata.

## 7. Context Coverage Receipt

`ContextCoverageReceipt` answers a different question from retrieval: **did UKB search the memory partitions that the business request requires?**

It reports:

```text
requested memory partitions
searched memory partitions
per-partition result status
Domain Pack ID and version
latest ingestion watermark
incomplete or unavailable sources
policy-based exclusions
conflicting memory
superseded memory
index lag
overall coverage status
```

Supported initial partitions:

```text
domain_pack
current_memory
historical_memory
investigations
metric_timeline
entity_timeline
external_intelligence
graph
```

Coverage states:

| Status | Meaning |
|---|---|
| `complete` | Requested partitions were searched with healthy required sources and current indexes. |
| `partial` | Some source, policy, conflict, or result limitation prevents full coverage. |
| `stale` | Required content is available but an ingestion or index watermark exceeds the configured tolerance. |
| `unavailable` | The current Domain Pack or required retrieval plane is unavailable. |
| `denied` | Relevant content may exist, but policy excludes all authorized memory for the caller. |

Talk2Data should not treat an empty result as comprehensive unless the receipt supports that conclusion.

## 8. API contract

The versioned API is under `/v1`.

```text
GET  /v1/domain-packs/current
GET  /v1/domain-packs/versions
POST /v1/domain-packs
POST /v1/domain-packs/resolve
POST /v1/domain-packs/classify

POST /v1/memory/episodes
GET  /v1/memory/episodes/{episode_id}
POST /v1/memory
POST /v1/memory/supersede
POST /v1/memory/relationships
POST /v1/memory/query
POST /v1/memory/query/graph
POST /v1/memory/timelines/entities
POST /v1/memory/timelines/metrics
POST /v1/memory/investigations
GET  /v1/memory/source-health
PUT  /v1/memory/source-health
GET  /v1/memory/index-watermarks
PUT  /v1/memory/index-watermarks
POST /v1/memory/context-coverage
GET  /v1/memory/audit

POST /v1/obsidian/validate
POST /v1/obsidian/promote

GET  /v1/graph/status
POST /v1/graph/rebuild
```

Focused OpenAPI: `docs/openapi-talk2data.json`  
Versioned JSON Schemas: `schemas/talk2data/v1/`

## 9. Talk2Data integration sequence

Recommended client sequence:

1. Authenticate and bind the request to one tenant, user, roles, and classification clearance.
2. Retrieve the current effective Domain Pack.
3. Resolve tenant vocabulary, metrics, entities, aliases, and abbreviations.
4. Classify the business question as in-domain, external-adjacent, excluded, or unsupported.
5. For in-domain or allowed-adjacent questions, request authorized typed memory.
6. Retrieve entity/metric timelines or prior investigations when the analytical plan needs them.
7. Request a Context Coverage Receipt for the partitions Talk2Data intended to use.
8. Proceed only with authorized returned memory. Qualify or abstain when coverage is partial, stale, unavailable, denied, or conflicting.
9. Keep citations and provenance IDs attached to downstream reasoning and audit records.

## 10. Deliberate non-goals

This implementation does not add:

- a chatbot interface;
- warehouse SQL generation or execution;
- anomaly visualizations;
- variance-analysis logic;
- business-answer generation;
- production Graphiti provisioning;
- Obsidian desktop synchronization.

Those remain separate Talk2Data or deployment responsibilities.
