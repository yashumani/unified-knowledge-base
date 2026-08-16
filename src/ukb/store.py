from __future__ import annotations

from ukb.config import Settings, get_settings
from ukb.storage import BrainStore, SqlAlchemyBrainStore


def build_store(settings: Settings | None = None) -> BrainStore:
    active = settings or get_settings()
    if active.store_backend.lower().strip() == "sqlalchemy":
        return SqlAlchemyBrainStore(
            active.database_url,
            create_schema=active.create_schema_on_startup,
        )
    return BrainStore()


store = build_store()

__all__ = ["BrainStore", "SqlAlchemyBrainStore", "build_store", "store"]
