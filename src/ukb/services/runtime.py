from __future__ import annotations

from ukb.application import BrainApplication
from ukb.config import get_settings
from ukb.plugins.builtin import register_builtin_plugins
from ukb.plugins.registry import registry
from ukb.store import store

settings = get_settings()
register_builtin_plugins(registry)
registry.load_entry_points()
application = BrainApplication(store=store, settings=settings)

__all__ = ["application", "registry", "settings", "store"]
