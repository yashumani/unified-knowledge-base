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
  EvidenceChunk,
  IngestionPayload,
  KnowledgeObject,
  PublishDecision,
  ReviewDecision,
  ReviewItem,
  ReviewRevisionRequest,
  SearchRequest,
  SearchResponse,
  SourceEvidence,
  SourceVersion
} from "../types";
import type {
  BatchIngestionResult,
  ConnectorIngestionRequest,
  CrawlIngestionRequest,
  DriveIngestionRequest,
  IngestionCapabilities,
  IngestionPreview
} from "../ingestionTypes";

const configuredApiBase = import.meta.env.VITE_UKB_API_BASE_URL;
export const API_BASE = configuredApiBase && configuredApiBase.trim().length > 0
  ? configuredApiBase.replace(/\/$/, "")
  : "http://localhost:8000";

const configuredApiToken = import.meta.env.VITE_UKB_API_TOKEN;
export const API_TOKEN = configuredApiToken?.trim() ?? "";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
  if (!headers.has("Content-Type") && init.body && !isFormData) {
    headers.set("Content-Type", "application/json");
  }
  if (API_TOKEN && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${API_TOKEN}`);
  }
  if (!headers.has("X-Request-ID")) {
    headers.set("X-Request-ID", `web-${crypto.randomUUID()}`);
  }

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    const raw = await response.text();
    let detail = raw;
    try {
      const parsed = JSON.parse(raw) as { detail?: string };
      detail = parsed.detail ?? raw;
    } catch {
      // Keep non-JSON detail.
    }
    if (response.status === 401 || response.status === 403) {
      throw new Error(
        `${response.status} ${response.statusText}: API identity missing or rejected. ` +
          `Configure a per-user session or set VITE_UKB_API_TOKEN for a trusted local deployment.`
      );
    }
    if (response.status === 409) {
      throw new Error(`This item changed while you were reviewing it. Refresh and try again. ${detail}`);
    }
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

export const brainClient = {
  health: () => request<{ status: string; environment: string; version?: string }>("/health"),
  ready: () => request<Record<string, unknown>>("/ready"),
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
  getIngestionCapabilities: () => request<IngestionCapabilities>("/ingestion/capabilities"),
  previewFiles: (form: FormData) =>
    request<IngestionPreview>("/ingestion/files/preview", { method: "POST", body: form }),
  submitFiles: (form: FormData) =>
    request<BatchIngestionResult>("/ingestion/files/submit", { method: "POST", body: form }),
  previewDriveFolder: (payload: DriveIngestionRequest) =>
    request<IngestionPreview>("/ingestion/google-drive/preview", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  submitDriveFolder: (payload: DriveIngestionRequest) =>
    request<BatchIngestionResult>("/ingestion/google-drive/submit", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  previewCrawl: (payload: CrawlIngestionRequest) =>
    request<IngestionPreview>("/ingestion/crawl4ai/preview", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  submitCrawl: (payload: CrawlIngestionRequest) =>
    request<BatchIngestionResult>("/ingestion/crawl4ai/submit", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  previewConnector: (payload: ConnectorIngestionRequest) =>
    request<IngestionPreview>("/ingestion/connectors/preview", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  submitConnector: (payload: ConnectorIngestionRequest) =>
    request<BatchIngestionResult>("/ingestion/connectors/submit", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  listSources: () => request<SourceEvidence[]>("/sources"),
  getSourceVersions: (sourceId: string) =>
    request<SourceVersion[]>(`/sources/${encodeURIComponent(sourceId)}/versions`),
  getSourceChunks: (sourceId: string) =>
    request<EvidenceChunk[]>(`/sources/${encodeURIComponent(sourceId)}/chunks`),
  listReviewItems: () => request<ReviewItem[]>("/review/queue"),
  listApprovedReviews: () => request<ReviewItem[]>("/review/approved"),
  enrichReviewItem: (reviewItemId: string) =>
    request<ReviewItem>(`/review/items/${reviewItemId}/enrich`, { method: "POST" }),
  getReviewItemAIEnrichment: (reviewItemId: string) =>
    request<AIEnrichmentResult>(`/review/items/${reviewItemId}/ai-enrichment`),
  approveReviewItem: (reviewItemId: string, decision: ReviewDecision) =>
    request<ReviewItem>(`/review/items/${reviewItemId}/approve`, {
      method: "POST",
      body: JSON.stringify(decision)
    }),
  publishReviewItem: (reviewItemId: string, decision: PublishDecision) =>
    request<ReviewItem>(`/review/items/${reviewItemId}/publish`, {
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
  reviseReviewItem: (reviewItemId: string, revision: ReviewRevisionRequest) =>
    request<ReviewItem>(`/review/items/${reviewItemId}/revise`, {
      method: "POST",
      body: JSON.stringify(revision)
    }),
  listObjects: () => request<KnowledgeObject[]>("/brain/objects"),
  getGraph: () => request<BrainGraph>("/brain/graph"),
  searchBrain: (payload: SearchRequest) =>
    request<SearchResponse>("/brain/search", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  buildContextPack: (payload: ContextPackRequest) =>
    request<ContextPack>("/brain/context-pack", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  listAuditEvents: () => request<AuditEvent[]>("/governance/audit")
};
