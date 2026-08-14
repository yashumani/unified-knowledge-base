from __future__ import annotations

from ukb.config import get_settings
from ukb.models import AuditEvent, ContextPackRequest, IngestionSubmission, ReviewDecision
from ukb.services.access import AccessPolicyService
from ukb.services.compiler import BrainCompiler
from ukb.services.context_pack import ContextPackService
from ukb.services.governance import GovernanceService
from ukb.store import store

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "The MCP extra is not installed. Run: pip install -e '.[mcp]'"
    ) from exc


settings = get_settings()
mcp = FastMCP(settings.mcp_server_name)

access_policy = AccessPolicyService.from_settings(settings)
compiler = BrainCompiler()
governance = GovernanceService(store)
context_pack_service = ContextPackService(store, access_policy=access_policy)

# MCP clients are LLM agents. They are treated as one unprivileged principal so
# an agent cannot select its own clearance by naming a user.
MCP_PRINCIPAL = "mcp-client"


@mcp.tool()
def submit_context(
    title: str,
    content: str,
    submitted_by: str,
    source_type: str = "manual",
    domain: str = "general",
    sensitivity: str = "internal",
) -> dict:
    """Submit context for AI classification and human review.

    This does not publish knowledge directly. It creates a review item.
    """

    submission = IngestionSubmission(
        title=title,
        content=content,
        submitted_by=submitted_by,
        source_type=source_type,
        domain=domain,
        sensitivity=sensitivity,
    )
    source, review_item = compiler.compile_submission(submission)
    store.add_source(source)
    store.add_review_item(review_item)
    store.add_audit_event(
        AuditEvent(
            event_type="submission_created",
            actor=submitted_by,
            target_id=review_item.id,
            details={
                "source_id": source.source_id,
                "domain": domain,
                "adapter": "mcp",
            },
        )
    )
    return review_item.model_dump(mode="json")


@mcp.tool()
def list_review_items() -> list[dict]:
    """List knowledge candidates waiting for human review."""

    return [
        item.model_dump(mode="json")
        for item in governance.list_queue()
        if access_policy.can_access(MCP_PRINCIPAL, item.candidate_object)
    ]


@mcp.tool()
def approve_review_item(review_item_id: str, reviewed_by: str, comment: str | None = None) -> dict:
    """Approve a review item. Disabled by default; approval is a human gate.

    The platform rule is that LLM output is a suggestion and only human review
    approves knowledge. Exposing approval as an agent tool breaks that rule, so
    it stays off unless an operator sets UKB_MCP_ALLOW_APPROVAL=true for a
    supervised environment.
    """

    if not settings.mcp_allow_approval:
        store.add_audit_event(
            AuditEvent(
                event_type="mcp_approval_blocked",
                actor=reviewed_by,
                target_id=review_item_id,
                details={"reason": "mcp_allow_approval_disabled"},
            )
        )
        return {
            "error": "approval_not_permitted_over_mcp",
            "detail": (
                "Approving knowledge is a human review gate and is disabled for MCP "
                "clients. Use the REST API or CLI as an authenticated reviewer."
            ),
            "review_item_id": review_item_id,
        }

    decision = ReviewDecision(reviewed_by=reviewed_by, comment=comment)
    return governance.approve(review_item_id, decision).model_dump(mode="json")


@mcp.tool()
def search_brain(query: str, domain: str | None = None) -> list[dict]:
    """Search approved brain objects using the scaffold retrieval service."""

    domains = [domain] if domain else []
    pack = context_pack_service.build(
        ContextPackRequest(question=query, user_id=MCP_PRINCIPAL, domains=domains),
        principal=MCP_PRINCIPAL,
    )
    return [obj.model_dump(mode="json") for obj in pack.knowledge_objects]


@mcp.tool()
def get_context_pack(
    question: str,
    user_id: str = "mcp-user",
    domain: str | None = None,
    mode: str = "default",
) -> dict:
    """Build a governed context pack for an LLM client or agent.

    ``user_id`` is recorded for attribution only. Clearance comes from the MCP
    principal so an agent cannot widen its access by naming another user.
    """

    domains = [domain] if domain else []
    request = ContextPackRequest(
        question=question,
        user_id=user_id,
        domains=domains,
        mode=mode,
    )
    pack = context_pack_service.build(request, principal=MCP_PRINCIPAL)
    store.add_audit_event(
        AuditEvent(
            event_type="context_pack_requested",
            actor=user_id,
            target_id=pack.context_pack_id,
            details={
                "question": question,
                "mode": mode,
                "principal": MCP_PRINCIPAL,
                "access_decision": pack.access_decision,
                "adapter": "mcp",
            },
        )
    )
    return pack.model_dump(mode="json")


@mcp.resource("brain://objects")
def list_brain_objects() -> str:
    """List published brain object IDs and titles the MCP principal may read."""

    lines = []
    for obj in store.knowledge_objects.values():
        if not access_policy.can_access(MCP_PRINCIPAL, obj):
            continue
        lines.append(f"{obj.id} | {obj.type.value} | {obj.title} | {obj.domain}")
    return "\n".join(lines) if lines else "No published brain objects yet."


@mcp.resource("brain://review-queue")
def review_queue_resource() -> str:
    """Show review queue as a readable MCP resource."""

    items = [
        item
        for item in governance.list_queue()
        if access_policy.can_access(MCP_PRINCIPAL, item.candidate_object)
    ]
    if not items:
        return "No review items waiting for review."
    return "\n".join(
        f"{item.id} | {item.candidate_object.type.value} | {item.candidate_object.title}"
        for item in items
    )


if __name__ == "__main__":
    mcp.run()
