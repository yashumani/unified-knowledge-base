from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from ukb.models import Sensitivity, SourceType, utc_now


class QualityDisposition(StrEnum):
    accept = "accept"
    accept_with_warnings = "accept_with_warnings"
    quarantine = "quarantine"
    reject = "reject"


class QualitySeverity(StrEnum):
    info = "info"
    warning = "warning"
    high = "high"
    critical = "critical"


class QualityFinding(BaseModel):
    code: str
    severity: QualitySeverity
    message: str
    recommendation: str | None = None


class QualityAssessmentRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=300)
    content: str = Field(..., min_length=1, max_length=2_000_000)
    source_type: SourceType = SourceType.document
    source_uri: str | None = None
    domain: str = Field(default="general", min_length=1, max_length=160)
    owner: str | None = None
    sensitivity: Sensitivity = Sensitivity.internal
    tags: list[str] = Field(default_factory=list)
    effective_date: str | None = None


class QualityAssessment(BaseModel):
    assessment_id: str
    tenant_id: str
    actor: str
    input_hash: str
    score: float = Field(ge=0.0, le=1.0)
    disposition: QualityDisposition
    findings: list[QualityFinding] = Field(default_factory=list)
    policy_version: str = "quality-firewall-v1"
    created_at: datetime = Field(default_factory=utc_now)


class QualitySubmissionResult(BaseModel):
    assessment: QualityAssessment
    review_item_id: str | None = None
    source_id: str | None = None
    status: Literal["review_created", "quarantined", "rejected"]


class ReviewPriority(StrEnum):
    low = "low"
    normal = "normal"
    high = "high"
    urgent = "urgent"


class AssignmentStatus(StrEnum):
    assigned = "assigned"
    claimed = "claimed"
    completed = "completed"
    cancelled = "cancelled"


class ReviewAssignmentRequest(BaseModel):
    review_item_id: str
    assignee: str = Field(..., min_length=1, max_length=200)
    priority: ReviewPriority = ReviewPriority.normal
    due_at: datetime | None = None
    note: str | None = Field(default=None, max_length=2000)


class ReviewAssignment(BaseModel):
    assignment_id: str
    tenant_id: str
    review_item_id: str
    assignee: str
    assigned_by: str
    priority: ReviewPriority = ReviewPriority.normal
    status: AssignmentStatus = AssignmentStatus.assigned
    due_at: datetime | None = None
    note: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ReviewCommentRequest(BaseModel):
    review_item_id: str
    body: str = Field(..., min_length=1, max_length=5000)
    comment_type: Literal["comment", "question", "response", "decision_note"] = "comment"


class ReviewComment(BaseModel):
    comment_id: str
    tenant_id: str
    review_item_id: str
    author: str
    body: str
    comment_type: str
    created_at: datetime = Field(default_factory=utc_now)


class ConnectorType(StrEnum):
    crawl4ai = "crawl4ai"
    google_drive = "google_drive"
    git = "git"
    object_store = "object_store"
    api = "api"


class SubscriptionStatus(StrEnum):
    active = "active"
    paused = "paused"
    failing = "failing"


class SourceSubscriptionRequest(BaseModel):
    connector_type: ConnectorType
    location: str = Field(..., min_length=3, max_length=2000)
    domain: str = Field(default="general", min_length=1, max_length=160)
    owner: str | None = None
    sensitivity: Sensitivity = Sensitivity.internal
    interval_minutes: int = Field(default=1440, ge=5, le=525600)
    tags: list[str] = Field(default_factory=list)


class SourceSubscription(BaseModel):
    subscription_id: str
    tenant_id: str
    connector_type: ConnectorType
    location: str
    domain: str
    owner: str | None = None
    sensitivity: Sensitivity = Sensitivity.internal
    interval_minutes: int = 1440
    tags: list[str] = Field(default_factory=list)
    status: SubscriptionStatus = SubscriptionStatus.active
    created_by: str
    last_checksum: str | None = None
    last_success_at: datetime | None = None
    next_run_at: datetime | None = None
    consecutive_failures: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RefreshStatus(StrEnum):
    changed = "changed"
    unchanged = "unchanged"
    failed = "failed"
    skipped = "skipped"


class SourceRefreshRun(BaseModel):
    run_id: str
    tenant_id: str
    subscription_id: str
    status: RefreshStatus
    checksum: str | None = None
    review_item_ids: list[str] = Field(default_factory=list)
    message: str
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime = Field(default_factory=utc_now)


class RetrievalFeedbackLabel(StrEnum):
    helpful = "helpful"
    wrong_source = "wrong_source"
    missing_source = "missing_source"
    outdated_source = "outdated_source"
    irrelevant_context = "irrelevant_context"
    should_have_abstained = "should_have_abstained"
    conflicting_knowledge = "conflicting_knowledge"


class RetrievalFeedbackRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    label: RetrievalFeedbackLabel
    object_id: str | None = None
    context_pack_id: str | None = None
    note: str | None = Field(default=None, max_length=3000)


class RetrievalFeedback(BaseModel):
    feedback_id: str
    tenant_id: str
    actor: str
    query: str
    label: RetrievalFeedbackLabel
    object_id: str | None = None
    context_pack_id: str | None = None
    note: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class RankingFactor(BaseModel):
    name: str
    value: float
    contribution: float


class RerankedResult(BaseModel):
    object_id: str
    title: str
    domain: str
    raw_score: float
    final_score: float
    factors: list[RankingFactor] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class RerankedSearchResponse(BaseModel):
    query: str
    policy_version: str = "governed-rerank-v1"
    results: list[RerankedResult] = Field(default_factory=list)
    denied_count: int = 0
    retrieval_backend: str


class EvaluationCase(BaseModel):
    question: str = Field(..., min_length=1)
    expected_object_ids: list[str] = Field(default_factory=list)
    expected_titles: list[str] = Field(default_factory=list)
    should_abstain: bool = False
    domains: list[str] = Field(default_factory=list)


class RetrievalEvaluationRequest(BaseModel):
    cases: list[EvaluationCase] = Field(..., min_length=1, max_length=200)
    top_k: int = Field(default=5, ge=1, le=50)


class RetrievalEvaluationReport(BaseModel):
    case_count: int
    recall_at_k: float = Field(ge=0.0, le=1.0)
    mean_reciprocal_rank: float = Field(ge=0.0, le=1.0)
    abstention_accuracy: float = Field(ge=0.0, le=1.0)
    passed_cases: int
    failed_cases: int
    policy_version: str = "governed-rerank-v1"
    generated_at: datetime = Field(default_factory=utc_now)


class KnowledgeOperationsStatus(BaseModel):
    tenant_id: str
    subject: str
    auth_method: str
    quality_assessments: int
    quarantined_sources: int
    active_assignments: int
    active_subscriptions: int
    retrieval_feedback: int
    capabilities: list[str] = Field(default_factory=list)
