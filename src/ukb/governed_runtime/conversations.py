from __future__ import annotations

import threading
from collections.abc import Iterable
from typing import Protocol

from sqlalchemy import JSON, Column, DateTime, Integer, MetaData, String, Table, Text, create_engine, delete, select
from sqlalchemy.engine import Engine

from ukb.config import Settings
from ukb.governed_runtime.models import CacheEventRecord, ConversationMessage, ConversationRecord
from ukb.models import utc_now

metadata = MetaData()

runtime_conversations = Table(
    "runtime_conversations",
    metadata,
    Column("conversation_id", String(80), primary_key=True),
    Column("tenant_id", String(160), nullable=False, index=True),
    Column("subject", String(320), nullable=False, index=True),
    Column("title", String(500), nullable=False),
    Column("summary", Text(), nullable=True),
    Column("summary_version", Integer(), nullable=False),
    Column("status", String(32), nullable=False),
    Column("attributes", JSON(), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

runtime_messages = Table(
    "runtime_conversation_messages",
    metadata,
    Column("message_id", String(80), primary_key=True),
    Column("conversation_id", String(80), nullable=False, index=True),
    Column("tenant_id", String(160), nullable=False, index=True),
    Column("subject", String(320), nullable=False),
    Column("role", String(32), nullable=False),
    Column("content", Text(), nullable=False),
    Column("context_pack_id", String(100), nullable=True),
    Column("cache_event_id", String(100), nullable=True),
    Column("attributes", JSON(), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, index=True),
)

runtime_cache_events = Table(
    "runtime_cache_events",
    metadata,
    Column("event_id", String(100), primary_key=True),
    Column("request_id", String(100), nullable=False, index=True),
    Column("tenant_id", String(160), nullable=False, index=True),
    Column("subject", String(320), nullable=False),
    Column("namespace", String(32), nullable=False, index=True),
    Column("eligible", Integer(), nullable=False),
    Column("hit", Integer(), nullable=False),
    Column("key_digest", String(64), nullable=False),
    Column("ttl_seconds", Integer(), nullable=True),
    Column("reason", String(300), nullable=True),
    Column("backend", String(32), nullable=False),
    Column("attributes", JSON(), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, index=True),
)


class ConversationRepository(Protocol):
    def create(self, record: ConversationRecord) -> ConversationRecord: ...

    def get(self, conversation_id: str, tenant_id: str, subject: str) -> ConversationRecord | None: ...

    def list(self, tenant_id: str, subject: str, limit: int = 50) -> list[ConversationRecord]: ...

    def add_message(self, message: ConversationMessage) -> ConversationMessage: ...

    def messages(self, conversation_id: str, tenant_id: str, subject: str) -> list[ConversationMessage]: ...

    def add_cache_event(self, event: CacheEventRecord) -> CacheEventRecord: ...

    def cache_events(self, tenant_id: str, subject: str, limit: int = 100) -> list[CacheEventRecord]: ...

    def counts(self, tenant_id: str | None = None) -> tuple[int, int]: ...

    def close(self) -> None: ...


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self._conversations: dict[str, ConversationRecord] = {}
        self._messages: dict[str, list[ConversationMessage]] = {}
        self._events: list[CacheEventRecord] = []
        self._lock = threading.RLock()

    def create(self, record: ConversationRecord) -> ConversationRecord:
        with self._lock:
            self._conversations[record.conversation_id] = record.model_copy(deep=True)
            return record.model_copy(deep=True)

    def get(self, conversation_id: str, tenant_id: str, subject: str) -> ConversationRecord | None:
        with self._lock:
            record = self._conversations.get(conversation_id)
            if record is None or record.tenant_id != tenant_id or record.subject != subject:
                return None
            return record.model_copy(deep=True)

    def list(self, tenant_id: str, subject: str, limit: int = 50) -> list[ConversationRecord]:
        with self._lock:
            values = [
                record.model_copy(deep=True)
                for record in self._conversations.values()
                if record.tenant_id == tenant_id and record.subject == subject
            ]
        return sorted(values, key=lambda item: item.updated_at, reverse=True)[: max(1, limit)]

    def add_message(self, message: ConversationMessage) -> ConversationMessage:
        with self._lock:
            self._messages.setdefault(message.conversation_id, []).append(message.model_copy(deep=True))
            record = self._conversations.get(message.conversation_id)
            if record is not None:
                record.updated_at = utc_now()
            return message.model_copy(deep=True)

    def messages(self, conversation_id: str, tenant_id: str, subject: str) -> list[ConversationMessage]:
        if self.get(conversation_id, tenant_id, subject) is None:
            return []
        with self._lock:
            return [item.model_copy(deep=True) for item in self._messages.get(conversation_id, [])]

    def add_cache_event(self, event: CacheEventRecord) -> CacheEventRecord:
        with self._lock:
            self._events.append(event.model_copy(deep=True))
        return event.model_copy(deep=True)

    def cache_events(self, tenant_id: str, subject: str, limit: int = 100) -> list[CacheEventRecord]:
        with self._lock:
            values = [
                event.model_copy(deep=True)
                for event in self._events
                if event.tenant_id == tenant_id and event.subject == subject
            ]
        return sorted(values, key=lambda item: item.created_at, reverse=True)[: max(1, limit)]

    def counts(self, tenant_id: str | None = None) -> tuple[int, int]:
        with self._lock:
            conversations = [
                value for value in self._conversations.values() if tenant_id is None or value.tenant_id == tenant_id
            ]
            ids = {value.conversation_id for value in conversations}
            messages = sum(len(self._messages.get(conversation_id, [])) for conversation_id in ids)
            return len(conversations), messages

    def close(self) -> None:
        return


class SQLConversationRepository:
    def __init__(self, engine: Engine, *, create_schema: bool = False) -> None:
        self.engine = engine
        if create_schema:
            metadata.create_all(self.engine)

    def create(self, record: ConversationRecord) -> ConversationRecord:
        with self.engine.begin() as connection:
            connection.execute(runtime_conversations.insert().values(**record.model_dump(mode="python")))
        return record

    def get(self, conversation_id: str, tenant_id: str, subject: str) -> ConversationRecord | None:
        statement = select(runtime_conversations).where(
            runtime_conversations.c.conversation_id == conversation_id,
            runtime_conversations.c.tenant_id == tenant_id,
            runtime_conversations.c.subject == subject,
        )
        with self.engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
        return ConversationRecord.model_validate(dict(row)) if row is not None else None

    def list(self, tenant_id: str, subject: str, limit: int = 50) -> list[ConversationRecord]:
        statement = (
            select(runtime_conversations)
            .where(
                runtime_conversations.c.tenant_id == tenant_id,
                runtime_conversations.c.subject == subject,
            )
            .order_by(runtime_conversations.c.updated_at.desc())
            .limit(max(1, limit))
        )
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [ConversationRecord.model_validate(dict(row)) for row in rows]

    def add_message(self, message: ConversationMessage) -> ConversationMessage:
        with self.engine.begin() as connection:
            connection.execute(runtime_messages.insert().values(**message.model_dump(mode="python")))
            connection.execute(
                runtime_conversations.update()
                .where(runtime_conversations.c.conversation_id == message.conversation_id)
                .values(updated_at=utc_now())
            )
        return message

    def messages(self, conversation_id: str, tenant_id: str, subject: str) -> list[ConversationMessage]:
        if self.get(conversation_id, tenant_id, subject) is None:
            return []
        statement = (
            select(runtime_messages)
            .where(
                runtime_messages.c.conversation_id == conversation_id,
                runtime_messages.c.tenant_id == tenant_id,
            )
            .order_by(runtime_messages.c.created_at.asc())
        )
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [ConversationMessage.model_validate(dict(row)) for row in rows]

    def add_cache_event(self, event: CacheEventRecord) -> CacheEventRecord:
        values = event.model_dump(mode="python")
        values["namespace"] = event.namespace.value
        values["eligible"] = int(event.eligible)
        values["hit"] = int(event.hit)
        with self.engine.begin() as connection:
            connection.execute(runtime_cache_events.insert().values(**values))
        return event

    def cache_events(self, tenant_id: str, subject: str, limit: int = 100) -> list[CacheEventRecord]:
        statement = (
            select(runtime_cache_events)
            .where(
                runtime_cache_events.c.tenant_id == tenant_id,
                runtime_cache_events.c.subject == subject,
            )
            .order_by(runtime_cache_events.c.created_at.desc())
            .limit(max(1, limit))
        )
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        values: list[CacheEventRecord] = []
        for row in rows:
            payload = dict(row)
            payload["eligible"] = bool(payload["eligible"])
            payload["hit"] = bool(payload["hit"])
            values.append(CacheEventRecord.model_validate(payload))
        return values

    def counts(self, tenant_id: str | None = None) -> tuple[int, int]:
        conversation_statement = select(runtime_conversations.c.conversation_id)
        message_statement = select(runtime_messages.c.message_id)
        if tenant_id is not None:
            conversation_statement = conversation_statement.where(runtime_conversations.c.tenant_id == tenant_id)
            message_statement = message_statement.where(runtime_messages.c.tenant_id == tenant_id)
        with self.engine.connect() as connection:
            conversations = len(connection.execute(conversation_statement).all())
            messages = len(connection.execute(message_statement).all())
        return conversations, messages

    def clear_tenant(self, tenant_id: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(delete(runtime_cache_events).where(runtime_cache_events.c.tenant_id == tenant_id))
            connection.execute(delete(runtime_messages).where(runtime_messages.c.tenant_id == tenant_id))
            connection.execute(delete(runtime_conversations).where(runtime_conversations.c.tenant_id == tenant_id))

    def close(self) -> None:
        self.engine.dispose()


def build_conversation_repository(settings: Settings) -> ConversationRepository:
    if settings.conversation_store_backend.casefold() == "sqlalchemy":
        engine = create_engine(settings.database_url, future=True)
        return SQLConversationRepository(engine, create_schema=settings.create_schema_on_startup)
    return InMemoryConversationRepository()


def export_records(records: Iterable[ConversationRecord]) -> list[dict]:
    return [record.model_dump(mode="json") for record in records]
