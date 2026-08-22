from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from ukb.api.security import Principal
from ukb.models import KnowledgeObject, KnowledgeObjectType, ReviewStatus
from ukb.storage.memory import BrainStore
from ukb.talk2data.models import (
    AuthorityLevel,
    EpisodeIngestionRequest,
    MemoryPromotionRequest,
    MemoryProvenance,
    MemoryStatus,
    MemoryType,
)
from ukb.talk2data.service import Talk2DataService


class BackfillEntry(BaseModel):
    legacy_object_id: str
    action: Literal["planned", "migrated", "skipped", "ambiguous", "failed"]
    mapped_memory_type: MemoryType
    episode_id: str | None = None
    memory_id: str | None = None
    reason: str = ""


class BackfillReport(BaseModel):
    tenant_id: str
    dry_run: bool
    scanned: int = 0
    migrated: int = 0
    skipped: int = 0
    ambiguous: int = 0
    failed: int = 0
    entries: list[BackfillEntry] = Field(default_factory=list)


class LegacyKnowledgeBackfill:
    """Migrate published legacy objects without deleting or overwriting them."""

    TYPE_MAP: dict[KnowledgeObjectType, MemoryType] = {
        KnowledgeObjectType.metric: MemoryType.metric_context,
        KnowledgeObjectType.dimension: MemoryType.business_definition,
        KnowledgeObjectType.business_rule: MemoryType.policy,
        KnowledgeObjectType.process: MemoryType.business_definition,
        KnowledgeObjectType.decision: MemoryType.business_decision,
        KnowledgeObjectType.glossary_term: MemoryType.business_definition,
        KnowledgeObjectType.owner: MemoryType.entity_context,
        KnowledgeObjectType.dataset: MemoryType.source_document,
        KnowledgeObjectType.table: MemoryType.source_document,
        KnowledgeObjectType.column: MemoryType.source_document,
        KnowledgeObjectType.report: MemoryType.source_document,
        KnowledgeObjectType.dashboard: MemoryType.source_document,
        KnowledgeObjectType.system: MemoryType.entity_context,
        KnowledgeObjectType.narrative_template: MemoryType.recommendation,
    }

    def __init__(
        self,
        *,
        legacy_store: BrainStore,
        service: Talk2DataService,
    ) -> None:
        self.legacy_store = legacy_store
        self.service = service

    def run(
        self,
        *,
        principal: Principal,
        dry_run: bool = True,
        limit: int | None = None,
    ) -> BackfillReport:
        objects = sorted(
            (
                obj
                for obj in self.legacy_store.knowledge_objects.values()
                if obj.status == ReviewStatus.published
            ),
            key=lambda obj: (obj.updated_at, obj.id),
        )
        if limit is not None:
            objects = objects[: max(0, limit)]
        report = BackfillReport(
            tenant_id=principal.tenant_id,
            dry_run=dry_run,
            scanned=len(objects),
        )
        for obj in objects:
            try:
                entry = self._migrate(obj, principal=principal, dry_run=dry_run)
            except Exception as exc:
                entry = BackfillEntry(
                    legacy_object_id=obj.id,
                    action="failed",
                    mapped_memory_type=self._map_type(obj)[0],
                    reason=str(exc),
                )
            report.entries.append(entry)
            if entry.action == "migrated":
                report.migrated += 1
            elif entry.action == "skipped":
                report.skipped += 1
            elif entry.action == "ambiguous":
                report.ambiguous += 1
            elif entry.action == "failed":
                report.failed += 1
        return report

    def _migrate(
        self,
        obj: KnowledgeObject,
        *,
        principal: Principal,
        dry_run: bool,
    ) -> BackfillEntry:
        memory_type, ambiguous = self._map_type(obj)
        idempotency_key = (
            f"legacy-knowledge-object:{principal.tenant_id}:{obj.id}:v{obj.version}"
        )
        existing_episode = self.service.store.find_episode_by_idempotency(
            principal.tenant_id,
            idempotency_key,
        )
        existing_memory = self._existing_memory(
            tenant_id=principal.tenant_id,
            legacy_object_id=obj.id,
        )
        if existing_episode is not None and existing_memory is not None:
            return BackfillEntry(
                legacy_object_id=obj.id,
                action="skipped",
                mapped_memory_type=memory_type,
                episode_id=existing_episode.episode_id,
                memory_id=existing_memory.memory_id,
                reason="The legacy object version was already migrated.",
            )
        if dry_run:
            return BackfillEntry(
                legacy_object_id=obj.id,
                action="ambiguous" if ambiguous else "planned",
                mapped_memory_type=memory_type,
                reason=(
                    "The legacy object type requires governance review before publication."
                    if ambiguous
                    else "Ready for idempotent canonical-episode and memory migration."
                ),
            )

        raw_content = json.dumps(
            obj.model_dump(mode="json"),
            sort_keys=True,
            ensure_ascii=False,
        )
        episode_result = self.service.ingest_episode(
            EpisodeIngestionRequest(
                tenant_id=principal.tenant_id,
                source_type="legacy_knowledge_object",
                source_id=obj.id,
                source_uri=f"ukb://legacy/knowledge-objects/{obj.id}",
                title=obj.title,
                raw_content=raw_content,
                content_type="application/json",
                idempotency_key=idempotency_key,
                observed_at=obj.updated_at,
                effective_from=obj.published_at or obj.created_at,
                classification=obj.sensitivity,
                owner=obj.owner,
                metadata={
                    "legacy_object_id": obj.id,
                    "legacy_object_type": obj.type.value,
                    "legacy_version": obj.version,
                    "legacy_status": obj.status.value,
                },
            ),
            principal=principal,
        )
        episode = episode_result.episode
        status = MemoryStatus.unverified if ambiguous else MemoryStatus.published
        authority = (
            AuthorityLevel.unverified
            if ambiguous
            else self._authority(obj.authority_tier)
        )
        memory = self.service.promote_memory(
            MemoryPromotionRequest(
                tenant_id=principal.tenant_id,
                memory_type=memory_type,
                source_type="legacy_knowledge_object",
                source_id=obj.id,
                business_domain=obj.domain,
                related_metrics=[obj.id]
                if obj.type == KnowledgeObjectType.metric
                else [],
                related_entities=self._related_entities(obj),
                effective_from=obj.published_at or obj.created_at,
                status=status,
                classification=obj.sensitivity,
                authority_level=authority,
                owner=obj.owner,
                approved_by=(obj.published_by or principal.subject)
                if not ambiguous
                else None,
                content={
                    "legacy_object_id": obj.id,
                    "title": obj.title,
                    "summary": obj.summary,
                    "legacy_object_type": obj.type.value,
                    "legacy_version": obj.version,
                    "aliases": obj.aliases,
                    "attributes": obj.attributes,
                    "relationships": [
                        relationship.model_dump(mode="json")
                        for relationship in obj.relationships
                    ],
                },
                provenance=MemoryProvenance(
                    episode_id=episode.episode_id,
                    source_checksum=episode.source_checksum,
                    derivation_type="legacy_backfill",
                    derived_by=principal.subject,
                    derivation_version="1.0",
                    source_relationships=[
                        relationship.target_id for relationship in obj.relationships
                    ],
                    notes=[
                        "The original KnowledgeObject remains in the legacy store.",
                        f"Legacy identifier preserved: {obj.id}",
                    ],
                ),
                tags=[
                    "legacy-backfill",
                    f"legacy-object:{obj.id}",
                    f"legacy-type:{obj.type.value}",
                ],
            ),
            principal=principal,
        )
        return BackfillEntry(
            legacy_object_id=obj.id,
            action="ambiguous" if ambiguous else "migrated",
            mapped_memory_type=memory_type,
            episode_id=episode.episode_id,
            memory_id=memory.memory_id,
            reason=(
                "Migrated as unverified memory pending governance review."
                if ambiguous
                else "Migrated without changing or deleting the legacy object."
            ),
        )

    def _existing_memory(
        self,
        *,
        tenant_id: str,
        legacy_object_id: str,
    ):
        marker = f"legacy-object:{legacy_object_id}"
        return next(
            (
                memory
                for memory in self.service.store.memories.values()
                if memory.tenant_id == tenant_id and marker in memory.tags
            ),
            None,
        )

    @classmethod
    def _map_type(cls, obj: KnowledgeObject) -> tuple[MemoryType, bool]:
        mapped = cls.TYPE_MAP.get(obj.type)
        if mapped is None:
            return MemoryType.source_document, True
        return mapped, False

    @staticmethod
    def _authority(tier: int) -> AuthorityLevel:
        return {
            1: AuthorityLevel.authoritative,
            2: AuthorityLevel.approved,
            3: AuthorityLevel.corroborated,
            4: AuthorityLevel.unverified,
            5: AuthorityLevel.hypothesis,
        }.get(tier, AuthorityLevel.unverified)

    @staticmethod
    def _related_entities(obj: KnowledgeObject) -> list[str]:
        return sorted(
            {
                relationship.target_id
                for relationship in obj.relationships
                if relationship.target_id
            }
        )
