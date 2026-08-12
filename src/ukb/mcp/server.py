from __future__ import annotations

from ukb.models import ContextPackRequest, IngestionSubmission, ReviewDecision
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


mcp = FastMCP("unified-knowledge-base")

compiler = BrainCompiler()
governance = GovernanceService(store)
context_pack_service = ContextPackService(store)


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
    return review_item.model_dump(mode="json")


@mcp.tool()
def list_review_items() -> list[dict]:
    """List knowledge candidates waiting for human review."""

    return [item.model_dump(mode="json") for item in governance.list_queue()]


@mcp.tool()
def approve_review_item(review_item_id: str, reviewed_by: str, comment: str | None = None) -> dict:
    """Approve a review item and publish it into the AI Brain."""

    decision = ReviewDecision(reviewed_by=reviewed_by, comment=comment)
    return governance.approve(review_item_id, decision).model_dump(mode="json")


@mcp.tool()
def search_brain(query: str, domain: str | None = None) -> list[dict]:
    """Search approved brain objects using the scaffold retrieval service."""

    domains = [domain] if domain else []
    pack = context_pack_service.build(
        ContextPackRequest(question=query, user_id="mcp-user", domains=domains)
    )
    return [obj.model_dump(mode="json") for obj in pack.knowledge_objects]


@mcp.tool()
def get_context_pack(
    question: str,
    user_id: str = "mcp-user",
    domain: str | None = None,
    mode: str = "default",
) -> dict:
    """Build a governed context pack for an LLM client or agent."""

    domains = [domain] if domain else []
    request = ContextPackRequest(
        question=question,
        user_id=user_id,
        domains=domains,
        mode=mode,
    )
    return context_pack_service.build(request).model_dump(mode="json")


@mcp.resource("brain://objects")
def list_brain_objects() -> str:
    """List published brain object IDs and titles."""

    lines = []
    for obj in store.knowledge_objects.values():
        lines.append(f"{obj.id} | {obj.type.value} | {obj.title} | {obj.domain}")
    return "\n".join(lines) if lines else "No published brain objects yet."


@mcp.resource("brain://review-queue")
def review_queue_resource() -> str:
    """Show review queue as a readable MCP resource."""

    items = governance.list_queue()
    if not items:
        return "No review items waiting for review."
    return "\n".join(
        f"{item.id} | {item.candidate_object.type.value} | {item.candidate_object.title}"
        for item in items
    )


if __name__ == "__main__":
    mcp.run()
