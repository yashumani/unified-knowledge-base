import { GOVERNANCE_MEANING, LOCKED_REASON } from "./copy";
import type { PipelineSnapshot, StepDefinition } from "./types";

/** Candidates a human still has to decide on. */
export const pendingItems = (s: PipelineSnapshot) =>
  s.reviewItems.filter((item) => item.status === "human_review_required");

/** Candidates sent back for rework; still live, not yet decided. */
export const changesRequestedItems = (s: PipelineSnapshot) =>
  s.reviewItems.filter((item) => item.status === "changes_requested");

export const unenrichedItems = (s: PipelineSnapshot) =>
  s.reviewItems.filter((item) => !item.ai_enrichment);

const plural = (n: number, one: string, many = `${one}s`) => (n === 1 ? one : many);

/**
 * The five stages of the governed pipeline, and the only place their order,
 * naming and anchors are defined. The stepper, the side navigation and every
 * section header render from this array, so they cannot drift apart.
 */
export const STEPS: readonly StepDefinition[] = [
  {
    id: "submit",
    number: 1,
    label: "Submit",
    verb: "Submit source context",
    category: "Context ingestion",
    sectionId: "context-ingestion",
    governanceMeaning: GOVERNANCE_MEANING.submit,
    // Never locked: this is how anything enters the pipeline at all.
    progress: (s) =>
      s.reviewItems.length > 0 || s.objects.length > 0 || s.ledger.length > 0
        ? "complete"
        : "available",
    whatHappens: (s) => {
      if (s.session.submitted.length > 0) {
        const n = s.session.submitted.length;
        return `You submitted ${n} ${plural(n, "source")}. The compiler turned it into candidate knowledge — not published truth.`;
      }
      if (s.reviewItems.length > 0 || s.objects.length > 0) {
        return "This brain was seeded with example context so you can walk the workflow. Submit your own to see the compiler run.";
      }
      return "Nothing has entered the brain yet. Submit some context to create the first candidate.";
    },
    count: (s) => (s.session.submitted.length ? { value: s.session.submitted.length, noun: "submitted" } : null),
    nextAction: (s) =>
      s.reviewItems.length === 0 && s.objects.length === 0
        ? { label: "Submit your first source", targetStepId: "submit" }
        : null
  },
  {
    id: "enrich",
    number: 2,
    label: "Enrich",
    verb: "Generate the AI review brief",
    category: "Assisted analysis",
    sectionId: "enrichment-lab",
    governanceMeaning: GOVERNANCE_MEANING.enrich,
    progress: (s) => {
      // Enrichment counts as witnessed if this viewer ran it, or if a decision
      // was taken on a candidate that carried a brief. Without the second
      // clause the step regresses from complete to locked the moment an
      // already-enriched queue drains, which reads as the page breaking.
      const witnessed =
        s.session.enriched.length > 0 || s.ledger.some((record) => record.hadAIBrief);
      if (s.reviewItems.length === 0 && !witnessed) return "locked";
      // A disabled provider has not done anything, so it can never read as done.
      if (s.aiStatus && s.aiStatus.enabled === false) return "available";
      if (witnessed) return "complete";
      if (s.reviewItems.length > 0 && unenrichedItems(s).length === 0) return "complete";
      return "available";
    },
    lockedReason: () => LOCKED_REASON.enrich,
    whatHappens: (s) => {
      if (s.aiStatus && s.aiStatus.enabled === false) {
        return "Enrichment is disabled by server configuration. Reviewers work from the source evidence alone — the workflow still runs.";
      }
      if (s.session.enriched.length > 0) {
        const n = s.session.enriched.length;
        return `You generated ${n} ${plural(n, "brief")}. Each one is advisory: it flags what to check, and decides nothing.`;
      }
      const approvedWithoutBrief = s.ledger.filter((record) => !record.hadAIBrief).length;
      if (approvedWithoutBrief > 0 && s.reviewItems.length === 0) {
        return `${approvedWithoutBrief} ${plural(approvedWithoutBrief, "decision")} were taken without an AI brief. That is permitted — the activity log records it.`;
      }
      const waiting = unenrichedItems(s).length;
      if (waiting > 0) {
        return `${waiting} ${plural(waiting, "candidate")} ${waiting === 1 ? "has" : "have"} no brief yet. Enrichment is optional — approving without one is allowed, and recorded.`;
      }
      return "Every candidate already carries a brief.";
    },
    count: (s) => {
      const waiting = unenrichedItems(s).length;
      return waiting ? { value: waiting, noun: "without a brief" } : null;
    },
    nextAction: (s) => {
      if (s.aiStatus && s.aiStatus.enabled === false) return null;
      const waiting = unenrichedItems(s);
      if (!waiting.length) return null;
      return {
        label: `Run enrichment on ${waiting[0].candidate_object.title}`,
        targetStepId: "enrich"
      };
    }
  },
  {
    id: "review",
    number: 3,
    label: "Review",
    verb: "Make the governed decision",
    category: "Human validation",
    sectionId: "review-queue",
    governanceMeaning: GOVERNANCE_MEANING.review,
    progress: (s) => {
      if (s.reviewItems.length === 0 && s.ledger.length === 0) return "locked";
      // Rejecting counts. The step's job is "a human decided", not "something
      // got published" — publication is step 4's job to represent.
      if (s.ledger.length > 0) return "complete";
      return "available";
    },
    lockedReason: () => LOCKED_REASON.review,
    whatHappens: (s) => {
      if (s.ledger.length === 0) {
        const n = pendingItems(s).length;
        return n > 0
          ? `${n} ${plural(n, "candidate")} waiting on a human. Nothing reaches an AI app until one of them is approved.`
          : "No decisions have been made yet.";
      }
      const approved = s.ledger.filter((r) => r.action === "approved").length;
      const rejected = s.ledger.filter((r) => r.action === "rejected").length;
      const changes = s.ledger.filter((r) => r.action === "changes_requested").length;
      const parts = [
        approved ? `${approved} approved` : null,
        rejected ? `${rejected} rejected` : null,
        changes ? `${changes} sent back` : null
      ].filter(Boolean);
      return `You made ${s.ledger.length} governed ${plural(s.ledger.length, "decision")} — ${parts.join(", ")}. Every one is recorded in the activity log.`;
    },
    count: (s) => {
      const n = pendingItems(s).length + changesRequestedItems(s).length;
      return n ? { value: n, noun: "to decide" } : null;
    },
    nextAction: (s) => {
      const next = pendingItems(s)[0];
      if (!next) return null;
      return { label: `Review ${next.candidate_object.title}`, targetStepId: "review" };
    }
  },
  {
    id: "publish",
    number: 4,
    label: "Publish",
    verb: "Inspect the approved brain",
    category: "Governed knowledge",
    sectionId: "published-objects",
    governanceMeaning: GOVERNANCE_MEANING.publish,
    progress: (s) => {
      const approvedInLedger = s.ledger.some((record) => record.action === "approved");
      if (s.objects.length === 0 && !approvedInLedger) return "locked";
      if (s.objects.length > 0) return "complete";
      return "available";
    },
    lockedReason: () => LOCKED_REASON.publish,
    whatHappens: (s) => {
      if (s.objects.length === 0) return "Nothing is published yet.";
      if (s.session.published.length > 0) {
        const n = s.session.published.length;
        return `You published ${n} ${plural(n, "object")}. ${plural(n, "It is", "They are")} now official context an AI app may draw on.`;
      }
      return `${s.objects.length} approved ${plural(s.objects.length, "object")} were seeded as examples. Approve a candidate to add your own.`;
    },
    count: (s) => (s.objects.length ? { value: s.objects.length, noun: "published" } : null),
    nextAction: () => null
  },
  {
    id: "compose",
    number: 5,
    label: "Compose",
    verb: "Compose a context pack",
    category: "Context runtime",
    sectionId: "context-pack",
    governanceMeaning: GOVERNANCE_MEANING.compose,
    progress: (s) => {
      if (s.objects.length === 0) return "locked";
      if (s.contextPack) return "complete";
      return "available";
    },
    // The one lock that teaches the rule rather than merely gating.
    lockedReason: () => LOCKED_REASON.compose,
    whatHappens: (s) => {
      if (!s.contextPack) {
        return s.objects.length === 0
          ? "There is no approved knowledge to compose from yet."
          : "Ask a question to see exactly what an AI app would receive.";
      }
      if (s.contextPack.access_decision === "denied") {
        return "Access was denied by policy. Matching context exists but sits above this user's clearance, so the pack withholds it rather than leaking it.";
      }
      const objectCount = s.contextPack.knowledge_objects.length;
      return objectCount === 0
        ? "The pack came back empty and says so. An honest gap beats a confident guess."
        : `The pack drew on ${objectCount} approved ${plural(objectCount, "object")} plus their source evidence. No unapproved content is reachable.`;
    },
    count: (s) => (s.session.packsBuilt ? { value: s.session.packsBuilt, noun: "composed" } : null),
    nextAction: (s) =>
      s.objects.length > 0 && !s.contextPack
        ? { label: "Compose a context pack", targetStepId: "compose" }
        : null
  }
];

export const stepById = (id: string) => STEPS.find((step) => step.id === id);
export const stepBySectionId = (sectionId: string) =>
  STEPS.find((step) => step.sectionId === sectionId);
