from __future__ import annotations

from dataclasses import dataclass, field

from ukb.models import (
    AITaskRun,
    AuditEvent,
    ContextPack,
    EvidenceChunk,
    KnowledgeObject,
    RelationshipRecord,
    ReviewItem,
    ReviewStatus,
    SourceEvidence,
    SourceVersion,
)


@dataclass
class BrainStore:
    """In-memory backend implementing the authoritative-store contract.

    Tests and explicit offline sessions use this implementation. Local and
    production environment files select SqlAlchemyBrainStore for durability.
    """

    sources: dict[str, SourceEvidence] = field(default_factory=dict)
    source_versions: dict[str, SourceVersion] = field(default_factory=dict)
    evidence_chunks: dict[str, EvidenceChunk] = field(default_factory=dict)
    review_items: dict[str, ReviewItem] = field(default_factory=dict)
    knowledge_objects: dict[str, KnowledgeObject] = field(default_factory=dict)
    relationships: dict[str, RelationshipRecord] = field(default_factory=dict)
    ai_task_runs: dict[str, AITaskRun] = field(default_factory=dict)
    context_packs: dict[str, ContextPack] = field(default_factory=dict)
    audit_events: list[AuditEvent] = field(default_factory=list)

    def add_source(self, source: SourceEvidence) -> SourceEvidence:
        self.sources[source.source_id] = source
        return source

    def add_source_version(self, version: SourceVersion) -> SourceVersion:
        self.source_versions[version.id] = version
        source = self.sources.get(version.source_id)
        if source is not None:
            source.current_version_id = version.id
            source.content_hash = version.content_hash
            source.updated_at = version.created_at
        return version

    def add_evidence_chunk(self, chunk: EvidenceChunk) -> EvidenceChunk:
        self.evidence_chunks[chunk.id] = chunk
        return chunk

    def add_evidence_chunks(self, chunks: list[EvidenceChunk]) -> list[EvidenceChunk]:
        for chunk in chunks:
            self.add_evidence_chunk(chunk)
        return chunks

    def list_source_versions(self, source_id: str) -> list[SourceVersion]:
        return sorted(
            (item for item in self.source_versions.values() if item.source_id == source_id),
            key=lambda item: (item.version, item.created_at),
        )

    def list_evidence_chunks(
        self,
        *,
        source_id: str | None = None,
        source_version_id: str | None = None,
    ) -> list[EvidenceChunk]:
        chunks = list(self.evidence_chunks.values())
        if source_id is not None:
            chunks = [chunk for chunk in chunks if chunk.source_id == source_id]
        if source_version_id is not None:
            chunks = [chunk for chunk in chunks if chunk.source_version_id == source_version_id]
        return sorted(chunks, key=lambda item: (item.source_id, item.ordinal))

    def add_review_item(self, review_item: ReviewItem) -> ReviewItem:
        self.review_items[review_item.id] = review_item
        return review_item

    def update_review_item(self, review_item: ReviewItem) -> ReviewItem:
        self.review_items[review_item.id] = review_item
        return review_item

    def get_review_item(self, review_item_id: str) -> ReviewItem:
        return self.review_items[review_item_id]

    def list_review_items(
        self,
        status: ReviewStatus | None = None,
        statuses: set[ReviewStatus] | None = None,
    ) -> list[ReviewItem]:
        items = list(self.review_items.values())
        if status is not None:
            items = [item for item in items if item.status == status]
        if statuses is not None:
            items = [item for item in items if item.status in statuses]
        return sorted(items, key=lambda item: item.updated_at, reverse=True)

    def publish_object(self, obj: KnowledgeObject) -> KnowledgeObject:
        obj.status = ReviewStatus.published
        self.knowledge_objects[obj.id] = obj
        return obj

    def add_object(self, obj: KnowledgeObject) -> KnowledgeObject:
        self.knowledge_objects[obj.id] = obj
        return obj

    def list_objects(self, domain: str | None = None) -> list[KnowledgeObject]:
        objects = list(self.knowledge_objects.values())
        if domain:
            objects = [obj for obj in objects if obj.domain == domain]
        return sorted(objects, key=lambda item: item.updated_at, reverse=True)

    def add_relationship(self, relationship: RelationshipRecord) -> RelationshipRecord:
        self.relationships[relationship.id] = relationship
        return relationship

    def add_ai_task_run(self, task_run: AITaskRun) -> AITaskRun:
        self.ai_task_runs[task_run.id] = task_run
        return task_run

    def add_context_pack(self, context_pack: ContextPack) -> ContextPack:
        self.context_packs[context_pack.context_pack_id] = context_pack
        return context_pack

    def add_audit_event(self, event: AuditEvent) -> AuditEvent:
        self.audit_events.append(event)
        return event

    def clear(self) -> None:
        self.sources.clear()
        self.source_versions.clear()
        self.evidence_chunks.clear()
        self.review_items.clear()
        self.knowledge_objects.clear()
        self.relationships.clear()
        self.ai_task_runs.clear()
        self.context_packs.clear()
        self.audit_events.clear()

    def close(self) -> None:
        """Compatibility hook for durable stores."""
