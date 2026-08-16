from ukb.config import get_settings
from ukb.services.retrieval import RetrievalService
from ukb.store import store

settings = get_settings()
retrieval_service = RetrievalService(store, settings=settings)

__all__ = ["retrieval_service"]
