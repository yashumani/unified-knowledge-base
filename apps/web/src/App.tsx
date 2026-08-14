import { API_BASE } from "./api/brainClient";
import { ObsidianGraphView } from "./components/ObsidianGraphView";
import { Hero } from "./components/Hero";
import { SideNav } from "./components/SideNav";
import { StatsGrid } from "./components/StatsGrid";
import { ComposeStep } from "./components/steps/ComposeStep";
import { PublishStep } from "./components/steps/PublishStep";
import { ReviewStep } from "./components/steps/ReviewStep";
import { SubmitStep } from "./components/steps/SubmitStep";
import { useBrainState } from "./hooks/useBrainState";

export default function App() {
  const brain = useBrainState();

  return (
    <div className="site-shell">
      <a className="skip-link" href="#pipeline">Skip to the workflow</a>

      <SideNav aiStatus={brain.aiStatus} />

      <main className="app-shell" id="main">
        {brain.demoMode && (
          <div className="mode-banner" role="status">
            <strong>Demo Mode</strong>
            <span>No backend connected. Actions are simulated and reset on refresh.</span>
          </div>
        )}

        <Hero
          demoMode={brain.demoMode}
          environment={brain.environment}
          apiBase={API_BASE}
          loading={brain.loading}
          onRefresh={brain.refresh}
        />

        {brain.error && <div className="notice" role="alert">{brain.error}</div>}

        <StatsGrid
          published={brain.stats.published}
          review={brain.stats.review}
          enrichedReviews={brain.stats.enrichedReviews}
          graphEdges={brain.stats.graphEdges}
        />

        <section id="brain-map" className="section-shell" aria-labelledby="brain-map-heading">
          <div className="section-heading">
            <p className="eyebrow">Visual knowledge runtime</p>
            <h2 id="brain-map-heading">Inspect the brain before trusting the answer</h2>
            <p>
              Use the map to trace source evidence, review state, published knowledge, and graph relationships.
            </p>
          </div>
          <ObsidianGraphView graph={brain.graph} />
        </section>

        {/* Was a second <main>, which produced two main landmarks. */}
        <section className="workbench" id="pipeline" aria-label="Governance workflow">
          <SubmitStep onSubmit={brain.submitContext} demoMode={brain.demoMode} />
          <ReviewStep
            items={brain.reviewItems}
            onApprove={brain.approveReview}
            onReject={brain.rejectReview}
            onEnrich={brain.enrichReview}
            demoMode={brain.demoMode}
          />
          <ComposeStep
            onAsk={brain.askBrain}
            contextPack={brain.contextPack}
            demoMode={brain.demoMode}
          />
          <PublishStep objects={brain.objects} />
        </section>
      </main>
    </div>
  );
}
