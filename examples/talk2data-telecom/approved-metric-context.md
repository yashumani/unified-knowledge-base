---
id: postpaid-churn-context
tenant_id: synthetic-telecom
type: metric_context
domain: subscriber
status: approved
classification: internal
effective_from: 2026-01-01T00:00:00Z
effective_to:
owner: Synthetic Subscriber Analytics
approved_by: synthetic.domain.reviewer
related_metrics:
  - postpaid_churn_rate
related_entities:
  - subscriber
  - service_plan
source: obsidian://synthetic-telecom/postpaid-churn-context
version: 1
authority_level: approved
allowed_roles:
  - consumer
  - analyst
  - reviewer
tags:
  - synthetic
  - talk2data
---

# Postpaid churn context

Postpaid churn should be interpreted with the approved [[Postpaid Churn]] definition and segmented by [[Service Plan]] only when the requested reporting period and subscriber population are explicit.

The raw source is synthetic and contains no employer data.
