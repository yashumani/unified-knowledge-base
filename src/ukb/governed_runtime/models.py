from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from ukb.models import ContextPack, utc_now


def new_runtime_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class ConversationRole(StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"
    tool = "tool"


class CacheNamespace(StrEnum):
    response = "response"
    tool = "tool"
    retrieval = "retrieval"
    prompt = "prompt"


class ConversationRecord(BaseModel):
    conversation_id: str = Field(default_factory=lambda: new_runtime_id("conv"))
    tenant_id: str
    subject: str
    title: str = "New Brain Chat"
    summary: str | None = None
    summary_version: int = 0
    status: Literal["active", "archived"] = "active"
    attributes: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ConversationMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: new_runtime_id("msg"))
    conversation_id: str
    tenant_id: str
    subject: str
    role: ConversationRole
    content: str
    context_pack_id: str | None = None
    cache_event_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class CacheEventRecord(BaseModel):
    event_id: str = Field(default_factory=lambda: new_runtime_id("cache"))
    request_id: str = Field(default_factory=lambda: new_runtime_id("req"))
    tenant_id: str
    subject: str
    namespace: CacheNamespace
    eligible: bool = True
    hit: bool = False
    key_digest: str
    ttl_seconds: int | None = None
    reason: str | None = None
    backend: str = "memory"
    attributes: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class AskBrainRequest(BaseModel):
    question: str = Field(min_length=1, max_length=20_000)
    conversation_id: str | None = None
    title: str | None = None
    domains: list[str] = Field(default_factory=list)
    mode: Literal[
        "default",
        "executive_insight",
        "metric_definition",
        "lineage",
        "governance_review",
        "debug",
    ] = "default"
    locale: str = "en-US"
    data_snapshot_id: str | None = None
    force_refresh: bool = False
    attributes: dict[str, Any] = Field(default_factory=dict)


class GovernedAnswer(BaseModel):
    conversation: ConversationRecord
    user_message: ConversationMessage
    assistant_message: ConversationMessage
    context_pack: ContextPack
    response_cache_hit: bool
    cache_events: list[CacheEventRecord] = Field(default_factory=list)
    prompt_prefix_hash: str
    knowledge_snapshot_id: str


class RuntimeStatus(BaseModel):
    cache_enabled: bool
    cache_backend: str
    prompt_prefix_version: str
    tool_schema_version: str
    response_schema_version: str
    access_policy_version: str
    mcp_transport: str
    mcp_subject: str
    mcp_tenant_id: str
    cache_metrics: dict[str, int] = Field(default_factory=dict)
    conversation_count: int = 0
    message_count: int = 0
