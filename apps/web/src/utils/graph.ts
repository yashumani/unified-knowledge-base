import type { BrainGraph, GraphEdge, GraphNode, KnowledgeObject, ReviewItem } from "../types";

function objectToNode(object: KnowledgeObject, typeOverride?: string): GraphNode {
  return {
    id: object.id,
    label: object.title,
    type: typeOverride ?? object.type,
    domain: object.domain,
    status: object.status,
    sensitivity: object.sensitivity,
    confidence: object.confidence,
    metadata: object
  };
}

export function buildGraphFromState(objects: KnowledgeObject[], reviewItems: ReviewItem[]): BrainGraph {
  const nodes = new Map<string, GraphNode>();
  const edges = new Map<string, GraphEdge>();

  const addEdge = (source: string | undefined, target: string | undefined, type: string, confidence = 0.5) => {
    if (!source || !target || source === target) return;
    const id = `${source}::${type}::${target}`;
    edges.set(id, { id, source, target, type, confidence, metadata: {} });
  };

  for (const object of objects) {
    nodes.set(object.id, objectToNode(object));
    for (const sourceId of object.source_ids) {
      const sourceNodeId = `source:${sourceId}`;
      if (!nodes.has(sourceNodeId)) {
        nodes.set(sourceNodeId, {
          id: sourceNodeId,
          label: sourceId,
          type: "source_evidence",
          domain: object.domain,
          status: "evidence",
          sensitivity: object.sensitivity,
          confidence: 1,
          metadata: { source_id: sourceId }
        });
      }
      addEdge(sourceNodeId, object.id, "evidence_for", object.confidence);
    }
    for (const relationship of object.relationships) {
      addEdge(object.id, relationship.target_id, relationship.type, relationship.confidence);
    }
  }

  for (const item of reviewItems) {
    nodes.set(item.id, {
      id: item.id,
      label: `Review: ${item.candidate_object.title}`,
      type: "review_item",
      domain: item.candidate_object.domain,
      status: item.status,
      sensitivity: item.candidate_object.sensitivity,
      confidence: item.candidate_object.confidence,
      metadata: item
    });
    nodes.set(item.candidate_object.id, objectToNode(item.candidate_object, "candidate_object"));
    addEdge(item.id, item.candidate_object.id, "reviews", item.candidate_object.confidence);
    addEdge(`source:${item.source_id}`, item.id, "submitted_as", 0.5);
  }

  return {
    nodes: [...nodes.values()],
    edges: [...edges.values()],
    generated_at: new Date().toISOString()
  };
}
