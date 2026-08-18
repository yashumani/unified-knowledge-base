from __future__ import annotations

import json
import logging
import secrets
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Mapping

import jwt
from fastapi import Header, HTTPException, status
from jwt import InvalidTokenError, PyJWKClient

from ukb.config import Settings, get_settings
from ukb.models import Sensitivity

logger = logging.getLogger("ukb.security")


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset[str]
    clearance: Sensitivity
    tenant_id: str = "default"
    auth_method: str = "token"

    def has_any_role(self, allowed: set[str]) -> bool:
        return bool(self.roles.intersection(allowed))


PrincipalLike = Principal | str


def extract_token(authorization: str | None, x_api_token: str | None) -> str | None:
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.casefold() == "bearer" and value.strip():
            return value.strip()
    if x_api_token and x_api_token.strip():
        return x_api_token.strip()
    return None


@lru_cache(maxsize=8)
def _jwks_client(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True)


def _parse_clearance(value: object, default: str) -> Sensitivity:
    raw = str(value or default).strip().casefold()
    try:
        return Sensitivity(raw)
    except ValueError:
        return Sensitivity.internal


def _claim_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in value.replace(",", " ").split() if part.strip()]
    if isinstance(value, (list, tuple, set, frozenset)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def principal_from_oidc_claims(claims: Mapping[str, Any], settings: Settings) -> Principal:
    subject = str(claims.get(settings.oidc_subject_claim, "")).strip()
    if not subject:
        raise InvalidTokenError(
            f"OIDC token is missing the configured subject claim {settings.oidc_subject_claim!r}."
        )
    tenant_id = str(claims.get(settings.oidc_tenant_claim) or settings.default_tenant_id).strip()
    if not tenant_id:
        raise InvalidTokenError(
            f"OIDC token is missing the configured tenant claim {settings.oidc_tenant_claim!r}."
        )
    roles = {
        *[value.casefold() for value in _claim_values(claims.get(settings.oidc_roles_claim))],
        *[value.casefold() for value in _claim_values(claims.get(settings.oidc_groups_claim))],
    }
    if not roles:
        roles.add("consumer")
    clearance = _parse_clearance(
        claims.get(settings.oidc_clearance_claim),
        settings.default_user_clearance,
    )
    return Principal(
        subject=subject,
        tenant_id=tenant_id,
        roles=frozenset(roles),
        clearance=clearance,
        auth_method="oidc",
    )


def _verify_oidc_token(token: str, settings: Settings) -> Principal:
    if not settings.oidc_enabled:
        raise InvalidTokenError("OIDC authentication is disabled.")
    if not settings.oidc_issuer or not settings.oidc_audience or not settings.oidc_jwks_url:
        raise InvalidTokenError(
            "OIDC requires UKB_OIDC_ISSUER, UKB_OIDC_AUDIENCE, and UKB_OIDC_JWKS_URL."
        )
    signing_key = _jwks_client(settings.oidc_jwks_url).get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=settings.oidc_algorithm_list,
        audience=settings.oidc_audience,
        issuer=settings.oidc_issuer,
        options={"require": ["exp", "iat", settings.oidc_subject_claim]},
    )
    if not isinstance(claims, dict):
        raise InvalidTokenError("OIDC token claims were not an object.")
    return principal_from_oidc_claims(claims, settings)


def _configured_principals(settings: Settings) -> dict[str, Principal]:
    try:
        raw = json.loads(settings.api_tokens_json or "{}")
    except json.JSONDecodeError:
        logger.error("UKB_API_TOKENS_JSON is not valid JSON; configured tokens were ignored.")
        return {}
    if not isinstance(raw, dict):
        return {}
    principals: dict[str, Principal] = {}
    for token, config in raw.items():
        if not isinstance(token, str) or not token or not isinstance(config, dict):
            continue
        subject = str(config.get("subject") or "").strip()
        tenant_id = str(config.get("tenant_id") or settings.default_tenant_id).strip()
        if not subject or not tenant_id:
            continue
        roles = frozenset(value.casefold() for value in _claim_values(config.get("roles")))
        principals[token] = Principal(
            subject=subject,
            tenant_id=tenant_id,
            roles=roles or frozenset({"consumer"}),
            clearance=_parse_clearance(
                config.get("clearance"),
                settings.default_user_clearance,
            ),
            auth_method="configured_token",
        )
    return principals


def authenticate_token(token: str, settings: Settings) -> Principal:
    for configured_token, principal in _configured_principals(settings).items():
        if secrets.compare_digest(token, configured_token):
            return principal

    if secrets.compare_digest(token, settings.api_token):
        return Principal(
            subject="local-api-token",
            tenant_id=settings.default_tenant_id,
            roles=frozenset(
                {
                    "consumer",
                    "submitter",
                    "reviewer",
                    "publisher",
                    "domain_pack_admin",
                    "source_admin",
                    "index_admin",
                    "auditor",
                    "governance_admin",
                }
            ),
            clearance=_parse_clearance(None, settings.default_user_clearance),
            auth_method="legacy_token",
        )

    if settings.oidc_enabled:
        try:
            return _verify_oidc_token(token, settings)
        except InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Invalid API token or OIDC access token: {exc}",
            ) from exc
        except Exception as exc:
            logger.exception("OIDC verification failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The configured identity provider could not be verified.",
            ) from exc

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API token.")


def require_principal(
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None),
) -> Principal:
    settings = get_settings()
    if not settings.require_auth:
        return Principal(
            subject="anonymous",
            tenant_id=settings.default_tenant_id,
            roles=frozenset(
                {
                    "consumer",
                    "submitter",
                    "reviewer",
                    "publisher",
                    "domain_pack_admin",
                    "source_admin",
                    "index_admin",
                }
            ),
            clearance=_parse_clearance(None, settings.default_user_clearance),
            auth_method="disabled",
        )

    token = extract_token(authorization, x_api_token)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer or API token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authenticate_token(token, settings)


# Compatibility alias for older adapters/tests. New code should depend on
# require_principal and use the authenticated subject, tenant and roles.
def require_api_token(
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None),
) -> str:
    return require_principal(authorization, x_api_token).subject


def require_roles(principal: Principal, allowed: set[str]) -> Principal:
    if not principal.has_any_role({role.casefold() for role in allowed}):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires one of these roles: {', '.join(sorted(allowed))}.",
        )
    return principal


def warn_on_insecure_configuration(settings: Settings) -> list[str]:
    warnings: list[str] = []
    if not settings.require_auth:
        warnings.append("unauthenticated access is enabled. Do not run this way with real data.")
    elif settings.api_token_is_default and not settings.oidc_enabled:
        warnings.append(
            "UKB_API_TOKEN is still the shipped development default and OIDC is disabled. "
            "Set per-user, tenant-bound tokens or OIDC before exposing the API beyond localhost."
        )
    if settings.oidc_enabled and (
        not settings.oidc_issuer
        or not settings.oidc_audience
        or not settings.oidc_jwks_url
    ):
        warnings.append(
            "OIDC is enabled but issuer, audience, or JWKS URL is missing; authenticated requests will fail."
        )
    if settings.default_user_clearance.strip().casefold() == "restricted":
        warnings.append("Default clearance is restricted; every fallback principal can read restricted objects.")
    if settings.store_backend.casefold() == "memory" and settings.environment.casefold() in {"stage", "prod"}:
        warnings.append("Production is configured with the in-memory store; all state will be lost on restart.")
    for message in warnings:
        logger.warning(message)
    return warnings
