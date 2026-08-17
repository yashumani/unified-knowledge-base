from __future__ import annotations

from ukb.api.security import Principal
from ukb.models import (
    ContextPackRequest,
    IngestionSubmission,
    PublishDecision,
    ReviewDecision,
    Sensitivity,
)
from ukb.search import SearchRequest
from ukb.services.runtime import application, settings

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise SystemExit("The MCP extra is not installed. Run: pip install -e '.[mcp]'") from exc

mcp = FastMCP(settings.mcp_server_name)
MCP_PRINCIPAL = Principal(
    subject="mcp-client",
    roles=frozenset({"consumer", "submitter"}),
    clearance=Sensitivity.internal,
    auth_method="mcp",
)


@mcp.tool()
def submit_context(
    title: str,
    content: str,
    submitted_by: str = "mcp-client",
    source_type: str = "manual",
    domain: str = "general",
    sensitivity: str = "internal",
) -> dict:
    """Submit evidence for deterministic parsing, AI enrichment, and human review."""

    submission = IngestionSubmission(
        title=title,
        content=content,
        submitted_by=submitted_by,
        source_type=source_type,
        domain=domain,
        sensitivity=sensitivity,
    )
    return application.submit_text(submission, principal=MCP_PRINCIPAL).model_dump(mode="json")


@mcp.tool()
def list_review_items() -> list[dict]:
    """List visible candidates waiting for human review."""

    return [
        item.model_dump(mode="json")
        for item in application.governance.list_queue()
        if application.access_policy.can_access(MCP_PRINCIPAL, item.candidate_object)
    ]


@mcp.tool()
def approve_review_item(
    review_item_id: str,
    reviewed_by: str = "mcp-client",
    comment: str | None = None,
) -> dict:
    """Request approval only in an explicitly supervised MCP deployment."""

    if not settings.mcp_allow_approval:
        return {
            "error": "approval_not_permitted_over_mcp",
            "detail": "Human approval is disabled for MCP clients.",
            "review_item_id": review_item_id,
        }
    supervised = Principal(
        subject=reviewed_by,
        roles=frozenset({"reviewer"}),
        clearance=MCP_PRINCIPAL.clearance,
        auth_method="supervised_mcp",
    )
    decision = ReviewDecision(comment=comment)
    return application.approve_review(
        review_item_id,
        decision,
        principal=supervised,
    ).model_dump(mode="json")


@mcp.tool()
def publish_review_item(
    review_item_id: str,
    published_by: str = "mcp-client",
    comment: str | None = None,
) -> dict:
    """Publish only in an explicitly supervised MCP deployment."""

    if not settings.mcp_allow_publication:
        return {
            "error": "publication_not_permitted_over_mcp",
            "detail": "Publication is disabled for MCP clients.",
            "review_item_id": review_item_id,
        }
    supervised = Principal(
        subject=published_by,
        roles=frozenset({"publisher"}),
        clearance=MCP_PRINCIPAL.clearance,
        auth_method="supervised_mcp",
    )
    transition = application.publish_review(
        review_item_id,
        PublishDecision(comment=comment),
        principal=supervised,
    )
    return transition.item.model_dump(mode="json")


@mcp.tool()
def search_brain(query: str, domain: str | None = None, limit: int = 5) -> dict:
    """Search approved, permission-filtered memory through the shared retrieval runtime."""

    response = application.search(
        SearchRequest(query=query, domains=[domain] if domain else [], limit=limit),
        principal=MCP_PRINCIPAL,
    )
    return response.model_dump(mode="json")


@mcp.tool()
def get_context_pack(
    question: str,
    user_id: str = "mcp-user",
    domain: str | None = None,
    mode: str = "default",
) -> dict:
    """Build the same governed context pack served by REST and the Python runtime."""

    request = ContextPackRequest(
        question=question,
        user_id=user_id,
        domains=[domain] if domain else [],
        mode=mode,
    )
    return application.build_context_pack(
        request,
        principal=MCP_PRINCIPAL,
    ).model_dump(mode="json")


@mcp.resource("brain://objects")
def list_brain_objects() -> str:
    lines = []
    for obj in application.store.knowledge_objects.values():
        if application.access_policy.can_access(MCP_PRINCIPAL, obj):
            lines.append(f"{obj.id} | {obj.type.value} | {obj.title} | {obj.domain} | v{obj.version}")
    return "\n".join(lines) if lines else "No published brain objects yet."


@mcp.resource("brain://review-queue")
def review_queue_resource() -> str:
    items = [
        item
        for item in application.governance.list_queue()
        if application.access_policy.can_access(MCP_PRINCIPAL, item.candidate_object)
    ]
    return "\n".join(
        f"{item.id} | {item.status.value} | r{item.revision} | {item.candidate_object.title}"
        for item in items
    ) or "No review items waiting for review."


if __name__ == "__main__":
    mcp.run()
