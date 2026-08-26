from __future__ import annotations

from datetime import timedelta

from sqlalchemy import create_engine

from ukb.config import Settings
from ukb.governed_runtime.cache import CacheCoordinator, InMemoryTTLCache
from ukb.governed_runtime.conversations import (
    InMemoryConversationRepository,
    SQLConversationRepository,
)
from ukb.governed_runtime.models import (
    CacheEventRecord,
    CacheNamespace,
    ConversationMessage,
    ConversationRecord,
    ConversationRole,
)
from ukb.models import utc_now


def settings(**overrides) -> Settings:
    return Settings(
        cache_enabled=True,
        cache_backend="memory",
        cache_fail_open=True,
        default_tenant_id="tenant-default",
        **overrides,
    )


def test_exact_cache_key_is_hashed_and_tenant_scoped() -> None:
    coordinator = CacheCoordinator(settings(), backend=InMemoryTTLCache())
    identity = {
        "question": "What is current churn?",
        "permission_scope_hash": "scope-a",
        "data_snapshot_id": "snapshot-1",
    }
    key_a, digest_a = coordinator.key(CacheNamespace.response, "tenant-a", identity)
    key_b, digest_b = coordinator.key(CacheNamespace.response, "tenant-b", identity)

    assert digest_a == digest_b
    assert key_a != key_b
    assert "tenant-a" not in key_a
    assert "What is current churn" not in key_a


def test_cache_hit_miss_and_tenant_invalidation() -> None:
    coordinator = CacheCoordinator(settings(), backend=InMemoryTTLCache())
    identity = {"question": "Define churn", "snapshot": "v1"}

    first, first_event = coordinator.get_json(
        namespace=CacheNamespace.response,
        tenant_id="tenant-a",
        subject="user-a",
        identity=identity,
    )
    assert first is None
    assert first_event.hit is False

    assert coordinator.set_json(
        namespace=CacheNamespace.response,
        tenant_id="tenant-a",
        identity=identity,
        payload={"answer": "approved definition"},
        ttl_seconds=60,
    )
    assert coordinator.set_json(
        namespace=CacheNamespace.response,
        tenant_id="tenant-b",
        identity=identity,
        payload={"answer": "tenant-b definition"},
        ttl_seconds=60,
    )

    cached, event = coordinator.get_json(
        namespace=CacheNamespace.response,
        tenant_id="tenant-a",
        subject="user-a",
        identity=identity,
    )
    assert cached == {"answer": "approved definition"}
    assert event.hit is True

    coordinator.invalidate_tenant("tenant-a")
    missing, _ = coordinator.get_json(
        namespace=CacheNamespace.response,
        tenant_id="tenant-a",
        subject="user-a",
        identity=identity,
    )
    retained, _ = coordinator.get_json(
        namespace=CacheNamespace.response,
        tenant_id="tenant-b",
        subject="user-b",
        identity=identity,
    )
    assert missing is None
    assert retained == {"answer": "tenant-b definition"}


def test_conversation_memory_repository_is_subject_and_tenant_scoped() -> None:
    repository = InMemoryConversationRepository()
    conversation = repository.create(
        ConversationRecord(tenant_id="tenant-a", subject="user-a", title="Churn review")
    )
    repository.add_message(
        ConversationMessage(
            conversation_id=conversation.conversation_id,
            tenant_id="tenant-a",
            subject="user-a",
            role=ConversationRole.user,
            content="What changed?",
        )
    )

    assert repository.get(conversation.conversation_id, "tenant-a", "user-a") is not None
    assert repository.get(conversation.conversation_id, "tenant-b", "user-a") is None
    assert repository.get(conversation.conversation_id, "tenant-a", "user-b") is None
    assert len(repository.messages(conversation.conversation_id, "tenant-a", "user-a")) == 1
    assert repository.messages(conversation.conversation_id, "tenant-b", "user-a") == []


def test_sql_conversation_repository_survives_repository_restart(tmp_path) -> None:
    database = tmp_path / "runtime.db"
    url = f"sqlite+pysqlite:///{database}"
    first = SQLConversationRepository(create_engine(url, future=True), create_schema=True)
    conversation = first.create(
        ConversationRecord(tenant_id="tenant-a", subject="user-a", title="Durable thread")
    )
    message = first.add_message(
        ConversationMessage(
            conversation_id=conversation.conversation_id,
            tenant_id="tenant-a",
            subject="user-a",
            role=ConversationRole.assistant,
            content="Persisted message",
        )
    )
    first.add_cache_event(
        CacheEventRecord(
            tenant_id="tenant-a",
            subject="user-a",
            namespace=CacheNamespace.response,
            hit=True,
            key_digest="a" * 64,
            ttl_seconds=900,
        )
    )
    first.close()

    second = SQLConversationRepository(create_engine(url, future=True), create_schema=False)
    restored = second.get(conversation.conversation_id, "tenant-a", "user-a")
    messages = second.messages(conversation.conversation_id, "tenant-a", "user-a")
    events = second.cache_events("tenant-a", "user-a")
    assert restored is not None
    assert messages[0].message_id == message.message_id
    assert events[0].hit is True
    assert second.get(conversation.conversation_id, "tenant-b", "user-a") is None
    second.close()


def test_expired_memory_cache_entry_is_not_returned(monkeypatch) -> None:
    backend = InMemoryTTLCache()
    coordinator = CacheCoordinator(settings(), backend=backend)
    identity = {"question": "stable"}
    key, _ = coordinator.key(CacheNamespace.tool, "tenant-a", identity)
    backend.set(key, '{"value": 1}', ttl_seconds=1)
    backend._values[key].expires_at = 0  # noqa: SLF001 - deterministic cache expiry test

    value, event = coordinator.get_json(
        namespace=CacheNamespace.tool,
        tenant_id="tenant-a",
        subject="user-a",
        identity=identity,
    )
    assert value is None
    assert event.hit is False


def test_cache_event_model_supports_prompt_telemetry() -> None:
    event = CacheEventRecord(
        tenant_id="tenant-a",
        subject="user-a",
        namespace=CacheNamespace.prompt,
        hit=True,
        key_digest="b" * 64,
        attributes={"cached_input_tokens": 4096, "cache_write_tokens": 0},
        created_at=utc_now() - timedelta(seconds=1),
    )
    assert event.attributes["cached_input_tokens"] == 4096
