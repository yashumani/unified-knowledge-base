import { collapseWhitespace, newId, sentenceWith } from "./config";
import type {
  AIEnrichmentResult,
  KnowledgeObject,
  SourceEvidence,
  SuggestedRelationship,
  ValidationFinding,
  ValidationSeverity
} from "../types";

/**
 * Browser port of ukb.ai.providers.noop.NoopProvider.enrich_source.
 *
 * This is not a fake. The backend already ships a deterministic, zero-network
 * enrichment provider — it is what runs whenever the platform is in
 * offline_no_model mode. Running the same algorithm in the browser means the
 * demo is honest about what produced the brief, needs no dependency, and
 * cannot drift into inventing findings the real provider would not raise.
 *
 * Every heuristic below mirrors its Python counterpart, including the exact
 * severity levels and message wording, so the two stay comparable.
 */

const TOPIC_MAP: Array<[string, string[]]> = [
  ["support", ["support operations"]],
  ["incident", ["incident management"]],
  ["sla", ["sla"]],
  ["dashboard", ["dashboard"]],
  ["metric", ["metric definition"]],
  ["rule", ["business rule"]],
  ["quality", ["quality review"]]
];

const CONFIDENCE_KEYWORDS = ["definition", "owned by", "dashboard", "metric", "excluding", "review"];

function sourceKind(lowered: string, source: SourceEvidence): string {
  if (
    lowered.includes("metric") ||
    lowered.includes("average") ||
    lowered.includes("rate") ||
    lowered.includes("kpi")
  ) {
    return "metric_definition";
  }
  if (lowered.includes("dashboard") || source.source_type === "dashboard") {
    return "report_or_dashboard_context";
  }
  if (
    lowered.includes("rule") ||
    lowered.includes("must") ||
    lowered.includes("policy") ||
    lowered.includes("caveat")
  ) {
    return "business_rule";
  }
  if (lowered.includes("select ") || lowered.includes(" from ")) return "sql_or_lineage";
  return "general_context";
}

function topicsFor(lowered: string): string[] {
  const topics: string[] = [];
  for (const [keyword, values] of TOPIC_MAP) {
    if (lowered.includes(keyword)) topics.push(...values);
  }
  const unique = [...new Set(topics)].sort();
  return unique.length ? unique : ["general context"];
}

function findingsFor(
  clean: string,
  lowered: string,
  candidate: KnowledgeObject
): ValidationFinding[] {
  const findings: ValidationFinding[] = [];

  if (!candidate.owner) {
    findings.push({
      severity: "medium",
      finding_type: "owner_missing",
      message:
        "No owner was detected. A reviewer should assign a responsible owner before publishing.",
      source_span: null,
      recommended_action: "Request changes or assign an owner during review."
    });
  }
  if (lowered.includes("excluding") || lowered.includes("exclude")) {
    findings.push({
      severity: "medium",
      finding_type: "exclusion_rule_needs_review",
      message:
        "The source mentions an exclusion rule. Confirm how this exclusion is implemented before approval.",
      source_span: sentenceWith(clean, "exclud"),
      recommended_action: "Ask the domain owner to confirm exclusion logic."
    });
  }
  if (lowered.includes("recent") || lowered.includes("settle") || lowered.includes("preliminary")) {
    findings.push({
      severity: "low",
      finding_type: "freshness_caveat_detected",
      message:
        "The source includes a freshness or review-window caveat that should be carried into context packs.",
      source_span: sentenceWith(clean, "settle") ?? sentenceWith(clean, "recent"),
      recommended_action: "Keep this caveat attached to the candidate object."
    });
  }
  if (candidate.type === "Unknown") {
    findings.push({
      severity: "medium",
      finding_type: "object_type_unclear",
      message: "The deterministic classifier could not confidently identify the object type.",
      source_span: null,
      recommended_action: "Have a reviewer classify the object manually."
    });
  }
  if (clean.length < 80) {
    findings.push({
      severity: "low",
      finding_type: "source_context_short",
      message: "The source context is short. Reviewers may need more evidence before approval.",
      source_span: null,
      recommended_action: "Attach a richer source or add more detail."
    });
  }
  return findings;
}

