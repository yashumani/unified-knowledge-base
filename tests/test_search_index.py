from pathlib import Path

import pytest

from ukb.config import Settings
from ukb.models import KnowledgeObject, KnowledgeObjectType, ReviewStatus, Sensitivity
from ukb.search import SearchDocument, SearchRequest
from ukb.search.memory import MemorySearchIndex
from ukb.search.zvec_index import ZvecSearchIndex
from ukb.services.retrieval import RetrievalService
from ukb.storage.memory import BrainStore


def knowledge_object(object_id: str, title: str, *, domain: str = "support", aliases: list[str] | None = None) -> KnowledgeObject:
    return KnowledgeObject(
        id=object_id,
        type=KnowledgeObjectType.metric,
        title=title,
        summary=f"Approved definition for {title}.",
        domain=domain,
        status=ReviewStatus.published,
        sensitivity=Sensitivity.internal,
        attributes={"aliases": aliases or [], "raw_excerpt": f"{title} is governed context."},
        confidence=0.9,
    )


def test_memory_search_ranks_exact_alias_and_applies_filters() -> None:
    index = MemorySearchIndex()
    first = knowledge_object("support.metric.resolution_time", "Incident Resolution Time", aliases=["IRT"])
    second = knowledge_object("operations.metric.queue_time", "Queue Time", domain="operations")
    index.rebuild([SearchDocument.from_object(first), SearchDocument.from_object(second)])
    hits = index.search(SearchRequest(query="IRT", domains=["support"], limit=5))
    assert [hit.object_id for hit in hits] == [first.id]
    assert "exact_alias" in hits[0].reasons


def test_retrieval_service_indexes_only_published_objects() -> None:
    store = BrainStore()
    published = knowledge_object("support.metric.published", "Published Metric")
    draft = knowledge_object("support.metric.draft", "Draft Metric")
    draft.status = ReviewStatus.ai_classified
    store.publish_object(published)
    store.knowledge_objects[draft.id] = draft
    service = RetrievalService(store, settings=Settings(search_backend="memory", search_sync_on_query=True))
    results = service.search("metric", domains=["support"], limit=10)
    assert [item.id for item in results] == [published.id]
    assert service.status().document_count == 1


def test_zvec_full_text_round_trip(tmp_path: Path) -> None:
    pytest.importorskip("zvec")
    index = ZvecSearchIndex(path=str(tmp_path / "approved-knowledge"))
    first = knowledge_object("support.metric.resolution_time", "Incident Resolution Time")
    second = knowledge_object("support.metric.response_time", "First Response Time")
    try:
        index.rebuild([SearchDocument.from_object(first), SearchDocument.from_object(second)])
        hits = index.search(SearchRequest(query="resolution", domains=["support"], limit=5))
    finally:
        index.close()
    assert hits
    assert hits[0].object_id == first.id
    assert hits[0].engine == "zvec"
