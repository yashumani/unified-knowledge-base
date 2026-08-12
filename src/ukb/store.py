from __future__ import annotations

from dataclasses import dataclass, field

from ukb.models import AuditEvent, KnowledgeObject, ReviewItem, ReviewStatus, SourceEvidence


@dataclass
class BrainStore:
    """Development store.

    This in-memory store makes the scaffold runnable. Replace with Postgres and
    object storage before using the platform for durable data.
    """

    sources: dict[str, SourceEvidence] = field(default_factory=dict)
    review_items: dict[str, ReviewItem] = field(default_factory=dict)
    knowledge_objects: dict[str, KnowledgeObject] = field(default_factory=dict)
    audit_events: list[AuditEvent] = field(default_factory=list)

    def add_source(self, source: SourceEvidence) -> SourceEvidence:
        self.sources[source.source_id] = source
        return source

    def add_review_item(self, review_item: ReviewItem) -> ReviewItem:
        self.review_items[review_item.id] = review_item
        return review_item

    def list_review_items(self, status: ReviewStatus | None = None) -> list[ReviewItem]:
        items = list(self.review_items.values())
        if status is not None:
            return [item for item in items if item.status == status]
        return items

    def publish_object(self, obj: KnowledgeObject) -> KnowledgeObject:
        obj.status = ReviewStatus.published
        self.knowledge_objects[obj.id] = obj
        return obj

    def list_objects(self, domain: str | None = None) -> list[KnowledgeObject]:
        objects = list(self.knowledge_objects.values())
        if domain:
            return [obj for obj in objects if obj.domain == domain]
        return objects

    def add_audit_event(self, event: AuditEvent) -> AuditEvent:
        self.audit_events.append(event)
        return event


store = BrainStore()
