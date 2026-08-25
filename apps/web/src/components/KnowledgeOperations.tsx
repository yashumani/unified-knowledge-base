import { useEffect, useMemo, useState } from "react";

type OperationsStatus = {
  tenant_id: string;
  subject: string;
  auth_method: string;
  quality_assessments: number;
  quarantined_sources: number;
  active_assignments: number;
  active_subscriptions: number;
  retrieval_feedback: number;
  capabilities: string[];
};

type KnowledgeOperationsProps = {
  onBack: () => void;
};

const demoStatus: OperationsStatus = {
  tenant_id: "synthetic-pilot",
  subject: "demo.governance.admin",
  auth_method: "browser-demo",
  quality_assessments: 18,
  quarantined_sources: 2,
  active_assignments: 6,
  active_subscriptions: 4,
  retrieval_feedback: 27,
  capabilities: [
    "oidc_tenant_context",
    "knowledge_quality_firewall",
    "review_assignments",
    "continuous_source_refresh",
    "explainable_reranking",
    "retrieval_evaluation",
  ],
};

const priorityCards = [
  {
    number: "01",
    title: "Private identity",
    accent: "lime",
    description: "Tenant, roles, groups, clearance, and authentication method travel with every governed operation.",
    metric: (status: OperationsStatus) => status.auth_method,
    label: "active identity mode",
  },
  {
    number: "02",
    title: "Quality firewall",
    accent: "coral",
    description: "Deterministic screening catches secrets, injection language, missing ownership, and weak source context before Ollama.",
    metric: (status: OperationsStatus) => String(status.quarantined_sources),
    label: "quarantined or rejected",
  },
  {
    number: "03",
    title: "Reviewer operations",
    accent: "lavender",
    description: "Assignments, due dates, priorities, questions, responses, and workload make human governance operational.",
    metric: (status: OperationsStatus) => String(status.active_assignments),
    label: "active assignments",
  },
  {
    number: "04",
    title: "Continuous refresh",
    accent: "cobalt",
    description: "Scheduled connector subscriptions compare checksums and create new review candidates only when evidence changes.",
    metric: (status: OperationsStatus) => String(status.active_subscriptions),
    label: "active subscriptions",
  },
  {
    number: "05",
    title: "Recall evaluation",
    accent: "sun",
    description: "Explainable ranking factors, golden cases, abstention checks, and feedback expose why memory was selected.",
    metric: (status: OperationsStatus) => String(status.retrieval_feedback),
    label: "feedback observations",
  },
] as const;

export function KnowledgeOperations({ onBack }: KnowledgeOperationsProps) {
  const [status, setStatus] = useState<OperationsStatus>(demoStatus);
  const [connection, setConnection] = useState<"checking" | "connected" | "demo">("checking");
  const [message, setMessage] = useState("Checking for a governed private runtime…");

  const apiBase = String(import.meta.env.VITE_UKB_API_BASE_URL || "").replace(/\/$/, "");
  const apiToken = String(import.meta.env.VITE_UKB_API_TOKEN || "");

  useEffect(() => {
    if (!apiBase || !apiToken) {
      setConnection("demo");
      setMessage("Synthetic preview. Connect the private v0.5 API to display tenant-filtered operational state.");
      return;
    }
    const controller = new AbortController();
    fetch(`${apiBase}/v1/knowledge-operations/status`, {
      headers: { Authorization: `Bearer ${apiToken}` },
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Runtime returned ${response.status}`);
        return response.json() as Promise<OperationsStatus>;
      })
      .then((payload) => {
        setStatus(payload);
        setConnection("connected");
        setMessage("Live tenant-filtered operational state from the governed API.");
      })
      .catch((error: Error) => {
        if (error.name === "AbortError") return;
        setConnection("demo");
        setMessage(`Private runtime unavailable (${error.message}). Showing synthetic operational state.`);
      });
    return () => controller.abort();
  }, [apiBase, apiToken]);

  const completed = useMemo(
    () => priorityCards.filter((card) => status.capabilities.includes(capabilityFor(card.number))).length,
    [status.capabilities],
  );

  return (
    <main className="ops-shell" id="main-content">
      <header className="ops-topbar">
        <button type="button" className="ops-back" onClick={onBack}>← AI Brain workspace</button>
        <div className="ops-brand">
          <span className="ops-brand-mark">UKB</span>
          <span>Knowledge Operations</span>
        </div>
        <span className={`ops-connection ops-connection--${connection}`}>{connection}</span>
      </header>

      <section className="ops-hero" aria-labelledby="ops-title">
        <div>
          <p className="ops-kicker">Governed Knowledge Supply Chain · v0.5</p>
          <h1 id="ops-title">Operate the brain.<br />Not just the model.</h1>
          <p className="ops-lede">
            Five control planes turn raw context into trustworthy, continuously maintained memory:
            identity, quality, people, sources, and recall.
          </p>
        </div>
        <aside className="ops-runtime-card" aria-label="Runtime status">
          <div className="ops-runtime-score"><strong>{completed}/5</strong><span>capabilities active</span></div>
          <dl>
            <div><dt>Tenant</dt><dd>{status.tenant_id}</dd></div>
            <div><dt>Principal</dt><dd>{status.subject}</dd></div>
            <div><dt>Quality checks</dt><dd>{status.quality_assessments}</dd></div>
          </dl>
          <p>{message}</p>
        </aside>
      </section>

      <section className="ops-priority-grid" aria-label="Knowledge operations priorities">
        {priorityCards.map((card) => (
          <article className={`ops-priority ops-priority--${card.accent}`} key={card.number}>
            <span className="ops-priority-number">{card.number}</span>
            <div className="ops-priority-copy">
              <h2>{card.title}</h2>
              <p>{card.description}</p>
            </div>
            <div className="ops-priority-metric">
              <strong>{card.metric(status)}</strong>
              <span>{card.label}</span>
            </div>
          </article>
        ))}
      </section>

      <section className="ops-flow" aria-labelledby="ops-flow-title">
        <div className="ops-flow-heading">
          <p className="ops-kicker">The operating loop</p>
          <h2 id="ops-flow-title">Every source earns its place in memory.</h2>
        </div>
        <ol className="ops-flow-track">
          {[
            ["Collect", "Connector or contributor submits evidence"],
            ["Screen", "Quality firewall accepts, warns, quarantines, or rejects"],
            ["Enrich", "Local Ollama proposes structure and review guidance"],
            ["Govern", "Assigned humans discuss, approve, and publish"],
            ["Recall", "Authorized reranking returns cited context and coverage"],
            ["Learn", "Feedback and refresh cycles improve the next decision"],
          ].map(([title, body], index) => (
            <li key={title}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div><strong>{title}</strong><p>{body}</p></div>
            </li>
          ))}
        </ol>
      </section>

      <section className="ops-live-boundary">
        <div>
          <p className="ops-kicker">Live testing boundary</p>
          <h2>GitHub Pages shows the operator experience. The private API performs the governed work.</h2>
        </div>
        <div className="ops-boundary-grid">
          <div><strong>Available here</strong><p>Responsive dashboard, workflow explanation, demo state, and direct navigation.</p></div>
          <div><strong>Requires private runtime</strong><p>OIDC, durable PostgreSQL state, Ollama, connector refresh, real assignments, and retrieval evaluation.</p></div>
        </div>
      </section>
    </main>
  );
}

function capabilityFor(number: string): string {
  return ({
    "01": "oidc_tenant_context",
    "02": "knowledge_quality_firewall",
    "03": "review_assignments",
    "04": "continuous_source_refresh",
    "05": "explainable_reranking",
  } as Record<string, string>)[number];
}
