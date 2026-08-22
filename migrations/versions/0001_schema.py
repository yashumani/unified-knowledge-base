"""Create the authoritative Unified Knowledge Base schema.

Revision ID: 0001_schema
Revises:
Create Date: 2026-08-16
"""

from __future__ import annotations

from alembic import op

from ukb.storage.orm import Base

revision = "0001_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), checkfirst=True)
