from __future__ import annotations

from datetime import timedelta

from ukb.models import (
    ConfidenceFactors,
    ContextPack,
    ContextPackCitation,
    ContextPackRequest,
    EvidenceChunk,
    KnowledgeObject,
    SourceEvidence,
    utc_now,
)
from ukb.search import SearchRequest
from ukb.services.access import AccessPolicyService, PrincipalLike
from ukb.services.retrieval import RetrievalService
from ukb.storage.memory import BrainStore


class ContextPackService:
    """Compose a governed, citation-bearing context contract for AI consumers."""

    def __init__(
        self,
        store: BrainStore,
        access_policy: AccessPolicyService | None = None,
        retrieval: RetrievalService | None = None,
    ):
        self.store = store
        self.access_policy = access_policy or AccessPolicyService()
        self.retrieval = retrieval or RetrievalService(store, access_policy=self.access_policy)

    def build(
        self,
        request: ContextPackRequest,
        principal: str | PrincipalLike | None = None,
    ) -> ContextPack:
        subject: str | PrincipalLike = principal or request.user_id
        response = self.retrieval.search_response(
            SearchRequest(
                query=request.question,
                user_id=request.user_id,
                domains=request.domains,
                limit=8,
            ),
            principal=subject,
        )
        objects = [result.object for result in response.results]
        access_decision = "denied" if response.denied_count and not objects else "allowed"

        evidence: list[SourceEvidence] = []
        citations: list[ContextPackCitation] = []
        seen_sources: set[str] = set()
        seen_citations: set[tuple[str, str | None]] = set()
        object_cited: set[str] = set()

        for result in response.results:
            chunks = self._result_chunks(result.object, result.evidence_chunk)
            for chunk in chunks[:3]:
                source = self.store.sources.get(chunk.source_id)
                if source is None or not self.access_policy.can_access_sensitivity(subject, source.sensitivity):
                    continue
                if source.source_id not in seen_sources:
                    evidence.append(source)
                    seen_sources.add(source.source_id)
                key = (result.object.id, chunk.id)
                if key in seen_citations:
                    continue
                citations.append(
                    ContextPackCitation(
                        object_id=result.object.id,
                        source_id=source.source_id,
                        source_version_id=chunk.source_version_id,
                        chunk_id=chunk.id,
                        title=source.title,
                        quote=self._excerpt(chunk.content, 600),
                        locator=chunk.locator,
                    )
                )
                seen_citations.add(key)
                object_cited.add(result.object.id)

            if result.object.id not in object_cited:
                for source_id in result.object.source_ids:
                    source = self.store.sources.get(source_id)
                    if source is None or not self.access_policy.can_access_sensitivity(subject, source.sensitivity):
                        continue
                    if source.source_id not in seen_sources:
                        evidence.append(source)
                        seen_sources.add(source.source_id)
                    key = (result.object.id, None)
                    if key not in seen_citations:
                        citations.append(
                            ContextPackCitation(
                                object_id=result.object.id,
                                source_id=source.source_id,
                                source_version_id=source.current_version_id,
                                title=source.title,
                                quote=source.content_excerpt,
                                locator="source excerpt",
                            )
                        )
                        seen_citations.add(key)
                        object_cited.add(result.object.id)
                    break

        conflicts = self._conflicts(objects)
        factors = self._confidence_factors(response.results, object_cited, conflicts)
        confidence = self._overall_confidence(factors, bool(objects), access_decision)
        caveats = self._caveats(objects, response.denied_count, conflicts)
        missing_context = self._missing_context(objects, citations, access_decision)

        return ContextPack(
            question=request.question,
            user_id=request.user_id,
            mode=request.mode,
            access_decision=access_decision,
            confidence=confidence,
            confidence_factors=factors,
            retrieval_engine=response.index.backend_active,
            answer_guidance=self._guidance(request, objects, access_decision, conflicts),
            knowledge_objects=objects,
            evidence=evidence,
            citations=citations,
            caveats=caveats,
            conflicts=conflicts,
            related_objects=self._related_objects(objects, subject),
            recommended_followups=self._followups(request, objects, access_decision, conflicts),
            missing_context=missing_context,
        )

    def _result_chunks(
        self,
        obj: KnowledgeObject,
        selected: EvidenceChunk | None,
    ) -> list[EvidenceChunk]:
        chunks: list[EvidenceChunk] = []
        if selected is not None:
            chunks.append(selected)
        referenced = {reference.chunk_id for reference in obj.evidence_refs}
        for chunk in self.store.evidence_chunks.values():
            if chunk.id in referenced or chunk.source_id in obj.source_ids:
                if all(existing.id != chunk.id for existing in chunks):
                    chunks.append(chunk)
        return sorted(chunks, key=lambda item: item.ordinal)

    def _confidence_factors(self, results, cited: set[str], conflicts: list[str]) -> ConfidenceFactors:
        if not results:
            return ConfidenceFactors()
        best_score = max(result.hit.score for result in results)
        retrieval = 1.0 if best_score >= 100 else min(0.95, best_score / (best_score + 5.0))
        evidence_coverage = len(cited) / len(results)
        source_authority = sum((6 - result.object.authority_tier) / 5 for result in results) / len(results)
        now = utc_now()
        freshness_values: list[float] = []
        for result in results:
            age = now - result.object.updated_at
            freshness_values.append(1.0 if age <= timedelta(days=180) else 0.8 if age <= timedelta(days=365) else 0.6)
        return ConfidenceFactors(
            retrieval=round(retrieval, 3),
            evidence_coverage=round(evidence_coverage, 3),
            source_authority=round(source_authority, 3),
            freshness=round(sum(freshness_values) / len(freshness_values), 3),
            conflict_penalty=min(0.6, len(conflicts) * 0.2),
        )

    @staticmethod
    def _overall_confidence(
        factors: ConfidenceFactors,
        has_objects: bool,
        access_decision: str,
    ) -> float:
        if access_decision == "denied":
            return 0.0
        if not has_objects:
            return 0.15
        score = (
            factors.retrieval * 0.35
            + factors.evidence_coverage * 0.30
            + factors.source_authority * 0.20
            + factors.freshness * 0.15
            - factors.conflict_penalty
        )
        return round(max(0.0, min(0.98, score)), 2)

    def _conflicts(self, objects: list[KnowledgeObject]) -> list[str]:
        conflicts: list[str] = []
        result_ids = {obj.id for obj in objects}
        for obj in objects:
            normalized = (obj.domain.casefold(), obj.type.value.casefold(), obj.title.casefold())
            for other in self.store.knowledge_objects.values():
                if other.id == obj.id or other.status.value != "published":
                    continue
                if (other.domain.casefold(), other.type.value.casefold(), other.title.casefold()) != normalized:
                    continue
                if other.summary.strip().casefold() != obj.summary.strip().casefold():
                    conflicts.append(
                        f"Published objects {obj.id} and {other.id} share the title '{obj.title}' but have different definitions."
                    )
                    result_ids.add(other.id)
        return sorted(set(conflicts))

    @staticmethod
    def _caveats(objects: list[KnowledgeObject], denied_count: int, conflicts: list[str]) -> list[str]:
        caveats: list[str] = []
        if denied_count:
            caveats.append(f"{denied_count} matching result(s) were withheld by access policy.")
        if any(not obj.owner for obj in objects):
            caveats.append("At least one returned object has no assigned owner.")
        if conflicts:
            caveats.append("Conflicting published definitions require governance review before a definitive answer.")
        for obj in objects:
            raw = " ".join(str(value) for value in obj.attributes.values()).lower()
            if "exclude" in raw:
                caveats.append("Confirm inclusion and exclusion rules before comparing the result.")
        return sorted(set(caveats))

    @staticmethod
    def _missing_context(
        objects: list[KnowledgeObject],
        citations: list[ContextPackCitation],
        access_decision: str,
    ) -> list[str]:
        if access_decision == "denied":
            return ["Matching context exists but is above the authenticated principal's clearance."]
        missing: list[str] = []
        if not objects:
            missing.append("No approved knowledge object matched the question.")
        if objects and not citations:
            missing.append("Approved knowledge matched, but no traceable evidence chunk was available.")
        return missing

    @staticmethod
    def _guidance(
        request: ContextPackRequest,
        objects: list[KnowledgeObject],
        decision: str,
        conflicts: list[str],
    ) -> str:
        if decision == "denied":
            return "Access was denied. Do not speculate about withheld content; ask the user to request access."
        if not objects:
            return "The governed brain has insufficient approved context. Abstain and recommend ingestion or review."
        if conflicts:
            return "Present the conflicting approved definitions with citations; do not silently choose one."
        if request.mode == "executive_insight":
            return "Use only cited approved context, state caveats, and keep the explanation decision-oriented."
        if request.mode == "metric_definition":
            return "Explain the approved definition, owner, evidence, and caveats. Do not invent formula details."
        return "Use only approved objects and cite the supplied evidence excerpts."

    def _related_objects(
        self,
        objects: list[KnowledgeObject],
        principal: str | PrincipalLike,
    ) -> list[str]:
        related: list[str] = []
        for obj in objects:
            for relationship in obj.relationships:
                target = self.store.knowledge_objects.get(relationship.target_id)
                if target is not None and not self.access_policy.can_access(principal, target):
                    continue
                related.append(relationship.target_id)
        return sorted(set(related))

    @staticmethod
    def _followups(
        request: ContextPackRequest,
        objects: list[KnowledgeObject],
        decision: str,
        conflicts: list[str],
    ) -> list[str]:
        if decision == "denied":
            return ["Request the required domain access from a governance administrator."]
        if not objects:
            return ["Submit or approve authoritative context related to this question."]
        if conflicts:
            return ["Resolve the conflicting definitions with the responsible owners."]
        if request.mode == "executive_insight":
            return [
                "Check related driver metrics.",
                "Confirm source freshness with the owner.",
                "Review caveats before sharing the narrative.",
            ]
        return ["Review the cited evidence and object owner before production use."]

    @staticmethod
    def _excerpt(text: str, limit: int) -> str:
        cleaned = " ".join(text.split())
        return cleaned if len(cleaned) <= limit else cleaned[: limit - 3] + "..."
