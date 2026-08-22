from __future__ import annotations

from pydantic import BaseModel, Field

from ukb.talk2data.client import Talk2DataMemoryClient
from ukb.talk2data.models import (
    ContextCoverageReceipt,
    ContextCoverageRequest,
    CoverageStatus,
    DomainClassificationResult,
    DomainFit,
    MemoryQuery,
    MemoryStatus,
)


class Talk2DataRoutingDecision(BaseModel):
    """Structured routing decision supplied to the separate Talk2Data app."""

    question: str
    domain_classification: DomainFit
    domain_pack_id: str
    domain_pack_version: int
    matched_domains: list[str] = Field(default_factory=list)
    matched_metrics: list[str] = Field(default_factory=list)
    matched_entities: list[str] = Field(default_factory=list)
    external_categories: list[str] = Field(default_factory=list)
    internal_anchors: list[str] = Field(default_factory=list)
    coverage_status: CoverageStatus | None = None
    receipt_id: str | None = None
    searched_partitions: list[str] = Field(default_factory=list)
    memory_count: int = 0
    policy_exclusions: list[str] = Field(default_factory=list)
    may_proceed: bool
    required_qualifications: list[str] = Field(default_factory=list)


class Talk2DataDecisionOrchestrator:
    """Classify a question and gather governed memory without answering it."""

    def __init__(self, client: Talk2DataMemoryClient) -> None:
        self.client = client

    def evaluate(self, question: str) -> Talk2DataRoutingDecision:
        classification = self.client.classify_question(question)
        qualifications = self._domain_qualifications(classification)

        if classification.classification in {
            DomainFit.excluded,
            DomainFit.unsupported,
            DomainFit.ambiguous,
        }:
            return Talk2DataRoutingDecision(
                question=question,
                domain_classification=classification.classification,
                domain_pack_id=classification.domain_pack_id,
                domain_pack_version=classification.domain_pack_version,
                matched_domains=classification.matched_domains,
                matched_metrics=classification.matched_metrics,
                matched_entities=classification.matched_entities,
                external_categories=classification.matched_external_categories,
                internal_anchors=classification.internal_anchors,
                may_proceed=False,
                required_qualifications=qualifications,
            )

        query = MemoryQuery(
            query=question,
            business_domains=classification.matched_domains,
            related_metrics=classification.matched_metrics,
            related_entities=classification.matched_entities,
            statuses=[
                MemoryStatus.approved,
                MemoryStatus.published,
                MemoryStatus.conflicting,
            ],
            limit=25,
        )
        memory = self.client.query_memory_with_graph(query)
        partitions = self._requested_partitions(classification)
        receipt = self.client.get_context_coverage_receipt(
            ContextCoverageRequest(
                question=question,
                requested_memory_partitions=partitions,
                business_domains=classification.matched_domains,
                related_metrics=classification.matched_metrics,
                related_entities=classification.matched_entities,
            )
        )
        qualifications.extend(self._coverage_qualifications(receipt))
        qualifications.extend(memory.policy_exclusions)
        qualifications = list(dict.fromkeys(qualifications))

        may_proceed = receipt.overall_coverage_status not in {
            CoverageStatus.denied,
            CoverageStatus.unavailable,
        }
        return Talk2DataRoutingDecision(
            question=question,
            domain_classification=classification.classification,
            domain_pack_id=classification.domain_pack_id,
            domain_pack_version=classification.domain_pack_version,
            matched_domains=classification.matched_domains,
            matched_metrics=classification.matched_metrics,
            matched_entities=classification.matched_entities,
            external_categories=classification.matched_external_categories,
            internal_anchors=classification.internal_anchors,
            coverage_status=receipt.overall_coverage_status,
            receipt_id=receipt.receipt_id,
            searched_partitions=receipt.searched_memory_partitions,
            memory_count=memory.returned_count,
            policy_exclusions=memory.policy_exclusions,
            may_proceed=may_proceed,
            required_qualifications=qualifications,
        )

    @staticmethod
    def _requested_partitions(
        classification: DomainClassificationResult,
    ) -> list[str]:
        partitions = ["domain_pack", "current_memory", "graph"]
        if classification.matched_metrics:
            partitions.append("metric_timeline")
        if classification.matched_entities:
            partitions.append("entity_timeline")
        if classification.classification == DomainFit.external_adjacent:
            partitions.append("external_intelligence")
        return partitions

    @staticmethod
    def _domain_qualifications(
        classification: DomainClassificationResult,
    ) -> list[str]:
        if classification.classification == DomainFit.excluded:
            return [
                "The question is explicitly excluded by the tenant Domain Pack; "
                "Talk2Data must not route it to business-data analysis."
            ]
        if classification.classification == DomainFit.unsupported:
            return [
                "The tenant Domain Pack does not support this subject. Request a "
                "governance update rather than guessing."
            ]
        if classification.classification == DomainFit.ambiguous:
            return [
                "The question lacks a sufficient approved internal anchor. Ask the "
                "user to clarify the business metric, entity, or process."
            ]
        if classification.classification == DomainFit.external_adjacent:
            return [
                "External context is permitted only because the question contains an "
                "approved internal tenant anchor."
            ]
        return []

    @staticmethod
    def _coverage_qualifications(
        receipt: ContextCoverageReceipt,
    ) -> list[str]:
        values: list[str] = []
        if receipt.overall_coverage_status == CoverageStatus.partial:
            values.append(
                "Context coverage is partial; disclose unavailable sources and avoid a "
                "definitive conclusion."
            )
        elif receipt.overall_coverage_status == CoverageStatus.stale:
            values.append(
                "At least one required memory partition or index is stale; qualify all "
                "time-sensitive conclusions."
            )
        elif receipt.overall_coverage_status == CoverageStatus.unavailable:
            values.append(
                "Required context is unavailable; Talk2Data must abstain from analysis."
            )
        elif receipt.overall_coverage_status == CoverageStatus.denied:
            values.append(
                "Policy withheld required context; Talk2Data must not infer the hidden data."
            )
        if receipt.conflicting_memory_ids:
            values.append(
                "Conflicting governed memory exists; present the conflict to a reviewer "
                "rather than silently selecting one version."
            )
        if receipt.incomplete_or_unavailable_sources:
            values.append(
                "One or more required knowledge sources are incomplete or unavailable."
            )
        return values
