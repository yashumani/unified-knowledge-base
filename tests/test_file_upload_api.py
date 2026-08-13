from pathlib import Path

from fastapi.testclient import TestClient

from ukb.ai.providers.noop import NoopProvider
from ukb.ai.service import AIEnrichmentService
from ukb.api import file_routes
from ukb.api.main import app
from ukb.ingestion.files import FileIngestionService
from ukb.services.compiler import BrainCompiler
from ukb.storage.objects import LocalObjectStore
from ukb.store import store


def build_upload_service(root: Path) -> FileIngestionService:
    return FileIngestionService(
        compiler=BrainCompiler(),
        object_store=LocalObjectStore(root),
        max_upload_bytes=4096,
        max_extracted_chars=10000,
    )
