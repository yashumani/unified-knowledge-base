import { useEffect, useMemo, useState } from "react";
import { brainClient } from "../api/brainClient";
import { DEMO_ENRICHMENT_LATENCY_MS, DEMO_PACK_LATENCY_MS } from "../demo/config";
import { compileSubmission } from "../demo/offlineCompiler";
import { buildContextPack } from "../demo/offlineContextPack";
import { enrichSource } from "../demo/offlineEnrichment";
import {
  demoGraph,
  demoObjects,
  demoReviewItems,
  demoSources
} from "../data/demoBrain";
import { buildGraphFromState } from "../utils/graph";
import type { PipelineSnapshot, ReviewDecisionRecord, SessionActivity } from "../pipeline/types";
import type {
  AIProviderStatus,
  BrainGraph,
  ContextPack,
  ContextPackRequest,
  IngestionPayload,
  KnowledgeObject,
  ReviewItem,
  SourceEvidence
} from "../types";

export const REVIEWER = "ui.reviewer";

const EMPTY_GRAPH: BrainGraph = { nodes: [], edges: [], generated_at: "" };

const EMPTY_SESSION: SessionActivity = {
  submitted: [],
  enriched: [],
  published: [],
  packsBuilt: 0
};

/** What the browser-side offline provider reports about itself. */
export const demoAIStatus: AIProviderStatus = {
  provider: "noop",
  mode: "offline_no_model",
  enabled: true,
  model: "deterministic",
  embedding_model: null,
  base_url: null,
  hosted_allowed_for_restricted: false,
  local_only: true,
  capabilities: [
    "deterministic_classification",
    "deterministic_review_brief",
    "offline_context_pack"
  ]
};

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export function useBrainState() {
  const [environment, setEnvironment] = useState("unknown");
  const [demoMode, setDemoMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>([]);
  const [objects, setObjects] = useState<KnowledgeObject[]>([]);
  const [sources, setSources] = useState<SourceEvidence[]>([]);
  // Not seeded with fixtures. Seeding meant a connected console rendered
  // synthetic support-ops data before any fetch resolved.
  const [graph, setGraph] = useState<BrainGraph>(EMPTY_GRAPH);
  const [contextPack, setContextPack] = useState<ContextPack | null>(null);
  const [aiStatus, setAIStatus] = useState<AIProviderStatus | null>(null);
  const [ledger, setLedger] = useState<ReviewDecisionRecord[]>([]);
  const [session, setSession] = useState<SessionActivity>(EMPTY_SESSION);

  const record = (entry: ReviewDecisionRecord) => setLedger((current) => [entry, ...current]);

  const stats = useMemo(
    () => ({
      published: objects.length,
      review: reviewItems.length,
      graphNodes: graph.nodes.length,
      graphEdges: graph.edges.length,
      enrichedReviews: reviewItems.filter((item) => item.ai_enrichment).length
    }),
    [graph.edges.length, graph.nodes.length, objects.length, reviewItems]
  );

  function enterDemoMode(message: string | null) {
    setEnvironment("offline-demo");
    setReviewItems(demoReviewItems);
    setObjects(demoObjects);
    setSources(demoSources);
    setGraph(demoGraph);
    setAIStatus(demoAIStatus);
    setDemoMode(true);
    // The context pack is deliberately NOT seeded. It is the last step of the
    // walk, and pre-filling it would show step 5 as already done before the
    // viewer has composed anything.
    setContextPack(null);
    setError(message);
  }

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      // Health decides connected vs demo. Previously a single Promise.all
      // covered four endpoints, so one failing route made the console announce
      // "no backend connected" while showing fabricated data — the opposite of
      // what demo mode is supposed to signal.
      const health = await brainClient.health();

      const [reviews, publishedObjects, providerStatus, fetchedGraph] = await Promise.allSettled([
        brainClient.listReviewItems(),
        brainClient.listObjects(),
        brainClient.getAIProviderStatus(),
        brainClient.getGraph()
      ]);

      const nextReviews = reviews.status === "fulfilled" ? reviews.value : [];
      const nextObjects = publishedObjects.status === "fulfilled" ? publishedObjects.value : [];

      setEnvironment(health.environment);
      setReviewItems(nextReviews);
      setObjects(nextObjects);
      setGraph(
        fetchedGraph.status === "fulfilled"
          ? fetchedGraph.value
          : buildGraphFromState(nextObjects, nextReviews)
      );
      if (providerStatus.status === "fulfilled") setAIStatus(providerStatus.value);
      setDemoMode(false);

      // A partial failure is reported as a partial failure, not as demo mode.
      const failed = [
        reviews.status === "rejected" ? "review queue" : null,
        publishedObjects.status === "rejected" ? "published objects" : null,
        providerStatus.status === "rejected" ? "AI provider status" : null
      ].filter(Boolean);
      setError(
        failed.length
          ? `Connected, but these could not be loaded: ${failed.join(", ")}.`
          : null
      );
    } catch (caught) {
      enterDemoMode(
        caught instanceof Error
          ? `${caught.message} — showing the built-in demo brain.`
          : "Could not reach the API. Showing the built-in demo brain."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Clear everything this viewer did and reseed, without losing their place. */
  function restartDemo() {
    setReviewItems(demoReviewItems);
    setObjects(demoObjects);
    setSources(demoSources);
    setGraph(demoGraph);
    setContextPack(null);
    setLedger([]);
    setSession(EMPTY_SESSION);
  }

  async function submitContext(payload: IngestionPayload) {
    if (demoMode) {
      // Runs the same heuristics as ukb.services.compiler rather than guessing.
      const { source, reviewItem } = compileSubmission(payload);
      const nextReviews = [reviewItem, ...reviewItems];
      setSources((current) => [source, ...current]);
      setReviewItems(nextReviews);
      setGraph(buildGraphFromState(objects, nextReviews));
      setSession((s) => ({ ...s, submitted: [...s.submitted, payload.title] }));
      return;
    }

    await brainClient.submitContext(payload);
    setSession((s) => ({ ...s, submitted: [...s.submitted, payload.title] }));
    await refresh();
  }

  async function enrichReview(reviewItemId: string) {
    if (demoMode) {
      const item = reviewItems.find((review) => review.id === reviewItemId);
      if (!item) return;
      const source =
        sources.find((candidate) => candidate.source_id === item.source_id) ?? sources[0];
      if (!source) return;

      await wait(DEMO_ENRICHMENT_LATENCY_MS);
      const enrichment = enrichSource({
        source,
        content: String(item.candidate_object.attributes?.raw_excerpt ?? source.content_excerpt),
        candidate: item.candidate_object
      });
      const nextReviews = reviewItems.map((review) =>
        review.id === reviewItemId ? { ...review, ai_enrichment: enrichment } : review
      );
      setReviewItems(nextReviews);
      setGraph(buildGraphFromState(objects, nextReviews));
      setSession((s) => ({ ...s, enriched: [...s.enriched, reviewItemId] }));
      return;
    }

    await brainClient.enrichReviewItem(reviewItemId);
    setSession((s) => ({ ...s, enriched: [...s.enriched, reviewItemId] }));
    await refresh();
  }

  function decisionRecord(
    item: ReviewItem,
    action: ReviewDecisionRecord["action"],
    comment: string | null
  ): ReviewDecisionRecord {
    return {
      reviewItemId: item.id,
      candidateTitle: item.candidate_object.title,
      action,
      reviewer: REVIEWER,
      comment,
      at: new Date().toISOString(),
      hadAIBrief: Boolean(item.ai_enrichment)
    };
  }

  async function approveReview(reviewItemId: string, comment: string | null = null) {
    const item = reviewItems.find((review) => review.id === reviewItemId);
    if (!item) return;
    const entry = decisionRecord(item, "approved", comment);

    if (demoMode) {
      const approvedObject: KnowledgeObject = {
        ...item.candidate_object,
        status: "published",
        updated_at: new Date().toISOString()
      };
      const nextObjects = [approvedObject, ...objects];
      const nextReviews = reviewItems.filter((review) => review.id !== reviewItemId);
      setObjects(nextObjects);
      setReviewItems(nextReviews);
      setGraph(buildGraphFromState(nextObjects, nextReviews));
      record(entry);
      setSession((s) => ({ ...s, published: [...s.published, item.candidate_object.title] }));
      return;
    }

    await brainClient.approveReviewItem(reviewItemId, {
      reviewed_by: REVIEWER,
      comment: comment ?? "Approved from the React console."
    });
    record(entry);
    setSession((s) => ({ ...s, published: [...s.published, item.candidate_object.title] }));
    await refresh();
  }

  async function rejectReview(reviewItemId: string, comment: string | null = null) {
    const item = reviewItems.find((review) => review.id === reviewItemId);
    if (!item) return;
    const entry = decisionRecord(item, "rejected", comment);

    if (demoMode) {
      const nextReviews = reviewItems.filter((review) => review.id !== reviewItemId);
      setReviewItems(nextReviews);
      setGraph(buildGraphFromState(objects, nextReviews));
      record(entry);
      return;
    }

    await brainClient.rejectReviewItem(reviewItemId, {
      reviewed_by: REVIEWER,
      comment: comment ?? "Rejected from the React console."
    });
    record(entry);
    await refresh();
  }

  /**
   * Send a candidate back for rework. Implemented in the backend, typed in the
   * client, recommended by the enrichment brief itself — and until now the UI
   * was the only layer that could not do it.
   */
  async function requestChanges(reviewItemId: string, comment: string | null = null) {
    const item = reviewItems.find((review) => review.id === reviewItemId);
    if (!item) return;
    const entry = decisionRecord(item, "changes_requested", comment);

    if (demoMode) {
      // The item stays in the queue; only its state changes.
      const nextReviews = reviewItems.map((review) =>
        review.id === reviewItemId
          ? {
              ...review,
              status: "changes_requested" as const,
              reviewer: REVIEWER,
              review_comment: comment,
              updated_at: new Date().toISOString(),
              candidate_object: {
                ...review.candidate_object,
                status: "changes_requested" as const
              }
            }
          : review
      );
      setReviewItems(nextReviews);
      setGraph(buildGraphFromState(objects, nextReviews));
      record(entry);
      return;
    }

    await brainClient.requestChanges(reviewItemId, {
      reviewed_by: REVIEWER,
      comment: comment ?? "Changes requested from the React console."
    });
    record(entry);
    await refresh();
  }

  async function askBrain(request: ContextPackRequest) {
    if (demoMode) {
      await wait(DEMO_PACK_LATENCY_MS);
      setContextPack(buildContextPack({ request, objects, sources }));
      setSession((s) => ({ ...s, packsBuilt: s.packsBuilt + 1 }));
      return;
    }
    setContextPack(await brainClient.buildContextPack(request));
    setSession((s) => ({ ...s, packsBuilt: s.packsBuilt + 1 }));
  }

  const resolvedAIStatus = aiStatus ?? demoAIStatus;

  const snapshot: PipelineSnapshot = {
    reviewItems,
    objects,
    contextPack,
    aiStatus,
    demoMode,
    ledger,
    session
  };

  return {
    snapshot,
    ledger,
    session,
    environment,
    demoMode,
    loading,
    error,
    reviewItems,
    objects,
    graph,
    contextPack,
    aiStatus: resolvedAIStatus,
    aiStatusLoaded: aiStatus !== null,
    stats,
    refresh,
    restartDemo,
    submitContext,
    approveReview,
    rejectReview,
    requestChanges,
    enrichReview,
    askBrain
  };
}
