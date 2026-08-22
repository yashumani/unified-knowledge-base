from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from ukb.api.ingestion_routes import router as ingestion_router
from ukb.api.search_routes import router as search_router
from ukb.api.security import (
    Principal,
    require_principal,
    require_roles,
    warn_on_insecure_configuration,
)
from ukb.models import (
    AIEnrichmentResult,
    AIProviderHealth,
    AIProviderStatus,
    AITaskRun,
    AuditEvent,
    BrainGraph,
    ContextPack,
    ContextPackRequest,
    EmbeddingRequest,
    EmbeddingResponse,
    IngestionSubmission,
    KnowledgeObject,
    PublishDecision,
    ReviewDecision,
    ReviewItem,
    ReviewRevisionRequest,
)
from ukb.services.governance import GovernanceConflict, GovernanceValidationError
from ukb.services.graph import BrainGraphService
from ukb.services.runtime import application, settings


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    warn_on_insecure_configuration(settings)
    yield
    application.close()


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description=(
        "Governed AI Brain runtime with durable evidence, advisory local Ollama enrichment, "
        "human approval, explicit publication, permission-aware retrieval, and context packs."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_identity(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex[:16]}"
    request.state.request_id = request_id
    response = cast(Response, await call_next(request))
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(GovernanceConflict)
async def governance_conflict(_: Request, exc: GovernanceConflict) -> Response:
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(GovernanceValidationError)
async def governance_validation(_: Request, exc: GovernanceValidationError) -> Response:
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=422, content={"detail": str(exc)})


public_router = APIRouter()
protected_router = APIRouter()
graph_service = BrainGraphService(application.store)


@public_router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "environment": settings.environment,
        "version": app.version,
    }


@public_router.get("/ready")
def readiness() -> dict[str, object]:
    index = application.retrieval.status()
    return {
        "status": "ready",
        "store_backend": settings.store_backend,
        "search_backend": index.backend_active,
        "search_available": index.available,
        "ai_provider": application.ai.status().provider.value,
    }


@protected_router.get("/ai/providers", response_model=AIProviderStatus)
def get_ai_provider_status(
    principal: Principal = Depends(require_principal),
) -> AIProviderStatus:
    require_roles(
        principal,
        {"consumer", "submitter", "reviewer", "publisher", "governance_admin"},
    )
    return application.ai.status()


@protected_router.get("/ai/health", response_model=AIProviderHealth)
def get_ai_provider_health(
    principal: Principal = Depends(require_principal),
) -> AIProviderHealth:
    require_roles(principal, {"reviewer", "publisher", "governance_admin"})
    return application.ai.health()


@protected_router.post("/ai/embeddings", response_model=EmbeddingResponse)
def build_embeddings(
    request: EmbeddingRequest,
    principal: Principal = Depends(require_principal),
) -> EmbeddingResponse:
    require_roles(principal, {"reviewer", "publisher", "governance_admin"})
    return application.ai.embed_texts(texts=request.texts, model=request.model)


@protected_router.get("/ai/tasks", response_model=list[AITaskRun])
def list_ai_tasks(
    principal: Principal = Depends(require_principal),
) -> list[AITaskRun]:
    require_roles(principal, {"reviewer", "governance_admin"})
    return sorted(
        application.store.ai_task_runs.values(),
        key=lambda item: item.created_at,
        reverse=True,
    )


@protected_router.post("/ingestion/submissions", response_model=ReviewItem)
def submit_context(
    submission: IngestionSubmission,
    principal: Principal = Depends(require_principal),
) -> ReviewItem:
    require_roles(principal, {"submitter", "reviewer", "governance_admin"})
    return application.submit_text(submission, principal=principal)


@protected_router.get("/review/queue", response_model=list[ReviewItem])
def list_review_queue(
    principal: Principal = Depends(require_principal),
) -> list[ReviewItem]:
    require_roles(principal, {"reviewer", "governance_admin"})
    return [
        item
        for item in application.governance.list_queue()
        if application.access_policy.can_access(principal, item.candidate_object)
    ]


@protected_router.get("/review/approved", response_model=list[ReviewItem])
def list_approved_reviews(
    principal: Principal = Depends(require_principal),
) -> list[ReviewItem]:
    require_roles(principal, {"publisher", "governance_admin"})
    return [
        item
        for item in application.governance.list_approved()
        if application.access_policy.can_access(principal, item.candidate_object)
    ]


@protected_router.get("/review/items/{review_item_id}", response_model=ReviewItem)
def get_review_item(
    review_item_id: str,
    principal: Principal = Depends(require_principal),
) -> ReviewItem:
    require_roles(principal, {"reviewer", "publisher", "governance_admin"})
    item = application.store.review_items.get(review_item_id)
    if item is None or not application.access_policy.can_access(
        principal, item.candidate_object
    ):
        raise HTTPException(
            status_code=404,
            detail=f"Review item not found: {review_item_id}",
        )
    return item


