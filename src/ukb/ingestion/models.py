from __future__ import annotations

from pydantic import BaseModel

from ukb.models import ReviewItem, SourceEvidence


class FileArtifactMetadata(BaseModel):
    original_filename: str
    media_type: str
    extension: str
    object_key: str
    object_uri: str
    content_digest: str
    size_bytes: int
