import { useEffect, useMemo, useState } from "react";
import { API_BASE, brainClient } from "./api/brainClient";
import { demoContextPack, demoGraph, demoObjects, demoReviewItems } from "./data/demoBrain";
import { ObsidianGraphView } from "./components/ObsidianGraphView";
import { buildGraphFromState } from "./utils/graph";
import type { BrainGraph, ContextPack, ContextPackRequest, IngestionPayload, KnowledgeObject, ReviewItem, SourceType } from "./types";

const reviewer = "ui.reviewer";

export default function App() {
  const [environment, setEnvironment] = useState("unknown");
  const [demoMode, setDemoMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>([]);
  const [objects, setObjects] = useState<KnowledgeObject[]>([]);
  const [graph, setGraph] = useState<BrainGraph>(demoGraph);
  const [contextPack, setContextPack] = useState<ContextPack | null>(null);

  const stats = useMemo(() => ({
    published: objects.length,
    review: reviewItems.length,
    graphNodes: graph.nodes.length,
    graphEdges: graph.edges.length
  }), [graph.edges.length, graph.nodes.length, objects.length, reviewItems.length]);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [health, reviews, publishedObjects] = await Promise.all([
        brainClient.health(),
        brainClient.listReviewItems(),
        brainClient.listObjects()
      ]);
      const nextGraph = await brainClient.getGraph().catch(() => buildGraphFromState(publishedObjects, reviews));
      setEnvironment(health.environment);
      setReviewItems(reviews);
      setObjects(publishedObjects);
      setGraph(nextGraph);
      setDemoMode(false);
    } catch (caught) {
      setEnvironment("offline-demo");
      setReviewItems(demoReviewItems);
      setObjects(demoObjects);
      setGraph(demoGraph);
      setContextPack(demoContextPack);
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
      const nextReviews = [{
        id,
        source_id: candidate.source_ids[0],
        candidate_object: candidate,
        status: "human_review_required" as const,
        reviewer: null,
        review_comment: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }, ...reviewItems];
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

  async function askBrain(request: ContextPackRequest) {
    if (demoMode) {
      setContextPack({ ...demoContextPack, question: request.question, user_id: request.user_id, mode: request.mode, generated_at: new Date().toISOString() });
      return;
    }
    setContextPack(await brainClient.buildContextPack(request));
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Unified Knowledge Base</p>
          <h1>Governed AI Brain Console</h1>
          <p className="hero-copy">Submit context, review AI-classified candidates, publish approved knowledge, and explore the brain as an Obsidian-style graph.</p>
        </div>
        <div className="status-card">
          <span className={demoMode ? "pulse warning" : "pulse"} />
          <div>
            <strong>{demoMode ? "Offline demo" : "Connected"}</strong>
            <span>{demoMode ? "Using synthetic local state" : `${API_BASE} · ${environment}`}</span>
          </div>
          <button type="button" onClick={refresh} disabled={loading}>{loading ? "Refreshing..." : "Refresh"}</button>
        </div>
      </header>

      {error && <div className="notice">{error}</div>}

      <section className="stats-grid">
        <Metric label="Published objects" value={stats.published} />
        <Metric label="Review queue" value={stats.review} />
        <Metric label="Graph nodes" value={stats.graphNodes} />
        <Metric label="Graph edges" value={stats.graphEdges} />
      </section>

      <ObsidianGraphView graph={graph} />

      <main className="workbench">
        <SubmitContext onSubmit={submitContext} />
        <ReviewQueue items={reviewItems} onApprove={approveReview} onReject={rejectReview} />
        <ContextPackExplorer onAsk={askBrain} contextPack={contextPack} />
        <PublishedObjects objects={objects} />
      </main>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function SubmitContext({ onSubmit }: { onSubmit: (payload: IngestionPayload) => Promise<void> }) {
  const [title, setTitle] = useState("Device Revenue Definition");
  const [domain, setDomain] = useState("finance");
  const [sourceType, setSourceType] = useState<SourceType>("document");
  const [content, setContent] = useState("Device Revenue is revenue generated from device sales, excluding service revenue. It appears in the CFO KPI dashboard and is owned by Finance BI.");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: React.FormEvent) {
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
    <section className="panel">
      <p className="eyebrow">Context ingestion</p>
      <h2>Submit context</h2>
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
        <button type="submit" disabled={submitting || !title || !content}>{submitting ? "Submitting..." : "Submit for review"}</button>
      </form>
    </section>
  );
}

function ReviewQueue({ items, onApprove, onReject }: { items: ReviewItem[]; onApprove: (id: string) => Promise<void>; onReject: (id: string) => Promise<void> }) {
  return (
    <section className="panel">
      <p className="eyebrow">Human validation</p>
      <h2>Review queue</h2>
      <div className="scroll-list">
        {items.length === 0 && <div className="empty-state">No candidate knowledge is waiting for review.</div>}
        {items.map((item) => (
          <article className="review-item" key={item.id}>
            <div>
              <span className="badge">{item.candidate_object.type}</span>
              <h3>{item.candidate_object.title}</h3>
              <p>{item.candidate_object.summary}</p>
              <small>{item.status} · {Math.round(item.candidate_object.confidence * 100)}% confidence</small>
            </div>
            <div className="actions">
              <button type="button" onClick={() => onApprove(item.id)}>Approve</button>
              <button type="button" className="secondary" onClick={() => onReject(item.id)}>Reject</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ContextPackExplorer({ onAsk, contextPack }: { onAsk: (request: ContextPackRequest) => Promise<void>; contextPack: ContextPack | null }) {
  const [question, setQuestion] = useState("Why is device revenue down?");
  const [mode, setMode] = useState<ContextPackRequest["mode"]>("executive_insight");
  const [asking, setAsking] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setAsking(true);
    try {
      await onAsk({ question, user_id: "ui.consumer", domains: ["finance"], mode });
    } finally {
      setAsking(false);
    }
  }

  return (
    <section className="panel wide-panel">
      <p className="eyebrow">Context runtime</p>
      <h2>Context pack explorer</h2>
      <form onSubmit={submit} className="context-form">
        <input value={question} onChange={(event) => setQuestion(event.target.value)} />
        <select value={mode} onChange={(event) => setMode(event.target.value as ContextPackRequest["mode"])}>
          <option value="default">Default</option>
          <option value="executive_insight">Executive insight</option>
          <option value="metric_definition">Metric definition</option>
          <option value="lineage">Lineage</option>
          <option value="governance_review">Governance review</option>
        </select>
        <button type="submit" disabled={asking}>{asking ? "Building..." : "Build pack"}</button>
      </form>
      {contextPack && (
        <div className="context-pack">
          <div className="pack-header">
            <strong>{contextPack.access_decision.toUpperCase()}</strong>
            <span>{Math.round(contextPack.confidence * 100)}% confidence</span>
          </div>
          <p>{contextPack.answer_guidance}</p>
          <h4>Evidence</h4>
          <ul>{contextPack.evidence.map((source) => <li key={source.source_id}>{source.title}: {source.content_excerpt}</li>)}</ul>
          <h4>Recommended follow-ups</h4>
          <ul>{contextPack.recommended_followups.map((item) => <li key={item}>{item}</li>)}</ul>
        </div>
      )}
    </section>
  );
}

function PublishedObjects({ objects }: { objects: KnowledgeObject[] }) {
  return (
    <section className="panel wide-panel">
      <p className="eyebrow">Published AI Brain</p>
      <h2>Approved knowledge objects</h2>
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
