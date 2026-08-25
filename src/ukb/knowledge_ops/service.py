from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from datetime import timedelta
from uuid import uuid4

from ukb.api.security import Principal
from ukb.application import BrainApplication
from ukb.config import Settings
from ukb.connectors.crawl4ai import Crawl4AIConnector
from ukb.connectors.google_drive import GoogleDriveConnector
from ukb.ingestion_models import (
    CrawlIngestionRequest,
    DriveIngestionRequest,
    IngestionGovernance,
    IngestionSourceMode,
)
from ukb.knowledge_ops.models import (
    AssignmentStatus,
    KnowledgeOperationsStatus,
    QualityAssessment,
    QualityAssessmentRequest,
    QualityDisposition,
    QualityFinding,
    QualitySeverity,
    QualitySubmissionResult,
    RankingFactor,
    RefreshStatus,
    RerankedResult,
    RerankedSearchResponse,
    RetrievalEvaluationReport,
    RetrievalEvaluationRequest,
    RetrievalFeedback,
    RetrievalFeedbackRequest,
    ReviewAssignment,
    ReviewAssignmentRequest,
    ReviewComment,
    ReviewCommentRequest,
    SourceRefreshRun,
    SourceSubscription,
    SourceSubscriptionRequest,
    SubscriptionStatus,
)
from ukb.knowledge_ops.store import (
    InMemoryKnowledgeOperationsStore,
    KnowledgeOperationsRepository,
    SqlAlchemyKnowledgeOperationsStore,
)
from ukb.models import IngestionSubmission, utc_now
from ukb.search import SearchRequest
from ukb.services.ingestion import IngestionParserService, ParsedIngestionItem

