from __future__ import annotations

from ukb.config import Settings, get_settings
from ukb.models import KnowledgeObject, ReviewStatus, Sensitivity
from ukb.search import (
    SearchHit,
    SearchIndex,
    SearchIndexStatus,
    SearchRequest,
    SearchResponse,
    SearchResult,
    build_search_index,
)
from ukb.search.base import approved_documents
from ukb.services.access import AccessPolicyService, PrincipalLike
from ukb.storage.memory import BrainStore


class RetrievalService:
    """Permission-aware retrieval over a rebuildable local search index."""

    def __init__(
        self,
        store: BrainStore,
        *,
        settings: Settings | None = None,
        index: SearchIndex | None = None,
        access_policy: AccessPolicyService | None = None,
    ):
        self.store = store
        self.settings = settings or get_settings()
        self.index = index or build_search_index(self.settings)
        self.access_policy = access_policy or AccessPolicyService.from_settings(
            self.settings
        )
        self._sync_key: tuple[tuple[str, str], ...] | None = None

    def search(
        self,
        query: str,
        domains: list[str] | None = None,
        limit: int = 5,
        user_id: str = "anonymous",
    ) -> list[KnowledgeObject]:
        response = self.search_response(
            SearchRequest(
                query=query,
                domains=domains or [],
                limit=limit,
                user_id=user_id,
            ),
            principal=user_id,
        )
        return [result.object for result in response.results]

    def search_response(
        self,
        request: SearchRequest,
        *,
        principal: str | PrincipalLike,
    ) -> SearchResponse:
        self._ensure_synced()

        # Search the caller-requested partitions first, then enforce clearance
        # before any object or evidence content is returned. This preserves the
        # ability to distinguish "nothing matched" from "matching memory was
        # withheld" without exposing the withheld object's identifiers or text.
        effective = request.model_copy(
            update={
                "sensitivities": (
                    list(request.sensitivities)
                    if request.sensitivities
                    else list(Sensitivity)
                )
            }
        )

        candidates: list[SearchHit] = self._exact_hits(effective)
        candidates.extend(self.index.search(effective))
        candidates.sort(key=lambda hit: (-hit.score, hit.document_id))

        results: list[SearchResult] = []
        seen_objects: set[str] = set()
        denied_objects: set[str] = set()
        for hit in candidates:
            if hit.object_id in seen_objects or hit.object_id in denied_objects:
                continue
            obj = self.store.knowledge_objects.get(hit.object_id)
            if obj is None or obj.status != ReviewStatus.published:
                continue
            if not self.access_policy.can_access(principal, obj):
                denied_objects.add(obj.id)
                continue
            chunk = self.store.evidence_chunks.get(hit.chunk_id) if hit.chunk_id else None
            if chunk is not None and not self.access_policy.can_access_sensitivity(
                principal, chunk.sensitivity
            ):
                denied_objects.add(obj.id)
                continue
            results.append(SearchResult(hit=hit, object=obj, evidence_chunk=chunk))
            seen_objects.add(obj.id)
            if len(results) >= request.limit:
                break

        return SearchResponse(
            query=request.query,
            results=results,
            denied_count=len(denied_objects),
            index=self.index.status(),
        )

    def rebuild(self) -> SearchIndexStatus:
        objects = list(self.store.knowledge_objects.values())
        chunks = list(self.store.evidence_chunks.values())
        status = self.index.rebuild(approved_documents(objects, chunks))
        self._sync_key = self._key(objects, chunks)
        return status

    def status(self) -> SearchIndexStatus:
        return self.index.status()

    def close(self) -> None:
        self.index.close()

    def _ensure_synced(self) -> None:
        if not self.settings.search_sync_on_query:
            return
        objects = list(self.store.knowledge_objects.values())
        chunks = list(self.store.evidence_chunks.values())
        key = self._key(objects, chunks)
        if key != self._sync_key:
            self.index.rebuild(approved_documents(objects, chunks))
            self._sync_key = key

    def _exact_hits(self, request: SearchRequest) -> list[SearchHit]:
        query = " ".join(request.query.casefold().split())
        hits: list[SearchHit] = []
        domain_filter = {value.casefold() for value in request.domains}
        type_filter = {value.casefold() for value in request.object_types}
        sensitivity_filter = {value.value for value in request.sensitivities}
        for obj in self.store.knowledge_objects.values():
            if obj.status != ReviewStatus.published:
                continue
            if domain_filter and obj.domain.casefold() not in domain_filter:
                continue
            if type_filter and obj.type.value.casefold() not in type_filter:
                continue
            if sensitivity_filter and obj.sensitivity.value not in sensitivity_filter:
                continue
            title = " ".join(obj.title.casefold().split())
            aliases = {" ".join(alias.casefold().split()) for alias in obj.aliases}
            score = 0.0
            reasons: list[str] = []
            if query == obj.id.casefold():
                score = 150.0
                reasons.append("exact_object_id")
            elif query == title:
                score = 130.0
                reasons.append("exact_title")
            elif query in aliases:
                score = 120.0
                reasons.append("exact_alias")
            if score:
                hits.append(
                    SearchHit(
                        document_id=f"object:{obj.id}",
                        object_id=obj.id,
                        score=score,
                        engine="authoritative_exact",
                        reasons=reasons,
                    )
                )
        return hits

    @staticmethod
    def _key(
        objects: list[KnowledgeObject],
        chunks: list,
    ) -> tuple[tuple[str, str], ...]:
        object_keys = [
            (f"obj:{obj.id}", obj.updated_at.isoformat()) for obj in objects
        ]
        chunk_keys = [
            (f"chunk:{chunk.id}", chunk.content_hash) for chunk in chunks
        ]
        return tuple(sorted([*object_keys, *chunk_keys]))
