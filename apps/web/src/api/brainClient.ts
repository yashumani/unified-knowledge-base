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

// The API requires a token on every route except /health. This is a
// single-tenant development convenience: a Vite env var is baked into the
// client bundle at build time, so it is only ever safe for a local or
// trusted-network deployment. A public deployment must move to per-user
// sessions (SSO/OIDC) rather than shipping a shared secret to the browser.
const configuredApiToken = import.meta.env.VITE_UKB_API_TOKEN;
export const API_TOKEN = configuredApiToken?.trim() ?? "";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  if (API_TOKEN && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${API_TOKEN}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers
  });

  if (!response.ok) {
    const detail = await response.text();
    if (response.status === 401 || response.status === 403) {
      throw new Error(
        `${response.status} ${response.statusText}: API token missing or rejected. ` +
          `Set VITE_UKB_API_TOKEN to match the server's UKB_API_TOKEN.`
      );
    }
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
