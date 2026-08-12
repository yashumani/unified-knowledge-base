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
    unknown = "Unknown"


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


class ReviewItem(BaseModel):
    id: str = Field(default_factory=lambda: new_id("review"))
    source_id: str
    candidate_object: KnowledgeObject
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
    generated_at: datetime = Field(default_factory=utc_now)


class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: new_id("audit"))
    event_type: str
    actor: str
    target_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
