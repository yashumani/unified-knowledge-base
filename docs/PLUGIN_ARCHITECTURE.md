# Plugin Architecture

## Goal

The platform should let users build their own domain brain by adding plugins, not by editing platform internals.

A plugin can add a source connector, parser, extractor, validator, retriever, context-pack decorator, policy rule, or exporter.

## Core rule

Plugins may create evidence and candidate knowledge.

Plugins must not bypass human review or publish official knowledge directly.

```text
plugin output -> candidate object -> review queue -> human approval -> published brain
```

## Plugin types

### Source connector

Fetches or receives source material.

Examples:

```text
local markdown folder
Obsidian vault
Git repository
SQL folder
CSV export
BI metadata export
SharePoint connector
Confluence connector
BigQuery metadata connector
```

### Parser

Turns evidence into structured artifacts.

Examples:

```text
PDF sections
spreadsheet tables
SQL models
dashboard metadata
Markdown frontmatter
YAML knowledge objects
```

### Extractor

Turns parsed artifacts into candidate brain objects.

Examples:

```text
Metric
Report
BusinessRule
Dataset
Owner
Decision
NarrativeTemplate
```

### Validator

Checks candidate quality before human review.

Examples:

```text
required fields are present
metric formula exists
owner is assigned
source evidence exists
conflicting definition is detected
sensitivity label is present
```

### Retriever

Adds retrieval capabilities.

Examples:

```text
keyword search
vector search
graph traversal
semantic-layer lookup
SQL lineage lookup
```

### Context-pack decorator

Adds extra context to a pack.

Examples:

```text
metric caveats
executive narrative hints
freshness warning
related driver metrics
source confidence notes
```

### Policy plugin

Applies governance/security decisions.

Examples:

```text
source ACL inheritance
role-based filtering
sensitivity policy
PII blocking
published-only enforcement
```

### Exporter

Publishes or packages the brain.

Examples:

```text
static Markdown docs
JSON bundle
MCP resources
search index dump
graph export
SDK package
```

## Manifest

Each plugin should declare:

```yaml
name: local.markdown_vault
version: 0.1.0
description: Reads Markdown files from a local folder.
capabilities:
  - source_connector
  - parser
offline_safe: true
requires_network: false
```

## Python contract

The current scaffold includes Python plugin contracts in:

```text
src/ukb/plugins/contracts.py
src/ukb/plugins/registry.py
src/ukb/plugins/builtin.py
```

A simple connector looks like:

```python
from ukb.plugins.contracts import PluginCapability, PluginManifest, PluginResult

class LocalMarkdownConnector:
    manifest = PluginManifest(
        name="local.markdown",
        version="0.1.0",
        description="Read Markdown files from a local directory.",
        capabilities=(PluginCapability.source_connector,),
        offline_safe=True,
        requires_network=False,
    )

    def can_handle(self, source_type: str, source_uri: str | None = None) -> bool:
        return source_type == "markdown_folder"

    def ingest(self, payload: dict) -> PluginResult:
        return PluginResult(items=[], evidence=[], confidence=0.8)
```

## Runtime lifecycle

```text
load brain.config.yaml
  -> discover enabled plugins
  -> register plugin manifests
  -> run connector/parser/extractor pipeline
  -> create review items
  -> human approval
  -> publish approved objects
  -> expose via API/MCP/SDK
```

## Governance boundary

Every plugin must preserve:

```text
source evidence
confidence
warnings
sensitivity
source URI or local path
owner/reviewer metadata when known
```

Every plugin result should be reviewable by a human.

## Offline-safe plugin rules

An offline-safe plugin:

- does not call external APIs
- does not require SaaS credentials
- can run on a GitLab/Linux server
- can operate on local files or local services
- produces deterministic output when AI is disabled

A network plugin must declare `requires_network: true`.

## Future package formats

The platform can support multiple plugin packaging styles:

```text
local Python module
installed Python package
local npm package
MCP server adapter
containerized connector
Git repository plugin
```

The first production-safe implementation should support local Python plugins and Git-backed brain packages before adding remote plugin installation.
