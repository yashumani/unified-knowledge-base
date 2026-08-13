from __future__ import annotations

from fastapi import APIRouter

from ukb.models import AuditEvent
from ukb.search import SearchIndexStatus, SearchRequest, SearchResponse
from ukb.services.runtime import retrieval_service
from ukb.store import store

router = APIRouter(tags=["search"])


@router.get("/search/status", response_model=SearchIndexStatus)
def search_status() -> SearchIndexStatus:
    return retrieval_service.status()


@router.post("/search/rebuild", response_model=SearchIndexStatus)
def rebuild_search_index() -> SearchIndexStatus:
    status = retrieval_service.rebuild()
    store.add_audit_event(
        AuditEvent(
            event_type="search_index_rebuilt",
            actor="search_admin",
            details={
                "backend": status.backend_active,
                "document_count": status.document_count,
                "fallback_reason": status.fallback_reason,
            },
        )
    )
    return status


@router.post("/brain/search", response_model=SearchResponse)
def search_brain(request: SearchRequest) -> SearchResponse:
    response = retrieval_service.search_response(request)
    store.add_audit_event(
        AuditEvent(
            event_type="brain_searched",
            actor=request.user_id,
            details={
                "query": request.query,
                "domains": request.domains,
                "result_ids": [result.object.id for result in response.results],
                "backend": response.index.backend_active,
            },
        )
    )
    return response
