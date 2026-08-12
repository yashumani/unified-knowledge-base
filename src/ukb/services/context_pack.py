from __future__ import annotations

from ukb.models import ContextPack, ContextPackRequest, SourceEvidence
from ukb.services.retrieval import RetrievalService
from ukb.store import BrainStore


class ContextPackService:
    def __init__(self, store: BrainStore):
        self.store = store
        self.retrieval = RetrievalService(store)

    def build(self, request: ContextPackRequest) -> ContextPack:
        objects = self.retrieval.search(
            query=request.question,
            domains=request.domains,
            limit=8,
        )

        evidence: list[SourceEvidence] = []
        for obj in objects:
            for source_id in obj.source_ids:
                source = self.store.sources.get(source_id)
                if source is not None:
                    evidence.append(source)

        confidence = self._confidence(objects, evidence)

        return ContextPack(
            question=request.question,
            user_id=request.user_id,
            mode=request.mode,
            confidence=confidence,
            answer_guidance=self._guidance(request, objects),
            knowledge_objects=objects,
            evidence=evidence,
            caveats=self._caveats(objects),
            related_objects=self._related_objects(objects),
            recommended_followups=self._followups(request, objects),
        )

    def _confidence(self, objects: list, evidence: list) -> float:
        if not objects:
            return 0.2
        object_confidence = sum(obj.confidence for obj in objects) / len(objects)
        evidence_bonus = min(len(evidence) * 0.03, 0.15)
        return min(round(object_confidence + evidence_bonus, 2), 0.95)

    def _guidance(self, request: ContextPackRequest, objects: list) -> str:
        if not objects:
            return (
                "No approved brain objects matched this question. Answer cautiously, "
                "state that the brain is missing context, and recommend submitting "
                "or approving relevant knowledge."
            )

        if request.mode == "executive_insight":
            return (
                "Use approved definitions, business caveats, related drivers, and "
                "source evidence. Keep the answer concise and decision-oriented."
            )

        if request.mode == "metric_definition":
            return (
                "Explain the approved definition, owner, source evidence, caveats, "
                "and related metrics. Do not invent formula details."
            )

        return "Use only approved knowledge objects and cite evidence from the context pack."

    def _caveats(self, objects: list) -> list[str]:
        caveats: list[str] = []
        for obj in objects:
            raw = obj.attributes.get("raw_excerpt", "")
            lowered = raw.lower()
            if "quality review" in lowered or "reopened" in lowered:
                caveats.append(
                    "Recently resolved incidents may need time for quality review tags and reopen checks to settle."
                )
            if "excluding" in lowered or "exclude" in lowered:
                caveats.append("Confirm inclusion/exclusion rules before comparing the metric.")
        return sorted(set(caveats))

    def _related_objects(self, objects: list) -> list[str]:
        related = []
        for obj in objects:
            related.extend([relationship.target_id for relationship in obj.relationships])
        return sorted(set(related))

    def _followups(self, request: ContextPackRequest, objects: list) -> list[str]:
        if not objects:
            return ["Submit or approve source context related to this question."]

        if request.mode == "executive_insight":
            return [
                "Check related driver metrics before finalizing the narrative.",
                "Validate whether the source data is final or still preliminary.",
                "Ask the metric owner to confirm caveats before sharing the explanation.",
            ]

        return ["Review the source evidence and object owner before using this in production."]
