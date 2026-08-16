## Summary

Describe the user or developer outcome of this change.

## Scope

- [ ] Backend/runtime
- [ ] React UI
- [ ] Local Ollama/AI enrichment
- [ ] Governance/security
- [ ] MCP/SDK/plugin architecture
- [ ] Deployment/CI
- [ ] Documentation only

## Governance and data-safety check

- [ ] No employer, client, customer, or proprietary material is included.
- [ ] AI output remains advisory and cannot bypass human approval.
- [ ] Restricted content is filtered before retrieval or model access.
- [ ] Secrets and local runtime URLs are not exposed to the browser.

## Validation

List the checks run and their results.

```text
pytest:
ruff:
mypy:
React build:
Docker/Compose:
```

## API, schema, or migration impact

Describe any API, Pydantic model, database, migration, or compatibility changes.

## UI evidence

For visible UI changes, include screenshots or a short recording using synthetic data only.

## Follow-up work

List intentionally deferred work or known limitations.
