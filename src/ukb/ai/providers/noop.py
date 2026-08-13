from __future__ import annotations

import hashlib
import re

from ukb.models import (
    AIEnrichmentResult,
    AIProviderHealth,
    AIProviderName,
    AIReviewBrief,
    AITaskStatus,
    ContextPack,
    EmbeddingResponse,
    KnowledgeObject,
    KnowledgeObjectType,
    ReviewStatus,
    SourceClassification,
    SourceEvidence,
    SuggestedRelationship,
    ValidationFinding,
    ValidationSeverity,
)


class NoopProvider:
    """Offline deterministic provider.

    This is the safety baseline: no network, no model, no secrets. It gives the
    review workflow useful structured hints even when LLMs are disabled or when
    a local Ollama runtime is not reachable.
    """

    name = AIProviderName.noop.value
    model = "deterministic"

    def health_check(self) -> AIProviderHealth:
        return AIProviderHealth(
            provider=AIProviderName.noop,
            reachable=True,
            message="Deterministic fallback is available. No model runtime is required.",
            base_url=None,
            model=self.model,
            embedding_model="deterministic-hash",
            details={"network": "none", "secrets": "none"},
        )

    def enrich_source(
        self,
        *,
        source: SourceEvidence,
        content: str,
        baseline_candidate: KnowledgeObject,
    ) -> AIEnrichmentResult:
        clean = " ".join(content.split())
        lowered = clean.lower()
        source_kind = self._source_kind(lowered, source)
        topics = self._topics(lowered)
        findings = self._findings(clean, lowered, baseline_candidate)
        relationships = self._relationships(clean, lowered, baseline_candidate)
        action = "request_changes" if any(f.severity == ValidationSeverity.medium for f in findings) else "needs_review"

        enriched_candidate = baseline_candidate.model_copy(deep=True)
        enriched_candidate.status = ReviewStatus.human_review_required
        enriched_candidate.attributes = {
            **enriched_candidate.attributes,
            "ai_enrichment_provider": self.name,
            "ai_detected_source_kind": source_kind,
            "ai_topics": topics,
        }

        return AIEnrichmentResult(
            provider=AIProviderName.noop,
            model=self.model,
            status=AITaskStatus.completed,
            source_classification=SourceClassification(
                source_kind=source_kind,
                domain=source.domain,
                summary=self._summary(clean),
                topics=topics,
                suggested_tags=sorted(set([source.domain, source_kind, *topics])),
                confidence=self._confidence(lowered),
            ),
            extracted_objects=[enriched_candidate],
            suggested_relationships=relationships,
            validation_findings=findings,
            review_brief=AIReviewBrief(
                summary=self._review_summary(source_kind, baseline_candidate, findings),
                recommended_action=action,
                reviewer_questions=self._review_questions(lowered, baseline_candidate),
                risk_flags=[finding.finding_type for finding in findings if finding.severity in {ValidationSeverity.medium, ValidationSeverity.high, ValidationSeverity.critical}],
            ),
            confidence=self._confidence(lowered),
        )

    def enrich_context_pack(self, *, context_pack: ContextPack) -> ContextPack:
        if not context_pack.knowledge_objects:
            context_pack.missing_context.append(
                "No approved knowledge objects matched the question. Submit and approve source context first."
            )
            context_pack.ai_guidance = "Offline enrichment found no approved objects to ground this request."
            return context_pack

        object_titles = ", ".join(obj.title for obj in context_pack.knowledge_objects[:3])
        guidance = (
            f"Offline enrichment found approved context for: {object_titles}. "
            "Use source evidence, caveats, and reviewer-approved relationships only."
        )
        context_pack.ai_guidance = guidance
        if "Review source evidence before sharing this outside the approved audience." not in context_pack.recommended_followups:
            context_pack.recommended_followups.append(
                "Review source evidence before sharing this outside the approved audience."
            )
        return context_pack

    def embed_texts(self, *, texts: list[str], model: str | None = None) -> EmbeddingResponse:
        """Return deterministic hash embeddings when Ollama is unavailable.

        These vectors are only a fallback scaffold. They let the API contract and
        tests work offline; they should not be treated as semantic embeddings.
        """

        embeddings = [self._hash_embedding(text) for text in texts]
        return EmbeddingResponse(
            provider=AIProviderName.noop,
            model=model or "deterministic-hash",
            dimensions=len(embeddings[0]) if embeddings else 0,
            embeddings=embeddings,
            fallback_used=True,
        )

    def _source_kind(self, lowered: str, source: SourceEvidence) -> str:
        if "metric" in lowered or "average" in lowered or "rate" in lowered or "kpi" in lowered:
            return "metric_definition"
        if "dashboard" in lowered or source.source_type.value == "dashboard":
            return "report_or_dashboard_context"
        if "rule" in lowered or "must" in lowered or "policy" in lowered or "caveat" in lowered:
            return "business_rule"
        if "select " in lowered or " from " in lowered:
            return "sql_or_lineage"
        return "general_context"

    def _topics(self, lowered: str) -> list[str]:
        topic_map = {
            "support": ["support operations"],
            "incident": ["incident management"],
            "sla": ["sla"],
            "dashboard": ["dashboard"],
            "metric": ["metric definition"],
            "rule": ["business rule"],
            "quality": ["quality review"],
        }
        topics: list[str] = []
        for keyword, values in topic_map.items():
            if keyword in lowered:
                topics.extend(values)
        return sorted(set(topics)) or ["general context"]

    def _findings(self, clean: str, lowered: str, candidate: KnowledgeObject) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        if not candidate.owner:
            findings.append(
                ValidationFinding(
                    severity=ValidationSeverity.medium,
                    finding_type="owner_missing",
                    message="No owner was detected. A reviewer should assign a responsible owner before publishing.",
                    recommended_action="Request changes or assign an owner during review.",
                )
            )
        if "excluding" in lowered or "exclude" in lowered:
            findings.append(
                ValidationFinding(
                    severity=ValidationSeverity.medium,
                    finding_type="exclusion_rule_needs_review",
                    message="The source mentions an exclusion rule. Confirm how this exclusion is implemented before approval.",
                    source_span=self._sentence_with(clean, "exclud"),
                    recommended_action="Ask the domain owner to confirm exclusion logic.",
                )
            )
        if "recent" in lowered or "settle" in lowered or "preliminary" in lowered:
            findings.append(
                ValidationFinding(
                    severity=ValidationSeverity.low,
                    finding_type="freshness_caveat_detected",
                    message="The source includes a freshness or review-window caveat that should be carried into context packs.",
                    source_span=self._sentence_with(clean, "settle") or self._sentence_with(clean, "recent"),
                    recommended_action="Keep this caveat attached to the candidate object.",
                )
            )
        if candidate.type == KnowledgeObjectType.unknown:
            findings.append(
                ValidationFinding(
                    severity=ValidationSeverity.medium,
                    finding_type="object_type_unclear",
                    message="The deterministic classifier could not confidently identify the object type.",
                    recommended_action="Have a reviewer classify the object manually.",
                )
            )
        if len(clean) < 80:
            findings.append(
                ValidationFinding(
                    severity=ValidationSeverity.low,
                    finding_type="source_context_short",
                    message="The source context is short. Reviewers may need more evidence before approval.",
                    recommended_action="Attach a richer source or add more detail.",
                )
            )
        return findings

    def _relationships(
        self,
        clean: str,
        lowered: str,
        candidate: KnowledgeObject,
    ) -> list[SuggestedRelationship]:
        relationships: list[SuggestedRelationship] = []
        dashboard_match = re.search(r"appears in the ([A-Za-z0-9 _&-]+ dashboard)", clean, re.IGNORECASE)
        if dashboard_match:
            relationships.append(
                SuggestedRelationship(
                    source_label=candidate.title,
                    relationship_type="appears_in",
                    target_label=dashboard_match.group(1).strip(),
                    confidence=0.82,
                    rationale="The source explicitly says the item appears in a dashboard.",
                )
            )
        if "caveat" in lowered or "settle" in lowered or "preliminary" in lowered:
            relationships.append(
                SuggestedRelationship(
                    source_label=candidate.title,
                    relationship_type="governed_by",
                    target_label="Review Window Caveat",
                    confidence=0.65,
                    rationale="The source includes a caveat or review-window condition.",
                )
            )
        return relationships

    def _review_questions(self, lowered: str, candidate: KnowledgeObject) -> list[str]:
        questions = ["Is this candidate safe to publish as approved organizational context?"]
        if not candidate.owner:
            questions.append("Who owns this definition or rule?")
        if "excluding" in lowered or "exclude" in lowered:
            questions.append("How are excluded records identified in the source system?")
        if "dashboard" in lowered:
            questions.append("Is the named dashboard the official reporting surface?")
        if "settle" in lowered or "recent" in lowered:
            questions.append("How long should this context be treated as preliminary?")
        return questions

    def _review_summary(self, source_kind: str, candidate: KnowledgeObject, findings: list[ValidationFinding]) -> str:
        risk_count = len([finding for finding in findings if finding.severity != ValidationSeverity.info])
        return (
            f"Detected {source_kind} and prepared a {candidate.type.value} candidate named "
            f"'{candidate.title}'. {risk_count} review finding(s) should be checked before approval."
        )

    def _summary(self, clean: str) -> str:
        return clean if len(clean) <= 280 else clean[:277] + "..."

    def _confidence(self, lowered: str) -> float:
        score = 0.45
        for keyword in ["definition", "owned by", "dashboard", "metric", "excluding", "review"]:
            if keyword in lowered:
                score += 0.07
        return min(round(score, 2), 0.9)

    def _sentence_with(self, text: str, needle: str) -> str | None:
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            if needle.lower() in sentence.lower():
                return sentence.strip()
        return None

    def _hash_embedding(self, text: str, dimensions: int = 16) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = []
        for index in range(dimensions):
            raw = digest[index] / 255
            values.append(round((raw * 2) - 1, 6))
        return values
