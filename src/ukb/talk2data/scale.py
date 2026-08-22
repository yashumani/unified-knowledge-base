from __future__ import annotations

import hashlib
import statistics
import time
from dataclasses import dataclass
from datetime import timedelta

from pydantic import BaseModel, Field

from ukb.api.security import Principal
from ukb.models import Sensitivity, utc_now
from ukb.talk2data.graph import InMemoryTemporalGraphAdapter
from ukb.talk2data.models import (
    AuthorityLevel,
    CanonicalEpisode,
    ContextCoverageRequest,
    DomainConcept,
    DomainPackStatus,
    GovernedMemoryObject,
    MemoryProvenance,
    MemoryQuery,
    MemoryStatus,
    MemoryType,
    MetricReference,
    OrganizationalDomain,
    TenantDomainPack,
    VocabularyEntry,
)
from ukb.talk2data.service import Talk2DataService
from ukb.talk2data.store import InMemoryTalk2DataStore


class ScaleProfile(BaseModel):
    name: str
    tenants: int = Field(ge=2)
    source_files: int = Field(ge=1)
    memory_objects: int = Field(ge=1)
    query_iterations: int = Field(ge=1)


class ScaleBenchmarkResult(BaseModel):
    profile: ScaleProfile
    episodes_created: int
    memories_created: int
    ingestion_seconds: float
    query_p50_ms: float
    query_p95_ms: float
    cross_tenant_leakage_count: int
    coverage_status: str
    passed: bool
    notes: list[str] = Field(default_factory=list)


PROFILES: dict[str, ScaleProfile] = {
    "unit": ScaleProfile(
        name="unit",
        tenants=2,
        source_files=10,
        memory_objects=100,
        query_iterations=6,
    ),
    "ci": ScaleProfile(
        name="ci",
        tenants=3,
        source_files=100,
        memory_objects=2_000,
        query_iterations=30,
    ),
    "full": ScaleProfile(
        name="full",
        tenants=10,
        source_files=5_000,
        memory_objects=100_000,
        query_iterations=200,
    ),
}


@dataclass(frozen=True)
class ScaleFixture:
    service: Talk2DataService
    principals: list[Principal]
    tenant_markers: dict[str, list[str]]


def run_scale_benchmark(profile: ScaleProfile) -> ScaleBenchmarkResult:
    started = time.perf_counter()
    fixture = _build_fixture(profile)
    ingestion_seconds = time.perf_counter() - started

    latencies: list[float] = []
    leakage = 0
    for iteration in range(profile.query_iterations):
        principal = fixture.principals[iteration % len(fixture.principals)]
        markers = fixture.tenant_markers[principal.tenant_id]
        marker = markers[iteration % len(markers)]
        query_started = time.perf_counter()
        result = fixture.service.query_memory(
            MemoryQuery(query=marker, limit=5),
            principal=principal,
        )
        latencies.append((time.perf_counter() - query_started) * 1000)

        own_marker_hits = [
            memory
            for memory in result.memory
            if marker in memory.content_text
        ]
        if not own_marker_hits:
            leakage += 1
        leakage += sum(
            1
            for memory in result.memory
            if memory.tenant_id != principal.tenant_id
        )

        other = fixture.principals[(iteration + 1) % len(fixture.principals)]
        foreign = fixture.service.query_memory(
            MemoryQuery(query=marker, limit=5),
            principal=other,
        )
        # A same-tenant result for the second principal is not leakage. Leakage
        # means either a record escaped its tenant filter or content containing
        # the first tenant's unique marker was returned to another tenant.
        leakage += sum(
            1
            for memory in foreign.memory
            if memory.tenant_id != other.tenant_id
            or marker in memory.content_text
        )

    first = fixture.principals[0]
    receipt = fixture.service.context_coverage(
        ContextCoverageRequest(
            question="What is network congestion?",
            requested_memory_partitions=[
                "domain_pack",
                "current_memory",
                "metric_timeline",
                "graph",
            ],
            business_domains=["network"],
            related_metrics=["network_congestion"],
        ),
        principal=first,
    )
    ordered = sorted(latencies)
    p50 = statistics.median(ordered)
    p95_index = max(0, min(len(ordered) - 1, round(len(ordered) * 0.95) - 1))
    p95 = ordered[p95_index]
    passed = leakage == 0 and receipt.overall_coverage_status.value in {
        "complete",
        "partial",
    }
    notes = [
        "This benchmark measures tenant filtering, governed retrieval and coverage "
        "over deterministic in-process stores.",
        "Every tenant marker is a unique single retrieval token. The leakage count "
        "increments only when that marker or a foreign-tenant record crosses the "
        "authenticated tenant boundary.",
        "The full profile represents 5,000 source episodes and 100,000 typed memory "
        "objects; it is intentionally workflow-dispatched rather than run on every PR.",
    ]
    return ScaleBenchmarkResult(
        profile=profile,
        episodes_created=len(fixture.service.store.episodes),
        memories_created=len(fixture.service.store.memories),
        ingestion_seconds=round(ingestion_seconds, 3),
        query_p50_ms=round(p50, 3),
        query_p95_ms=round(p95, 3),
        cross_tenant_leakage_count=leakage,
        coverage_status=receipt.overall_coverage_status.value,
        passed=passed,
        notes=notes,
    )


