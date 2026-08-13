from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ukb.ai.service import AIEnrichmentService
from ukb.config import get_settings
from ukb.models import (
    AIEnrichmentResult,
    AIProviderStatus,
    AuditEvent,
    BrainGraph,
    ContextPack,
    ContextPackRequest,
    IngestionSubmission,
    KnowledgeObject,
    ReviewDecision,
    ReviewItem,
)
from ukb.services.compiler import BrainCompiler
from ukb.services.context_pack import ContextPackService
from ukb.services.governance import GovernanceService
from ukb.services.graph import BrainGraphService
from ukb.store import store

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Governed AI Brain starter platform with ingestion, review, and context-pack endpoints.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

compiler = BrainCompiler()
governance = GovernanceService(store)
context_pack_service = ContextPackService(store)
graph_service = BrainGraphService(store)
ai_enrichment_service = AIEnrichmentService(settings=settings)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@app.get("/ai/providers", response_model=AIProviderStatus)
def get_ai_provider_status() -> AIProviderStatus:
    return ai_enrichment_service.status()


@app.post("/ingestion/submissions", response_model=ReviewItem)
def submit_context(submission: IngestionSubmission) -> ReviewItem:
    source, review_item = compiler.compile_submission(submission)
    review_item.ai_enrichment = ai_enrichment_service.enrich_source(
        source=source,
        content=submission.content,
        baseline_candidate=review_item.candidate_object,
    )
    store.add_source(source)
    store.add_review_item(review_item)
    store.add_audit_event(
        AuditEvent(
            event_type="submission_created",
            actor=submission.submitted_by,
            target_id=review_item.id,
            details={
                "source_id": source.source_id,
                "domain": submission.domain,
                "ai_enrichment_id": review_item.ai_enrichment.id if review_item.ai_enrichment else None,
                "ai_provider": review_item.ai_enrichment.provider.value if review_item.ai_enrichment else None,
            },
        )
    )
    return review_item


@app.get("/review/queue", response_model=list[ReviewItem])
def list_review_queue() -> list[ReviewItem]:
    return governance.list_queue()


@app.post("/review/items/{review_item_id}/enrich", response_model=ReviewItem)
def enrich_review_item(review_item_id: str) -> ReviewItem:
    try:
        review_item = store.review_items[review_item_id]
        source = store.sources[review_item.source_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Review item or source not found: {review_item_id}") from exc

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


@app.get("/review/items/{review_item_id}/ai-enrichment", response_model=AIEnrichmentResult)
def get_review_item_ai_enrichment(review_item_id: str) -> AIEnrichmentResult:
    try:
        enrichment = store.review_items[review_item_id].ai_enrichment
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Review item not found: {review_item_id}") from exc
    if enrichment is None:
        raise HTTPException(status_code=404, detail=f"Review item has no AI enrichment: {review_item_id}")
    return enrichment


@app.post("/review/items/{review_item_id}/approve", response_model=ReviewItem)
def approve_review_item(review_item_id: str, decision: ReviewDecision) -> ReviewItem:
    try:
        return governance.approve(review_item_id, decision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/review/items/{review_item_id}/reject", response_model=ReviewItem)
def reject_review_item(review_item_id: str, decision: ReviewDecision) -> ReviewItem:
    try:
        return governance.reject(review_item_id, decision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/review/items/{review_item_id}/request-changes", response_model=ReviewItem)
def request_review_changes(review_item_id: str, decision: ReviewDecision) -> ReviewItem:
    try:
        return governance.request_changes(review_item_id, decision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/brain/objects", response_model=list[KnowledgeObject])
def list_brain_objects(domain: str | None = None) -> list[KnowledgeObject]:
    return store.list_objects(domain=domain)


@app.get("/brain/objects/{object_id}", response_model=KnowledgeObject)
def get_brain_object(object_id: str) -> KnowledgeObject:
    try:
        return store.knowledge_objects[object_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Knowledge object not found: {object_id}") from exc


@app.get("/brain/graph", response_model=BrainGraph)
def get_brain_graph(include_review_items: bool = True) -> BrainGraph:
    return graph_service.build(include_review_items=include_review_items)


@app.post("/brain/context-pack", response_model=ContextPack)
def build_context_pack(request: ContextPackRequest) -> ContextPack:
    pack = context_pack_service.build(request)
    pack = ai_enrichment_service.enrich_context_pack(context_pack=pack)
    store.add_audit_event(
        AuditEvent(
            event_type="context_pack_requested",
            actor=request.user_id,
            target_id=pack.context_pack_id,
            details={
                "question": request.question,
                "mode": request.mode,
                "ai_guidance_added": bool(pack.ai_guidance),
            },
        )
    )
    return pack


@app.get("/governance/audit", response_model=list[AuditEvent])
def list_audit_events() -> list[AuditEvent]:
    return store.audit_events
