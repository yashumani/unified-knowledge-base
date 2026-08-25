import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { API_BASE } from "../../api/brainClient";
import { useBrainState, REVIEWER } from "../../hooks/useBrainState";
import { ActivityLedger } from "../ActivityLedger";
import { ObsidianGraphView } from "../ObsidianGraphView";
import { ComposeStep } from "../steps/ComposeStep";
import { EnrichStep } from "../steps/EnrichStep";
import { PublishStep } from "../steps/PublishStep";
import { ReviewStep } from "../steps/ReviewStep";
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
type SlideDirection = "forward" | "backward";

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
  { key: "enrich", number: "02", label: "Enrich", verb: "Structure candidates", detail: "Strict local Ollama output, validation findings and evidence links" },
  { key: "review", number: "03", label: "Review", verb: "Make the human decision", detail: "Edit, approve, reject or request changes with a revision guard" },
  { key: "publish", number: "04", label: "Publish", verb: "Create official memory", detail: "A separate publisher gate makes approved knowledge retrievable" },
  { key: "compose", number: "05", label: "Compose", verb: "Build context packs", detail: "Citations, confidence factors, conflicts and downstream constraints" }
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

const PAGE_LABELS: Record<WorkspacePage, string> = {
  home: "Overview",
  ingest: "Submit",
  enrich: "Enrich",
  review: "Review",
  publish: "Publish",
  compose: "Compose",
  memory: "Memory map",
  activity: "Activity",
  help: "Help"
};

const PAGE_META: Record<WorkspacePage, { eyebrow: string; title: string; copy: string }> = {
  home: { eyebrow: "AI brain workspace", title: "Choose the job. Stay oriented.", copy: "Every capability is one click away. The five governance stages remain visible while you work." },
  ingest: { eyebrow: "Stage 01 · source quality", title: "Build a clean ingestion batch.", copy: "Choose a source, configure governance metadata, inspect the manifest, then create evidence-backed candidates." },
  enrich: { eyebrow: "Stage 02 · advisory AI", title: "Turn evidence into structured candidates.", copy: "Run local schema-validated enrichment and inspect its findings without giving the model authority." },
  review: { eyebrow: "Stage 03 · human gate", title: "Decide what may proceed to publication.", copy: "Edit source-grounded candidates, preserve the reason and approve without silently publishing." },
  publish: { eyebrow: "Stage 04 · official memory", title: "Publish approved knowledge explicitly.", copy: "The publication queue separates a review decision from context that is actually retrievable." },
  compose: { eyebrow: "Stage 05 · governed recall", title: "Compose the context an AI receives.", copy: "Inspect citations, evidence coverage, source authority, conflicts and answer constraints." },
  memory: { eyebrow: "Memory map", title: "Trace every source, candidate and relationship.", copy: "Navigate the permission-filtered graph and inspect why each object exists." },
  activity: { eyebrow: "Governance trail", title: "See every human decision.", copy: "Approval, publication, rejection and requested changes remain attributable and explainable." },
  help: { eyebrow: "Help center", title: "Instructions and answers without leaving the workspace.", copy: "Use the end-to-end guide, ingestion reference and troubleshooting answers." }
};

function pageFromLocation(): WorkspacePage {
  if (typeof window === "undefined") return "home";
  const value = new URLSearchParams(window.location.search).get("page") as WorkspacePage | null;
  return value && PAGE_ORDER.includes(value) ? value : "home";
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return Boolean(target.closest("input, textarea, select, button, a, [contenteditable='true'], [role='slider']"));
}

