import { useEffect, useMemo, useState } from "react";
import { brainClient } from "../api/brainClient";
import { demoContextPack, demoGraph, demoObjects, demoReviewItems } from "../data/demoBrain";
import { buildGraphFromState } from "../utils/graph";
import type {
  PipelineSnapshot,
  ReviewDecisionRecord,
  SessionActivity
} from "../pipeline/types";
import type {
  AIProviderStatus,
  BrainGraph,
  ContextPack,
  ContextPackRequest,
  IngestionPayload,
  KnowledgeObject,
  ReviewItem
} from "../types";

const EMPTY_SESSION: SessionActivity = {
  submitted: [],
  enriched: [],
  published: [],
  packsBuilt: 0
};

export const REVIEWER = "ui.reviewer";

export const demoAIStatus: AIProviderStatus = {
  provider: "noop",
  mode: "offline_no_model",
  enabled: true,
  model: "deterministic",
  embedding_model: "embeddinggemma",
  base_url: null,
  hosted_allowed_for_restricted: false
};

/** Owns every piece of console state plus the connected/demo handler pairs. */
export function useBrainState() {
  const [environment, setEnvironment] = useState("unknown");
  const [demoMode, setDemoMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>([]);
  const [objects, setObjects] = useState<KnowledgeObject[]>([]);
  const [graph, setGraph] = useState<BrainGraph>(demoGraph);
  const [contextPack, setContextPack] = useState<ContextPack | null>(null);
  const [aiStatus, setAIStatus] = useState<AIProviderStatus>(demoAIStatus);
  // Append-only record of governed decisions. The review handlers drop items
  // from the queue once decided, so without this a rejection would leave no
  // trace that anything happened at all.
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

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [health, reviews, publishedObjects, providerStatus] = await Promise.all([
        brainClient.health(),
        brainClient.listReviewItems(),
        brainClient.listObjects(),
        brainClient.getAIProviderStatus()
      ]);
      const nextGraph = await brainClient
        .getGraph()
        .catch(() => buildGraphFromState(publishedObjects, reviews));
      setEnvironment(health.environment);
      setReviewItems(reviews);
      setObjects(publishedObjects);
      setGraph(nextGraph);
      setAIStatus(providerStatus);
      setDemoMode(false);
    } catch (caught) {
      setEnvironment("offline-demo");
      setReviewItems(demoReviewItems);
      setObjects(demoObjects);
      setGraph(demoGraph);
      setContextPack(demoContextPack);
      setAIStatus(demoAIStatus);
      setDemoMode(true);
      setError(
        caught instanceof Error ? caught.message : "Could not reach API. Using built-in demo data."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submitContext(payload: IngestionPayload) {
    if (demoMode) {
      const id = `review_ui_${Date.now()}`;
      const candidate: KnowledgeObject = {
        id: `candidate.${payload.domain}.${payload.title.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`,
        type: payload.content.toLowerCase().includes("dashboard") ? "Report" : "Metric",
        title: payload.title,
        summary: payload.content.slice(0, 240),
        domain: payload.domain,
        owner: payload.content.match(/owned by ([A-Za-z0-9 _&-]+)/i)?.[1] ?? null,
        status: "human_review_required",
        sensitivity: payload.sensitivity,
        source_ids: [`source_ui_${Date.now()}`],
        relationships: [],
        attributes: { tags: payload.tags, demo_mode: true },
        confidence: 0.67,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      const nextReviews: ReviewItem[] = [
        {
          id,
          source_id: candidate.source_ids[0],
          candidate_object: candidate,
          status: "human_review_required",
          reviewer: null,
          review_comment: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        ...reviewItems
      ];
      setReviewItems(nextReviews);
      setGraph(buildGraphFromState(objects, nextReviews));
      setSession((s) => ({ ...s, submitted: [...s.submitted, payload.title] }));
      return;
    }

    await brainClient.submitContext(payload);
    setSession((s) => ({ ...s, submitted: [...s.submitted, payload.title] }));
    await refresh();
  }

  async function approveReview(reviewItemId: string) {
    const item = reviewItems.find((review) => review.id === reviewItemId);
    if (!item) return;
    const entry: ReviewDecisionRecord = {
      reviewItemId,
      candidateTitle: item.candidate_object.title,
      action: "approved",
      reviewer: REVIEWER,
      comment: null,
      at: new Date().toISOString(),
      hadAIBrief: Boolean(item.ai_enrichment)
    };

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
      comment: "Approved from React console."
    });
    record(entry);
    setSession((s) => ({ ...s, published: [...s.published, item.candidate_object.title] }));
    await refresh();
  }

  async function rejectReview(reviewItemId: string) {
    const item = reviewItems.find((review) => review.id === reviewItemId);
    if (!item) return;
    const entry: ReviewDecisionRecord = {
      reviewItemId,
      candidateTitle: item.candidate_object.title,
      action: "rejected",
      reviewer: REVIEWER,
      comment: null,
      at: new Date().toISOString(),
      hadAIBrief: Boolean(item.ai_enrichment)
    };

    if (demoMode) {
      const nextReviews = reviewItems.filter((review) => review.id !== reviewItemId);
      setReviewItems(nextReviews);
      setGraph(buildGraphFromState(objects, nextReviews));
      record(entry);
      return;
    }

    await brainClient.rejectReviewItem(reviewItemId, {
      reviewed_by: REVIEWER,
      comment: "Rejected from React console."
    });
    record(entry);
    await refresh();
  }

  async function enrichReview(reviewItemId: string) {
    if (demoMode) return;
    await brainClient.enrichReviewItem(reviewItemId);
    setSession((s) => ({ ...s, enriched: [...s.enriched, reviewItemId] }));
    await refresh();
  }

  async function askBrain(request: ContextPackRequest) {
    if (demoMode) {
      setContextPack({
        ...demoContextPack,
        question: request.question,
        user_id: request.user_id,
        mode: request.mode,
        generated_at: new Date().toISOString()
      });
      setSession((s) => ({ ...s, packsBuilt: s.packsBuilt + 1 }));
      return;
    }
    setContextPack(await brainClient.buildContextPack(request));
    setSession((s) => ({ ...s, packsBuilt: s.packsBuilt + 1 }));
  }

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
    aiStatus,
    stats,
    refresh,
    submitContext,
    approveReview,
    rejectReview,
    enrichReview,
    askBrain
  };
}
