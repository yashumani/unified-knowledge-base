from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field


class CheckStatus(StrEnum):
    passed = "passed"
    failed = "failed"
    warning = "warning"
    skipped = "skipped"


class StagingCheck(BaseModel):
    check_id: str
    status: CheckStatus
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class StagingReadinessReport(BaseModel):
    generated_at: datetime
    environment_file: str | None = None
    expected_ui_origin: str | None = None
    checks: list[StagingCheck]
    ready: bool
    failure_count: int
    warning_count: int


class RuntimeProbe(BaseModel):
    probe_id: str
    method: str
    path: str
    status: CheckStatus
    message: str
    status_code: int | None = None
    request_id: str | None = None
    elapsed_ms: float | None = None
    response: dict[str, Any] | list[Any] | None = None


class StagingAcceptanceReport(BaseModel):
    generated_at: datetime
    base_url: str
    probes: list[RuntimeProbe]
    ready: bool
    failure_count: int
    warning_count: int


_PLACEHOLDER_FRAGMENTS = (
    "replace-with",
    "replace-",
    "change-me",
    "changeme",
    "dev-token",
    "example.org",
    "example.com",
    "placeholder",
    "your-token",
    "your-password",
)

_SECRET_KEYS = {
    "UKB_API_TOKEN",
    "UKB_POSTGRES_PASSWORD",
    "UKB_GOOGLE_DRIVE_ACCESS_TOKEN",
    "UKB_CRAWL4AI_API_TOKEN",
    "UKB_GRAPHITI_API_KEY",
}

_ALLOWED_OBJECT_STORE_SCHEMES = {"file", "s3", "minio"}
_REQUIRED_ACCEPTANCE_PROBES = (
    ("health", "GET", "/health"),
    ("ready", "GET", "/ready"),
    ("ai-providers", "GET", "/ai/providers"),
    ("ai-health", "GET", "/ai/health"),
    ("search-status", "GET", "/search/status"),
    ("ingestion-capabilities", "GET", "/ingestion/capabilities"),
    ("graph-status", "GET", "/v1/graph/status"),
)


