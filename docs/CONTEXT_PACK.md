# Context Pack

## Purpose

A context pack is the reusable unit served by the AI Brain.

It is not the final answer. It is the governed context that allows an AI app to produce a grounded answer.

## Shape

```json
{
  "context_pack_id": "ctx_...",
  "question": "Why is device revenue down?",
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
  "question": "Why is device revenue down vs forecast?",
  "mode": "executive_insight",
  "access_decision": "allowed",
  "confidence": 0.86,
  "answer_guidance": "Explain variance using approved metric definition and known month-end caveats.",
  "knowledge_objects": [
    {
      "id": "finance.metric.device_revenue",
      "type": "Metric",
      "title": "Device Revenue",
      "summary": "Revenue from device sales, excluding service revenue.",
      "status": "published"
    }
  ],
  "evidence": [
    {
      "source_id": "source_demo_metric_definition",
      "quote": "Device Revenue is revenue generated from device sales, excluding service revenue.",
      "confidence": 0.94
    }
  ],
  "caveats": [
    "Month-end finance adjustments may not be complete before WD4."
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
