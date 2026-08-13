import type { BrainGraph, ContextPack, KnowledgeObject, ReviewItem, SourceEvidence } from "../types";

const now = new Date().toISOString();

export const demoSources: SourceEvidence[] = [
  {
    source_id: "source_demo_incident_resolution",
    source_type: "document",
    title: "Incident Resolution Time Definition",
    content_excerpt: "Incident Resolution Time is the average elapsed time from incident creation to resolved status for product support cases, excluding duplicate incidents and customer-wait periods. It appears in the SLA Review Dashboard and is owned by Support Operations.",
    source_uri: "local://synthetic/incident-resolution-time.md",
    submitted_by: "demo.user",
    domain: "support",
    sensitivity: "internal",
    created_at: now
  },
  {
    source_id: "source_demo_sla_review_window",
    source_type: "manual",
    title: "SLA Review Window Caveat",
    content_excerpt: "Recently resolved incidents may need 24 hours for quality review tags to settle. Reopened incidents can change final resolution-time calculations.",
    source_uri: "local://synthetic/sla-review-window.md",
    submitted_by: "demo.user",
    domain: "support",
    sensitivity: "internal",
    created_at: now
  }
];

export const demoObjects: KnowledgeObject[] = [
  {
    id: "support.metric.incident_resolution_time",
    type: "Metric",
    title: "Incident Resolution Time",
    summary: "Average elapsed time from incident creation to resolved status for product support cases.",
    domain: "support",
    owner: "Support Operations",
    status: "published",
    sensitivity: "internal",
    source_ids: ["source_demo_incident_resolution"],
    relationships: [
      { type: "appears_in", target_id: "support.report.sla_review_dashboard", confidence: 0.86 },
      { type: "governed_by", target_id: "support.rule.sla_review_window", confidence: 0.79 }
    ],
    attributes: {
      caveats: ["Recently resolved incidents may need 24 hours for quality review tags to settle."],
      related_metrics: ["first_response_time", "reopen_rate", "ticket_backlog"]
    },
    confidence: 0.91,
    created_at: now,
    updated_at: now
  },
  {
    id: "support.report.sla_review_dashboard",
    type: "Report",
    title: "SLA Review Dashboard",
    summary: "Generic operations dashboard used for support health and service-level review.",
    domain: "support",
    owner: "Support Operations",
    status: "published",
    sensitivity: "internal",
    source_ids: ["source_demo_incident_resolution"],
    relationships: [],
    attributes: { refresh_frequency: "daily" },
    confidence: 0.82,
    created_at: now,
    updated_at: now
  },
  {
    id: "support.rule.sla_review_window",
    type: "BusinessRule",
    title: "SLA Review Window",
    summary: "Treat newly resolved incidents as preliminary until quality review tags settle.",
    domain: "support",
    owner: "Support Governance",
    status: "published",
    sensitivity: "internal",
    source_ids: ["source_demo_sla_review_window"],
    relationships: [],
    attributes: { review_cadence: "weekly" },
    confidence: 0.88,
    created_at: now,
    updated_at: now
  }
];

const demoCandidate: KnowledgeObject = {
  id: "support.metric.reopen_rate",
  type: "Metric",
  title: "Reopen Rate",
  summary: "Candidate metric for the share of resolved incidents reopened after initial resolution.",
  domain: "support",
  owner: "Support Operations",
  status: "human_review_required",
  sensitivity: "internal",
  source_ids: ["source_demo_incident_resolution"],
  relationships: [{ type: "related_to", target_id: "support.metric.incident_resolution_time", confidence: 0.74 }],
  attributes: { compiler: "demo" },
  confidence: 0.72,
  created_at: now,
  updated_at: now
};

