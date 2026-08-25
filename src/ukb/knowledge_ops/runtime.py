from ukb.knowledge_ops.service import KnowledgeOperationsService
from ukb.services.runtime import application, settings

service = KnowledgeOperationsService(application=application, settings=settings)

__all__ = ["service"]
