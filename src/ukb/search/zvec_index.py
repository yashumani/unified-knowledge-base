from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ukb.models import utc_now
from ukb.search.base import SearchDocument, SearchHit, SearchIndexStatus, SearchRequest


class ZvecUnavailableError(RuntimeError):
    pass


class ZvecSearchIndex:
    """Local Zvec FTS projection. SQL and object storage remain authoritative."""

    name = "zvec"

    def __init__(self, *, path: str, collection_name: str = "ukb_approved_knowledge_v2"):
        try:
            import zvec  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ZvecUnavailableError("Install the UKB search extra to enable Zvec.") from exc
        self.zvec = zvec
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.document_count = 0
        self.indexed_ids: set[str] = set()
        self.last_synced_at: datetime | None = None
        self.last_error: str | None = None
        self.collection = self._open_or_create()

    def rebuild(self, documents: list[SearchDocument]) -> SearchIndexStatus:
        current_ids = {document.id for document in documents}
        try:
            stale_ids = sorted(self.indexed_ids - current_ids)
            if stale_ids:
                self.collection.delete(ids=stale_ids)
            if documents:
                self.collection.upsert([self._to_doc(document) for document in documents])
                self.collection.optimize()
            self.indexed_ids = current_ids
            self.document_count = len(documents)
            self.last_synced_at = utc_now()
            self.last_error = None
        except Exception as exc:
            self.last_error = str(exc)
            raise ZvecUnavailableError(f"Zvec rebuild failed: {exc}") from exc
        return self.status()

    def search(self, request: SearchRequest) -> list[SearchHit]:
        try:
            results = self.collection.query(
                queries=self.zvec.Query(
                    field_name="search_text",
                    fts=self.zvec.Fts(match_string=request.query),
                ),
                filter=self._filter(request),
                topk=min(request.limit * 8, 300),
                output_fields=["title", "object_id", "chunk_id", "document_kind", "authority_tier"],
            )
        except Exception as exc:
            self.last_error = str(exc)
            raise ZvecUnavailableError(f"Zvec query failed: {exc}") from exc

        query = self._normalize(request.query)
        hits: list[SearchHit] = []
        for result in results:
            fields = dict(result.fields or {})
            title = self._normalize(str(fields.get("title", "")))
            object_id = str(fields.get("object_id", ""))
            chunk_id = str(fields.get("chunk_id", "")).strip() or None
            reasons = ["zvec_fts"]
            if query == title:
                reasons.append("exact_title")
            if str(fields.get("document_kind", "")) == "evidence_chunk":
                reasons.append("evidence_chunk")
            authority = int(fields.get("authority_tier", 3) or 3)
            score = float(result.score or 0.0) + max(0, 6 - authority) * 0.02
            hits.append(
                SearchHit(
                    document_id=str(result.id),
                    object_id=object_id,
                    chunk_id=chunk_id,
                    score=score,
                    engine=self.name,
                    reasons=reasons,
                )
            )
        return hits[: min(request.limit * 6, 300)]

    def status(self) -> SearchIndexStatus:
        return SearchIndexStatus(
            backend_requested=self.name,
            backend_active=self.name,
            available=self.last_error is None,
            document_count=self.document_count,
            path=str(self.path),
            last_error=self.last_error,
            last_synced_at=self.last_synced_at,
            details={"mode": "full_text_and_scalar_filters", "schema_version": "2"},
        )

    def close(self) -> None:
        close = getattr(self.collection, "close", None)
        if callable(close):
            close()

    def _open_or_create(self) -> Any:
        option = self.zvec.CollectionOption(read_only=False, enable_mmap=True)
        if self.path.exists() and self.path.is_dir() and any(self.path.iterdir()):
            try:
                return self.zvec.open(path=str(self.path), option=option)
            except Exception as exc:
                raise ZvecUnavailableError(
                    "Existing Zvec collection cannot be opened with schema v2; move it aside and rebuild."
                ) from exc

        fields = [
            self.zvec.FieldSchema("object_id", self.zvec.DataType.STRING, nullable=False),
            self.zvec.FieldSchema("chunk_id", self.zvec.DataType.STRING, nullable=False),
            self.zvec.FieldSchema("document_kind", self.zvec.DataType.STRING, nullable=False),
            self.zvec.FieldSchema("title", self.zvec.DataType.STRING, nullable=False),
            self.zvec.FieldSchema("summary", self.zvec.DataType.STRING, nullable=False),
            self.zvec.FieldSchema(
                "search_text",
                self.zvec.DataType.STRING,
                nullable=False,
                index_param=self.zvec.FtsIndexParam(
                    tokenizer_name="standard",
                    filters=["lowercase", "ascii_folding"],
                ),
            ),
        ]
        for name in ["domain", "object_type", "sensitivity", "review_status", "document_kind"]:
            fields.append(
                self.zvec.FieldSchema(
                    name,
                    self.zvec.DataType.STRING,
                    nullable=False,
                    index_param=self.zvec.InvertIndexParam(),
                )
            )
        fields.extend(
            [
                self.zvec.FieldSchema("authority_tier", self.zvec.DataType.INT32, nullable=False),
                self.zvec.FieldSchema("source_ids_json", self.zvec.DataType.STRING, nullable=False),
                self.zvec.FieldSchema("aliases_json", self.zvec.DataType.STRING, nullable=False),
                self.zvec.FieldSchema("updated_at", self.zvec.DataType.STRING, nullable=False),
            ]
        )
        schema = self.zvec.CollectionSchema(name=self.collection_name, fields=fields)
        return self.zvec.create_and_open(path=str(self.path), schema=schema, option=option)

    def _to_doc(self, document: SearchDocument) -> Any:
        return self.zvec.Doc(
            id=document.id,
            fields={
                "object_id": document.object_id,
                "chunk_id": document.chunk_id or "",
                "document_kind": document.document_kind,
                "title": document.title,
                "summary": document.summary,
                "search_text": document.search_text,
                "domain": document.domain,
                "object_type": document.object_type,
                "sensitivity": document.sensitivity,
                "review_status": document.status,
                "authority_tier": document.authority_tier,
                "source_ids_json": json.dumps(document.source_ids),
                "aliases_json": json.dumps(document.aliases),
                "updated_at": document.updated_at.isoformat(),
            },
        )

    @staticmethod
    def _filter(request: SearchRequest) -> str:
        clauses = ["review_status = 'published'"]
        for name, values in [
            ("domain", request.domains),
            ("object_type", request.object_types),
            ("sensitivity", [value.value for value in request.sensitivities]),
        ]:
            if values:
                quoted = ", ".join("'" + value.replace("'", "''") + "'" for value in values)
                clauses.append(f"{name} in ({quoted})")
        return " and ".join(clauses)

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().split())
