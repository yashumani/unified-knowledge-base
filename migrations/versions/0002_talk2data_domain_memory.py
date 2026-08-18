"""Add Talk2Data tenant Domain Packs and governed temporal memory.

Revision ID: 0002_talk2data_domain_memory
Revises: 0001_schema
Create Date: 2026-08-18
"""

from __future__ import annotations

from alembic import op

from ukb.talk2data.store import TALK2DATA_TABLES

revision = "0002_talk2data_domain_memory"
down_revision = "0001_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in TALK2DATA_TABLES:
        table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(TALK2DATA_TABLES):
        table.drop(bind=bind, checkfirst=True)
