from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class SourceType(str, Enum):
    document = "document"
    markdown = "markdown"
    spreadsheet = "spreadsheet"
    sql = "sql"
    dashboard = "dashboard"
    git = "git"
    api = "api"
    manual = "manual"
    web = "web"
    folder = "folder"
    archive = "archive"
    object_store = "object_store"


class ReviewStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    parsing = "parsing"
    enrichment_pending = "enrichment_pending"
    ai_classified = "ai_classified"
    human_review_required = "human_review_required"
    changes_requested = "changes_requested"
    approved = "approved"
    publication_pending = "publication_pending"
    published = "published"
    rejected = "rejected"
    superseded = "superseded"
    deprecated = "deprecated"


class Sensitivity(str, Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"


class KnowledgeObjectType(str, Enum):
    metric = "Metric"
    dimension = "Dimension"
    report = "Report"
    dashboard = "Dashboard"
    business_rule = "BusinessRule"
    dataset = "Dataset"
    table = "Table"
    column = "Column"
    process = "Process"
    decision = "Decision"
    system = "System"
    owner = "Owner"
    narrative_template = "NarrativeTemplate"
    glossary_term = "GlossaryTerm"
    unknown = "Unknown"


class AIProviderName(str, Enum):
    noop = "noop"
    ollama = "ollama"
    openai = "openai"
    custom = "custom"


class AIEnrichmentMode(str, Enum):
    offline_no_model = "offline_no_model"
    local_ai = "local_ai"
    hosted_ai = "hosted_ai"
    hybrid = "hybrid"


class AITaskStatus(str, Enum):
    queued = "queued"
    running = "running"
    skipped = "skipped"
    completed = "completed"
    failed = "failed"


class ValidationSeverity(str, Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IngestionSubmission(BaseModel):
    title: str = Field(..., min_length=3)
    source_type: SourceType
    submitted_by: str = "unknown"
    content: str = Field(..., min_length=1)
    source_uri: str | None = None
    domain: str = "general"
    owner: str | None = None
    sensitivity: Sensitivity = Sensitivity.internal
    tags: list[str] = Field(default_factory=list)
    effective_date: str | None = None


class SourceEvidence(BaseModel):
    source_id: str = Field(default_factory=lambda: new_id("source"))
    source_type: SourceType
    title: str
    content_excerpt: str
    source_uri: str | None = None
    submitted_by: str
    domain: str
    owner: str | None = None
    sensitivity: Sensitivity
    access_policy: dict[str, Any] = Field(default_factory=dict)
    content_hash: str | None = None
    current_version_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SourceVersion(BaseModel):
    id: str = Field(default_factory=lambda: new_id("source_version"))
    source_id: str
    version: int = 1
    content_hash: str
    content_type: str = "text/plain"
    size_bytes: int = 0
    object_key: str | None = None
    object_uri: str | None = None
    normalized_text: str = ""
    parser: str = "deterministic"
    parser_version: str = "1"
    source_uri: str | None = None
    created_by: str
    created_at: datetime = Field(default_factory=utc_now)


class EvidenceChunk(BaseModel):
    id: str = Field(default_factory=lambda: new_id("chunk"))
    source_id: str
    source_version_id: str
    ordinal: int
    heading_path: list[str] = Field(default_factory=list)
    content: str
    content_type: str = "text"
    locator: str | None = None
    start_offset: int = 0
    end_offset: int = 0
    content_hash: str
    sensitivity: Sensitivity = Sensitivity.internal
    created_at: datetime = Field(default_factory=utc_now)


class EvidenceReference(BaseModel):
    chunk_id: str
    source_id: str
    source_version_id: str
    quote: str = ""
    locator: str | None = None
    field_name: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class Relationship(BaseModel):
    type: str
    target_id: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class RelationshipRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("rel"))
    source_object_id: str
    target_object_id: str
    relationship_type: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)
    status: ReviewStatus = ReviewStatus.publication_pending
    proposed_by: str = "compiler"
    approved_by: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class KnowledgeObject(BaseModel):
    id: str = Field(default_factory=lambda: new_id("obj"))
    type: KnowledgeObjectType = KnowledgeObjectType.unknown
    title: str
    summary: str
    domain: str
    owner: str | None = None
    status: ReviewStatus = ReviewStatus.ai_classified
    sensitivity: Sensitivity = Sensitivity.internal
    source_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    authority_tier: int = Field(default=3, ge=1, le=5)
    version: int = Field(default=1, ge=1)
    supersedes_id: str | None = None
    published_by: str | None = None
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SourceClassification(BaseModel):
    source_kind: str = "unknown"
    domain: str = "general"
    summary: str
    topics: list[str] = Field(default_factory=list)
    suggested_tags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class SuggestedRelationship(BaseModel):
    source_label: str
    relationship_type: str
    target_label: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str | None = None
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)


class ValidationFinding(BaseModel):
    severity: ValidationSeverity = ValidationSeverity.info
    finding_type: str
    message: str
    source_span: str | None = None
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)
    recommended_action: str | None = None


