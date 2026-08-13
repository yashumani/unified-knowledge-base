# GitLab Deployment

## Target constraint

This project is designed so the production-style version can be hosted on an internal GitLab/Linux/Docker server.

Do not assume public cloud services are available. For this Unified Knowledge Base use case, AI enrichment should use a local/internal Ollama runtime.

## Deployment shape

```text
GitLab repository
  -> GitLab CI pipeline
  -> build Docker image
  -> push to GitLab container registry
  -> deploy on Linux server with Docker Compose or Kubernetes
  -> internal API URL
  -> internal Ollama service
  -> internal MCP endpoint or stdio gateway
```

## Recommended environments

```text
dev
  local Docker Compose
  synthetic data
  Ollama running locally or as compose service

stage
  private GitLab server
  synthetic data
  test reviewers
  internal Ollama host or sidecar

prod
  private GitLab server
  real enterprise sources
  SSO / service accounts
  audit logs
  locked-down internal Ollama host
```

## GitLab CI flow

```text
lint
test
build
container-scan
publish-image
deploy-dev
deploy-stage
deploy-prod
```

CI should not require Ollama unless the job explicitly runs local-model integration tests. Unit tests should be able to use the deterministic `noop` fallback.

## Secrets

Store secrets in GitLab CI/CD variables or server secret management.

Never commit:

```text
API keys
database passwords
OAuth client secrets
company documents
customer data
raw internal exports
service account JSON
private certificates
```

Ollama local enrichment does not require hosted API keys for the default UKB workflow.

## Local LLM deployment

Recommended internal topology:

```text
React UI
  -> internal FastAPI service
      -> internal Ollama service
```

The browser should not call Ollama directly.

For Docker Compose, the API uses:

```text
UKB_AI_PROVIDER=ollama
UKB_AI_MODE=local_ai
UKB_AI_BASE_URL=http://ollama:11434
UKB_AI_CHAT_MODEL=llama3.1
UKB_AI_EMBEDDING_MODEL=embeddinggemma
```

The Ollama port should be reachable by the API container but should not be exposed publicly in a production-like deployment.

## Docker Compose production starter

Services to add as the platform matures:

```text
api
worker
ollama
postgres
redis
object-store
opensearch
graph-db
admin-ui
```

## MCP hosting options

### Option A: stdio gateway

Best when an MCP client runs inside a controlled desktop or server environment.

```text
LLM client launches: python -m ukb.mcp.server
```

### Option B: internal Streamable HTTP endpoint

Best when agent clients run as services and can call an internal URL.

```text
https://ukb.internal.company/mcp
```

Add:

```text
auth
origin validation
network restrictions
rate limits
audit logs
```

MCP tools must call the same governed brain runtime as the REST API; MCP must not bypass review or access control.

## Workplace-safe development pattern

Use this public/personal repository for:

```text
architecture
synthetic examples
open-source scaffold
generic code
local Ollama integration patterns
```

Use private GitLab for:

```text
real connectors
real documents
real dashboard metadata
real source data
enterprise auth
work-specific logic
approved internal Ollama model/runtime choices
```
