import { useEffect, useMemo, useRef, useState, type PointerEvent } from "react";
import { GraphLegend } from "./graph/GraphLegend";
import { GraphNodeList } from "./graph/GraphNodeList";
import { formatRelative } from "../utils/format";
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
  const svgRef = useRef<SVGSVGElement | null>(null);

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

  /**
   * Zoom is bound to ctrl/meta + wheel and attached natively.
   *
   * React's synthetic wheel handler is registered passively at the root, so the
   * previous preventDefault() logged a warning and did nothing — the page
   * scrolled while the graph zoomed. Gating on a modifier also matters now that
   * the graph sits inside a long scrolling page: a plain wheel must scroll past
   * it, not trap the pointer.
   */
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const onWheel = (event: globalThis.WheelEvent) => {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      const direction = event.deltaY > 0 ? -0.08 : 0.08;
      setZoom((value) => Math.min(2.4, Math.max(0.45, Number((value + direction).toFixed(2)))));
    };
    svg.addEventListener("wheel", onWheel, { passive: false });
    return () => svg.removeEventListener("wheel", onWheel);
  }, []);

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
    // Reset previously left the search query and filter mode alone, so pressing
    // it on a filtered graph still showed an empty canvas.
    setQuery("");
    setMode("all");
  };

  const filtersActive = query.trim() !== "" || mode !== "all" || localOnly;

  return (
    <section className="graph-card">
      <div className="graph-toolbar">
        <div>
          <p className="eyebrow">Obsidian-style graph</p>
          <h2>AI Brain Map</h2>
        </div>
        <div className="graph-controls">
          <label className="visually-hidden" htmlFor="graph-filter">Filter nodes by name</label>
          <input
            id="graph-filter"
            type="search"
            placeholder="Filter nodes..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <label className="visually-hidden" htmlFor="graph-mode">Limit to node type</label>
          <select
            id="graph-mode"
            value={mode}
            onChange={(event) => setMode(event.target.value as FilterMode)}
          >
            <option value="all">All nodes</option>
            <option value="published">Published</option>
            <option value="review">Review/candidates</option>
            <option value="sources">Sources</option>
          </select>
          <button
            type="button"
            onClick={() => setLocalOnly((value) => !value)}
            className={localOnly ? "active" : ""}
            aria-pressed={localOnly}
          >
            Local graph
          </button>
          <button type="button" aria-label="Zoom in" onClick={() => setZoom((value) => Math.min(2.4, value + 0.15))}>+</button>
          <button type="button" aria-label="Zoom out" onClick={() => setZoom((value) => Math.max(0.45, value - 0.15))}>−</button>
          <button type="button" onClick={resetView}>Reset</button>
        </div>
      </div>

      <GraphLegend />
      <p className="graph-hint">
        Hover or select a node to highlight its relationships. Hold Ctrl and scroll to zoom;
        drag to pan. Every node is also listed beside the canvas for keyboard use.
      </p>

      <div className="graph-layout">
        <div className="graph-canvas-column">
          <svg
          ref={svgRef}
          className="brain-graph"
          role="img"
          aria-label={`AI Brain relationship graph, ${visibleNodes.length} nodes shown. A keyboard-navigable list of the same nodes follows.`}
          viewBox="0 0 1000 620"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={() => setDragStart(null)}
          onPointerLeave={() => {
            setDragStart(null);
            setHoverId(null);
          }}
        >
          <rect className="graph-background" x="0" y="0" width="1000" height="620" />
          {visibleNodes.length === 0 && (
            <text className="graph-empty" x="500" y="300" textAnchor="middle">
              No nodes match the current filter.
            </text>
          )}
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
                  tabIndex={0}
                  role="button"
                  aria-label={`${node.label}, ${node.type.replace(/_/g, " ")}`}
                  onMouseEnter={() => setHoverId(node.id)}
                  onMouseLeave={() => setHoverId(null)}
                  onFocus={() => setHoverId(node.id)}
                  onBlur={() => setHoverId(null)}
                  onClick={() => setSelectedId(node.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelectedId(node.id);
                    }
                  }}
                >
                  <circle r={size} />
                  <text y={size + 16}>{node.label}</text>
                </g>
              );
            })}
          </g>
          </svg>
          <GraphNodeList
            nodes={visibleNodes}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </div>

        <aside className="node-panel">
          {visibleNodes.length === 0 && filtersActive && (
            <div className="empty-state">
              <p>Nothing matches those filters.</p>
              <button type="button" className="secondary" onClick={resetView}>Clear filters</button>
            </div>
          )}

          {selectedNode ? (
            <>
              <h3>
                <span className="step-kicker">Selected node</span>
                {selectedNode.label}
              </h3>
              <dl>
                <div><dt>Type</dt><dd>{selectedNode.type.replace(/_/g, " ")}</dd></div>
                <div><dt>Status</dt><dd>{selectedNode.status ?? "unknown"}</dd></div>
                <div><dt>Domain</dt><dd>{selectedNode.domain ?? "general"}</dd></div>
                <div><dt>Sensitivity</dt><dd>{selectedNode.sensitivity ?? "unknown"}</dd></div>
                <div><dt>Connections</dt><dd>{selectedNode.degree}</dd></div>
              </dl>
              <NodeMetadata metadata={selectedNode.metadata} />
              {/* The raw dump is still reachable, but it is no longer the
                  primary way to read a node. */}
              <details className="node-raw">
                <summary>Raw metadata</summary>
                <pre>{JSON.stringify(selectedNode.metadata, null, 2)}</pre>
              </details>
            </>
          ) : (
            <div className="empty-state">Select a node to inspect its evidence, status, and relationships.</div>
          )}
        </aside>
      </div>
    </section>
  );
}

/** Renders the handful of metadata fields worth reading as prose. */
function NodeMetadata({ metadata }: { metadata: unknown }) {
  if (!metadata || typeof metadata !== "object") return null;
  const data = metadata as Record<string, unknown>;
  const summary = typeof data.summary === "string" ? data.summary : null;
  const excerpt = typeof data.content_excerpt === "string" ? data.content_excerpt : null;
  const owner = typeof data.owner === "string" ? data.owner : null;
  const submittedBy = typeof data.submitted_by === "string" ? data.submitted_by : null;
  const createdAt = typeof data.created_at === "string" ? data.created_at : null;
  const reviewer = typeof data.reviewer === "string" ? data.reviewer : null;
  const brief = typeof data.ai_review_brief === "string" ? data.ai_review_brief : null;

  if (!summary && !excerpt && !owner && !submittedBy && !createdAt && !reviewer && !brief) {
    return null;
  }

  return (
    <div className="node-detail">
      {summary && <p>{summary}</p>}
      {excerpt && <blockquote>{excerpt}</blockquote>}
      {brief && (
        <p className="node-detail-brief"><strong>AI brief:</strong> {brief}</p>
      )}
      <dl>
        {owner && <div><dt>Owner</dt><dd>{owner}</dd></div>}
        {submittedBy && <div><dt>Submitted by</dt><dd>{submittedBy}</dd></div>}
        {reviewer && <div><dt>Reviewer</dt><dd>{reviewer}</dd></div>}
        {createdAt && <div><dt>Created</dt><dd>{formatRelative(createdAt)}</dd></div>}
      </dl>
    </div>
  );
}
