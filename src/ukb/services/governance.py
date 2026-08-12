from __future__ import annotations

from ukb.models import AuditEvent, ReviewDecision, ReviewItem, ReviewStatus
from ukb.store import BrainStore


class GovernanceService:
    def __init__(self, store: BrainStore):
        self.store = store

    def list_queue(self) -> list[ReviewItem]:
        return self.store.list_review_items(ReviewStatus.human_review_required)

    def approve(self, review_item_id: str, decision: ReviewDecision) -> ReviewItem:
        review_item = self._get_review_item(review_item_id)
        review_item.status = ReviewStatus.approved
        review_item.reviewer = decision.reviewed_by
        review_item.review_comment = decision.comment
        review_item.candidate_object.status = ReviewStatus.approved

        published = self.store.publish_object(review_item.candidate_object)

        self.store.add_audit_event(
            AuditEvent(
                event_type="review_approved",
                actor=decision.reviewed_by,
                target_id=review_item_id,
                details={"published_object_id": published.id, "comment": decision.comment},
            )
        )
        return review_item

    def reject(self, review_item_id: str, decision: ReviewDecision) -> ReviewItem:
        review_item = self._get_review_item(review_item_id)
        review_item.status = ReviewStatus.rejected
        review_item.reviewer = decision.reviewed_by
        review_item.review_comment = decision.comment
        review_item.candidate_object.status = ReviewStatus.rejected

        self.store.add_audit_event(
            AuditEvent(
                event_type="review_rejected",
                actor=decision.reviewed_by,
                target_id=review_item_id,
                details={"comment": decision.comment},
            )
        )
        return review_item

    def request_changes(self, review_item_id: str, decision: ReviewDecision) -> ReviewItem:
        review_item = self._get_review_item(review_item_id)
        review_item.status = ReviewStatus.changes_requested
        review_item.reviewer = decision.reviewed_by
        review_item.review_comment = decision.comment
        review_item.candidate_object.status = ReviewStatus.changes_requested

        self.store.add_audit_event(
            AuditEvent(
                event_type="review_changes_requested",
                actor=decision.reviewed_by,
                target_id=review_item_id,
                details={"comment": decision.comment},
            )
        )
        return review_item

    def _get_review_item(self, review_item_id: str) -> ReviewItem:
        try:
            return self.store.review_items[review_item_id]
        except KeyError as exc:
            raise KeyError(f"Review item not found: {review_item_id}") from exc
