import { newId } from "./config";
import type {
  ContextPack,
  ContextPackRequest,
  KnowledgeObject,
  SourceEvidence
} from "../types";

/**
 * Browser port of RetrievalService, ContextPackService and
 * NoopProvider.enrich_context_pack.
 *
 * Demo mode used to return one canned answer whatever you asked, listing
 * evidence it had not retrieved. That made the most important honesty state in
 * the product unreachable: a pack that comes back empty and says so. This does
 * real term matching over whatever is actually published, so asking something
 * unrelated produces a genuinely empty pack with populated missing_context.
 */

const SENSITIVITY_ORDER: Record<string, number> = {
  public: 0,
  internal: 1,
  confidential: 2,
  restricted: 3
};

/** Mirrors RetrievalService._score: terms longer than two characters. */
function score(query: string, haystack: string): number {
  const terms = query
    .toLowerCase()
    .split(/\s+/)
    .filter((term) => term.length > 2);
  return terms.reduce((total, term) => total + (haystack.includes(term) ? 1 : 0), 0);
}

function guidance(mode: string, hasObjects: boolean, denied: boolean): string {
  if (denied) {
    return (
      "Access denied by policy. Matching context exists but is above this user's clearance. " +
      "Do not speculate about the withheld content; tell the user to request access."
    );
  }
  if (!hasObjects) {
    return (
      "No approved brain objects matched this question. Answer cautiously, state that the " +
      "brain is missing context, and recommend submitting or approving relevant knowledge."
    );
  }
  if (mode === "executive_insight") {
    return (
      "Use approved definitions, business caveats, related drivers, and source evidence. " +
      "Keep the answer concise and decision-oriented."
    );
  }
  if (mode === "metric_definition") {
    return (
      "Explain the approved definition, owner, source evidence, caveats, and related metrics. " +
      "Do not invent formula details."
    );
  }
  return "Use only approved knowledge objects and cite evidence from the context pack.";
}

function caveatsFor(objects: KnowledgeObject[]): string[] {
  const caveats: string[] = [];
  for (const object of objects) {
    const raw = String(object.attributes?.raw_excerpt ?? "").toLowerCase();
    if (raw.includes("quality review") || raw.includes("reopened")) {
      caveats.push(
        "Recently resolved incidents may need time for quality review tags and reopen checks to settle."
      );
    }
    if (raw.includes("excluding") || raw.includes("exclude")) {
      caveats.push("Confirm inclusion/exclusion rules before comparing the metric.");
    }
  }
  return [...new Set(caveats)].sort();
}

function followups(mode: string, hasObjects: boolean, denied: boolean): string[] {
  if (denied) return ["Request access to the restricted domain from the governance admin."];
  if (!hasObjects) return ["Submit or approve source context related to this question."];
  if (mode === "executive_insight") {
    return [
      "Check related driver metrics before finalizing the narrative.",
      "Validate whether the source data is final or still preliminary.",
      "Ask the metric owner to confirm caveats before sharing the explanation."
    ];
  }
  return ["Review the source evidence and object owner before using this in production."];
}

export function buildContextPack({
  request,
  objects,
  sources,
  clearance = "internal"
}: {
  request: ContextPackRequest;
  objects: KnowledgeObject[];
  sources: SourceEvidence[];
  clearance?: string;
}): ContextPack {
  const domainFilter = new Set(request.domains ?? []);
  const clearanceRank = SENSITIVITY_ORDER[clearance] ?? 1;

  const matched = objects
    .filter((object) => (domainFilter.size ? domainFilter.has(object.domain) : true))
    .map((object) => {
      const haystack = [
        object.title,
        object.summary,
        object.type,
        object.domain,
        JSON.stringify(object.attributes ?? {})
      ]
        .join(" ")
        .toLowerCase();
      return { object, hits: score(request.question, haystack) };
    })
    .filter((entry) => entry.hits > 0)
    .sort((a, b) => b.hits - a.hits)
    .map((entry) => entry.object);

  // Policy runs before composition, never after: the pack is assembled from
  // what the caller may see, rather than filtered on the way out.
  const allowed = matched.filter(
    (object) => (SENSITIVITY_ORDER[object.sensitivity] ?? 1) <= clearanceRank
  );
  const deniedCount = matched.length - allowed.length;
  const denied = deniedCount > 0 && allowed.length === 0;
  const selected = allowed.slice(0, 8);

  const evidence: SourceEvidence[] = [];
  for (const object of selected) {
    for (const sourceId of object.source_ids) {
      const source = sources.find((candidate) => candidate.source_id === sourceId);
      if (source && (SENSITIVITY_ORDER[source.sensitivity] ?? 1) <= clearanceRank) {
        evidence.push(source);
      }
    }
  }

  const caveats = caveatsFor(selected);
  if (deniedCount > 0 && selected.length > 0) {
    caveats.push(
      `${deniedCount} matching knowledge object(s) were withheld by the access policy for ` +
        `clearance '${clearance}'. This context pack is incomplete.`
    );
  }

  const missingContext: string[] = [];
  if (denied) {
    missingContext.push(
      "Every matching knowledge object is above your access clearance. Request elevated access " +
        "instead of inferring the withheld content."
    );
  } else if (selected.length === 0) {
    missingContext.push(
      "No approved knowledge objects matched the question. Submit and approve source context first."
    );
  }

  const averageConfidence = selected.length
    ? selected.reduce((total, object) => total + object.confidence, 0) / selected.length
    : 0;
  const confidence = selected.length
    ? Math.min(Number((averageConfidence + Math.min(evidence.length * 0.03, 0.15)).toFixed(2)), 0.95)
    : 0.2;

  const aiGuidance = selected.length
    ? `Offline enrichment found approved context for: ${selected
        .slice(0, 3)
        .map((object) => object.title)
        .join(", ")}. Use source evidence, caveats, and reviewer-approved relationships only.`
    : "Offline enrichment found no approved objects to ground this request.";

  const recommended = followups(request.mode, selected.length > 0, denied);
  if (selected.length > 0) {
    recommended.push("Review source evidence before sharing this outside the approved audience.");
  }

  return {
    context_pack_id: newId("ctx"),
    question: request.question,
    user_id: request.user_id,
    mode: request.mode,
    access_decision: denied ? "denied" : "allowed",
    confidence,
    answer_guidance: guidance(request.mode, selected.length > 0, denied),
    knowledge_objects: selected,
    evidence,
    caveats: [...new Set(caveats)],
    related_objects: [
      ...new Set(
        selected.flatMap((object) => object.relationships.map((relation) => relation.target_id))
      )
    ].sort(),
    recommended_followups: [...new Set(recommended)],
    ai_guidance: aiGuidance,
    missing_context: missingContext,
    generated_at: new Date().toISOString()
  };
}
