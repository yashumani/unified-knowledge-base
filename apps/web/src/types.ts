export type SourceType = "document" | "markdown" | "spreadsheet" | "sql" | "dashboard" | "git" | "api" | "manual";
export type Sensitivity = "public" | "internal" | "confidential" | "restricted";
export type ReviewStatus = "draft" | "submitted" | "ai_classified" | "human_review_required" | "approved" | "rejected" | "changes_requested" | "published" | "deprecated";
export type ValidationSeverity = "info" | "low" | "medium" | "high" | "critical";
export type AIProviderName = "noop" | "ollama" | "openai" | "custom";
export type AIEnrichmentMode = "offline_no_model" | "local_ai" | "hosted_ai" | "hybrid";

export interface IngestionPayload {
  title: string;
  source_type: SourceType;
  submitted_by: string;
  content: string;
  source_uri?: string | null;
  domain: string;
  sensitivity: Sensitivity;
  tags: string[];
}

export interface SourceEvidence {
  source_id: string;
  source_type: SourceType;
  title: string;
  content_excerpt: string;
  source_uri?: string | null;
  submitted_by: string;
  domain: string;
  sensitivity: Sensitivity;
  created_at: string;
}

export interface Relationship {
  type: string;
  target_id: string;
  confidence: number;
}

export interface KnowledgeObject {
  id: string;
  type: string;
  title: string;
  summary: string;
  domain: string;
  owner?: string | null;
  status: ReviewStatus;
  sensitivity: Sensitivity;
  source_ids: string[];
  relationships: Relationship[];
  attributes: Record<string, unknown>;
  confidence: number;
  created_at: string;
  updated_at: string;
}

export interface SourceClassification {
  source_kind: string;
  domain: string;
  summary: string;
  topics: string[];
  suggested_tags: string[];
  confidence: number;
}

export interface SuggestedRelationship {
  source_label: string;
  relationship_type: string;
  target_label: string;
  confidence: number;
  rationale?: string | null;
}

export interface ValidationFinding {
  severity: ValidationSeverity;
  finding_type: string;
  message: string;
  source_span?: string | null;
  recommended_action?: string | null;
}

export interface AIReviewBrief {
  summary: string;
  recommended_action: "approve" | "request_changes" | "reject" | "needs_review";
  reviewer_questions: string[];
  risk_flags: string[];
}

export interface AIEnrichmentResult {
  id: string;
  provider: AIProviderName;
  model: string;
  status: "skipped" | "completed" | "failed";
  source_classification: SourceClassification;
  extracted_objects: KnowledgeObject[];
  suggested_relationships: SuggestedRelationship[];
  validation_findings: ValidationFinding[];
  review_brief: AIReviewBrief;
  confidence: number;
  error_message?: string | null;
  created_at: string;
}

export interface AIProviderStatus {
  provider: AIProviderName;
  mode: AIEnrichmentMode;
  enabled: boolean;
  model: string;
  embedding_model?: string | null;
  base_url?: string | null;
  hosted_allowed_for_restricted: boolean;
  local_only: boolean;
  capabilities: string[];
}

export interface AIProviderHealth {
  provider: AIProviderName;
  reachable: boolean;
  message: string;
  base_url?: string | null;
  model: string;
  embedding_model?: string | null;
  checked_at: string;
  details: Record<string, unknown>;
}

export interface EmbeddingRequest {
  texts: string[];
  model?: string | null;
}

export interface EmbeddingResponse {
  provider: AIProviderName;
  model: string;
  dimensions: number;
  embeddings: number[][];
  fallback_used: boolean;
}

export interface ReviewItem {
  id: string;
  source_id: string;
  candidate_object: KnowledgeObject;
  ai_enrichment?: AIEnrichmentResult | null;
  status: ReviewStatus;
  reviewer?: string | null;
  review_comment?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewDecision {
  reviewed_by: string;
  comment?: string | null;
}

export interface ContextPackRequest {
  question: string;
  user_id: string;
  domains: string[];
  mode: "default" | "executive_insight" | "metric_definition" | "lineage" | "governance_review" | "debug";
}

export interface ContextPack {
  context_pack_id: string;
  question: string;
  user_id: string;
  mode: string;
  access_decision: "allowed" | "denied";
  confidence: number;
  answer_guidance: string;
  knowledge_objects: KnowledgeObject[];
  evidence: SourceEvidence[];
  caveats: string[];
  related_objects: string[];
  recommended_followups: string[];
  ai_guidance?: string | null;
  missing_context: string[];
  generated_at: string;
}

export interface AuditEvent {
  id: string;
  event_type: string;
  actor: string;
  target_id?: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  domain?: string | null;
  status?: string | null;
  sensitivity?: string | null;
  confidence?: number | null;
  metadata: unknown;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  confidence: number;
  metadata: unknown;
}

export interface BrainGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  generated_at: string;
}
