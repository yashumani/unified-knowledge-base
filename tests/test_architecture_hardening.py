from __future__ import annotations

from pathlib import Path

import pytest

from ukb.ai.providers.noop import NoopProvider
from ukb.ai.service import AIEnrichmentService
from ukb.api.main import app as fastapi_app
from ukb.api.security import Principal
from ukb.application import BrainApplication
from ukb.config import Settings
from ukb.models import (
    ContextPackRequest,
    IngestionSubmission,
    PublishDecision,
    ReviewDecision,
    ReviewStatus,
    Sensitivity,
)
from ukb.services.governance import GovernanceConflict
from ukb.storage.memory import BrainStore
from ukb.storage.sqlalchemy_store import SqlAlchemyBrainStore


def settings_for(tmp_path: Path, *, store_backend: str = "memory") -> Settings:
    return Settings(
        store_backend=store_backend,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'ukb.db'}",
        object_store_url=f"file://{tmp_path / 'objects'}",
        search_backend="memory",
        ai_provider="noop",
        ai_mode="offline_no_model",
        ai_chat_model="deterministic",
        require_owner_for_publish=True,
        create_schema_on_startup=True,
    )


def principal(*roles: str) -> Principal:
    return Principal(
        subject="architecture.tester",
        roles=frozenset(
            roles or {"consumer", "submitter", "reviewer", "publisher"}
        ),
        clearance=Sensitivity.internal,
        auth_method="test",
    )


def build_application(tmp_path: Path, *, durable: bool = False) -> BrainApplication:
    settings = settings_for(
        tmp_path,
        store_backend="sqlalchemy" if durable else "memory",
    )
    store = SqlAlchemyBrainStore(settings.database_url) if durable else BrainStore()
    return BrainApplication(
        store=store,
        settings=settings,
        ai_service=AIEnrichmentService(
            settings=settings,
            provider=NoopProvider(),
        ),
    )


def submission() -> IngestionSubmission:
    return IngestionSubmission(
        title="Service Handoff Time",
        source_type="document",
        submitted_by="client-asserted-name",
        domain="support",
        owner="Support Operations",
        sensitivity="internal",
        source_uri="https://docs.example.org/service-handoff-time",
        tags=["alias:Handoff Duration", "synthetic"],
        content=(
            "# Service Handoff Time\n\n"
            "Service Handoff Time is the elapsed time between first-line support and "
            "specialist support. It is owned by Support Operations. Customer-wait "
            "periods are excluded.\n\n"
            "## Caveat\n\nRecently reassigned cases may need 12 hours to reconcile."
        ),
    )


def test_evidence_is_versioned_chunked_and_ai_runs_are_audited(
    tmp_path: Path,
) -> None:
    application = build_application(tmp_path)
    item = application.submit_text(submission(), principal=principal("submitter"))

    source = application.store.sources[item.source_id]
    versions = application.store.list_source_versions(source.source_id)
    chunks = application.store.list_evidence_chunks(source_id=source.source_id)

    assert source.submitted_by == "architecture.tester"
    assert source.current_version_id == versions[0].id
    assert source.content_hash == versions[0].content_hash
    assert versions[0].object_uri and versions[0].object_uri.startswith("object://")
    assert chunks
    assert chunks[0].source_version_id == versions[0].id
    assert item.candidate_object.evidence_refs
    assert application.store.ai_task_runs


