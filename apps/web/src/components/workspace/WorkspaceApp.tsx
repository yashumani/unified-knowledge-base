import { useEffect, useMemo, useState } from "react";
import { API_BASE } from "../../api/brainClient";
import { ActivityLedger } from "../ActivityLedger";
import { ObsidianGraphView } from "../ObsidianGraphView";
import { ComposeStep } from "../steps/ComposeStep";
import { EnrichStep } from "../steps/EnrichStep";
import { PublishStep } from "../steps/PublishStep";
import { ReviewStep } from "../steps/ReviewStep";
import { useBrainState, REVIEWER } from "../../hooks/useBrainState";
import { DashboardHome } from "./DashboardHome";
import { HelpCenter } from "./HelpCenter";
import { IngestionStudio } from "./IngestionStudio";

export type WorkspacePage =
  | "home"
  | "ingest"
  | "enrich"
  | "review"
  | "publish"
  | "compose"
  | "memory"
  | "activity"
  | "help";

type StageKey = "ingest" | "enrich" | "review" | "publish" | "compose";
type StageState = "complete" | "current" | "ready" | "waiting";

interface StageDefinition {
  key: StageKey;
  number: string;
  label: string;
  verb: string;
  detail: string;
}

interface ResolvedStage extends StageDefinition {
  state: StageState;
  count: number;
}

const STAGES: StageDefinition[] = [
  { key: "ingest", number: "01", label: "Submit", verb: "Collect context", detail: "Files, folders, Drive, Crawl4AI, repositories and containers" },
  { key: "enrich", number: "02", label: "Enrich", verb: "Structure candidates", detail: "Local Ollama briefs, validation findings and proposed relationships" },
  { key: "review", number: "03", label: "Review", verb: "Make the human decision", detail: "Approve, reject, request changes and preserve the reason" },
  { key: "publish", number: "04", label: "Publish", verb: "Create official memory", detail: "Only approved knowledge enters governed retrieval" },
  { key: "compose", number: "05", label: "Compose", verb: "Build context packs", detail: "Evidence, caveats, confidence and downstream AI guidance" }
];

const PAGE_ORDER: WorkspacePage[] = [
  "home",
  "ingest",
  "enrich",
  "review",
  "publish",
  "compose",
  "memory",
  "activity",
  "help"
];

const PAGE_META: Record<WorkspacePage, { eyebrow: string; title: string; copy: string }> = {
  home: {
    eyebrow: "AI brain workspace",
    title: "Choose the job. Stay oriented.",
    copy: "Every capability is one click away. The five governance stages remain visible while you work."
  },
  ingest: {
    eyebrow: "Stage 01 · source quality",
    title: "Build a clean ingestion batch.",
    copy: "Choose a source, configure governance metadata, inspect the manifest, then create review candidates."
  },
  enrich: {
    eyebrow: "Stage 02 · advisory AI",
    title: "Turn evidence into structured candidates.",
    copy: "Run local enrichment, inspect validation findings and keep the model advisory."
  },
  review: {
    eyebrow: "Stage 03 · human gate",
    title: "Decide what the brain is allowed to remember.",
    copy: "Review source-grounded candidates, record the reason and publish only trusted knowledge."
  },
  publish: {
    eyebrow: "Stage 04 · official memory",
    title: "Inspect published knowledge.",
    copy: "Approved objects carry ownership, sensitivity, lineage and version-ready metadata."
  },
  compose: {
    eyebrow: "Stage 05 · governed recall",
    title: "Compose the context an AI receives.",
    copy: "Ask a question and inspect the evidence, caveats, confidence and guidance in the resulting pack."
  },
  memory: {
    eyebrow: "Memory map",
    title: "Trace every source, candidate and relationship.",
    copy: "Navigate the graph visually or by keyboard and inspect why each object exists."
  },
  activity: {
    eyebrow: "Governance trail",
    title: "See every human decision.",
    copy: "Approval, rejection and requested changes remain attributable and explainable."
  },
  help: {
    eyebrow: "Help center",
    title: "Instructions and answers without leaving the workspace.",
    copy: "Use the end-to-end guide, ingestion reference and troubleshooting answers."
  }
};

