from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from ukb.models import (
    AITaskRun,
    AuditEvent,
    ContextPack,
    EvidenceChunk,
    KnowledgeObject,
    RelationshipRecord,
    ReviewItem,
    SourceEvidence,
    SourceVersion,
)
from ukb.storage.memory import BrainStore
from ukb.storage.orm import (
    AITaskRunRow,
    AuditEventRow,
    Base,
    ContextPackRow,
    EvidenceChunkRow,
    KnowledgeObjectRow,
    RelationshipRow,
    ReviewItemRow,
    SourceRow,
    SourceVersionRow,
)


class SqlAlchemyBrainStore(BrainStore):
    """Durable authoritative store backed by SQLite or PostgreSQL."""

    def __init__(self, database_url: str, *, create_schema: bool = True):
        super().__init__()
        self.database_url = database_url
        self._prepare_sqlite_directory(database_url)
        self.engine = self._build_engine(database_url)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )
        if create_schema:
            Base.metadata.create_all(self.engine)
        self.reload()

    def _build_engine(self, database_url: str) -> Engine:
        url = make_url(database_url)
        connect_args: dict[str, object] = {}
        if url.get_backend_name() == "sqlite":
            connect_args["check_same_thread"] = False
        return create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)

    def _prepare_sqlite_directory(self, database_url: str) -> None:
        url = make_url(database_url)
        if url.get_backend_name() != "sqlite":
            return
        database = url.database
        if not database or database == ":memory:":
            return
        Path(database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    def reload(self) -> None:
        with self.session_factory() as session:
            self.sources = {
                row.source_id: SourceEvidence.model_validate_json(row.payload)
                for row in session.scalars(select(SourceRow))
            }
            self.source_versions = {
                row.id: SourceVersion.model_validate_json(row.payload)
                for row in session.scalars(select(SourceVersionRow))
            }
            self.evidence_chunks = {
                row.id: EvidenceChunk.model_validate_json(row.payload)
                for row in session.scalars(select(EvidenceChunkRow))
            }
            self.review_items = {
                row.id: ReviewItem.model_validate_json(row.payload)
                for row in session.scalars(select(ReviewItemRow))
            }
            self.knowledge_objects = {
                row.id: KnowledgeObject.model_validate_json(row.payload)
                for row in session.scalars(select(KnowledgeObjectRow))
            }
            self.relationships = {
                row.id: RelationshipRecord.model_validate_json(row.payload)
                for row in session.scalars(select(RelationshipRow))
            }
            self.ai_task_runs = {
                row.id: AITaskRun.model_validate_json(row.payload)
                for row in session.scalars(select(AITaskRunRow))
            }
            self.context_packs = {
                row.id: ContextPack.model_validate_json(row.payload)
                for row in session.scalars(select(ContextPackRow))
            }
            self.audit_events = [
                AuditEvent.model_validate_json(row.payload)
                for row in session.scalars(
                    select(AuditEventRow).order_by(AuditEventRow.created_at, AuditEventRow.id)
                )
            ]

    def add_source(self, source: SourceEvidence) -> SourceEvidence:
        super().add_source(source)
        self._merge(self._source_row(source))
        return source

    def add_source_version(self, version: SourceVersion) -> SourceVersion:
        super().add_source_version(version)
        self._merge(self._source_version_row(version))
        source = self.sources.get(version.source_id)
        if source is not None:
            self._merge(self._source_row(source))
        return version

    def add_evidence_chunk(self, chunk: EvidenceChunk) -> EvidenceChunk:
        super().add_evidence_chunk(chunk)
        self._merge(self._chunk_row(chunk))
        return chunk

    def add_evidence_chunks(self, chunks: list[EvidenceChunk]) -> list[EvidenceChunk]:
        super().add_evidence_chunks(chunks)
        with self.session_factory.begin() as session:
            for chunk in chunks:
                session.merge(self._chunk_row(chunk))
        return chunks

    def add_review_item(self, review_item: ReviewItem) -> ReviewItem:
        super().add_review_item(review_item)
        self._merge(self._review_row(review_item))
        return review_item

    def update_review_item(self, review_item: ReviewItem) -> ReviewItem:
        super().update_review_item(review_item)
        self._merge(self._review_row(review_item))
        return review_item

    def publish_object(self, obj: KnowledgeObject) -> KnowledgeObject:
        published = super().publish_object(obj)
        self._merge(self._object_row(published))
        return published

    def add_object(self, obj: KnowledgeObject) -> KnowledgeObject:
        super().add_object(obj)
        self._merge(self._object_row(obj))
        return obj

    def add_relationship(self, relationship: RelationshipRecord) -> RelationshipRecord:
        super().add_relationship(relationship)
        self._merge(self._relationship_row(relationship))
        return relationship

    def add_ai_task_run(self, task_run: AITaskRun) -> AITaskRun:
        super().add_ai_task_run(task_run)
        self._merge(self._ai_task_row(task_run))
        return task_run

    def add_context_pack(self, context_pack: ContextPack) -> ContextPack:
        super().add_context_pack(context_pack)
        self._merge(self._context_pack_row(context_pack))
        return context_pack

    def add_audit_event(self, event: AuditEvent) -> AuditEvent:
        super().add_audit_event(event)
        self._merge(self._audit_row(event))
        return event

    def clear(self) -> None:
        super().clear()
        with self.session_factory.begin() as session:
            for row_type in (
                AuditEventRow,
                ContextPackRow,
                AITaskRunRow,
                RelationshipRow,
                ReviewItemRow,
                KnowledgeObjectRow,
                EvidenceChunkRow,
                SourceVersionRow,
                SourceRow,
            ):
                session.execute(delete(row_type))

    def close(self) -> None:
        self.engine.dispose()

    def _merge(self, row: object) -> None:
        with self.session_factory.begin() as session:
            session.merge(row)

    def _source_row(self, source: SourceEvidence) -> SourceRow:
        return SourceRow(
            source_id=source.source_id,
            domain=source.domain,
            sensitivity=source.sensitivity.value,
            content_hash=source.content_hash,
            payload=source.model_dump_json(),
            created_at=source.created_at,
            updated_at=source.updated_at,
        )

    def _source_version_row(self, version: SourceVersion) -> SourceVersionRow:
        return SourceVersionRow(
            id=version.id,
            source_id=version.source_id,
            version=version.version,
            content_hash=version.content_hash,
            object_key=version.object_key,
            payload=version.model_dump_json(),
            created_at=version.created_at,
        )

    def _chunk_row(self, chunk: EvidenceChunk) -> EvidenceChunkRow:
        return EvidenceChunkRow(
            id=chunk.id,
            source_id=chunk.source_id,
            source_version_id=chunk.source_version_id,
            ordinal=chunk.ordinal,
            content_hash=chunk.content_hash,
            sensitivity=chunk.sensitivity.value,
            payload=chunk.model_dump_json(),
            created_at=chunk.created_at,
        )

    def _review_row(self, review_item: ReviewItem) -> ReviewItemRow:
        return ReviewItemRow(
            id=review_item.id,
            source_id=review_item.source_id,
            status=review_item.status.value,
            revision=review_item.revision,
            domain=review_item.candidate_object.domain,
            payload=review_item.model_dump_json(),
            created_at=review_item.created_at,
            updated_at=review_item.updated_at,
        )

    def _object_row(self, obj: KnowledgeObject) -> KnowledgeObjectRow:
        return KnowledgeObjectRow(
            id=obj.id,
            object_type=obj.type.value,
            domain=obj.domain,
            status=obj.status.value,
            sensitivity=obj.sensitivity.value,
            version=obj.version,
            payload=obj.model_dump_json(),
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )

    def _relationship_row(self, relationship: RelationshipRecord) -> RelationshipRow:
        return RelationshipRow(
            id=relationship.id,
            source_object_id=relationship.source_object_id,
            target_object_id=relationship.target_object_id,
            relationship_type=relationship.relationship_type,
            status=relationship.status.value,
            payload=relationship.model_dump_json(),
            created_at=relationship.created_at,
            updated_at=relationship.updated_at,
        )

    def _ai_task_row(self, task_run: AITaskRun) -> AITaskRunRow:
        return AITaskRunRow(
            id=task_run.id,
            task_type=task_run.task_type,
            provider=task_run.provider.value,
            status=task_run.status.value,
            source_id=task_run.source_id,
            review_item_id=task_run.review_item_id,
            payload=task_run.model_dump_json(),
            created_at=task_run.created_at,
        )

    def _context_pack_row(self, pack: ContextPack) -> ContextPackRow:
        return ContextPackRow(
            id=pack.context_pack_id,
            user_id=pack.user_id,
            mode=pack.mode,
            access_decision=pack.access_decision,
            payload=pack.model_dump_json(),
            created_at=pack.generated_at,
        )

    def _audit_row(self, event: AuditEvent) -> AuditEventRow:
        return AuditEventRow(
            id=event.id,
            event_type=event.event_type,
            actor=event.actor,
            target_id=event.target_id,
            request_id=event.request_id,
            payload=event.model_dump_json(),
            created_at=event.created_at,
        )
