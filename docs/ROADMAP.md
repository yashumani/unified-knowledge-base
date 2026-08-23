# Roadmap

## Release status

### v0.3.0 — Governed AI Brain platform release

Completed:

- durable SQLite/PostgreSQL persistence and Alembic migrations
- immutable source artifacts, source versions, evidence chunks, hashes, and provenance
- governed ingestion for text, files, folders, ZIP archives, Obsidian notes, Drive, Crawl4AI, and plugin connectors
- local Ollama advisory enrichment with deterministic fallback
- separate human approval and publication transitions
- tenant, role, classification, and policy-aware retrieval
- Zvec derived retrieval index and rebuild path
- versioned Tenant Domain Packs and typed temporal Talk2Data memory
- Context Coverage Receipts, source health, and index watermarks
- replaceable Graphiti boundary and live Neo4j validation
- legacy knowledge backfill tooling
- REST, MCP, and typed Talk2Data client boundaries
- 5,000-source / 100,000-memory scale and tenant-isolation gate
- React dashboard, guided and advanced experiences, graph, help, and ingestion studio
- exact-commit CI, CodeQL, GitHub Pages deployment, and GHCR publication

Release evidence:

https://github.com/yashumani/unified-knowledge-base/issues/19

## v0.4 — Private Runtime Pilot

### Code-complete pilot controls

- [x] Fail-closed staging environment validator
- [x] Placeholder, weak-secret, role-separation, CORS, storage, search, AI, MCP, and connector checks
- [x] Read-only deployed-runtime acceptance probe
- [x] Self-hosted deployment workflow integration
- [x] Redacted configuration and runtime evidence artifacts
- [x] Staging deployment ledger entry
- [x] Private-runtime pilot runbook and go/no-go checklist

### Environment-dependent pilot work

- [ ] Provision an approved Linux staging host
- [ ] Register a protected self-hosted runner labeled `self-hosted`, `linux`, and `ukb`
- [ ] Configure persistent PostgreSQL, object-store, Ollama, and Zvec volumes
- [ ] Configure HTTPS reverse proxy and DNS
- [ ] Replace every staging secret placeholder through an approved secret-management process
- [ ] Configure attributable reviewer and publisher identities
- [ ] Deploy the immutable v0.3.0 or later API image
- [ ] Connect GitHub Pages through `UKB_API_BASE_URL`
- [ ] Run source → enrichment → review → publication → retrieval acceptance
- [ ] Run restart, backup, restore, projection rebuild, and connector-failure drills
- [ ] Prove zero cross-tenant content and metadata leakage
- [ ] Configure operational dashboards and alerts
- [ ] Record pilot go/no-go decision

### Production identity

- [ ] Configure OIDC issuer, audience, JWKS, tenant claim, groups, roles, and clearance
- [ ] Test login, expiry, logout, group changes, and break-glass access
- [ ] Require OIDC in the deployment gate
- [ ] Enable protected-branch and protected-environment policies in GitHub

## v0.5 — Governed Query Execution

- [ ] Add read-only warehouse connection profiles
- [ ] Add schema discovery and governed dataset metadata
- [ ] Resolve approved metrics, entities, dimensions, calendars, currencies, and units
- [ ] Add deterministic SQL planning and validation
- [ ] Enforce row, time, cost, and statement limits
- [ ] Record query text, parameters, source, execution identity, and result provenance
- [ ] Add a result contract for Talk2Data without duplicating Domain Pack logic
- [ ] Add golden query and permission-leakage evaluation suites

## v0.6 — Talk2Data Conversation Experience

- [ ] Build the Talk2Data end-user interface in its separate repository
- [ ] Add clarification, proceed, qualify, reject, and abstain states
- [ ] Display citations, memory timelines, conflicts, and Context Coverage Receipts
- [ ] Add conversation/session history with tenant-scoped retention
- [ ] Add accessible desktop and mobile evidence inspection
- [ ] Add error recovery and user feedback capture

## v0.7 — Anomaly and Variance Intelligence

- [ ] Add KPI movement and anomaly detection
- [ ] Add period and segment comparison
- [ ] Add deterministic contribution and variance decomposition
- [ ] Add evidence-backed narrative generation
- [ ] Add charts and caveat presentation
- [ ] Add validation against approved metric definitions and source freshness

## v1.0 — Production Platform

- [ ] Complete one real tenant/domain onboarding
- [ ] Operate at least three approved source connectors with monitored refresh
- [ ] Complete security threat modeling and penetration review
- [ ] Complete privacy, retention, deletion, legal-hold, and residency controls
- [ ] Complete backup, restore, disaster-recovery, and migration rollback drills
- [ ] Complete load, chaos, failover, and permission-leakage testing
- [ ] Publish Python and TypeScript SDKs
- [ ] Harden MCP Streamable HTTP deployment
- [ ] Publish an operator and developer documentation site
- [ ] Complete pilot-user acceptance and production go-live review

## Definition of complete

The one-domain production release is complete when a real authenticated user can:

```text
submit approved enterprise context
→ preserve and trace the evidence
→ receive advisory local-AI enrichment
→ complete governed review and publication
→ retrieve only authorized current memory
→ inspect conflicts, history, citations, and coverage
→ execute a governed read-only business query
→ receive an evidence-backed result
```

and the platform has passed tenant isolation, recovery, observability, security, and user-acceptance gates.
