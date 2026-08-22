from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


class ObjectStoreError(RuntimeError):
    """Raised when an object-store operation is unsafe or cannot complete."""


@dataclass(frozen=True)
class StoredObject:
    key: str
    uri: str
    sha256: str
    size_bytes: int


class LocalObjectStore:
    """Filesystem-backed object store for local and self-hosted UKB runtimes."""

    def __init__(self, root: Path):
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_url(cls, object_store_url: str) -> LocalObjectStore:
        if not object_store_url.startswith("file://"):
            raise ObjectStoreError("Only file:// object-store URLs are supported in this phase.")
        raw_path = object_store_url.removeprefix("file://")
        if not raw_path:
            raise ObjectStoreError("The object-store URL does not include a path.")
        return cls(Path(raw_path))

    def put_bytes(self, key: str, data: bytes) -> StoredObject:
        destination = self._resolve_key(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(f"{destination.suffix}.tmp-{os.getpid()}")
        temporary.write_bytes(data)
        temporary.replace(destination)
        digest = hashlib.sha256(data).hexdigest()
        return StoredObject(
            key=key,
            uri=f"object://local/{key}",
            sha256=digest,
            size_bytes=len(data),
        )

    def get_bytes(self, key: str) -> bytes:
        path = self._resolve_key(key)
        if not path.is_file():
            raise ObjectStoreError(f"Object not found: {key}")
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._resolve_key(key).is_file()

    def _resolve_key(self, key: str) -> Path:
        normalized = PurePosixPath(key)
        if normalized.is_absolute() or ".." in normalized.parts or not normalized.parts:
            raise ObjectStoreError("Object key must be a non-empty relative path without traversal.")
        candidate = self.root.joinpath(*normalized.parts).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ObjectStoreError("Object key escaped the configured storage root.")
        return candidate
