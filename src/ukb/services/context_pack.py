from __future__ import annotations

from ukb.models import ContextPack, ContextPackRequest, SourceEvidence
from ukb.services.access import SENSITIVITY_ORDER, AccessPolicyService
from ukb.services.retrieval import RetrievalService
from ukb.store import BrainStore


class ContextPackService:
    def __init__(self, store: BrainStore, access_policy: AccessPolicyService | None = None):
        self.store = store
        self.access_policy = access_policy or AccessPolicyService()
        self.retrieval = RetrievalService(store, access_policy=self.access_policy)

    def build(self, request: ContextPackRequest, principal: str | None = None) -> ContextPack:
        """Compose a context pack for an authenticated principal.

        Clearance is resolved from ``principal`` (the identity the transport
        authenticated), never from ``request.user_id``. The request body is
        client-asserted, so honoring it here would let any caller pick their own
        clearance. ``user_id`` remains an attribution label for audit only.
        """

        subject = principal or request.user_id
        decision = self.retrieval.search(
            query=request.question,
            domains=request.domains,
            limit=8,
            user_id=subject,
        )
        objects = decision.allowed_objects

        clearance = decision.clearance
        evidence: list[SourceEvidence] = []
        withheld_evidence = 0
        for obj in objects:
            for source_id in obj.source_ids:
                source = self.store.sources.get(source_id)
                if source is None:
                    continue
                # Evidence carries its own sensitivity and can outrank the
                # object it supports, so it is checked independently.
                if SENSITIVITY_ORDER[source.sensitivity] > SENSITIVITY_ORDER[clearance]:
                    withheld_evidence += 1
                    continue
                evidence.append(source)

        confidence = self._confidence(objects, evidence)
        caveats = self._caveats(objects)
        missing_context: list[str] = []

        if decision.partially_redacted:
            caveats.append(
                f"{decision.denied_count} matching knowledge object(s) were withheld by the "
                f"access policy for clearance '{clearance.value}'. This context pack is incomplete."
            )
        if withheld_evidence:
            caveats.append(
                f"{withheld_evidence} source evidence record(s) were withheld by the access policy."
            )
        if decision.decision == "denied":
            missing_context.append(
                "Every matching knowledge object is above your access clearance. "
                "Request elevated access instead of inferring the withheld content."
            )

        return ContextPack(
            question=request.question,
            user_id=request.user_id,
            mode=request.mode,
            access_decision=decision.decision,
            confidence=confidence,
            answer_guidance=self._guidance(request, objects, decision.decision),
            knowledge_objects=objects,
            evidence=evidence,
            caveats=sorted(set(caveats)),
            related_objects=self._related_objects(objects, subject),
            recommended_followups=self._followups(request, objects, decision.decision),
            missing_context=missing_context,
        )

    def _confidence(self, objects: list, evidence: list) -> float:
        if not objects:
            return 0.2
        object_confidence = sum(obj.confidence for obj in objects) / len(objects)
        evidence_bonus = min(len(evidence) * 0.03, 0.15)
        return min(round(object_confidence + evidence_bonus, 2), 0.95)

    def _guidance(self, request: ContextPackRequest, objects: list, decision: str) -> str:
        if decision == "denied":
            return (
                "Access denied by policy. Matching context exists but is above this "
                "user's clearance. Do not speculate about the withheld content; tell "
                "the user to request access."
            )

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
        return caveats

    def _related_objects(self, objects: list, user_id: str) -> list[str]:
        """List related object IDs, minus any the caller may not see.

        A bare ID still discloses that a restricted object exists, so targets
        that resolve to blocked objects are dropped. Targets with no stored
        object are labels, not identifiers, and stay.
        """

        related = []
        for obj in objects:
            for relationship in obj.relationships:
                target = self.store.knowledge_objects.get(relationship.target_id)
                if target is not None and not self.access_policy.can_access(user_id, target):
                    continue
                related.append(relationship.target_id)
        return sorted(set(related))

    def _followups(self, request: ContextPackRequest, objects: list, decision: str) -> list[str]:
        if decision == "denied":
            return ["Request access to the restricted domain from the governance admin."]

        if not objects:
            return ["Submit or approve source context related to this question."]

        if request.mode == "executive_insight":
            return [
                "Check related driver metrics before finalizing the narrative.",
                "Validate whether the source data is final or still preliminary.",
                "Ask the metric owner to confirm caveats before sharing the explanation.",
            ]

        return ["Review the source evidence and object owner before using this in production."]
