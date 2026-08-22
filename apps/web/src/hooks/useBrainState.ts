import { useEffect, useMemo, useState } from "react";
import { brainClient } from "../api/brainClient";
import { DEMO_ENRICHMENT_LATENCY_MS, DEMO_PACK_LATENCY_MS } from "../demo/config";
import { compileSubmission } from "../demo/offlineCompiler";
import { buildContextPack } from "../demo/offlineContextPack";
import { enrichSource } from "../demo/offlineEnrichment";
import { demoGraph, demoObjects, demoReviewItems, demoSources } from "../data/demoBrain";
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
  ReviewRevisionRequest,
  SourceEvidence
} from "../types";

export const REVIEWER = "ui.reviewer";
export const PUBLISHER = "ui.publisher";

const EMPTY_GRAPH: BrainGraph = { nodes: [], edges: [], generated_at: "" };
const EMPTY_SESSION: SessionActivity = {
  submitted: [],
  enriched: [],
  approved: [],
  published: [],
  packsBuilt: 0
};

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
  const [approvedItems, setApprovedItems] = useState<ReviewItem[]>([]);
  const [objects, setObjects] = useState<KnowledgeObject[]>([]);
  const [sources, setSources] = useState<SourceEvidence[]>([]);
  const [graph, setGraph] = useState<BrainGraph>(EMPTY_GRAPH);
  const [contextPack, setContextPack] = useState<ContextPack | null>(null);
  const [aiStatus, setAIStatus] = useState<AIProviderStatus | null>(null);
  const [ledger, setLedger] = useState<ReviewDecisionRecord[]>([]);
  const [session, setSession] = useState<SessionActivity>(EMPTY_SESSION);

  const record = (entry: ReviewDecisionRecord) => setLedger((current) => [entry, ...current]);

  const stats = useMemo(
    () => ({
      published: objects.length,
      approved: approvedItems.length,
      review: reviewItems.length,
      graphNodes: graph.nodes.length,
      graphEdges: graph.edges.length,
      enrichedReviews: [...reviewItems, ...approvedItems].filter((item) => item.ai_enrichment).length
    }),
    [approvedItems, graph.edges.length, graph.nodes.length, objects.length, reviewItems]
  );

  function enterDemoMode(message: string | null) {
    setEnvironment("offline-demo");
    setReviewItems(demoReviewItems.map((item) => ({ ...item, revision: item.revision ?? 1 })));
    setApprovedItems([]);
    setObjects(demoObjects);
    setSources(demoSources);
    setGraph(demoGraph);
    setAIStatus(demoAIStatus);
    setDemoMode(true);
    setContextPack(null);
    setError(message);
  }

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const health = await brainClient.health();
      const [reviews, approved, publishedObjects, providerStatus, fetchedGraph, fetchedSources] =
        await Promise.allSettled([
          brainClient.listReviewItems(),
          brainClient.listApprovedReviews(),
          brainClient.listObjects(),
          brainClient.getAIProviderStatus(),
          brainClient.getGraph(),
          brainClient.listSources()
        ]);

      const nextReviews = reviews.status === "fulfilled" ? reviews.value : [];
      const nextApproved = approved.status === "fulfilled" ? approved.value : [];
      const nextObjects = publishedObjects.status === "fulfilled" ? publishedObjects.value : [];
      setEnvironment(health.environment);
      setReviewItems(nextReviews);
      setApprovedItems(nextApproved);
      setObjects(nextObjects);
      setSources(fetchedSources.status === "fulfilled" ? fetchedSources.value : []);
      setGraph(
        fetchedGraph.status === "fulfilled"
          ? fetchedGraph.value
          : buildGraphFromState(nextObjects, [...nextReviews, ...nextApproved])
      );
      if (providerStatus.status === "fulfilled") setAIStatus(providerStatus.value);
      setDemoMode(false);

      const failed = [
        reviews.status === "rejected" ? "review queue" : null,
        approved.status === "rejected" ? "publication queue" : null,
        publishedObjects.status === "rejected" ? "published objects" : null,
        providerStatus.status === "rejected" ? "AI provider status" : null,
        fetchedSources.status === "rejected" ? "source evidence" : null
      ].filter(Boolean);
      setError(failed.length ? `Connected, but these could not be loaded: ${failed.join(", ")}.` : null);
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

  function restartDemo() {
    setReviewItems(demoReviewItems.map((item) => ({ ...item, revision: item.revision ?? 1 })));
    setApprovedItems([]);
    setObjects(demoObjects);
    setSources(demoSources);
    setGraph(demoGraph);
    setContextPack(null);
    setLedger([]);
    setSession(EMPTY_SESSION);
  }

  async function submitContext(payload: IngestionPayload) {
    if (demoMode) {
      const { source, reviewItem } = compileSubmission(payload);
      const nextItem = { ...reviewItem, revision: 1 };
      const nextReviews = [nextItem, ...reviewItems];
      setSources((current) => [source, ...current]);
      setReviewItems(nextReviews);
      setGraph(buildGraphFromState(objects, [...nextReviews, ...approvedItems]));
      setSession((current) => ({ ...current, submitted: [...current.submitted, payload.title] }));
      return;
    }
    await brainClient.submitContext(payload);
    setSession((current) => ({ ...current, submitted: [...current.submitted, payload.title] }));
    await refresh();
  }

  async function enrichReview(reviewItemId: string) {
    if (demoMode) {
      const item = reviewItems.find((review) => review.id === reviewItemId);
      if (!item) return;
      const source = sources.find((candidate) => candidate.source_id === item.source_id) ?? sources[0];
      if (!source) return;
      await wait(DEMO_ENRICHMENT_LATENCY_MS);
      const enrichment = enrichSource({
        source,
        content: String(item.candidate_object.attributes?.raw_excerpt ?? source.content_excerpt),
        candidate: item.candidate_object
      });
      const nextReviews = reviewItems.map((review) =>
        review.id === reviewItemId
          ? {
              ...review,
              ai_enrichment: enrichment,
              revision: (review.revision ?? 1) + 1,
              updated_at: new Date().toISOString()
            }
          : review
      );
      setReviewItems(nextReviews);
      setGraph(buildGraphFromState(objects, [...nextReviews, ...approvedItems]));
      setSession((current) => ({ ...current, enriched: [...current.enriched, reviewItemId] }));
      return;
    }
    await brainClient.enrichReviewItem(reviewItemId);
    setSession((current) => ({ ...current, enriched: [...current.enriched, reviewItemId] }));
    await refresh();
  }

  function decisionRecord(
    item: ReviewItem,
    action: ReviewDecisionRecord["action"],
    comment: string | null,
    actor = REVIEWER
  ): ReviewDecisionRecord {
    return {
      reviewItemId: item.id,
      candidateTitle: item.candidate_object.title,
      action,
      reviewer: actor,
      comment,
      at: new Date().toISOString(),
      hadAIBrief: Boolean(item.ai_enrichment)
    };
  }

  async function approveReview(reviewItemId: string, comment: string | null = null) {
    const item = reviewItems.find((review) => review.id === reviewItemId);
    if (!item) return;
    if (demoMode) {
      const approved: ReviewItem = {
        ...item,
        status: "approved",
        revision: (item.revision ?? 1) + 1,
        reviewer: REVIEWER,
        approved_by: REVIEWER,
        approved_at: new Date().toISOString(),
        review_comment: comment,
        updated_at: new Date().toISOString(),
        candidate_object: { ...item.candidate_object, status: "approved" }
      };
      const nextReviews = reviewItems.filter((review) => review.id !== reviewItemId);
      const nextApproved = [approved, ...approvedItems];
      setReviewItems(nextReviews);
      setApprovedItems(nextApproved);
      setGraph(buildGraphFromState(objects, [...nextReviews, ...nextApproved]));
      record(decisionRecord(item, "approved", comment));
      setSession((current) => ({ ...current, approved: [...current.approved, item.candidate_object.title] }));
      return;
    }
    await brainClient.approveReviewItem(reviewItemId, {
      comment: comment ?? "Approved from the React console.",
      expected_revision: item.revision ?? 1
    });
    record(decisionRecord(item, "approved", comment));
    setSession((current) => ({ ...current, approved: [...current.approved, item.candidate_object.title] }));
    await refresh();
  }

  async function publishReview(reviewItemId: string, comment: string | null = null) {
    const item = approvedItems.find((review) => review.id === reviewItemId);
    if (!item) return;
    if (demoMode) {
      const publishedObject: KnowledgeObject = {
        ...item.candidate_object,
        status: "published",
        published_by: PUBLISHER,
        published_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      const nextObjects = [publishedObject, ...objects];
      const nextApproved = approvedItems.filter((review) => review.id !== reviewItemId);
      setObjects(nextObjects);
      setApprovedItems(nextApproved);
      setGraph(buildGraphFromState(nextObjects, [...reviewItems, ...nextApproved]));
      record(decisionRecord(item, "published", comment, PUBLISHER));
      setSession((current) => ({ ...current, published: [...current.published, item.candidate_object.title] }));
      return;
    }
    await brainClient.publishReviewItem(reviewItemId, {
      comment: comment ?? "Published from the React console.",
      expected_revision: item.revision ?? 1
    });
    record(decisionRecord(item, "published", comment, PUBLISHER));
    setSession((current) => ({ ...current, published: [...current.published, item.candidate_object.title] }));
    await refresh();
  }

  async function approveAndPublishReview(reviewItemId: string, comment: string | null = null) {
    const item = reviewItems.find((review) => review.id === reviewItemId);
    if (!item) return;
    if (demoMode) {
      const approved: ReviewItem = {
        ...item,
        status: "approved",
        revision: (item.revision ?? 1) + 1,
        candidate_object: { ...item.candidate_object, status: "approved" }
      };
      const publishedObject: KnowledgeObject = {
        ...approved.candidate_object,
        status: "published",
        published_by: PUBLISHER,
        published_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      const nextReviews = reviewItems.filter((review) => review.id !== reviewItemId);
      const nextObjects = [publishedObject, ...objects];
      setReviewItems(nextReviews);
      setObjects(nextObjects);
      setGraph(buildGraphFromState(nextObjects, [...nextReviews, ...approvedItems]));
      record(decisionRecord(item, "approved", comment));
      record(decisionRecord(approved, "published", comment, PUBLISHER));
      setSession((current) => ({
        ...current,
        approved: [...current.approved, item.candidate_object.title],
        published: [...current.published, item.candidate_object.title]
      }));
      return;
    }
    const approved = await brainClient.approveReviewItem(reviewItemId, {
      comment: comment ?? "Approved from the guided demo.",
      expected_revision: item.revision ?? 1
    });
    await brainClient.publishReviewItem(reviewItemId, {
      comment: comment ?? "Published from the guided demo.",
      expected_revision: approved.revision ?? (item.revision ?? 1) + 1
    });
    record(decisionRecord(item, "approved", comment));
    record(decisionRecord(approved, "published", comment, PUBLISHER));
    setSession((current) => ({
      ...current,
      approved: [...current.approved, item.candidate_object.title],
      published: [...current.published, item.candidate_object.title]
    }));
    await refresh();
  }

  async function rejectReview(reviewItemId: string, comment: string | null = null) {
    const item = reviewItems.find((review) => review.id === reviewItemId);
    if (!item) return;
    if (demoMode) {
      const nextReviews = reviewItems.filter((review) => review.id !== reviewItemId);
      setReviewItems(nextReviews);
      setGraph(buildGraphFromState(objects, [...nextReviews, ...approvedItems]));
      record(decisionRecord(item, "rejected", comment));
      return;
    }
    await brainClient.rejectReviewItem(reviewItemId, {
      comment: comment ?? "Rejected from the React console.",
      expected_revision: item.revision ?? 1
    });
    record(decisionRecord(item, "rejected", comment));
    await refresh();
  }

  async function requestChanges(reviewItemId: string, comment: string | null = null) {
    const item = reviewItems.find((review) => review.id === reviewItemId);
    if (!item) return;
    if (demoMode) {
      const nextReviews = reviewItems.map((review) =>
        review.id === reviewItemId
          ? {
              ...review,
              status: "changes_requested" as const,
              revision: (review.revision ?? 1) + 1,
              reviewer: REVIEWER,
              review_comment: comment,
              updated_at: new Date().toISOString(),
              candidate_object: { ...review.candidate_object, status: "changes_requested" as const }
            }
          : review
      );
      setReviewItems(nextReviews);
      setGraph(buildGraphFromState(objects, [...nextReviews, ...approvedItems]));
      record(decisionRecord(item, "changes_requested", comment));
      return;
    }
    await brainClient.requestChanges(reviewItemId, {
      comment: comment ?? "Changes requested from the React console.",
      expected_revision: item.revision ?? 1
    });
    record(decisionRecord(item, "changes_requested", comment));
    await refresh();
  }

  async function reviseReview(reviewItemId: string, request: ReviewRevisionRequest) {
    if (demoMode) return;
    await brainClient.reviseReviewItem(reviewItemId, request);
    await refresh();
  }

  async function askBrain(request: ContextPackRequest) {
    if (demoMode) {
      await wait(DEMO_PACK_LATENCY_MS);
      setContextPack(buildContextPack({ request, objects, sources }));
      setSession((current) => ({ ...current, packsBuilt: current.packsBuilt + 1 }));
      return;
    }
    setContextPack(await brainClient.buildContextPack(request));
    setSession((current) => ({ ...current, packsBuilt: current.packsBuilt + 1 }));
  }

  const resolvedAIStatus = aiStatus ?? demoAIStatus;
  const snapshot: PipelineSnapshot = {
    reviewItems,
    approvedItems,
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
    approvedItems,
    objects,
    sources,
    graph,
    contextPack,
    aiStatus: resolvedAIStatus,
    aiStatusLoaded: aiStatus !== null,
    stats,
    refresh,
    restartDemo,
    submitContext,
    approveReview,
    publishReview,
    approveAndPublishReview,
    rejectReview,
    requestChanges,
    reviseReview,
    enrichReview,
    askBrain
  };
}
