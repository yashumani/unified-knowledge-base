from ukb.models import ContextPackRequest, IngestionSubmission, ReviewDecision
from ukb.services.compiler import BrainCompiler
from ukb.services.context_pack import ContextPackService
from ukb.services.governance import GovernanceService
from ukb.store import BrainStore


def test_approved_submission_appears_in_context_pack():
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

    governance.approve(review_item.id, ReviewDecision(reviewed_by="reviewer"))

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
