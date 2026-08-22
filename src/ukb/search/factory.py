from __future__ import annotations

from ukb.config import Settings
from ukb.search.base import SearchIndex
from ukb.search.memory import MemorySearchIndex
from ukb.search.resilient import ResilientSearchIndex
from ukb.search.zvec_index import ZvecSearchIndex


def build_search_index(settings: Settings) -> SearchIndex:
    backend = settings.search_backend.casefold().strip()
    fallback = MemorySearchIndex(requested_backend=backend)
    if backend != "zvec":
        return fallback
    try:
        zvec_index = ZvecSearchIndex(
            path=settings.zvec_path,
            collection_name=settings.zvec_collection_name,
        )
    except RuntimeError as error:
        return ResilientSearchIndex(
            requested_backend=backend,
            primary=None,
            fallback=fallback,
            startup_error=str(error),
        )
    return ResilientSearchIndex(
        requested_backend=backend,
        primary=zvec_index,
        fallback=fallback,
    )
