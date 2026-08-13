from __future__ import annotations

from ukb.config import Settings, get_settings
from ukb.storage import BrainStore, SqlAlchemyBrainStore


def build_store(settings: Settings | None = None) -> BrainStore:
    """Build the configured UKB storage backend.

    The code default remains memory-safe for tests and first import. Local and
    production environment files select SQLAlchemy for durable SQLite/Postgres.
    """

    active_settings = settings or get_settings()
    if active_settings.store_backend.lower().strip() == "sqlalchemy":
        return SqlAlchemyBrainStore(active_settings.database_url)
    return BrainStore()


store = build_store()

__all__ = ["BrainStore", "SqlAlchemyBrainStore", "build_store", "store"]
