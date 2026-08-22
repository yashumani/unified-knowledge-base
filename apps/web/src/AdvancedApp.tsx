import { useState } from "react";
import { ActivityLedger } from "./components/ActivityLedger";
import { ObsidianGraphView } from "./components/ObsidianGraphView";
import { ComposeStep } from "./components/steps/ComposeStep";
import { EnrichStep } from "./components/steps/EnrichStep";
import { PublishStep } from "./components/steps/PublishStep";
import { ReviewStep } from "./components/steps/ReviewStep";
import { SubmitStep } from "./components/steps/SubmitStep";
import { REVIEWER, useBrainState } from "./hooks/useBrainState";

export default function AdvancedApp() {
  const brain = useBrainState();
  const [enrichingId, setEnrichingId] = useState<string | null>(null);

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
      <a className="skip-link" href="#pipeline">Skip to the advanced workflow</a>
      <header className="editorial-nav">
        <a className="editorial-brand" href="#advanced-top"><span>UKB</span><small>Advanced console</small></a>
        <nav aria-label="Advanced console navigation">
          <a href="#pipeline">Pipeline</a><a href="#brain-map">Memory map</a><a href="#activity">Activity</a><a href="#questions">Questions</a>
        </nav>
      </header>

      <main className="app-shell" id="advanced-top">
        <section className="editorial-hero">
          <div className="editorial-hero-copy">
            <p className="editorial-overline">Every governance control</p>
            <h1>Give AI the <span>right memory.</span></h1>
            <p className="editorial-lede">
              Inspect source evidence, run local structured enrichment, revise candidates, approve them, publish them through a separate gate, and compose citation-bearing context packs.
            </p>
          </div>
          <div className="brain-poster">
            <div className="poster-shell">
              <div className="poster-topline"><span>AUTHORITATIVE STATE</span><strong>{brain.demoMode ? "DEMO" : brain.environment}</strong></div>
              <div className="poster-number"><span>Published memory</span><strong>{String(brain.objects.length).padStart(2, "0")}</strong><small>{brain.approvedItems.length} approved candidate(s) await publication</small></div>
              <div className="poster-flow">
                <div><span>01</span><strong>Review</strong><small>{brain.reviewItems.length} open</small></div>
                <div><span>02</span><strong>Publish</strong><small>{brain.approvedItems.length} ready</small></div>
                <div><span>03</span><strong>Recall</strong><small>{brain.graph.edges.length} links</small></div>
              </div>
            </div>
          </div>
        </section>

        {brain.demoMode && (
          <section className="mode-banner editorial-mode" role="status">
            <div><strong>Browser demo mode</strong><span>All actions are simulated and reset on refresh.</span></div>
            <button type="button" className="secondary" onClick={brain.restartDemo}>Restart demo</button>
          </section>
        )}
        {brain.error && <div className="notice" role="alert">{brain.error}</div>}

        <section id="pipeline" className="pipeline editorial-pipeline" aria-label="Advanced governance workflow">
          <section className="step-section" id="context-ingestion">
            <header className="section-heading"><span>01</span><div><p>Context ingestion</p><h2>Submit source context</h2><small>Every source becomes evidence and a versioned candidate.</small></div></header>
            <SubmitStep onSubmit={brain.submitContext} demoMode={brain.demoMode} />
          </section>

          <section className="step-section" id="enrichment-lab">
            <header className="section-heading"><span>02</span><div><p>Advisory AI</p><h2>Generate the AI review brief</h2><small>Local Ollama returns schema-validated suggestions, never authority.</small></div></header>
            <EnrichStep items={brain.reviewItems} aiStatus={brain.aiStatus} onEnrich={runEnrichment} enrichingId={enrichingId} demoMode={brain.demoMode} />
          </section>

          <section className="step-section" id="review-queue">
            <header className="section-heading"><span>03</span><div><p>Human validation</p><h2>Approve without silently publishing</h2><small>Edit, reject, request changes, or move a candidate to the publisher queue.</small></div></header>
            <ReviewStep
              items={brain.reviewItems}
              reviewer={REVIEWER}
              onApprove={brain.approveReview}
              onReject={brain.rejectReview}
              onRequestChanges={brain.requestChanges}
              onRevise={brain.reviseReview}
              demoMode={brain.demoMode}
            />
          </section>

          <section className="step-section" id="published-objects">
            <header className="section-heading"><span>04</span><div><p>Official memory</p><h2>Publish approved knowledge</h2><small>Only this transition makes an object eligible for retrieval.</small></div></header>
            <PublishStep approvedItems={brain.approvedItems} objects={brain.objects} onPublish={brain.publishReview} demoMode={brain.demoMode} />
          </section>

          <section className="step-section" id="context-pack">
            <header className="section-heading"><span>05</span><div><p>Governed recall</p><h2>Compose a context pack</h2><small>Inspect citations, access decisions, confidence factors, conflicts, and answer constraints.</small></div></header>
            <ComposeStep onAsk={brain.askBrain} contextPack={brain.contextPack} demoMode={brain.demoMode} />
          </section>
        </section>

        <section id="brain-map" className="graph-story">
          <div className="graph-story-copy"><p className="editorial-overline">Permission-filtered memory</p><h2>Trace the evidence and relationships.</h2><p>The visualization is a projection over authoritative sources, versions, reviews, objects, and published relationship records.</p></div>
          <div className="graph-stage-wrap"><ObsidianGraphView graph={brain.graph} /></div>
        </section>

        <div id="activity" className="activity-story"><ActivityLedger records={brain.ledger} /></div>

        <section className="faq-section" id="questions">
          <div className="faq-heading"><p className="editorial-overline">Architecture boundaries</p><h2>The blunt answers.</h2></div>
          <div className="faq-list">
            <details><summary>Can the local model publish memory?</summary><p>No. The model can only propose structured candidates and validation findings.</p></details>
            <details><summary>Why are approval and publication separate?</summary><p>Review confirms meaning. Publication confirms that the approved version is ready to become retrievable official context.</p></details>
            <details><summary>Where does Zvec fit?</summary><p>Zvec is a disposable full-text index. SQL and private object storage remain authoritative and can rebuild it.</p></details>
          </div>
        </section>
      </main>
    </div>
  );
}
