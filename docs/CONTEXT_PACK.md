# Context Pack

## Purpose

A context pack is the reusable unit served by the AI Brain.

It is not the final answer. It is the governed context that allows an AI app to produce a grounded answer.

## Shape

```json
{
  "context_pack_id": "ctx_...",
  "question": "Why is sample order value down?",
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

## Example

```json
{
  "context_pack_id": "ctx_demo_001",
  "question": "Why is sample order value down vs forecast?",
  "mode": "executive_insight",
  "access_decision": "allowed",
  "confidence": 0.86,
  "answer_guidance": "Explain variance using approved metric definition and known month-end caveats.",
  "knowledge_objects": [
    {
      "id": "finance.metric.sample_order_value",
      "type": "Metric",
      "title": "Sample Order Value",
      "summary": "Revenue from device sales, excluding service revenue.",
      "status": "published"
    }
  ],
  "evidence": [
    {
      "source_id": "source_demo_metric_definition",
      "quote": "Sample Order Value is value of sample orders, excluding test orders.",
      "confidence": 0.94
    }
  ],
  "caveats": [
    "Demo data checks may not be complete before the sample cutoff."
  ],
  "recommended_followups": [
    "Check related drivers: device units, upgrade rate, promotional credits, returns."
  ]
}
```

## Design rules

1. Context packs should be deterministic enough to test.
2. Context packs should include evidence.
3. Context packs should enforce access before retrieval.
4. Context packs should expose confidence and caveats.
5. Context packs should not require the consumer to understand source-system internals.
