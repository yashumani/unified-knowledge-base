from __future__ import annotations

from dataclasses import dataclass

from ukb.config import Settings, get_settings
from ukb.models import (
    AuditEvent,
    KnowledgeObject,
    PublishDecision,
    RelationshipRecord,
    ReviewDecision,
    ReviewItem,
    ReviewRevisionRequest,
    ReviewStatus,
    utc_now,
)
from ukb.storage.memory import BrainStore


class GovernanceConflict(RuntimeError):
    """Raised when a stale revision or invalid state transition is requested."""


class GovernanceValidationError(RuntimeError):
    """Raised when publication requirements are not met."""


@dataclass(frozen=True)
class GovernanceTransition:
    item: ReviewItem
    published_object: KnowledgeObject | None = None


class GovernanceService:
    def __init__(self, store: BrainStore, settings: Settings | None = None):
        self.store = store
        self.settings = settings or get_settings()

    def list_queue(self) -> list[ReviewItem]:
        return self.store.list_review_items(
            statuses={ReviewStatus.human_review_required, ReviewStatus.changes_requested}
        )

    def list_approved(self) -> list[ReviewItem]:
        return self.store.list_review_items(
            statuses={ReviewStatus.approved, ReviewStatus.publication_pending}
        )

    def approve(self, review_item_id: str, decision: ReviewDecision, *, actor: str) -> ReviewItem:
        item = self._get(review_item_id)
        self._check_revision(item, decision.expected_revision)
        self._require_state(item, {ReviewStatus.human_review_required})
        item.status = ReviewStatus.approved
        item.candidate_object.status = ReviewStatus.approved
        item.reviewer = actor
        item.approved_by = actor
        item.approved_at = utc_now()
        item.review_comment = decision.comment
        self._touch(item)
        self.store.update_review_item(item)
        self._audit(
            "review_approved",
            actor,
            item.id,
            {"comment": decision.comment, "revision": item.revision},
        )
        return item

    def publish(
        self,
        review_item_id: str,
        decision: PublishDecision,
        *,
        actor: str,
    ) -> GovernanceTransition:
        item = self._get(review_item_id)
        self._check_revision(item, decision.expected_revision)
        self._require_state(item, {ReviewStatus.approved, ReviewStatus.publication_pending})
        if self.settings.require_owner_for_publish and not item.candidate_object.owner:
            raise GovernanceValidationError("A responsible owner is required before publication.")

        item.status = ReviewStatus.published
        item.candidate_object.status = ReviewStatus.published
        item.candidate_object.published_by = actor
        item.candidate_object.published_at = utc_now()
        item.candidate_object.updated_at = utc_now()
        self._touch(item)
        published = self.store.publish_object(item.candidate_object)
        self.store.update_review_item(item)

        for relationship in published.relationships:
            self.store.add_relationship(
                RelationshipRecord(
                    source_object_id=published.id,
                    target_object_id=relationship.target_id,
                    relationship_type=relationship.type,
                    confidence=relationship.confidence,
                    status=ReviewStatus.published,
                    approved_by=actor,
                )
            )

        self._audit(
            "knowledge_published",
            actor,
            item.id,
            {
                "published_object_id": published.id,
                "object_version": published.version,
                "comment": decision.comment,
                "revision": item.revision,
            },
        )
        return GovernanceTransition(item=item, published_object=published)

    def reject(self, review_item_id: str, decision: ReviewDecision, *, actor: str) -> ReviewItem:
        item = self._get(review_item_id)
        self._check_revision(item, decision.expected_revision)
        self._require_state(
            item,
            {ReviewStatus.human_review_required, ReviewStatus.changes_requested},
        )
        if not (decision.comment or "").strip():
            raise GovernanceValidationError("A rejection comment is required.")
        item.status = ReviewStatus.rejected
        item.candidate_object.status = ReviewStatus.rejected
        item.reviewer = actor
        item.review_comment = decision.comment
        self._touch(item)
        self.store.update_review_item(item)
        self._audit(
            "review_rejected",
            actor,
            item.id,
            {"comment": decision.comment, "revision": item.revision},
        )
        return item

    def request_changes(
        self,
        review_item_id: str,
        decision: ReviewDecision,
        *,
        actor: str,
    ) -> ReviewItem:
        item = self._get(review_item_id)
        self._check_revision(item, decision.expected_revision)
        self._require_state(item, {ReviewStatus.human_review_required})
        if not (decision.comment or "").strip():
            raise GovernanceValidationError("A change-request comment is required.")
        item.status = ReviewStatus.changes_requested
        item.candidate_object.status = ReviewStatus.changes_requested
        item.reviewer = actor
        item.review_comment = decision.comment
        self._touch(item)
        self.store.update_review_item(item)
        self._audit(
            "review_changes_requested",
            actor,
            item.id,
            {"comment": decision.comment, "revision": item.revision},
        )
        return item

    def revise(
        self,
        review_item_id: str,
        request: ReviewRevisionRequest,
        *,
        actor: str,
    ) -> ReviewItem:
        item = self._get(review_item_id)
        self._check_revision(item, request.expected_revision)
        self._require_state(item, {ReviewStatus.changes_requested})
        candidate = item.candidate_object
        if request.title is not None:
            candidate.title = request.title
        if request.summary is not None:
            candidate.summary = request.summary
        if request.owner is not None:
            candidate.owner = request.owner or None
        if request.attributes is not None:
            candidate.attributes = {**candidate.attributes, **request.attributes}
        candidate.status = ReviewStatus.human_review_required
        candidate.updated_at = utc_now()
        item.status = ReviewStatus.human_review_required
        item.reviewer = None
        item.review_comment = request.comment
        self._touch(item)
        self.store.update_review_item(item)
        self._audit(
            "review_resubmitted",
            actor,
            item.id,
            {"comment": request.comment, "revision": item.revision},
        )
        return item

    def _touch(self, item: ReviewItem) -> None:
        item.revision += 1
        item.updated_at = utc_now()

    def _check_revision(self, item: ReviewItem, expected: int | None) -> None:
        if expected is not None and expected != item.revision:
            raise GovernanceConflict(
                f"Review item revision changed from {expected} to {item.revision}; reload before acting."
            )

    @staticmethod
    def _require_state(item: ReviewItem, allowed: set[ReviewStatus]) -> None:
        if item.status not in allowed:
            expected = ", ".join(sorted(status.value for status in allowed))
            raise GovernanceConflict(
                f"Review item {item.id} is {item.status.value}; allowed state(s): {expected}."
            )

    def _get(self, review_item_id: str) -> ReviewItem:
        try:
            return self.store.get_review_item(review_item_id)
        except KeyError as exc:
            raise KeyError(f"Review item not found: {review_item_id}") from exc

    def _audit(self, event_type: str, actor: str, target_id: str, details: dict) -> None:
        self.store.add_audit_event(
            AuditEvent(event_type=event_type, actor=actor, target_id=target_id, details=details)
        )