def test_approval_and_publication_are_separate_revision_guarded_transitions(
    tmp_path: Path,
) -> None:
    application = build_application(tmp_path)
    item = application.submit_text(submission(), principal=principal("submitter"))
    submitted_revision = item.revision

    approved = application.approve_review(
        item.id,
        ReviewDecision(
            comment="Definition and evidence verified.",
            expected_revision=submitted_revision,
        ),
        principal=principal("reviewer"),
    )
    assert approved.status == ReviewStatus.approved
    assert application.store.knowledge_objects == {}

    with pytest.raises(GovernanceConflict):
        application.publish_review(
            item.id,
            PublishDecision(
                comment="Stale publication attempt.",
                expected_revision=submitted_revision,
            ),
            principal=principal("publisher"),
        )

    transition = application.publish_review(
        item.id,
        PublishDecision(
            comment="Ready for governed retrieval.",
            expected_revision=approved.revision,
        ),
        principal=principal("publisher"),
    )
    assert transition.item.status == ReviewStatus.published
    assert transition.published_object is not None
    assert transition.published_object.id in application.store.knowledge_objects
    assert {event.event_type for event in application.store.audit_events} >= {
        "review_approved",
        "knowledge_published",
    }


def test_context_pack_uses_indexed_published_memory_and_citations(
    tmp_path: Path,
) -> None:
    application = build_application(tmp_path)
    item = application.submit_text(submission(), principal=principal("submitter"))
    approved = application.approve_review(
        item.id,
        ReviewDecision(expected_revision=item.revision),
        principal=principal("reviewer"),
    )
    application.publish_review(
        item.id,
        PublishDecision(expected_revision=approved.revision),
        principal=principal("publisher"),
    )

    pack = application.build_context_pack(
        ContextPackRequest(
            question="What is Handoff Duration and what caveat applies?",
            user_id="untrusted-body-user",
            domains=["support"],
            mode="metric_definition",
        ),
        principal=principal("consumer"),
    )

    assert pack.access_decision == "allowed"
    assert pack.retrieval_engine == "memory"
    assert pack.knowledge_objects
    assert pack.citations
    assert pack.citations[0].chunk_id
    assert pack.confidence_factors.evidence_coverage > 0
    assert pack.context_pack_id in application.store.context_packs


def test_sql_store_survives_restart_with_evidence_governance_and_context_pack(
    tmp_path: Path,
) -> None:
    first = build_application(tmp_path, durable=True)
    item = first.submit_text(submission(), principal=principal("submitter"))
    approved = first.approve_review(
        item.id,
        ReviewDecision(expected_revision=item.revision),
        principal=principal("reviewer"),
    )
    first.publish_review(
        item.id,
        PublishDecision(expected_revision=approved.revision),
        principal=principal("publisher"),
    )
    pack = first.build_context_pack(
        ContextPackRequest(
            question="Define Service Handoff Time.",
            user_id="consumer",
            domains=["support"],
            mode="metric_definition",
        ),
        principal=principal("consumer"),
    )
    first.close()

    settings = settings_for(tmp_path, store_backend="sqlalchemy")
    reopened = SqlAlchemyBrainStore(settings.database_url)
    try:
        assert item.source_id in reopened.sources
        assert reopened.list_source_versions(item.source_id)
        assert reopened.list_evidence_chunks(source_id=item.source_id)
        assert item.candidate_object.id in reopened.knowledge_objects
        assert pack.context_pack_id in reopened.context_packs
        assert any(
            event.event_type == "knowledge_published"
            for event in reopened.audit_events
        )
    finally:
        reopened.close()


def test_openapi_registers_every_workspace_contract() -> None:
    paths = set(fastapi_app.openapi()["paths"])
    required = {
        "/ingestion/capabilities",
        "/ingestion/files/preview",
        "/ingestion/files/submit",
        "/ingestion/google-drive/preview",
        "/ingestion/google-drive/submit",
        "/ingestion/crawl4ai/preview",
        "/ingestion/crawl4ai/submit",
        "/ingestion/connectors/preview",
        "/ingestion/connectors/submit",
        "/review/queue",
        "/review/approved",
        "/review/items/{review_item_id}/approve",
        "/review/items/{review_item_id}/publish",
        "/review/items/{review_item_id}/revise",
        "/brain/search",
        "/brain/context-pack",
        "/sources/{source_id}/versions",
        "/sources/{source_id}/chunks",
    }
    assert required <= paths
