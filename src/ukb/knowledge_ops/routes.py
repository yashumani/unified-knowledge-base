from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException

from ukb.api.security import Principal, require_principal, require_roles
from ukb.knowledge_ops.models import (
    KnowledgeOperationsStatus,
    QualityAssessment,
    QualityAssessmentRequest,
    QualitySubmissionResult,
    RerankedSearchResponse,
    RetrievalEvaluationReport,
    RetrievalEvaluationRequest,
    RetrievalFeedback,
    RetrievalFeedbackRequest,
    ReviewAssignment,
    ReviewAssignmentRequest,
    ReviewComment,
    ReviewCommentRequest,
    SourceRefreshRun,
    SourceSubscription,
    SourceSubscriptionRequest,
    SubscriptionStatus,
)
from ukb.knowledge_ops.runtime import service
from ukb.models import utc_now
from ukb.search import SearchRequest

router = APIRouter(prefix="/v1/knowledge-operations", tags=["knowledge-operations"])


@router.get("/status", response_model=KnowledgeOperationsStatus)
def operations_status(
    principal: Principal = Depends(require_principal),
) -> KnowledgeOperationsStatus:
    require_roles(
        principal,
        {"consumer", "submitter", "reviewer", "publisher", "governance_admin"},
    )
    return service.status(principal)


@router.get("/auth/config")
def auth_config() -> dict[str, object]:
    settings = service.settings
    return {
        "oidc_enabled": settings.oidc_enabled,
        "issuer": settings.oidc_issuer if settings.oidc_enabled else None,
        "audience_configured": bool(settings.oidc_audience),
        "tenant_claim": settings.oidc_tenant_claim,
        "roles_claim": settings.oidc_roles_claim,
        "groups_claim": settings.oidc_groups_claim,
        "clearance_claim": settings.oidc_clearance_claim,
    }


@router.get("/auth/me")
def auth_me(
    principal: Principal = Depends(require_principal),
) -> dict[str, object]:
    return {
        "subject": principal.subject,
        "tenant_id": principal.tenant_id,
        "roles": sorted(principal.roles),
        "clearance": principal.clearance.value,
        "auth_method": principal.auth_method,
    }


@router.post("/quality/assess", response_model=QualityAssessment)
def assess_quality(
    request: QualityAssessmentRequest,
    principal: Principal = Depends(require_principal),
) -> QualityAssessment:
    require_roles(principal, {"submitter", "reviewer", "governance_admin"})
    return service.assess(request, principal=principal)


@router.post("/quality/submit", response_model=QualitySubmissionResult)
def submit_through_quality_firewall(
    request: QualityAssessmentRequest,
    principal: Principal = Depends(require_principal),
) -> QualitySubmissionResult:
    require_roles(principal, {"submitter", "reviewer", "governance_admin"})
    return service.submit(request, principal=principal)


@router.get("/quality/assessments", response_model=list[QualityAssessment])
def list_quality_assessments(
    principal: Principal = Depends(require_principal),
) -> list[QualityAssessment]:
    require_roles(principal, {"reviewer", "governance_admin"})
    return service.list_assessments(principal)


@router.post("/reviews/assign", response_model=ReviewAssignment)
def assign_review(
    request: ReviewAssignmentRequest,
    principal: Principal = Depends(require_principal),
) -> ReviewAssignment:
    require_roles(principal, {"reviewer", "governance_admin"})
    try:
        return service.assign_review(request, principal=principal)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/reviews/assignments", response_model=list[ReviewAssignment])
def list_review_assignments(
    principal: Principal = Depends(require_principal),
) -> list[ReviewAssignment]:
    require_roles(principal, {"reviewer", "governance_admin"})
    return sorted(
        (
            value
            for value in service.store.assignments.values()
            if value.tenant_id == principal.tenant_id
        ),
        key=lambda value: value.updated_at,
        reverse=True,
    )


@router.post("/reviews/comments", response_model=ReviewComment)
def add_review_comment(
    request: ReviewCommentRequest,
    principal: Principal = Depends(require_principal),
) -> ReviewComment:
    require_roles(principal, {"submitter", "reviewer", "governance_admin"})
    try:
        return service.add_comment(request, principal=principal)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/reviews/{review_item_id}/comments", response_model=list[ReviewComment])
def list_review_comments(
    review_item_id: str,
    principal: Principal = Depends(require_principal),
) -> list[ReviewComment]:
    require_roles(principal, {"submitter", "reviewer", "governance_admin"})
    return sorted(
        (
            value
            for value in service.store.comments.values()
            if value.tenant_id == principal.tenant_id
            and value.review_item_id == review_item_id
        ),
        key=lambda value: value.created_at,
    )