def load_env_file(path: str | Path) -> dict[str, str]:
    """Load a Docker-style environment file without evaluating shell expressions."""

    env_path = Path(path)
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"{env_path}:{line_number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"{env_path}:{line_number}: invalid environment key {key!r}")
        if key in values:
            raise ValueError(f"{env_path}:{line_number}: duplicate environment key {key}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def validate_staging_environment(
    values: Mapping[str, str],
    *,
    environment_file: str | None = None,
    expected_ui_origin: str | None = None,
    require_oidc: bool = False,
    require_graphiti: bool = False,
) -> StagingReadinessReport:
    checks: list[StagingCheck] = []

    def add(
        check_id: str,
        status: CheckStatus,
        message: str,
        **details: Any,
    ) -> None:
        checks.append(
            StagingCheck(
                check_id=check_id,
                status=status,
                message=message,
                details=details,
            )
        )

    environment = values.get("UKB_ENVIRONMENT", "").strip().casefold()
    add(
        "environment",
        CheckStatus.passed if environment in {"stage", "staging", "prod"} else CheckStatus.failed,
        (
            f"Runtime environment is {environment!r}."
            if environment in {"stage", "staging", "prod"}
            else "UKB_ENVIRONMENT must be stage, staging, or prod."
        ),
    )

    image = values.get("UKB_API_IMAGE", "").strip()
    image_ok = image.startswith("ghcr.io/") and bool(
        re.search(r"(?::[^/:]+|@sha256:[a-f0-9]{64})$", image)
    )
    image_immutable = image_ok and not image.endswith(":latest")
    add(
        "immutable-api-image",
        CheckStatus.passed if image_immutable else CheckStatus.failed,
        (
            f"API image is pinned to {image}."
            if image_immutable
            else "UKB_API_IMAGE must use a non-latest GHCR tag or an immutable digest."
        ),
    )

    api_token = values.get("UKB_API_TOKEN", "")
    api_token_ok = _strong_secret(api_token, minimum_length=32)
    add(
        "break-glass-token",
        CheckStatus.passed if api_token_ok else CheckStatus.failed,
        (
            "Break-glass API token is non-placeholder and meets the minimum length."
            if api_token_ok
            else "UKB_API_TOKEN must be a non-placeholder secret of at least 32 characters."
        ),
    )

    database_password = values.get("UKB_POSTGRES_PASSWORD", "")
    database_password_ok = _strong_secret(database_password, minimum_length=24)
    add(
        "database-password",
        CheckStatus.passed if database_password_ok else CheckStatus.failed,
        (
            "Database password is non-placeholder and meets the minimum length."
            if database_password_ok
            else "UKB_POSTGRES_PASSWORD must be a non-placeholder secret of at least 24 characters."
        ),
    )
    add(
        "secret-separation",
        CheckStatus.passed
        if api_token_ok and database_password_ok and api_token != database_password
        else CheckStatus.failed,
        (
            "API and database secrets are distinct."
            if api_token_ok and database_password_ok and api_token != database_password
            else "API and database credentials must be valid and distinct."
        ),
    )

    tenant_id = values.get("UKB_DEFAULT_TENANT_ID", "").strip()
    tenant_ok = bool(tenant_id) and not _looks_placeholder(tenant_id)
    add(
        "default-tenant",
        CheckStatus.passed if tenant_ok else CheckStatus.failed,
        (
            f"Default tenant is {tenant_id!r}."
            if tenant_ok
            else "UKB_DEFAULT_TENANT_ID must be explicit and non-placeholder."
        ),
    )

    token_map, token_map_error = _parse_principal_map(values.get("UKB_API_TOKENS_JSON", ""))
    if token_map_error:
        add("principal-map", CheckStatus.failed, token_map_error)
    else:
        reviewer_subjects: set[str] = set()
        publisher_subjects: set[str] = set()
        weak_tokens: list[str] = []
        wrong_tenants: list[str] = []
        for token, principal in token_map.items():
            roles = {str(role).casefold() for role in principal.get("roles", [])}
            subject = str(principal.get("subject", "")).strip()
            if "reviewer" in roles or "governance_admin" in roles:
                reviewer_subjects.add(subject)
            if "publisher" in roles or "governance_admin" in roles:
                publisher_subjects.add(subject)
            if not _strong_secret(token, minimum_length=24):
                weak_tokens.append(_redact(token))
            if tenant_ok and principal.get("tenant_id") != tenant_id:
                wrong_tenants.append(subject or _redact(token))
        separated = bool(reviewer_subjects and publisher_subjects) and bool(
            reviewer_subjects.symmetric_difference(publisher_subjects)
        )
        map_ok = len(token_map) >= 2 and separated and not weak_tokens and not wrong_tenants
        add(
            "principal-map",
            CheckStatus.passed if map_ok else CheckStatus.failed,
            (
                "Reviewer and publisher principals are separately attributable."
                if map_ok
                else (
                    "UKB_API_TOKENS_JSON must define at least two strong tenant-bound tokens "
                    "with separately attributable reviewer and publisher identities."
                )
            ),
            principal_count=len(token_map),
            reviewer_subjects=sorted(reviewer_subjects),
            publisher_subjects=sorted(publisher_subjects),
            weak_tokens=weak_tokens,
            wrong_tenants=wrong_tenants,
        )

    add(
        "authentication-required",
        CheckStatus.passed if _as_bool(values.get("UKB_REQUIRE_AUTH", "true")) else CheckStatus.failed,
        (
            "Authentication is required."
            if _as_bool(values.get("UKB_REQUIRE_AUTH", "true"))
            else "UKB_REQUIRE_AUTH must be true."
        ),
    )

    add(
        "authoritative-store",
        CheckStatus.passed
        if values.get("UKB_STORE_BACKEND", "").casefold() == "sqlalchemy"
        else CheckStatus.failed,
        (
            "SQLAlchemy is configured as the authoritative store."
            if values.get("UKB_STORE_BACKEND", "").casefold() == "sqlalchemy"
            else "UKB_STORE_BACKEND must be sqlalchemy."
        ),
    )
    add(
        "migration-controlled-schema",
        CheckStatus.passed
        if not _as_bool(values.get("UKB_CREATE_SCHEMA_ON_STARTUP", "true"))
        else CheckStatus.failed,
        (
            "Schema creation is migration-controlled."
            if not _as_bool(values.get("UKB_CREATE_SCHEMA_ON_STARTUP", "true"))
            else "UKB_CREATE_SCHEMA_ON_STARTUP must be false for staging."
        ),
    )

    object_store_url = values.get("UKB_OBJECT_STORE_URL", "").strip()
    object_store_scheme = urlparse(object_store_url).scheme.casefold()
    add(
        "object-store",
        CheckStatus.passed
        if object_store_scheme in _ALLOWED_OBJECT_STORE_SCHEMES
        else CheckStatus.failed,
        (
            f"Object store uses the {object_store_scheme!r} scheme."
            if object_store_scheme in _ALLOWED_OBJECT_STORE_SCHEMES
            else "UKB_OBJECT_STORE_URL must use file, s3, or minio."
        ),
    )

    search_backend = values.get("UKB_SEARCH_BACKEND", "").casefold()
    add(
        "retrieval-index",
        CheckStatus.passed if search_backend == "zvec" else CheckStatus.failed,
        (
            "Zvec is configured as the derived retrieval index."
            if search_backend == "zvec"
            else "UKB_SEARCH_BACKEND must be zvec for the private-runtime pilot."
        ),
    )
    add(
        "retrieval-sync",
        CheckStatus.passed
        if _as_bool(values.get("UKB_SEARCH_SYNC_ON_QUERY", "true"))
        else CheckStatus.warning,
        (
            "Synchronous index reconciliation is enabled for the pilot."
            if _as_bool(values.get("UKB_SEARCH_SYNC_ON_QUERY", "true"))
            else "UKB_SEARCH_SYNC_ON_QUERY is disabled; ensure the background worker is monitored."
        ),
    )

    cors_origins = _split_csv(values.get("UKB_CORS_ALLOW_ORIGINS", ""))
    insecure_origins = [
        origin
        for origin in cors_origins
        if origin == "*" or urlparse(origin).scheme != "https" or "localhost" in origin.casefold()
    ]
    expected_missing = bool(expected_ui_origin and expected_ui_origin not in cors_origins)
    cors_ok = bool(cors_origins) and not insecure_origins and not expected_missing
    add(
        "cors",
        CheckStatus.passed if cors_ok else CheckStatus.failed,
        (
            "CORS is restricted to explicit HTTPS origins."
            if cors_ok
            else "CORS must contain explicit HTTPS origins and include the expected UI origin."
        ),
        origins=cors_origins,
        insecure_origins=insecure_origins,
        expected_origin_missing=expected_missing,
    )

    oidc_enabled = _as_bool(values.get("UKB_OIDC_ENABLED", "false"))
    oidc_fields = {
        "issuer": values.get("UKB_OIDC_ISSUER", "").strip(),
        "audience": values.get("UKB_OIDC_AUDIENCE", "").strip(),
        "jwks_url": values.get("UKB_OIDC_JWKS_URL", "").strip(),
    }
    oidc_complete = oidc_enabled and all(oidc_fields.values()) and all(
        urlparse(value).scheme == "https"
        for key, value in oidc_fields.items()
        if key != "audience"
    )
    if require_oidc:
        add(
            "oidc",
            CheckStatus.passed if oidc_complete else CheckStatus.failed,
            (
                "OIDC is configured with issuer, audience, and JWKS URL."
                if oidc_complete
                else "OIDC is required but issuer, audience, or HTTPS JWKS configuration is incomplete."
            ),
        )
    elif oidc_complete:
        add("oidc", CheckStatus.passed, "OIDC is configured for attributable user identity.")
    else:
        add(
            "oidc",
            CheckStatus.warning,
            "OIDC is not complete; the pilot may use mapped tokens, but production must use OIDC.",
        )

    ai_ok = (
        values.get("UKB_AI_MODE", "").casefold() == "local_ai"
        and values.get("UKB_AI_PROVIDER", "").casefold() == "ollama"
    )
    add(
        "local-ai",
        CheckStatus.passed if ai_ok else CheckStatus.failed,
        (
            "Local Ollama is configured as the advisory AI provider."
            if ai_ok
            else "UKB_AI_MODE must be local_ai and UKB_AI_PROVIDER must be ollama."
        ),
    )

    add(
        "mcp-governance",
        CheckStatus.passed
        if not _as_bool(values.get("UKB_MCP_ALLOW_APPROVAL", "false"))
        and not _as_bool(values.get("UKB_MCP_ALLOW_PUBLICATION", "false"))
        else CheckStatus.failed,
        (
            "MCP approval and publication remain disabled."
            if not _as_bool(values.get("UKB_MCP_ALLOW_APPROVAL", "false"))
            and not _as_bool(values.get("UKB_MCP_ALLOW_PUBLICATION", "false"))
            else "MCP approval and publication must remain disabled in the pilot."
        ),
    )

    crawl_enabled = _as_bool(values.get("UKB_CRAWL4AI_ENABLED", "false"))
    if crawl_enabled:
        allowed_hosts = _split_csv(values.get("UKB_WEB_ALLOWED_HOSTS", ""))
        crawl_ok = (
            bool(allowed_hosts)
            and "*" not in allowed_hosts
            and not any(_looks_placeholder(host) for host in allowed_hosts)
            and not _as_bool(values.get("UKB_WEB_ALLOW_PRIVATE_NETWORKS", "false"))
            and _as_bool(values.get("UKB_WEB_RESPECT_ROBOTS", "true"))
            and _as_bool(values.get("UKB_WEB_ROBOTS_FAIL_CLOSED", "true"))
        )
        add(
            "crawl4ai-policy",
            CheckStatus.passed if crawl_ok else CheckStatus.failed,
            (
                "Crawl4AI is constrained by explicit hosts, public egress, and fail-closed robots policy."
                if crawl_ok
                else (
                    "Enabled Crawl4AI requires non-placeholder allowlisted hosts, private-network "
                    "blocking, and fail-closed robots enforcement."
                )
            ),
            allowed_hosts=allowed_hosts,
        )
    else:
        add("crawl4ai-policy", CheckStatus.skipped, "Crawl4AI is disabled for this pilot.")

    drive_enabled = _as_bool(values.get("UKB_GOOGLE_DRIVE_ENABLED", "false"))
    if drive_enabled:
        drive_token = values.get("UKB_GOOGLE_DRIVE_ACCESS_TOKEN", "")
        drive_ok = _strong_secret(drive_token, minimum_length=20)
        add(
            "google-drive",
            CheckStatus.passed if drive_ok else CheckStatus.failed,
            (
                "Google Drive is enabled with a server-side token."
                if drive_ok
                else "Enabled Google Drive ingestion requires a non-placeholder server-side token."
            ),
        )
    else:
        add("google-drive", CheckStatus.skipped, "Google Drive ingestion is disabled.")

    graph_backend = values.get("UKB_TALK2DATA_GRAPH_BACKEND", "memory").casefold()
    graphiti_complete = (
        graph_backend == "graphiti"
        and urlparse(values.get("UKB_GRAPHITI_BASE_URL", "")).scheme in {"http", "https"}
        and _strong_secret(values.get("UKB_GRAPHITI_API_KEY", ""), minimum_length=16)
    )
    if require_graphiti:
        add(
            "graphiti",
            CheckStatus.passed if graphiti_complete else CheckStatus.failed,
            (
                "Graphiti is configured as a replaceable temporal projection."
                if graphiti_complete
                else "Graphiti is required but its backend URL or API key is incomplete."
            ),
        )
    elif graphiti_complete:
        add("graphiti", CheckStatus.passed, "Graphiti is configured as a derived projection.")
    else:
        add(
            "graphiti",
            CheckStatus.warning,
            "Graphiti is not configured; the canonical SQL memory remains available.",
        )

    present_placeholders = sorted(
        key
        for key, value in values.items()
        if key in _SECRET_KEYS and value and _looks_placeholder(value)
    )
    add(
        "placeholder-secrets",
        CheckStatus.passed if not present_placeholders else CheckStatus.failed,
        (
            "No placeholder secret values were detected."
            if not present_placeholders
            else "Placeholder values remain in secret-bearing settings."
        ),
        keys=present_placeholders,
    )

    failure_count = sum(check.status == CheckStatus.failed for check in checks)
    warning_count = sum(check.status == CheckStatus.warning for check in checks)
    return StagingReadinessReport(
        generated_at=datetime.now(UTC),
        environment_file=environment_file,
        expected_ui_origin=expected_ui_origin,
        checks=checks,
        ready=failure_count == 0,
        failure_count=failure_count,
        warning_count=warning_count,
    )


