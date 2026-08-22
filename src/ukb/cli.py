from __future__ import annotations

import json

import typer

from ukb.config import get_settings
from ukb.models import (
    AuditEvent,
    ContextPackRequest,
    IngestionSubmission,
    ReviewDecision,
    SourceType,
)
from ukb.services.access import AccessPolicyService
from ukb.services.compiler import BrainCompiler
from ukb.services.context_pack import ContextPackService
from ukb.services.governance import GovernanceService
from ukb.store import store

app = typer.Typer(help="Unified Knowledge Base development CLI.")

settings = get_settings()
access_policy = AccessPolicyService.from_settings(settings)
compiler = BrainCompiler()
governance = GovernanceService(store)
context_pack_service = ContextPackService(store, access_policy=access_policy)


@app.command()
def submit(
    title: str,
    content: str,
    submitted_by: str = "cli-user",
    domain: str = "general",
) -> None:
    submission = IngestionSubmission(
        title=title,
        content=content,
        submitted_by=submitted_by,
        source_type=SourceType.manual,
        domain=domain,
    )
    source, review_item = compiler.compile_submission(submission)
    store.add_source(source)
    store.add_review_item(review_item)
    store.add_audit_event(
        AuditEvent(
            event_type="submission_created",
            actor=submitted_by,
            target_id=review_item.id,
            details={"source_id": source.source_id, "domain": domain, "adapter": "cli"},
        )
    )
    typer.echo(json.dumps(review_item.model_dump(mode="json"), indent=2))


@app.command("review-queue")
def review_queue() -> None:
    typer.echo(
        json.dumps(
            [item.model_dump(mode="json") for item in governance.list_queue()],
            indent=2,
        )
    )


@app.command()
def approve(review_item_id: str, reviewed_by: str = "cli-reviewer") -> None:
    item = governance.approve(
        review_item_id,
        ReviewDecision(reviewed_by=reviewed_by),
    )
    typer.echo(json.dumps(item.model_dump(mode="json"), indent=2))


@app.command("context-pack")
def context_pack(
    question: str,
    user_id: str = "cli-user",
    domain: str = "general",
) -> None:
    # The CLI runs as a local operator, so the supplied user_id is also the
    # clearance principal. Over HTTP that binding comes from the auth layer.
    pack = context_pack_service.build(
        ContextPackRequest(question=question, user_id=user_id, domains=[domain]),
        principal=user_id,
    )
    typer.echo(json.dumps(pack.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    app()
