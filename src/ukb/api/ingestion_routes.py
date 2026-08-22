from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from ukb.api.security import Principal, require_principal, require_roles
from ukb.connectors.crawl4ai import Crawl4AIConnector, Crawl4AIConnectorError
from ukb.connectors.google_drive import GoogleDriveConnector, GoogleDriveConnectorError
from ukb.ingestion_models import (
    BatchIngestionResult,
    ConnectorIngestionRequest,
    CrawlIngestionRequest,
    DriveIngestionRequest,
    IngestionCapabilities,
    IngestionCapability,
    IngestionGovernance,
    IngestionPreview,
    IngestionSourceMode,
)
from ukb.models import EvidenceChunk, Sensitivity, SourceEvidence, SourceVersion
from ukb.plugins.registry import registry
from ukb.services.ingestion import SUPPORTED_EXTENSIONS, IngestionParserService, RawIngestionItem
from ukb.services.runtime import application, settings

router = APIRouter(tags=["ingestion"])
parser = IngestionParserService(
    max_file_bytes=settings.max_upload_bytes,
    max_batch_files=settings.max_batch_files,
    max_archive_bytes=settings.max_archive_bytes,
    max_archive_uncompressed_bytes=settings.max_archive_uncompressed_bytes,
)
drive_connector = GoogleDriveConnector(settings)
crawl_connector = Crawl4AIConnector(settings)


def _formats() -> list[str]:
    return sorted({extension.lstrip(".").upper() for extension in SUPPORTED_EXTENSIONS})


def _plugin_configured(source_type: str) -> bool:
    for plugin in registry.source_connectors.values():
        try:
            if plugin.can_handle(source_type=source_type, source_uri=None):
                return True
        except Exception:
            continue
    return False


@router.get("/ingestion/capabilities", response_model=IngestionCapabilities)
def ingestion_capabilities(
    principal: Principal = Depends(require_principal),
) -> IngestionCapabilities:
    require_roles(principal, {"submitter", "reviewer", "governance_admin"})
    formats = _formats()
    git_ready = _plugin_configured("git")
    object_store_ready = _plugin_configured("object_store")
    return IngestionCapabilities(
        capabilities=[
            IngestionCapability(
                id=IngestionSourceMode.text,
                enabled=True,
                configured=True,
                formats=["TEXT"],
                message="Direct context submission is available.",
            ),
            IngestionCapability(
                id=IngestionSourceMode.files,
                enabled=True,
                configured=True,
                formats=formats,
                message="Multi-file preview and governed submission are available.",
            ),
            IngestionCapability(
                id=IngestionSourceMode.folder,
                enabled=True,
                configured=True,
                formats=formats,
                message="Folder paths are preserved in the source manifest.",
            ),
            IngestionCapability(
                id=IngestionSourceMode.zip,
                enabled=True,
                configured=True,
                formats=["ZIP", *formats],
                message="ZIP archives are inspected with traversal and expansion limits.",
            ),
            IngestionCapability(
                id=IngestionSourceMode.google_drive,
                enabled=settings.google_drive_enabled,
                configured=bool(settings.google_drive_enabled and settings.google_drive_access_token),
                formats=formats,
                message=(
                    "Google Drive is connected through a server-side token."
                    if settings.google_drive_enabled and settings.google_drive_access_token
                    else "Enable Drive and configure UKB_GOOGLE_DRIVE_ACCESS_TOKEN on the backend."
                ),
            ),
            IngestionCapability(
                id=IngestionSourceMode.crawl4ai,
                enabled=settings.crawl4ai_enabled,
                configured=bool(settings.crawl4ai_enabled and settings.web_hosts),
                formats=["MARKDOWN", "HTML"],
                message=(
                    "Crawl4AI is available for allowlisted hosts."
                    if settings.crawl4ai_enabled and settings.web_hosts
                    else "Enable Crawl4AI and configure UKB_WEB_ALLOWED_HOSTS."
                ),
            ),
            IngestionCapability(
                id=IngestionSourceMode.git,
                enabled=git_ready,
                configured=git_ready,
                formats=formats,
                message=(
                    "An installed UKB connector plugin handles Git repositories."
                    if git_ready
                    else "Install a source-connector plugin that declares Git support."
                ),
            ),
            IngestionCapability(
                id=IngestionSourceMode.object_store,
                enabled=object_store_ready,
                configured=object_store_ready,
                formats=formats,
                message=(
                    "An installed UKB connector plugin handles object containers."
                    if object_store_ready
                    else "Install a source-connector plugin that declares object-store support."
                ),
            ),
        ],
        max_batch_files=settings.max_batch_files,
        max_file_bytes=settings.max_upload_bytes,
        max_archive_bytes=settings.max_archive_bytes,
    )


