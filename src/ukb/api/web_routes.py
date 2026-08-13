from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ukb.ai.service import AIEnrichmentService
from ukb.config import get_settings
from ukb.connectors import (
    WebCaptureRequest,
    WebCaptureResponse,
    WebConnectorError,
    WebConnectorStatus,
    WebKnowledgeConnector,
)
from ukb.connectors.web_fetcher import HttpWebFetcher, RobotsAwareWebFetcher, WebFetcher
from ukb.connectors.web_policy import WebUrlPolicy
from ukb.models import AuditEvent
from ukb.services.compiler import BrainCompiler
from ukb.storage.objects import LocalObjectStore
from ukb.store import store

settings = get_settings()
policy = WebUrlPolicy(
    allowed_hosts=settings.web_hosts,
    allowed_ports=settings.web_ports,
    allow_private_networks=settings.web_allow_private_networks,
)
http_fetcher = HttpWebFetcher(
    policy=policy,
    user_agent=settings.web_user_agent,
    timeout_seconds=settings.web_timeout_seconds,
    max_response_bytes=settings.web_max_response_bytes,
    max_redirects=settings.web_max_redirects,
)
fetcher: WebFetcher = (
    RobotsAwareWebFetcher(
        fetcher=http_fetcher,
        user_agent=settings.web_user_agent,
        fail_closed=settings.web_robots_fail_closed,
    )
    if settings.web_respect_robots
    else http_fetcher
)
connector = WebKnowledgeConnector(
    compiler=BrainCompiler(),
    object_store=LocalObjectStore.from_url(settings.object_store_url),
    fetcher=fetcher,
    policy=policy,
    max_extracted_chars=settings.max_extracted_chars,
)
ai_enrichment_service = AIEnrichmentService(settings=settings)

router = APIRouter(tags=["connectors"])


@router.get("/connectors/web/status", response_model=WebConnectorStatus)
def web_connector_status() -> WebConnectorStatus:
    ready = settings.web_connector_enabled and bool(settings.web_hosts)
    message = (
        "Web source capture is ready for configured hosts."
        if ready
        else "Enable the connector and configure UKB_WEB_ALLOWED_HOSTS before collecting URLs."
    )
    return WebConnectorStatus(
        enabled=settings.web_connector_enabled,
        ready=ready,
        allowed_hosts=settings.web_hosts,
        allowed_ports=settings.web_ports,
        allow_private_networks=settings.web_allow_private_networks,
        respect_robots=settings.web_respect_robots,
        robots_fail_closed=settings.web_robots_fail_closed,
        max_response_bytes=settings.web_max_response_bytes,
        user_agent=settings.web_user_agent,
        message=message,
    )


@router.post("/ingestion/web", response_model=WebCaptureResponse)
def capture_web_source(request: WebCaptureRequest) -> WebCaptureResponse:
    if not settings.web_connector_enabled:
        raise HTTPException(status_code=503, detail="The web connector is disabled.")
    try:
        result = connector.capture(request)
    except WebConnectorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result.review_item.ai_enrichment = ai_enrichment_service.enrich_source(
        source=result.source,
        content=result.source.content_excerpt,
        baseline_candidate=result.review_item.candidate_object,
    )
    store.add_source(result.source)
    store.add_review_item(result.review_item)
    store.add_audit_event(
        AuditEvent(
            event_type="web_submission_created",
            actor=request.submitted_by,
            target_id=result.review_item.id,
            details={
                "source_id": result.source.source_id,
                "domain": request.domain,
                "artifact": result.artifact.model_dump(mode="json"),
                "ai_provider": (
                    result.review_item.ai_enrichment.provider.value
                    if result.review_item.ai_enrichment
                    else None
                ),
            },
        )
    )
    return result