export const demoReviewItems: ReviewItem[] = [
  {
    id: "review_demo_reopen_rate",
    source_id: "source_demo_incident_resolution",
    candidate_object: demoCandidate,
    ai_enrichment: {
      id: "ai_demo_reopen_rate",
      provider: "ollama",
      model: "llama3.1",
      status: "completed",
      source_classification: {
        source_kind: "metric_definition",
        domain: "support",
        summary: "Local Ollama enrichment identified a support metric candidate and a related operational driver.",
        topics: ["support operations", "incident management", "metric definition"],
        suggested_tags: ["support", "metric_definition", "incident management"],
        confidence: 0.76
      },
      extracted_objects: [demoCandidate],
      suggested_relationships: [
        {
          source_label: "Reopen Rate",
          relationship_type: "related_to",
          target_label: "Incident Resolution Time",
          confidence: 0.74,
          rationale: "Reopened incidents can change final resolution-time calculations."
        }
      ],
      validation_findings: [
        {
          severity: "medium",
          finding_type: "definition_needs_precision",
          message: "The candidate should define the time window and denominator before approval.",
          recommended_action: "Ask the reviewer to confirm whether reopened incidents are counted by created date, resolved date, or reopen date."
        }
      ],
      review_brief: {
        summary: "Local Ollama prepared a Reopen Rate candidate and found one definition gap that should be reviewed before publication.",
        recommended_action: "request_changes",
        reviewer_questions: [
          "What reporting window should Reopen Rate use?",
          "Should reopened incidents be counted once or every time they reopen?"
        ],
        risk_flags: ["definition_needs_precision"]
      },
      confidence: 0.72,
      created_at: now
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
    })),
    ...demoReviewItems.flatMap((item) => item.ai_enrichment ? [{
      id: item.ai_enrichment.id,
      label: `Ollama: ${item.candidate_object.title}`,
      type: "ai_enrichment",
      domain: item.candidate_object.domain,
      status: item.ai_enrichment.status,
      sensitivity: item.candidate_object.sensitivity,
      confidence: item.ai_enrichment.confidence,
      metadata: item.ai_enrichment
    }] : [])
  ],
  edges: [
    { id: "source_demo_incident_resolution::evidence_for::support.metric.incident_resolution_time", source: "source_demo_incident_resolution", target: "support.metric.incident_resolution_time", type: "evidence_for", confidence: 0.91, metadata: {} },
    { id: "source_demo_sla_review_window::evidence_for::support.rule.sla_review_window", source: "source_demo_sla_review_window", target: "support.rule.sla_review_window", type: "evidence_for", confidence: 0.88, metadata: {} },
    { id: "support.metric.incident_resolution_time::appears_in::support.report.sla_review_dashboard", source: "support.metric.incident_resolution_time", target: "support.report.sla_review_dashboard", type: "appears_in", confidence: 0.86, metadata: {} },
    { id: "support.metric.incident_resolution_time::governed_by::support.rule.sla_review_window", source: "support.metric.incident_resolution_time", target: "support.rule.sla_review_window", type: "governed_by", confidence: 0.79, metadata: {} },
    { id: "source_demo_incident_resolution::submitted_as::review_demo_reopen_rate", source: "source_demo_incident_resolution", target: "review_demo_reopen_rate", type: "submitted_as", confidence: 0.5, metadata: {} },
    { id: "review_demo_reopen_rate::reviews::support.metric.reopen_rate", source: "review_demo_reopen_rate", target: "support.metric.reopen_rate", type: "reviews", confidence: 0.72, metadata: {} },
    { id: "ai_demo_reopen_rate::enriches::review_demo_reopen_rate", source: "ai_demo_reopen_rate", target: "review_demo_reopen_rate", type: "enriches", confidence: 0.72, metadata: {} },
    { id: "support.metric.reopen_rate::related_to::support.metric.incident_resolution_time", source: "support.metric.reopen_rate", target: "support.metric.incident_resolution_time", type: "related_to", confidence: 0.74, metadata: {} }
  ]
};

export const demoContextPack: ContextPack = {
  context_pack_id: "ctx_demo_incident_resolution",
  question: "Why did incident resolution time increase?",
  user_id: "demo.user",
  mode: "executive_insight",
  access_decision: "allowed",
  confidence: 0.86,
  answer_guidance: "Use the approved Incident Resolution Time definition, mention the SLA review-window caveat, and check related support drivers before finalizing an operational narrative.",
  knowledge_objects: demoObjects,
  evidence: demoSources,
  caveats: ["Recently resolved incidents may need 24 hours for quality review tags to settle."],
  related_objects: ["support.report.sla_review_dashboard", "support.rule.sla_review_window"],
  recommended_followups: [
    "Check related driver metrics: first response time, reopen rate, ticket backlog, and incident severity mix.",
    "Confirm whether the current reporting window has completed quality review tagging."
  ],
  ai_guidance: "Local Ollama guidance: use only approved support-operations objects and source evidence; do not treat review candidates as official context.",
  missing_context: [],
  generated_at: now
};
