import type { WorkspacePage } from "./WorkspaceApp";

interface StageCard {
  key: "ingest" | "enrich" | "review" | "publish" | "compose";
  number: string;
  label: string;
  verb: string;
  detail: string;
  state: "complete" | "current" | "ready" | "waiting";
  count: number;
}

const UTILITY_CARDS: Array<{
  page: WorkspacePage;
  label: string;
  detail: string;
  symbol: string;
}> = [
  { page: "memory", label: "Memory map", detail: "Trace source evidence, candidates and approved relationships.", symbol: "◇" },
  { page: "activity", label: "Governance trail", detail: "Inspect who decided what, when and why.", symbol: "≡" },
  { page: "help", label: "Help center", detail: "Open the full workflow guide, FAQ and troubleshooting.", symbol: "?" }
];

export function DashboardHome({
  stages,
  stats,
  demoMode,
  onNavigate
}: {
  stages: StageCard[];
  stats: { review: number; published: number; graph: number; provider: string };
  demoMode: boolean;
  onNavigate: (page: WorkspacePage) => void;
}) {
  const brandMarkUrl = `${import.meta.env.BASE_URL}ai-brain-mark.svg`;

  return (
    <section className="dashboard-home" aria-labelledby="dashboard-title">
      <header className="dashboard-heading">
        <div>
          <p>Unified Knowledge Base</p>
          <h1 id="dashboard-title" tabIndex={-1}>Build, govern and recall AI memory.</h1>
          <span>
            Choose a page instead of scrolling through a long console. Your workflow status stays
            visible across every page.
          </span>
        </div>
        <div className="dashboard-status-card">
          <div className="dashboard-brain-visual" aria-hidden="true">
            <span className="dashboard-orbit orbit-one" />
            <span className="dashboard-orbit orbit-two" />
            <span className="dashboard-orbit orbit-three" />
            <img src={brandMarkUrl} alt="" />
          </div>
          <div className="dashboard-runtime-copy">
            <span className={demoMode ? "connection-dot is-demo" : "connection-dot"} />
            <div>
              <strong>{demoMode ? "Safe browser demo" : "Connected workspace"}</strong>
              <small>{demoMode ? "Everything works; nothing persists" : "Actions are stored and audited"}</small>
            </div>
          </div>
          <div className="dashboard-pulse-bars" aria-hidden="true"><i /><i /><i /><i /><i /></div>
        </div>
      </header>

      <div className="dashboard-grid" aria-label="Workspace pages">
        {stages.map((stage, index) => (
          <button
            type="button"
            key={stage.key}
            className={`dashboard-tile stage-tile tone-${index + 1} is-${stage.state}`}
            onClick={() => onNavigate(stage.key)}
          >
            <header>
              <span>{stage.number}</span>
              <small>{stage.state === "complete" ? "Complete" : stage.state === "ready" ? "Ready" : stage.state === "current" ? "Open" : "Waiting"}</small>
            </header>
            <div>
              <h2>{stage.label}</h2>
              <strong>{stage.verb}</strong>
              <p>{stage.detail}</p>
            </div>
            <footer>
              <span>{stage.count} items</span>
              <b aria-hidden="true">↗</b>
            </footer>
          </button>
        ))}

        {UTILITY_CARDS.map((card) => (
          <button
            type="button"
            key={card.page}
            className="dashboard-tile utility-tile"
            onClick={() => onNavigate(card.page)}
          >
            <header><span>{card.symbol}</span><small>Workspace tool</small></header>
            <div>
              <h2>{card.label}</h2>
              <p>{card.detail}</p>
            </div>
            <footer><span>Open page</span><b aria-hidden="true">↗</b></footer>
          </button>
        ))}
      </div>

      <aside className="dashboard-signal-strip" aria-label="Current brain signals">
        <div><span>Review queue</span><strong>{stats.review}</strong></div>
        <div><span>Published memory</span><strong>{stats.published}</strong></div>
        <div><span>Graph nodes</span><strong>{stats.graph}</strong></div>
        <div><span>Local enrichment</span><strong>{stats.provider}</strong></div>
      </aside>
    </section>
  );
}
