# GitLab Deployment

## Target constraint

This project is designed so the production-style version can be hosted on an internal GitLab/Linux/Docker server.

Do not assume public cloud services are available.

## Deployment shape

```text
GitLab repository
  -> GitLab CI pipeline
  -> build Docker image
  -> push to GitLab container registry
  -> deploy on Linux server with Docker Compose or Kubernetes
  -> internal API URL
  -> internal MCP endpoint or stdio gateway
```

## Recommended environments

```text
dev
  local Docker Compose

stage
  private GitLab server
  synthetic data
  test reviewers

prod
  private GitLab server
  real enterprise sources
  SSO / service accounts
  audit logs
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

## Docker Compose production starter

Services to add as the platform matures:

```text
api
worker
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

## Workplace-safe development pattern

Use this public/personal repository for:

```text
architecture
synthetic examples
open-source scaffold
generic code
```

Use private GitLab for:

```text
real connectors
real documents
real dashboard metadata
real source data
enterprise auth
work-specific logic
```
