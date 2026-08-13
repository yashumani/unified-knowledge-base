from pathlib import Path

from ukb.models import IngestionSubmission, ReviewDecision
from ukb.services.compiler import BrainCompiler
from ukb.services.governance import GovernanceService
from ukb.storage.sqlalchemy_store import SqlAlchemyBrainStore


def sqlite_url(path: Path) -> str:
    return f"sqlite+pysqlite:///{path.as_posix()}"


def test_sqlalchemy_store_survives_restart(tmp_path: Path) -> None:
    database_path = tmp_path / "ukb.db"
    compiler = BrainCompiler()

    first_store = SqlAlchemyBrainStore(sqlite_url(database_path))
    governance = GovernanceService(first_store)

    submission = IngestionSubmission(
        title="Incident Resolution Time Definition",
        source_type="document",
        submitted_by="persistence-test.submitter",
        domain="support",
        content=(
            "Incident Resolution Time is a support metric owned by Support Operations. "
            "It appears in the SLA Review Dashboard."
        ),
    )
    source, review_item = compiler.compile_submission(submission)
    first_store.add_source(source)
    first_store.add_review_item(review_item)
    governance.approve(
        review_item.id,
        ReviewDecision(
            reviewed_by="persistence-test.reviewer",
            comment="Approved synthetic persistence test.",
        ),
    )
    object_id = review_item.candidate_object.id
    first_store.close()

    reloaded_store = SqlAlchemyBrainStore(sqlite_url(database_path))
    try:
        assert source.source_id in reloaded_store.sources
        assert review_item.id in reloaded_store.review_items
        assert reloaded_store.review_items[review_item.id].status.value == "approved"
        assert object_id in reloaded_store.knowledge_objects
        assert reloaded_store.knowledge_objects[object_id].status.value == "published"
        assert any(event.event_type == "review_approved" for event in reloaded_store.audit_events)
    finally:
        reloaded_store.clear()
        reloaded_store.close()