@protected_router.post("/review/items/{review_item_id}/enrich", response_model=ReviewItem)
def enrich_review_item(
    review_item_id: str,
    principal: Principal = Depends(require_principal),
) -> ReviewItem:
    require_roles(principal, {"reviewer", "governance_admin"})
    try:
        return application.enrich_review(review_item_id, principal=principal)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@protected_router.get(
    "/review/items/{review_item_id}/ai-enrichment",
    response_model=AIEnrichmentResult,
)
def get_review_item_ai_enrichment(
    review_item_id: str,
    principal: Principal = Depends(require_principal),
) -> AIEnrichmentResult:
    item = get_review_item(review_item_id, principal)
    if item.ai_enrichment is None:
        raise HTTPException(
            status_code=404,
            detail="The review item has no AI enrichment.",
        )
    return item.ai_enrichment


@protected_router.post("/review/items/{review_item_id}/approve", response_model=ReviewItem)
def approve_review_item(
    review_item_id: str,
    decision: ReviewDecision,
    principal: Principal = Depends(require_principal),
) -> ReviewItem:
    require_roles(principal, settings.reviewer_role_set)
    try:
        return application.approve_review(review_item_id, decision, principal=principal)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@protected_router.post("/review/items/{review_item_id}/publish", response_model=ReviewItem)
def publish_review_item(
    review_item_id: str,
    decision: PublishDecision,
    principal: Principal = Depends(require_principal),
) -> ReviewItem:
    require_roles(principal, settings.publisher_role_set)
    try:
        return application.publish_review(
            review_item_id,
            decision,
            principal=principal,
        ).item
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@protected_router.post("/review/items/{review_item_id}/reject", response_model=ReviewItem)
def reject_review_item(
    review_item_id: str,
    decision: ReviewDecision,
    principal: Principal = Depends(require_principal),
) -> ReviewItem:
    require_roles(principal, settings.reviewer_role_set)
    try:
        return application.reject_review(review_item_id, decision, principal=principal)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@protected_router.post(
    "/review/items/{review_item_id}/request-changes",
    response_model=ReviewItem,
)
def request_review_changes(
    review_item_id: str,
    decision: ReviewDecision,
    principal: Principal = Depends(require_principal),
) -> ReviewItem:
    require_roles(principal, settings.reviewer_role_set)
    try:
        return application.request_changes(
            review_item_id,
            decision,
            principal=principal,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@protected_router.post("/review/items/{review_item_id}/revise", response_model=ReviewItem)
def revise_review_item(
    review_item_id: str,
    request: ReviewRevisionRequest,
    principal: Principal = Depends(require_principal),
) -> ReviewItem:
    require_roles(principal, {"submitter", "reviewer", "governance_admin"})
    try:
        return application.revise_review(review_item_id, request, principal=principal)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@protected_router.get("/brain/objects", response_model=list[KnowledgeObject])
def list_brain_objects(
    domain: str | None = None,
    principal: Principal = Depends(require_principal),
) -> list[KnowledgeObject]:
    return [
        obj
        for obj in application.store.list_objects(domain=domain)
        if application.access_policy.can_access(principal, obj)
    ]


@protected_router.get("/brain/objects/{object_id}", response_model=KnowledgeObject)
def get_brain_object(
    object_id: str,
    principal: Principal = Depends(require_principal),
) -> KnowledgeObject:
    obj = application.store.knowledge_objects.get(object_id)
    if obj is None or not application.access_policy.can_access(principal, obj):
        raise HTTPException(
            status_code=404,
            detail=f"Knowledge object not found: {object_id}",
        )
    return obj


@protected_router.get("/brain/graph", response_model=BrainGraph)
def get_brain_graph(
    include_review_items: bool = True,
    principal: Principal = Depends(require_principal),
) -> BrainGraph:
    return graph_service.build(
        include_review_items=include_review_items,
        access_policy=application.access_policy,
        principal=principal,
    )


@protected_router.post("/brain/context-pack", response_model=ContextPack)
def build_context_pack(
    request: ContextPackRequest,
    principal: Principal = Depends(require_principal),
) -> ContextPack:
    return application.build_context_pack(request, principal=principal)


@protected_router.get("/brain/context-packs/{context_pack_id}", response_model=ContextPack)
def get_context_pack(
    context_pack_id: str,
    principal: Principal = Depends(require_principal),
) -> ContextPack:
    pack = application.store.context_packs.get(context_pack_id)
    if pack is None:
        raise HTTPException(
            status_code=404,
            detail=f"Context pack not found: {context_pack_id}",
        )
    return pack


@protected_router.get("/governance/audit", response_model=list[AuditEvent])
def list_audit_events(
    principal: Principal = Depends(require_principal),
) -> list[AuditEvent]:
    require_roles(principal, {"reviewer", "governance_admin"})
    return list(reversed(application.store.audit_events))


app.include_router(public_router)
app.include_router(protected_router)
app.include_router(ingestion_router)
app.include_router(search_router)
