from __future__ import annotations

from ukb.models import BrainGraph, GraphEdge, GraphNode, KnowledgeObject, ReviewItem
from ukb.store import BrainStore


class BrainGraphService:
    """Build an Obsidian-style graph projection from the governed brain store.

    This projection is UI-oriented. It does not replace graph persistence or
    lineage storage; it gives the React app a single endpoint for visualizing
    sources, review items, published objects, AI enrichment state, and relationships.
    """

    def __init__(self, store: BrainStore):
        self.store = store

    def build(self, include_review_items: bool = True) -> BrainGraph:
        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}

        def add_edge(source: str | None, target: str | None, edge_type: str, confidence: float = 0.5) -> None:
            if not source or not target or source == target:
                return
            edge_id = f"{source}::{edge_type}::{target}"
            edges[edge_id] = GraphEdge(
                id=edge_id,
                source=source,
                target=target,
                type=edge_type,
                confidence=confidence,
            )

        def add_object_node(obj: KnowledgeObject, node_type: str = "knowledge_object") -> None:
            if obj.id not in nodes:
                nodes[obj.id] = GraphNode(
                    id=obj.id,
                    label=obj.title,
                    type=node_type if node_type != "knowledge_object" else obj.type.value,
                    domain=obj.domain,
                    status=obj.status.value,
                    sensitivity=obj.sensitivity.value,
                    confidence=obj.confidence,
                    metadata={
                        "summary": obj.summary,
                        "owner": obj.owner,
                        "source_ids": obj.source_ids,
                        "attributes": obj.attributes,
                    },
                )
            for source_id in obj.source_ids:
                add_edge(source_id, obj.id, "evidence_for", confidence=obj.confidence)
            for relationship in obj.relationships:
                add_edge(obj.id, relationship.target_id, relationship.type, relationship.confidence)

        def add_review_node(review_item: ReviewItem) -> None:
            ai = review_item.ai_enrichment
            nodes[review_item.id] = GraphNode(
                id=review_item.id,
                label=f"Review: {review_item.candidate_object.title}",
                type="review_item",
                domain=review_item.candidate_object.domain,
                status=review_item.status.value,
                sensitivity=review_item.candidate_object.sensitivity.value,
                confidence=review_item.candidate_object.confidence,
                metadata={
                    "reviewer": review_item.reviewer,
                    "review_comment": review_item.review_comment,
                    "candidate_object_id": review_item.candidate_object.id,
                    "ai_enrichment_id": ai.id if ai else None,
                    "ai_provider": ai.provider.value if ai else None,
                    "ai_review_brief": ai.review_brief.summary if ai else None,
                    "ai_validation_findings": [finding.model_dump(mode="json") for finding in ai.validation_findings] if ai else [],
                },
            )
            add_edge(review_item.source_id, review_item.id, "submitted_as")
            add_edge(review_item.id, review_item.candidate_object.id, "reviews")
            if ai:
                ai_node_id = f"ai:{ai.id}"
                nodes[ai_node_id] = GraphNode(
                    id=ai_node_id,
                    label=f"AI brief: {review_item.candidate_object.title}",
                    type="ai_enrichment",
                    domain=review_item.candidate_object.domain,
                    status=ai.status.value,
                    sensitivity=review_item.candidate_object.sensitivity.value,
                    confidence=ai.confidence,
                    metadata=ai.model_dump(mode="json"),
                )
                add_edge(ai_node_id, review_item.id, "enriches_review", ai.confidence)

        for source in self.store.sources.values():
            nodes[source.source_id] = GraphNode(
                id=source.source_id,
                label=source.title,
                type="source_evidence",
                domain=source.domain,
                status="evidence",
                sensitivity=source.sensitivity.value,
                confidence=1.0,
                metadata={
                    "source_type": source.source_type.value,
                    "source_uri": source.source_uri,
                    "submitted_by": source.submitted_by,
                    "content_excerpt": source.content_excerpt,
                    "created_at": source.created_at.isoformat(),
                },
            )

        for obj in self.store.knowledge_objects.values():
            add_object_node(obj)

        if include_review_items:
            for review_item in self.store.review_items.values():
                add_object_node(review_item.candidate_object, node_type="candidate_object")
                add_review_node(review_item)

        return BrainGraph(nodes=list(nodes.values()), edges=list(edges.values()))
