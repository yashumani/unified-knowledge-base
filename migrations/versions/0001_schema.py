"""Initial persistence schema revision."""

from alembic import op

from ukb.storage.orm import Base

revision = "0001_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())
