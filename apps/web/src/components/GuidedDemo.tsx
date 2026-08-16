import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useBrainState } from "../hooks/useBrainState";
import type { ContextPackRequest, IngestionPayload } from "../types";

const SAMPLE_TITLE = "Support Handoff Time Definition";
const SAMPLE_CONTENT =
  "Support Handoff Time is the elapsed time between a support case being reassigned from first-line support to specialist support. It is owned by Support Operations and appears in the Service Quality Review. Cases waiting for a customer response are excluded. Recently reassigned cases may take 12 hours to reconcile before the metric is final.";
const SAMPLE_QUESTION =
  "What is Support Handoff Time, and what caveat should an AI mention?";

type GuidedStage = "source" | "review" | "ask" | "result";

const STEP_INDEX: Record<GuidedStage, number> = {
  source: 0,
  review: 1,
  ask: 2,
  result: 2
};

export function GuidedDemo({ onOpenAdvanced }: { onOpenAdvanced: () => void }) {
  const brain = useBrainState();
  const [stage, setStage] = useState<GuidedStage>("source");
  const [content, setContent] = useState(SAMPLE_CONTENT);
  const [question, setQuestion] = useState(SAMPLE_QUESTION);
  const [submittedTitle, setSubmittedTitle] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [approving, setApproving] = useState(false);
  const [asking, setAsking] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const enrichmentStarted = useRef(new Set<string>());

  const createdReview = useMemo(() => {
    if (!submittedTitle) return undefined;
    return [...brain.reviewItems]
      .filter((item) => item.candidate_object.title === submittedTitle)
      .sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
  }, [brain.reviewItems, submittedTitle]);

  const createdObject = useMemo(() => {
    if (!submittedTitle) return undefined;
    return [...brain.objects]
      .filter((item) => item.title === submittedTitle)
      .sort((a, b) => b.updated_at.localeCompare(a.updated_at))[0];
  }, [brain.objects, submittedTitle]);

  useEffect(() => {
    if (
      stage !== "review" ||
      !createdReview ||
      createdReview.ai_enrichment ||
      enrichmentStarted.current.has(createdReview.id)
    ) {
      return;
    }

    enrichmentStarted.current.add(createdReview.id);
    setEnriching(true);
    setActionError(null);
    brain
      .enrichReview(createdReview.id)
      .catch((error: unknown) => {
        setActionError(
          error instanceof Error
            ? error.message
            : "The enrichment brief could not be generated. You can still review the source."
        );
      })
      .finally(() => setEnriching(false));
    // The action is intentionally keyed to the created review item rather than
    // the hook function identity, which changes whenever brain state refreshes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [createdReview?.id, createdReview?.ai_enrichment, stage]);

  async function submitSource(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setActionError(null);
    try {
      const payload: IngestionPayload = {
        title: SAMPLE_TITLE,
        domain: "support",
        source_type: "document",
        submitted_by: "guided.demo",
        content,
        sensitivity: "internal",
        tags: ["guided-demo", "support", "synthetic"]
      };
      await brain.submitContext(payload);
      setSubmittedTitle(SAMPLE_TITLE);
      setStage("review");
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "The source could not be submitted.");
    } finally {
      setSubmitting(false);
    }
  }

  async function approveCandidate() {
    if (!createdReview) return;
    setApproving(true);
    setActionError(null);
    try {
      await brain.approveReview(
        createdReview.id,
        "Reviewed and approved from the guided three-step demo."
      );
      setConfirming(false);
      setStage("ask");
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "The candidate could not be approved.");
    } finally {
      setApproving(false);
    }
  }

  async function askBrain(event: FormEvent) {
    event.preventDefault();
    setAsking(true);
    setActionError(null);
    try {
      const request: ContextPackRequest = {
        question,
        user_id: "guided.consumer",
        domains: ["support"],
        mode: "metric_definition"
      };
      await brain.askBrain(request);
      setStage("result");
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "The context pack could not be built.");
    } finally {
      setAsking(false);
    }
  }

  function resetDemo() {
    if (brain.demoMode) brain.restartDemo();
    setStage("source");
    setContent(SAMPLE_CONTENT);
    setQuestion(SAMPLE_QUESTION);
    setSubmittedTitle(null);
    setConfirming(false);
    setActionError(null);
    enrichmentStarted.current.clear();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const currentStep = STEP_INDEX[stage];
  const enrichment = createdReview?.ai_enrichment;
  const contextPack = brain.contextPack;

  return (
    <div className="guided-page">
      <a className="skip-link" href="#guided-workflow">Skip to the guided workflow</a>

      <header className="guided-nav">
        <a href="#guided-top" className="guided-brand" aria-label="Unified Knowledge Base guided demo home">
          <span>UKB</span>
          <strong>Guided demo</strong>
        </a>
        <div className="guided-nav-actions">
          <span className={brain.demoMode ? "guided-runtime is-demo" : "guided-runtime"}>
            {brain.loading ? "Checking runtime" : brain.demoMode ? "Browser demo" : "Connected backend"}
          </span>
          <button type="button" className="guided-secondary" onClick={onOpenAdvanced}>
            Advanced console
          </button>
        </div>
      </header>

      <main>
        <section className="guided-hero" id="guided-top" aria-labelledby="guided-title">
          <div>
            <p className="guided-kicker">The shortest governed path</p>
            <h1 id="guided-title">Turn one source into trusted AI context in three steps.</h1>
            <p>
              Add a source. Make the human decision. Ask the brain. UKB handles extraction,
              enrichment, publication, and retrieval behind the scenes without hiding the
              approval gate.
            </p>
            <div className="guided-actions">
              <a className="guided-primary-link" href="#guided-workflow">Run the 2-minute demo</a>
              <button type="button" className="guided-text-button" onClick={onOpenAdvanced}>
                I need every control →
              </button>
            </div>
          </div>
          <div className="guided-promise" aria-label="Guided demo principles">
            <span>01</span>
            <strong>Source</strong>
            <span>02</span>
            <strong>Human approval</strong>
            <span>03</span>
            <strong>Evidence-backed recall</strong>
          </div>
        </section>

        {brain.demoMode && (
          <section className="guided-demo-notice" role="status">
            <strong>Safe browser demo</strong>
            <span>Everything works, nothing persists, and the sample is fully synthetic.</span>
          </section>
        )}

        {(brain.error || actionError) && (
          <div className="guided-error" role="alert">{actionError ?? brain.error}</div>
        )}

        <section className="guided-workflow" id="guided-workflow" aria-labelledby="guided-workflow-title">
          <header className="guided-workflow-header">
            <div>
              <p className="guided-kicker">One task at a time</p>
              <h2 id="guided-workflow-title">Source → Approve → Ask</h2>
            </div>
            <button type="button" className="guided-reset" onClick={resetDemo}>Reset demo</button>
          </header>

          <ol className="guided-progress" aria-label="Guided workflow progress">
            {["Add source", "Approve memory", "Ask the brain"].map((label, index) => (
              <li
                key={label}
                className={index < currentStep ? "is-complete" : index === currentStep ? "is-current" : ""}
                aria-current={index === currentStep ? "step" : undefined}
              >
                <span>{index < currentStep ? "✓" : index + 1}</span>
                <strong>{label}</strong>
              </li>
            ))}
          </ol>

          <div className="guided-stage" aria-live="polite">
            {stage === "source" && (
              <form className="guided-source-card" onSubmit={submitSource}>
                <div className="guided-stage-heading">
                  <span>Step 1 of 3</span>
                  <h3>Add one source</h3>
                  <p>
                    The sample is ready. Read it, edit it if useful, then create a candidate.
                    It will not become trusted memory yet.
                  </p>
                </div>
                <div className="guided-source-title">
                  <span>Source title</span>
                  <strong>{SAMPLE_TITLE}</strong>
                </div>
                <label>
                  Source context
                  <textarea
                    rows={8}
                    value={content}
                    onChange={(event) => setContent(event.target.value)}
                    required
                  />
                </label>
                <button type="submit" className="guided-primary" disabled={submitting || !content.trim()}>
                  {submitting ? "Creating candidate…" : "Create review candidate"}
                </button>
                <p className="guided-footnote">Behind the scenes: evidence capture + classification.</p>
              </form>
            )}

            {stage === "review" && (
              <article className="guided-review-card">
                <div className="guided-stage-heading">
                  <span>Step 2 of 3 · Human gate</span>
                  <h3>Approve what the AI may remember</h3>
                  <p>
                    The model can prepare the brief. Only you can publish the candidate.
                  </p>
                </div>

                {!createdReview && (
                  <div className="guided-loading">
                    <span />
                    Creating the candidate and attaching source evidence…
                  </div>
                )}

                {createdReview && (
                  <>
                    <div className="guided-candidate-summary">
                      <div>
                        <span>Candidate</span>
                        <strong>{createdReview.candidate_object.title}</strong>
                      </div>
                      <div>
                        <span>Type</span>
                        <strong>{createdReview.candidate_object.type}</strong>
                      </div>
                      <div>
                        <span>Owner</span>
                        <strong>{createdReview.candidate_object.owner ?? "Needs review"}</strong>
                      </div>
                    </div>

                    <blockquote>{createdReview.candidate_object.summary}</blockquote>

                    <div className="guided-ai-brief">
                      <span>AI review brief · advisory only</span>
                      {enriching && !enrichment && <p>Checking clarity, caveats, ownership, and evidence…</p>}
                      {!enriching && !enrichment && (
                        <p>No AI brief is available. The source evidence is still sufficient for a human decision.</p>
                      )}
                      {enrichment && (
                        <>
                          <p>{enrichment.review_brief.summary}</p>
                          {enrichment.validation_findings[0] && (
                            <div className="guided-finding">
                              <strong>{enrichment.validation_findings[0].severity} check</strong>
                              <span>{enrichment.validation_findings[0].message}</span>
                            </div>
                          )}
                        </>
                      )}
                    </div>

                    {!confirming ? (
                      <div className="guided-decision-row">
                        <button type="button" className="guided-primary" onClick={() => setConfirming(true)}>
                          Approve and publish this memory
                        </button>
                        <button type="button" className="guided-text-button" onClick={onOpenAdvanced}>
                          Open full review controls →
                        </button>
                      </div>
                    ) : (
                      <div className="guided-confirm" role="group" aria-label="Confirm publication">
                        <div>
                          <strong>Publish this candidate?</strong>
                          <span>It becomes approved context available to retrieval.</span>
                        </div>
                        <button type="button" className="guided-primary" onClick={approveCandidate} disabled={approving}>
                          {approving ? "Publishing…" : "Yes, publish it"}
                        </button>
                        <button type="button" className="guided-secondary" onClick={() => setConfirming(false)}>
                          Keep reviewing
                        </button>
                      </div>
                    )}
                  </>
                )}
                <p className="guided-footnote">Behind the scenes: local enrichment + human review + publication.</p>
              </article>
            )}

            {stage === "ask" && (
              <form className="guided-ask-card" onSubmit={askBrain}>
                <div className="guided-stage-heading">
                  <span>Step 3 of 3</span>
                  <h3>Ask the approved brain</h3>
                  <p>
                    Retrieval can now use the memory you approved. The output remains a governed
                    context pack, not an invented final answer.
                  </p>
                </div>
                <div className="guided-published-note">
                  <span>Published memory</span>
                  <strong>{createdObject?.title ?? submittedTitle}</strong>
                </div>
                <label>
                  Question
                  <input value={question} onChange={(event) => setQuestion(event.target.value)} required />
                </label>
                <button type="submit" className="guided-primary" disabled={asking || !question.trim()}>
                  {asking ? "Building governed context…" : "Build the context pack"}
                </button>
                <p className="guided-footnote">Behind the scenes: approved retrieval + evidence packaging.</p>
              </form>
            )}

            {stage === "result" && contextPack && (
              <article className="guided-result-card">
                <div className="guided-result-status">
                  <span>{contextPack.access_decision}</span>
                  <strong>{Math.round(contextPack.confidence * 100)}% confidence</strong>
                </div>
                <div className="guided-stage-heading">
                  <span>Demo complete</span>
                  <h3>The AI receives governed context—not a pile of files.</h3>
                  <p>{contextPack.answer_guidance}</p>
                </div>
                {contextPack.ai_guidance && (
                  <div className="guided-result-block">
                    <span>Guidance for the downstream AI</span>
                    <p>{contextPack.ai_guidance}</p>
                  </div>
                )}
                <div className="guided-result-grid">
                  <div>
                    <span>Evidence used</span>
                    <ul>
                      {contextPack.evidence.slice(0, 3).map((evidence) => (
                        <li key={`${evidence.source_id}-${evidence.title}`}>
                          <strong>{evidence.title}</strong>
                          <p>{evidence.content_excerpt}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <span>Caveats and next checks</span>
                    <ul>
                      {[...contextPack.caveats, ...contextPack.missing_context]
                        .slice(0, 4)
                        .map((item) => <li key={item}>{item}</li>)}
                    </ul>
                  </div>
                </div>
                <div className="guided-actions">
                  <button type="button" className="guided-primary" onClick={resetDemo}>Run it again</button>
                  <button type="button" className="guided-secondary" onClick={onOpenAdvanced}>
                    Inspect the advanced console
                  </button>
                </div>
              </article>
            )}

            {stage === "result" && !contextPack && (
              <div className="guided-loading"><span />Building the context pack…</div>
            )}
          </div>
        </section>

        <section className="guided-behind-scenes" aria-labelledby="guided-behind-title">
          <div>
            <p className="guided-kicker">Simple on top, complete underneath</p>
            <h2 id="guided-behind-title">Three user decisions. Five governed operations.</h2>
          </div>
          <ol>
            <li><span>1</span><strong>Submit</strong><small>Capture source evidence</small></li>
            <li><span>2</span><strong>Enrich</strong><small>Generate an advisory brief</small></li>
            <li><span>3</span><strong>Review</strong><small>Human approval gate</small></li>
            <li><span>4</span><strong>Publish</strong><small>Create official memory</small></li>
            <li><span>5</span><strong>Compose</strong><small>Build the context pack</small></li>
          </ol>
          <p>
            The guided path combines operations that do not require a decision. The advanced console
            keeps every field, alternate action, graph control, and audit detail available separately.
          </p>
        </section>
      </main>

      <footer className="guided-footer">
        <div><strong>UKB</strong><span>Unified Knowledge Base</span></div>
        <button type="button" className="guided-text-button" onClick={onOpenAdvanced}>
          Open advanced console →
        </button>
        <a href="https://github.com/yashumani/unified-knowledge-base" target="_blank" rel="noreferrer">
          GitHub ↗
        </a>
      </footer>
    </div>
  );
}
