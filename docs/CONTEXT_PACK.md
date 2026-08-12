# Context Pack

## Purpose

A context pack is the reusable unit served by the AI Brain.

It is not the final answer. It is the governed context that allows an AI app to produce a grounded answer.

## Shape

```json
{
  "context_pack_id": "ctx_...",
  "question": "Why did incident resolution time increase?",
  "mode": "executive_insight",
  "access_decision": "allowed",
  "confidence": 0.82,
  "answer_guidance": "Use approved metric definitions, source caveats, and related drivers.",
  "knowledge_objects": [],
  "evidence": [],
  "rules": [],
  "caveats": [],
  "related_objects": [],
  "freshness": {
    "status": "fresh",
    "oldest_source_age_days": 3
  }
}
```

## Required fields

```text
context_pack_id
question
user_id
mode
access_decision
knowledge_objects
evidence
confidence
generated_at
```

## Optional fields

```text
business_rules
caveats
lineage
related_metrics
narrative_template
prompt_hint
freshness
conflicts
recommended_followups
```

## Modes

Initial modes:

```text
default
executive_insight
metric_definition
lineage
governance_review
debug
```

## Neutral example

This example is synthetic and workplace-safe.

```json
{
  "context_pack_id": "ctx_demo_001",
  "question": "Why did incident resolution time increase?",
  "mode": "executive_insight",
  "access_decision": "allowed",
  "confidence": 0.86,
  "answer_guidance": "Explain the movement using the approved Incident Resolution Time definition and SLA review-window caveat.",
  "knowledge_objects": [
    {
      "id": "support.metric.incident_resolution_time",
      "type": "Metric",
      "title": "Incident Resolution Time",
      "summary": "Average elapsed time from incident creation to resolved status for product support cases.",
      "status": "published"
    }
  ],
  "evidence": [
    {
      "source_id": "source_demo_incident_resolution",
      "quote": "Incident Resolution Time is the average elapsed time from incident creation to resolved status for product support cases.",
      "confidence": 0.94
    }
  ],
  "caveats": [
    "Recently resolved incidents may need 24 hours for quality review tags to settle."
  ],
  "recommended_followups": [
    "Check related drivers: first response time, reopen rate, ticket backlog, and incident severity mix."
  ]
}
```

## Design rules

1. Context packs should be deterministic enough to test.
2. Context packs should include evidence.
3. Context packs should enforce access before retrieval.
4. Context packs should expose confidence and caveats.
5. Context packs should not require the consumer to understand source-system internals.
