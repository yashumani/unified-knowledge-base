from ukb.models import (
    ContextPackRequest,
    IngestionSubmission,
    PublishDecision,
    ReviewDecision,
)
from ukb.services.compiler import BrainCompiler
from ukb.services.context_pack import ContextPackService
from ukb.services.governance import GovernanceService
from ukb.store import BrainStore


def test_published_submission_appears_in_context_pack():
    store = BrainStore()
    compiler = BrainCompiler()
    governance = GovernanceService(store)
    context_service = ContextPackService(store)

    submission = IngestionSubmission(
        title="Incident Resolution Time Definition",
        source_type="document",
        submitted_by="tester",
        domain="support",
        content=(
            "Incident Resolution Time is a metric for the average elapsed time from "
            "incident creation to resolved status for product support cases. It is "
            "owned by Support Operations."
        ),
    )

    source, review_item = compiler.compile_submission(submission)
    store.add_source(source)
    store.add_review_item(review_item)

    approved = governance.approve(
        review_item.id,
        ReviewDecision(
            reviewed_by="reviewer",
            expected_revision=review_item.revision,
        ),
    )
    governance.publish(
        review_item.id,
        PublishDecision(
            published_by="publisher",
            expected_revision=approved.revision,
        ),
    )

    pack = context_service.build(
        ContextPackRequest(
            question="What is Incident Resolution Time?",
            user_id="tester",
            domains=["support"],
            mode="metric_definition",
        )
    )

    assert pack.access_decision == "allowed"
    assert pack.knowledge_objects
    assert pack.evidence
    assert pack.confidence > 0.5
