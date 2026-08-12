# Product Requirements

## Product name

Unified Knowledge Base / AI Brain Platform

## Problem

Enterprises have context spread across documents, dashboards, SQL, spreadsheets, tickets, and human memory. AI applications can retrieve a number or a document snippet, but they often lack the business meaning required to create reliable insights.

## Users

### Context Submitter

Provides documents, definitions, notes, SQL, or business rules.

### Domain Reviewer

Validates whether extracted knowledge is correct.

### Governance Admin

Controls ontology, role rules, review policies, and publication.

### AI App Developer

Consumes context through API, SDK, or MCP.

### Business User

Asks questions through a chatbot, BI copilot, or insight app.

## Core use cases

1. Submit context into the AI Brain.
2. AI classifies and converts context into candidate knowledge objects.
3. Human reviewer approves or rejects candidate knowledge.
4. Approved knowledge is published.
5. AI apps retrieve context packs.
6. Context packs explain numbers, rules, lineage, and caveats.

## MVP acceptance criteria

- A submitter can submit text context.
- The compiler creates at least one candidate object.
- A reviewer can approve the candidate.
- Approved knowledge appears in the brain store.
- A consumer can request a context pack.
- The context pack includes evidence, confidence, and governance status.
- MCP and REST call the same core logic.
