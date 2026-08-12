export type SourceType = "document" | "markdown" | "spreadsheet" | "sql" | "dashboard" | "git" | "api" | "manual";
export type Sensitivity = "public" | "internal" | "confidential" | "restricted";
export type ReviewStatus = "draft" | "submitted" | "ai_classified" | "human_review_required" | "approved" | "rejected" | "changes_requested" | "published" | "deprecated";

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

export interface ReviewItem {
  id: string;
  source_id: string;
  candidate_object: KnowledgeObject;
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
  metadata: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  confidence: number;
  metadata: Record<string, unknown>;
}

export interface BrainGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  generated_at: string;
}
