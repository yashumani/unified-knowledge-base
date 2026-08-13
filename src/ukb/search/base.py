from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field

from ukb.models import KnowledgeObject, ReviewStatus, Sensitivity, utc_now


class SearchDocument(BaseModel):
    """Approved knowledge projected into a rebuildable retrieval document."""

    id: str
    title: str
    summary: str
    search_text: str
    domain: str
    object_type: str
    sensitivity: str
    status: str
    source_ids: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    updated_at: datetime

    @classmethod
    def from_object(cls, obj: KnowledgeObject) -> "SearchDocument":
        aliases_value = obj.attributes.get("aliases", [])
        aliases = (
            [str(value).strip() for value in aliases_value if str(value).strip()]
            if isinstance(aliases_value, list)
            else []
        )
        raw_excerpt = str(obj.attributes.get("raw_excerpt", "")).strip()
        owner = obj.owner or ""
        search_text = "\n".join(
            part
            for part in [
                obj.title,
                obj.title,
                obj.summary,
                owner,
                obj.type.value,
                obj.domain,
                " ".join(aliases),
                raw_excerpt,
            ]
            if part
        )
        return cls(
            id=obj.id,
            title=obj.title,
            summary=obj.summary,
            search_text=search_text,
            domain=obj.domain,
            object_type=obj.type.value,
            sensitivity=obj.sensitivity.value,
            status=obj.status.value,
            source_ids=obj.source_ids,
            aliases=aliases,
            updated_at=obj.updated_at,
        )


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    user_id: str = "anonymous"
    domains: list[str] = Field(default_factory=list)
    object_types: list[str] = Field(default_factory=list)
    sensitivities: list[Sensitivity] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=50)


class SearchHit(BaseModel):
    object_id: str
    score: float
    engine: str
    reasons: list[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    hit: SearchHit
    object: KnowledgeObject


class SearchIndexStatus(BaseModel):
    backend_requested: str
    backend_active: str
    available: bool
    document_count: int = 0
    path: str | None = None
    supports_full_text: bool = True
    supports_vectors: bool = False
    fallback_reason: str | None = None
    last_error: str | None = None
    last_synced_at: datetime | None = None
    checked_at: datetime = Field(default_factory=utc_now)
    details: dict[str, object] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult] = Field(default_factory=list)
    index: SearchIndexStatus


class SearchIndex(Protocol):
    name: str

    def rebuild(self, documents: list[SearchDocument]) -> SearchIndexStatus:
        """Replace the derived index contents with approved documents."""
        ...

    def search(self, request: SearchRequest) -> list[SearchHit]:
        """Return ranked candidate identifiers without bypassing governance."""
        ...

    def status(self) -> SearchIndexStatus:
        """Return index readiness and fallback information."""
        ...

    def close(self) -> None:
        """Release local index resources."""
        ...


def approved_documents(objects: list[KnowledgeObject]) -> list[SearchDocument]:
    return [
        SearchDocument.from_object(obj)
        for obj in objects
        if obj.status == ReviewStatus.published
    ]
