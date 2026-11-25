"""Add durable conversations and cache telemetry for governed runtime v0.7.

Revision ID: 0004_governed_runtime_cache_mcp
Revises: 0003_knowledge_operations_v05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_governed_runtime_cache_mcp"
down_revision: str | None = "0003_knowledge_operations_v05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runtime_conversations",
        sa.Column("conversation_id", sa.String(length=80), primary_key=True),
        sa.Column("tenant_id", sa.String(length=160), nullable=False),
        sa.Column("subject", sa.String(length=320), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("summary_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_runtime_conversations_tenant", "runtime_conversations", ["tenant_id"])
    op.create_index("ix_runtime_conversations_subject", "runtime_conversations", ["subject"])

    op.create_table(
        "runtime_conversation_messages",
        sa.Column("message_id", sa.String(length=80), primary_key=True),
        sa.Column("conversation_id", sa.String(length=80), nullable=False),
        sa.Column("tenant_id", sa.String(length=160), nullable=False),
        sa.Column("subject", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("context_pack_id", sa.String(length=100), nullable=True),
        sa.Column("cache_event_id", sa.String(length=100), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_runtime_messages_conversation",
        "runtime_conversation_messages",
        ["conversation_id"],
    )
    op.create_index("ix_runtime_messages_tenant", "runtime_conversation_messages", ["tenant_id"])
    op.create_index("ix_runtime_messages_created", "runtime_conversation_messages", ["created_at"])

    op.create_table(
        "runtime_cache_events",
        sa.Column("event_id", sa.String(length=100), primary_key=True),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("tenant_id", sa.String(length=160), nullable=False),
        sa.Column("subject", sa.String(length=320), nullable=False),
        sa.Column("namespace", sa.String(length=32), nullable=False),
        sa.Column("eligible", sa.Integer(), nullable=False),
        sa.Column("hit", sa.Integer(), nullable=False),
        sa.Column("key_digest", sa.String(length=64), nullable=False),
        sa.Column("ttl_seconds", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(length=300), nullable=True),
        sa.Column("backend", sa.String(length=32), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_runtime_cache_request", "runtime_cache_events", ["request_id"])
    op.create_index("ix_runtime_cache_tenant", "runtime_cache_events", ["tenant_id"])
    op.create_index("ix_runtime_cache_namespace", "runtime_cache_events", ["namespace"])
    op.create_index("ix_runtime_cache_created", "runtime_cache_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_runtime_cache_created", table_name="runtime_cache_events")
    op.drop_index("ix_runtime_cache_namespace", table_name="runtime_cache_events")
    op.drop_index("ix_runtime_cache_tenant", table_name="runtime_cache_events")
    op.drop_index("ix_runtime_cache_request", table_name="runtime_cache_events")
    op.drop_table("runtime_cache_events")

    op.drop_index("ix_runtime_messages_created", table_name="runtime_conversation_messages")
    op.drop_index("ix_runtime_messages_tenant", table_name="runtime_conversation_messages")
    op.drop_index("ix_runtime_messages_conversation", table_name="runtime_conversation_messages")
    op.drop_table("runtime_conversation_messages")

    op.drop_index("ix_runtime_conversations_subject", table_name="runtime_conversations")
    op.drop_index("ix_runtime_conversations_tenant", table_name="runtime_conversations")
    op.drop_table("runtime_conversations")
