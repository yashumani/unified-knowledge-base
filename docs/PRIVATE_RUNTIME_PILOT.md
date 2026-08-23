# Private Runtime Pilot v0.4

The public GitHub Pages site is a static interface. A complete AI Brain pilot requires a private runtime that hosts FastAPI, PostgreSQL, object storage, Ollama, Zvec, background processing, and optional governed connectors.

This runbook adds a fail-closed gate before any private deployment and a read-only acceptance probe after the runtime starts.

## Deployment boundary

```text
GitHub Pages
  static React application
        |
        | HTTPS
        v
Private staging runtime
  reverse proxy / TLS
  FastAPI
  PostgreSQL
  private object storage
  Ollama
  Zvec
  Crawl4AI when explicitly enabled
  Graphiti when explicitly enabled
```

PostgreSQL and original artifacts remain authoritative. Zvec and Graphiti are rebuildable projections. Ollama is advisory and cannot approve or publish knowledge.

## Prerequisites

Provision one approved Linux machine or VM with:

- Docker and Docker Compose
- a GitHub self-hosted runner labeled `self-hosted`, `linux`, and `ukb`
- persistent storage for PostgreSQL, Ollama models, the object store, and Zvec
- an HTTPS hostname and reverse proxy
- a protected backup destination
- outbound access only to approved model, connector, and registry endpoints

The workflow environment is named `ukb-staging`. Apply GitHub environment protection and restrict which branches may deploy to it.

## Configure the environment

On the runner:

```bash
sudo mkdir -p /opt/unified-knowledge-base-staging
sudo cp deploy/staging.env.example \
  /opt/unified-knowledge-base-staging/.env
sudo chown "$(id -u):$(id -g)" \
  /opt/unified-knowledge-base-staging/.env
chmod 600 /opt/unified-knowledge-base-staging/.env
```

Replace every placeholder. Do not commit the completed file.

The staging gate requires:

- an immutable GHCR image tag or digest, never `latest`
- a strong break-glass token
- a distinct strong PostgreSQL password
- separately attributable reviewer and publisher tokens
- authentication enabled
- SQLAlchemy as the authoritative store
- migration-controlled schema creation
- file, S3, or MinIO object storage
- Zvec retrieval
- explicit HTTPS CORS origins
- local Ollama configuration
- MCP approval and publication disabled
- fail-closed crawler controls whenever Crawl4AI is enabled
- a server-side token whenever Google Drive is enabled

OIDC and Graphiti can be made mandatory with workflow inputs. For an early staging pilot, mapped tokens are allowed with a warning; production identity must use OIDC.

## Validate before deployment

Run locally on the staging host:

```bash
python -m pip install "pydantic>=2.8.0" "httpx>=0.27.0"

PYTHONPATH=src python scripts/validate_staging_readiness.py \
  --env-file /opt/unified-knowledge-base-staging/.env \
  --expected-ui-origin https://yashumani.github.io \
  --output /tmp/ukb-staging-config.json
```

Production identity gate:

```bash
PYTHONPATH=src python scripts/validate_staging_readiness.py \
  --env-file /opt/unified-knowledge-base-staging/.env \
  --expected-ui-origin https://yashumani.github.io \
  --require-oidc \
  --output /tmp/ukb-production-config.json
```

The report never includes secret values. Any failed check returns a non-zero exit code.

## Deploy through GitHub Actions

Run:

```text
Actions
→ Deploy UKB private runtime pilot
→ Run workflow
```

Inputs:

```text
image_tag          v0.3.0 or an immutable commit SHA
deploy_path        /opt/unified-knowledge-base-staging
expected_ui_origin https://yashumani.github.io
bootstrap_models   pull configured Ollama models
require_oidc       enforce production identity configuration
require_graphiti   enforce Graphiti projection configuration
```

The workflow:

1. validates the resolved environment
2. pulls the pinned API image
3. starts PostgreSQL, Ollama, and Crawl4AI privately
4. applies Alembic migrations
5. starts FastAPI
6. optionally pulls the Ollama models
7. waits for `/ready`
8. probes the governed API
9. uploads redacted evidence
10. records the result in deployment ledger issue #19

## Read-only acceptance probes

The post-deployment script checks:

```text
GET /health
GET /ready
GET /ai/providers
GET /ai/health
GET /search/status
GET /ingestion/capabilities
GET /v1/graph/status
```

It verifies that:

- health reports `ok`
- readiness reports `ready`
- the authoritative store is SQLAlchemy
- the search projection is available
- ingestion capabilities are registered
- a graph projection is available
- protected endpoints accept the supplied attributable token
- request IDs are returned for tracing

Manual invocation:

```bash
export UKB_API_TOKEN='read-from-the-private-secret-store'

PYTHONPATH=src python scripts/run_staging_acceptance.py \
  --base-url https://ukb-staging.example.net \
  --token-env UKB_API_TOKEN \
  --output /tmp/ukb-staging-acceptance.json
```

The token is accepted only through an environment variable, never as a command-line value.

## End-to-end pilot acceptance

After the read-only gate passes, test with synthetic data:

```text
source ingestion
→ immutable artifact
→ source version
→ evidence chunks
→ advisory Ollama enrichment
→ human approval
→ explicit publication
→ Zvec/Graphiti projection update
→ authorized retrieval
→ Context Coverage Receipt
```

Run every enabled ingestion path independently. Validate two synthetic tenants and attempt cross-tenant reads of content, IDs, graph metadata, watermarks, coverage details, and audit records. Every leakage count must be zero.

## Recovery tests

Before promotion beyond staging:

- restart FastAPI and PostgreSQL
- stop Ollama and verify governed fallback
- stop Graphiti and verify canonical memory remains available
- rebuild Zvec from canonical storage
- exercise worker retry and dead-letter handling
- create and restore a backup
- verify superseded historical memory remains queryable
- verify failed connector jobs do not publish knowledge

## Go/no-go gate

The pilot may proceed only when:

```text
[ ] Configuration report is ready.
[ ] Every read-only probe passes.
[ ] HTTPS and attributable identity work.
[ ] Source and review records survive restarts.
[ ] Original evidence is recoverable.
[ ] Reviewer and publisher duties are separated.
[ ] Published memory is searchable with citations.
[ ] Coverage receipts expose incomplete sources and index lag.
[ ] Cross-tenant content and metadata leakage are zero.
[ ] Backup and restore succeed.
[ ] Monitoring and alerts are active.
```

The deployment ledger is:

https://github.com/yashumani/unified-knowledge-base/issues/19
