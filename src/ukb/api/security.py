from __future__ import annotations

import logging
import secrets

from fastapi import Header, HTTPException, status

from ukb.config import Settings, get_settings

logger = logging.getLogger("ukb.security")


def extract_token(authorization: str | None, x_api_token: str | None) -> str | None:
    """Read the caller token from either supported header form."""

    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and value.strip():
            return value.strip()
    if x_api_token and x_api_token.strip():
        return x_api_token.strip()
    return None


def require_api_token(
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None),
) -> str:
    """Guard mutating and privileged routes with the configured shared secret.

    Returns the authenticated principal so routes can attribute audit events to
    something other than a client-supplied string.
    """

    settings = get_settings()
    if not settings.require_auth:
        return "anonymous"

    token = extract_token(authorization, x_api_token)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API token. Send 'Authorization: Bearer <token>' or 'X-API-Token: <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Constant-time comparison keeps the check free of timing side channels.
    if not secrets.compare_digest(token, settings.api_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API token.",
        )

    return "api-token"


def warn_on_insecure_configuration(settings: Settings) -> list[str]:
    """Emit loud startup warnings so a weak config cannot pass unnoticed."""

    warnings: list[str] = []
    if not settings.require_auth:
        warnings.append(
            "UKB_REQUIRE_AUTH is false. Every ingestion, review, and governance "
            "endpoint is unauthenticated. Do not run this way with real data."
        )
    elif settings.api_token_is_default:
        warnings.append(
            "UKB_API_TOKEN is still the shipped development default. Set a unique "
            "token before exposing the API beyond localhost."
        )

    if settings.default_user_clearance.strip().lower() == "restricted":
        warnings.append(
            "UKB_DEFAULT_USER_CLEARANCE is 'restricted'. Every caller can read "
            "restricted knowledge objects."
        )

    for message in warnings:
        logger.warning(message)
    return warnings
