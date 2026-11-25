from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from ukb.config import Settings
from ukb.governed_runtime.models import CacheEventRecord, CacheNamespace


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def digest_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass
class CacheValue:
    tenant_hash: str
    payload: str
    expires_at: float


class CacheBackend(Protocol):
    name: str

    def get(self, key: str) -> str | None: ...

    def set(self, key: str, payload: str, ttl_seconds: int) -> None: ...

    def delete_prefix(self, prefix: str) -> int: ...

    def close(self) -> None: ...


class InMemoryTTLCache:
    name = "memory"

    def __init__(self) -> None:
        self._values: dict[str, CacheValue] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> str | None:
        now = time.monotonic()
        with self._lock:
            value = self._values.get(key)
            if value is None:
                return None
            if value.expires_at <= now:
                self._values.pop(key, None)
                return None
            return value.payload

    def set(self, key: str, payload: str, ttl_seconds: int) -> None:
        tenant_hash = key.split(":", 3)[2] if key.count(":") >= 3 else "unknown"
        with self._lock:
            self._values[key] = CacheValue(
                tenant_hash=tenant_hash,
                payload=payload,
                expires_at=time.monotonic() + max(1, ttl_seconds),
            )

    def delete_prefix(self, prefix: str) -> int:
        with self._lock:
            keys = [key for key in self._values if key.startswith(prefix)]
            for key in keys:
                self._values.pop(key, None)
            return len(keys)

    def close(self) -> None:
        with self._lock:
            self._values.clear()


class RedisTTLCache:
    name = "redis"

    def __init__(self, url: str) -> None:
        try:
            import redis  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError("Redis caching requires the redis Python package") from exc
        self._redis = redis.Redis.from_url(url, decode_responses=True)
        self._redis.ping()

    def get(self, key: str) -> str | None:
        value = self._redis.get(key)
        return str(value) if value is not None else None

    def set(self, key: str, payload: str, ttl_seconds: int) -> None:
        self._redis.set(key, payload, ex=max(1, ttl_seconds))

    def delete_prefix(self, prefix: str) -> int:
        deleted = 0
        batch: list[str] = []
        for raw_key in self._redis.scan_iter(match=f"{prefix}*"):
            batch.append(str(raw_key))
            if len(batch) >= 250:
                deleted += int(self._redis.delete(*batch))
                batch.clear()
        if batch:
            deleted += int(self._redis.delete(*batch))
        return deleted

    def close(self) -> None:
        try:
            self._redis.close()
        except Exception:
            return


class CacheCoordinator:
    """Tenant-scoped disposable caches with fail-open behavior and telemetry."""

    def __init__(self, settings: Settings, backend: CacheBackend | None = None) -> None:
        self.settings = settings
        self.backend = backend or build_cache_backend(settings)
        self._metrics: dict[str, int] = {
            "lookups": 0,
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "errors": 0,
            "invalidations": 0,
        }
        self._lock = threading.RLock()

    @staticmethod
    def tenant_hash(tenant_id: str) -> str:
        return hashlib.sha256(tenant_id.encode("utf-8")).hexdigest()[:20]

    def key(self, namespace: CacheNamespace, tenant_id: str, identity: Mapping[str, Any]) -> tuple[str, str]:
        digest = digest_payload(identity)
        return f"ukb:{namespace.value}:{self.tenant_hash(tenant_id)}:{digest}", digest

    def get_json(
        self,
        *,
        namespace: CacheNamespace,
        tenant_id: str,
        subject: str,
        identity: Mapping[str, Any],
        eligible: bool = True,
        reason: str | None = None,
    ) -> tuple[dict[str, Any] | None, CacheEventRecord]:
        key, digest = self.key(namespace, tenant_id, identity)
        self._increment("lookups")
        if not self.settings.cache_enabled or not eligible:
            self._increment("misses")
            return None, CacheEventRecord(
                tenant_id=tenant_id,
                subject=subject,
                namespace=namespace,
                eligible=False,
                hit=False,
                key_digest=digest,
                reason=reason or "cache_not_eligible",
                backend=self.backend.name,
            )
        try:
            raw = self.backend.get(key)
        except Exception as exc:
            self._increment("errors")
            self._increment("misses")
            return None, CacheEventRecord(
                tenant_id=tenant_id,
                subject=subject,
                namespace=namespace,
                eligible=True,
                hit=False,
                key_digest=digest,
                reason=f"cache_backend_error:{type(exc).__name__}",
                backend=self.backend.name,
            )
        if raw is None:
            self._increment("misses")
            return None, CacheEventRecord(
                tenant_id=tenant_id,
                subject=subject,
                namespace=namespace,
                eligible=True,
                hit=False,
                key_digest=digest,
                reason="cache_miss",
                backend=self.backend.name,
            )
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise TypeError("cached payload is not an object")
        except (json.JSONDecodeError, TypeError):
            self._increment("errors")
            self._increment("misses")
            return None, CacheEventRecord(
                tenant_id=tenant_id,
                subject=subject,
                namespace=namespace,
                eligible=True,
                hit=False,
                key_digest=digest,
                reason="invalid_cached_payload",
                backend=self.backend.name,
            )
        self._increment("hits")
        return payload, CacheEventRecord(
            tenant_id=tenant_id,
            subject=subject,
            namespace=namespace,
            eligible=True,
            hit=True,
            key_digest=digest,
            reason="cache_hit",
            backend=self.backend.name,
        )

    def set_json(
        self,
        *,
        namespace: CacheNamespace,
        tenant_id: str,
        identity: Mapping[str, Any],
        payload: Mapping[str, Any],
        ttl_seconds: int,
    ) -> bool:
        if not self.settings.cache_enabled:
            return False
        key, _ = self.key(namespace, tenant_id, identity)
        try:
            self.backend.set(key, canonical_json(dict(payload)), ttl_seconds)
        except Exception:
            self._increment("errors")
            return False
        self._increment("writes")
        return True

    def invalidate_tenant(self, tenant_id: str, namespace: CacheNamespace | None = None) -> int:
        namespaces = [namespace] if namespace is not None else list(CacheNamespace)
        deleted = 0
        tenant_hash = self.tenant_hash(tenant_id)
        for item in namespaces:
            try:
                deleted += self.backend.delete_prefix(f"ukb:{item.value}:{tenant_hash}:")
            except Exception:
                self._increment("errors")
        self._increment("invalidations", deleted or 1)
        return deleted

    def metrics(self) -> dict[str, int]:
        with self._lock:
            return dict(self._metrics)

    def close(self) -> None:
        self.backend.close()

    def _increment(self, key: str, amount: int = 1) -> None:
        with self._lock:
            self._metrics[key] = self._metrics.get(key, 0) + amount


def build_cache_backend(settings: Settings) -> CacheBackend:
    if not settings.cache_enabled:
        return InMemoryTTLCache()
    if settings.cache_backend.casefold() == "redis":
        try:
            return RedisTTLCache(settings.redis_url)
        except Exception:
            if settings.cache_fail_open:
                return InMemoryTTLCache()
            raise
    return InMemoryTTLCache()
