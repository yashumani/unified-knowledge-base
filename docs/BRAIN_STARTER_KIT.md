# Brain Starter Kit

## Purpose

The starter kit lets someone create a domain-specific AI Brain without forking the platform core.

A user should be able to start with a command like:

```bash
npm create ukb-brain@latest my-finance-brain -- --template default --offline
```

or, before the package is published:

```bash
node packages/create-ukb-brain/bin/create-ukb-brain.mjs my-finance-brain --offline
```

This creates a project folder with:

```text
brain.config.yaml
domains/
plugins/
evals/
README.md
```

The generated project is not a separate platform. It is a **brain package** that can be loaded by the Unified Knowledge Base runtime.

## Mental model

```text
Unified Knowledge Base runtime
  stable engine: API, MCP, governance, retrieval, review workflow

Brain project
  domain-specific configuration, ontology extensions, templates, plugins, evals

Plugins
  source connectors, parsers, extractors, validators, retrievers, exporters
```

This is similar to how app frameworks separate the framework from the application. The runtime stays stable; each user brings their own context and plugin choices.

## What a generated brain should contain

```text
brain.config.yaml
  id, name, domains, runtime mode, plugin list, governance rules

domains/
  finance, product, sales, operations, legal, custom domain folders

plugins/
  optional custom connectors, parsers, validators, exporters

evals/
  golden questions and expected context objects

README.md
  operating notes for the team that owns the brain
```

## Offline-first requirement

A generated brain must work without a network connection for basic operations:

- edit Markdown/YAML context
- run deterministic validation
- load local plugins
- submit manual context
- create candidate objects with heuristic extraction
- use human review workflow
- produce context packs from approved local objects

AI should improve the experience, but the brain should not collapse when hosted AI is unavailable.

## AI modes

```text
offline_no_model
  Works with deterministic rules and human-entered structured knowledge.

local_ai
  Uses a local model provider for extraction, summarization, embeddings, or reranking.

hosted_ai
  Uses an enterprise-approved hosted model provider for richer classification and reasoning.

hybrid
  Uses local AI by default and hosted AI only for approved tasks.
```

## Why this matters

The AI Brain is enterprise infrastructure. It should not depend on a single vendor, cloud connection, UI, or model provider.

The safest design is:

```text
human-editable brain package
  + plugin contracts
  + offline deterministic path
  + optional local AI
  + optional hosted AI
  + governed publishing
```

## Starter command contract

The npm starter package should eventually support:

```bash
npm create ukb-brain@latest my-brain
npm create ukb-brain@latest my-finance-brain -- --template finance
npm create ukb-brain@latest my-ops-brain -- --offline
npm create ukb-brain@latest my-brain -- --with-example-data
```

Generated files should contain synthetic examples only.

## Recommended next iteration

1. Publish `create-ukb-brain` only after the local package is stable.
2. Add first-class templates: `default`, `finance-bi`, `product-analytics`, `ops-runbook`.
3. Add `ukb brain validate <path>` to validate generated brain packages.
4. Add `ukb brain load <path>` to load a brain package into the runtime.
5. Add plugin discovery from local paths and installed Python packages.
