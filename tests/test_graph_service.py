from ukb.models import IngestionSubmission, ReviewDecision
from ukb.services.compiler import BrainCompiler
from ukb.services.governance import GovernanceService
from ukb.services.graph import BrainGraphService
from ukb.store import BrainStore


def test_graph_includes_source_review_and_published_object():
    store = BrainStore()
    compiler = BrainCompiler()
    governance = GovernanceService(store)
    graph_service = BrainGraphService(store)

    submission = IngestionSubmission(
        title="Incident Resolution Time Definition",
        source_type="document",
        submitted_by="tester",
        domain="support",
        content="Incident Resolution Time is a metric owned by Support Operations.",
    )

    source, review_item = compiler.compile_submission(submission)
    store.add_source(source)
    store.add_review_item(review_item)
    governance.approve(review_item.id, ReviewDecision(reviewed_by="reviewer"))

    graph = graph_service.build()
    node_ids = {node.id for node in graph.nodes}
    edge_types = {edge.type for edge in graph.edges}

    assert source.source_id in node_ids
    assert review_item.id in node_ids
    assert review_item.candidate_object.id in node_ids
    assert "evidence_for" in edge_types
    assert "reviews" in edge_types
