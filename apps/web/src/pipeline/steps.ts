import { GOVERNANCE_MEANING, LOCKED_REASON } from "./copy";
import type { PipelineSnapshot, StepDefinition } from "./types";

export const pendingItems = (s: PipelineSnapshot) =>
  s.reviewItems.filter((item) => item.status === "human_review_required");
export const changesRequestedItems = (s: PipelineSnapshot) =>
  s.reviewItems.filter((item) => item.status === "changes_requested");
export const allCandidates = (s: PipelineSnapshot) => [...s.reviewItems, ...s.approvedItems];
export const unenrichedItems = (s: PipelineSnapshot) =>
  allCandidates(s).filter((item) => !item.ai_enrichment);

const plural = (n: number, one: string, many = `${one}s`) => (n === 1 ? one : many);

export const STEPS: readonly StepDefinition[] = [
  {
    id: "submit",
    number: 1,
    label: "Submit",
    verb: "Submit source context",
    category: "Context ingestion",
    sectionId: "context-ingestion",
    governanceMeaning: GOVERNANCE_MEANING.submit,
    progress: (s) =>
      allCandidates(s).length > 0 || s.objects.length > 0 || s.ledger.length > 0
        ? "complete"
        : "available",
    whatHappens: (s) => {
      if (s.session.submitted.length > 0) {
        const n = s.session.submitted.length;
        return `You submitted ${n} ${plural(n, "source")}. The compiler created candidate knowledge and preserved evidence — not published truth.`;
      }
      if (allCandidates(s).length > 0 || s.objects.length > 0) {
        return "This brain contains example context. Submit your own to see evidence versioning and compilation run.";
      }
      return "Nothing has entered the brain yet. Submit source evidence to create the first candidate.";
    },
    count: (s) => (s.session.submitted.length ? { value: s.session.submitted.length, noun: "submitted" } : null),
    nextAction: (s) =>
      allCandidates(s).length === 0 && s.objects.length === 0
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
      const witnessed =
        s.session.enriched.length > 0 || s.ledger.some((record) => record.hadAIBrief);
      if (allCandidates(s).length === 0 && !witnessed) return "locked";
      if (s.aiStatus && s.aiStatus.enabled === false) return "available";
      if (witnessed || (allCandidates(s).length > 0 && unenrichedItems(s).length === 0)) {
        return "complete";
      }
      return "available";
    },
    lockedReason: () => LOCKED_REASON.enrich,
    whatHappens: (s) => {
      if (s.aiStatus && s.aiStatus.enabled === false) {
        return "AI enrichment is disabled. Reviewers continue from deterministic parsing and source evidence.";
      }
      if (s.session.enriched.length > 0) {
        const n = s.session.enriched.length;
        return `You generated ${n} advisory ${plural(n, "brief")}. Each one is schema-validated and decides nothing.`;
      }
      const waiting = unenrichedItems(s).length;
      return waiting
        ? `${waiting} ${plural(waiting, "candidate")} ${waiting === 1 ? "has" : "have"} no AI brief yet.`
        : "Every current candidate carries a review brief.";
    },
    count: (s) => {
      const waiting = unenrichedItems(s).length;
      return waiting ? { value: waiting, noun: "without a brief" } : null;
    },
    nextAction: (s) => {
      if (s.aiStatus && s.aiStatus.enabled === false) return null;
      const waiting = unenrichedItems(s);
      return waiting.length
        ? { label: `Run enrichment on ${waiting[0].candidate_object.title}`, targetStepId: "enrich" }
        : null;
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
      if (s.reviewItems.length === 0 && s.approvedItems.length === 0 && s.ledger.length === 0) return "locked";
      if (s.approvedItems.length > 0 || s.ledger.some((record) => record.action === "approved")) return "complete";
      return "available";
    },
    lockedReason: () => LOCKED_REASON.review,
    whatHappens: (s) => {
      if (s.ledger.length === 0) {
        const n = pendingItems(s).length;
        return n > 0
          ? `${n} ${plural(n, "candidate")} waiting on a human. Approval moves it to a separate publication queue.`
          : "No human decision has been made yet.";
      }
      const approved = s.ledger.filter((record) => record.action === "approved").length;
      const rejected = s.ledger.filter((record) => record.action === "rejected").length;
      const changes = s.ledger.filter((record) => record.action === "changes_requested").length;
      const parts = [
        approved ? `${approved} approved` : null,
        rejected ? `${rejected} rejected` : null,
        changes ? `${changes} sent back` : null
      ].filter(Boolean);
      return `Human decisions recorded: ${parts.join(", ") || "none"}. Approval alone does not publish.`;
    },
    count: (s) => {
      const n = pendingItems(s).length + changesRequestedItems(s).length;
      return n ? { value: n, noun: "to decide" } : null;
    },
    nextAction: (s) => {
      const next = pendingItems(s)[0];
      return next ? { label: `Review ${next.candidate_object.title}`, targetStepId: "review" } : null;
    }
  },
  {
    id: "publish",
    number: 4,
    label: "Publish",
    verb: "Publish approved memory",
    category: "Governed knowledge",
    sectionId: "published-objects",
    governanceMeaning: GOVERNANCE_MEANING.publish,
    progress: (s) => {
      if (s.objects.length > 0 || s.session.published.length > 0) return "complete";
      if (s.approvedItems.length > 0) return "available";
      return "locked";
    },
    lockedReason: () => LOCKED_REASON.publish,
    whatHappens: (s) => {
      if (s.approvedItems.length > 0) {
        return `${s.approvedItems.length} approved ${plural(s.approvedItems.length, "candidate")} await an explicit publication decision.`;
      }
      if (s.session.published.length > 0) {
        const n = s.session.published.length;
        return `You published ${n} ${plural(n, "object")}. ${plural(n, "It is", "They are")} now eligible for governed retrieval.`;
      }
      return s.objects.length
        ? `${s.objects.length} published ${plural(s.objects.length, "object")} are available to retrieval.`
        : "Nothing is published yet.";
    },
    count: (s) =>
      s.approvedItems.length
        ? { value: s.approvedItems.length, noun: "awaiting publication" }
        : s.objects.length
          ? { value: s.objects.length, noun: "published" }
          : null,
    nextAction: (s) =>
      s.approvedItems.length
        ? { label: `Publish ${s.approvedItems[0].candidate_object.title}`, targetStepId: "publish" }
        : null
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
      return s.contextPack ? "complete" : "available";
    },
    lockedReason: () => LOCKED_REASON.compose,
    whatHappens: (s) => {
      if (!s.contextPack) {
        return s.objects.length === 0
          ? "There is no published knowledge to retrieve yet."
          : "Ask a question to inspect the exact context, citations, confidence factors, and constraints an AI receives.";
      }
      if (s.contextPack.access_decision === "denied") {
        return "Access policy withheld every matching object. The pack refuses to speculate."
      }
      const count = s.contextPack.knowledge_objects.length;
      return count
        ? `The pack used ${count} published ${plural(count, "object")}, ${s.contextPack.citations?.length ?? 0} citation(s), and the ${s.contextPack.retrieval_engine ?? "configured"} retrieval engine.`
        : "The pack reports an evidence gap rather than inventing an answer.";
    },
    count: (s) => (s.session.packsBuilt ? { value: s.session.packsBuilt, noun: "composed" } : null),
    nextAction: (s) =>
      s.objects.length > 0 && !s.contextPack
        ? { label: "Compose a context pack", targetStepId: "compose" }
        : null
  }
];

export const stepById = (id: string) => STEPS.find((step) => step.id === id);
export const stepBySectionId = (sectionId: string) => STEPS.find((step) => step.sectionId === sectionId);