_SECRET_PATTERNS = (
    re.compile(r"\b(?:api[_-]?key|secret|password|passwd|access[_-]?token)\s*[:=]\s*\S+", re.I),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
_INJECTION_PATTERNS = (
    re.compile(r"ignore (?:all |the )?(?:previous|prior|system) instructions", re.I),
    re.compile(r"reveal (?:the )?(?:system prompt|hidden instructions|secrets)", re.I),
    re.compile(r"you are now (?:an?|the) ", re.I),
)
_PERSONAL_PATTERNS = (
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
)


class KnowledgeOperationsService:
    """Governed operational layer around ingestion, review, refresh, and recall.

    The service never publishes knowledge. It screens evidence, coordinates
    reviewers, creates refresh candidates, and evaluates recall while retaining
    the application's existing human approval and publication boundaries.
    """

    def __init__(
        self,
        *,
        application: BrainApplication,
        settings: Settings,
        store: KnowledgeOperationsRepository | None = None,
    ) -> None:
        self.application = application
        self.settings = settings
        self.store = store or self._build_store(settings)
        self.parser = IngestionParserService(
            max_file_bytes=settings.max_upload_bytes,
            max_batch_files=settings.max_batch_files,
            max_archive_bytes=settings.max_archive_bytes,
            max_archive_uncompressed_bytes=settings.max_archive_uncompressed_bytes,
        )
        self.crawl = Crawl4AIConnector(settings)
        self.drive = GoogleDriveConnector(settings)

    @staticmethod
    def _build_store(settings: Settings) -> KnowledgeOperationsRepository:
        if settings.store_backend.casefold().strip() == "sqlalchemy":
            return SqlAlchemyKnowledgeOperationsStore(
                settings.database_url,
                create_schema=settings.create_schema_on_startup,
            )
        return InMemoryKnowledgeOperationsStore()

    def assess(
        self,
        request: QualityAssessmentRequest,
        *,
        principal: Principal,
    ) -> QualityAssessment:
        content = request.content.strip()
        normalized = " ".join(content.casefold().split())
        input_hash = hashlib.sha256(normalized.encode()).hexdigest()
        findings: list[QualityFinding] = []
        score = 1.0

        if len(content) < 80:
            score -= 0.28
            findings.append(
                QualityFinding(
                    code="content_too_short",
                    severity=QualitySeverity.warning,
                    message="The source is too short to establish reliable organizational context.",
                    recommendation="Add definitions, ownership, scope, caveats, and source evidence.",
                )
            )
        if not request.owner:
            score -= 0.12
            findings.append(
                QualityFinding(
                    code="owner_missing",
                    severity=QualitySeverity.warning,
                    message="No responsible owner was provided.",
                    recommendation="Assign a domain owner before publication.",
                )
            )
        if request.domain.casefold() in {"", "general", "unknown"}:
            score -= 0.08
            findings.append(
                QualityFinding(
                    code="domain_generic",
                    severity=QualitySeverity.info,
                    message="The source is not mapped to a specific business domain.",
                    recommendation="Select the narrowest valid organizational domain.",
                )
            )
        if not request.source_uri:
            score -= 0.06
            findings.append(
                QualityFinding(
                    code="source_uri_missing",
                    severity=QualitySeverity.info,
                    message="A canonical source URI was not supplied.",
                    recommendation="Provide a stable document, repository, dashboard, or system URI.",
                )
            )

        if any(pattern.search(content) for pattern in _SECRET_PATTERNS):
            score -= 0.65
            findings.append(
                QualityFinding(
                    code="possible_secret",
                    severity=QualitySeverity.critical,
                    message="The source may contain a credential, token, password, or private key.",
                    recommendation="Remove the secret, rotate it, and submit a sanitized source.",
                )
            )
        if any(pattern.search(content) for pattern in _INJECTION_PATTERNS):
            score -= 0.4
            findings.append(
                QualityFinding(
                    code="instruction_injection",
                    severity=QualitySeverity.high,
                    message="The source contains language that may attempt to redirect model behavior.",
                    recommendation="Quarantine and review the source as untrusted evidence.",
                )
            )
        if any(pattern.search(content) for pattern in _PERSONAL_PATTERNS):
            score -= 0.16
            findings.append(
                QualityFinding(
                    code="possible_personal_data",
                    severity=QualitySeverity.high,
                    message="The source may contain personal identifiers.",
                    recommendation="Confirm classification, minimization, and access policy before use.",
                )
            )
        duplicate = next(
            (
                value
                for value in self.store.quality_assessments.values()
                if value.tenant_id == principal.tenant_id and value.input_hash == input_hash
            ),
            None,
        )
        if duplicate is not None:
            score -= 0.12
            findings.append(
                QualityFinding(
                    code="duplicate_submission",
                    severity=QualitySeverity.warning,
                    message=f"The same normalized source was assessed as {duplicate.assessment_id}.",
                    recommendation="Confirm whether this is a new version before continuing.",
                )
            )

        score = max(0.0, min(1.0, round(score, 4)))
        severities = {finding.severity for finding in findings}
        if QualitySeverity.critical in severities:
            disposition = QualityDisposition.reject
        elif QualitySeverity.high in severities or score < 0.45:
            disposition = QualityDisposition.quarantine
        elif findings or score < 0.82:
            disposition = QualityDisposition.accept_with_warnings
        else:
            disposition = QualityDisposition.accept

        return self.store.add_quality(
            QualityAssessment(
                assessment_id=f"quality_{uuid4().hex[:16]}",
                tenant_id=principal.tenant_id,
                actor=principal.subject,
                input_hash=input_hash,
                score=score,
                disposition=disposition,
                findings=findings,
            )
        )

    def submit(
        self,
        request: QualityAssessmentRequest,
        *,
        principal: Principal,
    ) -> QualitySubmissionResult:
        assessment = self.assess(request, principal=principal)
        if assessment.disposition == QualityDisposition.reject:
            return QualitySubmissionResult(assessment=assessment, status="rejected")
        if assessment.disposition == QualityDisposition.quarantine:
            return QualitySubmissionResult(assessment=assessment, status="quarantined")

        item = self.application.submit_text(
            IngestionSubmission(
                title=request.title,
                source_type=request.source_type,
                submitted_by=principal.subject,
                content=request.content,
                source_uri=request.source_uri,
                domain=request.domain,
                owner=request.owner,
                sensitivity=request.sensitivity,
                tags=[*request.tags, f"quality:{assessment.disposition.value}"],
                effective_date=request.effective_date,
            ),
            principal=principal,
        )
        item.candidate_object.attributes["tenant_id"] = principal.tenant_id
        item.candidate_object.attributes["quality_assessment_id"] = assessment.assessment_id
        source = self.application.store.sources[item.source_id]
        source.access_policy["tenant_id"] = principal.tenant_id
        self.application.store.add_source(source)
        self.application.store.update_review_item(item)
        return QualitySubmissionResult(
            assessment=assessment,
            review_item_id=item.id,
            source_id=item.source_id,
            status="review_created",
        )

    def list_assessments(self, principal: Principal) -> list[QualityAssessment]:
        return sorted(
            (
                value
                for value in self.store.quality_assessments.values()
                if value.tenant_id == principal.tenant_id
            ),
            key=lambda value: value.created_at,
            reverse=True,
        )

    def assign_review(
        self,
        request: ReviewAssignmentRequest,
        *,
        principal: Principal,
    ) -> ReviewAssignment:
        item = self.application.store.review_items.get(request.review_item_id)
        if item is None or self._review_tenant(item) != principal.tenant_id:
            raise KeyError(f"Review item not found: {request.review_item_id}")
        current = next(
            (
                value
                for value in self.store.assignments.values()
                if value.tenant_id == principal.tenant_id
                and value.review_item_id == request.review_item_id
                and value.status in {AssignmentStatus.assigned, AssignmentStatus.claimed}
            ),
            None,
        )
        if current is not None:
            current.status = AssignmentStatus.cancelled
            current.updated_at = utc_now()
            self.store.add_assignment(current)
        assignment = ReviewAssignment(
            assignment_id=f"assignment_{uuid4().hex[:16]}",
            tenant_id=principal.tenant_id,
            review_item_id=request.review_item_id,
            assignee=request.assignee,
            assigned_by=principal.subject,
            priority=request.priority,
            due_at=request.due_at,
            note=request.note,
        )
        item.reviewer = request.assignee
        item.revision += 1
        item.updated_at = utc_now()
        self.application.store.update_review_item(item)
        return self.store.add_assignment(assignment)

    def add_comment(
        self,
        request: ReviewCommentRequest,
        *,
        principal: Principal,
    ) -> ReviewComment:
        item = self.application.store.review_items.get(request.review_item_id)
        if item is None or self._review_tenant(item) != principal.tenant_id:
            raise KeyError(f"Review item not found: {request.review_item_id}")
        return self.store.add_comment(
            ReviewComment(
                comment_id=f"comment_{uuid4().hex[:16]}",
                tenant_id=principal.tenant_id,
                review_item_id=request.review_item_id,
                author=principal.subject,
                body=request.body,
                comment_type=request.comment_type,
            )
        )

    def review_workload(self, principal: Principal) -> dict[str, object]:
        assignments = [
            value
            for value in self.store.assignments.values()
            if value.tenant_id == principal.tenant_id
            and value.status in {AssignmentStatus.assigned, AssignmentStatus.claimed}
        ]
        return {
            "tenant_id": principal.tenant_id,
            "active_assignments": len(assignments),
            "overdue": sum(
                1
                for value in assignments
                if value.due_at is not None and value.due_at < utc_now()
            ),
            "by_assignee": dict(sorted(Counter(value.assignee for value in assignments).items())),
        }

    def create_subscription(
        self,
        request: SourceSubscriptionRequest,
        *,
        principal: Principal,
    ) -> SourceSubscription:
        now = utc_now()
        return self.store.add_subscription(
            SourceSubscription(
                subscription_id=f"subscription_{uuid4().hex[:16]}",
                tenant_id=principal.tenant_id,
                connector_type=request.connector_type,
                location=request.location,
                domain=request.domain,
                owner=request.owner,
                sensitivity=request.sensitivity,
                interval_minutes=request.interval_minutes,
                tags=request.tags,
                created_by=principal.subject,
                next_run_at=now,
            )
        )

    def list_subscriptions(self, principal: Principal) -> list[SourceSubscription]:
        return sorted(
            (
                value
                for value in self.store.subscriptions.values()
                if value.tenant_id == principal.tenant_id
            ),
            key=lambda value: value.updated_at,
            reverse=True,
        )

    def run_subscription(
        self,
        subscription_id: str,
        *,
        principal: Principal,
    ) -> SourceRefreshRun:
        subscription = self.store.subscriptions.get(subscription_id)
        if subscription is None or subscription.tenant_id != principal.tenant_id:
            raise KeyError(f"Source subscription not found: {subscription_id}")
        if subscription.status == SubscriptionStatus.paused:
            return self.store.add_refresh_run(
                SourceRefreshRun(
                    run_id=f"refresh_{uuid4().hex[:16]}",
                    tenant_id=principal.tenant_id,
                    subscription_id=subscription_id,
                    status=RefreshStatus.skipped,
                    message="The source subscription is paused.",
                )
            )

        try:
            parsed_items = self._collect_subscription(subscription)
            digest = hashlib.sha256(
                "\n".join(item.text for item in parsed_items).encode("utf-8")
            ).hexdigest()
            if subscription.last_checksum == digest:
                status = RefreshStatus.unchanged
                review_ids: list[str] = []
                message = "The source checksum is unchanged; no duplicate candidate was created."
            else:
                batch = self.application.submit_parsed_batch(
                    governance=IngestionGovernance(
                        title=f"Scheduled refresh: {subscription.location}",
                        submitted_by=principal.subject,
                        domain=subscription.domain,
                        owner=subscription.owner,
                        sensitivity=subscription.sensitivity,
                        tags=[*subscription.tags, "scheduled-refresh"],
                    ),
                    source_mode=IngestionSourceMode(subscription.connector_type.value),
                    parsed_items=parsed_items,
                    principal=principal,
                )
                for item in batch.review_items:
                    item.candidate_object.attributes["tenant_id"] = principal.tenant_id
                    item.candidate_object.attributes["subscription_id"] = subscription.subscription_id
                    self.application.store.update_review_item(item)
                review_ids = [item.id for item in batch.review_items]
                status = RefreshStatus.changed
                message = f"Created {len(review_ids)} governed refresh candidate(s)."
                subscription.last_checksum = digest
            subscription.last_success_at = utc_now()
            subscription.consecutive_failures = 0
            subscription.status = SubscriptionStatus.active
            subscription.next_run_at = utc_now() + timedelta(minutes=subscription.interval_minutes)
            subscription.updated_at = utc_now()
            self.store.add_subscription(subscription)
            run = SourceRefreshRun(
                run_id=f"refresh_{uuid4().hex[:16]}",
                tenant_id=principal.tenant_id,
                subscription_id=subscription_id,
                status=status,
                checksum=digest,
                review_item_ids=review_ids,
                message=message,
            )
        except Exception as exc:
            subscription.consecutive_failures += 1
            subscription.status = SubscriptionStatus.failing
            subscription.next_run_at = utc_now() + timedelta(minutes=subscription.interval_minutes)
            subscription.updated_at = utc_now()
            self.store.add_subscription(subscription)
            run = SourceRefreshRun(
                run_id=f"refresh_{uuid4().hex[:16]}",
                tenant_id=principal.tenant_id,
                subscription_id=subscription_id,
                status=RefreshStatus.failed,
                message=f"Refresh failed: {type(exc).__name__}: {exc}",
            )
        return self.store.add_refresh_run(run)

    def _collect_subscription(self, subscription: SourceSubscription) -> list[ParsedIngestionItem]:
        if subscription.connector_type.value == "crawl4ai":
            crawl_request = CrawlIngestionRequest.model_validate(
                {
                    "title": f"Scheduled web refresh: {subscription.location}",
                    "submitted_by": subscription.created_by,
                    "domain": subscription.domain,
                    "owner": subscription.owner,
                    "sensitivity": subscription.sensitivity,
                    "tags": subscription.tags,
                    "url": subscription.location,
                    "max_pages": 1,
                }
            )
            crawl_collection = self.crawl.collect(crawl_request)
            _, parsed = self.parser.preview(
                crawl_collection.items,
                source_mode=IngestionSourceMode.crawl4ai,
                connector="scheduled:crawl4ai",
            )
            return parsed
        if subscription.connector_type.value == "google_drive":
            drive_collection = self.drive.collect(
                DriveIngestionRequest(
                    title=f"Scheduled Drive refresh: {subscription.location}",
                    submitted_by=subscription.created_by,
                    domain=subscription.domain,
                    owner=subscription.owner,
                    sensitivity=subscription.sensitivity,
                    tags=subscription.tags,
                    folder_url=subscription.location,
                    max_files=100,
                )
            )
            _, parsed = self.parser.preview(
                drive_collection.items,
                source_mode=IngestionSourceMode.google_drive,
                connector="scheduled:google-drive",
            )
            return parsed
        raise ValueError(
            f"Scheduled refresh for {subscription.connector_type.value!r} requires an installed worker plugin."
        )

    def reranked_search(
        self,
        request: SearchRequest,
        *,
        principal: Principal,
    ) -> RerankedSearchResponse:
        base = self.application.search(request, principal=principal)
        results: list[RerankedResult] = []
        for result in base.results:
            obj = result.object
            if str(obj.attributes.get("tenant_id") or principal.tenant_id) != principal.tenant_id:
                continue
            raw = float(result.hit.score)
            authority = max(0.0, min(1.0, (6 - obj.authority_tier) / 5))
            evidence = max(0.0, min(1.0, len(obj.evidence_refs) / 3))
            freshness_days = max(0.0, (utc_now() - obj.updated_at).total_seconds() / 86400)
            freshness = math.exp(-freshness_days / 365)
            confidence = float(obj.confidence)
            exact = 1.0 if any(reason.startswith("exact_") for reason in result.hit.reasons) else 0.0
            lexical = min(1.0, raw / 100.0)
            factors = [
                RankingFactor(name="exact_match", value=exact, contribution=exact * 35),
                RankingFactor(name="lexical", value=lexical, contribution=lexical * 25),
                RankingFactor(name="authority", value=authority, contribution=authority * 15),
                RankingFactor(name="evidence", value=evidence, contribution=evidence * 12),
                RankingFactor(name="freshness", value=freshness, contribution=freshness * 8),
                RankingFactor(name="object_confidence", value=confidence, contribution=confidence * 5),
            ]
            results.append(
                RerankedResult(
                    object_id=obj.id,
                    title=obj.title,
                    domain=obj.domain,
                    raw_score=raw,
                    final_score=round(sum(factor.contribution for factor in factors), 6),
                    factors=factors,
                    reasons=result.hit.reasons,
                    source_ids=obj.source_ids,
                )
            )
        results.sort(key=lambda value: (-value.final_score, value.object_id))
        return RerankedSearchResponse(
            query=request.query,
            results=results[: request.limit],
            denied_count=base.denied_count,
            retrieval_backend=base.index.backend_active,
        )

    def evaluate(
        self,
        request: RetrievalEvaluationRequest,
        *,
        principal: Principal,
    ) -> RetrievalEvaluationReport:
        reciprocal_ranks: list[float] = []
        recalled = 0
        abstention_correct = 0
        passed = 0
        for case in request.cases:
            response = self.reranked_search(
                SearchRequest(
                    query=case.question,
                    domains=case.domains,
                    limit=request.top_k,
                ),
                principal=principal,
            )
            expected_ids = set(case.expected_object_ids)
            expected_titles = {value.casefold() for value in case.expected_titles}
            positions = [
                index + 1
                for index, result in enumerate(response.results)
                if result.object_id in expected_ids or result.title.casefold() in expected_titles
            ]
            hit = bool(positions)
            reciprocal_ranks.append(1.0 / min(positions) if positions else 0.0)
            if hit:
                recalled += 1
            abstained = not response.results
            if abstained == case.should_abstain:
                abstention_correct += 1
            if abstained if case.should_abstain else hit:
                passed += 1
        count = len(request.cases)
        return RetrievalEvaluationReport(
            case_count=count,
            recall_at_k=recalled / count,
            mean_reciprocal_rank=sum(reciprocal_ranks) / count,
            abstention_accuracy=abstention_correct / count,
            passed_cases=passed,
            failed_cases=count - passed,
        )

    def add_feedback(
        self,
        request: RetrievalFeedbackRequest,
        *,
        principal: Principal,
    ) -> RetrievalFeedback:
        return self.store.add_feedback(
            RetrievalFeedback(
                feedback_id=f"feedback_{uuid4().hex[:16]}",
                tenant_id=principal.tenant_id,
                actor=principal.subject,
                query=request.query,
                label=request.label,
                object_id=request.object_id,
                context_pack_id=request.context_pack_id,
                note=request.note,
            )
        )

    def status(self, principal: Principal) -> KnowledgeOperationsStatus:
        assessments = [
            value
            for value in self.store.quality_assessments.values()
            if value.tenant_id == principal.tenant_id
        ]
        return KnowledgeOperationsStatus(
            tenant_id=principal.tenant_id,
            subject=principal.subject,
            auth_method=principal.auth_method,
            quality_assessments=len(assessments),
            quarantined_sources=sum(
                1
                for value in assessments
                if value.disposition in {QualityDisposition.quarantine, QualityDisposition.reject}
            ),
            active_assignments=sum(
                1
                for value in self.store.assignments.values()
                if value.tenant_id == principal.tenant_id
                and value.status in {AssignmentStatus.assigned, AssignmentStatus.claimed}
            ),
            active_subscriptions=sum(
                1
                for value in self.store.subscriptions.values()
                if value.tenant_id == principal.tenant_id
                and value.status == SubscriptionStatus.active
            ),
            retrieval_feedback=sum(
                1 for value in self.store.feedback.values() if value.tenant_id == principal.tenant_id
            ),
            capabilities=[
                "oidc_tenant_context",
                "knowledge_quality_firewall",
                "review_assignments",
                "continuous_source_refresh",
                "explainable_reranking",
                "retrieval_evaluation",
            ],
        )

    @staticmethod
    def _review_tenant(item: object) -> str:
        candidate = getattr(item, "candidate_object")
        return str(candidate.attributes.get("tenant_id") or "default")

    def close(self) -> None:
        self.store.close()
