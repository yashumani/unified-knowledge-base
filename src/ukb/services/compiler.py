from __future__ import annotations

import re

from ukb.models import (
    IngestionSubmission,
    KnowledgeObject,
    KnowledgeObjectType,
    ReviewItem,
    SourceEvidence,
)


class BrainCompiler:
    """Converts submitted context into candidate brain objects.

    This scaffold uses transparent heuristics so the workflow is easy to inspect.
    Replace or augment this with LLM extraction, document parsing, SQL parsing,
    and graph linking as the product matures.
    """

    metric_patterns = [
        re.compile(r"\bmetric\b", re.IGNORECASE),
        re.compile(r"\bkpi\b", re.IGNORECASE),
        re.compile(r"\bincident\b", re.IGNORECASE),
        re.compile(r"\bresolution\b", re.IGNORECASE),
        re.compile(r"\bresponse time\b", re.IGNORECASE),
        re.compile(r"\breopen rate\b", re.IGNORECASE),
        re.compile(r"\bbacklog\b", re.IGNORECASE),
    ]

    report_patterns = [
        re.compile(r"\bdashboard\b", re.IGNORECASE),
        re.compile(r"\breport\b", re.IGNORECASE),
        re.compile(r"\breview\b", re.IGNORECASE),
    ]

    rule_patterns = [
        re.compile(r"\brule\b", re.IGNORECASE),
        re.compile(r"\bpolicy\b", re.IGNORECASE),
        re.compile(r"\bmust\b", re.IGNORECASE),
        re.compile(r"\bexclude\b", re.IGNORECASE),
        re.compile(r"\bcaveat\b", re.IGNORECASE),
    ]

    def compile_submission(self, submission: IngestionSubmission) -> tuple[SourceEvidence, ReviewItem]:
        source = SourceEvidence(
            source_type=submission.source_type,
            title=submission.title,
            content_excerpt=self._excerpt(submission.content),
            source_uri=submission.source_uri,
            submitted_by=submission.submitted_by,
            domain=submission.domain,
            sensitivity=submission.sensitivity,
        )

        candidate = KnowledgeObject(
            type=self._classify(submission.content),
            title=submission.title,
            summary=self._summarize(submission.content),
            domain=submission.domain,
            owner=self._extract_owner(submission.content),
            sensitivity=submission.sensitivity,
            source_ids=[source.source_id],
            confidence=self._confidence(submission.content),
            attributes={
                "tags": submission.tags,
                "raw_excerpt": self._excerpt(submission.content, limit=1000),
                "compiler": "heuristic-v0",
            },
        )

        review_item = ReviewItem(
            source_id=source.source_id,
            candidate_object=candidate,
        )
        return source, review_item

    def _classify(self, content: str) -> KnowledgeObjectType:
        if any(pattern.search(content) for pattern in self.metric_patterns):
            return KnowledgeObjectType.metric
        if any(pattern.search(content) for pattern in self.report_patterns):
            return KnowledgeObjectType.report
        if any(pattern.search(content) for pattern in self.rule_patterns):
            return KnowledgeObjectType.business_rule
        return KnowledgeObjectType.unknown

    def _summarize(self, content: str) -> str:
        cleaned = " ".join(content.split())
        if len(cleaned) <= 240:
            return cleaned
        return cleaned[:237] + "..."

    def _excerpt(self, content: str, limit: int = 500) -> str:
        cleaned = " ".join(content.split())
        return cleaned[:limit]

    def _confidence(self, content: str) -> float:
        score = 0.45
        lowered = content.lower()
        for keyword in ["definition", "owned by", "source", "dashboard", "metric", "rule", "exclude", "incident"]:
            if keyword in lowered:
                score += 0.07
        return min(score, 0.92)

    def _extract_owner(self, content: str) -> str | None:
        match = re.search(r"owned by ([A-Za-z0-9 _&-]+)", content, re.IGNORECASE)
        if not match:
            return None
        return match.group(1).strip().rstrip(".")
