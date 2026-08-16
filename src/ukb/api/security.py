from __future__ import annotations

import json
import logging
import secrets
from dataclasses import dataclass
from typing import Any

from fastapi import Header, HTTPException, status

from ukb.config import Settings, get_settings
from ukb.models import Sensitivity

logger = logging.getLogger("ukb.security")


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    roles: frozenset[str]
    clearance: Sensitivity
    auth_method: str = "api_token"

    def has_any_role(self, roles: set[str]) -> bool:
        return bool(self.roles.intersection(roles))


def extract_token(authorization: str | None, x_api_token: str | None) -> str | None:
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and value.strip():
            return value.strip()
    if x_api_token and x_api_token.strip():
        return x_api_token.strip()
    return None


def _clearance(raw: object, fallback: str) -> Sensitivity:
    value = str(raw or fallback).strip().lower()
    try:
        return Sensitivity(value)
    except ValueError:
        return Sensitivity.internal


def _configured_principals(settings: Settings) -> dict[str, Principal]:
    try:
        payload: Any = json.loads(settings.api_tokens_json or "{}")
    except json.JSONDecodeError:
        logger.error("UKB_API_TOKENS_JSON is invalid JSON; configured token principals are disabled.")
        return {}
    if not isinstance(payload, dict):
        return {}

    principals: dict[str, Principal] = {}
    for token, definition in payload.items():
        if not isinstance(token, str) or not token:
            continue
        if isinstance(definition, str):
            subject = definition.strip()
            roles = frozenset({"consumer"})
            clearance = _clearance(None, settings.default_user_clearance)
        elif isinstance(definition, dict):
            subject = str(definition.get("subject", "")).strip()
            raw_roles = definition.get("roles", ["consumer"])
            roles = frozenset(
                str(role).strip()
                for role in raw_roles
                if str(role).strip()
            ) if isinstance(raw_roles, list) else frozenset({"consumer"})
            clearance = _clearance(definition.get("clearance"), settings.default_user_clearance)
        else:
            continue
        if subject:
            principals[token] = Principal(subject=subject, roles=roles, clearance=clearance)
    return principals


def authenticate_token(token: str, settings: Settings | None = None) -> Principal | None:
    active = settings or get_settings()
    for configured_token, principal in _configured_principals(active).items():
        if secrets.compare_digest(token, configured_token):
            return principal

    if secrets.compare_digest(token, active.api_token):
        return Principal(
            subject="local-admin",
            roles=frozenset({"consumer", "submitter", "reviewer", "publisher", "governance_admin"}),
            clearance=_clearance(None, active.default_user_clearance),
            auth_method="legacy_api_token",
        )
    return None


def require_principal(
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None),
) -> Principal:
    settings = get_settings()
    if not settings.require_auth:
        return Principal(
            subject="anonymous",
            roles=frozenset({"consumer", "submitter", "reviewer", "publisher"}),
            clearance=_clearance(None, settings.default_user_clearance),
            auth_method="disabled",
        )

    token = extract_token(authorization, x_api_token)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API token. Send 'Authorization: Bearer <token>' or 'X-API-Token: <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    principal = authenticate_token(token, settings)
    if principal is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API token.")
    return principal


def require_api_token(
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None),
) -> str:
    """Backward-compatible dependency returning the authenticated subject."""

    return require_principal(authorization=authorization, x_api_token=x_api_token).subject


def require_roles(principal: Principal, allowed: set[str]) -> None:
    if principal.has_any_role(allowed):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"This action requires one of these roles: {', '.join(sorted(allowed))}.",
    )


def warn_on_insecure_configuration(settings: Settings) -> list[str]:
    warnings: list[str] = []
    if not settings.require_auth:
        warnings.append(
            "UKB_REQUIRE_AUTH is false. Every ingestion, review, publication, and governance endpoint is unauthenticated."
        )
    elif settings.api_token_is_default and settings.api_tokens_json.strip() in {"", "{}"}:
        warnings.append(
            "UKB_API_TOKEN is still the shipped development default and no token-principal map is configured."
        )
    if settings.default_user_clearance.strip().lower() == "restricted":
        warnings.append("UKB_DEFAULT_USER_CLEARANCE is restricted; every legacy token holder can read restricted objects.")
    if settings.environment.lower() in {"prod", "production"} and not settings.oidc_enabled:
        warnings.append("OIDC is not enabled. The token-principal map is an interim deployment mode, not enterprise SSO.")
    for message in warnings:
        logger.warning(message)
    return warnings
