from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ukb.ai.service import AIEnrichmentService
from ukb.config import get_settings
from ukb.ingestion import FileIngestionError, FileIngestionResponse, FileIngestionService
from ukb.models import AuditEvent, Sensitivity, SourceEvidence
from ukb.services.compiler import BrainCompiler
from ukb.storage.objects import LocalObjectStore
from ukb.store import store

settings = get_settings()
compiler = BrainCompiler()
ai_enrichment_service = AIEnrichmentService(settings=settings)
file_ingestion_service = FileIngestionService(
    compiler=compiler,
    object_store=LocalObjectStore.from_url(settings.object_store_url),
    max_upload_bytes=settings.max_upload_bytes,
    max_extracted_chars=settings.max_extracted_chars,
)

router = APIRouter(tags=["ingestion"])


@router.post("/ingestion/files", response_model=FileIngestionResponse)
async def submit_file(
    file: UploadFile = File(...),
    submitted_by: str = Form(...),
    domain: str = Form("general"),
    sensitivity: Sensitivity = Form(Sensitivity.internal),
    title: str | None = Form(None),
    tags: str = Form(""),
) -> FileIngestionResponse:
    data = await file.read(settings.max_upload_bytes + 1)
    await file.close()
    try:
        parsed = file_ingestion_service.ingest(
            filename=file.filename or "uploaded-source.txt",
            media_type=file.content_type,
            data=data,
            submitted_by=submitted_by,
            domain=domain,
            sensitivity=sensitivity,
            title=title,
            tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
        )
    except FileIngestionError as exc:
        status_code = 413 if len(data) > settings.max_upload_bytes else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    parsed.review_item.ai_enrichment = ai_enrichment_service.enrich_source(
        source=parsed.source,
        content=parsed.extracted_text,
        baseline_candidate=parsed.review_item.candidate_object,
    )
    store.add_source(parsed.source)
    store.add_review_item(parsed.review_item)
    store.add_audit_event(
        AuditEvent(
            event_type="file_submission_created",
            actor=submitted_by,
            target_id=parsed.review_item.id,
            details={
                "source_id": parsed.source.source_id,
                "domain": domain,
                "artifact": parsed.artifact.model_dump(mode="json"),
                "ai_provider": (
                    parsed.review_item.ai_enrichment.provider.value
                    if parsed.review_item.ai_enrichment
                    else None
                ),
            },
        )
    )
    return FileIngestionResponse(
        source=parsed.source,
        review_item=parsed.review_item,
        artifact=parsed.artifact,
    )


@router.get("/sources", response_model=list[SourceEvidence])
def list_sources(domain: str | None = None) -> list[SourceEvidence]:
    sources = list(store.sources.values())
    if domain:
        return [source for source in sources if source.domain == domain]
    return sources


@router.get("/sources/{source_id}", response_model=SourceEvidence)
def get_source(source_id: str) -> SourceEvidence:
    try:
        return store.sources[source_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Source not found: {source_id}") from exc
