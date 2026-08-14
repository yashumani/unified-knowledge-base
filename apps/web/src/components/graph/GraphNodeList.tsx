import type { GraphNode } from "../../types";

/**
 * Keyboard-operable equivalent of the SVG canvas.
 *
 * The graph was role="img" with a single static label, and its nodes handled
 * click and hover on <g> elements with no tabIndex, role or key handling — so
 * it was completely unreachable without a mouse. This list is the guaranteed
 * path; the SVG nodes are additionally focusable, but a real list of buttons
 * is what makes the content navigable.
 */
export function GraphNodeList({
  nodes,
  selectedId,
  onSelect
}: {
  nodes: GraphNode[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="graph-node-list">
      <h3 id="graph-node-list-heading">Nodes ({nodes.length})</h3>
      {nodes.length === 0 ? (
        <p className="empty-state">No nodes match the current filter.</p>
      ) : (
        <ul aria-labelledby="graph-node-list-heading">
          {nodes.map((node) => (
            <li key={node.id}>
              <button
                type="button"
                aria-pressed={selectedId === node.id}
                className={selectedId === node.id ? "is-selected" : undefined}
                onClick={() => onSelect(node.id)}
              >
                <span className={`legend-swatch node-${node.type.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} aria-hidden="true" />
                <span className="node-list-label">{node.label}</span>
                <small>{node.type.replace(/_/g, " ")}</small>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
