from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ukb.ai.providers.noop import NoopProvider
from ukb.ai.service import AIEnrichmentService
from ukb.api import main as api_main
from ukb.store import store


@pytest.fixture(autouse=True)
def isolate_api_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    store.sources.clear()
    store.review_items.clear()
    store.knowledge_objects.clear()
    store.audit_events.clear()
    monkeypatch.setattr(
        api_main,
        "ai_enrichment_service",
        AIEnrichmentService(provider=NoopProvider()),
    )
    yield
    store.sources.clear()
    store.review_items.clear()
    store.knowledge_objects.clear()
    store.audit_events.clear()


def test_health_and_ai_status() -> None:
    with TestClient(api_main.app) as client:
        health = client.get("/health")
        provider = client.get("/ai/providers")
        provider_health = client.get("/ai/health")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert provider.status_code == 200
    assert provider.json()["provider"] == "noop"
    assert provider_health.status_code == 200
    assert provider_health.json()["reachable"] is True


def test_submit_approve_and_build_context_pack() -> None:
    with TestClient(api_main.app) as client:
        submission = client.post(
            "/ingestion/submissions",
            json={
                "title": "Incident Resolution Time Definition",
                "source_type": "document",
                "submitted_by": "api-test.submitter",
                "domain": "support",
                "sensitivity": "internal",
                "tags": ["synthetic", "test"],
                "content": (
                    "Incident Resolution Time is a support metric owned by Support Operations. "
                    "It appears in the SLA Review Dashboard."
                ),
            },
        )
        assert submission.status_code == 200
        review_item = submission.json()
        assert review_item["ai_enrichment"]["provider"] == "noop"

        approval = client.post(
            f"/review/items/{review_item['id']}/approve",
            json={"reviewed_by": "api-test.reviewer", "comment": "Approved synthetic test."},
        )
        assert approval.status_code == 200

        context_pack = client.post(
            "/brain/context-pack",
            json={
                "question": "What is Incident Resolution Time?",
                "user_id": "api-test.consumer",
                "domains": ["support"],
                "mode": "metric_definition",
            },
        )

    assert context_pack.status_code == 200
    payload = context_pack.json()
    assert payload["knowledge_objects"]
    assert payload["evidence"]
    assert payload["ai_guidance"]
