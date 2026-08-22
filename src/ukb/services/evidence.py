from __future__ import annotations

import hashlib
import re
from pathlib import PurePosixPath

from ukb.config import Settings
from ukb.models import EvidenceChunk, EvidenceReference, SourceEvidence, SourceVersion
from ukb.storage.memory import BrainStore
from ukb.storage.objects import LocalObjectStore


class EvidenceService:
    """Preserve immutable source versions and create traceable evidence chunks."""

    def __init__(
        self,
        store: BrainStore,
        settings: Settings,
        object_store: LocalObjectStore | None = None,
    ) -> None:
        self.store = store
        self.settings = settings
        self.object_store = object_store

    def preserve(
        self,
        *,
        source: SourceEvidence,
        normalized_text: str,
        actor: str,
        content_type: str = "text/plain",
        original_bytes: bytes | None = None,
        original_name: str | None = None,
        parser: str = "deterministic",
        parser_version: str = "1",
    ) -> tuple[SourceVersion, list[EvidenceChunk]]:
        versions = self.store.list_source_versions(source.source_id)
        version_number = max((item.version for item in versions), default=0) + 1
        raw = original_bytes if original_bytes is not None else normalized_text.encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()

        object_key: str | None = None
        object_uri: str | None = None
        if self.object_store is not None:
            safe_name = self._safe_name(original_name or f"source-{source.source_id}.txt")
            object_key = f"sources/{source.source_id}/v{version_number}/{safe_name}"
            stored = self.object_store.put_bytes(object_key, raw)
            object_uri = stored.uri

        version = SourceVersion(
            source_id=source.source_id,
            version=version_number,
            content_hash=digest,
            content_type=content_type,
            size_bytes=len(raw),
            object_key=object_key,
            object_uri=object_uri,
            normalized_text=normalized_text,
            parser=parser,
            parser_version=parser_version,
            source_uri=source.source_uri,
            created_by=actor,
        )
        source.content_hash = digest
        source.current_version_id = version.id
        source.content_excerpt = self._excerpt(normalized_text)
        self.store.add_source(source)
        self.store.add_source_version(version)

        chunks = self.chunk(
            source=source,
            version=version,
            text=normalized_text,
        )
        self.store.add_evidence_chunks(chunks)
        return version, chunks

    def chunk(
        self,
        *,
        source: SourceEvidence,
        version: SourceVersion,
        text: str,
    ) -> list[EvidenceChunk]:
        sections = self._sections(text)
        chunks: list[EvidenceChunk] = []
        ordinal = 0
        offset = 0
        for heading_path, section_text in sections:
            section_start = text.find(section_text, offset)
            if section_start < 0:
                section_start = offset
            for part in self._window(section_text):
                part_start = text.find(part, section_start)
                if part_start < 0:
                    part_start = section_start
                part_end = part_start + len(part)
                locator = " > ".join(heading_path) if heading_path else f"chunk {ordinal + 1}"
                chunks.append(
                    EvidenceChunk(
                        source_id=source.source_id,
                        source_version_id=version.id,
                        ordinal=ordinal,
                        heading_path=heading_path,
                        content=part,
                        locator=locator,
                        start_offset=part_start,
                        end_offset=part_end,
                        content_hash=hashlib.sha256(part.encode("utf-8")).hexdigest(),
                        sensitivity=source.sensitivity,
                    )
                )
                ordinal += 1
                section_start = max(part_end - self.settings.evidence_chunk_overlap, section_start)
            offset = max(offset, section_start)
        return chunks

    def references(
        self,
        chunks: list[EvidenceChunk],
        *,
        field_name: str | None = None,
        limit: int = 3,
    ) -> list[EvidenceReference]:
        return [
            EvidenceReference(
                chunk_id=chunk.id,
                source_id=chunk.source_id,
                source_version_id=chunk.source_version_id,
                quote=self._excerpt(chunk.content, 400),
                locator=chunk.locator,
                field_name=field_name,
                confidence=1.0,
            )
            for chunk in chunks[:limit]
        ]

    def _window(self, text: str) -> list[str]:
        limit = max(400, self.settings.evidence_chunk_chars)
        overlap = min(max(0, self.settings.evidence_chunk_overlap), limit // 2)
        cleaned = text.strip()
        if not cleaned:
            return []
        if len(cleaned) <= limit:
            return [cleaned]
        parts: list[str] = []
        start = 0
        while start < len(cleaned):
            end = min(len(cleaned), start + limit)
            if end < len(cleaned):
                boundary = max(
                    cleaned.rfind("\n\n", start, end),
                    cleaned.rfind(". ", start, end),
                    cleaned.rfind("\n", start, end),
                )
                if boundary > start + limit // 2:
                    end = boundary + 1
            part = cleaned[start:end].strip()
            if part:
                parts.append(part)
            if end >= len(cleaned):
                break
            start = max(start + 1, end - overlap)
        return parts

    @staticmethod
    def _sections(text: str) -> list[tuple[list[str], str]]:
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
        matches = list(heading_pattern.finditer(text))
        if not matches:
            return [([], text)]
        sections: list[tuple[list[str], str]] = []
        heading_stack: list[str] = []
        if matches[0].start() > 0 and text[: matches[0].start()].strip():
            sections.append(([], text[: matches[0].start()].strip()))
        for index, match in enumerate(matches):
            level = len(match.group(1))
            heading = match.group(2).strip()
            heading_stack = heading_stack[: level - 1]
            heading_stack.append(heading)
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            if body:
                sections.append((list(heading_stack), body))
        return sections or [([], text)]

    @staticmethod
    def _excerpt(text: str, limit: int = 700) -> str:
        cleaned = " ".join(text.split())
        return cleaned if len(cleaned) <= limit else cleaned[: limit - 3] + "..."

    @staticmethod
    def _safe_name(name: str) -> str:
        safe = PurePosixPath(name.replace("\\", "/")).name
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", safe).strip("-.")
        return safe or "source.bin"
