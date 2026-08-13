from __future__ import annotations

from ukb.config import Settings, get_settings
from ukb.models import KnowledgeObject, ReviewStatus
from ukb.search import SearchIndex, SearchIndexStatus, SearchRequest, SearchResponse, SearchResult, build_search_index
from ukb.search.base import approved_documents
from ukb.store import BrainStore


class RetrievalService:
    """Retrieve only published knowledge through a rebuildable local index."""

    def __init__(self, store: BrainStore, *, settings: Settings | None = None, index: SearchIndex | None = None):
        self.store = store
        self.settings = settings or get_settings()
        self.index = index or build_search_index(self.settings)
        self._sync_key: tuple[tuple[str, str], ...] | None = None

    def search(self, query: str, domains: list[str] | None = None, limit: int = 5) -> list[KnowledgeObject]:
        response = self.search_response(SearchRequest(query=query, domains=domains or [], limit=limit))
        return [result.object for result in response.results]

    def search_response(self, request: SearchRequest) -> SearchResponse:
        self._ensure_synced()
        results: list[SearchResult] = []
        for hit in self.index.search(request):
            obj = self.store.knowledge_objects.get(hit.object_id)
            if obj is None or obj.status != ReviewStatus.published:
                continue
            results.append(SearchResult(hit=hit, object=obj))
            if len(results) >= request.limit:
                break
        return SearchResponse(query=request.query, results=results, index=self.index.status())

    def rebuild(self) -> SearchIndexStatus:
        objects = list(self.store.knowledge_objects.values())
        status = self.index.rebuild(approved_documents(objects))
        self._sync_key = self._key(objects)
        return status

    def status(self) -> SearchIndexStatus:
        return self.index.status()

    def close(self) -> None:
        self.index.close()

    def _ensure_synced(self) -> None:
        if not self.settings.search_sync_on_query:
            return
        objects = list(self.store.knowledge_objects.values())
        key = self._key(objects)
        if key != self._sync_key:
            self.index.rebuild(approved_documents(objects))
            self._sync_key = key

    def _key(self, objects: list[KnowledgeObject]) -> tuple[tuple[str, str], ...]:
        return tuple(sorted((obj.id, obj.updated_at.isoformat()) for obj in objects))
