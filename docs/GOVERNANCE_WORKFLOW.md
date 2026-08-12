# Governance Workflow

## Why this matters

Enterprise AI Brain quality depends on trust.

The platform should not let AI-generated extraction automatically become official knowledge. AI creates candidates. Humans approve official knowledge.

## Roles

```text
Submitter
  Provides source context.

AI Curator
  System role that classifies, extracts, links, and scores candidates.

Domain Reviewer
  Human SME who validates correctness.

Governance Admin
  Controls ontology, roles, policies, and publication rules.

Consumer
  Uses approved knowledge through API, SDK, MCP, or UI.
```

## State machine

```text
draft
  -> submitted
  -> ai_classified
  -> human_review_required
  -> approved
  -> published
  -> deprecated
```

Alternative paths:

```text
human_review_required -> rejected
human_review_required -> changes_requested
changes_requested -> submitted
published -> deprecated
```

## Workflow

### 1. Context submission

A user submits context:

```text
title
source_type
source_uri or content
domain
sensitivity
tags
submitted_by
```

### 2. AI classification

Compiler creates candidate objects:

```text
object_type
candidate_title
summary
extracted_entities
relationships
confidence
source_refs
risk_flags
```

### 3. Human review

Reviewer sees:

```text
original evidence
AI summary
candidate object
confidence
conflicts
policy flags
suggested relationships
```

Reviewer can:

```text
approve
reject
request changes
merge with existing object
mark duplicate
assign owner
change sensitivity
```

### 4. Publish

After approval, the item becomes a published brain object.

Published objects must include:

```text
owner
status
approval metadata
source evidence
updated_at
sensitivity
access policy
```

### 5. Runtime use

Only published/approved objects should be used for official context packs unless the consumer explicitly requests draft mode and has permission.

## Conflict handling

The system should flag conflicts such as:

```text
same metric name, different formula
same report, different owner
same source, different freshness date
same business rule, conflicting exceptions
same term, different domain meaning
```

## Freshness handling

Every object should have:

```text
last_validated_at
valid_until
freshness_status
owner
review_cadence
```

Freshness statuses:

```text
fresh
aging
stale
expired
unknown
```

## Audit events

Every material action should write an audit event:

```text
submission_created
candidate_generated
review_approved
review_rejected
object_published
object_deprecated
context_pack_requested
policy_denied
```

## Production rule

In production, reviewer actions should be non-repudiable:

```text
who
what
when
source IP/session
before/after diff
comment
```
