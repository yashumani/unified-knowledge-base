from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from ukb.api.security import Principal, require_principal
from ukb.talk2data.models import (
    CanonicalEpisode,
    ContextCoverageReceipt,
    ContextCoverageRequest,
    DomainClassificationResult,
    DomainPackVersionList,
    DomainPackWriteResult,
    DomainQuestionRequest,
    EpisodeIngestionRequest,
    EpisodeIngestionResult,
    GovernedMemoryObject,
    GraphAdapterStatus,
    GraphRebuildResult,
    IndexWatermark,
    MemoryPromotionRequest,
    MemoryQuery,
    MemoryQueryResult,
    MemoryRelationship,
    MemorySupersessionRequest,
    MemorySupersessionResult,
    ObsidianPromotionRequest,
    ObsidianPromotionResult,
    ObsidianValidationRequest,
    ObsidianValidationResult,
    SourceIngestionHealth,
    Talk2DataAuditEvent,
    TenantDomainPack,
    TimelineRequest,
    VocabularyResolution,
    VocabularyResolutionRequest,
)
from ukb.talk2data.runtime import service
from ukb.talk2data.service import (
    Talk2DataAuthorizationError,
    Talk2DataConflictError,
    Talk2DataNotFoundError,
    Talk2DataValidationError,
)

