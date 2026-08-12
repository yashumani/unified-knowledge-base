from ukb.models import IngestionSubmission, ReviewDecision, ReviewStatus
from ukb.services.compiler import BrainCompiler
from ukb.services.governance import GovernanceService
from ukb.store import BrainStore


def test_governance_approval_publishes_object():
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
        ReviewDecision(reviewed_by="domain-reviewer", comment="Looks good."),
    )

    assert approved.status == ReviewStatus.approved
    assert approved.candidate_object.id in store.knowledge_objects
    assert store.knowledge_objects[approved.candidate_object.id].status == ReviewStatus.published
    assert store.audit_events
