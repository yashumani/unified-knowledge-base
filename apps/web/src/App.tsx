import { useState } from "react";
import { API_BASE } from "./api/brainClient";
import { ObsidianGraphView } from "./components/ObsidianGraphView";
import { Hero } from "./components/Hero";
import { NextActionBar } from "./components/NextActionBar";
import { PipelineStepper } from "./components/PipelineStepper";
import { SideNav } from "./components/SideNav";
import { StatsGrid } from "./components/StatsGrid";
import { StepSection } from "./components/StepSection";
import { ComposeStep } from "./components/steps/ComposeStep";
import { EnrichStep } from "./components/steps/EnrichStep";
import { PublishStep } from "./components/steps/PublishStep";
import { ReviewStep } from "./components/steps/ReviewStep";
import { SubmitStep } from "./components/steps/SubmitStep";
import { useActiveStep } from "./hooks/useActiveStep";
import { useBrainState } from "./hooks/useBrainState";
import { STEP_INTRO } from "./pipeline/copy";
import { deriveStepStates, resolveNextMove } from "./pipeline/derive";

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
    <div className="site-shell">
      <a className="skip-link" href="#pipeline">Skip to the workflow</a>

      <SideNav aiStatus={brain.aiStatus} states={states} onNavigate={goToStep} />

      <main className="app-shell" id="main">
        {brain.demoMode && (
          <div className="mode-banner" role="status">
            <div>
              <strong>Demo mode</strong>
              <span>
                No backend is connected. Every step below still runs — classification,
                enrichment and context-pack composition all execute in your browser using
                the platform's deterministic offline provider.
              </span>
              <details>
                <summary>What does that mean?</summary>
                <p>
                  The console normally talks to a FastAPI backend. Without one it falls back to
                  a port of the same offline provider the server uses when no model runtime is
                  available, so the workflow is real even though nothing is persisted. Reload
                  and it all resets.
                </p>
              </details>
            </div>
            <button type="button" className="secondary" onClick={brain.restartDemo}>
              Restart demo
            </button>
          </div>
        )}

        <Hero
          demoMode={brain.demoMode}
          environment={brain.environment}
          apiBase={API_BASE}
          loading={brain.loading}
          onRefresh={brain.refresh}
          onStart={() => goToStep("submit")}
        />

        {brain.error && <div className="notice" role="alert">{brain.error}</div>}

        {/* Sticky rail: where you are, and the one thing to do next. */}
        <div className="pipeline-rail">
          <PipelineStepper states={states} onNavigate={goToStep} />
          <NextActionBar nextMove={nextMove} onNavigate={goToStep} />
        </div>

        <StatsGrid
          published={brain.stats.published}
          review={brain.stats.review}
          enrichedReviews={brain.stats.enrichedReviews}
          graphNodes={brain.stats.graphNodes}
          graphEdges={brain.stats.graphEdges}
        />

        {/* Steps run in pipeline order, one per row. The old two-column grid
            made the visual reading order 1, 3, 5, 4. */}
        <section id="pipeline" className="pipeline" aria-label="Governance workflow">
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
              onApprove={brain.approveReview}
              onReject={brain.rejectReview}
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

        {/* The graph is the payoff, so it follows the walk rather than
            preceding it. */}
        <section id="brain-map" className="section-shell" aria-labelledby="brain-map-heading">
          <div className="section-heading">
            <h2 id="brain-map-heading">
              <span className="step-kicker">Visual knowledge runtime</span>
              Inspect the lineage you just built
            </h2>
            <p>
              Every node here came from the workflow above: source evidence, the candidates it
              produced, the review state, and the approved objects a context pack may draw on.
            </p>
          </div>
          <ObsidianGraphView graph={brain.graph} />
        </section>
      </main>
    </div>
  );
}
