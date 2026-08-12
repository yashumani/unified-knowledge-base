# API vs MCP

## Decision

Use both.

The REST API is the product backend. The MCP server is an adapter for AI agents.

```text
Core Brain Runtime
  compiler
  governance
  store
  retrieval
  context pack builder

        |
        +-- REST API for product/platform operations
        +-- MCP server for LLM agents
        +-- Python SDK for developers/data teams
        +-- CLI for GitLab jobs and local workflows
```

## Why API is still required

A real platform needs actions that are not naturally MCP-first:

- user login
- admin UI
- source onboarding
- file upload
- approval workflow
- audit logs
- metrics and monitoring
- batch ingestion jobs
- CI/CD integration
- background processing
- long-running parsing
- retry handling
- environment configuration
- enterprise SSO integration
- role management

These are normal product/service capabilities and should live behind the REST API.

## Why MCP is valuable

MCP is useful when the AI Brain needs to be exposed to LLM applications.

Example MCP tools:

```text
submit_context
search_brain
get_context_pack
get_metric_definition
list_review_items
approve_review_item
explain_metric_movement
```

Example MCP resources:

```text
brain://domains
brain://objects/{object_id}
brain://metrics/{metric_id}
brain://governance/review-queue
```

Example MCP prompts:

```text
executive_insight_prompt
metric_definition_review_prompt
conflict_resolution_prompt
```

## Recommended enterprise pattern

```text
                           ┌─────────────────────────┐
                           │ Admin UI / Portal        │
                           └───────────┬─────────────┘
                                       │ REST
                                       ▼
┌────────────────────┐       ┌───────────────────────┐       ┌────────────────────┐
│ GitLab jobs         │ ----> │ Core Brain API         │ <---- │ BI / data services  │
└────────────────────┘       └──────────┬────────────┘       └────────────────────┘
                                        │
                                        ▼
                               ┌─────────────────┐
                               │ MCP server       │
                               │ thin adapter     │
                               └────────┬────────┘
                                        │ MCP
                                        ▼
                               ┌─────────────────┐
                               │ LLM clients      │
                               │ agents/copilots  │
                               └─────────────────┘
```

## When to use REST API

Use REST API for:

- platform UI
- ingestion submissions
- reviewer actions
- publishing and deprecating knowledge
- data/system integrations
- CI/CD jobs
- scheduled refreshes
- audit reporting
- service-to-service calls

## When to use MCP

Use MCP for:

- connecting the brain to AI assistants
- exposing approved context as LLM-readable tools/resources
- giving agents a controlled way to retrieve context packs
- letting an agent submit a candidate knowledge item for review
- letting AI development tools use the knowledge base

## Self-hosted GitLab constraint

Because the target environment is a workplace GitLab server, the safest model is:

```text
1. Keep the core platform containerized.
2. Deploy API and MCP as internal services on the Linux/GitLab server environment.
3. Use internal DNS and private network routes.
4. Do not require public callbacks.
5. Do not require SaaS vector stores for MVP.
6. Use GitLab CI/CD for build/test/deploy.
7. Store secrets only in GitLab CI/CD variables or server secret management.
```

## Transport decision

For developer/local use:

```text
MCP stdio
```

For hosted internal service use:

```text
MCP Streamable HTTP behind auth
```

For normal product operations:

```text
REST API
```

## Rule of thumb

If the consumer is an application, dashboard, web UI, or pipeline, use API.

If the consumer is an LLM client or agent, expose the relevant capabilities through MCP.

## Important design rule

Never let the MCP server bypass governance.

MCP tools must call the same BrainService and policy checks as the REST API.
