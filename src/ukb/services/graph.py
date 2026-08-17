from __future__ import annotations

from ukb.models import BrainGraph, GraphEdge, GraphNode, KnowledgeObject, ReviewItem, ReviewStatus
from ukb.services.access import AccessPolicyService, PrincipalLike, SENSITIVITY_ORDER
from ukb.storage.memory import BrainStore


class BrainGraphService:
    """Build a permission-aware projection from authoritative UKB records."""

    def __init__(self, store: BrainStore):
        self.store = store

    def build(
        self,
        include_review_items: bool = True,
        access_policy: AccessPolicyService | None = None,
        principal: str | PrincipalLike = "anonymous",
    ) -> BrainGraph:
        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}
        clearance = access_policy.clearance_for(principal) if access_policy else None
        hidden: set[str] = set()

        def visible(sensitivity) -> bool:
            return clearance is None or SENSITIVITY_ORDER[sensitivity] <= SENSITIVITY_ORDER[clearance]

        def add_edge(
            source: str | None,
            target: str | None,
            edge_type: str,
            confidence: float = 0.5,
            metadata: dict | None = None,
        ) -> None:
            if not source or not target or source == target:
                return
            edge_id = f"{source}::{edge_type}::{target}"
            edges[edge_id] = GraphEdge(
                id=edge_id,
                source=source,
                target=target,
                type=edge_type,
                confidence=confidence,
                metadata=metadata or {},
            )

        def add_object_node(obj: KnowledgeObject, node_type: str | None = None) -> None:
            if not visible(obj.sensitivity):
                hidden.add(obj.id)
                return
            nodes[obj.id] = GraphNode(
                id=obj.id,
                label=obj.title,
                type=node_type or obj.type.value,
                domain=obj.domain,
                status=obj.status.value,
                sensitivity=obj.sensitivity.value,
                confidence=obj.confidence,
                metadata={
                    "summary": obj.summary,
                    "owner": obj.owner,
                    "source_ids": obj.source_ids,
                    "evidence_refs": [reference.model_dump(mode="json") for reference in obj.evidence_refs],
                    "aliases": obj.aliases,
                    "version": obj.version,
                    "authority_tier": obj.authority_tier,
                    "published_by": obj.published_by,
                    "published_at": obj.published_at.isoformat() if obj.published_at else None,
                    "attributes": obj.attributes,
                },
            )
            for source_id in obj.source_ids:
                add_edge(source_id, obj.id, "evidence_for", obj.confidence)

        def add_review_node(item: ReviewItem) -> None:
            if not visible(item.candidate_object.sensitivity):
                hidden.add(item.id)
                return
            ai = item.ai_enrichment
            nodes[item.id] = GraphNode(
                id=item.id,
                label=f"Review: {item.candidate_object.title}",
                type="review_item",
                domain=item.candidate_object.domain,
                status=item.status.value,
                sensitivity=item.candidate_object.sensitivity.value,
                confidence=item.candidate_object.confidence,
                metadata={
                    "revision": item.revision,
                    "reviewer": item.reviewer,
                    "review_comment": item.review_comment,
                    "approved_by": item.approved_by,
                    "candidate_object_id": item.candidate_object.id,
                },
            )
            add_edge(item.source_id, item.id, "submitted_as")
            add_edge(item.id, item.candidate_object.id, "reviews")
            if ai:
                ai_id = f"ai:{ai.id}"
                nodes[ai_id] = GraphNode(
                    id=ai_id,
                    label=f"AI brief: {item.candidate_object.title}",
                    type="ai_enrichment",
                    domain=item.candidate_object.domain,
                    status=ai.status.value,
                    sensitivity=item.candidate_object.sensitivity.value,
                    confidence=ai.confidence,
                    metadata={
                        "provider": ai.provider.value,
                        "model": ai.model,
                        "prompt_version": ai.prompt_version,
                        "schema_version": ai.schema_version,
                        "review_brief": ai.review_brief.model_dump(mode="json"),
                        "validation_findings": [finding.model_dump(mode="json") for finding in ai.validation_findings],
                    },
                )
                add_edge(ai_id, item.id, "enriches_review", ai.confidence)

        for source in self.store.sources.values():
            if not visible(source.sensitivity):
                hidden.add(source.source_id)
                continue
            version_count = len(self.store.list_source_versions(source.source_id))
            chunk_count = len(self.store.list_evidence_chunks(source_id=source.source_id))
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
                    "owner": source.owner,
                    "submitted_by": source.submitted_by,
                    "content_excerpt": source.content_excerpt,
                    "content_hash": source.content_hash,
                    "current_version_id": source.current_version_id,
                    "version_count": version_count,
                    "chunk_count": chunk_count,
                },
            )

        for obj in self.store.knowledge_objects.values():
            add_object_node(obj)

        if include_review_items:
            for item in self.store.review_items.values():
                add_object_node(item.candidate_object, node_type="candidate_object")
                add_review_node(item)

        for relationship in self.store.relationships.values():
            if relationship.status != ReviewStatus.published:
                continue
            source_obj = self.store.knowledge_objects.get(relationship.source_object_id)
            target_obj = self.store.knowledge_objects.get(relationship.target_object_id)
            if source_obj is not None and not visible(source_obj.sensitivity):
                continue
            if target_obj is not None and not visible(target_obj.sensitivity):
                continue
            add_edge(
                relationship.source_object_id,
                relationship.target_object_id,
                relationship.relationship_type,
                relationship.confidence,
                {
                    "relationship_id": relationship.id,
                    "approved_by": relationship.approved_by,
                    "evidence_refs": [reference.model_dump(mode="json") for reference in relationship.evidence_refs],
                },
            )

        visible_edges = [
            edge
            for edge in edges.values()
            if edge.source not in hidden and edge.target not in hidden
        ]
        return BrainGraph(nodes=list(nodes.values()), edges=visible_edges)