def probe_staging_runtime(
    *,
    base_url: str,
    token: str,
    timeout_seconds: float = 20.0,
    transport: httpx.BaseTransport | None = None,
) -> StagingAcceptanceReport:
    normalized_base_url = base_url.rstrip("/")
    parsed = urlparse(normalized_base_url)
    probes: list[RuntimeProbe] = []
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base_url must be an absolute HTTP or HTTPS URL")
    if not token:
        raise ValueError("token must not be empty")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "UKB-Staging-Acceptance/0.4",
    }
    with httpx.Client(
        base_url=normalized_base_url + "/",
        timeout=timeout_seconds,
        transport=transport,
        headers=headers,
    ) as client:
        for probe_id, method, path in _REQUIRED_ACCEPTANCE_PROBES:
            request_id = f"stage_{uuid4().hex[:16]}"
            started = datetime.now(UTC)
            try:
                response = client.request(
                    method,
                    path.lstrip("/"),
                    headers={"X-Request-ID": request_id},
                )
                elapsed_ms = (datetime.now(UTC) - started).total_seconds() * 1000
                response_request_id = response.headers.get("X-Request-ID", request_id)
                payload: dict[str, Any] | list[Any] | None
                try:
                    decoded = response.json()
                    payload = decoded if isinstance(decoded, (dict, list)) else None
                except ValueError:
                    payload = None
                semantic_error = _semantic_probe_error(probe_id, payload)
                passed = response.is_success and semantic_error is None
                probes.append(
                    RuntimeProbe(
                        probe_id=probe_id,
                        method=method,
                        path=path,
                        status=CheckStatus.passed if passed else CheckStatus.failed,
                        message=(
                            "Probe passed."
                            if passed
                            else semantic_error
                            or f"Probe returned HTTP {response.status_code}."
                        ),
                        status_code=response.status_code,
                        request_id=response_request_id,
                        elapsed_ms=round(elapsed_ms, 3),
                        response=payload,
                    )
                )
            except httpx.HTTPError as exc:
                probes.append(
                    RuntimeProbe(
                        probe_id=probe_id,
                        method=method,
                        path=path,
                        status=CheckStatus.failed,
                        message=f"Probe failed: {exc}",
                        request_id=request_id,
                    )
                )

    failure_count = sum(probe.status == CheckStatus.failed for probe in probes)
    warning_count = sum(probe.status == CheckStatus.warning for probe in probes)
    return StagingAcceptanceReport(
        generated_at=datetime.now(UTC),
        base_url=normalized_base_url,
        probes=probes,
        ready=failure_count == 0,
        failure_count=failure_count,
        warning_count=warning_count,
    )