function pageFromLocation(): WorkspacePage {
  if (typeof window === "undefined") return "home";
  const value = new URLSearchParams(window.location.search).get("page") as WorkspacePage | null;
  return value && PAGE_ORDER.includes(value) ? value : "home";
}

export function WorkspaceApp({
  onOpenAdvanced,
  onOpenGuided
}: {
  onOpenAdvanced: () => void;
  onOpenGuided: () => void;
}) {
  const brain = useBrainState();
  const [page, setPage] = useState<WorkspacePage>(pageFromLocation);
  const [enrichingId, setEnrichingId] = useState<string | null>(null);

  useEffect(() => {
    const update = () => setPage(pageFromLocation());
    window.addEventListener("popstate", update);
    return () => window.removeEventListener("popstate", update);
  }, []);

  function navigate(next: WorkspacePage) {
    const url = new URL(window.location.href);
    url.searchParams.delete("view");
    if (next === "home") url.searchParams.delete("page");
    else url.searchParams.set("page", next);
    url.hash = "";
    window.history.pushState({}, "", url);
    setPage(next);
  }

  async function runEnrichment(reviewItemId: string) {
    setEnrichingId(reviewItemId);
    try {
      await brain.enrichReview(reviewItemId);
    } finally {
      setEnrichingId(null);
    }
  }

  const stages = useMemo<ResolvedStage[]>(() => {
    const userSubmitted = brain.session.submitted.length > 0;
    const userEnriched = brain.session.enriched.length > 0;
    const userPublished = brain.session.published.length > 0;
    const userComposed = brain.session.packsBuilt > 0;
    const counts: Record<StageKey, number> = {
      ingest: brain.reviewItems.length + brain.objects.length,
      enrich: brain.stats.enrichedReviews,
      review: brain.reviewItems.length,
      publish: brain.objects.length,
      compose: brain.session.packsBuilt
    };

    return STAGES.map((stage) => {
      let complete = false;
      let ready = false;
      if (stage.key === "ingest") {
        complete = userSubmitted;
        ready = true;
      } else if (stage.key === "enrich") {
        complete = userEnriched;
        ready = brain.reviewItems.length > 0;
      } else if (stage.key === "review") {
        complete = userPublished || brain.ledger.length > 0;
        ready = brain.reviewItems.length > 0;
      } else if (stage.key === "publish") {
        complete = userPublished;
        ready = brain.objects.length > 0;
      } else {
        complete = userComposed;
        ready = brain.objects.length > 0;
      }

      return {
        ...stage,
        count: counts[stage.key],
        state: page === stage.key ? "current" : complete ? "complete" : ready ? "ready" : "waiting"
      };
    });
  }, [brain.ledger.length, brain.objects.length, brain.reviewItems.length, brain.session, brain.stats.enrichedReviews, page]);

  const currentIndex = PAGE_ORDER.indexOf(page);
  const previous = currentIndex > 0 ? PAGE_ORDER[currentIndex - 1] : null;
  const next = currentIndex < PAGE_ORDER.length - 1 ? PAGE_ORDER[currentIndex + 1] : null;
  const meta = PAGE_META[page];

  return (
    <div className="workspace-shell">
      <a className="skip-link" href="#workspace-main">Skip to workspace content</a>

      <header className="workspace-topbar">
        <button type="button" className="workspace-brand" onClick={() => navigate("home")}>
          <span>UKB</span>
          <strong>AI Brain Workspace</strong>
        </button>
        <div className="workspace-runtime" aria-live="polite">
          <span className={brain.demoMode ? "connection-dot is-demo" : "connection-dot"} />
          <div>
            <strong>{brain.loading ? "Checking runtime" : brain.demoMode ? "Browser demo" : brain.environment}</strong>
            <small>{brain.demoMode ? "Temporary synthetic state" : API_BASE}</small>
          </div>
        </div>
        <nav className="workspace-actions" aria-label="Workspace utilities">
          <button type="button" onClick={() => navigate("help")}>Help</button>
          <button type="button" onClick={onOpenGuided}>Guided</button>
          <button type="button" className="workspace-solid" onClick={onOpenAdvanced}>Advanced console</button>
        </nav>
      </header>

      <WorkflowTracker stages={stages} onNavigate={navigate} />

      <main className="workspace-main" id="workspace-main">
        {page === "home" ? (
          <DashboardHome
            stages={stages}
            stats={{
              review: brain.reviewItems.length,
              published: brain.objects.length,
              graph: brain.graph.nodes.length,
              provider: `${brain.aiStatus.provider} · ${brain.aiStatus.model}`
            }}
            demoMode={brain.demoMode}
            onNavigate={navigate}
          />
        ) : (
          <section className={`workspace-slide workspace-slide-${page}`} aria-labelledby="workspace-page-title">
            <header className="workspace-slide-header">
              <div>
                <p>{meta.eyebrow}</p>
                <h1 id="workspace-page-title">{meta.title}</h1>
                <span>{meta.copy}</span>
              </div>
              <button type="button" className="workspace-home-button" onClick={() => navigate("home")}>All pages</button>
            </header>

            <div className="workspace-slide-body">
              {page === "ingest" && (
                <IngestionStudio
                  demoMode={brain.demoMode}
                  onSubmitContext={brain.submitContext}
                  onCompleted={() => navigate("enrich")}
                />
              )}
              {page === "enrich" && (
                <EnrichStep
                  items={brain.reviewItems}
                  aiStatus={brain.aiStatus}
                  onEnrich={runEnrichment}
                  enrichingId={enrichingId}
                  demoMode={brain.demoMode}
                />
              )}
              {page === "review" && (
                <ReviewStep
                  items={brain.reviewItems}
                  reviewer={REVIEWER}
                  onApprove={brain.approveReview}
                  onReject={brain.rejectReview}
                  onRequestChanges={brain.requestChanges}
                  demoMode={brain.demoMode}
                />
              )}
              {page === "publish" && <PublishStep objects={brain.objects} />}
              {page === "compose" && (
                <ComposeStep onAsk={brain.askBrain} contextPack={brain.contextPack} demoMode={brain.demoMode} />
              )}
              {page === "memory" && <ObsidianGraphView graph={brain.graph} />}
              {page === "activity" && <ActivityLedger records={brain.ledger} />}
              {page === "help" && <HelpCenter onNavigate={navigate} />}
            </div>
          </section>
        )}
      </main>

      <footer className="workspace-footer">
        <div>
          <strong>{page === "home" ? "Workspace home" : meta.title}</strong>
          <span>{brain.demoMode ? "Demo actions reset on refresh" : "Connected, governed runtime"}</span>
        </div>
        <div className="workspace-pager">
          <button type="button" disabled={!previous} onClick={() => previous && navigate(previous)}>← Previous</button>
          <span>{currentIndex + 1} / {PAGE_ORDER.length}</span>
          <button type="button" disabled={!next} onClick={() => next && navigate(next)}>Next →</button>
        </div>
      </footer>
    </div>
  );
}

function WorkflowTracker({ stages, onNavigate }: { stages: ResolvedStage[]; onNavigate: (page: WorkspacePage) => void }) {
  return (
    <nav className="workspace-tracker" aria-label="AI brain workflow">
      {stages.map((stage) => (
        <button
          key={stage.key}
          type="button"
          className={`workspace-track-step is-${stage.state}`}
          onClick={() => onNavigate(stage.key)}
          aria-current={stage.state === "current" ? "step" : undefined}
        >
          <span>{stage.state === "complete" ? "✓" : stage.number}</span>
          <div>
            <strong>{stage.label}</strong>
            <small>{stage.count} items</small>
          </div>
        </button>
      ))}
    </nav>
  );
}
