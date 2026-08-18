from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI

from ukb.api.security import Principal
from ukb.models import Sensitivity
from ukb.talk2data.graph import (
    GraphitiClientProtocol,
    GraphitiTemporalGraphAdapter,
    InMemoryTemporalGraphAdapter,
)
from ukb.talk2data.models import (
    AuthorityLevel,
    ContextCoverageRequest,
    CoverageStatus,
    DomainFit,
    DomainPackStatus,
    EpisodeIngestionRequest,
    IndexStatus,
    IndexWatermark,
    MemoryPromotionRequest,
    MemoryProvenance,
    MemoryQuery,
    MemoryStatus,
    MemorySupersessionRequest,
    MemoryType,
    ObsidianPromotionRequest,
    SourceHealthStatus,
    SourceIngestionHealth,
    TenantDomainPack,
    TimelineRequest,
)
from ukb.talk2data.routes import router
from ukb.talk2data.service import (
    Talk2DataAuthorizationError,
    Talk2DataService,
    Talk2DataValidationError,
)
from ukb.talk2data.store import InMemoryTalk2DataStore, SqlAlchemyTalk2DataStore

UTC = timezone.utc
EXAMPLE_DIR = Path(__file__).parents[1] / "examples" / "talk2data-telecom"


def principal(
    tenant_id: str = "synthetic-telecom",
    *,
    roles: tuple[str, ...] = (
        "consumer",
        "submitter",
        "reviewer",
        "publisher",
        "domain_pack_admin",
        "source_admin",
        "index_admin",
        "auditor",
        "governance_admin",
    ),
    clearance: Sensitivity = Sensitivity.restricted,
    subject: str = "test.operator",
) -> Principal:
    return Principal(
        subject=subject,
        tenant_id=tenant_id,
        roles=frozenset(roles),
        clearance=clearance,
        auth_method="test",
    )


def load_pack() -> TenantDomainPack:
    raw = yaml.safe_load((EXAMPLE_DIR / "domain-pack.yaml").read_text(encoding="utf-8"))
    return TenantDomainPack.model_validate(raw)


def service_with_pack() -> tuple[Talk2DataService, Principal]:
    actor = principal()
    service = Talk2DataService(store=InMemoryTalk2DataStore())
    service.create_domain_pack(load_pack(), principal=actor)
    return service, actor


