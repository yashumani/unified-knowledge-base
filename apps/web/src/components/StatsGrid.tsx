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
  graphEdges
}: {
  published: number;
  review: number;
  enrichedReviews: number;
  graphEdges: number;
}) {
  return (
    <section className="stats-grid" aria-label="Brain state summary">
      <Metric label="Published objects" value={published} detail="approved runtime context" />
      <Metric label="Review queue" value={review} detail="awaiting validation" />
      <Metric label="AI enriched" value={enrichedReviews} detail="review briefs attached" />
      <Metric label="Graph edges" value={graphEdges} detail="typed relationships" />
    </section>
  );
}
