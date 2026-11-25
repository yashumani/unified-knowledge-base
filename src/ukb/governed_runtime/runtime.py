from __future__ import annotations

from ukb.governed_runtime.cache import CacheCoordinator
from ukb.governed_runtime.conversations import build_conversation_repository
from ukb.governed_runtime.service import GovernedRuntimeService
from ukb.services.runtime import application, settings

conversation_repository = build_conversation_repository(settings)
cache_coordinator = CacheCoordinator(settings)
governed_runtime = GovernedRuntimeService(
    application=application,
    settings=settings,
    conversations=conversation_repository,
    cache=cache_coordinator,
)
