import pytest
from fastapi.testclient import TestClient

from ukb.api.main import app
from ukb.store import store

DEV_TOKEN = "dev-token-change-me"
AUTH = {"Authorization": f"Bearer {DEV_TOKEN}"}


@pytest.fixture
def client():
    store.clear()
    return TestClient(app)


def _submit(
    client: TestClient,
    title: str,
    content: str,
    sensitivity: str = "internal",
) -> str:
    response = client.post(
        "/ingestion/submissions",
        headers=AUTH,
        json={
            "title": title,
            "source_type": "document",
            "submitted_by": "demo.user",
            "domain": "support",
            "sensitivity": sensitivity,
            "content": content,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _approve_and_publish(client: TestClient, review_item_id: str) -> dict:
    approved = client.post(
        f"/review/items/{review_item_id}/approve",
        headers=AUTH,
        json={"comment": "Definition and evidence approved."},
    )
    assert approved.status_code == 200, approved.text
    approved_payload = approved.json()
    assert approved_payload["status"] == "approved"

    published = client.post(
        f"/review/items/{review_item_id}/publish",
        headers=AUTH,
        json={
            "comment": "Published for governed retrieval.",
            "expected_revision": approved_payload["revision"],
        },
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    return published.json()


def test_submit_approve_publish_and_compose_context_pack(client):
    review_item_id = _submit(
        client,
        "Incident Resolution Time Definition",
        "Incident Resolution Time is the average elapsed time from incident creation to "
        "resolved status for product support cases, excluding duplicate incidents. It "
        "appears in the SLA Review Dashboard and is owned by Support Operations.",
    )

    queue = client.get("/review/queue", headers=AUTH).json()
    assert any(item["id"] == review_item_id for item in queue)

    _approve_and_publish(client, review_item_id)

    pack_response = client.post(
        "/brain/context-pack",
        headers=AUTH,
        json={
            "question": "What is Incident Resolution Time?",
            "user_id": "demo.user",
            "domains": ["support"],
            "mode": "metric_definition",
        },
    )
    assert pack_response.status_code == 200, pack_response.text
    pack = pack_response.json()

    assert pack["access_decision"] == "allowed"
    assert pack["knowledge_objects"]
    assert pack["evidence"]

    audit_types = {
        event["event_type"]
        for event in client.get("/governance/audit", headers=AUTH).json()
    }
    assert {
        "submission_created",
        "review_approved",
        "knowledge_published",
        "context_pack_requested",
    } <= audit_types


def test_restricted_object_is_denied_to_default_clearance(client):
    review_item_id = _submit(
        client,
        "Restricted Incident Metric",
        "Incident Resolution Time detail is a restricted metric owned by Support Operations.",
        sensitivity="restricted",
    )
    _approve_and_publish(client, review_item_id)

    pack_response = client.post(
        "/brain/context-pack",
        headers=AUTH,
        json={
            "question": "What is Incident Resolution Time?",
            "user_id": "demo.user",
            "domains": ["support"],
            "mode": "metric_definition",
        },
    )
    assert pack_response.status_code == 200, pack_response.text
    pack = pack_response.json()

    assert pack["access_decision"] == "denied"
    assert pack["knowledge_objects"] == []
    assert pack["evidence"] == []
    assert pack["missing_context"]

    # The same object must not leak through the other read surfaces.
    assert client.get("/brain/objects", headers=AUTH).json() == []
    graph = client.get("/brain/graph", headers=AUTH).json()
    assert graph["nodes"] == []
    assert graph["edges"] == []


def test_restricted_object_is_not_addressable_by_id(client):
    review_item_id = _submit(
        client,
        "Restricted Incident Metric",
        "Incident Resolution Time detail is a restricted metric owned by Support Operations.",
        sensitivity="restricted",
    )
    published = _approve_and_publish(client, review_item_id)
    object_id = published["candidate_object"]["id"]

    response = client.get(f"/brain/objects/{object_id}", headers=AUTH)
    assert response.status_code == 404
