const workflowSteps = [
  { label: "Submit", detail: "Capture source context" },
  { label: "Enrich", detail: "AI review brief + checks" },
  { label: "Review", detail: "Human approval gate" },
  { label: "Publish", detail: "Approved brain object" },
  { label: "Compose", detail: "Context pack for AI apps" }
];

export function Hero({
  demoMode,
  environment,
  apiBase,
  loading,
  onRefresh
}: {
  demoMode: boolean;
  environment: string;
  apiBase: string;
  loading: boolean;
  onRefresh: () => void;
}) {
  return (
    <header className="hero framer-hero">
      <div className="hero-content">
        <p className="eyebrow">Framer-inspired enterprise SaaS console</p>
        <h1>Governed AI Brain command center</h1>
        <p className="hero-copy">
          A dashboard-led workspace for submitting context, enriching candidates with AI review briefs,
          publishing approved brain objects, and exploring the knowledge graph behind every context pack.
        </p>
        <div className="hero-actions">
          <button
            type="button"
            onClick={() =>
              document.getElementById("context-ingestion")?.scrollIntoView({ behavior: "smooth" })
            }
          >
            Start workflow
          </button>
          <a className="secondary-link" href="#brain-map">Explore graph</a>
        </div>
      </div>

      <div className="hero-dashboard-card" aria-label="Brain runtime status">
        <div className="status-card elevated">
          <span className={demoMode ? "pulse warning" : "pulse"} />
          <div>
            <strong>{demoMode ? "Demo Mode" : "Connected Backend"}</strong>
            <span>{demoMode ? "Simulated local state" : `${apiBase} · ${environment}`}</span>
          </div>
          <button type="button" onClick={onRefresh} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        <div className="workflow-timeline">
          {workflowSteps.map((step, index) => (
            <div className="timeline-step" key={step.label}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div>
                <strong>{step.label}</strong>
                <small>{step.detail}</small>
              </div>
            </div>
          ))}
        </div>
      </div>
    </header>
  );
}
