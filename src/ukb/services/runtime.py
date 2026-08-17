from __future__ import annotations

from ukb.application import BrainApplication
from ukb.config import get_settings
from ukb.store import store

settings = get_settings()
application = BrainApplication(store=store, settings=settings)

__all__ = ["application", "settings", "store"]
