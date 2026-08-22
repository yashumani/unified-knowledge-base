from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ukb.models import Sensitivity, new_id, utc_now


def canonical_checksum(value: Any) -> str:
    """Create a stable SHA-256 checksum for JSON-compatible data."""

    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", exclude_none=True)
    else:
        payload = value
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class DomainPackStatus(str, Enum):
    draft = "draft"
    approved = "approved"
    superseded = "superseded"
    deprecated = "deprecated"


class DomainFit(str, Enum):
    in_domain = "in_domain"
    external_adjacent = "external_adjacent"
    excluded = "excluded"
    unsupported = "unsupported"
    ambiguous = "ambiguous"


class MemoryType(str, Enum):
    business_definition = "business_definition"
    business_decision = "business_decision"
    policy = "policy"
    business_event = "business_event"
    project_event = "project_event"
    investigation = "investigation"
    user_approved_preference = "user_approved_preference"
    metric_context = "metric_context"
    entity_context = "entity_context"
    external_intelligence = "external_intelligence"
    source_document = "source_document"
    meeting_record = "meeting_record"
    hypothesis = "hypothesis"
    recommendation = "recommendation"


class MemoryStatus(str, Enum):
    unverified = "unverified"
    approved = "approved"
    published = "published"
    deprecated = "deprecated"
    superseded = "superseded"
    expired = "expired"
    conflicting = "conflicting"
    rejected = "rejected"


class AuthorityLevel(str, Enum):
    authoritative = "authoritative"
    approved = "approved"
    corroborated = "corroborated"
    unverified = "unverified"
    hypothesis = "hypothesis"


class CoverageStatus(str, Enum):
    complete = "complete"
    partial = "partial"
    stale = "stale"
    unavailable = "unavailable"
    denied = "denied"


class SourceHealthStatus(str, Enum):
    healthy = "healthy"
    partial = "partial"
    stale = "stale"
    failed = "failed"
    unavailable = "unavailable"


class IndexStatus(str, Enum):
    current = "current"
    lagging = "lagging"
    unavailable = "unavailable"


class RelationshipStatus(str, Enum):
    active = "active"
    superseded = "superseded"
    deprecated = "deprecated"


class DomainConcept(BaseModel):
    concept_id: str
    name: str
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class OrganizationalDomain(BaseModel):
    domain_id: str
    name: str
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    subdomains: list[str] = Field(default_factory=list)


class BusinessEntityDefinition(BaseModel):
    entity_id: str
    name: str
    entity_type: str
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)


class EntityRelationshipDefinition(BaseModel):
    source_entity: str
    relationship_type: str
    target_entity: str
    description: str = ""


class VocabularyEntry(BaseModel):
    canonical_term: str
    concept_type: str
    concept_id: str | None = None
    domain: str | None = None
    aliases: list[str] = Field(default_factory=list)
    abbreviations: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)

    @property
    def all_terms(self) -> list[str]:
        return [
            self.canonical_term,
            *self.aliases,
            *self.abbreviations,
            *self.synonyms,
        ]


class MetricReference(BaseModel):
    metric_id: str
    name: str
    domain: str
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)


class DimensionReference(BaseModel):
    dimension_id: str
    name: str
    domain: str
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)


class BusinessProcessDefinition(BaseModel):
    process_id: str
    name: str
    description: str = ""
    domains: list[str] = Field(default_factory=list)
    related_metrics: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)


class KnowledgeSourceReference(BaseModel):
    source_id: str
    name: str
    source_type: str
    domains: list[str] = Field(default_factory=list)
    required_for_partitions: list[str] = Field(default_factory=list)
    classification: Sensitivity = Sensitivity.internal
    access_policy_id: str | None = None
    required: bool = True


class ExternalContextCategory(BaseModel):
    category_id: str
    name: str
    description: str = ""
    keywords: list[str] = Field(default_factory=list)


class DomainAdjacencyRule(BaseModel):
    rule_id: str
    external_category: str
    description: str = ""
    internal_anchor_domains: list[str] = Field(default_factory=list)
    internal_anchor_metrics: list[str] = Field(default_factory=list)
    internal_anchor_entities: list[str] = Field(default_factory=list)
    internal_anchor_terms: list[str] = Field(default_factory=list)
    allowed: bool = True


class ExcludedDomain(BaseModel):
    domain_id: str
    name: str
    reason: str
    keywords: list[str] = Field(default_factory=list)


class TenantDefaults(BaseModel):
    calendar: str = "gregorian"
    fiscal_year_start_month: int = Field(default=1, ge=1, le=12)
    currency: str = "USD"
    unit_system: str = "metric"
    geography: str = "national"
    timezone: str = "UTC"
    terminology_rules: dict[str, str] = Field(default_factory=dict)


