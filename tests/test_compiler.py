import pytest

from ukb.models import IngestionSubmission, KnowledgeObjectType
from ukb.services.compiler import BrainCompiler


def _compile(content: str):
    compiler = BrainCompiler()
    submission = IngestionSubmission(
        title="Incident Resolution Time Definition",
        source_type="document",
        submitted_by="tester",
        domain="support",
        content=content,
    )
    _, review_item = compiler.compile_submission(submission)
    return review_item.candidate_object


@pytest.mark.parametrize(
    ("content", "expected_owner"),
    [
        ("This metric is owned by Support Operations.", "Support Operations"),
        ("This metric is owned by Support Operations", "Support Operations"),
        (
            "This metric is owned by Support Operations and reviewed weekly.",
            "Support Operations",
        ),
        (
            "This metric is owned by Support Operations which reports to the CTO.",
            "Support Operations",
        ),
        (
            "This metric is owned by Support Operations for the EMEA region.",
            "Support Operations",
        ),
        ("This metric is owned by Data & Analytics.", "Data & Analytics"),
        ("No ownership statement here.", None),
    ],
)
def test_owner_extraction_stops_at_clause_boundary(content, expected_owner):
    assert _compile(content).owner == expected_owner


def test_classifier_prefers_metric_over_report_keywords():
    candidate = _compile("This KPI metric appears in the SLA Review Dashboard.")
    assert candidate.type == KnowledgeObjectType.metric


def test_unmatched_content_is_unknown_type():
    candidate = _compile("Some generic prose with no classification signal at all.")
    assert candidate.type == KnowledgeObjectType.unknown
