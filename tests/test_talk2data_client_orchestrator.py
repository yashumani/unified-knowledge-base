from __future__ import annotations

import json

import httpx
import pytest

from ukb.talk2data.client import Talk2DataClientError, Talk2DataMemoryClient
from ukb.talk2data.models import DomainFit
from ukb.talk2data.orchestrator import Talk2DataDecisionOrchestrator

QUESTIONS = {
    "What was postpaid churn by plan last month?": "in_domain",
    "What is our restaurant food-cost margin by location?": "excluded",
    "Did restaurant foot traffic near our stores affect mobile activations?": "external_adjacent",
    "Did food-delivery application traffic contribute to evening network congestion?": "external_adjacent",
}


def _classification(question: str) -> dict:
    classification = QUESTIONS[question]
    external = []
    anchors = []
    metrics = []
    entities = []
    domains = []
    exclusions = []
    if classification == "in_domain":
        metrics = ["postpaid_churn"]
        entities = ["subscriber", "service_plan"]
        domains = ["wireless", "commercial"]
    elif classification == "excluded":
        exclusions = ["restaurant_unit_economics"]
    elif "foot traffic" in question:
        external = ["restaurant_foot_traffic"]
        anchors = ["mobile_activations", "retail_store"]
        metrics = ["mobile_activations"]
        entities = ["retail_store"]
        domains = ["retail", "commercial"]
    else:
        external = ["application_traffic"]
        anchors = ["network_congestion", "application_traffic"]
        metrics = ["network_congestion"]
        entities = ["application_traffic"]
        domains = ["network"]
    return {
        "question": question,
        "classification": classification,
        "domain_pack_id": "domain_pack_telecom",
        "domain_pack_version": 1,
        "matched_domains": domains,
        "matched_metrics": metrics,
        "matched_entities": entities,
        "matched_external_categories": external,
        "internal_anchors": anchors,
        "matched_exclusions": exclusions,
        "reasons": ["synthetic test classification"],
        "confidence": 0.95,
    }


def _handler(request: httpx.Request) -> httpx.Response:
    assert request.headers["Authorization"] == "Bearer test-token"
    assert request.headers.get("X-Request-ID", "").startswith("t2d_")
    if request.url.path == "/v1/domain-packs/classify":
        question = json.loads(request.content)["question"]
        return httpx.Response(200, json=_classification(question))
    if request.url.path == "/v1/memory/query/graph":
        return httpx.Response(
            200,
            json={
                "memory": [],
                "returned_count": 0,
                "searched_partitions": ["current_memory", "graph"],
                "policy_exclusions": [],
                "graph_backend": "memory",
            },
        )
    if request.url.path == "/v1/memory/context-coverage":
        payload = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "receipt_id": "coverage_test",
                "tenant_id": "synthetic-telco",
                "requested_memory_partitions": payload["requested_memory_partitions"],
                "searched_memory_partitions": payload["requested_memory_partitions"],
                "partition_coverage": [
                    {
                        "partition": partition,
                        "searched": True,
                        "result_count": 1,
                        "status": "complete",
                        "notes": [],
                    }
                    for partition in payload["requested_memory_partitions"]
                ],
                "domain_pack_id": "domain_pack_telecom",
                "domain_pack_version": 1,
                "incomplete_or_unavailable_sources": [],
                "policy_based_exclusions": [],
                "conflicting_memory_ids": [],
                "superseded_memory_ids": [],
                "overall_coverage_status": "complete",
                "notes": [],
            },
        )
    return httpx.Response(404, json={"detail": "not found"})


def test_orchestrator_classifies_all_required_questions() -> None:
    client = Talk2DataMemoryClient(
        base_url="https://ukb.example.test",
        token="test-token",
        transport=httpx.MockTransport(_handler),
    )
    try:
        orchestrator = Talk2DataDecisionOrchestrator(client)
        decisions = {
            question: orchestrator.evaluate(question) for question in QUESTIONS
        }
    finally:
        client.close()

    assert decisions[
        "What was postpaid churn by plan last month?"
    ].domain_classification == DomainFit.in_domain
    restaurant = decisions[
        "What is our restaurant food-cost margin by location?"
    ]
    assert restaurant.domain_classification == DomainFit.excluded
    assert restaurant.may_proceed is False
    foot_traffic = decisions[
        "Did restaurant foot traffic near our stores affect mobile activations?"
    ]
    assert foot_traffic.domain_classification == DomainFit.external_adjacent
    assert foot_traffic.may_proceed is True
    assert "mobile_activations" in foot_traffic.internal_anchors
    application = decisions[
        "Did food-delivery application traffic contribute to evening network congestion?"
    ]
    assert application.domain_classification == DomainFit.external_adjacent
    assert application.may_proceed is True
    assert "network_congestion" in application.internal_anchors


def test_client_surfaces_safe_http_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"detail": "memory access denied"})

    client = Talk2DataMemoryClient(
        base_url="https://ukb.example.test",
        token="test-token",
        transport=httpx.MockTransport(handler),
    )
    try:
        with pytest.raises(Talk2DataClientError) as captured:
            client.classify_question("What was postpaid churn?")
    finally:
        client.close()

    assert captured.value.status_code == 403
    assert "memory access denied" in str(captured.value)
