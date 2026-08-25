from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime

from ukb.models import utc_now
from ukb.search.base import SearchDocument, SearchHit, SearchIndexStatus, SearchRequest


class MemorySearchIndex:
    """Deterministic BM25-inspired lexical index and safe Zvec fallback."""

    name = "memory"

    def __init__(self, *, requested_backend: str = "memory", fallback_reason: str | None = None):
        self.requested_backend = requested_backend
        self.fallback_reason = fallback_reason
        self.documents: dict[str, SearchDocument] = {}
        self.last_synced_at: datetime | None = None

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

        document_frequencies: Counter[str] = Counter()
        tokenized = {doc.id: self._tokens(doc.search_text) for doc in self.documents.values()}
        for tokens in tokenized.values():
            document_frequencies.update(set(tokens))
        corpus_size = max(len(self.documents), 1)
        average_length = max(sum(len(tokens) for tokens in tokenized.values()) / corpus_size, 1.0)

        for document in self.documents.values():
            if domain_filter and document.domain.casefold() not in domain_filter:
                continue
            if type_filter and document.object_type.casefold() not in type_filter:
                continue
            if sensitivity_filter and document.sensitivity not in sensitivity_filter:
                continue

            score, reasons = self._score(
                document=document,
                query_tokens=query_tokens,
                normalized_query=normalized_query,
                document_frequencies=document_frequencies,
                corpus_size=corpus_size,
                content_tokens=tokenized[document.id],
                average_length=average_length,
            )
            if score > 0:
                hits.append(
                    SearchHit(
                        document_id=document.id,
                        object_id=document.object_id,
                        chunk_id=document.chunk_id,
                        score=round(score, 6),
                        engine=self.name,
                        reasons=reasons,
                    )
                )

        hits.sort(key=lambda hit: (-hit.score, hit.document_id))
        return hits[: min(request.limit * 6, 300)]

    def status(self) -> SearchIndexStatus:
        return SearchIndexStatus(
            backend_requested=self.requested_backend,
            backend_active=self.name,
            available=True,
            document_count=len(self.documents),
            fallback_reason=self.fallback_reason,
            last_synced_at=self.last_synced_at,
            details={"ranking": "BM25-inspired lexical + exact identifiers + authority"},
        )

    def close(self) -> None:
        return None

    def _score(
        self,
        *,
        document: SearchDocument,
        query_tokens: list[str],
        normalized_query: str,
        document_frequencies: Counter[str],
        corpus_size: int,
        content_tokens: list[str],
        average_length: float,
    ) -> tuple[float, list[str]]:
        title = self._normalize(document.title)
        aliases = {self._normalize(alias) for alias in document.aliases}
        token_counts = Counter(content_tokens)
        reasons: list[str] = []
        score = 0.0
        matched = False

        if normalized_query in {document.object_id.casefold(), document.id.casefold()}:
            score += 120.0
            reasons.append("exact_object_id")
            matched = True
        if normalized_query == title:
            score += 90.0
            reasons.append("exact_title")
            matched = True
        if normalized_query in aliases:
            score += 80.0
            reasons.append("exact_alias")
            matched = True
        if normalized_query and normalized_query in title:
            score += 15.0
            reasons.append("title_phrase")
            matched = True

        document_length = max(len(content_tokens), 1)
        for token in query_tokens:
            frequency = token_counts[token]
            if not frequency:
                continue
            matched = True
            document_frequency = document_frequencies[token]
            inverse_document_frequency = math.log(
                1 + (corpus_size - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            normalization = frequency + 1.2 * (1 - 0.75 + 0.75 * document_length / average_length)
            score += inverse_document_frequency * (frequency * 2.2 / normalization)
            if token in self._tokens(document.title):
                score += 3.5
                reasons.append(f"title_term:{token}")

        if not matched:
            return 0.0, []
        reasons.append("lexical_match")
        if document.document_kind == "knowledge_object":
            score += 0.25
            reasons.append("object_summary")
        else:
            score += 0.1
            reasons.append("evidence_chunk")
        score += max(0, 6 - document.authority_tier) * 0.2
        return score, sorted(set(reasons))

    @staticmethod
    def _tokens(value: str) -> list[str]:
        return [token for token in re.findall(r"[\w-]+", value.casefold()) if len(token) > 1]

    def _normalize(self, value: str) -> str:
        return " ".join(self._tokens(value))
