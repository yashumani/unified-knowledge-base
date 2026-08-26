from __future__ import annotations

import inspect
from typing import Any, Literal

from ukb.api.security import Principal
from ukb.governed_runtime.models import AskBrainRequest, CacheNamespace
from ukb.governed_runtime.runtime import governed_runtime
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

ContextMode = Literal[
    "default",
    "executive_insight",
    "metric_definition",
    "lineage",
    "governance_review",
    "debug",
]


def _build_fastmcp() -> FastMCP:
    constructor = inspect.signature(FastMCP)
    kwargs: dict[str, Any] = {}
    if "host" in constructor.parameters:
        kwargs["host"] = settings.mcp_host
    if "port" in constructor.parameters:
        kwargs["port"] = settings.mcp_port
    return FastMCP(settings.mcp_server_name, **kwargs)


mcp = _build_fastmcp()


def get_mcp_principal() -> Principal:
    clearance_value = settings.mcp_clearance.casefold()
    try:
        clearance = Sensitivity(clearance_value)
    except ValueError:
        clearance = Sensitivity.internal
    return Principal(
        subject=settings.mcp_subject,
        tenant_id=settings.mcp_tenant_id,
        roles=frozenset(settings.mcp_role_set),
        clearance=clearance,
        auth_method="mcp_service_account",
    )


def _principal() -> Principal:
    return get_mcp_principal()


@mcp.tool()
def runtime_status() -> dict:
    """Return governed runtime, conversation, cache, identity, and MCP transport status."""

    return governed_runtime.status(principal=_principal()).model_dump(mode="json")


@mcp.tool()
def start_conversation(title: str = "New Brain Chat") -> dict:
    """Create an attributable, tenant-scoped durable Brain Chat conversation."""

    return governed_runtime.start_conversation(
        principal=_principal(),
        title=title,
        attributes={"channel": "mcp"},
    ).model_dump(mode="json")


@mcp.tool()
def list_conversations(limit: int = 25) -> list[dict]:
    """List conversations visible to the configured MCP service identity."""

    return [
        conversation.model_dump(mode="json")
        for conversation in governed_runtime.list_conversations(principal=_principal(), limit=limit)
    ]


@mcp.tool()
def get_conversation(conversation_id: str) -> dict:
    """Read one tenant- and subject-scoped conversation and its messages."""

    value = governed_runtime.get_conversation(conversation_id, principal=_principal())
    return value or {"error": "conversation_not_found", "conversation_id": conversation_id}


@mcp.tool()
def ask_brain(
    question: str,
    conversation_id: str | None = None,
    domain: str | None = None,
    mode: ContextMode = "default",
    data_snapshot_id: str | None = None,
    force_refresh: bool = False,
) -> dict:
    """Ask the governed Brain and return a cited Context Pack plus cache receipt.

    The response cache is tenant, permission, model, prompt, schema, data-snapshot,
    knowledge-snapshot, and conversation-state scoped. Cached packs are
    re-authorized before delivery.
    """

    answer = governed_runtime.ask(
        AskBrainRequest(
            question=question,
            conversation_id=conversation_id,
            domains=[domain] if domain else [],
            mode=mode,
            data_snapshot_id=data_snapshot_id,
            force_refresh=force_refresh,
            attributes={"channel": "mcp"},
        ),
        principal=_principal(),
    )
    return answer.model_dump(mode="json")


@mcp.tool()
def submit_context(
    title: str,
    content: str,
    source_type: str = "manual",
    domain: str = "general",
    sensitivity: str = "internal",
) -> dict:
    """Submit evidence into parsing, advisory enrichment, and human review.

    MCP submission never publishes knowledge. The authenticated service account
    becomes the attributable submitter and the normal governance gates remain in
    force.
    """

    principal = _principal()
    submission = IngestionSubmission(
        title=title,
        content=content,
        submitted_by=principal.subject,
        source_type=source_type,
        domain=domain,
        sensitivity=sensitivity,
    )
    return application.submit_text(submission, principal=principal).model_dump(mode="json")


@mcp.tool()
def list_review_items() -> list[dict]:
    """List review candidates visible to the configured tenant and clearance."""

    principal = _principal()
    return [
        item.model_dump(mode="json")
        for item in application.governance.list_queue()
        if application.access_policy.can_access(principal, item.candidate_object)
    ]


@mcp.tool()
def search_brain(query: str, domain: str | None = None, limit: int = 5) -> dict:
    """Search approved memory through the shared authorization-first retrieval runtime."""

    response = application.search(
        SearchRequest(query=query, domains=[domain] if domain else [], limit=max(1, min(limit, 25))),
        principal=_principal(),
    )
    return response.model_dump(mode="json")


