from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Iterable

from ukb.api.security import Principal
from ukb.models import utc_now
from ukb.services.access import SENSITIVITY_ORDER
from ukb.talk2data.graph import InMemoryTemporalGraphAdapter, TemporalGraphAdapter
from ukb.talk2data.models import (
    CanonicalEpisode,
    ContextCoverageReceipt,
    ContextCoverageRequest,
    CoverageStatus,
    DomainClassificationResult,
    DomainFit,
    DomainPackStatus,
    DomainPackWriteResult,
    EpisodeIngestionRequest,
    EpisodeIngestionResult,
    GovernedMemoryObject,
    GraphAdapterStatus,
    GraphRebuildResult,
    GraphRetrievalRequest,
    IndexStatus,
    IndexWatermark,
    MemoryPromotionRequest,
    MemoryProvenance,
    MemoryQuery,
    MemoryQueryResult,
    MemoryRelationship,
    MemoryStatus,
    MemorySupersessionRequest,
    MemorySupersessionResult,
    MemoryType,
    ObsidianPromotionRequest,
    ObsidianPromotionResult,
    ObsidianValidationResult,
    PartitionCoverage,
    SourceHealthStatus,
    SourceIngestionHealth,
    Talk2DataAuditEvent,
    TenantDomainPack,
    TimelineRequest,
    VocabularyResolution,
    canonical_checksum,
)
from ukb.talk2data.obsidian import ObsidianNoteValidator
from ukb.talk2data.store import InMemoryTalk2DataStore


class Talk2DataAuthorizationError(PermissionError):
    pass


class Talk2DataNotFoundError(KeyError):
    pass


class Talk2DataConflictError(RuntimeError):
    pass


class Talk2DataValidationError(ValueError):
    pass


