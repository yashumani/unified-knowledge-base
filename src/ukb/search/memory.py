from __future__ import annotations

import math
import re
from collections import Counter

from ukb.models import utc_now
from ukb.search.base import SearchDocument, SearchHit, SearchIndexStatus, SearchRequest


class MemorySearchIndex:
    """Deterministic lexical index used for tests and safe fallback mode."""

    name = "memory"

    def __init__(self, *, requested_backend: str = "memory", fallback_reason: str | None = None):
        self.requested_backend = requested_backend
        self.fallback_reason = fallback_reason
        self.documents: dict[str, SearchDocument] = {}
        self.last_synced_at = None

    def rebuild(self, documents: list[SearchDocument]) -> SearchIndexStatus:
        self.documents = {document.id: document for document in documents}
        self.last_synced_at = utc_now()
        return self.status()

    def search(self, request: SearchRequest) -> list[SearchHit]:
        query_tokens = self._tokens(request.query)
        normalized_query = self._normalize(request.query)
        domain_filter = {value.casefold() for value in request.domains}
        type_filter = {value.casefold() for value in request.object_types}
        sensitivity_filter = {value.value for value in request.sensitivities}
        hits: list[SearchHit] = []

        document_frequencies = Counter()
        for document in self.documents.values():
            document_frequencies.update(set(self._tokens(document.search_text)))
        corpus_size = max(len(self.documents), 1)

        for document in self.documents.values():
            if domain_filter and document.domain.casefold() not in domain_filter:
                continue
            if type_filter and document.object_type.casefold() not in type_filter:
                continue
            if sensitivity_filter and document.sensitivity not in sensitivity_filter:
                continue

            score, reasons = self._score(
                request=request,
                document=document,
                query_tokens=query_tokens,
                normalized_query=normalized_query,
                document_frequencies=document_frequencies,
                corpus_size=corpus_size,
            )
            if score > 0:
                hits.append(
                    SearchHit(
                        object_id=document.id,
                        score=round(score, 6),
                        engine=self.name,
                        reasons=reasons,
                    )
                )

        hits.sort(key=lambda hit: (-hit.score, hit.object_id))
        return hits[: request.limit]

    def status(self) -> SearchIndexStatus:
        return SearchIndexStatus(
            backend_requested=self.requested_backend,
            backend_active=self.name,
            available=True,
            document_count=len(self.documents),
            fallback_reason=self.fallback_reason,
            last_synced_at=self.last_synced_at,
            details={"ranking": "deterministic lexical BM25-inspired"},
        )

    def close(self) -> None:
        return None

    def _score(
        self,
        *,
        request: SearchRequest,
        document: SearchDocument,
        query_tokens: list[str],
        normalized_query: str,
        document_frequencies: Counter[str],
        corpus_size: int,
    ) -> tuple[float, list[str]]:
        title = self._normalize(document.title)
        aliases = {self._normalize(alias) for alias in document.aliases}
        content_tokens = self._tokens(document.search_text)
        token_counts = Counter(content_tokens)
        reasons: list[str] = []
        score = 0.0

        if normalized_query == document.id.casefold():
            score += 100.0
            reasons.append("exact_object_id")
        if normalized_query == title:
            score += 80.0
            reasons.append("exact_title")
        if normalized_query in aliases:
            score += 70.0
            reasons.append("exact_alias")
        if normalized_query and normalized_query in title:
            score += 12.0
            reasons.append("title_phrase")

        document_length = max(len(content_tokens), 1)
        average_length = max(
            sum(len(self._tokens(item.search_text)) for item in self.documents.values())
            / max(len(self.documents), 1),
            1.0,
        )
        for token in query_tokens:
            frequency = token_counts[token]
            if not frequency:
                continue
            document_frequency = document_frequencies[token]
            inverse_document_frequency = math.log(
                1 + (corpus_size - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            normalization = frequency + 1.2 * (1 - 0.75 + 0.75 * document_length / average_length)
            score += inverse_document_frequency * (frequency * 2.2 / normalization)
            if token in self._tokens(document.title):
                score += 3.0
                reasons.append(f"title_term:{token}")

        if score > 0 and not reasons:
            reasons.append("lexical_match")
        return score, sorted(set(reasons))

    def _tokens(self, value: str) -> list[str]:
        return [token for token in re.findall(r"[\w-]+", value.casefold()) if len(token) > 1]

    def _normalize(self, value: str) -> str:
        return " ".join(self._tokens(value))
