from ukb.models import (
    ContextPackRequest,
    IngestionSubmission,
    KnowledgeObject,
    KnowledgeObjectType,
    PublishDecision,
    Relationship,
    ReviewDecision,
    Sensitivity,
)
from ukb.services.access import AccessPolicyService
from ukb.services.compiler import BrainCompiler
from ukb.services.context_pack import ContextPackService
from ukb.services.governance import GovernanceService
from ukb.services.graph import BrainGraphService
from ukb.store import BrainStore


def _publish(
    store: BrainStore,
    title: str,
    content: str,
    sensitivity: Sensitivity,
) -> str:
    compiler = BrainCompiler()
    governance = GovernanceService(store)
    submission = IngestionSubmission(
        title=title,
        source_type="document",
        submitted_by="tester",
        domain="support",
        sensitivity=sensitivity,
        content=content,
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
    return review_item.candidate_object.id


def test_objects_above_clearance_are_withheld_and_pack_is_denied():
    store = BrainStore()
    _publish(
        store,
        "Restricted Incident Metric",
        "Incident Resolution Time is a restricted metric owned by Support Operations.",
        Sensitivity.restricted,
    )
    policy = AccessPolicyService(default_clearance=Sensitivity.internal)
    service = ContextPackService(store, access_policy=policy)

    pack = service.build(
        ContextPackRequest(
            question="What is Incident Resolution Time?",
            user_id="consumer",
            domains=["support"],
        )
    )

    assert pack.access_decision == "denied"
    assert pack.knowledge_objects == []
    assert pack.evidence == []
    assert pack.missing_context


def test_no_match_is_allowed_not_denied():
    """An empty brain is missing context, not a policy denial."""

    store = BrainStore()
    service = ContextPackService(store, access_policy=AccessPolicyService())

    pack = service.build(
        ContextPackRequest(
            question="Anything at all?",
            user_id="consumer",
            domains=["support"],
        )
    )

    assert pack.access_decision == "allowed"
    assert pack.knowledge_objects == []


def test_partial_redaction_is_allowed_but_flagged():
    store = BrainStore()
    _publish(
        store,
        "Public Incident Metric",
        "Incident Resolution Time is a public metric owned by Support Operations.",
        Sensitivity.public,
    )
    _publish(
        store,
        "Confidential Incident Metric",
        "Incident Resolution Time detail is a confidential metric owned by Support Operations.",
        Sensitivity.confidential,
    )
    service = ContextPackService(
        store,
        access_policy=AccessPolicyService(default_clearance=Sensitivity.internal),
    )

    pack = service.build(
        ContextPackRequest(
            question="What is Incident Resolution Time?",
            user_id="consumer",
            domains=["support"],
        )
    )

    assert pack.access_decision == "allowed"
    assert len(pack.knowledge_objects) == 1
    assert pack.knowledge_objects[0].sensitivity == Sensitivity.public
    assert any("withheld by access policy" in caveat for caveat in pack.caveats)


def test_higher_clearance_sees_restricted_object():
    store = BrainStore()
    _publish(
        store,
        "Restricted Incident Metric",
        "Incident Resolution Time is a restricted metric owned by Support Operations.",
        Sensitivity.restricted,
    )
    policy = AccessPolicyService(
        default_clearance=Sensitivity.internal,
        user_clearances={"governance.admin": Sensitivity.restricted},
    )
    service = ContextPackService(store, access_policy=policy)

    pack = service.build(
        ContextPackRequest(
            question="What is Incident Resolution Time?",
            user_id="governance.admin",
            domains=["support"],
        ),
        principal="governance.admin",
    )

    assert pack.access_decision == "allowed"
    assert pack.knowledge_objects


def test_request_user_id_cannot_escalate_clearance():
    """The body is client-asserted; only the authenticated principal sets clearance."""

    store = BrainStore()
    _publish(
        store,
        "Restricted Incident Metric",
        "Incident Resolution Time is a restricted metric owned by Support Operations.",
        Sensitivity.restricted,
    )
    policy = AccessPolicyService(
        default_clearance=Sensitivity.internal,
        user_clearances={"governance.admin": Sensitivity.restricted},
    )
    service = ContextPackService(store, access_policy=policy)

    pack = service.build(
        ContextPackRequest(
            question="What is Incident Resolution Time?",
            user_id="governance.admin",
            domains=["support"],
        ),
        principal="attacker",
    )

    assert pack.access_decision == "denied"
    assert pack.knowledge_objects == []


def test_related_object_ids_above_clearance_are_dropped():
    store = BrainStore()
    secret = KnowledgeObject(
        id="obj_secret",
        type=KnowledgeObjectType.metric,
        title="Restricted Driver",
        summary="Restricted driver metric.",
        domain="support",
        sensitivity=Sensitivity.restricted,
    )
    store.publish_object(secret)

    visible = KnowledgeObject(
        id="obj_visible",
        type=KnowledgeObjectType.metric,
        title="Incident Resolution Time",
        summary="Incident resolution time metric.",
        domain="support",
        sensitivity=Sensitivity.public,
        relationships=[
            Relationship(type="related_to", target_id="obj_secret"),
            Relationship(type="appears_in", target_id="SLA Review Dashboard"),
        ],
    )
    store.publish_object(visible)

    service = ContextPackService(
        store,
        access_policy=AccessPolicyService(default_clearance=Sensitivity.public),
    )
    pack = service.build(
        ContextPackRequest(
            question="Incident Resolution Time relationships",
            user_id="consumer",
            domains=["support"],
        )
    )

    assert "obj_secret" not in pack.related_objects
    assert "SLA Review Dashboard" in pack.related_objects


def test_graph_hides_objects_and_edges_above_clearance():
    store = BrainStore()
    _publish(
        store,
        "Restricted Incident Metric",
        "Incident Resolution Time is a restricted metric owned by Support Operations.",
        Sensitivity.restricted,
    )
    policy = AccessPolicyService(default_clearance=Sensitivity.internal)
    graph = BrainGraphService(store).build(
        access_policy=policy,
        principal="consumer",
    )

    assert graph.nodes == []
    assert graph.edges == []


def test_graph_without_policy_is_unfiltered():
    store = BrainStore()
    _publish(
        store,
        "Restricted Incident Metric",
        "Incident Resolution Time is a restricted metric owned by Support Operations.",
        Sensitivity.restricted,
    )

    graph = BrainGraphService(store).build()

    assert graph.nodes


def test_clearance_map_parsing_skips_malformed_entries():
    policy = AccessPolicyService(
        default_clearance=Sensitivity.public,
        user_clearances=AccessPolicyService._parse_clearance_map(
            "admin:restricted, broken, :internal, ghost:not-a-level"
        ),
    )

    assert policy.clearance_for("admin") == Sensitivity.restricted
    assert policy.clearance_for("ghost") == Sensitivity.public
    assert policy.clearance_for("unknown") == Sensitivity.public
