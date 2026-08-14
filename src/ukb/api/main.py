from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ukb.ai.service import AIEnrichmentService
from ukb.api.security import require_api_token, warn_on_insecure_configuration
from ukb.config import get_settings
from ukb.models import (
    AIEnrichmentResult,
    AIProviderHealth,
    AIProviderStatus,
    AuditEvent,
    BrainGraph,
    ContextPack,
    ContextPackRequest,
    EmbeddingRequest,
    EmbeddingResponse,
    IngestionSubmission,
    KnowledgeObject,
    ReviewDecision,
    ReviewItem,
)
from ukb.services.access import AccessPolicyService
from ukb.services.compiler import BrainCompiler
from ukb.services.context_pack import ContextPackService
from ukb.services.governance import GovernanceService
from ukb.services.graph import BrainGraphService
from ukb.store import store

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    warn_on_insecure_configuration(settings)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Governed AI Brain starter platform with ingestion, review, and context-pack endpoints.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

access_policy = AccessPolicyService.from_settings(settings)
compiler = BrainCompiler()
governance = GovernanceService(store)
context_pack_service = ContextPackService(store, access_policy=access_policy)
graph_service = BrainGraphService(store)
ai_enrichment_service = AIEnrichmentService(settings=settings)

# Only liveness is unauthenticated. Everything else touches submitted context,
# unapproved candidates, provider infrastructure detail, or the audit trail.
public_router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(require_api_token)])


@public_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@protected_router.get("/ai/providers", response_model=AIProviderStatus)
def get_ai_provider_status() -> AIProviderStatus:
    return ai_enrichment_service.status()


@protected_router.get("/ai/health", response_model=AIProviderHealth)
def get_ai_provider_health() -> AIProviderHealth:
    return ai_enrichment_service.health()


@protected_router.post("/ai/embeddings", response_model=EmbeddingResponse)
def build_embeddings(request: EmbeddingRequest) -> EmbeddingResponse:
    return ai_enrichment_service.embed_texts(texts=request.texts, model=request.model)


@protected_router.post("/ingestion/submissions", response_model=ReviewItem)
def submit_context(submission: IngestionSubmission) -> ReviewItem:
    source, review_item = compiler.compile_submission(submission)
    review_item.ai_enrichment = ai_enrichment_service.enrich_source(
        source=source,
        content=submission.content,
        baseline_candidate=review_item.candidate_object,
    )
    store.add_source(source)
    store.add_review_item(review_item)
    enrichment = review_item.ai_enrichment
    store.add_audit_event(
        AuditEvent(
            event_type="submission_created",
            actor=submission.submitted_by,
            target_id=review_item.id,
            details={
                "source_id": source.source_id,
                "domain": submission.domain,
                "ai_enrichment_id": enrichment.id if enrichment else None,
                "ai_provider": enrichment.provider.value if enrichment else None,
            },
        )
    )
    return review_item


@protected_router.get("/review/queue", response_model=list[ReviewItem])
def list_review_queue() -> list[ReviewItem]:
    return governance.list_queue()


@protected_router.post("/review/items/{review_item_id}/enrich", response_model=ReviewItem)
def enrich_review_item(review_item_id: str) -> ReviewItem:
    try:
        review_item = store.review_items[review_item_id]
        source = store.sources[review_item.source_id]
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Review item or source not found: {review_item_id}"
        ) from exc

    review_item.ai_enrichment = ai_enrichment_service.enrich_source(
        source=source,
        content=source.content_excerpt,
        baseline_candidate=review_item.candidate_object,
    )
    store.add_audit_event(
        AuditEvent(
            event_type="ai_review_item_enriched",
            actor="ai_enrichment_service",
            target_id=review_item.id,
            details={
                "source_id": source.source_id,
                "ai_enrichment_id": review_item.ai_enrichment.id,
                "ai_provider": review_item.ai_enrichment.provider.value,
            },
        )
    )
    return review_item


@protected_router.get(
    "/review/items/{review_item_id}/ai-enrichment", response_model=AIEnrichmentResult
)
def get_review_item_ai_enrichment(review_item_id: str) -> AIEnrichmentResult:
    try:
        enrichment = store.review_items[review_item_id].ai_enrichment
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Review item not found: {review_item_id}"
        ) from exc
    if enrichment is None:
        raise HTTPException(
            status_code=404, detail=f"Review item has no AI enrichment: {review_item_id}"
        )
    return enrichment


@protected_router.post("/review/items/{review_item_id}/approve", response_model=ReviewItem)
def approve_review_item(review_item_id: str, decision: ReviewDecision) -> ReviewItem:
    try:
        return governance.approve(review_item_id, decision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@protected_router.post("/review/items/{review_item_id}/reject", response_model=ReviewItem)
def reject_review_item(review_item_id: str, decision: ReviewDecision) -> ReviewItem:
    try:
        return governance.reject(review_item_id, decision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@protected_router.post("/review/items/{review_item_id}/request-changes", response_model=ReviewItem)
def request_review_changes(review_item_id: str, decision: ReviewDecision) -> ReviewItem:
    try:
        return governance.request_changes(review_item_id, decision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@protected_router.get("/brain/objects", response_model=list[KnowledgeObject])
def list_brain_objects(
    domain: str | None = None,
    principal: str = Depends(require_api_token),
) -> list[KnowledgeObject]:
    return [
        obj
        for obj in store.list_objects(domain=domain)
        if access_policy.can_access(principal, obj)
    ]


@protected_router.get("/brain/objects/{object_id}", response_model=KnowledgeObject)
def get_brain_object(
    object_id: str,
    principal: str = Depends(require_api_token),
) -> KnowledgeObject:
    try:
        obj = store.knowledge_objects[object_id]
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Knowledge object not found: {object_id}"
        ) from exc
    if not access_policy.can_access(principal, obj):
        # 404 rather than 403: confirming the ID exists leaks that a restricted
        # object with this identifier is present.
        raise HTTPException(status_code=404, detail=f"Knowledge object not found: {object_id}")
    return obj


@protected_router.get("/brain/graph", response_model=BrainGraph)
def get_brain_graph(
    include_review_items: bool = True,
    principal: str = Depends(require_api_token),
) -> BrainGraph:
    return graph_service.build(
        include_review_items=include_review_items,
        access_policy=access_policy,
        principal=principal,
    )


@protected_router.post("/brain/context-pack", response_model=ContextPack)
def build_context_pack(
    request: ContextPackRequest,
    principal: str = Depends(require_api_token),
) -> ContextPack:
    # Clearance follows the authenticated principal, not request.user_id, so a
    # caller cannot widen their own access by relabelling the request body.
    pack = context_pack_service.build(request, principal=principal)
    # A denied pack has nothing groundable in it. Enriching anyway would replace
    # the denial guidance with "nothing matched", which misstates why the pack
    # is empty and sends the question to the model for no benefit.
    if pack.access_decision != "denied":
        pack = ai_enrichment_service.enrich_context_pack(context_pack=pack)
    store.add_audit_event(
        AuditEvent(
            event_type="context_pack_requested",
            actor=request.user_id,
            target_id=pack.context_pack_id,
            details={
                "question": request.question,
                "mode": request.mode,
                "principal": principal,
                "access_decision": pack.access_decision,
                "ai_guidance_added": bool(pack.ai_guidance),
            },
        )
    )
    return pack


@protected_router.get("/governance/audit", response_model=list[AuditEvent])
def list_audit_events() -> list[AuditEvent]:
    return store.audit_events


app.include_router(public_router)
app.include_router(protected_router)
