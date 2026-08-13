from __future__ import annotations

from ukb.models import KnowledgeObject
from ukb.store import BrainStore


class RetrievalService:
    """Deterministic approved-object retrieval pending local index activation."""

    def __init__(self, store: BrainStore):
        self.store = store

    def search(self, query: str, domains: list[str] | None = None, limit: int = 5) -> list[KnowledgeObject]:
        normalized_query = query.lower()
        domain_filter = set(domains or [])
        candidates = []
        for obj in self.store.knowledge_objects.values():
            if domain_filter and obj.domain not in domain_filter:
                continue
            haystack = " ".join([obj.title, obj.summary, obj.type.value, obj.domain, str(obj.attributes)]).lower()
            score = self._score(normalized_query, haystack)
            if score > 0:
                candidates.append((score, obj))
        candidates.sort(key=lambda item: item[0], reverse=True)
        return [obj for _, obj in candidates[:limit]]

    def _score(self, query: str, haystack: str) -> int:
        terms = [term for term in query.split() if len(term) > 2]
        return sum(1 for term in terms if term in haystack)
