from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from ukb.talk2data.models import (
    CanonicalEpisode,
    GovernedMemoryObject,
    GraphAdapterStatus,
    GraphMemoryHit,
    GraphRetrievalRequest,
    MemoryRelationship,
)


@runtime_checkable
class TemporalGraphAdapter(Protocol):
    """Replaceable projection boundary for Graphiti or another temporal graph backend."""

    name: str

    def upsert_episode(self, episode: CanonicalEpisode) -> None: ...

    def upsert_memory(self, memory: GovernedMemoryObject) -> None: ...

    def upsert_relationship(self, relationship: MemoryRelationship) -> None: ...

    def query(self, request: GraphRetrievalRequest) -> list[GraphMemoryHit]: ...

    def entity_timeline(
        self,
        *,
        tenant_id: str,
        entity_id: str,
        effective_at: datetime | None = None,
        limit: int = 100,
    ) -> list[str]: ...

    def metric_timeline(
        self,
        *,
        tenant_id: str,
        metric_id: str,
        effective_at: datetime | None = None,
        limit: int = 100,
    ) -> list[str]: ...

    def rebuild(
        self,
        *,
        episodes: list[CanonicalEpisode],
        memories: list[GovernedMemoryObject],
        relationships: list[MemoryRelationship],
    ) -> None: ...

    def status(self) -> GraphAdapterStatus: ...

    def close(self) -> None: ...


class InMemoryTemporalGraphAdapter:
    """Deterministic temporal graph projection used for tests and local development."""

    name = "memory"

    def __init__(self) -> None:
        self.episodes: dict[str, CanonicalEpisode] = {}
        self.memories: dict[str, GovernedMemoryObject] = {}
        self.relationships: dict[str, MemoryRelationship] = {}
        self._entity_index: dict[tuple[str, str], set[str]] = defaultdict(set)
        self._metric_index: dict[tuple[str, str], set[str]] = defaultdict(set)

    def upsert_episode(self, episode: CanonicalEpisode) -> None:
        self.episodes[episode.episode_id] = episode

    def upsert_memory(self, memory: GovernedMemoryObject) -> None:
        previous = self.memories.get(memory.memory_id)
        if previous is not None:
            self._remove_indexes(previous)
        self.memories[memory.memory_id] = memory
        for entity_id in memory.related_entities:
            self._entity_index[(memory.tenant_id, entity_id.casefold())].add(memory.memory_id)
        for metric_id in memory.related_metrics:
            self._metric_index[(memory.tenant_id, metric_id.casefold())].add(memory.memory_id)

    def upsert_relationship(self, relationship: MemoryRelationship) -> None:
        self.relationships[relationship.relationship_id] = relationship

    def query(self, request: GraphRetrievalRequest) -> list[GraphMemoryHit]:
        candidates = [
            memory for memory in self.memories.values() if memory.tenant_id == request.tenant_id
        ]
        if request.business_domains:
            allowed = {value.casefold() for value in request.business_domains}
            candidates = [memory for memory in candidates if memory.business_domain.casefold() in allowed]
        if request.related_metrics:
            wanted = {value.casefold() for value in request.related_metrics}
            candidates = [
                memory
                for memory in candidates
                if wanted.intersection(value.casefold() for value in memory.related_metrics)
            ]
        if request.related_entities:
            wanted = {value.casefold() for value in request.related_entities}
            candidates = [
                memory
                for memory in candidates
                if wanted.intersection(value.casefold() for value in memory.related_entities)
            ]
        query_terms = self._terms(request.query)
        hits: list[GraphMemoryHit] = []
        for memory in candidates:
            if not self._effective(memory, request.effective_at):
                continue
            searchable = " ".join(
                [
                    memory.memory_type.value,
                    memory.business_domain,
                    *memory.related_metrics,
                    *memory.related_entities,
                    memory.content_text,
                ]
            ).casefold()
            matched = [term for term in query_terms if term in searchable]
            if query_terms and not matched:
                continue
            relationship_count = sum(
                1
                for relationship in self.relationships.values()
                if relationship.tenant_id == request.tenant_id
                and (
                    relationship.source_memory_id == memory.memory_id
                    or relationship.target_memory_id == memory.memory_id
                )
            )
            score = float(len(matched)) + min(2.0, relationship_count * 0.2)
            reasons = ["graph_term_match"] if matched else ["graph_filter_match"]
            if relationship_count:
                reasons.append("graph_relationship_context")
            hits.append(GraphMemoryHit(memory_id=memory.memory_id, score=score, reasons=reasons))
        return sorted(hits, key=lambda item: (-item.score, item.memory_id))[: request.limit]

    def entity_timeline(
        self,
        *,
        tenant_id: str,
        entity_id: str,
        effective_at: datetime | None = None,
        limit: int = 100,
    ) -> list[str]:
        ids = self._entity_index.get((tenant_id, entity_id.casefold()), set())
        return self._timeline(ids, effective_at, limit)

    def metric_timeline(
        self,
        *,
        tenant_id: str,
        metric_id: str,
        effective_at: datetime | None = None,
        limit: int = 100,
    ) -> list[str]:
        ids = self._metric_index.get((tenant_id, metric_id.casefold()), set())
        return self._timeline(ids, effective_at, limit)

    def rebuild(
        self,
        *,
        episodes: list[CanonicalEpisode],
        memories: list[GovernedMemoryObject],
        relationships: list[MemoryRelationship],
    ) -> None:
        self.episodes.clear()
        self.memories.clear()
        self.relationships.clear()
        self._entity_index.clear()
        self._metric_index.clear()
        for episode in episodes:
            self.upsert_episode(episode)
        for memory in memories:
            self.upsert_memory(memory)
        for relationship in relationships:
            self.upsert_relationship(relationship)

    def status(self) -> GraphAdapterStatus:
        return GraphAdapterStatus(
            backend=self.name,
            available=True,
            details={
                "episodes": len(self.episodes),
                "memories": len(self.memories),
                "relationships": len(self.relationships),
            },
        )

    def close(self) -> None:
        return None

    def _timeline(
        self,
        memory_ids: set[str],
        effective_at: datetime | None,
        limit: int,
    ) -> list[str]:
        values = [self.memories[memory_id] for memory_id in memory_ids if memory_id in self.memories]
        if effective_at is not None:
            values = [memory for memory in values if memory.effective_from <= effective_at]
        values.sort(key=lambda item: (item.effective_from, item.version, item.memory_id), reverse=True)
        return [memory.memory_id for memory in values[:limit]]

    @staticmethod
    def _effective(memory: GovernedMemoryObject, at: datetime) -> bool:
        return memory.effective_from <= at and (memory.effective_to is None or at < memory.effective_to)

    @staticmethod
    def _terms(value: str) -> set[str]:
        return {term for term in value.casefold().replace("/", " ").split() if len(term) > 1}

    def _remove_indexes(self, memory: GovernedMemoryObject) -> None:
        for entity_id in memory.related_entities:
            self._entity_index[(memory.tenant_id, entity_id.casefold())].discard(memory.memory_id)
        for metric_id in memory.related_metrics:
            self._metric_index[(memory.tenant_id, metric_id.casefold())].discard(memory.memory_id)


