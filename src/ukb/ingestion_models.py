from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from ukb.models import ReviewItem, Sensitivity, new_id, utc_now


class IngestionSourceMode(str, Enum):
    text = "text"
    files = "files"
    folder = "folder"
    zip = "zip"
    google_drive = "google_drive"
    crawl4ai = "crawl4ai"
    git = "git"
    object_store = "object_store"


class IngestionItemStatus(str, Enum):
    ready = "ready"
    warning = "warning"
    rejected = "rejected"


class IngestionPreviewItem(BaseModel):
    item_id: str = Field(default_factory=lambda: new_id("preview_item"))
    name: str
    path: str
    content_type: str
    size_bytes: int = 0
    status: IngestionItemStatus = IngestionItemStatus.ready
    extracted_chars: int = 0
    source_uri: str | None = None


class IngestionPreview(BaseModel):
    preview_id: str = Field(default_factory=lambda: new_id("preview"))
    source_mode: IngestionSourceMode
    ready: bool
    items: list[IngestionPreviewItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    rejected_items: list[str] = Field(default_factory=list)
    extracted_chars: int = 0
    preview_markdown: str = ""
    connector: str
    generated_at: datetime = Field(default_factory=utc_now)


class BatchIngestionResult(BaseModel):
    batch_id: str = Field(default_factory=lambda: new_id("batch"))
    status: Literal["previewed", "review_created", "partial", "blocked"]
    source_mode: IngestionSourceMode
    preview: IngestionPreview
    review_items: list[ReviewItem] = Field(default_factory=list)
    message: str


class IngestionCapability(BaseModel):
    id: IngestionSourceMode
    enabled: bool
    configured: bool
    formats: list[str] = Field(default_factory=list)
    message: str


class IngestionCapabilities(BaseModel):
    capabilities: list[IngestionCapability]
    max_batch_files: int
    max_file_bytes: int
    max_archive_bytes: int


class IngestionGovernance(BaseModel):
    title: str = Field(..., min_length=3)
    submitted_by: str = "ui.ingestion"
    domain: str = "general"
    owner: str | None = None
    sensitivity: Sensitivity = Sensitivity.internal
    tags: list[str] = Field(default_factory=list)
    effective_date: str | None = None
    parser_mode: str = "layout-aware"
    chunking: str = "heading-and-table"
    duplicate_policy: str = "new-version"
    quality_mode: str = "flag-sensitive"


class DriveIngestionRequest(IngestionGovernance):
    folder_url: str
    recursive: bool = True
    max_files: int = Field(default=100, ge=1, le=500)


class CrawlIngestionRequest(IngestionGovernance):
    url: HttpUrl
    max_pages: int = Field(default=8, ge=1, le=25)
    max_depth: int = Field(default=1, ge=0, le=3)
    render_javascript: bool = True
    respect_robots: bool = True
    content_filter: Literal["pruning", "bm25", "none"] = "pruning"


class ConnectorIngestionRequest(IngestionGovernance):
    connector_type: Literal["git", "object_store"]
    location: str
    profile: str = "default"
