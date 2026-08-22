# Talk2Data integration and operations plan

This plan completes the immediate ten-item work order after the Tenant Domain Pack and governed-memory contract landed.

## Dependency order

1. Stabilize the governed AI Brain foundation.
2. Revalidate the Talk2Data contract against that foundation.
3. Review both change sets for duplicated or conflicting runtime logic.
4. Merge the validated foundation.
5. Integrate the Talk2Data contract with `main`.
6. Revalidate the integrated Talk2Data contract.
7. Merge the contract only after all remote checks pass.
8. Build the Talk2Data consumer integration harness.
9. Validate the replaceable Graphiti boundary against a real Neo4j runtime.
10. Add legacy backfill, migration safety, tenant-isolation scale tests, and recovery gates.

Items 1–7 were completed before this operations branch was created. This branch implements and validates items 8–10.

## Consumer integration harness

`Talk2DataMemoryClient` is a thin typed HTTP client. It forwards the authenticated bearer token and validates the response contract; it does not reproduce authorization in the client.

`Talk2DataDecisionOrchestrator` performs the following sequence:

```text
question
→ Domain Pack classification
→ authorized current-memory and graph retrieval
→ Context Coverage Receipt
→ proceed / qualify / abstain decision
```

It does not answer the business question and does not generate or execute warehouse SQL.

Run the live harness against a seeded UKB API:

```bash
UKB_API_BASE_URL=http://127.0.0.1:8000 \
UKB_API_TOKEN=dev-token-change-me \
python scripts/talk2data_integration_harness.py
```

## Graphiti validation

Graphiti remains a derived graph projection. PostgreSQL and the canonical episode store remain authoritative.

The dedicated workflow pins:

```text
graphiti-core 0.29.3
Neo4j 5.26 community
```

The smoke gate:

1. Starts an isolated Neo4j service.
2. Installs the pinned stable Graphiti SDK.
3. Initializes Graphiti indexes and constraints twice to prove idempotency.
4. Executes a live read probe through the Graphiti driver.
5. Closes the driver cleanly.

No LLM or embedding request is made during this connectivity test.

## Legacy backfill

The default command is a dry run:

```bash
python scripts/backfill_talk2data_memory.py
```

Execute only after reviewing the plan:

```bash
python scripts/backfill_talk2data_memory.py --execute
```

Properties:

- Published legacy `KnowledgeObject` records are never deleted or overwritten.
- Each legacy object version receives a tenant-scoped idempotency key.
- A canonical migration episode preserves the original JSON representation and checksum.
- The typed memory record stores the legacy object ID, type, version, aliases, attributes, and relationships.
- Re-running the command does not create duplicate episodes or memories.
- Ambiguous legacy types are promoted as `unverified` source-document memory and require governance review.

## Scale profiles

```bash
python scripts/talk2data_scale_test.py --profile unit
python scripts/talk2data_scale_test.py --profile ci
python scripts/talk2data_scale_test.py --profile full
```

| Profile | Tenants | Source episodes | Typed memory objects | Purpose |
|---|---:|---:|---:|---|
| `unit` | 2 | 10 | 100 | Fast deterministic regression test |
| `ci` | 3 | 100 | 2,000 | Pull-request retrieval and isolation gate |
| `full` | 10 | 5,000 | 100,000 | Manually dispatched capacity baseline |

Every profile verifies that a tenant-specific marker is never returned to another tenant. The benchmark records ingest time and governed-query p50/p95 latency.

## Release gates

No deployment should occur until all of these pass on the same commit:

```text
Continuous Integration
CodeQL
Talk2Data client/backfill/scale tests
Graphiti 0.29.3 + Neo4j 5.26 smoke
Alembic upgrade from an empty database
React production build
Desktop/mobile browser validation
Local and production Compose validation
API and web container builds
Cross-tenant leakage count = 0
```

The full 5,000-source / 100,000-memory profile is a manual release-candidate gate. It is not run on every pull request.

## Deployment boundary

GitHub Pages deploys only the static React application. The private runtime still requires:

```text
FastAPI
PostgreSQL
object storage
Ollama
Zvec
optional Graphiti + Neo4j
background workers
```

The backend image may be published to GHCR after tests pass. A private runtime deployment is successful only when the self-hosted deployment workflow and readiness probes pass; a Pages deployment alone is not a backend deployment.
