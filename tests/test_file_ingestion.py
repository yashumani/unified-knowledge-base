from pathlib import Path

import pytest

from ukb.ingestion.files import FileIngestionError, FileIngestionService
from ukb.models import Sensitivity
from ukb.services.compiler import BrainCompiler
from ukb.storage.objects import LocalObjectStore, ObjectStoreError


def build_service(root: Path, *, max_upload_bytes: int = 4096) -> FileIngestionService:
    return FileIngestionService(
        compiler=BrainCompiler(),
        object_store=LocalObjectStore(root),
        max_upload_bytes=max_upload_bytes,
        max_extracted_chars=10000,
    )


def test_file_service_preserves_original_and_creates_candidate(tmp_path: Path) -> None:
    service = build_service(tmp_path / "objects")
    payload = (
        b"Incident Resolution Time is a support metric owned by Support Operations. "
        b"It appears in the SLA Review Dashboard."
    )

    parsed = service.ingest(
        filename="incident-resolution.md",
        media_type="text/markdown",
        data=payload,
        submitted_by="file-test.submitter",
        domain="support",
        sensitivity=Sensitivity.internal,
    )

    assert parsed.source.source_uri == parsed.artifact.object_uri
    assert parsed.artifact.original_filename == "incident-resolution.md"
    assert parsed.review_item.candidate_object.domain == "support"
    assert service.object_store.get_bytes(parsed.artifact.object_key) == payload


def test_file_service_rejects_unsupported_extension(tmp_path: Path) -> None:
    service = build_service(tmp_path / "objects")
    with pytest.raises(FileIngestionError, match="Unsupported file extension"):
        service.ingest(
            filename="image.png",
            media_type="image/png",
            data=b"not-an-image",
            submitted_by="file-test.submitter",
            domain="support",
            sensitivity=Sensitivity.internal,
        )


def test_file_service_rejects_oversized_file(tmp_path: Path) -> None:
    service = build_service(tmp_path / "objects", max_upload_bytes=8)
    with pytest.raises(FileIngestionError, match="exceeds"):
        service.ingest(
            filename="large.txt",
            media_type="text/plain",
            data=b"123456789",
            submitted_by="file-test.submitter",
            domain="support",
            sensitivity=Sensitivity.internal,
        )


def test_object_store_rejects_path_traversal(tmp_path: Path) -> None:
    object_store = LocalObjectStore(tmp_path / "objects")
    with pytest.raises(ObjectStoreError, match="relative path"):
        object_store.put_bytes("../outside.txt", b"unsafe")
