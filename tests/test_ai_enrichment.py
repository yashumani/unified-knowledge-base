from ukb.ai.providers.noop import NoopProvider
from ukb.ai.service import AIEnrichmentService
from ukb.models import ContextPackRequest, IngestionSubmission, ReviewDecision
from ukb.services.compiler import BrainCompiler
from ukb.services.context_pack import ContextPackService
from ukb.services.governance import GovernanceService
from ukb.store import BrainStore


def test_noop_enrichment_adds_review_brief_and_findings():
    compiler = BrainCompiler()
    service = AIEnrichmentService(provider=NoopProvider())
    submission = IngestionSubmission(
        title="Incident Resolution Time Definition",
        source_type="document",
        submitted_by="tester",
        domain="support",
        content=(
            "Incident Resolution Time is a metric for support cases, excluding duplicate "
            "incidents. It appears in the SLA Review Dashboard and is owned by Support Operations. "
            "Recently resolved incidents may need 24 hours for quality review tags to settle."
        ),
    )

    source, review_item = compiler.compile_submission(submission)
    enrichment = service.enrich_source(
        source=source,
        content=submission.content,
        baseline_candidate=review_item.candidate_object,
    )

    assert enrichment.source_classification.source_kind == "metric_definition"
    assert enrichment.review_brief.summary
    assert enrichment.review_brief.reviewer_questions
    assert enrichment.validation_findings
    assert any(finding.finding_type == "exclusion_rule_needs_review" for finding in enrichment.validation_findings)
    assert enrichment.suggested_relationships


def test_context_pack_enrichment_adds_ai_guidance():
    store = BrainStore()
    compiler = BrainCompiler()
    governance = GovernanceService(store)
    context_service = ContextPackService(store)
    ai_service = AIEnrichmentService(provider=NoopProvider())

    submission = IngestionSubmission(
        title="Incident Resolution Time Definition",
        source_type="document",
        submitted_by="tester",
        domain="support",
        content=(
            "Incident Resolution Time is a metric for support cases and is owned by Support Operations."
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
    enriched = ai_service.enrich_context_pack(context_pack=pack)

    assert enriched.ai_guidance
    assert enriched.recommended_followups