@router.post("/ingestion/files/preview", response_model=IngestionPreview)
async def preview_files(
    files: Annotated[list[UploadFile], File(...)],
    relative_paths: Annotated[str, Form()] = "[]",
    source_mode: Annotated[IngestionSourceMode, Form()] = IngestionSourceMode.files,
    principal: Principal = Depends(require_principal),
) -> IngestionPreview:
    require_roles(principal, {"submitter", "reviewer", "governance_admin"})
    items = await _upload_items(files, relative_paths, source_mode)
    try:
        preview, _ = parser.preview(items, source_mode=source_mode, connector="file-upload")
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return preview


@router.post("/ingestion/files/submit", response_model=BatchIngestionResult)
async def submit_files(
    files: Annotated[list[UploadFile], File(...)],
    relative_paths: Annotated[str, Form()] = "[]",
    title: Annotated[str, Form()] = "Knowledge batch",
    submitted_by: Annotated[str, Form()] = "ui.ingestion",
    domain: Annotated[str, Form()] = "general",
    owner: Annotated[str, Form()] = "",
    sensitivity: Annotated[Sensitivity, Form()] = Sensitivity.internal,
    tags: Annotated[str, Form()] = "",
    effective_date: Annotated[str, Form()] = "",
    parser_mode: Annotated[str, Form()] = "layout-aware",
    chunking: Annotated[str, Form()] = "heading-and-table",
    duplicate_policy: Annotated[str, Form()] = "new-version",
    quality_mode: Annotated[str, Form()] = "flag-sensitive",
    source_mode: Annotated[IngestionSourceMode, Form()] = IngestionSourceMode.files,
    principal: Principal = Depends(require_principal),
) -> BatchIngestionResult:
    require_roles(principal, {"submitter", "reviewer", "governance_admin"})
    items = await _upload_items(files, relative_paths, source_mode)
    try:
        preview, parsed = parser.preview(items, source_mode=source_mode, connector="file-upload")
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    governance = IngestionGovernance(
        title=title,
        submitted_by=submitted_by,
        domain=domain,
        owner=owner or None,
        sensitivity=sensitivity,
        tags=_tags(tags),
        effective_date=effective_date or None,
        parser_mode=parser_mode,
        chunking=chunking,
        duplicate_policy=duplicate_policy,
        quality_mode=quality_mode,
    )
    batch = application.submit_parsed_batch(
        governance=governance,
        source_mode=source_mode,
        parsed_items=parsed,
        principal=principal,
    )
    return BatchIngestionResult(
        status="review_created" if batch.review_items else "blocked",
        source_mode=source_mode,
        preview=preview,
        review_items=batch.review_items,
        message=(
            f"Created {len(batch.review_items)} governed review candidate(s)."
            if batch.review_items
            else "No source passed deterministic validation."
        ),
    )


@router.post("/ingestion/google-drive/preview", response_model=IngestionPreview)
def preview_drive(
    request: DriveIngestionRequest,
    principal: Principal = Depends(require_principal),
) -> IngestionPreview:
    require_roles(principal, {"submitter", "reviewer", "governance_admin"})
    collection = _drive_collection(request)
    preview, _ = parser.preview(
        collection.items,
        source_mode=IngestionSourceMode.google_drive,
        connector="google-drive",
    )
    preview.warnings.extend(collection.warnings)
    return preview


@router.post("/ingestion/google-drive/submit", response_model=BatchIngestionResult)
def submit_drive(
    request: DriveIngestionRequest,
    principal: Principal = Depends(require_principal),
) -> BatchIngestionResult:
    require_roles(principal, {"submitter", "reviewer", "governance_admin"})
    collection = _drive_collection(request)
    preview, parsed = parser.preview(
        collection.items,
        source_mode=IngestionSourceMode.google_drive,
        connector="google-drive",
    )
    preview.warnings.extend(collection.warnings)
    batch = application.submit_parsed_batch(
        governance=request,
        source_mode=IngestionSourceMode.google_drive,
        parsed_items=parsed,
        principal=principal,
    )
    return BatchIngestionResult(
        status="review_created" if batch.review_items else "blocked",
        source_mode=IngestionSourceMode.google_drive,
        preview=preview,
        review_items=batch.review_items,
        message=f"Created {len(batch.review_items)} Drive-backed review candidate(s).",
    )