class AIReviewBrief(BaseModel):
    summary: str
    recommended_action: Literal["approve", "request_changes", "reject", "needs_review"] = (
        "needs_review"
    )
    reviewer_questions: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class AIEnrichmentResult(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ai"))
    provider: AIProviderName = AIProviderName.noop
    model: str = "deterministic"
    schema_version: str = "1.0"
    prompt_version: str = "source-enrichment-v1"
    status: AITaskStatus = AITaskStatus.completed
    source_classification: SourceClassification
    extracted_objects: list[KnowledgeObject] = Field(default_factory=list)
    suggested_relationships: list[SuggestedRelationship] = Field(default_factory=list)
    validation_findings: list[ValidationFinding] = Field(default_factory=list)
    review_brief: AIReviewBrief
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class AITaskRun(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ai_task"))
    task_type: str
    provider: AIProviderName
    model: str
    status: AITaskStatus
    source_id: str | None = None
    review_item_id: str | None = None
    context_pack_id: str | None = None
    input_hash: str
    prompt_version: str
    schema_version: str
    fallback_used: bool = False
    latency_ms: int | None = None
    output_id: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class AIProviderStatus(BaseModel):
    provider: AIProviderName
    mode: AIEnrichmentMode
    enabled: bool
    model: str
    embedding_model: str | None = None
    base_url: str | None = None
    hosted_allowed_for_restricted: bool = False
    local_only: bool = True
    capabilities: list[str] = Field(default_factory=list)


class AIProviderHealth(BaseModel):
    provider: AIProviderName
    reachable: bool
    message: str
    base_url: str | None = None
    model: str
    embedding_model: str | None = None
    checked_at: datetime = Field(default_factory=utc_now)
    details: dict[str, Any] = Field(default_factory=dict)


class EmbeddingRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=32)
    model: str | None = None


class EmbeddingResponse(BaseModel):
    provider: AIProviderName
    model: str
    dimensions: int
    embeddings: list[list[float]]
    fallback_used: bool = False


class ReviewItem(BaseModel):
    id: str = Field(default_factory=lambda: new_id("review"))
    source_id: str
    candidate_object: KnowledgeObject
    ai_enrichment: AIEnrichmentResult | None = None
    status: ReviewStatus = ReviewStatus.human_review_required
    revision: int = Field(default=1, ge=1)
    reviewer: str | None = None
    review_comment: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ReviewDecision(BaseModel):
    reviewed_by: str | None = None
    comment: str | None = None
    expected_revision: int | None = Field(default=None, ge=1)


class ReviewRevisionRequest(BaseModel):
    title: str | None = None
    summary: str | None = None
    owner: str | None = None
    attributes: dict[str, Any] | None = None
    expected_revision: int = Field(..., ge=1)
    comment: str | None = None


class PublishDecision(BaseModel):
    published_by: str | None = None
    comment: str | None = None
    expected_revision: int | None = Field(default=None, ge=1)


class ContextPackRequest(BaseModel):
    question: str = Field(..., min_length=3)
    user_id: str = "unknown"
    domains: list[str] = Field(default_factory=list)
    mode: Literal[
        "default",
        "executive_insight",
        "metric_definition",
        "lineage",
        "governance_review",
        "debug",
    ] = "default"


class ContextPackCitation(BaseModel):
    citation_id: str = Field(default_factory=lambda: new_id("citation"))
    object_id: str
    source_id: str
    source_version_id: str | None = None
    chunk_id: str | None = None
    title: str
    quote: str
    locator: str | None = None


class ConfidenceFactors(BaseModel):
    retrieval: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    source_authority: float = Field(default=0.0, ge=0.0, le=1.0)
    freshness: float = Field(default=0.0, ge=0.0, le=1.0)
    conflict_penalty: float = Field(default=0.0, ge=0.0, le=1.0)


class ContextPack(BaseModel):
    context_pack_id: str = Field(default_factory=lambda: new_id("ctx"))
    question: str
    user_id: str
    mode: str
    access_decision: Literal["allowed", "denied"] = "allowed"
    confidence: float
    confidence_factors: ConfidenceFactors = Field(default_factory=ConfidenceFactors)
    retrieval_engine: str = "memory"
    answer_guidance: str
    knowledge_objects: list[KnowledgeObject] = Field(default_factory=list)
    evidence: list[SourceEvidence] = Field(default_factory=list)
    citations: list[ContextPackCitation] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    related_objects: list[str] = Field(default_factory=list)
    recommended_followups: list[str] = Field(default_factory=list)
    ai_guidance: str | None = None
    missing_context: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    domain: str | None = None
    status: str | None = None
    sensitivity: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    confidence: float = 0.5
    metadata: dict[str, Any] = Field(default_factory=dict)


class BrainGraph(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: new_id("audit"))
    event_type: str
    actor: str
    target_id: str | None = None
    request_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
