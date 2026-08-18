from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from ukb.ai.service import AIEnrichmentService
from ukb.config import Settings, get_settings
from ukb.ingestion_models import IngestionGovernance, IngestionSourceMode
from ukb.models import (
    AITaskRun,
    AITaskStatus,
    AuditEvent,
    ContextPack,
    ContextPackRequest,
    IngestionSubmission,
    PublishDecision,
    ReviewDecision,
    ReviewItem,
    ReviewRevisionRequest,
    SourceEvidence,
    SourceType,
    utc_now,
)
from ukb.search import SearchIndexStatus, SearchRequest, SearchResponse
from ukb.services.access import AccessPolicyService, PrincipalLike
from ukb.services.compiler import BrainCompiler
from ukb.services.context_pack import ContextPackService
from ukb.services.evidence import EvidenceService
from ukb.services.governance import GovernanceService, GovernanceTransition
from ukb.services.ingestion import ParsedIngestionItem
from ukb.services.retrieval import RetrievalService
from ukb.storage.memory import BrainStore
from ukb.storage.objects import LocalObjectStore, ObjectStoreError


@dataclass(frozen=True)
class BatchSubmission:
    source_mode: IngestionSourceMode
    review_items: list[ReviewItem]
    sources: list[SourceEvidence]


class BrainApplication:
    """One application layer shared by REST, MCP, CLI and future workers."""

    def __init__(
        self,
        *,
        store: BrainStore,
        settings: Settings | None = None,
        ai_service: AIEnrichmentService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.store = store
        self.compiler = BrainCompiler()
        self.access_policy = AccessPolicyService.from_settings(self.settings)
        self.ai = ai_service or AIEnrichmentService(settings=self.settings)
        self.governance = GovernanceService(store, settings=self.settings)
        self.retrieval = RetrievalService(
            store,
            settings=self.settings,
            access_policy=self.access_policy,
        )
        self.context_packs = ContextPackService(
            store,
            access_policy=self.access_policy,
            retrieval=self.retrieval,
        )
        try:
            object_store = LocalObjectStore.from_url(self.settings.object_store_url)
        except ObjectStoreError:
            object_store = None
        self.evidence = EvidenceService(store, self.settings, object_store)

    def submit_text(
        self,
        submission: IngestionSubmission,
        *,
        principal: str | PrincipalLike,
    ) -> ReviewItem:
        actor = self.access_policy.subject(principal)
        trusted_submission = submission.model_copy(update={"submitted_by": actor})
        source, item = self.compiler.compile_submission(trusted_submission)
        _, chunks = self.evidence.preserve(
            source=source,
            normalized_text=trusted_submission.content,
            actor=actor,
            content_type="text/plain",
            original_bytes=trusted_submission.content.encode("utf-8"),
            original_name=f"{source.source_id}.txt",
            parser="manual-text",
        )
        item.candidate_object.evidence_refs = self.evidence.references(chunks, field_name="candidate")
        item.ai_enrichment = self._enrich(
            source=source,
            content=trusted_submission.content,
            item=item,
        )
        # The authoritative store owns its own object graph. The detached value
        # returned to an adapter remains a stable revision snapshot, so later
        # governance transitions cannot silently rewrite a caller's stale copy.
        self.store.add_review_item(item.model_copy(deep=True))
        self._audit(
            "submission_created",
            actor,
            item.id,
            {
                "source_id": source.source_id,
                "source_version_id": source.current_version_id,
                "domain": source.domain,
                "ai_enrichment_id": item.ai_enrichment.id if item.ai_enrichment else None,
            },
        )
        return item

    def submit_parsed_batch(
        self,
        *,
        governance: IngestionGovernance,
        source_mode: IngestionSourceMode,
        parsed_items: list[ParsedIngestionItem],
        principal: str | PrincipalLike,
    ) -> BatchSubmission:
        actor = self.access_policy.subject(principal)
        reviews: list[ReviewItem] = []
        sources: list[SourceEvidence] = []
        for parsed in parsed_items:
            if not parsed.text.strip() or parsed.status.value == "rejected":
                continue
            submission = IngestionSubmission(
                title=parsed.raw.name or governance.title,
                source_type=self._source_type(source_mode, parsed.raw.path),
                submitted_by=actor,
                content=parsed.text,
                source_uri=parsed.raw.source_uri,
                domain=governance.domain,
                owner=governance.owner,
                sensitivity=governance.sensitivity,
                tags=[*governance.tags, f"source:{source_mode.value}", f"path:{parsed.raw.path}"],
                effective_date=governance.effective_date,
            )
            source, item = self.compiler.compile_submission(submission)
            _, chunks = self.evidence.preserve(
                source=source,
                normalized_text=parsed.text,
                actor=actor,
                content_type=parsed.raw.content_type,
                original_bytes=parsed.raw.data,
                original_name=parsed.raw.name,
                parser=governance.parser_mode,
            )
            item.candidate_object.evidence_refs = self.evidence.references(chunks, field_name="candidate")
            item.ai_enrichment = self._enrich(source=source, content=parsed.text, item=item)
            self.store.add_review_item(item.model_copy(deep=True))
            self._audit(
                "batch_source_created",
                actor,
                item.id,
                {
                    "source_id": source.source_id,
                    "source_version_id": source.current_version_id,
                    "path": parsed.raw.path,
                    "source_mode": source_mode.value,
                },
            )
            reviews.append(item)
            sources.append(source)
        return BatchSubmission(source_mode=source_mode, review_items=reviews, sources=sources)

    def enrich_review(
        self,
        review_item_id: str,
        *,
        principal: str | PrincipalLike,
    ) -> ReviewItem:
        actor = self.access_policy.subject(principal)
        item = self.store.get_review_item(review_item_id)
        source = self.store.sources[item.source_id]
        version = self.store.source_versions.get(source.current_version_id or "")
        content = version.normalized_text if version is not None else source.content_excerpt
        item.ai_enrichment = self._enrich(source=source, content=content, item=item)
        item.updated_at = utc_now()
        item.revision += 1
        self.store.update_review_item(item)
        self._audit(
            "ai_review_item_enriched",
            actor,
            item.id,
            {"ai_enrichment_id": item.ai_enrichment.id, "revision": item.revision},
        )
        return item

    def approve_review(
        self,
        review_item_id: str,
        decision: ReviewDecision,
        *,
        principal: str | PrincipalLike,
    ) -> ReviewItem:
        item = self.governance.approve(
            review_item_id,
            decision,
            actor=self.access_policy.subject(principal),
        )
        if decision.expected_revision is None:
            self.retrieval.rebuild()
        return item

    def publish_review(
        self,
        review_item_id: str,
        decision: PublishDecision,
        *,
        principal: str | PrincipalLike,
    ) -> GovernanceTransition:
        transition = self.governance.publish(
            review_item_id,
            decision,
            actor=self.access_policy.subject(principal),
        )
        self.retrieval.rebuild()
        return transition

    def reject_review(
        self,
        review_item_id: str,
        decision: ReviewDecision,
        *,
        principal: str | PrincipalLike,
    ) -> ReviewItem:
        return self.governance.reject(
            review_item_id,
            decision,
            actor=self.access_policy.subject(principal),
        )

    def request_changes(
        self,
        review_item_id: str,
        decision: ReviewDecision,
        *,
        principal: str | PrincipalLike,
    ) -> ReviewItem:
        return self.governance.request_changes(
            review_item_id,
            decision,
            actor=self.access_policy.subject(principal),
        )

    def revise_review(
        self,
        review_item_id: str,
        request: ReviewRevisionRequest,
        *,
        principal: str | PrincipalLike,
    ) -> ReviewItem:
        return self.governance.revise(
            review_item_id,
            request,
            actor=self.access_policy.subject(principal),
        )

    def search(
        self,
        request: SearchRequest,
        *,
        principal: str | PrincipalLike,
    ) -> SearchResponse:
        return self.retrieval.search_response(request, principal=principal)

    def rebuild_search(self) -> SearchIndexStatus:
        return self.retrieval.rebuild()

    def build_context_pack(
        self,
        request: ContextPackRequest,
        *,
        principal: str | PrincipalLike,
    ) -> ContextPack:
        actor = self.access_policy.subject(principal)
        pack = self.context_packs.build(request, principal=principal)
        if pack.access_decision != "denied":
            started = time.monotonic()
            before = pack.model_dump_json()
            try:
                pack = self.ai.enrich_context_pack(context_pack=pack)
                status = AITaskStatus.completed
                error = None
            except Exception as exc:  # facade normally falls back; retain an auditable boundary
                status = AITaskStatus.failed
                error = str(exc)
            self.store.add_ai_task_run(
                AITaskRun(
                    task_type="enrich_context_pack",
                    provider=self.ai.status().provider,
                    model=self.ai.status().model,
                    status=status,
                    context_pack_id=pack.context_pack_id,
                    input_hash=hashlib.sha256(before.encode("utf-8")).hexdigest(),
                    prompt_version="context-pack-v1",
                    schema_version=self.settings.ai_schema_version,
                    fallback_used=self.ai.status().provider.value == "noop",
                    latency_ms=int((time.monotonic() - started) * 1000),
                    output_id=pack.context_pack_id,
                    error_message=error,
                    completed_at=utc_now(),
                )
            )
        self.store.add_context_pack(pack)
        self._audit(
            "context_pack_requested",
            actor,
            pack.context_pack_id,
            {
                "question": request.question,
                "mode": request.mode,
                "access_decision": pack.access_decision,
                "retrieval_engine": pack.retrieval_engine,
                "citation_count": len(pack.citations),
            },
        )
        return pack

    def _enrich(
        self,
        *,
        source: SourceEvidence,
        content: str,
        item: ReviewItem,
    ):
        started = time.monotonic()
        result = self.ai.enrich_source(
            source=source,
            content=content,
            baseline_candidate=item.candidate_object,
        )
        if result.extracted_objects:
            for extracted in result.extracted_objects:
                extracted.source_ids = list({*extracted.source_ids, source.source_id})
                if not extracted.evidence_refs:
                    extracted.evidence_refs = list(item.candidate_object.evidence_refs)
        self.store.add_ai_task_run(
            AITaskRun(
                task_type="enrich_source",
                provider=result.provider,
                model=result.model,
                status=result.status,
                source_id=source.source_id,
                review_item_id=item.id,
                input_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                prompt_version=result.prompt_version,
                schema_version=result.schema_version,
                fallback_used=(result.provider.value == "noop" or "provider_fallback" in result.review_brief.risk_flags),
                latency_ms=int((time.monotonic() - started) * 1000),
                output_id=result.id,
                error_message=result.error_message,
                completed_at=utc_now(),
            )
        )
        return result

    @staticmethod
    def _source_type(mode: IngestionSourceMode, path: str) -> SourceType:
        lowered = path.casefold()
        if mode == IngestionSourceMode.google_drive:
            return SourceType.document
        if mode == IngestionSourceMode.crawl4ai:
            return SourceType.web
        if mode == IngestionSourceMode.git:
            return SourceType.git
        if mode == IngestionSourceMode.object_store:
            return SourceType.object_store
        if mode == IngestionSourceMode.folder:
            return SourceType.folder
        if mode == IngestionSourceMode.zip:
            return SourceType.archive
        if lowered.endswith((".md", ".markdown", ".rst")):
            return SourceType.markdown
        if lowered.endswith((".csv", ".xlsx")):
            return SourceType.spreadsheet
        if lowered.endswith(".sql"):
            return SourceType.sql
        return SourceType.document

    def _audit(self, event_type: str, actor: str, target_id: str, details: dict) -> None:
        self.store.add_audit_event(
            AuditEvent(event_type=event_type, actor=actor, target_id=target_id, details=details)
        )

    def close(self) -> None:
        self.retrieval.close()
        self.store.close()
