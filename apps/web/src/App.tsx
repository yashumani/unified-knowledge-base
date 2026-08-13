import { useEffect, useMemo, useState, type FormEvent } from "react";
import { API_BASE, brainClient } from "./api/brainClient";
import { demoContextPack, demoGraph, demoObjects, demoReviewItems } from "./data/demoBrain";
import { ObsidianGraphView } from "./components/ObsidianGraphView";
import { buildGraphFromState } from "./utils/graph";
import type {
  AIProviderStatus,
  BrainGraph,
  ContextPack,
  ContextPackRequest,
  IngestionPayload,
  KnowledgeObject,
  ReviewItem,
  SourceType
} from "./types";

const reviewer = "ui.reviewer";

const workflowSteps = [
  { label: "Submit", detail: "Capture source context" },
  { label: "Enrich", detail: "AI review brief + checks" },
  { label: "Review", detail: "Human approval gate" },
  { label: "Publish", detail: "Approved brain object" },
  { label: "Compose", detail: "Context pack for AI apps" }
];

const navItems = [
  { label: "Map", href: "#brain-map" },
  { label: "Submit", href: "#context-ingestion" },
  { label: "Review", href: "#review-queue" },
  { label: "Context Pack", href: "#context-pack" },
  { label: "Published", href: "#published-objects" }
];

const demoAIStatus: AIProviderStatus = {
  provider: "noop",
  mode: "offline_no_model",
  enabled: true,
  model: "deterministic",
  embedding_model: "embeddinggemma",
  base_url: null,
  hosted_allowed_for_restricted: false
};

