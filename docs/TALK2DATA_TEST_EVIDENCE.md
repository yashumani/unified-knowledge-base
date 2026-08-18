# Talk2Data validation evidence

This file records reproducible checks for the Tenant Domain Pack and governed-memory contract.

## Local implementation validation

```text
Focused Talk2Data tests: 20 passed
Python compilation: passed for new and modified modules
JSON Schema generation: 10 schemas generated and parsed
Focused OpenAPI generation: 23 paths generated and parsed
```

## Required repository checks

The draft pull request must report the final remote results for:

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

The PR description is the authoritative place for workflow run IDs and final repository-wide counts after GitHub Actions completes.