@runtime_checkable
class GraphitiClientProtocol(Protocol):
    """Minimal client surface required by the Graphiti adapter.

    A deployment-specific client can translate these generic payloads to the
    Graphiti API or SDK version approved by the operator.
    """

    def upsert_episode(self, payload: dict[str, Any]) -> None: ...

    def upsert_entity(self, payload: dict[str, Any]) -> None: ...

    def upsert_relationship(self, payload: dict[str, Any]) -> None: ...

    def search(self, payload: dict[str, Any]) -> list[dict[str, Any]]: ...

    def timeline(self, payload: dict[str, Any]) -> list[str]: ...

    def clear_tenant(self, tenant_id: str) -> None: ...

    def close(self) -> None: ...


class GraphitiTemporalGraphAdapter:
    """Graphiti projection adapter that never becomes the canonical memory store."""

    name = "graphiti"

    def __init__(self, client: GraphitiClientProtocol | None = None) -> None:
        self.client = client
        self.last_error: str | None = None

    def upsert_episode(self, episode: CanonicalEpisode) -> None:
        client = self._client()
        client.upsert_episode(
            {
                "episode_id": episode.episode_id,
                "tenant_id": episode.tenant_id,
                "source_type": episode.source_type,
                "source_id": episode.source_id,
                "source_checksum": episode.source_checksum,
                "observed_at": episode.observed_at.isoformat(),
                "effective_from": episode.effective_from.isoformat()
                if episode.effective_from
                else None,
                "effective_to": episode.effective_to.isoformat() if episode.effective_to else None,
                "classification": episode.classification.value,
                "access_policy_id": episode.access_policy_id,
                "metadata": episode.metadata,
            }
        )

    def upsert_memory(self, memory: GovernedMemoryObject) -> None:
        client = self._client()
        client.upsert_entity(
            {
                "entity_id": memory.memory_id,
                "entity_type": memory.memory_type.value,
                "tenant_id": memory.tenant_id,
                "business_domain": memory.business_domain,
                "related_metrics": memory.related_metrics,
                "related_entities": memory.related_entities,
                "effective_from": memory.effective_from.isoformat(),
                "effective_to": memory.effective_to.isoformat() if memory.effective_to else None,
                "status": memory.status.value,
                "classification": memory.classification.value,
                "access_policy_id": memory.access_policy_id,
                "source_episode_id": memory.provenance.episode_id,
                "source_checksum": memory.provenance.source_checksum,
                "supersedes": memory.supersedes,
                "superseded_by": memory.superseded_by,
                "content": memory.content,
                "checksum": memory.checksum,
            }
        )

    def upsert_relationship(self, relationship: MemoryRelationship) -> None:
        client = self._client()
        client.upsert_relationship(
            {
                "relationship_id": relationship.relationship_id,
                "tenant_id": relationship.tenant_id,
                "source_memory_id": relationship.source_memory_id,
                "relationship_type": relationship.relationship_type,
                "target_memory_id": relationship.target_memory_id,
                "target_entity_id": relationship.target_entity_id,
                "effective_from": relationship.effective_from.isoformat(),
                "effective_to": relationship.effective_to.isoformat()
                if relationship.effective_to
                else None,
                "status": relationship.status.value,
                "classification": relationship.classification.value,
                "access_policy_id": relationship.access_policy_id,
                "provenance_episode_id": relationship.provenance_episode_id,
                "metadata": relationship.metadata,
            }
        )

    def query(self, request: GraphRetrievalRequest) -> list[GraphMemoryHit]:
        client = self._client()
        rows = client.search(request.model_dump(mode="json"))
        hits: list[GraphMemoryHit] = []
        for row in rows:
            memory_id = str(row.get("memory_id") or row.get("entity_id") or "").strip()
            if not memory_id:
                continue
            hits.append(
                GraphMemoryHit(
                    memory_id=memory_id,
                    score=float(row.get("score") or 0.0),
                    reasons=[str(value) for value in row.get("reasons", [])],
                )
            )
        return hits[: request.limit]

    def entity_timeline(
        self,
        *,
        tenant_id: str,
        entity_id: str,
        effective_at: datetime | None = None,
        limit: int = 100,
    ) -> list[str]:
        return self._client().timeline(
            {
                "tenant_id": tenant_id,
                "entity_id": entity_id,
                "effective_at": effective_at.isoformat() if effective_at else None,
                "limit": limit,
            }
        )

    def metric_timeline(
        self,
        *,
        tenant_id: str,
        metric_id: str,
        effective_at: datetime | None = None,
        limit: int = 100,
    ) -> list[str]:
        return self._client().timeline(
            {
                "tenant_id": tenant_id,
                "metric_id": metric_id,
                "effective_at": effective_at.isoformat() if effective_at else None,
                "limit": limit,
            }
        )

    def rebuild(
        self,
        *,
        episodes: list[CanonicalEpisode],
        memories: list[GovernedMemoryObject],
        relationships: list[MemoryRelationship],
    ) -> None:
        client = self._client()
        tenants = {episode.tenant_id for episode in episodes} | {
            memory.tenant_id for memory in memories
        }
        for tenant_id in tenants:
            client.clear_tenant(tenant_id)
        for episode in episodes:
            self.upsert_episode(episode)
        for memory in memories:
            self.upsert_memory(memory)
        for relationship in relationships:
            self.upsert_relationship(relationship)

    def status(self) -> GraphAdapterStatus:
        return GraphAdapterStatus(
            backend=self.name,
            available=self.client is not None and self.last_error is None,
            details={"configured": self.client is not None, "last_error": self.last_error},
        )

    def close(self) -> None:
        if self.client is not None:
            self.client.close()

    def _client(self) -> GraphitiClientProtocol:
        if self.client is None:
            raise RuntimeError(
                "Graphiti is selected but no deployment-specific Graphiti client is configured."
            )
        return self.client
