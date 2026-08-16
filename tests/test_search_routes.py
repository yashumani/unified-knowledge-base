from fastapi.testclient import TestClient

from ukb.api.main import app

client = TestClient(app)


def test_search_and_connector_routes_respond() -> None:
    search_status = client.get("/search/status")
    connector_status = client.get("/connectors/web/status")
    search_response = client.post(
        "/brain/search",
        json={
            "query": "incident resolution time",
            "user_id": "route-test.user",
            "domains": ["support"],
            "limit": 5,
        },
    )
    disabled_capture = client.post(
        "/ingestion/web",
        json={
            "url": "https://docs.example.org/guide",
            "submitted_by": "route-test.user",
            "domain": "support",
            "sensitivity": "internal",
        },
    )

    assert search_status.status_code == 200
    assert connector_status.status_code == 200
    assert search_response.status_code == 200
    assert disabled_capture.status_code == 503