@router.post("/ingestion/crawl4ai/preview", response_model=IngestionPreview)
def preview_crawl(
    request: CrawlIngestionRequest,
    principal: Principal = Depends(require_principal),
) -> IngestionPreview:
    require_roles(principal, {"submitter", "reviewer", "governance_admin"})
    collection = _crawl_collection(request)
    preview, _ = parser.preview(
        collection.items,
        source_mode=IngestionSourceMode.crawl4ai,
        connector="crawl4ai",
    )
    preview.warnings.extend(collection.warnings)
    if collection.discovered_links:
        preview.preview_markdown += "\n\n## Discovered links\n\n" + "\n".join(
            f"- {link}" for link in collection.discovered_links[:50]
        )
    return preview


@router.post("/ingestion/crawl4ai/submit", response_model=BatchIngestionResult)
def submit_crawl(
    request: CrawlIngestionRequest,
    principal: Principal = Depends(require_principal),
) -> BatchIngestionResult:
    require_roles(principal, {"submitter", "reviewer", "governance_admin"})
    collection = _crawl_collection(request)
    preview, parsed = parser.preview(
        collection.items,
        source_mode=IngestionSourceMode.crawl4ai,
        connector="crawl4ai",
    )
    preview.warnings.extend(collection.warnings)
    batch = application.submit_parsed_batch(
        governance=request,
        source_mode=IngestionSourceMode.crawl4ai,
        parsed_items=parsed,
        principal=principal,
    )
    return BatchIngestionResult(
        status="review_created" if batch.review_items else "blocked",
        source_mode=IngestionSourceMode.crawl4ai,
        preview=preview,
        review_items=batch.review_items,
        message=f"Created {len(batch.review_items)} Crawl4AI-backed review candidate(s).",
    )


@router.post("/ingestion/connectors/preview", response_model=IngestionPreview)
def preview_connector(
    request: ConnectorIngestionRequest,
    principal: Principal = Depends(require_principal),
) -> IngestionPreview:
    require_roles(principal, {"submitter", "reviewer", "governance_admin"})
    items, warnings, plugin_name = _plugin_items(request)
    mode = IngestionSourceMode(request.connector_type)
    preview, _ = parser.preview(items, source_mode=mode, connector=f"plugin:{plugin_name}")
    preview.warnings.extend(warnings)
    return preview


@router.post("/ingestion/connectors/submit", response_model=BatchIngestionResult)
def submit_connector(
    request: ConnectorIngestionRequest,
    principal: Principal = Depends(require_principal),
) -> BatchIngestionResult:
    require_roles(principal, {"submitter", "reviewer", "governance_admin"})
    items, warnings, plugin_name = _plugin_items(request)
    mode = IngestionSourceMode(request.connector_type)
    preview, parsed = parser.preview(items, source_mode=mode, connector=f"plugin:{plugin_name}")
    preview.warnings.extend(warnings)
    batch = application.submit_parsed_batch(
        governance=request,
        source_mode=mode,
        parsed_items=parsed,
        principal=principal,
    )
    return BatchIngestionResult(
        status="review_created" if batch.review_items else "blocked",
        source_mode=mode,
        preview=preview,
        review_items=batch.review_items,
        message=f"Created {len(batch.review_items)} plugin-backed review candidate(s).",
    )


@router.get("/sources", response_model=list[SourceEvidence])
def list_sources(
    domain: str | None = None,
    principal: Principal = Depends(require_principal),
) -> list[SourceEvidence]:
    sources = list(application.store.sources.values())
    if domain:
        sources = [source for source in sources if source.domain == domain]
    return [
        source
        for source in sources
        if application.access_policy.can_access_sensitivity(principal, source.sensitivity)
    ]


@router.get("/sources/{source_id}", response_model=SourceEvidence)
def get_source(
    source_id: str,
    principal: Principal = Depends(require_principal),
) -> SourceEvidence:
    source = application.store.sources.get(source_id)
    if source is None or not application.access_policy.can_access_sensitivity(principal, source.sensitivity):
        raise HTTPException(status_code=404, detail=f"Source not found: {source_id}")
    return source


