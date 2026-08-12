import type { BrainGraph, ContextPack, KnowledgeObject, ReviewItem, SourceEvidence } from "../types";

const now = new Date().toISOString();

export const demoSources: SourceEvidence[] = [
  {
    source_id: "source_demo_sample_order_value",
    source_type: "document",
    title: "Sample Order Value Definition",
    content_excerpt: "Sample Order Value is value of sample orders, excluding test orders. It appears in the example sales dashboard and is owned by Demo Analytics.",
    source_uri: "local://synthetic/sample-order-value.md",
    submitted_by: "demo.user",
    domain: "finance",
    sensitivity: "internal",
    created_at: now
  },
  {
    source_id: "source_demo_month_end",
    source_type: "manual",
    title: "Month-End Close Caveat",
    content_excerpt: "Demo data checks may not be complete before the sample cutoff. Executive narratives should call this out when data is preliminary.",
    source_uri: "local://synthetic/month-end-close.md",
    submitted_by: "demo.user",
    domain: "finance",
    sensitivity: "internal",
    created_at: now
  }
];

export const demoObjects: KnowledgeObject[] = [
  {
    id: "finance.metric.sample_order_value",
    type: "Metric",
    title: "Sample Order Value",
    summary: "Revenue generated from device sales, excluding service revenue.",
    domain: "finance",
    owner: "Demo Analytics",
    status: "published",
    sensitivity: "internal",
    source_ids: ["source_demo_sample_order_value"],
    relationships: [
      { type: "appears_in", target_id: "finance.report.example_sales_dashboard", confidence: 0.86 },
      { type: "governed_by", target_id: "finance.rule.month_end_close", confidence: 0.79 }
    ],
    attributes: {
      caveats: ["Demo data checks may not be complete before the sample cutoff."],
      related_metrics: ["device_units", "upgrade_rate", "promo_credit"]
    },
    confidence: 0.91,
    created_at: now,
    updated_at: now
  },
  {
    id: "finance.report.example_sales_dashboard",
    type: "Report",
    title: "Example Sales Dashboard",
    summary: "Executive dashboard used for monthly KPI reporting and variance review.",
    domain: "finance",
    owner: "Executive Reporting",
    status: "published",
    sensitivity: "internal",
    source_ids: ["source_demo_sample_order_value"],
    relationships: [],
    attributes: { refresh_frequency: "daily" },
    confidence: 0.82,
    created_at: now,
    updated_at: now
  },
  {
    id: "finance.rule.month_end_close",
    type: "BusinessRule",
    title: "Month-End Close Caveat",
    summary: "Treat sample metrics as preliminary until demo checks are complete.",
    domain: "finance",
    owner: "Finance Governance",
    status: "published",
    sensitivity: "internal",
    source_ids: ["source_demo_month_end"],
    relationships: [],
    attributes: { review_cadence: "monthly" },
    confidence: 0.88,
    created_at: now,
    updated_at: now
  }
];

export const demoReviewItems: ReviewItem[] = [
  {
    id: "review_demo_upgrade_rate",
    source_id: "source_demo_sample_order_value",
    candidate_object: {
      id: "finance.metric.upgrade_rate",
      type: "Metric",
      title: "Upgrade Rate",
      summary: "Candidate metric for customer upgrade activity that may explain sample order value movement.",
      domain: "finance",
      owner: "Demo Analytics",
      status: "human_review_required",
      sensitivity: "internal",
      source_ids: ["source_demo_sample_order_value"],
      relationships: [{ type: "related_to", target_id: "finance.metric.sample_order_value", confidence: 0.74 }],
      attributes: { compiler: "demo" },
      confidence: 0.72,
      created_at: now,
      updated_at: now
    },
    status: "human_review_required",
    reviewer: null,
    review_comment: null,
    created_at: now,
    updated_at: now
  }
];

export const demoGraph: BrainGraph = {
  generated_at: now,
  nodes: [
    ...demoSources.map((source) => ({
      id: source.source_id,
      label: source.title,
      type: "source_evidence",
      domain: source.domain,
      status: "evidence",
      sensitivity: source.sensitivity,
      confidence: 1,
      metadata: source
    })),
    ...demoObjects.map((object) => ({
      id: object.id,
      label: object.title,
      type: object.type,
      domain: object.domain,
      status: object.status,
      sensitivity: object.sensitivity,
      confidence: object.confidence,
      metadata: object
    })),
    ...demoReviewItems.map((item) => ({
      id: item.id,
      label: `Review: ${item.candidate_object.title}`,
      type: "review_item",
      domain: item.candidate_object.domain,
      status: item.status,
      sensitivity: item.candidate_object.sensitivity,
      confidence: item.candidate_object.confidence,
      metadata: item
    })),
    ...demoReviewItems.map((item) => ({
      id: item.candidate_object.id,
      label: item.candidate_object.title,
      type: "candidate_object",
      domain: item.candidate_object.domain,
      status: item.candidate_object.status,
      sensitivity: item.candidate_object.sensitivity,
      confidence: item.candidate_object.confidence,
      metadata: item.candidate_object
    }))
  ],
  edges: [
    { id: "source_demo_sample_order_value::evidence_for::finance.metric.sample_order_value", source: "source_demo_sample_order_value", target: "finance.metric.sample_order_value", type: "evidence_for", confidence: 0.91, metadata: {} },
    { id: "source_demo_month_end::evidence_for::finance.rule.month_end_close", source: "source_demo_month_end", target: "finance.rule.month_end_close", type: "evidence_for", confidence: 0.88, metadata: {} },
    { id: "finance.metric.sample_order_value::appears_in::finance.report.example_sales_dashboard", source: "finance.metric.sample_order_value", target: "finance.report.example_sales_dashboard", type: "appears_in", confidence: 0.86, metadata: {} },
    { id: "finance.metric.sample_order_value::governed_by::finance.rule.month_end_close", source: "finance.metric.sample_order_value", target: "finance.rule.month_end_close", type: "governed_by", confidence: 0.79, metadata: {} },
    { id: "source_demo_sample_order_value::submitted_as::review_demo_upgrade_rate", source: "source_demo_sample_order_value", target: "review_demo_upgrade_rate", type: "submitted_as", confidence: 0.5, metadata: {} },
    { id: "review_demo_upgrade_rate::reviews::finance.metric.upgrade_rate", source: "review_demo_upgrade_rate", target: "finance.metric.upgrade_rate", type: "reviews", confidence: 0.72, metadata: {} },
    { id: "finance.metric.upgrade_rate::related_to::finance.metric.sample_order_value", source: "finance.metric.upgrade_rate", target: "finance.metric.sample_order_value", type: "related_to", confidence: 0.74, metadata: {} }
  ]
};

export const demoContextPack: ContextPack = {
  context_pack_id: "ctx_demo_sample_order_value",
  question: "Why is sample order value down?",
  user_id: "demo.user",
  mode: "executive_insight",
  access_decision: "allowed",
  confidence: 0.86,
  answer_guidance: "Use the approved Sample Order Value definition, mention DEMO_CUTOFF caveat, and check driver metrics before finalizing an executive narrative.",
  knowledge_objects: demoObjects,
  evidence: demoSources,
  caveats: ["Demo data checks may not be complete before the sample cutoff."],
  related_objects: ["finance.report.example_sales_dashboard", "finance.rule.month_end_close"],
  recommended_followups: [
    "Check related driver metrics: device units, upgrade rate, promotional credits, and returns.",
    "Confirm whether the current period is preliminary or final."
  ],
  generated_at: now
};
