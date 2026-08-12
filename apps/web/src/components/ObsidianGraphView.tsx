import { useEffect, useMemo, useState, type PointerEvent, type WheelEvent } from "react";
import type { BrainGraph, GraphNode } from "../types";

interface Props {
  graph: BrainGraph;
}

type FilterMode = "all" | "published" | "review" | "sources";

type LayoutNode = GraphNode & {
  x: number;
  y: number;
  degree: number;
};

function nodeCategory(type: string): string {
  return type.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

function nodeTypeRank(type: string): number {
  const normalized = nodeCategory(type);
  if (normalized.includes("source")) return 0;
  if (normalized.includes("review")) return 1;
  if (normalized.includes("candidate")) return 2;
  if (normalized.includes("metric")) return 3;
  if (normalized.includes("report")) return 4;
  if (normalized.includes("rule")) return 5;
  return 6;
}

function buildNeighborhood(graph: BrainGraph, activeId: string | null): Set<string> {
  const ids = new Set<string>();
  if (!activeId) return ids;
  ids.add(activeId);
  for (const edge of graph.edges) {
    if (edge.source === activeId) ids.add(edge.target);
    if (edge.target === activeId) ids.add(edge.source);
  }
  return ids;
}

export function ObsidianGraphView({ graph }: Props) {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<FilterMode>("all");
  const [selectedId, setSelectedId] = useState<string | null>(graph.nodes[0]?.id ?? null);
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [localOnly, setLocalOnly] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    if (!graph.nodes.length) {
      setSelectedId(null);
      return;
    }
    if (!selectedId || !graph.nodes.some((node) => node.id === selectedId)) {
      setSelectedId(graph.nodes[0].id);
    }
  }, [graph.nodes, selectedId]);

  const degree = useMemo(() => {
    const counts = new Map<string, number>();
    for (const edge of graph.edges) {
      counts.set(edge.source, (counts.get(edge.source) ?? 0) + 1);
      counts.set(edge.target, (counts.get(edge.target) ?? 0) + 1);
    }
    return counts;
  }, [graph.edges]);

  const layout = useMemo(() => {
    const sorted = [...graph.nodes].sort((a, b) => {
      const rankDelta = nodeTypeRank(a.type) - nodeTypeRank(b.type);
      if (rankDelta !== 0) return rankDelta;
      return a.label.localeCompare(b.label);
    });

    const grouped = new Map<number, GraphNode[]>();
    for (const node of sorted) {
      const rank = nodeTypeRank(node.type);
      grouped.set(rank, [...(grouped.get(rank) ?? []), node]);
    }

    const center = { x: 500, y: 310 };
    const output = new Map<string, LayoutNode>();
    for (const [rank, nodes] of grouped.entries()) {
      const radius = rank === 3 ? 110 : 130 + rank * 42;
      const start = rank * 0.53;
      nodes.forEach((node, index) => {
        const angle = start + (index / Math.max(nodes.length, 1)) * Math.PI * 2;
        output.set(node.id, {
          ...node,
          x: center.x + Math.cos(angle) * radius,
          y: center.y + Math.sin(angle) * radius,
          degree: degree.get(node.id) ?? 0
        });
      });
    }
    return output;
  }, [degree, graph.nodes]);

  const activeId = hoverId ?? selectedId;
  const neighborhood = useMemo(() => buildNeighborhood(graph, activeId), [activeId, graph]);

  const visibleNodes = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return [...layout.values()].filter((node) => {
      if (localOnly && selectedId && !neighborhood.has(node.id)) return false;
      if (mode === "published" && node.status !== "published") return false;
      if (mode === "review" && !["review_item", "candidate_object"].includes(node.type)) return false;
      if (mode === "sources" && node.type !== "source_evidence") return false;
      if (!normalizedQuery) return true;
      const text = `${node.label} ${node.type} ${node.domain ?? ""} ${node.status ?? ""}`.toLowerCase();
      return text.includes(normalizedQuery);
    });
  }, [layout, localOnly, mode, neighborhood, query, selectedId]);

  const visibleIds = useMemo(() => new Set(visibleNodes.map((node) => node.id)), [visibleNodes]);
  const visibleEdges = graph.edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target));
  const selectedNode = selectedId ? layout.get(selectedId) : undefined;

  const handleWheel = (event: WheelEvent<SVGSVGElement>) => {
    event.preventDefault();
    const direction = event.deltaY > 0 ? -0.08 : 0.08;
    setZoom((value) => Math.min(2.4, Math.max(0.45, Number((value + direction).toFixed(2)))));
  };

  const handlePointerDown = (event: PointerEvent<SVGSVGElement>) => {
    setDragStart({ x: event.clientX - pan.x, y: event.clientY - pan.y });
  };

  const handlePointerMove = (event: PointerEvent<SVGSVGElement>) => {
    if (!dragStart) return;
    setPan({ x: event.clientX - dragStart.x, y: event.clientY - dragStart.y });
  };

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setLocalOnly(false);
  };

  return (
    <section className="graph-card">
      <div className="graph-toolbar">
        <div>
          <p className="eyebrow">Obsidian-style graph</p>
          <h2>AI Brain Map</h2>
        </div>
        <div className="graph-controls">
          <input
            type="search"
            placeholder="Filter nodes..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <select value={mode} onChange={(event) => setMode(event.target.value as FilterMode)}>
            <option value="all">All nodes</option>
            <option value="published">Published</option>
            <option value="review">Review/candidates</option>
            <option value="sources">Sources</option>
          </select>
          <button type="button" onClick={() => setLocalOnly((value) => !value)} className={localOnly ? "active" : ""}>
            Local graph
          </button>
          <button type="button" onClick={() => setZoom((value) => Math.min(2.4, value + 0.15))}>+</button>
          <button type="button" onClick={() => setZoom((value) => Math.max(0.45, value - 0.15))}>−</button>
          <button type="button" onClick={resetView}>Reset</button>
        </div>
      </div>

      <div className="graph-layout">
        <svg
          className="brain-graph"
          role="img"
          aria-label="AI Brain relationship graph"
          viewBox="0 0 1000 620"
          onWheel={handleWheel}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={() => setDragStart(null)}
          onPointerLeave={() => {
            setDragStart(null);
            setHoverId(null);
          }}
        >
          <rect className="graph-background" x="0" y="0" width="1000" height="620" />
          <g transform={`translate(${pan.x} ${pan.y}) scale(${zoom})`}>
            {visibleEdges.map((edge) => {
              const source = layout.get(edge.source);
              const target = layout.get(edge.target);
              if (!source || !target) return null;
              const isActive = activeId ? edge.source === activeId || edge.target === activeId : false;
              return (
                <g key={edge.id} className={isActive ? "edge active" : "edge"}>
                  <line x1={source.x} y1={source.y} x2={target.x} y2={target.y} />
                  {isActive && (
                    <text x={(source.x + target.x) / 2} y={(source.y + target.y) / 2 - 6}>
                      {edge.type}
                    </text>
                  )}
                </g>
              );
            })}

            {visibleNodes.map((node) => {
              const size = 12 + Math.min(node.degree, 5) * 3;
              const isActive = activeId ? neighborhood.has(node.id) : false;
              const category = nodeCategory(node.type);
              return (
                <g
                  key={node.id}
                  className={`graph-node node-${category} ${isActive ? "active" : ""} ${selectedId === node.id ? "selected" : ""}`}
                  transform={`translate(${node.x} ${node.y})`}
                  onMouseEnter={() => setHoverId(node.id)}
                  onMouseLeave={() => setHoverId(null)}
                  onClick={() => setSelectedId(node.id)}
                >
                  <circle r={size} />
                  <text y={size + 16}>{node.label}</text>
                </g>
              );
            })}
          </g>
        </svg>

        <aside className="node-panel">
          {selectedNode ? (
            <>
              <p className="eyebrow">Selected node</p>
              <h3>{selectedNode.label}</h3>
              <dl>
                <div><dt>Type</dt><dd>{selectedNode.type}</dd></div>
                <div><dt>Status</dt><dd>{selectedNode.status ?? "unknown"}</dd></div>
                <div><dt>Domain</dt><dd>{selectedNode.domain ?? "general"}</dd></div>
                <div><dt>Confidence</dt><dd>{selectedNode.confidence ? Math.round(selectedNode.confidence * 100) + "%" : "n/a"}</dd></div>
              </dl>
              <pre>{JSON.stringify(selectedNode.metadata, null, 2)}</pre>
            </>
          ) : (
            <div className="empty-state">Select a node to inspect its evidence, status, and relationships.</div>
          )}
        </aside>
      </div>
    </section>
  );
}
