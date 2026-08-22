from ukb.models import (
    IngestionSubmission,
    PublishDecision,
    ReviewDecision,
    ReviewStatus,
)
from ukb.services.compiler import BrainCompiler
from ukb.services.governance import GovernanceService
from ukb.store import BrainStore


def test_governance_approval_requires_explicit_publication():
    store = BrainStore()
    compiler = BrainCompiler()
    governance = GovernanceService(store)

    submission = IngestionSubmission(
        title="Reopen Rate Definition",
        source_type="document",
        submitted_by="tester",
        domain="support",
        content="Reopen Rate is a KPI metric owned by Support Operations.",
    )

    source, review_item = compiler.compile_submission(submission)
    store.add_source(source)
    store.add_review_item(review_item)

    approved = governance.approve(
        review_item.id,
        ReviewDecision(
            reviewed_by="domain-reviewer",
            comment="Looks good.",
            expected_revision=review_item.revision,
        ),
    )

    assert approved.status == ReviewStatus.approved
    assert approved.candidate_object.id not in store.knowledge_objects

    transition = governance.publish(
        review_item.id,
        PublishDecision(
            published_by="governance-publisher",
            comment="Approved object is ready for retrieval.",
            expected_revision=approved.revision,
        ),
    )

    assert transition.item.status == ReviewStatus.published
    assert transition.published_object is not None
    assert transition.published_object.id in store.knowledge_objects
    assert (
        store.knowledge_objects[transition.published_object.id].status
        == ReviewStatus.published
    )
    assert {event.event_type for event in store.audit_events} >= {
        "review_approved",
        "knowledge_published",
    }
