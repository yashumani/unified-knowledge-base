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
        title="Device Revenue Definition",
        source_type="document",
        submitted_by="tester",
        domain="finance",
        content=(
            "Device Revenue is a metric for revenue generated from device sales, "
            "excluding service revenue. It is owned by Finance BI."
        ),
    )

    source, review_item = compiler.compile_submission(submission)
    store.add_source(source)
    store.add_review_item(review_item)

    governance.approve(review_item.id, ReviewDecision(reviewed_by="reviewer"))

    pack = context_service.build(
        ContextPackRequest(
            question="What is Device Revenue?",
            user_id="tester",
            domains=["finance"],
            mode="metric_definition",
        )
    )

    assert pack.access_decision == "allowed"
    assert pack.knowledge_objects
    assert pack.evidence
    assert pack.confidence > 0.5