class Talk2DataService:
    """Tenant-aware Domain Pack and governed memory application service."""

    CURRENT_STATUSES = {
        MemoryStatus.approved,
        MemoryStatus.published,
        MemoryStatus.conflicting,
        MemoryStatus.superseded,
        MemoryStatus.expired,
    }
    HISTORICAL_STATUSES = {
        MemoryStatus.approved,
        MemoryStatus.published,
        MemoryStatus.conflicting,
        MemoryStatus.superseded,
        MemoryStatus.deprecated,
        MemoryStatus.expired,
    }
    PARTITIONS = {
        "domain_pack",
        "current_memory",
        "historical_memory",
        "investigations",
        "metric_timeline",
        "entity_timeline",
        "external_intelligence",
        "graph",
    }

    def __init__(
        self,
        *,
        store: InMemoryTalk2DataStore,
        graph: TemporalGraphAdapter | None = None,
        index_lag_tolerance_seconds: int = 300,
    ) -> None:
        self.store = store
        self.graph = graph or InMemoryTemporalGraphAdapter()
        self.obsidian = ObsidianNoteValidator()
        self.index_lag_tolerance_seconds = index_lag_tolerance_seconds

    # ------------------------------------------------------------------
    # Domain Pack
    # ------------------------------------------------------------------
    def create_domain_pack(
        self,
        domain_pack: TenantDomainPack,
        *,
        principal: Principal,
    ) -> DomainPackWriteResult:
        self._require_tenant(principal, domain_pack.tenant_id)
        self._require_role(principal, {"domain_pack_admin", "governance_admin"})
        tenant_packs = self._tenant_domain_packs(principal.tenant_id)
        expected_version = max((pack.version for pack in tenant_packs), default=0) + 1
        if domain_pack.version != expected_version:
            raise Talk2DataConflictError(
                f"Domain Pack version must be {expected_version} for tenant {principal.tenant_id}."
            )
        approved_by = principal.subject if domain_pack.status == DomainPackStatus.approved else None
        checksum_payload = domain_pack.model_dump(
            mode="json",
            exclude={"checksum", "created_at", "updated_at", "superseded_by"},
        )
        now = utc_now()
        candidate = domain_pack.model_copy(
            update={
                "approved_by": approved_by,
                "checksum": canonical_checksum(checksum_payload),
                "created_at": now,
                "updated_at": now,
            }
        )
        superseded_id: str | None = None
        if candidate.status == DomainPackStatus.approved:
            current = self.current_domain_pack(principal=principal, effective_at=candidate.effective_from)
            if current is not None:
                if candidate.supersedes_domain_pack_id not in {None, current.domain_pack_id}:
                    raise Talk2DataConflictError(
                        "supersedes_domain_pack_id does not match the current approved Domain Pack."
                    )
                current.status = DomainPackStatus.superseded
                current.superseded_by = candidate.domain_pack_id
                current.effective_to = candidate.effective_from
                current.updated_at = now
                self.store.add_domain_pack(current)
                candidate.supersedes_domain_pack_id = current.domain_pack_id
                superseded_id = current.domain_pack_id
        self.store.add_domain_pack(candidate)
        self._audit(
            principal,
            "domain_pack_created",
            candidate.domain_pack_id,
            {"version": candidate.version, "status": candidate.status.value},
        )
        return DomainPackWriteResult(
            domain_pack=candidate,
            superseded_domain_pack_id=superseded_id,
        )

    def current_domain_pack(
        self,
        *,
        principal: Principal,
        effective_at: datetime | None = None,
    ) -> TenantDomainPack | None:
        at = effective_at or utc_now()
        packs = [
            pack
            for pack in self._tenant_domain_packs(principal.tenant_id)
            if pack.status in {DomainPackStatus.approved, DomainPackStatus.superseded}
            and pack.effective_from <= at
            and (pack.effective_to is None or at < pack.effective_to)
        ]
        return max(packs, key=lambda pack: (pack.version, pack.effective_from), default=None)

    def list_domain_pack_versions(self, *, principal: Principal) -> list[TenantDomainPack]:
        self._require_role(
            principal,
            {"consumer", "submitter", "reviewer", "publisher", "domain_pack_admin", "governance_admin"},
        )
        return sorted(
            self._tenant_domain_packs(principal.tenant_id),
            key=lambda pack: (pack.version, pack.effective_from),
            reverse=True,
        )

    def resolve_vocabulary(
        self,
        term: str,
        *,
        principal: Principal,
    ) -> VocabularyResolution:
        pack = self._required_current_pack(principal)
        normalized = self._normalize(term)
        for entry in pack.vocabulary:
            for candidate in entry.all_terms:
                if self._normalize(candidate) == normalized:
                    return VocabularyResolution(
                        input_term=term,
                        resolved=True,
                        canonical_term=entry.canonical_term,
                        concept_type=entry.concept_type,
                        concept_id=entry.concept_id,
                        domain=entry.domain,
                        matched_term=candidate,
                        domain_pack_version=pack.version,
                    )
        for metric in pack.metric_references:
            for candidate in [metric.metric_id, metric.name, *metric.aliases]:
                if self._normalize(candidate) == normalized:
                    return VocabularyResolution(
                        input_term=term,
                        resolved=True,
                        canonical_term=metric.name,
                        concept_type="metric",
                        concept_id=metric.metric_id,
                        domain=metric.domain,
                        matched_term=candidate,
                        domain_pack_version=pack.version,
                    )
        for entity in pack.business_entities:
            for candidate in [entity.entity_id, entity.name, *entity.aliases]:
                if self._normalize(candidate) == normalized:
                    return VocabularyResolution(
                        input_term=term,
                        resolved=True,
                        canonical_term=entity.name,
                        concept_type="entity",
                        concept_id=entity.entity_id,
                        domain=entity.domains[0] if entity.domains else None,
                        matched_term=candidate,
                        domain_pack_version=pack.version,
                    )
        return VocabularyResolution(
            input_term=term,
            resolved=False,
            domain_pack_version=pack.version,
        )

    def classify_question(
        self,
        question: str,
        *,
        principal: Principal,
    ) -> DomainClassificationResult:
        pack = self._required_current_pack(principal)
        text = self._normalize(question)

        matched_domains = self._match_domain_ids(pack, text)
        matched_metrics = self._match_metric_ids(pack, text)
        matched_entities = self._match_entity_ids(pack, text)
        product_matches = self._match_concepts(pack.products_and_services, text)
        capability_matches = self._match_concepts(pack.business_capabilities, text)
        process_matches = self._match_processes(pack, text)
        vocabulary_matches = self._match_vocabulary(pack, text)
        internal_anchors = sorted(
            {
                *matched_domains,
                *matched_metrics,
                *matched_entities,
                *product_matches,
                *capability_matches,
                *process_matches,
                *vocabulary_matches,
            }
        )

        external_categories = [
            category.category_id
            for category in pack.allowed_external_context_categories
            if self._contains_any(text, [category.name, *category.keywords])
        ]
        exclusions = [
            excluded.domain_id
            for excluded in pack.excluded_domains
            if self._contains_any(text, [excluded.name, *excluded.keywords])
        ]

        adjacency_reasons: list[str] = []
        adjacent = False
        for rule in pack.domain_adjacency_relationships:
            if not rule.allowed or rule.external_category not in external_categories:
                continue
            rule_anchors = {
                *rule.internal_anchor_domains,
                *rule.internal_anchor_metrics,
                *rule.internal_anchor_entities,
            }
            anchor_match = bool(rule_anchors.intersection(internal_anchors)) or self._contains_any(
                text, rule.internal_anchor_terms
            )
            if anchor_match:
                adjacent = True
                adjacency_reasons.append(
                    f"External category {rule.external_category} is allowed by adjacency rule {rule.rule_id} because an internal telecom anchor was present."
                )

        reasons: list[str] = []
        if adjacent:
            classification = DomainFit.external_adjacent
            reasons.extend(adjacency_reasons)
            confidence = 0.94
        elif internal_anchors:
            classification = DomainFit.in_domain
            reasons.append("The question contains recognized tenant-domain concepts.")
            confidence = min(0.97, 0.72 + len(internal_anchors) * 0.04)
        elif exclusions:
            classification = DomainFit.excluded
            reasons.append("The question matches an explicitly excluded domain without an internal anchor.")
            confidence = 0.97
        elif external_categories:
            classification = DomainFit.unsupported
            reasons.append(
                "An allowed external subject was recognized, but the question did not contain the internal business anchor required by an adjacency rule."
            )
            confidence = 0.84
        else:
            classification = DomainFit.unsupported
            reasons.append("No approved tenant-domain or adjacent-domain concept was recognized.")
            confidence = 0.78

        return DomainClassificationResult(
            question=question,
            classification=classification,
            domain_pack_id=pack.domain_pack_id,
            domain_pack_version=pack.version,
            matched_domains=matched_domains,
            matched_metrics=matched_metrics,
            matched_entities=matched_entities,
            matched_external_categories=external_categories,
            internal_anchors=internal_anchors,
            matched_exclusions=exclusions,
            reasons=reasons,
            confidence=round(confidence, 2),
        )

    # ------------------------------------------------------------------
    # Canonical episodes and governed memory
    # ------------------------------------------------------------------
    def ingest_episode(
        self,
        request: EpisodeIngestionRequest,
        *,
        principal: Principal,
    ) -> EpisodeIngestionResult:
        self._require_tenant(principal, request.tenant_id)
        self._require_role(principal, {"submitter", "reviewer", "governance_admin"})
        checksum = hashlib.sha256(request.raw_content.encode("utf-8")).hexdigest()
        if request.source_checksum and request.source_checksum != checksum:
            raise Talk2DataValidationError("The supplied source checksum does not match raw_content.")
        if request.idempotency_key:
            existing = self.store.find_episode_by_idempotency(
                principal.tenant_id,
                request.idempotency_key,
            )
            if existing is not None:
                return EpisodeIngestionResult(
                    episode=existing,
                    duplicate=True,
                    duplicate_reason="idempotency_key",
                )
        existing = self.store.find_episode_by_checksum(
            principal.tenant_id,
            request.source_id,
            checksum,
        )
        if existing is not None:
            return EpisodeIngestionResult(
                episode=existing,
                duplicate=True,
                duplicate_reason="checksum",
            )
        for parent_id in request.parent_episode_ids:
            parent = self.store.episodes.get(parent_id)
            if parent is None or parent.tenant_id != principal.tenant_id:
                raise Talk2DataValidationError(f"Parent episode is missing or inaccessible: {parent_id}")
        episode = CanonicalEpisode(
            tenant_id=principal.tenant_id,
            source_type=request.source_type,
            source_id=request.source_id,
            source_uri=request.source_uri,
            title=request.title,
            raw_content=request.raw_content,
            content_type=request.content_type,
            source_checksum=checksum,
            idempotency_key=request.idempotency_key,
            observed_at=request.observed_at,
            effective_from=request.effective_from,
            effective_to=request.effective_to,
            classification=request.classification,
            access_policy_id=request.access_policy_id,
            owner=request.owner,
            parent_episode_ids=request.parent_episode_ids,
            metadata=request.metadata,
        )
        self.store.add_episode(episode)
        self.store.upsert_source_health(
            SourceIngestionHealth(
                tenant_id=principal.tenant_id,
                source_id=episode.source_id,
                status=SourceHealthStatus.healthy,
                latest_episode_id=episode.episode_id,
                latest_ingestion_watermark=episode.ingestion_timestamp,
                last_success_at=episode.ingestion_timestamp,
            )
        )
        self._project_episode(episode, principal)
        self._audit(
            principal,
            "canonical_episode_ingested",
            episode.episode_id,
            {
                "source_id": episode.source_id,
                "source_type": episode.source_type,
                "source_checksum": episode.source_checksum,
            },
        )
        return EpisodeIngestionResult(episode=episode)

    def promote_memory(
        self,
        request: MemoryPromotionRequest,
        *,
        principal: Principal,
    ) -> GovernedMemoryObject:
        self._require_tenant(principal, request.tenant_id)
        self._require_role(principal, {"submitter", "reviewer", "publisher", "governance_admin"})
        memory = self._build_memory(request, principal=principal)
        duplicate = self.store.find_memory_duplicate(
            principal.tenant_id,
            memory.provenance.episode_id,
            memory.checksum,
        )
        if duplicate is not None:
            return duplicate
        self._mark_conflicts(memory)
        self.store.add_memory(memory)
        self._project_memory(memory, principal)
        self._audit(
            principal,
            "governed_memory_promoted",
            memory.memory_id,
            {
                "memory_type": memory.memory_type.value,
                "status": memory.status.value,
                "episode_id": memory.provenance.episode_id,
            },
        )
        return memory

    def supersede_memory(
        self,
        request: MemorySupersessionRequest,
        *,
        principal: Principal,
    ) -> MemorySupersessionResult:
        self._require_role(principal, {"reviewer", "publisher", "governance_admin"})
        current = self._memory_for_tenant(request.memory_id, principal)
        if current.status in {MemoryStatus.superseded, MemoryStatus.deprecated, MemoryStatus.rejected}:
            raise Talk2DataConflictError(f"Memory {current.memory_id} is not eligible for supersession.")
        self._require_tenant(principal, request.replacement.tenant_id)
        replacement = self._build_memory(
            request.replacement,
            principal=principal,
            version=current.version + 1,
            effective_from=request.effective_at,
            supersedes=current.memory_id,
        )
        if replacement.business_domain != current.business_domain:
            raise Talk2DataValidationError(
                "A superseding memory version must remain in the same business domain."
            )
        now = utc_now()
        current.status = MemoryStatus.superseded
        current.effective_to = request.effective_at
        current.superseded_by = replacement.memory_id
        current.index_watermark = now
        self.store.add_memory(current)
        self.store.add_memory(replacement)
        self._project_memory(current, principal)
        self._project_memory(replacement, principal)
        self._audit(
            principal,
            "governed_memory_superseded",
            current.memory_id,
            {"replacement_memory_id": replacement.memory_id},
        )
        return MemorySupersessionResult(superseded=current, replacement=replacement)

    def add_relationship(
        self,
        relationship: MemoryRelationship,
        *,
        principal: Principal,
    ) -> MemoryRelationship:
        self._require_tenant(principal, relationship.tenant_id)
        self._require_role(principal, {"reviewer", "publisher", "governance_admin"})
        source = self._memory_for_tenant(relationship.source_memory_id, principal)
        if relationship.target_memory_id:
            self._memory_for_tenant(relationship.target_memory_id, principal)
        episode = self.store.episodes.get(relationship.provenance_episode_id)
        if episode is None or episode.tenant_id != principal.tenant_id:
            raise Talk2DataValidationError("Relationship provenance episode is missing or inaccessible.")
        if SENSITIVITY_ORDER[relationship.classification] < SENSITIVITY_ORDER[source.classification]:
            raise Talk2DataValidationError(
                "A relationship cannot be classified below its source memory."
            )
        self.store.add_relationship(relationship)
        try:
            self.graph.upsert_relationship(relationship)
        except Exception as exc:
            self._record_projection_failure(principal, "graph", relationship.relationship_id, exc)
        self._audit(
            principal,
            "memory_relationship_created",
            relationship.relationship_id,
            {"source_memory_id": relationship.source_memory_id},
        )
        return relationship

    # ------------------------------------------------------------------
    # Authorized retrieval and timelines
    # ------------------------------------------------------------------
    def query_memory(
        self,
        request: MemoryQuery,
        *,
        principal: Principal,
    ) -> MemoryQueryResult:
        allowed: list[tuple[float, GovernedMemoryObject]] = []
        exclusions: set[str] = set()
        statuses = set(request.statuses)
        if not statuses:
            statuses = self.HISTORICAL_STATUSES if request.include_historical else self.CURRENT_STATUSES
        if statuses.intersection({MemoryStatus.unverified, MemoryStatus.rejected}):
            self._require_role(principal, {"reviewer", "governance_admin"})

        for memory in self.store.memories.values():
            if memory.tenant_id != principal.tenant_id:
                continue
            exclusion = self._authorization_exclusion(memory, principal)
            if exclusion:
                exclusions.add(exclusion)
                continue
            if memory.status not in statuses:
                continue
            if not request.include_historical and not self._effective(memory, request.effective_at):
                continue
            if request.include_historical and memory.effective_from > request.effective_at:
                continue
            if request.business_domains and memory.business_domain.casefold() not in {
                value.casefold() for value in request.business_domains
            }:
                continue
            if request.related_metrics and not self._intersects(
                request.related_metrics,
                memory.related_metrics,
            ):
                continue
            if request.related_entities and not self._intersects(
                request.related_entities,
                memory.related_entities,
            ):
                continue
            if request.memory_types and memory.memory_type not in set(request.memory_types):
                continue
            score = self._memory_score(memory, request.query)
            if request.query and score <= 0:
                continue
            allowed.append((score, memory))

        allowed.sort(
            key=lambda item: (
                -item[0],
                -item[1].effective_from.timestamp(),
                -item[1].version,
                item[1].memory_id,
            )
        )
        memories = [memory for _, memory in allowed[: request.limit]]
        return MemoryQueryResult(
            memory=memories,
            returned_count=len(memories),
            searched_partitions=["historical_memory" if request.include_historical else "current_memory"],
            policy_exclusions=sorted(exclusions),
        )

    def query_memory_with_graph(
        self,
        request: MemoryQuery,
        *,
        principal: Principal,
    ) -> MemoryQueryResult:
        authorized = self.query_memory(request, principal=principal)
        if not authorized.memory:
            authorized.graph_backend = self.graph.status().backend
            return authorized
        try:
            hits = self.graph.query(
                GraphRetrievalRequest(
                    query=request.query,
                    tenant_id=principal.tenant_id,
                    business_domains=request.business_domains,
                    related_metrics=request.related_metrics,
                    related_entities=request.related_entities,
                    effective_at=request.effective_at,
                    limit=request.limit,
                )
            )
        except Exception:
            authorized.graph_backend = self.graph.status().backend
            return authorized
        order = {hit.memory_id: index for index, hit in enumerate(hits)}
        authorized_ids = {memory.memory_id for memory in authorized.memory}
        graph_ids = {hit.memory_id for hit in hits}
        # Graph results can only reorder already-authorized canonical memory.
        ordered = sorted(
            authorized.memory,
            key=lambda memory: (
                order.get(memory.memory_id, len(order)),
                memory.memory_id,
            ),
        )
        authorized.memory = [memory for memory in ordered if memory.memory_id in authorized_ids]
        authorized.returned_count = len(authorized.memory)
        authorized.searched_partitions = [*authorized.searched_partitions, "graph"]
        authorized.graph_backend = self.graph.status().backend
        if graph_ids - authorized_ids:
            # Do not expose graph-only IDs; they can be stale or unauthorized.
            authorized.policy_exclusions = sorted(
                {*authorized.policy_exclusions, "graph_results_verified_against_canonical_policy"}
            )
        return authorized

    def entity_timeline(
        self,
        request: TimelineRequest,
        *,
        principal: Principal,
    ) -> MemoryQueryResult:
        return self.query_memory(
            MemoryQuery(
                related_entities=[request.identifier],
                include_historical=True,
                effective_at=request.effective_at or utc_now(),
                limit=request.limit,
            ),
            principal=principal,
        )

    def metric_timeline(
        self,
        request: TimelineRequest,
        *,
        principal: Principal,
    ) -> MemoryQueryResult:
        return self.query_memory(
            MemoryQuery(
                related_metrics=[request.identifier],
                include_historical=True,
                effective_at=request.effective_at or utc_now(),
                limit=request.limit,
            ),
            principal=principal,
        )

    def prior_investigations(
        self,
        request: MemoryQuery,
        *,
        principal: Principal,
    ) -> MemoryQueryResult:
        scoped = request.model_copy(update={"memory_types": [MemoryType.investigation]})
        return self.query_memory(scoped, principal=principal)

    # ------------------------------------------------------------------
    # Ingestion health, watermarks, coverage
    # ------------------------------------------------------------------
    def upsert_source_health(
        self,
        health: SourceIngestionHealth,
        *,
        principal: Principal,
    ) -> SourceIngestionHealth:
        self._require_tenant(principal, health.tenant_id)
        self._require_role(principal, {"governance_admin", "source_admin"})
        trusted = health.model_copy(update={"updated_at": utc_now()})
        self.store.upsert_source_health(trusted)
        self._audit(
            principal,
            "source_health_updated",
            health.source_id,
            {"status": health.status.value},
        )
        return trusted

    def list_source_health(self, *, principal: Principal) -> list[SourceIngestionHealth]:
        return sorted(
            [
                health
                for health in self.store.source_health.values()
                if health.tenant_id == principal.tenant_id
            ],
            key=lambda item: item.source_id,
        )

    def upsert_index_watermark(
        self,
        watermark: IndexWatermark,
        *,
        principal: Principal,
    ) -> IndexWatermark:
        self._require_tenant(principal, watermark.tenant_id)
        self._require_role(principal, {"governance_admin", "index_admin"})
        trusted = watermark.model_copy(update={"updated_at": utc_now()})
        self.store.upsert_index_watermark(trusted)
        self._audit(
            principal,
            "index_watermark_updated",
            watermark.partition,
            {"status": watermark.status.value, "lag_seconds": watermark.lag_seconds},
        )
        return trusted

    def list_index_watermarks(self, *, principal: Principal) -> list[IndexWatermark]:
        return sorted(
            [
                watermark
                for watermark in self.store.index_watermarks.values()
                if watermark.tenant_id == principal.tenant_id
            ],
            key=lambda item: item.partition,
        )

    def context_coverage(
        self,
        request: ContextCoverageRequest,
        *,
        principal: Principal,
    ) -> ContextCoverageReceipt:
        requested = list(dict.fromkeys(request.requested_memory_partitions))
        invalid = sorted(set(requested) - self.PARTITIONS)
        if invalid:
            raise Talk2DataValidationError(
                f"Unsupported memory partition(s): {', '.join(invalid)}"
            )
        pack = self.current_domain_pack(principal=principal, effective_at=request.effective_at)
        searched: list[str] = []
        partition_coverage: list[PartitionCoverage] = []
        policy_exclusions: set[str] = set()
        visible_memories: dict[str, GovernedMemoryObject] = {}

        for partition in requested:
            result: MemoryQueryResult | None = None
            if partition == "domain_pack":
                searched.append(partition)
                partition_coverage.append(
                    PartitionCoverage(
                        partition=partition,
                        searched=True,
                        result_count=1 if pack else 0,
                        status=CoverageStatus.complete if pack else CoverageStatus.unavailable,
                        notes=[] if pack else ["No approved effective Domain Pack is available."],
                    )
                )
                continue
            if partition == "current_memory":
                result = self.query_memory(
                    MemoryQuery(
                        query=request.question,
                        business_domains=request.business_domains,
                        related_metrics=request.related_metrics,
                        related_entities=request.related_entities,
                        effective_at=request.effective_at,
                    ),
                    principal=principal,
                )
            elif partition == "historical_memory":
                result = self.query_memory(
                    MemoryQuery(
                        query=request.question,
                        business_domains=request.business_domains,
                        related_metrics=request.related_metrics,
                        related_entities=request.related_entities,
                        effective_at=request.effective_at,
                        include_historical=True,
                    ),
                    principal=principal,
                )
            elif partition == "investigations":
                result = self.prior_investigations(
                    MemoryQuery(
                        query=request.question,
                        business_domains=request.business_domains,
                        related_metrics=request.related_metrics,
                        related_entities=request.related_entities,
                        effective_at=request.effective_at,
                    ),
                    principal=principal,
                )
            elif partition == "metric_timeline":
                memories: list[GovernedMemoryObject] = []
                exclusions: set[str] = set()
                for metric in request.related_metrics:
                    timeline = self.metric_timeline(
                        TimelineRequest(identifier=metric, effective_at=request.effective_at),
                        principal=principal,
                    )
                    memories.extend(timeline.memory)
                    exclusions.update(timeline.policy_exclusions)
                result = MemoryQueryResult(
                    memory=self._dedupe_memories(memories),
                    returned_count=len(self._dedupe_memories(memories)),
                    searched_partitions=[partition],
                    policy_exclusions=sorted(exclusions),
                )
            elif partition == "entity_timeline":
                memories = []
                exclusions = set()
                for entity in request.related_entities:
                    timeline = self.entity_timeline(
                        TimelineRequest(identifier=entity, effective_at=request.effective_at),
                        principal=principal,
                    )
                    memories.extend(timeline.memory)
                    exclusions.update(timeline.policy_exclusions)
                result = MemoryQueryResult(
                    memory=self._dedupe_memories(memories),
                    returned_count=len(self._dedupe_memories(memories)),
                    searched_partitions=[partition],
                    policy_exclusions=sorted(exclusions),
                )
            elif partition == "external_intelligence":
                result = self.query_memory(
                    MemoryQuery(
                        query=request.question,
                        business_domains=request.business_domains,
                        related_metrics=request.related_metrics,
                        related_entities=request.related_entities,
                        memory_types=[MemoryType.external_intelligence],
                        effective_at=request.effective_at,
                    ),
                    principal=principal,
                )
            elif partition == "graph":
                result = self.query_memory_with_graph(
                    MemoryQuery(
                        query=request.question,
                        business_domains=request.business_domains,
                        related_metrics=request.related_metrics,
                        related_entities=request.related_entities,
                        effective_at=request.effective_at,
                    ),
                    principal=principal,
                )

            if result is not None:
                searched.append(partition)
                for memory in result.memory:
                    visible_memories[memory.memory_id] = memory
                policy_exclusions.update(result.policy_exclusions)
                partition_coverage.append(
                    PartitionCoverage(
                        partition=partition,
                        searched=True,
                        result_count=result.returned_count,
                        status=CoverageStatus.complete,
                    )
                )

        source_health = self.list_source_health(principal=principal)
        health_by_source = {health.source_id: health for health in source_health}
        required_source_ids: set[str] = set()
        if pack is not None:
            for source in pack.knowledge_sources:
                if source.required and set(source.required_for_partitions).intersection(requested):
                    required_source_ids.add(source.source_id)
        unavailable_sources: list[str] = []
        latest_ingestion: datetime | None = None
        stale_source = False
        for source_id in sorted(required_source_ids):
            health = health_by_source.get(source_id)
            if health is None:
                unavailable_sources.append(source_id)
                continue
            if health.latest_ingestion_watermark is not None:
                latest_ingestion = max(
                    latest_ingestion or health.latest_ingestion_watermark,
                    health.latest_ingestion_watermark,
                )
            if health.status in {
                SourceHealthStatus.partial,
                SourceHealthStatus.failed,
                SourceHealthStatus.unavailable,
            }:
                unavailable_sources.append(source_id)
            if health.status == SourceHealthStatus.stale:
                stale_source = True

        watermarks = self.list_index_watermarks(principal=principal)
        lags: list[int] = []
        for watermark in watermarks:
            lag = watermark.lag_seconds
            if lag is not None:
                lags.append(lag)
        index_lag = max(lags) if lags else None
        unavailable_index = any(watermark.status == IndexStatus.unavailable for watermark in watermarks)
        lagging_index = any(watermark.status == IndexStatus.lagging for watermark in watermarks) or (
            index_lag is not None and index_lag > self.index_lag_tolerance_seconds
        )

        conflicts = sorted(
            memory.memory_id
            for memory in visible_memories.values()
            if memory.status == MemoryStatus.conflicting or memory.conflict_group_id
        )
        superseded = sorted(
            memory.memory_id
            for memory in visible_memories.values()
            if memory.status == MemoryStatus.superseded or memory.superseded_by
        )

        if pack is None or not searched:
            overall = CoverageStatus.unavailable
        elif policy_exclusions and not visible_memories and any(
            partition != "domain_pack" for partition in requested
        ):
            overall = CoverageStatus.denied
        elif unavailable_sources or unavailable_index:
            overall = CoverageStatus.partial if searched else CoverageStatus.unavailable
        elif stale_source or lagging_index:
            overall = CoverageStatus.stale
        elif (
            conflicts
            or set(requested) - set(searched)
            or policy_exclusions
            or (
                any(partition != "domain_pack" for partition in requested)
                and not visible_memories
            )
        ):
            overall = CoverageStatus.partial
        else:
            overall = CoverageStatus.complete

        notes: list[str] = []
        if pack is not None:
            classification = self.classify_question(request.question, principal=principal)
            notes.append(f"Domain classification: {classification.classification.value}.")
        if not visible_memories and any(partition != "domain_pack" for partition in requested):
            notes.append("No authorized governed memory matched the requested business context.")
        if unavailable_sources:
            notes.append("One or more required knowledge sources are incomplete or unavailable.")
        if conflicts:
            notes.append("Conflicting governed memory must be resolved before a definitive answer.")

        receipt = ContextCoverageReceipt(
            tenant_id=principal.tenant_id,
            requested_memory_partitions=requested,
            searched_memory_partitions=searched,
            partition_coverage=partition_coverage,
            domain_pack_id=pack.domain_pack_id if pack else None,
            domain_pack_version=pack.version if pack else None,
            latest_ingestion_watermark=latest_ingestion,
            incomplete_or_unavailable_sources=unavailable_sources,
            policy_based_exclusions=sorted(policy_exclusions),
            conflicting_memory_ids=conflicts,
            superseded_memory_ids=superseded,
            index_lag_seconds=index_lag,
            overall_coverage_status=overall,
            notes=notes,
        )
        self._audit(
            principal,
            "context_coverage_receipt_created",
            receipt.receipt_id,
            {
                "coverage_status": receipt.overall_coverage_status.value,
                "requested_partitions": requested,
                "searched_partitions": searched,
            },
        )
        return receipt

    # ------------------------------------------------------------------
    # Obsidian and graph operations
    # ------------------------------------------------------------------
    def validate_obsidian(self, markdown: str) -> ObsidianValidationResult:
        return self.obsidian.validate(markdown)

    def promote_obsidian(
        self,
        request: ObsidianPromotionRequest,
        *,
        principal: Principal,
    ) -> ObsidianPromotionResult:
        parsed = self.obsidian.parse_authoritative(request.markdown)
        frontmatter = parsed.frontmatter
        self._require_tenant(principal, frontmatter.tenant_id)
        self._require_role(principal, {"reviewer", "publisher", "governance_admin"})
        episode_result = self.ingest_episode(
            EpisodeIngestionRequest(
                tenant_id=principal.tenant_id,
                source_type="obsidian",
                source_id=frontmatter.source,
                source_uri=frontmatter.source,
                title=frontmatter.id,
                raw_content=request.markdown,
                content_type="text/markdown",
                idempotency_key=request.idempotency_key
                or f"obsidian:{frontmatter.id}:v{frontmatter.version}",
                effective_from=frontmatter.effective_from,
                effective_to=frontmatter.effective_to,
                classification=frontmatter.classification,
                access_policy_id=frontmatter.access_policy_id,
                owner=frontmatter.owner,
                metadata={
                    "obsidian_note_id": frontmatter.id,
                    "wiki_links": parsed.wiki_links,
                    "frontmatter_version": frontmatter.version,
                },
            ),
            principal=principal,
        )
        memory = self.promote_memory(
            MemoryPromotionRequest(
                tenant_id=principal.tenant_id,
                memory_type=frontmatter.type,
                source_type=frontmatter.source_type,
                source_id=frontmatter.source,
                business_domain=frontmatter.domain,
                related_metrics=frontmatter.related_metrics,
                related_entities=frontmatter.related_entities,
                effective_from=frontmatter.effective_from,
                effective_to=frontmatter.effective_to,
                status=frontmatter.status,
                classification=frontmatter.classification,
                access_policy_id=frontmatter.access_policy_id,
                allowed_roles=frontmatter.allowed_roles,
                denied_roles=frontmatter.denied_roles,
                authority_level=frontmatter.authority_level,
                owner=frontmatter.owner,
                approved_by=principal.subject,
                content=parsed.body,
                provenance=MemoryProvenance(
                    episode_id=episode_result.episode.episode_id,
                    source_checksum=episode_result.episode.source_checksum,
                    derivation_type="obsidian_governed_promotion",
                    derived_by=principal.subject,
                    derivation_version=str(frontmatter.version),
                    source_relationships=parsed.source_relationships,
                ),
                tags=frontmatter.tags,
            ),
            principal=principal,
        )
        for link in parsed.wiki_links:
            relationship = MemoryRelationship(
                tenant_id=principal.tenant_id,
                source_memory_id=memory.memory_id,
                relationship_type="wiki_link",
                target_entity_id=link,
                effective_from=memory.effective_from,
                effective_to=memory.effective_to,
                classification=memory.classification,
                access_policy_id=memory.access_policy_id,
                provenance_episode_id=episode_result.episode.episode_id,
                metadata={"obsidian_wiki_link": link},
            )
            self.store.add_relationship(relationship)
            try:
                self.graph.upsert_relationship(relationship)
            except Exception as exc:
                self._record_projection_failure(principal, "graph", relationship.relationship_id, exc)
        return ObsidianPromotionResult(
            episode=episode_result.episode,
            memory=memory,
            wiki_links=parsed.wiki_links,
        )

    def graph_status(self) -> GraphAdapterStatus:
        return self.graph.status()

    def rebuild_graph(self, *, principal: Principal) -> GraphRebuildResult:
        self._require_role(principal, {"governance_admin", "index_admin"})
        episodes = [
            episode for episode in self.store.episodes.values() if episode.tenant_id == principal.tenant_id
        ]
        memories = [
            memory for memory in self.store.memories.values() if memory.tenant_id == principal.tenant_id
        ]
        relationships = [
            relationship
            for relationship in self.store.relationships.values()
            if relationship.tenant_id == principal.tenant_id
        ]
        self.graph.rebuild(
            episodes=episodes,
            memories=memories,
            relationships=relationships,
        )
        watermark_time = max(
            [memory.ingestion_timestamp for memory in memories]
            + [episode.ingestion_timestamp for episode in episodes],
            default=utc_now(),
        )
        self.store.upsert_index_watermark(
            IndexWatermark(
                tenant_id=principal.tenant_id,
                partition="graph",
                status=IndexStatus.current,
                source_watermark=watermark_time,
                indexed_watermark=watermark_time,
                details={"backend": self.graph.status().backend},
            )
        )
        self._audit(
            principal,
            "graph_rebuilt",
            None,
            {
                "episodes": len(episodes),
                "memories": len(memories),
                "relationships": len(relationships),
            },
        )
        return GraphRebuildResult(
            episodes_indexed=len(episodes),
            memories_indexed=len(memories),
            relationships_indexed=len(relationships),
            backend=self.graph.status().backend,
        )

    def list_audit_events(self, *, principal: Principal) -> list[Talk2DataAuditEvent]:
        self._require_role(principal, {"governance_admin", "auditor"})
        return sorted(
            [
                event
                for event in self.store.audit_events
                if event.tenant_id == principal.tenant_id
            ],
            key=lambda event: (event.created_at, event.audit_id),
            reverse=True,
        )

    def close(self) -> None:
        self.graph.close()
        self.store.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_memory(
        self,
        request: MemoryPromotionRequest,
        *,
        principal: Principal,
        version: int = 1,
        effective_from: datetime | None = None,
        supersedes: str | None = None,
    ) -> GovernedMemoryObject:
        episode = self.store.episodes.get(request.provenance.episode_id)
        if episode is None or episode.tenant_id != principal.tenant_id:
            raise Talk2DataValidationError("The provenance episode is missing or inaccessible.")
        if request.provenance.source_checksum != episode.source_checksum:
            raise Talk2DataValidationError(
                "The memory provenance checksum does not match the canonical episode."
            )
        if request.source_id != episode.source_id:
            raise Talk2DataValidationError("Memory source_id must match the canonical episode source_id.")
        if SENSITIVITY_ORDER[request.classification] < SENSITIVITY_ORDER[episode.classification]:
            raise Talk2DataValidationError(
                "Derived memory cannot be classified below its canonical source episode."
            )
        authoritative = request.status in {MemoryStatus.approved, MemoryStatus.published}
        if authoritative:
            self._require_role(principal, {"reviewer", "publisher", "governance_admin"})
        if request.status == MemoryStatus.published:
            self._require_role(principal, {"publisher", "governance_admin"})
        trusted_provenance = request.provenance.model_copy(update={"derived_by": principal.subject})
        checksum = canonical_checksum(
            {
                "tenant_id": principal.tenant_id,
                "memory_type": request.memory_type.value,
                "source_type": request.source_type,
                "source_id": request.source_id,
                "business_domain": request.business_domain,
                "related_metrics": sorted(request.related_metrics),
                "related_entities": sorted(request.related_entities),
                "effective_from": (effective_from or request.effective_from or episode.effective_from or episode.observed_at).isoformat(),
                "effective_to": request.effective_to.isoformat() if request.effective_to else None,
                "classification": request.classification.value,
                "content": request.content,
                "provenance": trusted_provenance.model_dump(mode="json"),
            }
        )
        return GovernedMemoryObject(
            tenant_id=principal.tenant_id,
            version=version,
            memory_type=request.memory_type,
            source_type=request.source_type,
            source_id=request.source_id,
            business_domain=request.business_domain,
            related_metrics=request.related_metrics,
            related_entities=request.related_entities,
            effective_from=effective_from
            or request.effective_from
            or episode.effective_from
            or episode.observed_at,
            effective_to=request.effective_to,
            status=request.status,
            classification=request.classification,
            access_policy_id=request.access_policy_id or episode.access_policy_id,
            allowed_roles=[role.casefold() for role in request.allowed_roles],
            denied_roles=[role.casefold() for role in request.denied_roles],
            authority_level=request.authority_level,
            owner=request.owner or episode.owner,
            approved_by=principal.subject if authoritative else None,
            supersedes=supersedes,
            conflict_group_id=request.conflict_group_id,
            content=request.content,
            provenance=trusted_provenance,
            checksum=checksum,
            tags=request.tags,
        )

    def _mark_conflicts(self, memory: GovernedMemoryObject) -> None:
        if memory.status not in self.CURRENT_STATUSES:
            return
        for other in self.store.memories.values():
            if other.tenant_id != memory.tenant_id or other.memory_id == memory.memory_id:
                continue
            if other.status not in self.CURRENT_STATUSES:
                continue
            if other.memory_type != memory.memory_type:
                continue
            if other.business_domain.casefold() != memory.business_domain.casefold():
                continue
            if not self._temporal_overlap(other, memory):
                continue
            same_subject = (
                self._intersects(other.related_metrics, memory.related_metrics)
                or self._intersects(other.related_entities, memory.related_entities)
                or (not other.related_metrics and not other.related_entities)
            )
            if not same_subject or other.checksum == memory.checksum:
                continue
            seed = "|".join(sorted([other.memory_id, memory.memory_id]))
            conflict_group = other.conflict_group_id or f"conflict_{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12]}"
            other.conflict_group_id = conflict_group
            other.status = MemoryStatus.conflicting
            memory.conflict_group_id = conflict_group
            memory.status = MemoryStatus.conflicting
            self.store.add_memory(other)

    @staticmethod
    def _temporal_overlap(left: GovernedMemoryObject, right: GovernedMemoryObject) -> bool:
        left_end = left.effective_to or datetime.max.replace(tzinfo=left.effective_from.tzinfo)
        right_end = right.effective_to or datetime.max.replace(tzinfo=right.effective_from.tzinfo)
        return left.effective_from < right_end and right.effective_from < left_end

    def _project_episode(self, episode: CanonicalEpisode, principal: Principal) -> None:
        try:
            self.graph.upsert_episode(episode)
            self._record_projection_watermark(principal, "graph", episode.ingestion_timestamp)
        except Exception as exc:
            self._record_projection_failure(principal, "graph", episode.episode_id, exc)

    def _project_memory(self, memory: GovernedMemoryObject, principal: Principal) -> None:
        try:
            self.graph.upsert_memory(memory)
            memory.index_watermark = utc_now()
            self.store.add_memory(memory)
            self._record_projection_watermark(principal, "graph", memory.ingestion_timestamp)
        except Exception as exc:
            self._record_projection_failure(principal, "graph", memory.memory_id, exc)

    def _record_projection_watermark(
        self,
        principal: Principal,
        partition: str,
        source_watermark: datetime,
    ) -> None:
        now = utc_now()
        self.store.upsert_index_watermark(
            IndexWatermark(
                tenant_id=principal.tenant_id,
                partition=partition,
                status=IndexStatus.current,
                source_watermark=source_watermark,
                indexed_watermark=now,
                details={"backend": self.graph.status().backend},
            )
        )

    def _record_projection_failure(
        self,
        principal: Principal,
        partition: str,
        target_id: str,
        exc: Exception,
    ) -> None:
        self.store.upsert_index_watermark(
            IndexWatermark(
                tenant_id=principal.tenant_id,
                partition=partition,
                status=IndexStatus.unavailable,
                source_watermark=utc_now(),
                indexed_watermark=None,
                details={"error": str(exc), "target_id": target_id},
            )
        )
        self._audit(
            principal,
            "derived_projection_failed",
            target_id,
            {"partition": partition, "error": str(exc)},
        )

    def _authorization_exclusion(
        self,
        memory: GovernedMemoryObject,
        principal: Principal,
    ) -> str | None:
        if memory.tenant_id != principal.tenant_id:
            return "tenant_policy"
        if SENSITIVITY_ORDER[memory.classification] > SENSITIVITY_ORDER[principal.clearance]:
            return "classification_policy"
        roles = {role.casefold() for role in principal.roles}
        if roles.intersection(role.casefold() for role in memory.denied_roles):
            return "role_policy"
        allowed_roles = {role.casefold() for role in memory.allowed_roles}
        if allowed_roles and not roles.intersection(allowed_roles):
            return "role_policy"
        return None

    def _memory_for_tenant(
        self,
        memory_id: str,
        principal: Principal,
    ) -> GovernedMemoryObject:
        memory = self.store.memories.get(memory_id)
        if memory is None or memory.tenant_id != principal.tenant_id:
            raise Talk2DataNotFoundError(f"Memory not found: {memory_id}")
        if self._authorization_exclusion(memory, principal):
            raise Talk2DataNotFoundError(f"Memory not found: {memory_id}")
        return memory

    def _required_current_pack(self, principal: Principal) -> TenantDomainPack:
        pack = self.current_domain_pack(principal=principal)
        if pack is None:
            raise Talk2DataNotFoundError(
                f"No approved current Domain Pack is available for tenant {principal.tenant_id}."
            )
        return pack

    def _tenant_domain_packs(self, tenant_id: str) -> list[TenantDomainPack]:
        return [pack for pack in self.store.domain_packs.values() if pack.tenant_id == tenant_id]

    def _require_tenant(self, principal: Principal, tenant_id: str) -> None:
        if tenant_id != principal.tenant_id:
            raise Talk2DataAuthorizationError("The authenticated principal cannot act for another tenant.")

    @staticmethod
    def _require_role(principal: Principal, allowed: set[str]) -> None:
        allowed_normalized = {role.casefold() for role in allowed}
        if not principal.roles.intersection(allowed_normalized):
            raise Talk2DataAuthorizationError(
                f"This action requires one of these roles: {', '.join(sorted(allowed))}."
            )

    def _audit(
        self,
        principal: Principal,
        event_type: str,
        target_id: str | None,
        details: dict,
    ) -> None:
        self.store.add_audit_event(
            Talk2DataAuditEvent(
                tenant_id=principal.tenant_id,
                actor=principal.subject,
                event_type=event_type,
                target_id=target_id,
                details=details,
            )
        )

    @staticmethod
    def _effective(memory: GovernedMemoryObject, at: datetime) -> bool:
        return memory.effective_from <= at and (memory.effective_to is None or at < memory.effective_to)

    @classmethod
    def _memory_score(cls, memory: GovernedMemoryObject, query: str) -> float:
        if not query.strip():
            return 1.0
        text = cls._normalize(
            " ".join(
                [
                    memory.memory_type.value,
                    memory.business_domain,
                    *memory.related_metrics,
                    *memory.related_entities,
                    *memory.tags,
                    memory.content_text,
                ]
            )
        )
        terms = [term for term in cls._normalize(query).split() if len(term) > 1]
        matched = sum(1 for term in terms if term in text)
        if not matched:
            return 0.0
        phrase_bonus = 2.0 if cls._normalize(query) in text else 0.0
        authority_bonus = {
            "authoritative": 1.0,
            "approved": 0.8,
            "corroborated": 0.5,
            "unverified": 0.1,
            "hypothesis": 0.0,
        }[memory.authority_level.value]
        return matched + phrase_bonus + authority_bonus

    @staticmethod
    def _intersects(left: Iterable[str], right: Iterable[str]) -> bool:
        return bool({value.casefold() for value in left}.intersection(value.casefold() for value in right))

    @staticmethod
    def _dedupe_memories(memories: list[GovernedMemoryObject]) -> list[GovernedMemoryObject]:
        unique: dict[str, GovernedMemoryObject] = {}
        for memory in memories:
            unique[memory.memory_id] = memory
        return sorted(
            unique.values(),
            key=lambda memory: (memory.effective_from, memory.version, memory.memory_id),
            reverse=True,
        )

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))

    @classmethod
    def _contains_any(cls, text: str, candidates: Iterable[str]) -> bool:
        return any(cls._normalize(candidate) in text for candidate in candidates if cls._normalize(candidate))

    @classmethod
    def _match_domain_ids(cls, pack: TenantDomainPack, text: str) -> list[str]:
        return sorted(
            domain.domain_id
            for domain in pack.organizational_domains
            if cls._contains_any(text, [domain.domain_id, domain.name, *domain.aliases, *domain.subdomains])
        )

    @classmethod
    def _match_metric_ids(cls, pack: TenantDomainPack, text: str) -> list[str]:
        return sorted(
            metric.metric_id
            for metric in pack.metric_references
            if cls._contains_any(text, [metric.metric_id, metric.name, *metric.aliases])
        )

    @classmethod
    def _match_entity_ids(cls, pack: TenantDomainPack, text: str) -> list[str]:
        return sorted(
            entity.entity_id
            for entity in pack.business_entities
            if cls._contains_any(text, [entity.entity_id, entity.name, *entity.aliases])
        )

    @classmethod
    def _match_concepts(cls, concepts, text: str) -> list[str]:
        return sorted(
            concept.concept_id
            for concept in concepts
            if cls._contains_any(text, [concept.concept_id, concept.name, *concept.aliases])
        )

    @classmethod
    def _match_processes(cls, pack: TenantDomainPack, text: str) -> list[str]:
        return sorted(
            process.process_id
            for process in pack.business_processes
            if cls._contains_any(text, [process.process_id, process.name, *process.aliases])
        )

    @classmethod
    def _match_vocabulary(cls, pack: TenantDomainPack, text: str) -> list[str]:
        values: set[str] = set()
        for entry in pack.vocabulary:
            if entry.concept_type.casefold() == "external_context":
                continue
            if cls._contains_any(text, entry.all_terms):
                values.add(entry.concept_id or entry.canonical_term)
        return sorted(values)