function relationshipsFor(
  clean: string,
  lowered: string,
  candidate: KnowledgeObject
): SuggestedRelationship[] {
  const relationships: SuggestedRelationship[] = [];
  const dashboardMatch = clean.match(/appears in the ([A-Za-z0-9 _&-]+ dashboard)/i);
  if (dashboardMatch) {
    relationships.push({
      source_label: candidate.title,
      relationship_type: "appears_in",
      target_label: dashboardMatch[1].trim(),
      confidence: 0.82,
      rationale: "The source explicitly says the item appears in a dashboard."
    });
  }
  if (
    lowered.includes("caveat") ||
    lowered.includes("settle") ||
    lowered.includes("preliminary")
  ) {
    relationships.push({
      source_label: candidate.title,
      relationship_type: "governed_by",
      target_label: "Review Window Caveat",
      confidence: 0.65,
      rationale: "The source includes a caveat or review-window condition."
    });
  }
  return relationships;
}

function reviewQuestions(lowered: string, candidate: KnowledgeObject): string[] {
  const questions = ["Is this candidate safe to publish as approved organizational context?"];
  if (!candidate.owner) questions.push("Who owns this definition or rule?");
  if (lowered.includes("excluding") || lowered.includes("exclude")) {
    questions.push("How are excluded records identified in the source system?");
  }
  if (lowered.includes("dashboard")) {
    questions.push("Is the named dashboard the official reporting surface?");
  }
  if (lowered.includes("settle") || lowered.includes("recent")) {
    questions.push("How long should this context be treated as preliminary?");
  }
  return questions;
}

function enrichmentConfidence(lowered: string): number {
  let score = 0.45;
  for (const keyword of CONFIDENCE_KEYWORDS) {
    if (lowered.includes(keyword)) score += 0.07;
  }
  return Math.min(Number(score.toFixed(2)), 0.9);
}

const ELEVATED: ValidationSeverity[] = ["medium", "high", "critical"];

export function enrichSource({
  source,
  content,
  candidate
}: {
  source: SourceEvidence;
  content: string;
  candidate: KnowledgeObject;
}): AIEnrichmentResult {
  const clean = collapseWhitespace(content);
  const lowered = clean.toLowerCase();
  const kind = sourceKind(lowered, source);
  const topics = topicsFor(lowered);
  const findings = findingsFor(clean, lowered, candidate);
  const relationships = relationshipsFor(clean, lowered, candidate);
  const confidence = enrichmentConfidence(lowered);

  const action = findings.some((finding) => finding.severity === "medium")
    ? ("request_changes" as const)
    : ("needs_review" as const);

  const riskCount = findings.filter((finding) => finding.severity !== "info").length;

  const enrichedCandidate: KnowledgeObject = {
    ...candidate,
    status: "human_review_required",
    attributes: {
      ...candidate.attributes,
      ai_enrichment_provider: "noop",
      ai_detected_source_kind: kind,
      ai_topics: topics
    }
  };

  return {
    id: newId("ai"),
    provider: "noop",
    model: "deterministic",
    status: "completed",
    source_classification: {
      source_kind: kind,
      domain: source.domain,
      summary: clean.length <= 280 ? clean : `${clean.slice(0, 277)}...`,
      topics,
      suggested_tags: [...new Set([source.domain, kind, ...topics])].sort(),
      confidence
    },
    extracted_objects: [enrichedCandidate],
    suggested_relationships: relationships,
    validation_findings: findings,
    review_brief: {
      summary:
        `Detected ${kind} and prepared a ${candidate.type} candidate named ` +
        `'${candidate.title}'. ${riskCount} review finding(s) should be checked before approval.`,
      recommended_action: action,
      reviewer_questions: reviewQuestions(lowered, candidate),
      risk_flags: findings
        .filter((finding) => ELEVATED.includes(finding.severity))
        .map((finding) => finding.finding_type)
    },
    confidence,
    error_message: null,
    created_at: new Date().toISOString()
  };
}
