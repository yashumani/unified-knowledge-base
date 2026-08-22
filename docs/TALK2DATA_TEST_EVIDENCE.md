# Talk2Data validation evidence

This file records reproducible checks for the Tenant Domain Pack and governed-memory contract.

## Local implementation validation

```text
Focused Talk2Data tests: 20 passed
Python compilation: passed for new and modified modules
JSON Schema generation: 10 schemas generated and parsed
Focused OpenAPI generation: 25 versioned routes generated and parsed
```

The focused tests cover Domain Pack versioning, telecom question classification, vocabulary resolution, domain adjacency, explicit exclusions, tenant and classification isolation, duplicate episodes, provenance, temporal supersession, Obsidian validation and promotion, Context Coverage Receipts, source/index health, and replaceable graph adapters.

## Required repository checks

The draft pull request reports the final remote results for:

```text
Ruff
mypy
full pytest suite and coverage
Alembic upgrade through 0002_talk2data_domain_memory
React production build
browser workflow
Docker and Compose validation
CodeQL
```

Validation is performed from the remote development branch `agent/talk2data-domain-pack-memory` against `agent/architecture-gap-closure`.

The PR description is the authoritative place for workflow run IDs, conclusions, the exact remote head, and final repository-wide counts after GitHub Actions completes.