router = APIRouter(prefix="/v1", tags=["Talk2Data domain and governed memory"])


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, Talk2DataAuthorizationError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, Talk2DataNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc).strip("'"))
    if isinstance(exc, Talk2DataConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, Talk2DataValidationError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error.")


@router.get("/domain-packs/current", response_model=TenantDomainPack)
def current_domain_pack(
    effective_at: datetime | None = None,
    principal: Principal = Depends(require_principal),
) -> TenantDomainPack:
    pack = service.current_domain_pack(principal=principal, effective_at=effective_at)
    if pack is None:
        raise HTTPException(status_code=404, detail="No approved current Domain Pack is available.")
    return pack


@router.get("/domain-packs/versions", response_model=DomainPackVersionList)
def domain_pack_versions(
    principal: Principal = Depends(require_principal),
) -> DomainPackVersionList:
    try:
        return DomainPackVersionList(domain_packs=service.list_domain_pack_versions(principal=principal))
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/domain-packs", response_model=DomainPackWriteResult, status_code=201)
def create_domain_pack(
    domain_pack: TenantDomainPack,
    principal: Principal = Depends(require_principal),
) -> DomainPackWriteResult:
    try:
        return service.create_domain_pack(domain_pack, principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/domain-packs/resolve", response_model=VocabularyResolution)
def resolve_vocabulary(
    request: VocabularyResolutionRequest,
    principal: Principal = Depends(require_principal),
) -> VocabularyResolution:
    try:
        return service.resolve_vocabulary(request.term, principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/domain-packs/classify", response_model=DomainClassificationResult)
def classify_question(
    request: DomainQuestionRequest,
    principal: Principal = Depends(require_principal),
) -> DomainClassificationResult:
    try:
        return service.classify_question(request.question, principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/memory/episodes", response_model=EpisodeIngestionResult, status_code=201)
def ingest_episode(
    request: EpisodeIngestionRequest,
    principal: Principal = Depends(require_principal),
) -> EpisodeIngestionResult:
    try:
        return service.ingest_episode(request, principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/memory/episodes/{episode_id}", response_model=CanonicalEpisode)
def get_episode(
    episode_id: str,
    principal: Principal = Depends(require_principal),
) -> CanonicalEpisode:
    episode = service.store.episodes.get(episode_id)
    if episode is None or episode.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=404, detail=f"Episode not found: {episode_id}")
    if episode.classification.value not in {"public", principal.clearance.value}:
        from ukb.services.access import SENSITIVITY_ORDER

        if SENSITIVITY_ORDER[episode.classification] > SENSITIVITY_ORDER[principal.clearance]:
            raise HTTPException(status_code=404, detail=f"Episode not found: {episode_id}")
    return episode


@router.post("/memory", response_model=GovernedMemoryObject, status_code=201)
def promote_memory(
    request: MemoryPromotionRequest,
    principal: Principal = Depends(require_principal),
) -> GovernedMemoryObject:
    try:
        return service.promote_memory(request, principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/memory/supersede", response_model=MemorySupersessionResult)
def supersede_memory(
    request: MemorySupersessionRequest,
    principal: Principal = Depends(require_principal),
) -> MemorySupersessionResult:
    try:
        return service.supersede_memory(request, principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/memory/relationships", response_model=MemoryRelationship, status_code=201)
def add_memory_relationship(
    relationship: MemoryRelationship,
    principal: Principal = Depends(require_principal),
) -> MemoryRelationship:
    try:
        return service.add_relationship(relationship, principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/memory/query", response_model=MemoryQueryResult)
def query_memory(
    request: MemoryQuery,
    principal: Principal = Depends(require_principal),
) -> MemoryQueryResult:
    try:
        return service.query_memory(request, principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/memory/query/graph", response_model=MemoryQueryResult)
def query_memory_with_graph(
    request: MemoryQuery,
    principal: Principal = Depends(require_principal),
) -> MemoryQueryResult:
    try:
        return service.query_memory_with_graph(request, principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/memory/timelines/entities", response_model=MemoryQueryResult)
def entity_timeline(
    request: TimelineRequest,
    principal: Principal = Depends(require_principal),
) -> MemoryQueryResult:
    try:
        return service.entity_timeline(request, principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/memory/timelines/metrics", response_model=MemoryQueryResult)
def metric_timeline(
    request: TimelineRequest,
    principal: Principal = Depends(require_principal),
) -> MemoryQueryResult:
    try:
        return service.metric_timeline(request, principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/memory/investigations", response_model=MemoryQueryResult)
def prior_investigations(
    request: MemoryQuery,
    principal: Principal = Depends(require_principal),
) -> MemoryQueryResult:
    try:
        return service.prior_investigations(request, principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/memory/source-health", response_model=list[SourceIngestionHealth])
def source_health(
    principal: Principal = Depends(require_principal),
) -> list[SourceIngestionHealth]:
    return service.list_source_health(principal=principal)


@router.put("/memory/source-health", response_model=SourceIngestionHealth)
def update_source_health(
    health: SourceIngestionHealth,
    principal: Principal = Depends(require_principal),
) -> SourceIngestionHealth:
    try:
        return service.upsert_source_health(health, principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/memory/index-watermarks", response_model=list[IndexWatermark])
def index_watermarks(
    principal: Principal = Depends(require_principal),
) -> list[IndexWatermark]:
    return service.list_index_watermarks(principal=principal)


@router.put("/memory/index-watermarks", response_model=IndexWatermark)
def update_index_watermark(
    watermark: IndexWatermark,
    principal: Principal = Depends(require_principal),
) -> IndexWatermark:
    try:
        return service.upsert_index_watermark(watermark, principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/memory/context-coverage", response_model=ContextCoverageReceipt)
def context_coverage(
    request: ContextCoverageRequest,
    principal: Principal = Depends(require_principal),
) -> ContextCoverageReceipt:
    try:
        return service.context_coverage(request, principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/obsidian/validate", response_model=ObsidianValidationResult)
def validate_obsidian(
    request: ObsidianValidationRequest,
    principal: Principal = Depends(require_principal),
) -> ObsidianValidationResult:
    del principal  # Authentication is required even though validation is read-only.
    return service.validate_obsidian(request.markdown)


@router.post("/obsidian/promote", response_model=ObsidianPromotionResult, status_code=201)
def promote_obsidian(
    request: ObsidianPromotionRequest,
    principal: Principal = Depends(require_principal),
) -> ObsidianPromotionResult:
    try:
        return service.promote_obsidian(request, principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/graph/status", response_model=GraphAdapterStatus)
def graph_status(
    principal: Principal = Depends(require_principal),
) -> GraphAdapterStatus:
    del principal
    return service.graph_status()


@router.post("/graph/rebuild", response_model=GraphRebuildResult)
def rebuild_graph(
    principal: Principal = Depends(require_principal),
) -> GraphRebuildResult:
    try:
        return service.rebuild_graph(principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/memory/audit", response_model=list[Talk2DataAuditEvent])
def memory_audit(
    principal: Principal = Depends(require_principal),
) -> list[Talk2DataAuditEvent]:
    try:
        return service.list_audit_events(principal=principal)
    except Exception as exc:
        raise _translate(exc) from exc
