import { collapseWhitespace, newId } from "./config";
import type { IngestionPayload, KnowledgeObject, ReviewItem, SourceEvidence } from "../types";

/**
 * Browser port of ukb.services.compiler.BrainCompiler.
 *
 * Demo mode previously guessed with `content.includes("dashboard") ? "Report"
 * : "Metric"` and a hardcoded 0.67 confidence, then presented the result as
 * classifier output. This runs the same heuristics the backend runs, so a demo
 * submission produces the candidate the real compiler would.
 */

const METRIC_PATTERNS = [
  /\bmetric\b/i,
  /\bkpi\b/i,
  /\bincident\b/i,
  /\bresolution\b/i,
  /\bresponse time\b/i,
  /\breopen rate\b/i,
  /\bbacklog\b/i
];

const REPORT_PATTERNS = [/\bdashboard\b/i, /\breport\b/i, /\breview\b/i];

const RULE_PATTERNS = [/\brule\b/i, /\bpolicy\b/i, /\bmust\b/i, /\bexclude\b/i, /\bcaveat\b/i];

const CONFIDENCE_KEYWORDS = [
  "definition",
  "owned by",
  "source",
  "dashboard",
  "metric",
  "rule",
  "exclude",
  "incident"
];

/** Owner names run until a clause boundary; see BrainCompiler.owner_stop_words. */
const OWNER_STOP_WORDS = [" and ", " but ", " which ", " that ", " with ", " for "];

export function classify(content: string): string {
  if (METRIC_PATTERNS.some((pattern) => pattern.test(content))) return "Metric";
  if (REPORT_PATTERNS.some((pattern) => pattern.test(content))) return "Report";
  if (RULE_PATTERNS.some((pattern) => pattern.test(content))) return "BusinessRule";
  return "Unknown";
}

export function summarize(content: string): string {
  const cleaned = collapseWhitespace(content);
  return cleaned.length <= 240 ? cleaned : `${cleaned.slice(0, 237)}...`;
}

export function excerpt(content: string, limit = 500): string {
  return collapseWhitespace(content).slice(0, limit);
}

export function compilerConfidence(content: string): number {
  let score = 0.45;
  const lowered = content.toLowerCase();
  for (const keyword of CONFIDENCE_KEYWORDS) {
    if (lowered.includes(keyword)) score += 0.07;
  }
  return Math.min(score, 0.92);
}

export function extractOwner(content: string): string | null {
  const match = content.match(/owned by ([A-Za-z0-9 _&-]+)/i);
  if (!match) return null;

  let owner = match[1].trim();
  let lowered = owner.toLowerCase();
  for (const stopWord of OWNER_STOP_WORDS) {
    const index = lowered.indexOf(stopWord);
    if (index > 0) {
      owner = owner.slice(0, index);
      lowered = owner.toLowerCase();
    }
  }
  return owner.replace(/[.,;:]+$/, "").trim() || null;
}

export function compileSubmission(payload: IngestionPayload): {
  source: SourceEvidence;
  reviewItem: ReviewItem;
} {
  const now = new Date().toISOString();
  const source: SourceEvidence = {
    source_id: newId("source"),
    source_type: payload.source_type,
    title: payload.title,
    content_excerpt: excerpt(payload.content),
    source_uri: payload.source_uri ?? null,
    submitted_by: payload.submitted_by,
    domain: payload.domain,
    sensitivity: payload.sensitivity,
    created_at: now
  };

  const candidate: KnowledgeObject = {
    id: newId("obj"),
    type: classify(payload.content),
    title: payload.title,
    summary: summarize(payload.content),
    domain: payload.domain,
    owner: extractOwner(payload.content),
    status: "human_review_required",
    sensitivity: payload.sensitivity,
    source_ids: [source.source_id],
    relationships: [],
    attributes: {
      tags: payload.tags,
      raw_excerpt: excerpt(payload.content, 1000),
      compiler: "heuristic-v0",
      simulated: true
    },
    confidence: compilerConfidence(payload.content),
    created_at: now,
    updated_at: now
  };

  return {
    source,
    reviewItem: {
      id: newId("review"),
      source_id: source.source_id,
      candidate_object: candidate,
      ai_enrichment: null,
      status: "human_review_required",
      reviewer: null,
      review_comment: null,
      created_at: now,
      updated_at: now
    }
  };
}