function canConsumeVerticalScroll(target: EventTarget | null, deltaY: number, boundary: HTMLElement): boolean {
  if (!(target instanceof HTMLElement)) return false;
  let element: HTMLElement | null = target;
  while (element && element !== boundary) {
    const style = window.getComputedStyle(element);
    const scrollable = /(auto|scroll)/.test(style.overflowY) && element.scrollHeight > element.clientHeight + 2;
    if (scrollable) {
      const atStart = element.scrollTop <= 1;
      const atEnd = element.scrollTop + element.clientHeight >= element.scrollHeight - 1;
      if ((deltaY < 0 && !atStart) || (deltaY > 0 && !atEnd)) return true;
    }
    element = element.parentElement;
  }
  return false;
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
  const [direction, setDirection] = useState<SlideDirection>("forward");
  const [enrichingId, setEnrichingId] = useState<string | null>(null);
  const shellRef = useRef<HTMLDivElement>(null);
  const wheelLockRef = useRef(0);
  const touchStartRef = useRef<{ x: number; y: number; target: EventTarget | null } | null>(null);

  const navigate = useCallback((next: WorkspacePage, requestedDirection?: SlideDirection) => {
    setPage((current) => {
      if (current === next) return current;
      const currentIndex = PAGE_ORDER.indexOf(current);
      const nextIndex = PAGE_ORDER.indexOf(next);
      setDirection(requestedDirection ?? (nextIndex >= currentIndex ? "forward" : "backward"));
      return next;
    });

    const url = new URL(window.location.href);
    url.searchParams.delete("view");
    if (next === "home") url.searchParams.delete("page");
    else url.searchParams.set("page", next);
    url.hash = "";
    window.history.pushState({}, "", url);
  }, []);

  useEffect(() => {
    const update = () => {
      const next = pageFromLocation();
      setPage((current) => {
        setDirection(PAGE_ORDER.indexOf(next) >= PAGE_ORDER.indexOf(current) ? "forward" : "backward");
        return next;
      });
    };
    window.addEventListener("popstate", update);
    return () => window.removeEventListener("popstate", update);
  }, []);

  const currentIndex = PAGE_ORDER.indexOf(page);
  const previous = currentIndex > 0 ? PAGE_ORDER[currentIndex - 1] : null;
  const next = currentIndex < PAGE_ORDER.length - 1 ? PAGE_ORDER[currentIndex + 1] : null;

  const navigateRelative = useCallback((offset: -1 | 1) => {
    const index = PAGE_ORDER.indexOf(page);
    const destination = PAGE_ORDER[index + offset];
    if (destination) navigate(destination, offset > 0 ? "forward" : "backward");
  }, [navigate, page]);

  useEffect(() => {
    const shell = shellRef.current;
    if (!shell) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || isEditableTarget(event.target)) return;
      if (event.key === "ArrowRight" || event.key === "PageDown") {
        event.preventDefault();
        navigateRelative(1);
      } else if (event.key === "ArrowLeft" || event.key === "PageUp") {
        event.preventDefault();
        navigateRelative(-1);
      } else if (event.key === "Home") {
        event.preventDefault();
        navigate("home", "backward");
      } else if (event.key === "End") {
        event.preventDefault();
        navigate("help", "forward");
      }
    };

    const onWheel = (event: WheelEvent) => {
      if (event.defaultPrevented || Math.abs(event.deltaY) < 42 || Math.abs(event.deltaY) < Math.abs(event.deltaX)) return;
      if (isEditableTarget(event.target) || canConsumeVerticalScroll(event.target, event.deltaY, shell)) return;
      const now = performance.now();
      if (now - wheelLockRef.current < 720) return;
      wheelLockRef.current = now;
      event.preventDefault();
      navigateRelative(event.deltaY > 0 ? 1 : -1);
    };

    const onTouchStart = (event: TouchEvent) => {
      const touch = event.touches[0];
      if (!touch) return;
      touchStartRef.current = { x: touch.clientX, y: touch.clientY, target: event.target };
    };

    const onTouchEnd = (event: TouchEvent) => {
      const start = touchStartRef.current;
      const touch = event.changedTouches[0];
      touchStartRef.current = null;
      if (!start || !touch || isEditableTarget(start.target)) return;
      const deltaX = touch.clientX - start.x;
      const deltaY = touch.clientY - start.y;
      if (Math.abs(deltaX) < 56 || Math.abs(deltaX) < Math.abs(deltaY) * 1.25) return;
      navigateRelative(deltaX < 0 ? 1 : -1);
    };

    window.addEventListener("keydown", onKeyDown);
    shell.addEventListener("wheel", onWheel, { passive: false });
    shell.addEventListener("touchstart", onTouchStart, { passive: true });
    shell.addEventListener("touchend", onTouchEnd, { passive: true });
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      shell.removeEventListener("wheel", onWheel);
      shell.removeEventListener("touchstart", onTouchStart);
      shell.removeEventListener("touchend", onTouchEnd);
    };
  }, [navigate, navigateRelative]);

  async function runEnrichment(reviewItemId: string) {
    setEnrichingId(reviewItemId);
    try {
      await brain.enrichReview(reviewItemId);
    } finally {
      setEnrichingId(null);
    }
  }

  const stages = useMemo<ResolvedStage[]>(() => {
    const counts: Record<StageKey, number> = {
      ingest: brain.reviewItems.length + brain.approvedItems.length + brain.objects.length,
      enrich: brain.stats.enrichedReviews,
      review: brain.reviewItems.length,
      publish: brain.approvedItems.length + brain.objects.length,
      compose: brain.session.packsBuilt
    };
    return STAGES.map((stage) => {
      let complete = false;
      let ready = false;
      if (stage.key === "ingest") {
        complete = brain.session.submitted.length > 0;
        ready = true;
      } else if (stage.key === "enrich") {
        complete = brain.session.enriched.length > 0;
        ready = brain.reviewItems.length > 0;
      } else if (stage.key === "review") {
        complete = brain.session.approved.length > 0 || brain.approvedItems.length > 0;
        ready = brain.reviewItems.length > 0;
      } else if (stage.key === "publish") {
        complete = brain.session.published.length > 0;
        ready = brain.approvedItems.length > 0 || brain.objects.length > 0;
      } else {
        complete = brain.session.packsBuilt > 0;
        ready = brain.objects.length > 0;
      }
      return {
        ...stage,
        count: counts[stage.key],
        state: page === stage.key ? "current" : complete ? "complete" : ready ? "ready" : "waiting"
      };
    });
  }, [
    brain.approvedItems.length,
    brain.objects.length,
    brain.reviewItems.length,
    brain.session,
    brain.stats.enrichedReviews,
    page
  ]);

  const meta = PAGE_META[page];
  const brandMarkUrl = `${import.meta.env.BASE_URL}ai-brain-mark.svg`;

  return (
    <div className="workspace-shell" ref={shellRef} data-workspace-page={page}>
      <a className="skip-link" href="#workspace-main">Skip to workspace content</a>
      <header className="workspace-topbar">
        <button type="button" className="workspace-brand" onClick={() => navigate("home", "backward")}>
          <img src={brandMarkUrl} alt="" aria-hidden="true" />
          <span><strong>AI Brain</strong><small>Unified Knowledge Base</small></span>
        </button>
        <div className="workspace-runtime" aria-live="polite">
          <span className={brain.demoMode ? "connection-dot is-demo" : "connection-dot"} />
          <div>
            <strong>{brain.loading ? "Checking runtime" : brain.demoMode ? "Browser demo" : brain.environment}</strong>
            <small>{brain.demoMode ? "Temporary synthetic state" : API_BASE}</small>
          </div>
        </div>
        <nav className="workspace-actions" aria-label="Workspace utilities">
          <button type="button" onClick={() => navigate("help", "forward")}>Help</button>
          <button type="button" onClick={onOpenGuided}>Guided</button>
          <button type="button" className="workspace-solid" onClick={onOpenAdvanced}>Advanced console</button>
        </nav>
      </header>

      <WorkflowTracker stages={stages} onNavigate={navigate} />

      <main className="workspace-main" id="workspace-main">
        <div key={page} className={`workspace-scene is-${direction}`}>
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
                  <h1 id="workspace-page-title" tabIndex={-1}>{meta.title}</h1>
                  <span>{meta.copy}</span>
                </div>
                <button type="button" className="workspace-home-button" onClick={() => navigate("home", "backward")}>All pages</button>
              </header>
              <div className="workspace-slide-body" data-slide-scroll>
                {page === "ingest" && (
                  <IngestionStudio
                    demoMode={brain.demoMode}
                    onSubmitContext={brain.submitContext}
                    onCompleted={() => navigate("enrich", "forward")}
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
                    onRevise={brain.reviseReview}
                    demoMode={brain.demoMode}
                  />
                )}
                {page === "publish" && (
                  <PublishStep
                    approvedItems={brain.approvedItems}
                    objects={brain.objects}
                    onPublish={brain.publishReview}
                    demoMode={brain.demoMode}
                  />
                )}
                {page === "compose" && (
                  <ComposeStep onAsk={brain.askBrain} contextPack={brain.contextPack} demoMode={brain.demoMode} />
                )}
                {page === "memory" && <ObsidianGraphView graph={brain.graph} />}
                {page === "activity" && <ActivityLedger records={brain.ledger} />}
                {page === "help" && <HelpCenter onNavigate={navigate} />}
              </div>
            </section>
          )}
        </div>
      </main>

      <footer className="workspace-footer">
        <div className="workspace-footer-copy">
          <strong>{PAGE_LABELS[page]}</strong>
          <span>{brain.demoMode ? "Demo actions reset on refresh" : "Connected, governed runtime"}</span>
        </div>
        <nav className="workspace-page-dots" aria-label="Workspace pages">
          {PAGE_ORDER.map((item, index) => (
            <button
              type="button"
              key={item}
              className={item === page ? "is-current" : ""}
              onClick={() => navigate(item)}
              aria-current={item === page ? "page" : undefined}
              aria-label={`Open ${PAGE_LABELS[item]} — page ${index + 1} of ${PAGE_ORDER.length}`}
              title={PAGE_LABELS[item]}
            >
              <span>{String(index + 1).padStart(2, "0")}</span>
              <small>{PAGE_LABELS[item]}</small>
            </button>
          ))}
        </nav>
        <div className="workspace-pager">
          <button type="button" disabled={!previous} onClick={() => previous && navigate(previous, "backward")} aria-label="Previous page">← <span>Previous</span></button>
          <strong>{currentIndex + 1} / {PAGE_ORDER.length}</strong>
          <button type="button" disabled={!next} onClick={() => next && navigate(next, "forward")} aria-label="Next page"><span>Next</span> →</button>
        </div>
      </footer>

      <div className="visually-hidden" aria-live="polite">Page {currentIndex + 1} of {PAGE_ORDER.length}: {PAGE_LABELS[page]}</div>
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
          <div><strong>{stage.label}</strong><small>{stage.count} items</small></div>
        </button>
      ))}
    </nav>
  );
}
