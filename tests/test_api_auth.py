import pytest
from fastapi.testclient import TestClient

from ukb.api.main import app
from ukb.api.security import extract_token, warn_on_insecure_configuration
from ukb.config import Settings, get_settings

DEV_TOKEN = "dev-token-change-me"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_health_is_public(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_protected_route_rejects_missing_token(client):
    response = client.get("/brain/objects")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_protected_route_rejects_wrong_token(client):
    response = client.get(
        "/brain/objects",
        headers={"Authorization": "Bearer nope"},
    )
    assert response.status_code == 403


def test_protected_route_accepts_bearer_token(client):
    response = client.get(
        "/brain/objects",
        headers={"Authorization": f"Bearer {DEV_TOKEN}"},
    )
    assert response.status_code == 200


def test_protected_route_accepts_x_api_token_header(client):
    response = client.get("/brain/objects", headers={"X-API-Token": DEV_TOKEN})
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/ingestion/submissions"),
        ("GET", "/review/queue"),
        ("GET", "/brain/graph"),
        ("POST", "/brain/context-pack"),
        ("GET", "/governance/audit"),
        ("GET", "/ai/providers"),
        ("GET", "/ai/health"),
        ("POST", "/ai/embeddings"),
    ],
)
def test_every_privileged_route_requires_a_token(client, method, path):
    response = client.get(path) if method == "GET" else client.post(path, json={})
    assert response.status_code == 401


def test_auth_runs_before_the_route_handler(client):
    """An unauthenticated call to a missing item must not reveal that it is missing."""

    response = client.post(
        "/review/items/does-not-exist/approve",
        json={"reviewed_by": "attacker"},
    )
    assert response.status_code == 401


def test_auth_can_be_disabled_for_local_development(client, monkeypatch):
    monkeypatch.setenv("UKB_REQUIRE_AUTH", "false")
    get_settings.cache_clear()

    response = client.get("/brain/objects")
    assert response.status_code == 200


def test_extract_token_handles_both_header_forms():
    assert extract_token("Bearer abc", None) == "abc"
    assert extract_token("bearer abc", None) == "abc"
    assert extract_token(None, "abc") == "abc"
    assert extract_token("Basic abc", None) is None
    assert extract_token("Bearer   ", None) is None
    assert extract_token(None, None) is None


def test_default_token_triggers_startup_warning():
    warnings = warn_on_insecure_configuration(Settings(api_token=DEV_TOKEN))
    assert any("development default" in warning for warning in warnings)


def test_disabled_auth_triggers_startup_warning():
    warnings = warn_on_insecure_configuration(Settings(require_auth=False))
    assert any("Authentication is disabled" in warning for warning in warnings)


def test_custom_token_produces_no_warning():
    assert (
        warn_on_insecure_configuration(Settings(api_token="a-real-rotated-secret"))
        == []
    )
