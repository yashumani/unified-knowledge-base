from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from sqlalchemy import DateTime, Index, Integer, String, Text, create_engine, delete, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from ukb.storage.orm import Base
from ukb.talk2data.models import (
    CanonicalEpisode,
    GovernedMemoryObject,
    IndexWatermark,
    MemoryRelationship,
    SourceIngestionHealth,
    Talk2DataAuditEvent,
    TenantDomainPack,
)


class DomainPackRow(Base):
    __tablename__ = "talk2data_domain_packs"

    domain_pack_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(160), index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), index=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CanonicalEpisodeRow(Base):
    __tablename__ = "talk2data_canonical_episodes"

    episode_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(160), index=True)
    source_type: Mapped[str] = mapped_column(String(80), index=True)
    source_id: Mapped[str] = mapped_column(String(320), index=True)
    source_checksum: Mapped[str] = mapped_column(String(64), index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    classification: Mapped[str] = mapped_column(String(40), index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    ingestion_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GovernedMemoryRow(Base):
    __tablename__ = "talk2data_memory_objects"

    memory_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(160), index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_type: Mapped[str] = mapped_column(String(80), index=True)
    business_domain: Mapped[str] = mapped_column(String(160), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    classification: Mapped[str] = mapped_column(String(40), index=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_id: Mapped[str] = mapped_column(String(320), index=True)
    episode_id: Mapped[str] = mapped_column(String(80), index=True)
    checksum: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    ingestion_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MemoryRelationshipRow(Base):
    __tablename__ = "talk2data_memory_relationships"

    relationship_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(160), index=True)
    source_memory_id: Mapped[str] = mapped_column(String(80), index=True)
    relationship_type: Mapped[str] = mapped_column(String(120), index=True)
    target_memory_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    target_entity_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SourceHealthRow(Base):
    __tablename__ = "talk2data_source_health"

    key: Mapped[str] = mapped_column(String(520), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(160), index=True)
    source_id: Mapped[str] = mapped_column(String(320), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IndexWatermarkRow(Base):
    __tablename__ = "talk2data_index_watermarks"

    key: Mapped[str] = mapped_column(String(400), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(160), index=True)
    partition: Mapped[str] = mapped_column(String(200), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Talk2DataAuditRow(Base):
    __tablename__ = "talk2data_audit_events"

    audit_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(160), index=True)
    actor: Mapped[str] = mapped_column(String(200), index=True)
    event_type: Mapped[str] = mapped_column(String(160), index=True)
    target_id: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index(
    "ux_talk2data_domain_pack_tenant_version",
    DomainPackRow.tenant_id,
    DomainPackRow.version,
    unique=True,
)
Index(
    "ux_talk2data_episode_tenant_idempotency",
    CanonicalEpisodeRow.tenant_id,
    CanonicalEpisodeRow.idempotency_key,
    unique=True,
)
Index(
    "ix_talk2data_episode_source_checksum",
    CanonicalEpisodeRow.tenant_id,
    CanonicalEpisodeRow.source_id,
    CanonicalEpisodeRow.source_checksum,
)
Index(
    "ix_talk2data_memory_tenant_temporal",
    GovernedMemoryRow.tenant_id,
    GovernedMemoryRow.effective_from,
    GovernedMemoryRow.effective_to,
)
Index(
    "ix_talk2data_memory_tenant_domain_status",
    GovernedMemoryRow.tenant_id,
    GovernedMemoryRow.business_domain,
    GovernedMemoryRow.status,
)

TALK2DATA_TABLES = [
    DomainPackRow.__table__,
    CanonicalEpisodeRow.__table__,
    GovernedMemoryRow.__table__,
    MemoryRelationshipRow.__table__,
    SourceHealthRow.__table__,
    IndexWatermarkRow.__table__,
    Talk2DataAuditRow.__table__,
]


@runtime_checkable
class Talk2DataRepository(Protocol):
    domain_packs: dict[str, TenantDomainPack]
    episodes: dict[str, CanonicalEpisode]
    memories: dict[str, GovernedMemoryObject]
    relationships: dict[str, MemoryRelationship]
    source_health: dict[str, SourceIngestionHealth]
    index_watermarks: dict[str, IndexWatermark]
    audit_events: list[Talk2DataAuditEvent]

    def add_domain_pack(self, domain_pack: TenantDomainPack) -> TenantDomainPack: ...

    def add_episode(self, episode: CanonicalEpisode) -> CanonicalEpisode: ...

    def add_memory(self, memory: GovernedMemoryObject) -> GovernedMemoryObject: ...

    def add_relationship(self, relationship: MemoryRelationship) -> MemoryRelationship: ...

    def upsert_source_health(self, health: SourceIngestionHealth) -> SourceIngestionHealth: ...

    def upsert_index_watermark(self, watermark: IndexWatermark) -> IndexWatermark: ...

    def add_audit_event(self, event: Talk2DataAuditEvent) -> Talk2DataAuditEvent: ...

    def close(self) -> None: ...


class InMemoryTalk2DataStore:
    """Deterministic authoritative store for tests and explicit offline sessions."""

    def __init__(self) -> None:
        self.domain_packs: dict[str, TenantDomainPack] = {}
        self.episodes: dict[str, CanonicalEpisode] = {}
        self.memories: dict[str, GovernedMemoryObject] = {}
        self.relationships: dict[str, MemoryRelationship] = {}
        self.source_health: dict[str, SourceIngestionHealth] = {}
        self.index_watermarks: dict[str, IndexWatermark] = {}
        self.audit_events: list[Talk2DataAuditEvent] = []

    @staticmethod
    def source_health_key(tenant_id: str, source_id: str) -> str:
        return f"{tenant_id}:{source_id}"

    @staticmethod
    def watermark_key(tenant_id: str, partition: str) -> str:
        return f"{tenant_id}:{partition}"

    def add_domain_pack(self, domain_pack: TenantDomainPack) -> TenantDomainPack:
        self.domain_packs[domain_pack.domain_pack_id] = domain_pack
        return domain_pack

    def add_episode(self, episode: CanonicalEpisode) -> CanonicalEpisode:
        self.episodes[episode.episode_id] = episode
        return episode

    def add_memory(self, memory: GovernedMemoryObject) -> GovernedMemoryObject:
        self.memories[memory.memory_id] = memory
        return memory

    def add_relationship(self, relationship: MemoryRelationship) -> MemoryRelationship:
        self.relationships[relationship.relationship_id] = relationship
        return relationship

    def upsert_source_health(self, health: SourceIngestionHealth) -> SourceIngestionHealth:
        self.source_health[self.source_health_key(health.tenant_id, health.source_id)] = health
        return health

    def upsert_index_watermark(self, watermark: IndexWatermark) -> IndexWatermark:
        self.index_watermarks[self.watermark_key(watermark.tenant_id, watermark.partition)] = watermark
        return watermark

    def add_audit_event(self, event: Talk2DataAuditEvent) -> Talk2DataAuditEvent:
        self.audit_events.append(event)
        return event

    def find_episode_by_idempotency(
        self,
        tenant_id: str,
        idempotency_key: str,
    ) -> CanonicalEpisode | None:
        return next(
            (
                episode
                for episode in self.episodes.values()
                if episode.tenant_id == tenant_id and episode.idempotency_key == idempotency_key
            ),
            None,
        )

    def find_episode_by_checksum(
        self,
        tenant_id: str,
        source_id: str,
        checksum: str,
    ) -> CanonicalEpisode | None:
        return next(
            (
                episode
                for episode in self.episodes.values()
                if episode.tenant_id == tenant_id
                and episode.source_id == source_id
                and episode.source_checksum == checksum
            ),
            None,
        )

    def find_memory_duplicate(
        self,
        tenant_id: str,
        episode_id: str,
        checksum: str,
    ) -> GovernedMemoryObject | None:
        return next(
            (
                memory
                for memory in self.memories.values()
                if memory.tenant_id == tenant_id
                and memory.provenance.episode_id == episode_id
                and memory.checksum == checksum
            ),
            None,
        )

    def clear(self) -> None:
        self.domain_packs.clear()
        self.episodes.clear()
        self.memories.clear()
        self.relationships.clear()
        self.source_health.clear()
        self.index_watermarks.clear()
        self.audit_events.clear()

    def close(self) -> None:
        return None


class SqlAlchemyTalk2DataStore(InMemoryTalk2DataStore):
    """Durable Talk2Data memory contract backed by SQLite or PostgreSQL."""

    def __init__(self, database_url: str, *, create_schema: bool = True) -> None:
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

    @staticmethod
    def _build_engine(database_url: str) -> Engine:
        url = make_url(database_url)
        connect_args: dict[str, object] = {}
        if url.get_backend_name() == "sqlite":
            connect_args["check_same_thread"] = False
        return create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)

    @staticmethod
    def _prepare_sqlite_directory(database_url: str) -> None:
        url = make_url(database_url)
        if url.get_backend_name() != "sqlite":
            return
        database = url.database
        if not database or database == ":memory:":
            return
        Path(database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    def reload(self) -> None:
        with self.session_factory() as session:
            packs = list(session.scalars(select(DomainPackRow)))
            episodes = list(session.scalars(select(CanonicalEpisodeRow)))
            memories = list(session.scalars(select(GovernedMemoryRow)))
            relationships = list(session.scalars(select(MemoryRelationshipRow)))
            source_health = list(session.scalars(select(SourceHealthRow)))
            watermarks = list(session.scalars(select(IndexWatermarkRow)))
            audit = list(
                session.scalars(
                    select(Talk2DataAuditRow).order_by(
                        Talk2DataAuditRow.created_at,
                        Talk2DataAuditRow.audit_id,
                    )
                )
            )
        self.domain_packs = {
            row.domain_pack_id: TenantDomainPack.model_validate_json(row.payload) for row in packs
        }
        self.episodes = {
            row.episode_id: CanonicalEpisode.model_validate_json(row.payload) for row in episodes
        }
        self.memories = {
            row.memory_id: GovernedMemoryObject.model_validate_json(row.payload) for row in memories
        }
        self.relationships = {
            row.relationship_id: MemoryRelationship.model_validate_json(row.payload)
            for row in relationships
        }
        self.source_health = {
            row.key: SourceIngestionHealth.model_validate_json(row.payload) for row in source_health
        }
        self.index_watermarks = {
            row.key: IndexWatermark.model_validate_json(row.payload) for row in watermarks
        }
        self.audit_events = [Talk2DataAuditEvent.model_validate_json(row.payload) for row in audit]

    def add_domain_pack(self, domain_pack: TenantDomainPack) -> TenantDomainPack:
        super().add_domain_pack(domain_pack)
        self._merge(
            DomainPackRow(
                domain_pack_id=domain_pack.domain_pack_id,
                tenant_id=domain_pack.tenant_id,
                version=domain_pack.version,
                status=domain_pack.status.value,
                effective_from=domain_pack.effective_from,
                effective_to=domain_pack.effective_to,
                checksum=domain_pack.checksum,
                payload=domain_pack.model_dump_json(),
                updated_at=domain_pack.updated_at,
            )
        )
        return domain_pack

    def add_episode(self, episode: CanonicalEpisode) -> CanonicalEpisode:
        super().add_episode(episode)
        self._merge(
            CanonicalEpisodeRow(
                episode_id=episode.episode_id,
                tenant_id=episode.tenant_id,
                source_type=episode.source_type,
                source_id=episode.source_id,
                source_checksum=episode.source_checksum,
                idempotency_key=episode.idempotency_key,
                observed_at=episode.observed_at,
                classification=episode.classification.value,
                payload=episode.model_dump_json(),
                ingestion_timestamp=episode.ingestion_timestamp,
            )
        )
        return episode

    def add_memory(self, memory: GovernedMemoryObject) -> GovernedMemoryObject:
        super().add_memory(memory)
        self._merge(
            GovernedMemoryRow(
                memory_id=memory.memory_id,
                tenant_id=memory.tenant_id,
                version=memory.version,
                memory_type=memory.memory_type.value,
                business_domain=memory.business_domain,
                status=memory.status.value,
                classification=memory.classification.value,
                effective_from=memory.effective_from,
                effective_to=memory.effective_to,
                source_id=memory.source_id,
                episode_id=memory.provenance.episode_id,
                checksum=memory.checksum,
                payload=memory.model_dump_json(),
                ingestion_timestamp=memory.ingestion_timestamp,
            )
        )
        return memory

    def add_relationship(self, relationship: MemoryRelationship) -> MemoryRelationship:
        super().add_relationship(relationship)
        self._merge(
            MemoryRelationshipRow(
                relationship_id=relationship.relationship_id,
                tenant_id=relationship.tenant_id,
                source_memory_id=relationship.source_memory_id,
                relationship_type=relationship.relationship_type,
                target_memory_id=relationship.target_memory_id,
                target_entity_id=relationship.target_entity_id,
                status=relationship.status.value,
                payload=relationship.model_dump_json(),
                effective_from=relationship.effective_from,
            )
        )
        return relationship

    def upsert_source_health(self, health: SourceIngestionHealth) -> SourceIngestionHealth:
        super().upsert_source_health(health)
        key = self.source_health_key(health.tenant_id, health.source_id)
        self._merge(
            SourceHealthRow(
                key=key,
                tenant_id=health.tenant_id,
                source_id=health.source_id,
                status=health.status.value,
                payload=health.model_dump_json(),
                updated_at=health.updated_at,
            )
        )
        return health

    def upsert_index_watermark(self, watermark: IndexWatermark) -> IndexWatermark:
        super().upsert_index_watermark(watermark)
        key = self.watermark_key(watermark.tenant_id, watermark.partition)
        self._merge(
            IndexWatermarkRow(
                key=key,
                tenant_id=watermark.tenant_id,
                partition=watermark.partition,
                status=watermark.status.value,
                payload=watermark.model_dump_json(),
                updated_at=watermark.updated_at,
            )
        )
        return watermark

    def add_audit_event(self, event: Talk2DataAuditEvent) -> Talk2DataAuditEvent:
        super().add_audit_event(event)
        self._merge(
            Talk2DataAuditRow(
                audit_id=event.audit_id,
                tenant_id=event.tenant_id,
                actor=event.actor,
                event_type=event.event_type,
                target_id=event.target_id,
                payload=event.model_dump_json(),
                created_at=event.created_at,
            )
        )
        return event

    def clear(self) -> None:
        super().clear()
        with self.session_factory.begin() as session:
            for row_type in (
                Talk2DataAuditRow,
                IndexWatermarkRow,
                SourceHealthRow,
                MemoryRelationshipRow,
                GovernedMemoryRow,
                CanonicalEpisodeRow,
                DomainPackRow,
            ):
                session.execute(delete(row_type))

    def _merge(self, row: object) -> None:
        with self.session_factory.begin() as session:
            session.merge(row)

    def close(self) -> None:
        self.engine.dispose()


def build_talk2data_store(
    *,
    store_backend: str,
    database_url: str,
    create_schema: bool,
) -> InMemoryTalk2DataStore:
    if store_backend.casefold() in {"sqlalchemy", "sql", "postgres", "postgresql", "sqlite"}:
        return SqlAlchemyTalk2DataStore(database_url, create_schema=create_schema)
    return InMemoryTalk2DataStore()
