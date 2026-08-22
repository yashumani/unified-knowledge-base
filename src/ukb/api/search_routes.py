from __future__ import annotations

from fastapi import APIRouter, Depends

from ukb.api.security import Principal, require_principal, require_roles
from ukb.search import SearchIndexStatus, SearchRequest, SearchResponse
from ukb.services.runtime import application

router = APIRouter(tags=["search"])


@router.get("/search/status", response_model=SearchIndexStatus)
def search_status(
    principal: Principal = Depends(require_principal),
) -> SearchIndexStatus:
    require_roles(principal, {"consumer", "submitter", "reviewer", "publisher", "governance_admin"})
    return application.retrieval.status()


@router.post("/search/rebuild", response_model=SearchIndexStatus)
def rebuild_search(
    principal: Principal = Depends(require_principal),
) -> SearchIndexStatus:
    require_roles(principal, {"publisher", "governance_admin"})
    return application.rebuild_search()


@router.post("/brain/search", response_model=SearchResponse)
def search_brain(
    request: SearchRequest,
    principal: Principal = Depends(require_principal),
) -> SearchResponse:
    return application.search(request, principal=principal)