@router.get("/sources/{source_id}/versions", response_model=list[SourceVersion])
def source_versions(
    source_id: str,
    principal: Principal = Depends(require_principal),
) -> list[SourceVersion]:
    get_source(source_id, principal)
    return application.store.list_source_versions(source_id)


@router.get("/sources/{source_id}/chunks", response_model=list[EvidenceChunk])
def source_chunks(
    source_id: str,
    principal: Principal = Depends(require_principal),
) -> list[EvidenceChunk]:
    get_source(source_id, principal)
    return [
        chunk
        for chunk in application.store.list_evidence_chunks(source_id=source_id)
        if application.access_policy.can_access_sensitivity(principal, chunk.sensitivity)
    ]


async def _upload_items(
    files: list[UploadFile],
    relative_paths: str,
    source_mode: IngestionSourceMode,
) -> list[RawIngestionItem]:
    if len(files) > settings.max_batch_files:
        raise HTTPException(status_code=413, detail="The batch exceeds the configured file-count limit.")
    try:
        paths = json.loads(relative_paths or "[]")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="relative_paths must be a JSON array.") from exc
    if not isinstance(paths, list):
        raise HTTPException(status_code=400, detail="relative_paths must be a JSON array.")
    items: list[RawIngestionItem] = []
    total = 0
    read_limit = settings.max_archive_bytes if source_mode == IngestionSourceMode.zip else settings.max_upload_bytes
    for index, upload in enumerate(files):
        data = await upload.read(read_limit + 1)
        await upload.close()
        if len(data) > read_limit:
            raise HTTPException(status_code=413, detail=f"{upload.filename} exceeds the configured size limit.")
        total += len(data)
        if total > settings.max_archive_uncompressed_bytes:
            raise HTTPException(status_code=413, detail="The submitted batch exceeds the configured total-byte limit.")
        path = str(paths[index]) if index < len(paths) and str(paths[index]).strip() else (upload.filename or f"file-{index}")
        items.append(
            RawIngestionItem(
                name=upload.filename or f"file-{index}",
                path=path,
                data=data,
                content_type=upload.content_type or "application/octet-stream",
            )
        )
    return items


def _tags(raw: str) -> list[str]:
    return [value.strip() for value in raw.split(",") if value.strip()]


def _drive_collection(request: DriveIngestionRequest):
    try:
        return drive_connector.collect(request)
    except GoogleDriveConnectorError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _crawl_collection(request: CrawlIngestionRequest):
    try:
        return crawl_connector.collect(request)
    except Crawl4AIConnectorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _plugin_items(request: ConnectorIngestionRequest) -> tuple[list[RawIngestionItem], list[str], str]:
    plugin = registry.find_source_connector(request.connector_type, request.location)
    if plugin is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                f"No installed source-connector plugin handles {request.connector_type!r} at "
                f"{request.location!r}. No memory was created."
            ),
        )
    try:
        result = plugin.ingest(request.model_dump(mode="json"))
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Connector plugin {plugin.manifest.name!r} failed: {type(exc).__name__}: {exc}",
        ) from exc

    candidates: list[dict[str, Any]] = []
    candidates.extend(item for item in result.evidence if isinstance(item, dict))
    candidates.extend(item for item in result.items if isinstance(item, dict))
    items: list[RawIngestionItem] = []
    warnings = list(result.warnings)
    for index, candidate in enumerate(candidates):
        raw_content = candidate.get("content") or candidate.get("text") or candidate.get("body")
        if isinstance(raw_content, str):
            data = raw_content.encode("utf-8")
        elif isinstance(raw_content, bytes):
            data = raw_content
        else:
            warnings.append(f"Plugin item {index + 1} had no text or byte content and was skipped.")
            continue
        name = str(candidate.get("name") or candidate.get("title") or f"plugin-item-{index + 1}.txt")
        path = str(candidate.get("path") or name)
        items.append(
            RawIngestionItem(
                name=name,
                path=path,
                data=data,
                content_type=str(candidate.get("content_type") or "text/plain"),
                source_uri=str(candidate.get("source_uri") or request.location),
            )
        )
    if not items:
        raise HTTPException(
            status_code=422,
            detail=f"Connector plugin {plugin.manifest.name!r} returned no parsable evidence.",
        )
    return items, warnings, plugin.manifest.name