def _semantic_probe_error(
    probe_id: str,
    payload: dict[str, Any] | list[Any] | None,
) -> str | None:
    if not isinstance(payload, dict):
        return "Probe did not return a JSON object."
    if probe_id == "health" and payload.get("status") != "ok":
        return "Health endpoint did not report status=ok."
    if probe_id == "ready":
        if payload.get("status") != "ready":
            return "Readiness endpoint did not report status=ready."
        if payload.get("store_backend") != "sqlalchemy":
            return "Readiness endpoint is not using the SQLAlchemy authoritative store."
        if not payload.get("search_available"):
            return "Readiness endpoint reports the search projection unavailable."
    if probe_id == "search-status" and not payload.get("available"):
        return "Search status reports the retrieval projection unavailable."
    if probe_id == "ingestion-capabilities" and not payload.get("capabilities"):
        return "Ingestion capabilities are empty."
    if probe_id == "graph-status" and not payload.get("available"):
        return "Graph status reports no available graph projection."
    return None


def _parse_principal_map(raw: str) -> tuple[dict[str, dict[str, Any]], str | None]:
    if not raw.strip():
        return {}, "UKB_API_TOKENS_JSON is required for the token-based staging pilot."
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {}, f"UKB_API_TOKENS_JSON is invalid JSON: {exc.msg}."
    if not isinstance(parsed, dict):
        return {}, "UKB_API_TOKENS_JSON must be a JSON object keyed by token."
    normalized: dict[str, dict[str, Any]] = {}
    for token, principal in parsed.items():
        if not isinstance(token, str) or not isinstance(principal, dict):
            return {}, "Each principal mapping must use a string token and object value."
        roles = principal.get("roles")
        if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
            return {}, "Each principal mapping must contain a string roles array."
        normalized[token] = principal
    return normalized, None


def _as_bool(value: str) -> bool:
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _looks_placeholder(value: str) -> bool:
    normalized = value.strip().casefold()
    return any(fragment in normalized for fragment in _PLACEHOLDER_FRAGMENTS)


def _strong_secret(value: str, *, minimum_length: int) -> bool:
    return len(value.strip()) >= minimum_length and not _looks_placeholder(value)


def _redact(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"
