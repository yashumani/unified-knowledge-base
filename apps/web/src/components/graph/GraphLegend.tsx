/**
 * Node types were encoded purely in colour with no legend anywhere in the app,
 * so the encoding was undiscoverable and unusable to anyone who cannot
 * distinguish the hues. Each entry names its category and pairs the swatch
 * with a shape cue.
 */
const LEGEND = [
  { category: "source-evidence", label: "Source evidence", shape: "ring" },
  { category: "review-item", label: "Review item", shape: "dashed" },
  { category: "candidate-object", label: "Candidate", shape: "dashed" },
  { category: "metric", label: "Metric", shape: "solid" },
  { category: "report", label: "Report", shape: "solid" },
  { category: "businessrule", label: "Business rule", shape: "solid" },
  { category: "ai-enrichment", label: "AI brief", shape: "ring" }
];

export function GraphLegend() {
  return (
    <ul className="graph-legend" aria-label="Node types">
      {LEGEND.map((entry) => (
        <li key={entry.category}>
          <span className={`legend-swatch node-${entry.category} shape-${entry.shape}`} aria-hidden="true" />
          {entry.label}
        </li>
      ))}
    </ul>
  );
}
