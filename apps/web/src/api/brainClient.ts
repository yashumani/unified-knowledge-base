import type {
  AIEnrichmentResult,
  AIProviderHealth,
  AIProviderStatus,
  AuditEvent,
  BrainGraph,
  ContextPack,
  ContextPackRequest,
  EmbeddingRequest,
  EmbeddingResponse,
  IngestionPayload,
  KnowledgeObject,
  ReviewDecision,
  ReviewItem
} from "../types";

const configuredApiBase = import.meta.env.VITE_UKB_API_BASE_URL;
export const API_BASE = configuredApiBase && configuredApiBase.trim().length > 0
  ? configuredApiBase.replace(/\/$/, "")
  : "http://localhost:8000";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }

  return response.json() as Promise<T>;
}

export const brainClient = {
  health: () => request<{ status: string; environment: string }>("/health"),
  getAIProviderStatus: () => request<AIProviderStatus>("/ai/providers"),
  getAIProviderHealth: () => request<AIProviderHealth>("/ai/health"),
  buildEmbeddings: (payload: EmbeddingRequest) =>
    request<EmbeddingResponse>("/ai/embeddings", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  submitContext: (payload: IngestionPayload) =>
    request<ReviewItem>("/ingestion/submissions", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  listReviewItems: () => request<ReviewItem[]>("/review/queue"),
  enrichReviewItem: (reviewItemId: string) =>
    request<ReviewItem>(`/review/items/${reviewItemId}/enrich`, {
      method: "POST"
    }),
  getReviewItemAIEnrichment: (reviewItemId: string) =>
    request<AIEnrichmentResult>(`/review/items/${reviewItemId}/ai-enrichment`),
  approveReviewItem: (reviewItemId: string, decision: ReviewDecision) =>
    request<ReviewItem>(`/review/items/${reviewItemId}/approve`, {
      method: "POST",
      body: JSON.stringify(decision)
    }),
  rejectReviewItem: (reviewItemId: string, decision: ReviewDecision) =>
    request<ReviewItem>(`/review/items/${reviewItemId}/reject`, {
      method: "POST",
      body: JSON.stringify(decision)
    }),
  requestChanges: (reviewItemId: string, decision: ReviewDecision) =>
    request<ReviewItem>(`/review/items/${reviewItemId}/request-changes`, {
      method: "POST",
      body: JSON.stringify(decision)
    }),
  listObjects: () => request<KnowledgeObject[]>("/brain/objects"),
  getGraph: () => request<BrainGraph>("/brain/graph"),
  buildContextPack: (payload: ContextPackRequest) =>
    request<ContextPack>("/brain/context-pack", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  listAuditEvents: () => request<AuditEvent[]>("/governance/audit")
};
