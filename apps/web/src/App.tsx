import { useState } from "react";
import { API_BASE } from "./api/brainClient";
import { ActivityLedger } from "./components/ActivityLedger";
import { NextActionBar } from "./components/NextActionBar";
import { ObsidianGraphView } from "./components/ObsidianGraphView";
import { StepSection } from "./components/StepSection";
import { ComposeStep } from "./components/steps/ComposeStep";
import { EnrichStep } from "./components/steps/EnrichStep";
import { PublishStep } from "./components/steps/PublishStep";
import { ReviewStep } from "./components/steps/ReviewStep";
import { SubmitStep } from "./components/steps/SubmitStep";
import { useActiveStep } from "./hooks/useActiveStep";
import { REVIEWER, useBrainState } from "./hooks/useBrainState";
import { STEP_INTRO } from "./pipeline/copy";
import { deriveStepStates, resolveNextMove } from "./pipeline/derive";
import type { StepId, StepState } from "./pipeline/types";

const NAV_ITEMS = [
  { label: "How it works", href: "#how-it-works" },
  { label: "Console", href: "#pipeline" },
  { label: "Memory map", href: "#brain-map" },
  { label: "Governance", href: "#activity" },
  { label: "Questions", href: "#questions" }
];

const TICKER_ITEMS = [
  "FOR TEAMS WITH TOO MUCH CONTEXT",
  "FOR LOCAL OLLAMA",
  "FOR HUMAN REVIEW",
  "FOR TRACEABLE ANSWERS",
  "FOR GOVERNED RECALL",
  "FOR 5,000+ FILES",
  "FOR AI APPS THAT NEED THE RIGHT MEMORY"
];

const FAQ_ITEMS = [
  {
    question: "What makes this different from chat-with-docs?",
    answer:
      "Raw context never becomes official memory just because a model extracted it. UKB turns a source into a candidate, attaches evidence and validation, requires a human decision, and only then makes the approved object available to retrieval."
  },
  {
    question: "Does the local LLM approve knowledge?",
    answer:
      "No. Ollama can classify, extract, summarize, identify gaps, and suggest reviewer questions. Approval and publication remain human actions, and the decision is recorded in the governance trail."
  },
  {
    question: "Where does Zvec fit?",
    answer:
      "Zvec is the fast, rebuildable retrieval index. PostgreSQL remains the governed source of truth for ownership, versions, access rules, approvals, and audit history. The index helps find the right memory; it does not become the memory authority."
  },
  {
    question: "What happens when no backend is connected?",
    answer:
      "The public site enters an unmistakable demo mode. The workflow still runs in the browser with deterministic synthetic data, but nothing persists and every action resets when the page reloads."
  },
  {
    question: "What does an AI application receive?",
    answer:
      "A governed context pack: approved objects, exact evidence, caveats, confidence, related concepts, missing-context warnings, and guidance about what the downstream model may safely say."
  }
];

