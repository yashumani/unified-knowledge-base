function Metric({ label, value, detail }: { label: string; value: number; detail: string }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

export function StatsGrid({
  published,
  review,
  enrichedReviews,
  graphNodes,
  graphEdges
}: {
  published: number;
  review: number;
  enrichedReviews: number;
  graphNodes: number;
  graphEdges: number;
}) {
  return (
    <section className="stats-grid" aria-label="Brain state summary">
      <Metric label="Published objects" value={published} detail="approved runtime context" />
      <Metric label="Review queue" value={review} detail="awaiting validation" />
      <Metric label="AI enriched" value={enrichedReviews} detail="review briefs attached" />
      {/* graphNodes was computed and thrown away, while the docs promise it. */}
      <Metric label="Graph nodes" value={graphNodes} detail="sources, candidates, objects" />
      <Metric label="Graph edges" value={graphEdges} detail="typed relationships" />
    </section>
  );
}
