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


class ReviewStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    ai_classified = "ai_classified"
    human_review_required = "human_review_required"
    approved = "approved"
    rejected = "rejected"
    changes_requested = "changes_requested"
    published = "published"
    deprecated = "deprecated"


class Sensitivity(str, Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"


class KnowledgeObjectType(str, Enum):
    metric = "Metric"
    report = "Report"
    business_rule = "BusinessRule"
    dataset = "Dataset"
    process = "Process"
    decision = "Decision"
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
    submitted_by: str
    content: str = Field(..., min_length=1)
    source_uri: str | None = None
    domain: str = "general"
    sensitivity: Sensitivity = Sensitivity.internal
    tags: list[str] = Field(default_factory=list)


class SourceEvidence(BaseModel):
    source_id: str = Field(default_factory=lambda: new_id("source"))
    source_type: SourceType
    title: str
    content_excerpt: str
    source_uri: str | None = None
    submitted_by: str
    domain: str
    sensitivity: Sensitivity
    created_at: datetime = Field(default_factory=utc_now)


class Relationship(BaseModel):
    type: str
    target_id: str
    confidence: float = 0.5


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
    relationships: list[Relationship] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.5
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SourceClassification(BaseModel):
    source_kind: str = "unknown"
    domain: str = "general"
    summary: str
    topics: list[str] = Field(default_factory=list)
    suggested_tags: list[str] = Field(default_factory=list)
    confidence: float = 0.5


class SuggestedRelationship(BaseModel):
    source_label: str
    relationship_type: str
    target_label: str
    confidence: float = 0.5
    rationale: str | None = None


class ValidationFinding(BaseModel):
    severity: ValidationSeverity = ValidationSeverity.info
    finding_type: str
    message: str
    source_span: str | None = None
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
    status: AITaskStatus = AITaskStatus.completed
    source_classification: SourceClassification
    extracted_objects: list[KnowledgeObject] = Field(default_factory=list)
    suggested_relationships: list[SuggestedRelationship] = Field(default_factory=list)
    validation_findings: list[ValidationFinding] = Field(default_factory=list)
    review_brief: AIReviewBrief
    confidence: float = 0.5
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class AIProviderStatus(BaseModel):
    provider: AIProviderName
    mode: AIEnrichmentMode
    enabled: bool
    model: str
    embedding_model: str | None = None
    base_url: str | None = None
    hosted_allowed_for_restricted: bool = False


class ReviewItem(BaseModel):
    id: str = Field(default_factory=lambda: new_id("review"))
    source_id: str
    candidate_object: KnowledgeObject
    ai_enrichment: AIEnrichmentResult | None = None
    status: ReviewStatus = ReviewStatus.human_review_required
    reviewer: str | None = None
    review_comment: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ReviewDecision(BaseModel):
    reviewed_by: str
    comment: str | None = None


class ContextPackRequest(BaseModel):
    question: str = Field(..., min_length=3)
    user_id: str
    domains: list[str] = Field(default_factory=list)
    mode: Literal[
        "default",
        "executive_insight",
        "metric_definition",
        "lineage",
        "governance_review",
        "debug",
    ] = "default"


class ContextPack(BaseModel):
    context_pack_id: str = Field(default_factory=lambda: new_id("ctx"))
    question: str
    user_id: str
    mode: str
    access_decision: Literal["allowed", "denied"] = "allowed"
    confidence: float
    answer_guidance: str
    knowledge_objects: list[KnowledgeObject] = Field(default_factory=list)
    evidence: list[SourceEvidence] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
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
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