@router.get("/reviews/workload")
def review_workload(
    principal: Principal = Depends(require_principal),
) -> dict[str, object]:
    require_roles(principal, {"reviewer", "governance_admin"})
    return service.review_workload(principal)


@router.post("/subscriptions", response_model=SourceSubscription)
def create_subscription(
    request: SourceSubscriptionRequest,
    principal: Principal = Depends(require_principal),
) -> SourceSubscription:
    require_roles(principal, {"source_admin", "governance_admin"})
    return service.create_subscription(request, principal=principal)


@router.get("/subscriptions", response_model=list[SourceSubscription])
def list_subscriptions(
    principal: Principal = Depends(require_principal),
) -> list[SourceSubscription]:
    require_roles(principal, {"source_admin", "reviewer", "governance_admin"})
    return service.list_subscriptions(principal)


@router.post("/subscriptions/{subscription_id}/run", response_model=SourceRefreshRun)
def run_subscription(
    subscription_id: str,
    principal: Principal = Depends(require_principal),
) -> SourceRefreshRun:
    require_roles(principal, {"source_admin", "governance_admin"})
    try:
        return service.run_subscription(subscription_id, principal=principal)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/subscriptions/{subscription_id}/pause", response_model=SourceSubscription)
def pause_subscription(
    subscription_id: str,
    principal: Principal = Depends(require_principal),
) -> SourceSubscription:
    require_roles(principal, {"source_admin", "governance_admin"})
    value = service.store.subscriptions.get(subscription_id)
    if value is None or value.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=404, detail=f"Source subscription not found: {subscription_id}")
    value.status = SubscriptionStatus.paused
    value.updated_at = utc_now()
    return service.store.add_subscription(value)


@router.post("/subscriptions/{subscription_id}/resume", response_model=SourceSubscription)
def resume_subscription(
    subscription_id: str,
    principal: Principal = Depends(require_principal),
) -> SourceSubscription:
    require_roles(principal, {"source_admin", "governance_admin"})
    value = service.store.subscriptions.get(subscription_id)
    if value is None or value.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=404, detail=f"Source subscription not found: {subscription_id}")
    value.status = SubscriptionStatus.active
    value.updated_at = utc_now()
    return service.store.add_subscription(value)


@router.get("/refresh-runs", response_model=list[SourceRefreshRun])
def list_refresh_runs(
    principal: Principal = Depends(require_principal),
) -> list[SourceRefreshRun]:
    require_roles(principal, {"source_admin", "reviewer", "governance_admin"})
    return sorted(
        (
            value
            for value in service.store.refresh_runs.values()
            if value.tenant_id == principal.tenant_id
        ),
        key=lambda value: value.completed_at,
        reverse=True,
    )


@router.post("/search", response_model=RerankedSearchResponse)
def reranked_search(
    request: SearchRequest,
    principal: Principal = Depends(require_principal),
) -> RerankedSearchResponse:
    require_roles(
        principal,
        {"consumer", "submitter", "reviewer", "publisher", "governance_admin"},
    )
    return service.reranked_search(request, principal=principal)


@router.post("/search/evaluate", response_model=RetrievalEvaluationReport)
def evaluate_search(
    request: RetrievalEvaluationRequest,
    principal: Principal = Depends(require_principal),
) -> RetrievalEvaluationReport:
    require_roles(principal, {"reviewer", "publisher", "governance_admin"})
    return service.evaluate(request, principal=principal)


@router.post("/search/feedback", response_model=RetrievalFeedback)
def add_search_feedback(
    request: RetrievalFeedbackRequest,
    principal: Principal = Depends(require_principal),
) -> RetrievalFeedback:
    require_roles(
        principal,
        {"consumer", "submitter", "reviewer", "publisher", "governance_admin"},
    )
    return service.add_feedback(request, principal=principal)


@router.get("/search/feedback-summary")
def feedback_summary(
    principal: Principal = Depends(require_principal),
) -> dict[str, object]:
    require_roles(principal, {"reviewer", "publisher", "governance_admin"})
    values = [
        value
        for value in service.store.feedback.values()
        if value.tenant_id == principal.tenant_id
    ]
    return {
        "tenant_id": principal.tenant_id,
        "count": len(values),
        "by_label": dict(sorted(Counter(value.label.value for value in values).items())),
    }
