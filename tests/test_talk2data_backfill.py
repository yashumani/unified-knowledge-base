from __future__ import annotations

from ukb.api.security import Principal
from ukb.models import (
    KnowledgeObject,
    KnowledgeObjectType,
    ReviewStatus,
    Sensitivity,
)
from ukb.storage.memory import BrainStore
from ukb.talk2data.backfill import LegacyKnowledgeBackfill
from ukb.talk2data.graph import InMemoryTemporalGraphAdapter
from ukb.talk2data.models import MemoryStatus, MemoryType
from ukb.talk2data.service import Talk2DataService
from ukb.talk2data.store import InMemoryTalk2DataStore


def _principal() -> Principal:
    return Principal(
        subject="backfill.admin",
        tenant_id="tenant-backfill",
        roles=frozenset(
            {
                "consumer",
                "submitter",
                "reviewer",
                "publisher",
                "source_admin",
                "index_admin",
                "governance_admin",
            }
        ),
        clearance=Sensitivity.restricted,
        auth_method="test",
    )


def _service() -> Talk2DataService:
    return Talk2DataService(
        store=InMemoryTalk2DataStore(),
        graph=InMemoryTemporalGraphAdapter(),
    )


def test_backfill_is_idempotent_and_preserves_legacy_object() -> None:
    legacy = BrainStore()
    legacy_object = KnowledgeObject(
        id="obj_postpaid_churn",
        type=KnowledgeObjectType.metric,
        title="Postpaid Churn",
        summary="Approved postpaid churn definition.",
        domain="wireless",
        owner="Commercial Analytics",
        status=ReviewStatus.published,
        sensitivity=Sensitivity.internal,
        authority_tier=1,
        version=3,
        published_by="legacy.publisher",
    )
    legacy.publish_object(legacy_object)
    service = _service()
    backfill = LegacyKnowledgeBackfill(legacy_store=legacy, service=service)

    dry = backfill.run(principal=_principal(), dry_run=True)
    assert dry.migrated == 0
    assert dry.entries[0].action == "planned"

    first = backfill.run(principal=_principal(), dry_run=False)
    assert first.failed == 0
    assert first.migrated == 1
    assert "obj_postpaid_churn" in legacy.knowledge_objects
    assert len(service.store.episodes) == 1
    assert len(service.store.memories) == 1
    memory = next(iter(service.store.memories.values()))
    assert memory.memory_type == MemoryType.metric_context
    assert memory.status == MemoryStatus.published
    assert "legacy-object:obj_postpaid_churn" in memory.tags
    assert memory.content["legacy_object_id"] == "obj_postpaid_churn"

    second = backfill.run(principal=_principal(), dry_run=False)
    assert second.skipped == 1
    assert len(service.store.episodes) == 1
    assert len(service.store.memories) == 1


def test_ambiguous_legacy_type_is_not_silently_published() -> None:
    legacy = BrainStore()
    legacy.publish_object(
        KnowledgeObject(
            id="obj_unknown",
            type=KnowledgeObjectType.unknown,
            title="Unclassified Legacy Note",
            summary="A legacy object that needs a human mapping decision.",
            domain="general",
            status=ReviewStatus.published,
            sensitivity=Sensitivity.internal,
            published_by="legacy.publisher",
        )
    )
    service = _service()
    report = LegacyKnowledgeBackfill(
        legacy_store=legacy,
        service=service,
    ).run(principal=_principal(), dry_run=False)

    assert report.ambiguous == 1
    memory = next(iter(service.store.memories.values()))
    assert memory.memory_type == MemoryType.source_document
    assert memory.status == MemoryStatus.unverified
    assert memory.approved_by is None
