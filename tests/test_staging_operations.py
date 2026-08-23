from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from ukb.operations.staging import (
    CheckStatus,
    load_env_file,
    probe_staging_runtime,
    validate_staging_environment,
)


def valid_environment() -> dict[str, str]:
    reviewer_token = "reviewer-token-" + "a" * 40
    publisher_token = "publisher-token-" + "b" * 40
    return {
        "UKB_ENVIRONMENT": "stage",
        "UKB_API_IMAGE": (
            "ghcr.io/yashumani/unified-knowledge-base-api:"
            "cd16f609c4fea43000356861016237b01d18b73b"
        ),
        "UKB_API_TOKEN": "break-glass-" + "c" * 48,
        "UKB_DEFAULT_TENANT_ID": "pilot-tenant",
        "UKB_API_TOKENS_JSON": json.dumps(
            {
                reviewer_token: {
                    "subject": "pilot.reviewer",
                    "tenant_id": "pilot-tenant",
                    "roles": ["consumer", "submitter", "reviewer"],
                    "clearance": "internal",
                },
                publisher_token: {
                    "subject": "pilot.publisher",
                    "tenant_id": "pilot-tenant",
                    "roles": ["consumer", "publisher"],
                    "clearance": "internal",
                },
            }
        ),
        "UKB_REQUIRE_AUTH": "true",
        "UKB_POSTGRES_PASSWORD": "database-" + "d" * 40,
        "UKB_STORE_BACKEND": "sqlalchemy",
        "UKB_CREATE_SCHEMA_ON_STARTUP": "false",
        "UKB_OBJECT_STORE_URL": "file:///app/.ukb/object-store",
        "UKB_SEARCH_BACKEND": "zvec",
        "UKB_SEARCH_SYNC_ON_QUERY": "true",
        "UKB_CORS_ALLOW_ORIGINS": "https://yashumani.github.io",
        "UKB_OIDC_ENABLED": "false",
        "UKB_AI_MODE": "local_ai",
        "UKB_AI_PROVIDER": "ollama",
        "UKB_MCP_ALLOW_APPROVAL": "false",
        "UKB_MCP_ALLOW_PUBLICATION": "false",
        "UKB_CRAWL4AI_ENABLED": "false",
        "UKB_GOOGLE_DRIVE_ENABLED": "false",
        "UKB_TALK2DATA_GRAPH_BACKEND": "memory",
    }


def test_valid_staging_environment_is_ready_without_leaking_secrets() -> None:
    values = valid_environment()

    report = validate_staging_environment(
        values,
        expected_ui_origin="https://yashumani.github.io",
    )

    assert report.ready is True
    assert report.failure_count == 0
    assert report.warning_count == 2
    serialized = report.model_dump_json()
    assert values["UKB_API_TOKEN"] not in serialized
    assert values["UKB_POSTGRES_PASSWORD"] not in serialized


def test_placeholder_and_latest_image_fail_closed() -> None:
    values = valid_environment()
    values["UKB_API_IMAGE"] = "ghcr.io/yashumani/unified-knowledge-base-api:latest"
    values["UKB_API_TOKEN"] = "replace-with-a-long-random-local-break-glass-token"
    values["UKB_POSTGRES_PASSWORD"] = "replace-with-a-long-random-database-password"

    report = validate_staging_environment(values)

    assert report.ready is False
    failed = {check.check_id for check in report.checks if check.status == CheckStatus.failed}
    assert {"immutable-api-image", "break-glass-token", "database-password"} <= failed


def test_oidc_and_graphiti_can_be_required() -> None:
    values = valid_environment()

    report = validate_staging_environment(
        values,
        require_oidc=True,
        require_graphiti=True,
    )

    assert report.ready is False
    failed = {check.check_id for check in report.checks if check.status == CheckStatus.failed}
    assert {"oidc", "graphiti"} <= failed


def test_principal_map_requires_separate_reviewer_and_publisher() -> None:
    values = valid_environment()
    shared_token = "shared-token-" + "x" * 40
    values["UKB_API_TOKENS_JSON"] = json.dumps(
        {
            shared_token: {
                "subject": "one.person",
                "tenant_id": "pilot-tenant",
                "roles": ["reviewer", "publisher"],
                "clearance": "internal",
            }
        }
    )

    report = validate_staging_environment(values)

    assert report.ready is False
    principal_check = next(check for check in report.checks if check.check_id == "principal-map")
    assert principal_check.status == CheckStatus.failed


def test_env_loader_rejects_duplicate_keys(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("UKB_ENVIRONMENT=stage\nUKB_ENVIRONMENT=prod\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate environment key"):
        load_env_file(env_file)


def test_runtime_probe_accepts_governed_private_runtime() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payloads: dict[str, object] = {
            "/health": {"status": "ok", "environment": "stage", "version": "0.3.0"},
            "/ready": {
                "status": "ready",
                "store_backend": "sqlalchemy",
                "search_backend": "zvec",
                "search_available": True,
                "ai_provider": "ollama",
                "talk2data_graph_backend": "memory",
                "talk2data_graph_available": True,
            },
            "/ai/providers": {"provider": "ollama"},
            "/ai/health": {"provider": "ollama", "available": True},
            "/search/status": {"available": True, "backend_active": "zvec"},
            "/ingestion/capabilities": {"capabilities": [{"id": "files"}]},
            "/v1/graph/status": {"backend": "memory", "available": True},
        }
        assert request.headers["authorization"] == "Bearer staging-token"
        return httpx.Response(
            200,
            json=payloads[request.url.path],
            headers={"X-Request-ID": request.headers["X-Request-ID"]},
        )

    report = probe_staging_runtime(
        base_url="https://staging.example.net",
        token="staging-token",
        transport=httpx.MockTransport(handler),
    )

    assert report.ready is True
    assert report.failure_count == 0
    assert len(report.probes) == 7
    assert all(probe.request_id for probe in report.probes)


def test_runtime_probe_fails_when_authoritative_store_is_not_sql() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/ready":
            return httpx.Response(
                200,
                json={
                    "status": "ready",
                    "store_backend": "memory",
                    "search_available": True,
                },
            )
        payloads: dict[str, object] = {
            "/health": {"status": "ok"},
            "/ai/providers": {"provider": "ollama"},
            "/ai/health": {"provider": "ollama", "available": True},
            "/search/status": {"available": True},
            "/ingestion/capabilities": {"capabilities": [{"id": "files"}]},
            "/v1/graph/status": {"available": True},
        }
        return httpx.Response(200, json=payloads[request.url.path])

    report = probe_staging_runtime(
        base_url="https://staging.example.net",
        token="staging-token",
        transport=httpx.MockTransport(handler),
    )

    assert report.ready is False
    readiness = next(probe for probe in report.probes if probe.probe_id == "ready")
    assert readiness.status == CheckStatus.failed
    assert "SQLAlchemy" in readiness.message
