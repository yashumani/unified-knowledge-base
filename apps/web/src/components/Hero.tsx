/**
 * The five-step timeline that used to live here was static decoration — five
 * identical cards bound to nothing. The real stepper in the sticky rail
 * replaces it, so the hero now only introduces the product and reports the
 * connection state.
 */
export function Hero({
  demoMode,
  environment,
  apiBase,
  loading,
  onRefresh,
  onStart
}: {
  demoMode: boolean;
  environment: string;
  apiBase: string;
  loading: boolean;
  onRefresh: () => void;
  onStart: () => void;
}) {
  return (
    <header className="hero framer-hero">
      <div className="hero-content">
        <p className="eyebrow">Governed context runtime</p>
        <h1>Knowledge an AI app is allowed to use</h1>
        <p className="hero-copy">
          Raw context becomes a candidate, a human approves it, and only then can it reach an
          AI application. Walk the five steps below to see how a governed brain is built —
          and what it refuses to do.
        </p>
        <div className="hero-actions">
          <button type="button" onClick={onStart}>Start at step 1</button>
          <a className="secondary-link" href="#brain-map">Skip to the graph</a>
        </div>
      </div>

      <div className="hero-dashboard-card">
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
        <p className="hero-aside">
          The graph at the end of the walk is the same brain you will have built by then —
          sources, candidates, review state and approved objects, with the edges between them.
        </p>
      </div>
    </header>
  );
}