export default function App() {
  const [environment, setEnvironment] = useState("unknown");
  const [demoMode, setDemoMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>([]);
  const [objects, setObjects] = useState<KnowledgeObject[]>([]);
  const [graph, setGraph] = useState<BrainGraph>(demoGraph);
  const [contextPack, setContextPack] = useState<ContextPack | null>(null);
  const [aiStatus, setAIStatus] = useState<AIProviderStatus>(demoAIStatus);

  const stats = useMemo(
    () => ({
      published: objects.length,
      review: reviewItems.length,
      graphNodes: graph.nodes.length,
      graphEdges: graph.edges.length,
      enrichedReviews: reviewItems.filter((item) => item.ai_enrichment).length
    }),
    [graph.edges.length, graph.nodes.length, objects.length, reviewItems]
  );

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [health, reviews, publishedObjects, providerStatus] = await Promise.all([
        brainClient.health(),
        brainClient.listReviewItems(),
        brainClient.listObjects(),
        brainClient.getAIProviderStatus()
      ]);
      const nextGraph = await brainClient.getGraph().catch(() => buildGraphFromState(publishedObjects, reviews));
      setEnvironment(health.environment);
      setReviewItems(reviews);
      setObjects(publishedObjects);
      setGraph(nextGraph);
      setAIStatus(providerStatus);
      setDemoMode(false);
    } catch (caught) {
      setEnvironment("offline-demo");
      setReviewItems(demoReviewItems);
      setObjects(demoObjects);
      setGraph(demoGraph);
      setContextPack(demoContextPack);
      setAIStatus(demoAIStatus);
      setDemoMode(true);
      setError(caught instanceof Error ? caught.message : "Could not reach API. Using built-in demo data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function submitContext(payload: IngestionPayload) {
    if (demoMode) {
      const id = `review_ui_${Date.now()}`;
      const candidate: KnowledgeObject = {
        id: `candidate.${payload.domain}.${payload.title.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`,
        type: payload.content.toLowerCase().includes("dashboard") ? "Report" : "Metric",
        title: payload.title,
        summary: payload.content.slice(0, 240),
        domain: payload.domain,
        owner: payload.content.match(/owned by ([A-Za-z0-9 _&-]+)/i)?.[1] ?? null,
        status: "human_review_required",
        sensitivity: payload.sensitivity,
        source_ids: [`source_ui_${Date.now()}`],
        relationships: [],
        attributes: { tags: payload.tags, demo_mode: true },
        confidence: 0.67,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      const nextReviews = [
        {
          id,
          source_id: candidate.source_ids[0],
          candidate_object: candidate,
          status: "human_review_required" as const,
          reviewer: null,
          review_comment: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        ...reviewItems
      ];
      setReviewItems(nextReviews);
      setGraph(buildGraphFromState(objects, nextReviews));
      return;
    }

    await brainClient.submitContext(payload);
    await refresh();
  }

  async function approveReview(reviewItemId: string) {
    if (demoMode) {
      const item = reviewItems.find((review) => review.id === reviewItemId);
      if (!item) return;
      const approvedObject = { ...item.candidate_object, status: "published" as const, updated_at: new Date().toISOString() };
      const nextObjects = [approvedObject, ...objects];
      const nextReviews = reviewItems.filter((review) => review.id !== reviewItemId);
      setObjects(nextObjects);
      setReviewItems(nextReviews);
      setGraph(buildGraphFromState(nextObjects, nextReviews));
      return;
    }

    await brainClient.approveReviewItem(reviewItemId, { reviewed_by: reviewer, comment: "Approved from React console." });
    await refresh();
  }

  async function rejectReview(reviewItemId: string) {
    if (demoMode) {
      const nextReviews = reviewItems.filter((review) => review.id !== reviewItemId);
      setReviewItems(nextReviews);
      setGraph(buildGraphFromState(objects, nextReviews));
      return;
    }

    await brainClient.rejectReviewItem(reviewItemId, { reviewed_by: reviewer, comment: "Rejected from React console." });
    await refresh();
  }

  async function enrichReview(reviewItemId: string) {
    if (demoMode) return;
    await brainClient.enrichReviewItem(reviewItemId);
    await refresh();
  }

  async function askBrain(request: ContextPackRequest) {
    if (demoMode) {
      setContextPack({
        ...demoContextPack,
        question: request.question,
        user_id: request.user_id,
        mode: request.mode,
        generated_at: new Date().toISOString()
      });
      return;
    }
    setContextPack(await brainClient.buildContextPack(request));
  }

  return (
    <div className="site-shell">
      <aside className="side-nav" aria-label="Console navigation">
        <div className="brand-lockup">
          <span className="brand-mark">UKB</span>
          <div>
            <strong>AI Brain</strong>
            <span>Governed context OS</span>
          </div>
        </div>
        <nav>
          {navItems.map((item) => (
            <a href={item.href} key={item.href}>{item.label}</a>
          ))}
        </nav>
        <div className="nav-callout">
          <span>AI enrichment</span>
          <strong>{aiStatus.provider} · {aiStatus.mode}</strong>
          <p>{aiStatus.enabled ? `Model: ${aiStatus.model}` : "Disabled by server config"}</p>
        </div>
        <div className="nav-callout">
          <span>Demo domain</span>
          <strong>Support Ops</strong>
          <p>Uses only synthetic, workplace-safe examples.</p>
        </div>
      </aside>

      <main className="app-shell">
        {demoMode && (
          <div className="mode-banner" role="status">
            <strong>Demo Mode</strong>
            <span>No backend connected. Actions are simulated and reset on refresh.</span>
          </div>
        )}

        <header className="hero framer-hero">
          <div className="hero-content">
            <p className="eyebrow">Framer-inspired enterprise SaaS console</p>
            <h1>Governed AI Brain command center</h1>
            <p className="hero-copy">
              A dashboard-led workspace for submitting context, enriching candidates with AI review briefs,
              publishing approved brain objects, and exploring the knowledge graph behind every context pack.
            </p>
            <div className="hero-actions">
              <button type="button" onClick={() => document.getElementById("context-ingestion")?.scrollIntoView({ behavior: "smooth" })}>
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
                <span>{demoMode ? "Simulated local state" : `${API_BASE} · ${environment}`}</span>
              </div>
              <button type="button" onClick={refresh} disabled={loading}>{loading ? "Refreshing..." : "Refresh"}</button>
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

        {error && <div className="notice">{error}</div>}

        <section className="stats-grid" aria-label="Brain state summary">
          <Metric label="Published objects" value={stats.published} detail="approved runtime context" />
          <Metric label="Review queue" value={stats.review} detail="awaiting validation" />
          <Metric label="AI enriched" value={stats.enrichedReviews} detail="review briefs attached" />
          <Metric label="Graph edges" value={stats.graphEdges} detail="typed relationships" />
        </section>

        <section id="brain-map" className="section-shell">
          <div className="section-heading">
            <p className="eyebrow">Visual knowledge runtime</p>
            <h2>Inspect the brain before trusting the answer</h2>
            <p>Use the map to trace source evidence, review state, published knowledge, and graph relationships.</p>
          </div>
          <ObsidianGraphView graph={graph} />
        </section>

        <main className="workbench">
          <SubmitContext onSubmit={submitContext} demoMode={demoMode} />
          <ReviewQueue items={reviewItems} onApprove={approveReview} onReject={rejectReview} onEnrich={enrichReview} demoMode={demoMode} />
          <ContextPackExplorer onAsk={askBrain} contextPack={contextPack} demoMode={demoMode} />
          <PublishedObjects objects={objects} />
        </main>
      </main>
    </div>
  );
}

function Metric({ label, value, detail }: { label: string; value: number; detail: string }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function SubmitContext({ onSubmit, demoMode }: { onSubmit: (payload: IngestionPayload) => Promise<void>; demoMode: boolean }) {
  const [title, setTitle] = useState("Incident Resolution Time Definition");
  const [domain, setDomain] = useState("support");
  const [sourceType, setSourceType] = useState<SourceType>("document");
  const [content, setContent] = useState(
    "Incident Resolution Time is the average elapsed time from incident creation to resolved status for product support cases, excluding duplicate incidents and customer-wait periods. It appears in the SLA Review Dashboard and is owned by Support Operations. Recently resolved incidents may need 24 hours for quality review tags to settle."
  );
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit({
        title,
        domain,
        source_type: sourceType,
        submitted_by: "ui.submitter",
        content,
        sensitivity: "internal",
        tags: ["ui", domain]
      });
      setTitle("");
      setContent("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel panel-accent" id="context-ingestion">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Context ingestion</p>
          <h2>Submit context</h2>
        </div>
        <span className="chip">Source → AI brief → Candidate</span>
      </div>
      <p className="panel-copy">Paste synthetic source context and let the compiler create a candidate with AI enrichment for human review.</p>
      <form onSubmit={submit} className="stack">
        <label>Title<input value={title} onChange={(event) => setTitle(event.target.value)} required /></label>
        <div className="form-row">
          <label>Domain<input value={domain} onChange={(event) => setDomain(event.target.value)} required /></label>
          <label>Source type
            <select value={sourceType} onChange={(event) => setSourceType(event.target.value as SourceType)}>
              <option value="document">Document</option>
              <option value="markdown">Markdown</option>
              <option value="sql">SQL</option>
              <option value="dashboard">Dashboard</option>
              <option value="manual">Manual</option>
            </select>
          </label>
        </div>
        <label>Context<textarea value={content} onChange={(event) => setContent(event.target.value)} rows={8} required /></label>
        <button type="submit" disabled={submitting || !title || !content}>
          {submitting ? "Submitting..." : demoMode ? "Simulate AI-enriched submission" : "Submit and enrich"}
        </button>
      </form>
    </section>
  );
}

function ReviewQueue({
  items,
  onApprove,
  onReject,
  onEnrich,
  demoMode
}: {
  items: ReviewItem[];
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string) => Promise<void>;
  onEnrich: (id: string) => Promise<void>;
  demoMode: boolean;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(items[0]?.id ?? null);

  useEffect(() => {
    if (!items.length) {
      setSelectedId(null);
      return;
    }
    if (!selectedId || !items.some((item) => item.id === selectedId)) {
      setSelectedId(items[0].id);
    }
  }, [items, selectedId]);

  const selectedItem = selectedId ? items.find((item) => item.id === selectedId) : undefined;
  const enrichment = selectedItem?.ai_enrichment;

  return (
    <section className="panel review-panel" id="review-queue">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Human validation</p>
          <h2>Review queue</h2>
        </div>
        <span className="chip warning-chip">{items.length} pending</span>
      </div>
      <div className="review-layout">
        <div className="scroll-list">
          {items.length === 0 && <div className="empty-state">No candidate knowledge is waiting for review.</div>}
          {items.map((item) => (
            <button
              type="button"
              className={selectedId === item.id ? "review-item selected-review" : "review-item"}
              key={item.id}
              onClick={() => setSelectedId(item.id)}
            >
              <span className="badge">{item.candidate_object.type}</span>
              <strong>{item.candidate_object.title}</strong>
              <small>{item.status} · {Math.round(item.candidate_object.confidence * 100)}% confidence · {item.ai_enrichment ? "AI brief" : "No AI brief"}</small>
            </button>
          ))}
        </div>
        <aside className="candidate-inspector">
          {selectedItem ? (
            <>
              <span className="badge">Candidate</span>
              <h3>{selectedItem.candidate_object.title}</h3>
              <p>{selectedItem.candidate_object.summary}</p>
              {enrichment && (
                <div className="ai-brief">
                  <div className="ai-brief-header">
                    <strong>AI review brief</strong>
                    <span>{enrichment.provider} · {Math.round(enrichment.confidence * 100)}%</span>
                  </div>
                  <p>{enrichment.review_brief.summary}</p>
                  {enrichment.validation_findings.length > 0 && (
                    <ul className="finding-list">
                      {enrichment.validation_findings.slice(0, 3).map((finding) => (
                        <li key={`${finding.finding_type}-${finding.message}`} className={`finding finding-${finding.severity}`}>
                          <strong>{finding.severity}</strong>
                          <span>{finding.message}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                  {enrichment.review_brief.reviewer_questions.length > 0 && (
                    <div className="question-stack">
                      <strong>Reviewer questions</strong>
                      {enrichment.review_brief.reviewer_questions.slice(0, 3).map((question) => <span key={question}>{question}</span>)}
                    </div>
                  )}
                </div>
              )}
              <dl>
                <div><dt>Status</dt><dd>{selectedItem.status}</dd></div>
                <div><dt>Domain</dt><dd>{selectedItem.candidate_object.domain}</dd></div>
                <div><dt>Owner</dt><dd>{selectedItem.candidate_object.owner ?? "Not assigned"}</dd></div>
              </dl>
              <div className="actions">
                {!demoMode && !enrichment && (
                  <button type="button" className="secondary" onClick={() => onEnrich(selectedItem.id)}>Run AI enrichment</button>
                )}
                <button type="button" onClick={() => onApprove(selectedItem.id)}>
                  {demoMode ? "Simulate approval" : "Approve and publish"}
                </button>
                <button type="button" className="secondary" onClick={() => onReject(selectedItem.id)}>
                  {demoMode ? "Simulate rejection" : "Reject"}
                </button>
              </div>
            </>
          ) : (
            <div className="empty-state">Select a candidate to inspect before approving.</div>
          )}
        </aside>
      </div>
    </section>
  );
}

function ContextPackExplorer({
  onAsk,
  contextPack,
  demoMode
}: {
  onAsk: (request: ContextPackRequest) => Promise<void>;
  contextPack: ContextPack | null;
  demoMode: boolean;
}) {
  const [question, setQuestion] = useState("Why did incident resolution time increase?");
  const [mode, setMode] = useState<ContextPackRequest["mode"]>("executive_insight");
  const [asking, setAsking] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setAsking(true);
    try {
      await onAsk({ question, user_id: "ui.consumer", domains: ["support"], mode });
    } finally {
      setAsking(false);
    }
  }

  return (
    <section className="panel wide-panel" id="context-pack">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Context runtime</p>
          <h2>Generate context pack</h2>
        </div>
        <span className="chip">Approved knowledge only</span>
      </div>
      <form onSubmit={submit} className="context-form">
        <input value={question} onChange={(event) => setQuestion(event.target.value)} aria-label="Context-pack question" />
        <select value={mode} onChange={(event) => setMode(event.target.value as ContextPackRequest["mode"])} aria-label="Context-pack mode">
          <option value="default">Default</option>
          <option value="executive_insight">Executive insight</option>
          <option value="metric_definition">Metric definition</option>
          <option value="lineage">Lineage</option>
          <option value="governance_review">Governance review</option>
        </select>
        <button type="submit" disabled={asking}>{asking ? "Generating..." : demoMode ? "Simulate pack" : "Generate enriched pack"}</button>
      </form>
      {contextPack && (
        <div className="context-pack">
          <div className="pack-header">
            <strong>{contextPack.access_decision.toUpperCase()}</strong>
            <span>{Math.round(contextPack.confidence * 100)}% confidence</span>
            <span>{contextPack.mode}</span>
          </div>
          <p>{contextPack.answer_guidance}</p>
          {contextPack.ai_guidance && (
            <div className="ai-guidance">
              <strong>AI enrichment guidance</strong>
              <span>{contextPack.ai_guidance}</span>
            </div>
          )}
          {contextPack.missing_context.length > 0 && (
            <div className="caveat-box">
              <strong>Missing context</strong>
              <span>{contextPack.missing_context.join(" · ")}</span>
            </div>
          )}
          <div className="pack-grid">
            <div>
              <h4>Evidence</h4>
              <ul>{contextPack.evidence.map((source) => <li key={source.source_id}>{source.title}: {source.content_excerpt}</li>)}</ul>
            </div>
            <div>
              <h4>Follow-ups</h4>
              <ul>{contextPack.recommended_followups.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          </div>
          {contextPack.caveats.length > 0 && (
            <div className="caveat-box">
              <strong>Caveats</strong>
              <span>{contextPack.caveats.join(" · ")}</span>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function PublishedObjects({ objects }: { objects: KnowledgeObject[] }) {
  return (
    <section className="panel wide-panel" id="published-objects">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Published AI Brain</p>
          <h2>Approved knowledge</h2>
        </div>
        <span className="chip success-chip">{objects.length} published</span>
      </div>
      <div className="object-grid">
        {objects.length === 0 && <div className="empty-state">Approved knowledge will appear here after review.</div>}
        {objects.map((object) => (
          <article className="object-card" key={object.id}>
            <span className="badge">{object.type}</span>
            <h3>{object.title}</h3>
            <p>{object.summary}</p>
            <small>{object.domain} · {object.owner ?? "No owner"} · {object.status}</small>
          </article>
        ))}
      </div>
    </section>
  );
}