class TenantDomainPack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    domain_pack_id: str = Field(default_factory=lambda: new_id("domain_pack"))
    tenant_id: str = Field(..., min_length=1)
    tenant_name: str = Field(..., min_length=1)
    industry: str = Field(..., min_length=1)
    subindustries: list[str] = Field(default_factory=list)
    products_and_services: list[DomainConcept] = Field(default_factory=list)
    business_capabilities: list[DomainConcept] = Field(default_factory=list)
    organizational_domains: list[OrganizationalDomain] = Field(default_factory=list)
    business_entities: list[BusinessEntityDefinition] = Field(default_factory=list)
    entity_relationships: list[EntityRelationshipDefinition] = Field(default_factory=list)
    vocabulary: list[VocabularyEntry] = Field(default_factory=list)
    metric_references: list[MetricReference] = Field(default_factory=list)
    dimension_references: list[DimensionReference] = Field(default_factory=list)
    business_processes: list[BusinessProcessDefinition] = Field(default_factory=list)
    knowledge_sources: list[KnowledgeSourceReference] = Field(default_factory=list)
    allowed_external_context_categories: list[ExternalContextCategory] = Field(
        default_factory=list
    )
    domain_adjacency_relationships: list[DomainAdjacencyRule] = Field(default_factory=list)
    excluded_domains: list[ExcludedDomain] = Field(default_factory=list)
    defaults: TenantDefaults = Field(default_factory=TenantDefaults)
    data_classification_policy_refs: list[str] = Field(default_factory=list)
    access_policy_refs: list[str] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    status: DomainPackStatus = DomainPackStatus.draft
    owner: str
    approved_by: str | None = None
    effective_from: datetime = Field(default_factory=utc_now)
    effective_to: datetime | None = None
    supersedes_domain_pack_id: str | None = None
    superseded_by: str | None = None
    checksum: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_governance(self) -> TenantDomainPack:
        if self.status == DomainPackStatus.approved and not self.approved_by:
            raise ValueError("An approved Domain Pack requires approved_by.")
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be after effective_from.")
        return self


class VocabularyResolutionRequest(BaseModel):
    term: str = Field(..., min_length=1)


class VocabularyResolution(BaseModel):
    input_term: str
    resolved: bool
    canonical_term: str | None = None
    concept_type: str | None = None
    concept_id: str | None = None
    domain: str | None = None
    matched_term: str | None = None
    domain_pack_version: int | None = None


class DomainQuestionRequest(BaseModel):
    question: str = Field(..., min_length=3)


class DomainClassificationResult(BaseModel):
    question: str
    classification: DomainFit
    domain_pack_id: str
    domain_pack_version: int
    matched_domains: list[str] = Field(default_factory=list)
    matched_metrics: list[str] = Field(default_factory=list)
    matched_entities: list[str] = Field(default_factory=list)
    matched_external_categories: list[str] = Field(default_factory=list)
    internal_anchors: list[str] = Field(default_factory=list)
    matched_exclusions: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class CanonicalEpisode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str = Field(default_factory=lambda: new_id("episode"))
    tenant_id: str
    source_type: str
    source_id: str
    source_uri: str | None = None
    title: str
    raw_content: str
    content_type: str = "text/markdown"
    source_checksum: str = ""
    idempotency_key: str | None = None
    observed_at: datetime = Field(default_factory=utc_now)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    classification: Sensitivity = Sensitivity.internal
    access_policy_id: str | None = None
    owner: str | None = None
    parent_episode_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    ingestion_timestamp: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_temporal_window(self) -> CanonicalEpisode:
        if self.effective_to and self.effective_from and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be after effective_from.")
        return self


