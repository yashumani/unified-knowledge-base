from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ukb.config import get_settings
from ukb.models import (
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@app.post("/ingestion/submissions", response_model=ReviewItem)
def submit_context(submission: IngestionSubmission) -> ReviewItem:
    source, review_item = compiler.compile_submission(submission)
    store.add_source(source)
    store.add_review_item(review_item)
    store.add_audit_event(
        AuditEvent(
            event_type="submission_created",
            actor=submission.submitted_by,
            target_id=review_item.id,
            details={"source_id": source.source_id, "domain": submission.domain},
        )
    )
    return review_item


@app.get("/review/queue", response_model=list[ReviewItem])
def list_review_queue() -> list[ReviewItem]:
    return governance.list_queue()


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
    store.add_audit_event(
        AuditEvent(
            event_type="context_pack_requested",
            actor=request.user_id,
            target_id=pack.context_pack_id,
            details={"question": request.question, "mode": request.mode},
        )
    )
    return pack


@app.get("/governance/audit", response_model=list[AuditEvent])
def list_audit_events() -> list[AuditEvent]:
    return store.audit_events