export default function App() {
  const brain = useBrainState();
  const { activeStepId, goToStep } = useActiveStep();
  const [enrichingId, setEnrichingId] = useState<string | null>(null);

  const states = deriveStepStates(brain.snapshot, activeStepId);
  const nextMove = resolveNextMove(states);
  const stepState = (index: number) => states[index];

  async function runEnrichment(reviewItemId: string) {
    setEnrichingId(reviewItemId);
    try {
      await brain.enrichReview(reviewItemId);
    } finally {
      setEnrichingId(null);
    }
  }

  return (
    <div className="site-shell depo-page">
      <a className="skip-link" href="#pipeline">Skip to the workflow</a>

      <EditorialNav
        demoMode={brain.demoMode}
        environment={brain.environment}
        loading={brain.loading}
        onRefresh={brain.refresh}
        onStart={() => goToStep("submit")}
      />

      <main className="app-shell" id="main">
        <section className="editorial-hero" id="top" aria-labelledby="hero-title">
          <div className="editorial-hero-copy">
            <p className="editorial-overline">The AI brain for teams with too much context</p>
            <h1 id="hero-title">
              Give AI the <span>right memory.</span>
            </h1>
            <p className="editorial-lede">
              Unified Knowledge Base turns messy documents, source systems, and web knowledge
              into governed context an AI application is actually allowed to use.
            </p>
            <div className="editorial-actions">
              <button type="button" onClick={() => goToStep("submit")}>Build the brain</button>
              <a href="#brain-map" className="editorial-text-link">
                See the memory map <span aria-hidden="true">↘</span>
              </a>
            </div>
            <p className="editorial-promise">
              No blind RAG. No auto-publish. No mystery answer without evidence.
            </p>
          </div>

          <BrainPoster
            demoMode={brain.demoMode}
            environment={brain.environment}
            loading={brain.loading}
            onRefresh={brain.refresh}
            aiProvider={brain.aiStatus.provider}
            aiModel={brain.aiStatus.model}
            published={brain.stats.published}
            pending={brain.stats.review}
            graphEdges={brain.stats.graphEdges}
            contextConfidence={brain.contextPack?.confidence ?? null}
          />
        </section>

        <EditorialTicker />

        {brain.demoMode && (
          <section className="mode-banner editorial-mode" role="status">
            <div>
              <strong>Demo mode. Real workflow, temporary state.</strong>
              <span>
                The backend is not connected. Classification, enrichment, review, publication,
                and context-pack composition still run in your browser, but nothing is persisted.
              </span>
              <details>
                <summary>What resets?</summary>
                <p>
                  New sources, review decisions, published objects, and context packs disappear
                  when the page reloads. Connect the FastAPI runtime for durable storage and local
                  Ollama enrichment.
                </p>
              </details>
            </div>
            <button type="button" className="secondary" onClick={brain.restartDemo}>
              Restart demo
            </button>
          </section>
        )}

        {brain.error && <div className="notice" role="alert">{brain.error}</div>}

        <section className="story-section" id="how-it-works" aria-labelledby="how-heading">
          <div className="story-heading">
            <p className="editorial-overline">Build the brain</p>
            <h2 id="how-heading">Mess in. Governed memory out.</h2>
            <p>
              Five gates separate raw information from context an AI application can trust.
              Every gate is visible, inspectable, and reversible.
            </p>
          </div>
          <ProcessBoard states={states} onNavigate={goToStep} />
        </section>

        <section className="system-band" aria-labelledby="system-heading">
          <div className="system-copy">
            <p className="editorial-overline">That is the whole system</p>
            <h2 id="system-heading">Less context noise. More answer authority.</h2>
            <p>
              The model does not browse a pile of files and hope. UKB first finds approved memory,
              checks its lineage, and packages only the evidence relevant to the question.
            </p>
          </div>
          <div className="system-metrics" aria-label="Current brain state">
            <EditorialMetric value={brain.stats.published} label="published memories" />
            <EditorialMetric value={brain.stats.review} label="open human reviews" />
            <EditorialMetric value={brain.stats.graphEdges} label="typed relationships" />
            <EditorialMetric
              value={brain.contextPack ? `${Math.round(brain.contextPack.confidence * 100)}%` : "—"}
              label="latest pack confidence"
            />
          </div>
        </section>

        <section className="console-intro" id="console" aria-labelledby="console-heading">
          <div>
            <p className="editorial-overline">Use the console</p>
            <h2 id="console-heading">Walk the full source-to-recall pipeline.</h2>
            <p>
              The interface below is not a mockup. Submit context, run enrichment, make the human
              decision, publish the approved object, and compose the context pack an AI app receives.
            </p>
          </div>
          <div className="console-next">
            <NextActionBar nextMove={nextMove} onNavigate={goToStep} />
          </div>
        </section>

        <section id="pipeline" className="pipeline editorial-pipeline" aria-label="Governance workflow">
          <StepSection state={stepState(0)} intro={STEP_INTRO.submit} onNavigate={goToStep}>
            <SubmitStep onSubmit={brain.submitContext} demoMode={brain.demoMode} />
          </StepSection>

          <StepSection state={stepState(1)} intro={STEP_INTRO.enrich} onNavigate={goToStep}>
            <EnrichStep
              items={brain.reviewItems}
              aiStatus={brain.aiStatus}
              onEnrich={runEnrichment}
              enrichingId={enrichingId}
              demoMode={brain.demoMode}
            />
          </StepSection>

          <StepSection state={stepState(2)} intro={STEP_INTRO.review} onNavigate={goToStep}>
            <ReviewStep
              items={brain.reviewItems}
              reviewer={REVIEWER}
              onApprove={brain.approveReview}
              onReject={brain.rejectReview}
              onRequestChanges={brain.requestChanges}
              demoMode={brain.demoMode}
            />
          </StepSection>

          <StepSection state={stepState(3)} intro={STEP_INTRO.publish} onNavigate={goToStep}>
            <PublishStep objects={brain.objects} />
          </StepSection>

          <StepSection state={stepState(4)} intro={STEP_INTRO.compose} onNavigate={goToStep}>
            <ComposeStep
              onAsk={brain.askBrain}
              contextPack={brain.contextPack}
              demoMode={brain.demoMode}
            />
          </StepSection>
        </section>

        <section id="brain-map" className="graph-story" aria-labelledby="brain-map-heading">
          <div className="graph-story-copy">
            <p className="editorial-overline">See the memory</p>
            <h2 id="brain-map-heading">Every answer has a shape.</h2>
            <p>
              Sources, candidates, AI briefs, review states, published objects, and their typed
              relationships form one inspectable memory map. Search it, filter it, navigate it by
              keyboard, and trace the evidence before trusting the output.
            </p>
            <ul className="graph-principles">
              <li>Source evidence stays attached.</li>
              <li>Human review is visible.</li>
              <li>Published memory is distinct from candidates.</li>
              <li>Retrieval can explain why an object matched.</li>
            </ul>
          </div>
          <div className="graph-stage-wrap">
            <ObsidianGraphView graph={brain.graph} />
          </div>
        </section>

        <div className="activity-story">
          <ActivityLedger records={brain.ledger} />
        </div>

        <section className="faq-section" id="questions" aria-labelledby="questions-heading">
          <div className="faq-heading">
            <p className="editorial-overline">Governed memory, decoded</p>
            <h2 id="questions-heading">The blunt answers.</h2>
          </div>
          <div className="faq-list">
            {FAQ_ITEMS.map((item) => (
              <details key={item.question}>
                <summary>{item.question}</summary>
                <p>{item.answer}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="final-cta" aria-labelledby="final-heading">
          <p className="editorial-overline">Your AI already has a model</p>
          <h2 id="final-heading">Now give it a memory worth trusting.</h2>
          <div className="editorial-actions">
            <button type="button" onClick={() => goToStep("submit")}>Start with one source</button>
            <a
              href="https://github.com/yashumani/unified-knowledge-base"
              target="_blank"
              rel="noreferrer"
              className="editorial-text-link"
            >
              View the architecture on GitHub <span aria-hidden="true">↗</span>
            </a>
          </div>
        </section>

        <EditorialFooter />
      </main>
    </div>
  );
}

function EditorialNav({
  demoMode,
  environment,
  loading,
  onRefresh,
  onStart
}: {
  demoMode: boolean;
  environment: string;
  loading: boolean;
  onRefresh: () => void;
  onStart: () => void;
}) {
  return (
    <header className="editorial-nav">
      <a className="editorial-brand" href="#top" aria-label="Unified Knowledge Base home">
        <span>UKB</span>
        <small>Unified Knowledge Base</small>
      </a>
      <nav aria-label="Primary navigation">
        {NAV_ITEMS.map((item) => <a key={item.href} href={item.href}>{item.label}</a>)}
        <a
          href="https://github.com/yashumani/unified-knowledge-base"
          target="_blank"
          rel="noreferrer"
        >
          GitHub ↗
        </a>
      </nav>
      <div className="editorial-nav-actions">
        <button
          type="button"
          className="nav-refresh"
          onClick={onRefresh}
          disabled={loading}
          aria-label="Refresh backend connection"
        >
          <span className={demoMode ? "connection-dot is-demo" : "connection-dot"} />
          {loading ? "Checking" : demoMode ? "Demo" : environment}
        </button>
        <button type="button" className="nav-console" onClick={onStart}>Open console</button>
      </div>
    </header>
  );
}

function BrainPoster({
  demoMode,
  environment,
  loading,
  onRefresh,
  aiProvider,
  aiModel,
  published,
  pending,
  graphEdges,
  contextConfidence
}: {
  demoMode: boolean;
  environment: string;
  loading: boolean;
  onRefresh: () => void;
  aiProvider: string;
  aiModel: string;
  published: number;
  pending: number;
  graphEdges: number;
  contextConfidence: number | null;
}) {
  return (
    <div className="brain-poster" aria-label="Current brain runtime">
      <div className="poster-shell">
        <div className="poster-topline">
          <span>UKB / MEMORY STATUS</span>
          <button type="button" onClick={onRefresh} disabled={loading}>
            {loading ? "Checking…" : "Refresh"}
          </button>
        </div>

        <div className="poster-question">
          <span>Question</span>
          <strong>What can this AI safely say?</strong>
        </div>

        <div className="poster-number">
          <span>Approved memory</span>
          <strong>{String(published).padStart(2, "0")}</strong>
          <small>published objects ready for retrieval</small>
        </div>

        <div className="poster-flow" aria-label="Governance pipeline summary">
          <div><span>01</span><strong>Source</strong><small>evidence captured</small></div>
          <div><span>02</span><strong>Review</strong><small>{pending} waiting</small></div>
          <div><span>03</span><strong>Recall</strong><small>{graphEdges} graph links</small></div>
        </div>

        <div className="poster-runtime">
          <div>
            <span className={demoMode ? "connection-dot is-demo" : "connection-dot"} />
            <div>
              <strong>{demoMode ? "Browser demo" : "Connected runtime"}</strong>
              <small>{demoMode ? "temporary synthetic state" : `${API_BASE} · ${environment}`}</small>
            </div>
          </div>
          <div>
            <span>Enrichment</span>
            <strong>{aiProvider} · {aiModel}</strong>
          </div>
          <div>
            <span>Latest pack</span>
            <strong>{contextConfidence === null ? "not built" : `${Math.round(contextConfidence * 100)}%`}</strong>
          </div>
        </div>
      </div>
    </div>
  );
}

function EditorialTicker() {
  const repeated = [...TICKER_ITEMS, ...TICKER_ITEMS];
  return (
    <section className="editorial-ticker" aria-label="Unified Knowledge Base capabilities">
      <p className="visually-hidden">{TICKER_ITEMS.join(". ")}</p>
      <div className="ticker-track" aria-hidden="true">
        {repeated.map((item, index) => (
          <span key={`${item}-${index}`}>{item}<b>•</b></span>
        ))}
      </div>
    </section>
  );
}

function ProcessBoard({
  states,
  onNavigate
}: {
  states: StepState[];
  onNavigate: (stepId: StepId) => void;
}) {
  return (
    <div className="process-board">
      {states.map((state, index) => (
        <button
          type="button"
          key={state.step.id}
          className={`process-card tone-${index + 1} is-${state.progress}${state.isActive ? " is-active" : ""}`}
          onClick={() => onNavigate(state.step.id)}
        >
          <span className="process-number">{String(state.step.number).padStart(2, "0")}</span>
          <div>
            <p>{state.step.category}</p>
            <h3>{state.step.label}</h3>
            <span>{state.step.governanceMeaning}</span>
          </div>
          <footer>
            <strong>{state.progress === "complete" ? "Done" : state.progress === "available" ? "Ready" : "Waiting"}</strong>
            {state.count && <span>{state.count.value} {state.count.noun}</span>}
          </footer>
        </button>
      ))}
    </div>
  );
}

function EditorialMetric({ value, label }: { value: number | string; label: string }) {
  return (
    <div className="editorial-metric">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function EditorialFooter() {
  return (
    <footer className="editorial-footer">
      <div>
        <strong>UKB</strong>
        <span>Unified Knowledge Base</span>
      </div>
      <p>Local-first AI enrichment. Human-governed publication. Evidence-backed recall.</p>
      <nav aria-label="Footer navigation">
        <a href="#top">Top</a>
        <a href="#pipeline">Console</a>
        <a href="#brain-map">Memory map</a>
        <a href="https://github.com/yashumani/unified-knowledge-base" target="_blank" rel="noreferrer">
          GitHub ↗
        </a>
      </nav>
    </footer>
  );
}