class EpisodeIngestionRequest(BaseModel):
    tenant_id: str
    source_type: str
    source_id: str
    source_uri: str | None = None
    title: str
    raw_content: str = Field(..., min_length=1)
    content_type: str = "text/markdown"
    source_checksum: str | None = None
    idempotency_key: str | None = None
    observed_at: datetime = Field(default_factory=utc_now)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    classification: Sensitivity = Sensitivity.internal
    access_policy_id: str | None = None
    owner: str | None = None
    parent_episode_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryProvenance(BaseModel):
    episode_id: str
    source_checksum: str
    derivation_type: str = "human_reviewed"
    derived_by: str
    derivation_version: str = "1.0"
    parent_memory_ids: list[str] = Field(default_factory=list)
    source_relationships: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class GovernedMemoryObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str = Field(default_factory=lambda: new_id("memory"))
    tenant_id: str
    version: int = Field(default=1, ge=1)
    memory_type: MemoryType
    source_type: str
    source_id: str
    business_domain: str
    related_metrics: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    effective_from: datetime = Field(default_factory=utc_now)
    effective_to: datetime | None = None
    status: MemoryStatus = MemoryStatus.unverified
    classification: Sensitivity = Sensitivity.internal
    access_policy_id: str | None = None
    allowed_roles: list[str] = Field(default_factory=list)
    denied_roles: list[str] = Field(default_factory=list)
    authority_level: AuthorityLevel = AuthorityLevel.unverified
    owner: str | None = None
    approved_by: str | None = None
    supersedes: str | None = None
    superseded_by: str | None = None
    conflict_group_id: str | None = None
    content: str | dict[str, Any]
    provenance: MemoryProvenance
    checksum: str = ""
    ingestion_timestamp: datetime = Field(default_factory=utc_now)
    index_watermark: datetime | None = None
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_memory(self) -> GovernedMemoryObject:
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be after effective_from.")
        if self.status in {MemoryStatus.approved, MemoryStatus.published} and not self.approved_by:
            raise ValueError("Approved or published memory requires approved_by.")
        return self

    @property
    def content_text(self) -> str:
        if isinstance(self.content, str):
            return self.content
        return json.dumps(self.content, sort_keys=True, ensure_ascii=False)


class MemoryPromotionRequest(BaseModel):
    tenant_id: str
    memory_type: MemoryType
    source_type: str
    source_id: str
    business_domain: str
    related_metrics: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    status: MemoryStatus = MemoryStatus.unverified
    classification: Sensitivity = Sensitivity.internal
    access_policy_id: str | None = None
    allowed_roles: list[str] = Field(default_factory=list)
    denied_roles: list[str] = Field(default_factory=list)
    authority_level: AuthorityLevel = AuthorityLevel.unverified
    owner: str | None = None
    approved_by: str | None = None
    content: str | dict[str, Any]
    provenance: MemoryProvenance
    tags: list[str] = Field(default_factory=list)
    conflict_group_id: str | None = None


class MemorySupersessionRequest(BaseModel):
    memory_id: str
    replacement: MemoryPromotionRequest
    effective_at: datetime = Field(default_factory=utc_now)


class MemoryRelationship(BaseModel):
    relationship_id: str = Field(default_factory=lambda: new_id("memory_rel"))
    tenant_id: str
    source_memory_id: str
    relationship_type: str
    target_memory_id: str | None = None
    target_entity_id: str | None = None
    effective_from: datetime = Field(default_factory=utc_now)
    effective_to: datetime | None = None
    status: RelationshipStatus = RelationshipStatus.active
    classification: Sensitivity = Sensitivity.internal
    access_policy_id: str | None = None
    provenance_episode_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_target(self) -> MemoryRelationship:
        if not self.target_memory_id and not self.target_entity_id:
            raise ValueError("A memory relationship requires a memory or entity target.")
        return self


class MemoryQuery(BaseModel):
    query: str = ""
    business_domains: list[str] = Field(default_factory=list)
    related_metrics: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    memory_types: list[MemoryType] = Field(default_factory=list)
    statuses: list[MemoryStatus] = Field(default_factory=list)
    effective_at: datetime = Field(default_factory=utc_now)
    include_historical: bool = False
    limit: int = Field(default=25, ge=1, le=200)


class MemoryQueryResult(BaseModel):
    memory: list[GovernedMemoryObject] = Field(default_factory=list)
    returned_count: int = 0
    searched_partitions: list[str] = Field(default_factory=list)
    policy_exclusions: list[str] = Field(default_factory=list)
    graph_backend: str | None = None


class TimelineRequest(BaseModel):
    identifier: str
    effective_at: datetime | None = None
    limit: int = Field(default=100, ge=1, le=500)


class SourceIngestionHealth(BaseModel):
    tenant_id: str
    source_id: str
    status: SourceHealthStatus
    latest_episode_id: str | None = None
    latest_ingestion_watermark: datetime | None = None
    last_success_at: datetime | None = None
    last_error_at: datetime | None = None
    error_message: str | None = None
    incomplete_partitions: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)


class IndexWatermark(BaseModel):
    tenant_id: str
    partition: str
    status: IndexStatus = IndexStatus.current
    source_watermark: datetime | None = None
    indexed_watermark: datetime | None = None
    updated_at: datetime = Field(default_factory=utc_now)
    details: dict[str, Any] = Field(default_factory=dict)

    @property
    def lag_seconds(self) -> int | None:
        if self.source_watermark is None or self.indexed_watermark is None:
            return None
        return max(0, int((self.source_watermark - self.indexed_watermark).total_seconds()))


