from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ukb.api.main import app
from ukb.knowledge_ops.runtime import service
from ukb.store import store

AUTH = {"Authorization": "Bearer dev-token-change-me"}


@pytest.fixture(autouse=True)
def reset_state():
    store.clear()
    service.store.clear()
    yield
    store.clear()
    service.store.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _quality_submit(client: TestClient) -> dict:
    response = client.post(
        "/v1/knowledge-operations/quality/submit",
        headers=AUTH,
        json={
            "title": "Incident Resolution Time",
            "content": (
                "Incident Resolution Time is the average elapsed time from incident creation "
                "to resolved status. It is owned by Support Operations, excludes duplicate "
                "incidents, and is reviewed in the monthly SLA dashboard."
            ),
            "source_type": "document",
            "source_uri": "https://docs.example.org/metrics/incident-resolution-time",
            "domain": "support",
            "owner": "Support Operations",
            "sensitivity": "internal",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "review_created"
    return payload


def _publish(client: TestClient, review_item_id: str) -> str:
    item = client.get(f"/review/items/{review_item_id}", headers=AUTH).json()
    approved = client.post(
        f"/review/items/{review_item_id}/approve",
        headers=AUTH,
        json={
            "comment": "Approved with source evidence.",
            "expected_revision": item["revision"],
        },
    )
    assert approved.status_code == 200, approved.text
    published = client.post(
        f"/review/items/{review_item_id}/publish",
        headers=AUTH,
        json={
            "comment": "Published for governed recall.",
            "expected_revision": approved.json()["revision"],
        },
    )
    assert published.status_code == 200, published.text
    return published.json()["candidate_object"]["id"]


def test_identity_status_is_tenant_attributed(client: TestClient) -> None:
    identity = client.get("/v1/knowledge-operations/auth/me", headers=AUTH)
    assert identity.status_code == 200
    assert identity.json()["tenant_id"] == "default"
    assert identity.json()["subject"] == "local-api-token"

    status = client.get("/v1/knowledge-operations/status", headers=AUTH)
    assert status.status_code == 200
    assert "knowledge_quality_firewall" in status.json()["capabilities"]


def test_quality_firewall_rejects_possible_secret_before_review(client: TestClient) -> None:
    response = client.post(
        "/v1/knowledge-operations/quality/submit",
        headers=AUTH,
        json={
            "title": "Unsafe source",
            "content": "Internal instructions password=super-secret-value and operational notes.",
            "source_type": "document",
            "domain": "support",
            "owner": "Support Operations",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert payload["review_item_id"] is None
    assert payload["assessment"]["disposition"] == "reject"
    assert store.review_items == {}


def test_quality_submission_assignment_and_collaboration(client: TestClient) -> None:
    created = _quality_submit(client)
    review_item_id = created["review_item_id"]

    assignment = client.post(
        "/v1/knowledge-operations/reviews/assign",
        headers=AUTH,
        json={
            "review_item_id": review_item_id,
            "assignee": "reviewer.one",
            "priority": "high",
            "note": "Validate metric scope and exclusion rules.",
        },
    )
    assert assignment.status_code == 200, assignment.text
    assert assignment.json()["assignee"] == "reviewer.one"

    comment = client.post(
        "/v1/knowledge-operations/reviews/comments",
        headers=AUTH,
        json={
            "review_item_id": review_item_id,
            "body": "Please confirm whether customer-wait time is excluded.",
            "comment_type": "question",
        },
    )
    assert comment.status_code == 200, comment.text

    workload = client.get("/v1/knowledge-operations/reviews/workload", headers=AUTH)
    assert workload.status_code == 200
    assert workload.json()["by_assignee"] == {"reviewer.one": 1}


def test_continuous_source_subscription_is_tenant_scoped(client: TestClient) -> None:
    created = client.post(
        "/v1/knowledge-operations/subscriptions",
        headers=AUTH,
        json={
            "connector_type": "crawl4ai",
            "location": "https://docs.example.org/metrics",
            "domain": "support",
            "owner": "Support Operations",
            "sensitivity": "internal",
            "interval_minutes": 1440,
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["tenant_id"] == "default"

    listed = client.get("/v1/knowledge-operations/subscriptions", headers=AUTH)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_explainable_reranking_evaluation_and_feedback(client: TestClient) -> None:
    created = _quality_submit(client)
    object_id = _publish(client, created["review_item_id"])

    search = client.post(
        "/v1/knowledge-operations/search",
        headers=AUTH,
        json={
            "query": "Incident Resolution Time",
            "domains": ["support"],
            "limit": 5,
        },
    )
    assert search.status_code == 200, search.text
    payload = search.json()
    assert payload["policy_version"] == "governed-rerank-v1"
    assert payload["results"][0]["object_id"] == object_id
    assert payload["results"][0]["factors"]

    evaluation = client.post(
        "/v1/knowledge-operations/search/evaluate",
        headers=AUTH,
        json={
            "top_k": 5,
            "cases": [
                {
                    "question": "Incident Resolution Time",
                    "expected_object_ids": [object_id],
                    "domains": ["support"],
                },
                {
                    "question": "Restaurant food cost margin",
                    "should_abstain": True,
                    "domains": ["support"],
                },
            ],
        },
    )
    assert evaluation.status_code == 200, evaluation.text
    assert evaluation.json()["case_count"] == 2
    assert evaluation.json()["passed_cases"] == 2

    feedback = client.post(
        "/v1/knowledge-operations/search/feedback",
        headers=AUTH,
        json={
            "query": "Incident Resolution Time",
            "label": "helpful",
            "object_id": object_id,
        },
    )
    assert feedback.status_code == 200
    summary = client.get(
        "/v1/knowledge-operations/search/feedback-summary",
        headers=AUTH,
    )
    assert summary.status_code == 200
    assert summary.json()["by_label"] == {"helpful": 1}
