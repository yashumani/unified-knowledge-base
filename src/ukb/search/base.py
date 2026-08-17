from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field

from ukb.models import EvidenceChunk, KnowledgeObject, ReviewStatus, Sensitivity, utc_now


class SearchDocument(BaseModel):
    """Approved knowledge or evidence projected into a rebuildable index."""

    id: str
    object_id: str
    chunk_id: str | None = None
    document_kind: str = "knowledge_object"
    title: str
    summary: str
    search_text: str
    domain: str
    object_type: str
    sensitivity: str
    status: str
    source_ids: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    authority_tier: int = 3
    updated_at: datetime

    @classmethod
    def from_object(cls, obj: KnowledgeObject) -> SearchDocument:
        raw_aliases = obj.aliases or obj.attributes.get("aliases", [])
        aliases = (
            [str(value).strip() for value in raw_aliases if str(value).strip()]
            if isinstance(raw_aliases, list)
            else []
        )
        owner = obj.owner or ""
        attributes = " ".join(
            f"{key} {value}"
            for key, value in obj.attributes.items()
            if key not in {"raw_excerpt"}
        )
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
                attributes,
            ]
            if part
        )
        return cls(
            id=f"object:{obj.id}",
            object_id=obj.id,
            title=obj.title,
            summary=obj.summary,
            search_text=search_text,
            domain=obj.domain,
            object_type=obj.type.value,
            sensitivity=obj.sensitivity.value,
            status=obj.status.value,
            source_ids=obj.source_ids,
            aliases=aliases,
            authority_tier=obj.authority_tier,
            updated_at=obj.updated_at,
        )

    @classmethod
    def from_chunk(cls, obj: KnowledgeObject, chunk: EvidenceChunk) -> SearchDocument:
        heading = " > ".join(chunk.heading_path)
        return cls(
            id=f"chunk:{obj.id}:{chunk.id}",
            object_id=obj.id,
            chunk_id=chunk.id,
            document_kind="evidence_chunk",
            title=obj.title,
            summary=heading or chunk.locator or obj.summary,
            search_text="\n".join(part for part in [obj.title, heading, chunk.content] if part),
            domain=obj.domain,
            object_type=obj.type.value,
            sensitivity=chunk.sensitivity.value,
            status=obj.status.value,
            source_ids=[chunk.source_id],
            aliases=obj.aliases,
            authority_tier=obj.authority_tier,
            updated_at=max(obj.updated_at, chunk.created_at),
        )


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    user_id: str = "anonymous"
    domains: list[str] = Field(default_factory=list)
    object_types: list[str] = Field(default_factory=list)
    sensitivities: list[Sensitivity] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=50)


class SearchHit(BaseModel):
    document_id: str
    object_id: str
    chunk_id: str | None = None
    score: float
    engine: str
    reasons: list[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    hit: SearchHit
    object: KnowledgeObject
    evidence_chunk: EvidenceChunk | None = None


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
    denied_count: int = 0
    index: SearchIndexStatus


class SearchIndex(Protocol):
    name: str

    def rebuild(self, documents: list[SearchDocument]) -> SearchIndexStatus:
        ...

    def search(self, request: SearchRequest) -> list[SearchHit]:
        ...

    def status(self) -> SearchIndexStatus:
        ...

    def close(self) -> None:
        ...


def approved_documents(
    objects: list[KnowledgeObject],
    chunks: list[EvidenceChunk] | None = None,
) -> list[SearchDocument]:
    chunk_list = chunks or []
    documents: list[SearchDocument] = []
    for obj in objects:
        if obj.status != ReviewStatus.published:
            continue
        documents.append(SearchDocument.from_object(obj))
        referenced_ids = {reference.chunk_id for reference in obj.evidence_refs}
        for chunk in chunk_list:
            if chunk.id in referenced_ids or chunk.source_id in obj.source_ids:
                documents.append(SearchDocument.from_chunk(obj, chunk))
    return documents
