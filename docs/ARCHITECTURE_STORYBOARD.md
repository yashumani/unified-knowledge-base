# Architecture Storyboard

## Purpose

This storyboard gives the meeting narrative for the demo deck and animated diagrams. Use it to explain the system without getting stuck in implementation details.

## Core message

Unified Knowledge Base is a governed context runtime. It compiles enterprise context into approved, reusable brain objects and serves context packs to AI applications.

## Story arc

### 1. The problem

A data query can return a number, but a number is not an insight.

The app also needs:

```text
definition
lineage
owner
business rules
caveats
source evidence
permissions
freshness
related drivers
```

Without those layers, the model can produce a fluent but unsupported explanation.

### 2. The product boundary

The platform should not be a pile of documents and embeddings.

The product boundary is:

```text
raw context -> evidence -> candidate knowledge -> review -> approved brain -> context pack
```

### 3. The architecture split

The runtime and the brain project should be separate.

```text
Runtime
  API, MCP, governance, compiler, retrieval, store

Brain project
  domains, ontology extensions, plugins, templates, evals
```

This allows any team to create a brain without forking the engine.

### 4. The plugin model

Plugins can extend ingestion, parsing, extraction, validation, retrieval, policy, and export. But plugins cannot publish official knowledge directly.

```text
plugin output -> candidate -> review queue -> approval -> published brain
```

### 5. Offline-first AI

AI is an accelerator, not a dependency.

The deterministic path works with structured files and human review. Local AI can be added for extraction and embeddings. Hosted AI can be added only when policy allows it. Hybrid mode can use local AI by default and hosted AI by exception.

### 6. Consumption adapters

One runtime serves multiple consumers:

```text
REST API    platform UI, ingestion, governance, service integration
MCP server  LLM clients and agents
Python SDK  BI notebooks and backend automation
npm starter brain project creation
```

### 7. Demo proof

The demo should prove a single concept:

> The same approved knowledge powers both product workflows and AI-agent workflows.

The API and MCP server should call shared services. Governance should be impossible to bypass through a different adapter.

## Demo close

The next build waves should focus on durability and trust before broad connector expansion:

1. Postgres and persistent audit log
2. evidence storage
3. review UI
4. role-based filtering
5. hybrid retrieval
6. graph relationships
7. GitLab deployment hardening