class ContextCoverageRequest(BaseModel):
    question: str = Field(..., min_length=3)
    requested_memory_partitions: list[str] = Field(default_factory=lambda: ["current_memory"])
    business_domains: list[str] = Field(default_factory=list)
    related_metrics: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    effective_at: datetime = Field(default_factory=utc_now)


class PartitionCoverage(BaseModel):
    partition: str
    searched: bool
    result_count: int = 0
    status: CoverageStatus = CoverageStatus.complete
    notes: list[str] = Field(default_factory=list)


class ContextCoverageReceipt(BaseModel):
    receipt_id: str = Field(default_factory=lambda: new_id("coverage"))
    tenant_id: str
    requested_memory_partitions: list[str]
    searched_memory_partitions: list[str]
    partition_coverage: list[PartitionCoverage] = Field(default_factory=list)
    domain_pack_id: str | None = None
    domain_pack_version: int | None = None
    latest_ingestion_watermark: datetime | None = None
    incomplete_or_unavailable_sources: list[str] = Field(default_factory=list)
    policy_based_exclusions: list[str] = Field(default_factory=list)
    conflicting_memory_ids: list[str] = Field(default_factory=list)
    superseded_memory_ids: list[str] = Field(default_factory=list)
    index_lag_seconds: int | None = None
    overall_coverage_status: CoverageStatus
    generated_at: datetime = Field(default_factory=utc_now)
    notes: list[str] = Field(default_factory=list)


class ObsidianFrontmatter(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    tenant_id: str
    type: MemoryType
    domain: str
    status: MemoryStatus
    classification: Sensitivity
    effective_from: datetime
    effective_to: datetime | None = None
    owner: str | None = None
    approved_by: str | None = None
    related_metrics: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    source: str
    source_type: str = "obsidian"
    access_policy_id: str | None = None
    allowed_roles: list[str] = Field(default_factory=list)
    denied_roles: list[str] = Field(default_factory=list)
    authority_level: AuthorityLevel = AuthorityLevel.unverified
    version: int = Field(default=1, ge=1)
    tags: list[str] = Field(default_factory=list)


class ObsidianValidationRequest(BaseModel):
    markdown: str = Field(..., min_length=1)


class ObsidianValidationResult(BaseModel):
    valid: bool
    authoritative: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    frontmatter: ObsidianFrontmatter | None = None
    body: str = ""
    wiki_links: list[str] = Field(default_factory=list)
    source_relationships: list[str] = Field(default_factory=list)


class ObsidianPromotionRequest(BaseModel):
    markdown: str = Field(..., min_length=1)
    idempotency_key: str | None = None


class GraphAdapterStatus(BaseModel):
    backend: str
    available: bool
    replaceable: bool = True
    canonical: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class GraphRetrievalRequest(BaseModel):
    query: str = ""
    tenant_id: str
    business_domains: list[str] = Field(default_factory=list)
    related_metrics: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    effective_at: datetime = Field(default_factory=utc_now)
    limit: int = Field(default=25, ge=1, le=200)


class GraphMemoryHit(BaseModel):
    memory_id: str
    score: float = 0.0
    reasons: list[str] = Field(default_factory=list)


class Talk2DataAuditEvent(BaseModel):
    audit_id: str = Field(default_factory=lambda: new_id("t2d_audit"))
    tenant_id: str
    actor: str
    event_type: str
    target_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class SourceHealthQuery(BaseModel):
    source_ids: list[str] = Field(default_factory=list)


class DomainPackVersionList(BaseModel):
    domain_packs: list[TenantDomainPack] = Field(default_factory=list)


class MemoryConflictSummary(BaseModel):
    conflict_group_id: str
    memory_ids: list[str]
    reason: str


class DomainPackCurrentQuery(BaseModel):
    effective_at: datetime = Field(default_factory=utc_now)


class GraphRebuildResult(BaseModel):
    episodes_indexed: int
    memories_indexed: int
    relationships_indexed: int
    backend: str


class ObsidianPromotionResult(BaseModel):
    episode: CanonicalEpisode
    memory: GovernedMemoryObject
    wiki_links: list[str]


class DomainPackWriteResult(BaseModel):
    domain_pack: TenantDomainPack
    superseded_domain_pack_id: str | None = None


class MemorySupersessionResult(BaseModel):
    superseded: GovernedMemoryObject
    replacement: GovernedMemoryObject


class EpisodeIngestionResult(BaseModel):
    episode: CanonicalEpisode
    duplicate: bool = False
    duplicate_reason: Literal["idempotency_key", "checksum", "none"] = "none"