def _build_fixture(profile: ScaleProfile) -> ScaleFixture:
    store = InMemoryTalk2DataStore()
    graph = InMemoryTemporalGraphAdapter()
    service = Talk2DataService(store=store, graph=graph)
    principals = [
        Principal(
            subject=f"scale.admin.{index}",
            tenant_id=f"scale-tenant-{index}",
            roles=frozenset(
                {
                    "consumer",
                    "submitter",
                    "reviewer",
                    "publisher",
                    "domain_pack_admin",
                    "source_admin",
                    "index_admin",
                    "governance_admin",
                }
            ),
            clearance=Sensitivity.restricted,
            auth_method="scale-test",
        )
        for index in range(profile.tenants)
    ]
    for principal in principals:
        service.create_domain_pack(
            _scale_domain_pack(principal.tenant_id, principal.subject),
            principal=principal,
        )

    episode_ids: dict[tuple[str, int], str] = {}
    files_per_tenant = max(1, profile.source_files // profile.tenants)
    for principal in principals:
        for file_index in range(files_per_tenant):
            content = (
                f"Synthetic governed source {file_index} for {principal.tenant_id}; "
                "covers network congestion and wireless operations."
            )
            checksum = hashlib.sha256(content.encode()).hexdigest()
            episode = CanonicalEpisode(
                episode_id=f"episode_{principal.tenant_id}_{file_index}",
                tenant_id=principal.tenant_id,
                source_type="scale_fixture",
                source_id=f"source_{file_index}",
                title=f"Scale source {file_index}",
                raw_content=content,
                source_checksum=checksum,
                idempotency_key=f"scale:{principal.tenant_id}:{file_index}",
                classification=Sensitivity.internal,
                owner=principal.subject,
            )
            store.add_episode(episode)
            graph.upsert_episode(episode)
            episode_ids[(principal.tenant_id, file_index)] = episode.episode_id

    tenant_markers: dict[str, list[str]] = {
        principal.tenant_id: [] for principal in principals
    }
    now = utc_now()
    for index in range(profile.memory_objects):
        principal = principals[index % len(principals)]
        file_index = (index // len(principals)) % files_per_tenant
        episode_id = episode_ids[(principal.tenant_id, file_index)]
        episode = store.episodes[episode_id]
        marker_seed = f"{principal.tenant_id}:{index}".encode()
        marker = f"tm{hashlib.sha256(marker_seed).hexdigest()[:24]}"
        tenant_markers[principal.tenant_id].append(marker)
        memory = GovernedMemoryObject(
            memory_id=f"memory_{principal.tenant_id}_{index}",
            tenant_id=principal.tenant_id,
            memory_type=MemoryType.metric_context,
            source_type="scale_fixture",
            source_id=episode.source_id,
            business_domain="network",
            related_metrics=["network_congestion"],
            related_entities=["network_cell"],
            effective_from=now - timedelta(days=index % 365),
            status=MemoryStatus.published,
            classification=Sensitivity.internal,
            authority_level=AuthorityLevel.approved,
            owner=principal.subject,
            approved_by=principal.subject,
            content=(
                f"{marker}: synthetic network congestion context for tenant-isolation "
                "and retrieval performance validation."
            ),
            provenance=MemoryProvenance(
                episode_id=episode.episode_id,
                source_checksum=episode.source_checksum,
                derivation_type="scale_fixture",
                derived_by=principal.subject,
            ),
            checksum=hashlib.sha256(marker.encode()).hexdigest(),
            tags=["synthetic", "scale-test"],
        )
        store.add_memory(memory)
        graph.upsert_memory(memory)
    return ScaleFixture(
        service=service,
        principals=principals,
        tenant_markers=tenant_markers,
    )


def _scale_domain_pack(tenant_id: str, actor: str) -> TenantDomainPack:
    return TenantDomainPack(
        tenant_id=tenant_id,
        tenant_name=f"Synthetic Scale Tenant {tenant_id}",
        industry="telecommunications",
        products_and_services=[
            DomainConcept(
                concept_id="wireless_service",
                name="Wireless Service",
                domains=["wireless", "network"],
            )
        ],
        organizational_domains=[
            OrganizationalDomain(
                domain_id="network",
                name="Network Operations",
                aliases=["network"],
            )
        ],
        vocabulary=[
            VocabularyEntry(
                canonical_term="network congestion",
                concept_type="metric",
                concept_id="network_congestion",
                domain="network",
                aliases=["congestion"],
            )
        ],
        metric_references=[
            MetricReference(
                metric_id="network_congestion",
                name="Network Congestion",
                domain="network",
                related_entities=["network_cell"],
            )
        ],
        version=1,
        status=DomainPackStatus.approved,
        owner=actor,
        approved_by=actor,
    )
