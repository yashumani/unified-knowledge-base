"""Add governed knowledge operations records.

Revision ID: 0003_knowledge_operations_v05
Revises: 0002_talk2data_domain_memory
Create Date: 2026-08-25
"""

from __future__ import annotations

from alembic import op

from ukb.knowledge_ops.store import KNOWLEDGE_OPERATIONS_TABLES

revision = "0003_knowledge_operations_v05"
down_revision = "0002_talk2data_domain_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in KNOWLEDGE_OPERATIONS_TABLES:
        table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(KNOWLEDGE_OPERATIONS_TABLES):
        table.drop(bind=bind, checkfirst=True)
