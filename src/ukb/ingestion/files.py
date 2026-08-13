from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from ukb.ingestion.models import FileArtifactMetadata
from ukb.models import IngestionSubmission, ReviewItem, Sensitivity, SourceEvidence, SourceType
from ukb.services.compiler import BrainCompiler
from ukb.storage.objects import LocalObjectStore


class FileIngestionError(ValueError):
    """Raised when an uploaded source cannot be accepted safely."""


@dataclass(frozen=True)
class ParsedFileSubmission:
    source: SourceEvidence
    review_item: ReviewItem
    artifact: FileArtifactMetadata
    extracted_text: str


class FileIngestionService:
    """Validate, preserve, and compile text-oriented source files."""

    extension_types: ClassVar[dict[str, SourceType]] = {
        ".txt": SourceType.document,
        ".md": SourceType.markdown,
        ".markdown": SourceType.markdown,
        ".sql": SourceType.sql,
        ".csv": SourceType.spreadsheet,
        ".json": SourceType.document,
        ".yaml": SourceType.document,
        ".yml": SourceType.document,
    }

    def __init__(
        self,
        *,
        compiler: BrainCompiler,
        object_store: LocalObjectStore,
        max_upload_bytes: int,
        max_extracted_chars: int,
    ):
        self.compiler = compiler
        self.object_store = object_store
        self.max_upload_bytes = max_upload_bytes
        self.max_extracted_chars = max_extracted_chars

    def ingest(
        self,
        *,
        filename: str,
        media_type: str | None,
        data: bytes,
        submitted_by: str,
        domain: str,
        sensitivity: Sensitivity,
        title: str | None = None,
        tags: list[str] | None = None,
    ) -> ParsedFileSubmission:
        safe_filename = Path(filename).name
        if not safe_filename or safe_filename in {".", ".."}:
            raise FileIngestionError("A valid filename is required.")
        if len(data) == 0:
            raise FileIngestionError("The uploaded file is empty.")
        if len(data) > self.max_upload_bytes:
            raise FileIngestionError(
                f"The uploaded file exceeds the {self.max_upload_bytes}-byte limit."
            )

        extension = Path(safe_filename).suffix.lower()
        source_type = self.extension_types.get(extension)
        if source_type is None:
            allowed = ", ".join(sorted(self.extension_types))
            raise FileIngestionError(f"Unsupported file extension. Allowed: {allowed}")

        extracted_text = self._decode_text(data)
        if len(extracted_text) > self.max_extracted_chars:
            extracted_text = extracted_text[: self.max_extracted_chars]

        resolved_title = (title or Path(safe_filename).stem).strip()
        if len(resolved_title) < 3:
            raise FileIngestionError("The source title must contain at least three characters.")

        digest = hashlib.sha256(data).hexdigest()
        submission = IngestionSubmission(
            title=resolved_title,
            source_type=source_type,
            submitted_by=submitted_by,
            content=extracted_text,
            domain=domain,
            sensitivity=sensitivity,
            tags=sorted(set(["file-upload", extension.removeprefix("."), *(tags or [])])),
        )
        source, review_item = self.compiler.compile_submission(submission)

        object_key = f"sources/{source.source_id}/{digest}{extension}"
        stored = self.object_store.put_bytes(object_key, data)
        source.source_uri = stored.uri

        artifact = FileArtifactMetadata(
            original_filename=safe_filename,
            media_type=media_type or "application/octet-stream",
            extension=extension,
            object_key=stored.key,
            object_uri=stored.uri,
            content_digest=stored.sha256,
            size_bytes=stored.size_bytes,
        )
        return ParsedFileSubmission(
            source=source,
            review_item=review_item,
            artifact=artifact,
            extracted_text=extracted_text,
        )

    def _decode_text(self, data: bytes) -> str:
        if b"\x00" in data:
            raise FileIngestionError("Binary content is not accepted by the text ingestion endpoint.")
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise FileIngestionError("The file must use UTF-8 text encoding.") from exc
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized:
            raise FileIngestionError("The file did not contain usable text.")
        return normalized
