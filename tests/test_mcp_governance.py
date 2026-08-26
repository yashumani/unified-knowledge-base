from __future__ import annotations

from ukb.config import Settings
from ukb.mcp import server as mcp_server
from ukb.models import Sensitivity


def test_mcp_principal_is_configured_and_least_privilege(monkeypatch) -> None:
    configured = Settings(
        mcp_subject="talk2data-mcp",
        mcp_tenant_id="tenant-blue",
        mcp_roles="consumer,submitter",
        mcp_clearance="confidential",
        mcp_allow_approval=False,
        mcp_allow_publication=False,
    )
    monkeypatch.setattr(mcp_server, "settings", configured)

    principal = mcp_server.get_mcp_principal()
    assert principal.subject == "talk2data-mcp"
    assert principal.tenant_id == "tenant-blue"
    assert principal.roles == frozenset({"consumer", "submitter"})
    assert principal.clearance == Sensitivity.confidential
    assert "reviewer" not in principal.roles
    assert "publisher" not in principal.roles


def test_mcp_approval_and_publication_fail_closed(monkeypatch) -> None:
    configured = Settings(
        mcp_allow_approval=False,
        mcp_allow_publication=False,
    )
    monkeypatch.setattr(mcp_server, "settings", configured)

    approval = mcp_server.approve_review_item("review-1")
    publication = mcp_server.publish_review_item("review-1")
    assert approval["error"] == "approval_not_permitted_over_mcp"
    assert publication["error"] == "publication_not_permitted_over_mcp"


def test_mcp_cache_invalidation_fails_closed(monkeypatch) -> None:
    configured = Settings(mcp_allow_cache_invalidation=False)
    monkeypatch.setattr(mcp_server, "settings", configured)

    result = mcp_server.invalidate_cache()
    assert result["error"] == "cache_invalidation_not_permitted_over_mcp"
