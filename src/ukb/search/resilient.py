from __future__ import annotations

from ukb.search.base import SearchDocument, SearchHit, SearchIndex, SearchIndexStatus, SearchRequest
from ukb.search.memory import MemorySearchIndex


class ResilientSearchIndex:
    """Keep deterministic retrieval available when the local index fails."""

    name = "resilient"

    def __init__(
        self,
        *,
        requested_backend: str,
        primary: SearchIndex | None,
        fallback: MemorySearchIndex,
        startup_error: str | None = None,
    ):
        self.requested_backend = requested_backend
        self.primary = primary
        self.fallback = fallback
        self.last_error = startup_error

    def rebuild(self, documents: list[SearchDocument]) -> SearchIndexStatus:
        self.fallback.rebuild(documents)
        if self.primary is not None:
            try:
                self.primary.rebuild(documents)
                self.last_error = None
            except Exception as exc:
                self.last_error = str(exc)
        return self.status()

    def search(self, request: SearchRequest) -> list[SearchHit]:
        if self.primary is not None and self.last_error is None:
            try:
                return self.primary.search(request)
            except Exception as exc:
                self.last_error = str(exc)
        return self.fallback.search(request)

    def status(self) -> SearchIndexStatus:
        if self.primary is not None and self.last_error is None:
            status = self.primary.status()
            status.backend_requested = self.requested_backend
            return status
        status = self.fallback.status()
        status.backend_requested = self.requested_backend
        status.fallback_reason = self.last_error or status.fallback_reason
        status.last_error = self.last_error
        status.details = {**status.details, "primary_backend": getattr(self.primary, "name", None)}
        return status

    def close(self) -> None:
        if self.primary is not None:
            self.primary.close()
        self.fallback.close()
