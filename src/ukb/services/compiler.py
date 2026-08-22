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
    """Transparent deterministic compiler used before advisory LLM enrichment."""

    patterns: list[tuple[KnowledgeObjectType, tuple[re.Pattern[str], ...]]] = [
        (
            KnowledgeObjectType.metric,
            tuple(
                re.compile(pattern, re.IGNORECASE)
                for pattern in (
                    r"\bmetric\b",
                    r"\bkpi\b",
                    r"\bformula\b",
                    r"\baverage\b",
                    r"\brate\b",
                    r"\btime\b",
                )
            ),
        ),
        (
            KnowledgeObjectType.dashboard,
            tuple(re.compile(pattern, re.IGNORECASE) for pattern in (r"\bdashboard\b",)),
        ),
        (
            KnowledgeObjectType.report,
            tuple(re.compile(pattern, re.IGNORECASE) for pattern in (r"\breport\b", r"\breview\b")),
        ),
        (
            KnowledgeObjectType.business_rule,
            tuple(
                re.compile(pattern, re.IGNORECASE)
                for pattern in (r"\brule\b", r"\bpolicy\b", r"\bmust\b", r"\bexclude(?:d)?\b", r"\bcaveat\b")
            ),
        ),
        (
            KnowledgeObjectType.dataset,
            tuple(re.compile(pattern, re.IGNORECASE) for pattern in (r"\bdataset\b", r"\btable\b", r"\bschema\b")),
        ),
        (
            KnowledgeObjectType.process,
            tuple(re.compile(pattern, re.IGNORECASE) for pattern in (r"\bprocess\b", r"\bworkflow\b", r"\bprocedure\b")),
        ),
    ]

    def compile_submission(self, submission: IngestionSubmission) -> tuple[SourceEvidence, ReviewItem]:
        source = SourceEvidence(
            source_type=submission.source_type,
            title=submission.title,
            content_excerpt=self._excerpt(submission.content),
            source_uri=submission.source_uri,
            submitted_by=submission.submitted_by,
            domain=submission.domain,
            owner=submission.owner,
            sensitivity=submission.sensitivity,
        )
        candidate = self.compile_candidate(submission, source.source_id)
        return source, ReviewItem(source_id=source.source_id, candidate_object=candidate)

    def compile_candidate(self, submission: IngestionSubmission, source_id: str) -> KnowledgeObject:
        owner = submission.owner or self._extract_owner(submission.content)
        aliases = [tag.removeprefix("alias:").strip() for tag in submission.tags if tag.startswith("alias:")]
        return KnowledgeObject(
            type=self._classify(submission.content),
            title=submission.title,
            summary=self._summarize(submission.content),
            domain=submission.domain,
            owner=owner,
            sensitivity=submission.sensitivity,
            source_ids=[source_id],
            aliases=[alias for alias in aliases if alias],
            confidence=self._confidence(submission.content),
            attributes={
                "tags": submission.tags,
                "compiler": "heuristic-v1",
                "effective_date": submission.effective_date,
            },
        )

    def _classify(self, content: str) -> KnowledgeObjectType:
        scores: list[tuple[int, KnowledgeObjectType]] = []
        for object_type, patterns in self.patterns:
            score = sum(1 for pattern in patterns if pattern.search(content))
            if score:
                scores.append((score, object_type))
        if not scores:
            return KnowledgeObjectType.unknown
        scores.sort(key=lambda item: item[0], reverse=True)
        return scores[0][1]

    @staticmethod
    def _summarize(content: str) -> str:
        cleaned = " ".join(content.split())
        if len(cleaned) <= 420:
            return cleaned
        sentence_end = cleaned.rfind(". ", 0, 420)
        if sentence_end > 160:
            return cleaned[: sentence_end + 1]
        return cleaned[:417] + "..."

    @staticmethod
    def _excerpt(content: str, limit: int = 700) -> str:
        cleaned = " ".join(content.split())
        return cleaned if len(cleaned) <= limit else cleaned[: limit - 3] + "..."

    @staticmethod
    def _confidence(content: str) -> float:
        score = 0.35
        lowered = content.lower()
        for keyword in (
            "definition",
            "owned by",
            "source",
            "dashboard",
            "metric",
            "formula",
            "rule",
            "exclude",
            "effective",
            "caveat",
        ):
            if keyword in lowered:
                score += 0.055
        if len(content) > 500:
            score += 0.05
        return min(round(score, 2), 0.9)

    owner_stop_words = (" and ", " but ", " which ", " that ", " with ", " for ")

    def _extract_owner(self, content: str) -> str | None:
        match = re.search(r"owned by ([A-Za-z0-9 _&-]+)", content, re.IGNORECASE)
        if not match:
            return None
        owner = match.group(1).strip()
        lowered = owner.lower()
        for stop_word in self.owner_stop_words:
            index = lowered.find(stop_word)
            if index > 0:
                owner = owner[:index]
                lowered = owner.lower()
        return owner.strip().rstrip(".,;:") or None