def ingest_episode(
    service: Talk2DataService,
    actor: Principal,
    *,
    source_id: str = "subscriber_metrics_catalog",
    content: str = "Postpaid churn is measured monthly by service plan.",
    classification: Sensitivity = Sensitivity.internal,
    idempotency_key: str | None = None,
):
    return service.ingest_episode(
        EpisodeIngestionRequest(
            tenant_id=actor.tenant_id,
            source_type="governed_catalog",
            source_id=source_id,
            title="Synthetic telecom source episode",
            raw_content=content,
            classification=classification,
            owner="Synthetic Domain Governance",
            idempotency_key=idempotency_key,
            effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        principal=actor,
    ).episode


def promote_memory(
    service: Talk2DataService,
    actor: Principal,
    *,
    episode=None,
    content: str = "Postpaid churn is the share of postpaid lines disconnected in the month.",
    memory_type: MemoryType = MemoryType.metric_context,
    status: MemoryStatus = MemoryStatus.published,
    classification: Sensitivity = Sensitivity.internal,
    allowed_roles: list[str] | None = None,
    related_metrics: list[str] | None = None,
    related_entities: list[str] | None = None,
    business_domain: str = "subscriber",
    effective_from: datetime | None = None,
    conflict_group_id: str | None = None,
):
    episode = episode or ingest_episode(service, actor)
    return service.promote_memory(
        MemoryPromotionRequest(
            tenant_id=actor.tenant_id,
            memory_type=memory_type,
            source_type=episode.source_type,
            source_id=episode.source_id,
            business_domain=business_domain,
            related_metrics=related_metrics or ["postpaid_churn_rate"],
            related_entities=related_entities or ["subscriber", "service_plan"],
            effective_from=effective_from or datetime(2026, 1, 1, tzinfo=UTC),
            status=status,
            classification=classification,
            access_policy_id="policy-telecom-metric-reader",
            allowed_roles=allowed_roles or [],
            authority_level=AuthorityLevel.authoritative,
            owner="Synthetic Subscriber Analytics",
            approved_by=actor.subject,
            content=content,
            provenance=MemoryProvenance(
                episode_id=episode.episode_id,
                source_checksum=episode.source_checksum,
                derived_by=actor.subject,
            ),
            conflict_group_id=conflict_group_id,
        ),
        principal=actor,
    )


def test_domain_pack_versioning_preserves_historical_effectivity() -> None:
    service, actor = service_with_pack()
    pack_v1 = service.current_domain_pack(
        principal=actor,
        effective_at=datetime(2026, 6, 1, tzinfo=UTC),
    )
    assert pack_v1 is not None and pack_v1.version == 1

    pack_v2 = load_pack().model_copy(
        update={
            "domain_pack_id": "domain_pack_synthetic_telecom_v2",
            "version": 2,
            "effective_from": datetime(2027, 1, 1, tzinfo=UTC),
            "status": DomainPackStatus.approved,
            "approved_by": "ignored-client-value",
        }
    )
    result = service.create_domain_pack(pack_v2, principal=actor)

    historical = service.current_domain_pack(
        principal=actor,
        effective_at=datetime(2026, 6, 1, tzinfo=UTC),
    )
    current = service.current_domain_pack(
        principal=actor,
        effective_at=datetime(2027, 2, 1, tzinfo=UTC),
    )
    assert result.superseded_domain_pack_id == pack_v1.domain_pack_id
    assert historical is not None and historical.version == 1
    assert historical.status == DomainPackStatus.superseded
    assert current is not None and current.version == 2
    assert current.approved_by == actor.subject


def test_vocabulary_resolution_handles_aliases_and_abbreviations() -> None:
    service, actor = service_with_pack()
    resolved = service.resolve_vocabulary("subscriber attrition", principal=actor)
    assert resolved.resolved is True
    assert resolved.canonical_term == "postpaid churn"
    assert resolved.concept_id == "postpaid_churn_rate"
    assert resolved.domain_pack_version == 1


def test_required_question_domain_classifications() -> None:
    service, actor = service_with_pack()
    cases = {
        "What was postpaid churn by plan last month?": DomainFit.in_domain,
        "What is our restaurant food-cost margin by location?": DomainFit.excluded,
        "Did restaurant foot traffic near our stores affect mobile activations?": DomainFit.external_adjacent,
        "Did food-delivery application traffic contribute to evening network congestion?": DomainFit.external_adjacent,
    }
    for question, expected in cases.items():
        result = service.classify_question(question, principal=actor)
        assert result.classification == expected, result.model_dump()


def test_external_subject_without_internal_anchor_is_not_adjacent() -> None:
    service, actor = service_with_pack()
    result = service.classify_question(
        "Did restaurant foot traffic increase last month?",
        principal=actor,
    )
    assert result.classification == DomainFit.unsupported
    assert result.matched_external_categories == ["restaurant_foot_traffic"]
    assert result.internal_anchors == []


def test_episode_ingestion_is_idempotent_and_checksum_protected() -> None:
    service, actor = service_with_pack()
    first = service.ingest_episode(
        EpisodeIngestionRequest(
            tenant_id=actor.tenant_id,
            source_type="governed_catalog",
            source_id="subscriber_metrics_catalog",
            title="Episode",
            raw_content="Postpaid churn by plan.",
            idempotency_key="episode-2026-01",
        ),
        principal=actor,
    )
    second = service.ingest_episode(
        EpisodeIngestionRequest(
            tenant_id=actor.tenant_id,
            source_type="governed_catalog",
            source_id="subscriber_metrics_catalog",
            title="Episode duplicate",
            raw_content="Different text is ignored because the idempotency key already exists.",
            idempotency_key="episode-2026-01",
        ),
        principal=actor,
    )
    assert first.duplicate is False
    assert second.duplicate is True
    assert second.duplicate_reason == "idempotency_key"
    assert second.episode.episode_id == first.episode.episode_id
    assert len(service.store.episodes) == 1

    with pytest.raises(Talk2DataValidationError):
        service.ingest_episode(
            EpisodeIngestionRequest(
                tenant_id=actor.tenant_id,
                source_type="document",
                source_id="bad-checksum",
                title="Bad checksum",
                raw_content="content",
                source_checksum="0" * 64,
            ),
            principal=actor,
        )


def test_memory_requires_canonical_episode_provenance() -> None:
    service, actor = service_with_pack()
    episode = ingest_episode(service, actor)
    with pytest.raises(Talk2DataValidationError, match="checksum"):
        service.promote_memory(
            MemoryPromotionRequest(
                tenant_id=actor.tenant_id,
                memory_type=MemoryType.business_definition,
                source_type=episode.source_type,
                source_id=episode.source_id,
                business_domain="subscriber",
                status=MemoryStatus.published,
                approved_by=actor.subject,
                content="Invalid provenance.",
                provenance=MemoryProvenance(
                    episode_id=episode.episode_id,
                    source_checksum="f" * 64,
                    derived_by=actor.subject,
                ),
            ),
            principal=actor,
        )


def test_role_and_classification_filters_run_before_return() -> None:
    service, actor = service_with_pack()
    episode = ingest_episode(
        service,
        actor,
        classification=Sensitivity.confidential,
        content="Confidential postpaid churn policy.",
    )
    promote_memory(
        service,
        actor,
        episode=episode,
        classification=Sensitivity.confidential,
        allowed_roles=["analyst"],
    )

    ordinary = principal(
        roles=("consumer",),
        clearance=Sensitivity.internal,
        subject="ordinary.consumer",
    )
    result = service.query_memory(MemoryQuery(query="postpaid churn"), principal=ordinary)
    assert result.memory == []
    assert set(result.policy_exclusions) == {"classification_policy"}

    analyst = principal(
        roles=("consumer", "analyst"),
        clearance=Sensitivity.confidential,
        subject="authorized.analyst",
    )
    result = service.query_memory(MemoryQuery(query="postpaid churn"), principal=analyst)
    assert len(result.memory) == 1


def test_cross_tenant_retrieval_returns_no_memory_or_hidden_identifiers() -> None:
    service, actor = service_with_pack()
    memory = promote_memory(service, actor)
    other = principal(
        tenant_id="other-tenant",
        roles=("consumer",),
        clearance=Sensitivity.restricted,
        subject="other.consumer",
    )
    result = service.query_memory(MemoryQuery(query="postpaid churn"), principal=other)
    assert result.memory == []
    assert result.policy_exclusions == []
    assert memory.memory_id not in result.model_dump_json()

    with pytest.raises(Talk2DataAuthorizationError):
        service.ingest_episode(
            EpisodeIngestionRequest(
                tenant_id=actor.tenant_id,
                source_type="manual",
                source_id="cross-tenant",
                title="Cross tenant",
                raw_content="not allowed",
            ),
            principal=other,
        )


def test_temporal_supersession_preserves_past_and_current_truth() -> None:
    service, actor = service_with_pack()
    first_episode = ingest_episode(service, actor, content="Churn excludes involuntary disconnects.")
    first = promote_memory(
        service,
        actor,
        episode=first_episode,
        content="Churn excludes involuntary disconnects.",
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
    )
    replacement_episode = ingest_episode(
        service,
        actor,
        source_id="subscriber_metrics_catalog",
        content="Beginning July 2026, churn includes involuntary disconnects.",
    )
    replacement_request = MemoryPromotionRequest(
        tenant_id=actor.tenant_id,
        memory_type=MemoryType.metric_context,
        source_type=replacement_episode.source_type,
        source_id=replacement_episode.source_id,
        business_domain="subscriber",
        related_metrics=["postpaid_churn_rate"],
        related_entities=["subscriber", "service_plan"],
        status=MemoryStatus.published,
        classification=Sensitivity.internal,
        authority_level=AuthorityLevel.authoritative,
        owner="Synthetic Subscriber Analytics",
        approved_by=actor.subject,
        content="Beginning July 2026, churn includes involuntary disconnects.",
        provenance=MemoryProvenance(
            episode_id=replacement_episode.episode_id,
            source_checksum=replacement_episode.source_checksum,
            derived_by=actor.subject,
            parent_memory_ids=[first.memory_id],
        ),
    )
    transition = service.supersede_memory(
        MemorySupersessionRequest(
            memory_id=first.memory_id,
            replacement=replacement_request,
            effective_at=datetime(2026, 7, 1, tzinfo=UTC),
        ),
        principal=actor,
    )

    past = service.query_memory(
        MemoryQuery(
            query="churn involuntary disconnects",
            effective_at=datetime(2026, 3, 1, tzinfo=UTC),
        ),
        principal=actor,
    )
    current = service.query_memory(
        MemoryQuery(
            query="churn involuntary disconnects",
            effective_at=datetime(2026, 8, 1, tzinfo=UTC),
        ),
        principal=actor,
    )
    assert [memory.memory_id for memory in past.memory] == [first.memory_id]
    assert [memory.memory_id for memory in current.memory] == [transition.replacement.memory_id]
    assert transition.superseded.superseded_by == transition.replacement.memory_id
    assert transition.replacement.supersedes == first.memory_id
    assert transition.replacement.version == 2


def test_invalid_and_unapproved_obsidian_notes_cannot_be_promoted() -> None:
    service, actor = service_with_pack()
    invalid = service.validate_obsidian("# Missing frontmatter")
    assert invalid.valid is False

    draft = (EXAMPLE_DIR / "unapproved-draft.md").read_text(encoding="utf-8")
    validation = service.validate_obsidian(draft)
    assert validation.valid is True
    assert validation.authoritative is False
    with pytest.raises(ValueError, match="not approved"):
        service.promote_obsidian(ObsidianPromotionRequest(markdown=draft), principal=actor)


def test_approved_obsidian_note_promotes_episode_memory_and_wiki_links() -> None:
    service, actor = service_with_pack()
    markdown = (EXAMPLE_DIR / "approved-metric-context.md").read_text(encoding="utf-8")
    result = service.promote_obsidian(
        ObsidianPromotionRequest(markdown=markdown),
        principal=actor,
    )
    assert result.memory.status == MemoryStatus.approved
    assert result.memory.provenance.episode_id == result.episode.episode_id
    assert result.wiki_links == ["Postpaid Churn", "Service Plan"]
    relationships = list(service.store.relationships.values())
    assert {relationship.target_entity_id for relationship in relationships} == {
        "Postpaid Churn",
        "Service Plan",
    }


def test_context_coverage_receipt_reports_sources_watermarks_and_conflicts() -> None:
    service, actor = service_with_pack()
    episode = ingest_episode(service, actor)
    promote_memory(
        service,
        actor,
        episode=episode,
        conflict_group_id="conflict-postpaid-churn",
    )
    now = datetime(2026, 8, 1, tzinfo=UTC)
    for source_id in ("subscriber_metrics_catalog", "network_performance_catalog"):
        service.upsert_source_health(
            SourceIngestionHealth(
                tenant_id=actor.tenant_id,
                source_id=source_id,
                status=SourceHealthStatus.healthy,
                latest_episode_id=episode.episode_id,
                latest_ingestion_watermark=now,
                last_success_at=now,
            ),
            principal=actor,
        )
    service.upsert_index_watermark(
        IndexWatermark(
            tenant_id=actor.tenant_id,
            partition="graph",
            status=IndexStatus.current,
            source_watermark=now,
            indexed_watermark=now,
        ),
        principal=actor,
    )

    receipt = service.context_coverage(
        ContextCoverageRequest(
            question="What was postpaid churn by plan last month?",
            requested_memory_partitions=["domain_pack", "current_memory", "metric_timeline"],
            business_domains=["subscriber"],
            related_metrics=["postpaid_churn_rate"],
            related_entities=["service_plan"],
            effective_at=now,
        ),
        principal=actor,
    )
    assert receipt.domain_pack_version == 1
    assert receipt.requested_memory_partitions == [
        "domain_pack",
        "current_memory",
        "metric_timeline",
    ]
    assert receipt.searched_memory_partitions == receipt.requested_memory_partitions
    assert receipt.latest_ingestion_watermark == now
    assert receipt.incomplete_or_unavailable_sources == []
    assert receipt.conflicting_memory_ids
    assert receipt.overall_coverage_status == CoverageStatus.partial


def test_context_coverage_reports_index_lag_and_missing_sources() -> None:
    service, actor = service_with_pack()
    episode = ingest_episode(service, actor)
    promote_memory(service, actor, episode=episode)
    source_time = datetime(2026, 8, 1, 12, tzinfo=UTC)
    indexed_time = source_time - timedelta(hours=2)
    service.upsert_source_health(
        SourceIngestionHealth(
            tenant_id=actor.tenant_id,
            source_id="subscriber_metrics_catalog",
            status=SourceHealthStatus.healthy,
            latest_ingestion_watermark=source_time,
        ),
        principal=actor,
    )
    service.upsert_index_watermark(
        IndexWatermark(
            tenant_id=actor.tenant_id,
            partition="graph",
            status=IndexStatus.lagging,
            source_watermark=source_time,
            indexed_watermark=indexed_time,
        ),
        principal=actor,
    )
    receipt = service.context_coverage(
        ContextCoverageRequest(
            question="What was postpaid churn by plan last month?",
            requested_memory_partitions=["current_memory"],
            business_domains=["subscriber"],
            effective_at=source_time,
        ),
        principal=actor,
    )
    assert receipt.index_lag_seconds == 7200
    assert "network_performance_catalog" in receipt.incomplete_or_unavailable_sources
    assert receipt.overall_coverage_status == CoverageStatus.partial


def test_entity_metric_timelines_and_investigations_are_typed() -> None:
    service, actor = service_with_pack()
    episode = ingest_episode(service, actor)
    metric_memory = promote_memory(service, actor, episode=episode)
    investigation = promote_memory(
        service,
        actor,
        episode=ingest_episode(
            service,
            actor,
            source_id="investigation-log",
            content="Investigation into churn by service plan.",
        ),
        memory_type=MemoryType.investigation,
        content="Investigation into churn by service plan.",
    )
    entity_timeline = service.entity_timeline(
        TimelineRequest(identifier="subscriber"),
        principal=actor,
    )
    metric_timeline = service.metric_timeline(
        TimelineRequest(identifier="postpaid_churn_rate"),
        principal=actor,
    )
    investigations = service.prior_investigations(
        MemoryQuery(query="churn service plan"),
        principal=actor,
    )
    assert metric_memory.memory_id in {memory.memory_id for memory in entity_timeline.memory}
    assert metric_memory.memory_id in {memory.memory_id for memory in metric_timeline.memory}
    assert [memory.memory_id for memory in investigations.memory] == [investigation.memory_id]


def test_graph_adapter_is_replaceable_and_canonical_store_survives_graph_failure() -> None:
    class FailingGraph(InMemoryTemporalGraphAdapter):
        name = "failing-test-adapter"

        def upsert_memory(self, memory):
            raise RuntimeError("graph unavailable")

    service, actor = service_with_pack()
    service.graph = FailingGraph()
    memory = promote_memory(service, actor)
    assert memory.memory_id in service.store.memories
    watermark = service.store.index_watermarks[f"{actor.tenant_id}:graph"]
    assert watermark.status == IndexStatus.unavailable

    replacement = InMemoryTemporalGraphAdapter()
    service.graph = replacement
    rebuilt = service.rebuild_graph(principal=actor)
    assert rebuilt.memories_indexed == 1
    assert replacement.status().available is True


def test_graphiti_adapter_maps_generic_client_without_becoming_canonical() -> None:
    class FakeGraphitiClient:
        def __init__(self):
            self.entities = []
            self.episodes = []
            self.relationships = []

        def upsert_episode(self, payload):
            self.episodes.append(payload)

        def upsert_entity(self, payload):
            self.entities.append(payload)

        def upsert_relationship(self, payload):
            self.relationships.append(payload)

        def search(self, payload):
            return [{"memory_id": self.entities[0]["entity_id"], "score": 1.0, "reasons": ["fake"]}]

        def timeline(self, payload):
            return [self.entities[0]["entity_id"]]

        def clear_tenant(self, tenant_id):
            self.entities.clear()
            self.episodes.clear()
            self.relationships.clear()

        def close(self):
            return None

    client: GraphitiClientProtocol = FakeGraphitiClient()
    adapter = GraphitiTemporalGraphAdapter(client)
    service = Talk2DataService(store=InMemoryTalk2DataStore(), graph=adapter)
    actor = principal()
    service.create_domain_pack(load_pack(), principal=actor)
    memory = promote_memory(service, actor)
    result = service.query_memory_with_graph(MemoryQuery(query="postpaid churn"), principal=actor)
    assert result.graph_backend == "graphiti"
    assert [item.memory_id for item in result.memory] == [memory.memory_id]
    assert service.store.memories[memory.memory_id].content_text


def test_sql_store_persists_domain_episode_memory_and_watermark(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'talk2data.db'}"
    store = SqlAlchemyTalk2DataStore(database_url)
    service = Talk2DataService(store=store)
    actor = principal()
    service.create_domain_pack(load_pack(), principal=actor)
    episode = ingest_episode(service, actor)
    memory = promote_memory(service, actor, episode=episode)
    store.close()

    reopened = SqlAlchemyTalk2DataStore(database_url)
    try:
        assert any(pack.tenant_id == actor.tenant_id for pack in reopened.domain_packs.values())
        assert episode.episode_id in reopened.episodes
        assert memory.memory_id in reopened.memories
        assert f"{actor.tenant_id}:graph" in reopened.index_watermarks
        assert reopened.audit_events
    finally:
        reopened.close()


def test_talk2data_routes_are_registered_in_typed_openapi() -> None:
    app = FastAPI()
    app.include_router(router)
    paths = set(app.openapi()["paths"])
    required = {
        "/v1/domain-packs/current",
        "/v1/domain-packs",
        "/v1/domain-packs/resolve",
        "/v1/domain-packs/classify",
        "/v1/memory/episodes",
        "/v1/memory",
        "/v1/memory/supersede",
        "/v1/memory/query",
        "/v1/memory/query/graph",
        "/v1/memory/timelines/entities",
        "/v1/memory/timelines/metrics",
        "/v1/memory/investigations",
        "/v1/memory/source-health",
        "/v1/memory/index-watermarks",
        "/v1/memory/context-coverage",
        "/v1/obsidian/validate",
        "/v1/obsidian/promote",
        "/v1/graph/status",
        "/v1/graph/rebuild",
        "/v1/memory/audit",
    }
    assert required <= paths
    schemas = app.openapi()["components"]["schemas"]
    assert "TenantDomainPack" in schemas
    assert "GovernedMemoryObject" in schemas
    assert "ContextCoverageReceipt" in schemas


def test_unverified_memory_is_not_authoritative_for_consumers() -> None:
    service, actor = service_with_pack()
    episode = ingest_episode(service, actor, content="Draft churn interpretation.")
    draft = promote_memory(
        service,
        actor,
        episode=episode,
        content="Draft churn interpretation.",
        status=MemoryStatus.unverified,
    )
    consumer = principal(roles=("consumer",), clearance=Sensitivity.restricted)
    result = service.query_memory(MemoryQuery(query="draft churn"), principal=consumer)
    assert result.memory == []
    reviewer_result = service.query_memory(
        MemoryQuery(query="draft churn", statuses=[MemoryStatus.unverified]),
        principal=actor,
    )
    assert [memory.memory_id for memory in reviewer_result.memory] == [draft.memory_id]


def test_overlapping_authoritative_facts_are_marked_conflicting() -> None:
    service, actor = service_with_pack()
    first = promote_memory(
        service,
        actor,
        episode=ingest_episode(service, actor, content="Churn excludes involuntary disconnects."),
        content="Churn excludes involuntary disconnects.",
    )
    second = promote_memory(
        service,
        actor,
        episode=ingest_episode(service, actor, content="Churn includes involuntary disconnects."),
        content="Churn includes involuntary disconnects.",
    )
    assert first.memory_id != second.memory_id
    assert service.store.memories[first.memory_id].status == MemoryStatus.conflicting
    assert service.store.memories[second.memory_id].status == MemoryStatus.conflicting
    assert service.store.memories[first.memory_id].conflict_group_id
    assert (
        service.store.memories[first.memory_id].conflict_group_id
        == service.store.memories[second.memory_id].conflict_group_id
    )