@mcp.tool()
def get_context_pack(
    question: str,
    domain: str | None = None,
    mode: ContextMode = "default",
) -> dict:
    """Build a fresh governed Context Pack without creating a conversation."""

    principal = _principal()
    request = ContextPackRequest(
        question=question,
        user_id=principal.subject,
        domains=[domain] if domain else [],
        mode=mode,
    )
    return application.build_context_pack(request, principal=principal).model_dump(mode="json")


@mcp.tool()
def get_source_lineage(source_id: str) -> dict:
    """Return authorized source versions, evidence chunks, and published dependents.

    This read-only tool uses a separately measured tool-result cache and never
    changes canonical evidence.
    """

    return governed_runtime.get_source_lineage(source_id, principal=_principal())


@mcp.tool()
def invalidate_cache(namespace: str | None = None) -> dict:
    """Invalidate this tenant's disposable cache only when explicitly authorized."""

    if not settings.mcp_allow_cache_invalidation:
        return {
            "error": "cache_invalidation_not_permitted_over_mcp",
            "detail": "Set UKB_MCP_ALLOW_CACHE_INVALIDATION only for a supervised cache-admin service.",
        }
    selected: CacheNamespace | None = None
    if namespace:
        try:
            selected = CacheNamespace(namespace)
        except ValueError:
            return {"error": "invalid_cache_namespace", "namespace": namespace}
    return governed_runtime.invalidate_cache(principal=_principal(), namespace=selected)


@mcp.tool()
def approve_review_item(
    review_item_id: str,
    comment: str | None = None,
) -> dict:
    """Request approval only in an explicitly supervised MCP deployment."""

    if not settings.mcp_allow_approval:
        return {
            "error": "approval_not_permitted_over_mcp",
            "detail": "Human approval is disabled for MCP clients.",
            "review_item_id": review_item_id,
        }
    principal = _principal()
    if not ({"reviewer", "governance_admin"} & set(principal.roles)):
        return {"error": "reviewer_role_required", "review_item_id": review_item_id}
    decision = ReviewDecision(comment=comment)
    return application.approve_review(
        review_item_id,
        decision,
        principal=principal,
    ).model_dump(mode="json")


@mcp.tool()
def publish_review_item(
    review_item_id: str,
    comment: str | None = None,
) -> dict:
    """Publish only in an explicitly supervised MCP deployment."""

    if not settings.mcp_allow_publication:
        return {
            "error": "publication_not_permitted_over_mcp",
            "detail": "Publication is disabled for MCP clients.",
            "review_item_id": review_item_id,
        }
    principal = _principal()
    if not ({"publisher", "governance_admin"} & set(principal.roles)):
        return {"error": "publisher_role_required", "review_item_id": review_item_id}
    transition = application.publish_review(
        review_item_id,
        PublishDecision(comment=comment),
        principal=principal,
    )
    return transition.item.model_dump(mode="json")


@mcp.resource("brain://runtime/status")
def runtime_status_resource() -> str:
    return governed_runtime.status(principal=_principal()).model_dump_json(indent=2)


@mcp.resource("brain://objects")
def list_brain_objects() -> str:
    principal = _principal()
    lines = []
    for obj in application.store.knowledge_objects.values():
        if application.access_policy.can_access(principal, obj):
            lines.append(f"{obj.id} | {obj.type.value} | {obj.title} | {obj.domain} | v{obj.version}")
    return "\n".join(lines) if lines else "No published brain objects yet."


@mcp.resource("brain://review-queue")
def review_queue_resource() -> str:
    principal = _principal()
    items = [
        item
        for item in application.governance.list_queue()
        if application.access_policy.can_access(principal, item.candidate_object)
    ]
    return "\n".join(
        f"{item.id} | {item.status.value} | r{item.revision} | {item.candidate_object.title}"
        for item in items
    ) or "No review items waiting for review."


@mcp.resource("brain://conversations/recent")
def recent_conversations_resource() -> str:
    conversations = governed_runtime.list_conversations(principal=_principal(), limit=25)
    return "\n".join(
        f"{item.conversation_id} | {item.updated_at.isoformat()} | {item.title}"
        for item in conversations
    ) or "No conversations yet."


def main() -> None:
    transport = settings.mcp_transport.replace("_", "-").casefold()
    run_signature = inspect.signature(mcp.run)
    kwargs: dict[str, Any] = {}
    if "transport" in run_signature.parameters:
        kwargs["transport"] = transport
    mcp.run(**kwargs)


if __name__ == "__main__":
    main()
