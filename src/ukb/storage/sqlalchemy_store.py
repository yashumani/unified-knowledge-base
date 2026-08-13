from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from ukb.models import AuditEvent, KnowledgeObject, ReviewItem, SourceEvidence
from ukb.storage.memory import BrainStore
from ukb.storage.orm import AuditEventRow, Base, KnowledgeObjectRow, ReviewItemRow, SourceRow


class SqlAlchemyBrainStore(BrainStore):
    """Durable UKB store backed by SQLite or PostgreSQL through SQLAlchemy.

    Public dictionaries remain available for compatibility with the current
    service layer. Every supported write updates the database, and audit writes
    also flush the current review/object snapshot so mutable review transitions
    survive a process restart.
    """

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
        return create_engine(
            database_url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )

    def _prepare_sqlite_directory(self, database_url: str) -> None:
        url = make_url(database_url)
        if url.get_backend_name() != "sqlite":
            return
        database = url.database
        if not database or database == ":memory:":
            return
        Path(database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    def reload(self) -> None:
        """Reload the in-process compatibility cache from durable rows."""

        with self.session_factory() as session:
            self.sources = {
                row.source_id: SourceEvidence.model_validate_json(row.payload)
                for row in session.scalars(select(SourceRow))
            }
            self.review_items = {
                row.id: ReviewItem.model_validate_json(row.payload)
                for row in session.scalars(select(ReviewItemRow))
            }
            self.knowledge_objects = {
                row.id: KnowledgeObject.model_validate_json(row.payload)
                for row in session.scalars(select(KnowledgeObjectRow))
            }
            self.audit_events = [
                AuditEvent.model_validate_json(row.payload)
                for row in session.scalars(
                    select(AuditEventRow).order_by(AuditEventRow.created_at, AuditEventRow.id)
                )
            ]

    def add_source(self, source: SourceEvidence) -> SourceEvidence:
        super().add_source(source)
        with self.session_factory.begin() as session:
            session.merge(self._source_row(source))
        return source

    def add_review_item(self, review_item: ReviewItem) -> ReviewItem:
        super().add_review_item(review_item)
        with self.session_factory.begin() as session:
            session.merge(self._review_row(review_item))
        return review_item

    def publish_object(self, obj: KnowledgeObject) -> KnowledgeObject:
        published = super().publish_object(obj)
        with self.session_factory.begin() as session:
            session.merge(self._object_row(published))
        return published

    def add_audit_event(self, event: AuditEvent) -> AuditEvent:
        super().add_audit_event(event)
        with self.session_factory.begin() as session:
            for source in self.sources.values():
                session.merge(self._source_row(source))
            for review_item in self.review_items.values():
                session.merge(self._review_row(review_item))
            for obj in self.knowledge_objects.values():
                session.merge(self._object_row(obj))
            session.merge(self._audit_row(event))
        return event

    def clear(self) -> None:
        super().clear()
        with self.session_factory.begin() as session:
            session.execute(delete(AuditEventRow))
            session.execute(delete(ReviewItemRow))
            session.execute(delete(KnowledgeObjectRow))
            session.execute(delete(SourceRow))

    def close(self) -> None:
        self.engine.dispose()

    def _source_row(self, source: SourceEvidence) -> SourceRow:
        return SourceRow(
            source_id=source.source_id,
            domain=source.domain,
            sensitivity=source.sensitivity.value,
            payload=source.model_dump_json(),
            created_at=source.created_at,
        )

    def _review_row(self, review_item: ReviewItem) -> ReviewItemRow:
        candidate = review_item.candidate_object
        return ReviewItemRow(
            id=review_item.id,
            source_id=review_item.source_id,
            status=review_item.status.value,
            domain=candidate.domain,
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
            payload=obj.model_dump_json(),
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )

    def _audit_row(self, event: AuditEvent) -> AuditEventRow:
        return AuditEventRow(
            id=event.id,
            event_type=event.event_type,
            actor=event.actor,
            target_id=event.target_id,
            payload=event.model_dump_json(),
            created_at=event.created_at,
        )
