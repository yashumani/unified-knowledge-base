import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useBrainState } from "../hooks/useBrainState";
import type { ContextPackRequest, IngestionPayload } from "../types";

const TITLE = "Support Handoff Time Definition";
const SOURCE =
  "Support Handoff Time is the elapsed time between a support case being reassigned from first-line support to specialist support. It is owned by Support Operations and appears in the Service Quality Review. Cases waiting for a customer response are excluded. Recently reassigned cases may take 12 hours to reconcile before the metric is final.";
const QUESTION = "What is Support Handoff Time, and what caveat should an AI mention?";

type Stage = "source" | "review" | "ask" | "result";

export function GuidedDemoV2({ onOpenAdvanced }: { onOpenAdvanced: () => void }) {
  const brain = useBrainState();
  const [stage, setStage] = useState<Stage>("source");
  const [content, setContent] = useState(SOURCE);
  const [question, setQuestion] = useState(QUESTION);
  const [submittedTitle, setSubmittedTitle] = useState<string | null>(null);
  const [busy, setBusy] = useState<"submit" | "enrich" | "publish" | "ask" | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const enriched = useRef(new Set<string>());

  const createdReview = useMemo(
    () =>
      submittedTitle
        ? [...brain.reviewItems]
            .filter((item) => item.candidate_object.title === submittedTitle)
            .sort((a, b) => b.created_at.localeCompare(a.created_at))[0]
        : undefined,
    [brain.reviewItems, submittedTitle]
  );
  const createdObject = useMemo(
    () =>
      submittedTitle
        ? [...brain.objects]
            .filter((item) => item.title === submittedTitle)
            .sort((a, b) => b.updated_at.localeCompare(a.updated_at))[0]
        : undefined,
    [brain.objects, submittedTitle]
  );

  useEffect(() => {
    if (stage !== "review" || !createdReview || createdReview.ai_enrichment || enriched.current.has(createdReview.id)) return;
    enriched.current.add(createdReview.id);
    setBusy("enrich");
    brain.enrichReview(createdReview.id)
      .catch((error: unknown) => setActionError(error instanceof Error ? error.message : "Enrichment failed."))
      .finally(() => setBusy(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [createdReview?.id, createdReview?.ai_enrichment, stage]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy("submit");
    setActionError(null);
    try {
      const payload: IngestionPayload = {
        title: TITLE,
        domain: "support",
        owner: "Support Operations",
        source_type: "document",
        submitted_by: "guided.demo",
        content,
        sensitivity: "internal",
        tags: ["guided-demo", "support", "synthetic"]
      };
      await brain.submitContext(payload);
      setSubmittedTitle(TITLE);
      setStage("review");
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "The source could not be submitted.");
    } finally {
      setBusy(null);
    }
  }

  async function approveAndPublish() {
    if (!createdReview) return;
    setBusy("publish");
    setActionError(null);
    try {
      await brain.approveAndPublishReview(
        createdReview.id,
        "Approved and explicitly published from the guided demonstration."
      );
      setConfirming(false);
      setStage("ask");
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "The candidate could not be published.");
    } finally {
      setBusy(null);
    }
  }

  async function ask(event: FormEvent) {
    event.preventDefault();
    setBusy("ask");
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
      setBusy(null);
    }
  }

  function reset() {
    if (brain.demoMode) brain.restartDemo();
    setStage("source");
    setContent(SOURCE);
    setQuestion(QUESTION);
    setSubmittedTitle(null);
    setConfirming(false);
    setActionError(null);
    enriched.current.clear();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const step = stage === "source" ? 0 : stage === "review" ? 1 : 2;
  const contextPack = brain.contextPack;

  return (
    <div className="guided-page">
      <a className="skip-link" href="#guided-workflow">Skip to the guided workflow</a>
      <header className="guided-nav">
        <a href="#guided-top" className="guided-brand"><span>UKB</span><strong>Guided demo</strong></a>
        <div className="guided-nav-actions">
          <span className={brain.demoMode ? "guided-runtime is-demo" : "guided-runtime"}>
            {brain.loading ? "Checking runtime" : brain.demoMode ? "Browser demo" : "Connected backend"}
          </span>
          <button type="button" className="guided-secondary" onClick={onOpenAdvanced}>Advanced console</button>
        </div>
      </header>

      <main>
        <section className="guided-hero" id="guided-top">
          <div>
            <p className="guided-kicker">The shortest governed path</p>
            <h1>Turn one source into trusted AI context in three steps.</h1>
            <p>
              Add a source. Confirm the human decision. Ask the brain. UKB records approval and publication as separate governance transitions even though this wrapper keeps the demo simple.
            </p>
            <div className="guided-actions">
              <a className="guided-primary-link" href="#guided-workflow">Run the demo</a>
              <button type="button" className="guided-text-button" onClick={onOpenAdvanced}>I need every control →</button>
            </div>
          </div>
          <div className="guided-promise">
            <span>01</span><strong>Source</strong>
            <span>02</span><strong>Human approval</strong>
            <span>03</span><strong>Cited recall</strong>
          </div>
        </section>

        {brain.demoMode && (
          <section className="guided-demo-notice" role="status">
            <strong>Safe browser demo</strong><span>Everything works, nothing persists, and the sample is synthetic.</span>
          </section>
        )}
        {(brain.error || actionError) && <div className="guided-error" role="alert">{actionError ?? brain.error}</div>}

        <section className="guided-workflow" id="guided-workflow">
          <header className="guided-workflow-header">
            <div><p className="guided-kicker">One task at a time</p><h2>Source → Approve + Publish → Ask</h2></div>
            <button type="button" className="guided-reset" onClick={reset}>Reset demo</button>
          </header>
          <ol className="guided-progress" aria-label="Guided workflow progress">
            {["Add source", "Approve memory", "Ask the brain"].map((label, index) => (
              <li key={label} className={index < step ? "is-complete" : index === step ? "is-current" : ""}>
                <span>{index < step ? "✓" : index + 1}</span><strong>{label}</strong>
              </li>
            ))}
          </ol>

          <div className="guided-stage" aria-live="polite">
            {stage === "source" && (
              <form className="guided-source-card" onSubmit={submit}>
                <div className="guided-stage-heading">
                  <span>Step 1 of 3</span><h3>Add one source</h3>
                  <p>The source becomes immutable evidence and a review candidate, never immediate truth.</p>
                </div>
                <div className="guided-source-title"><span>Source title</span><strong>{TITLE}</strong></div>
                <label>Source context<textarea rows={8} value={content} onChange={(event) => setContent(event.target.value)} required /></label>
                <button type="submit" className="guided-primary" disabled={busy === "submit" || !content.trim()}>
                  {busy === "submit" ? "Creating candidate…" : "Create review candidate"}
                </button>
              </form>
            )}

            {stage === "review" && (
              <article className="guided-review-card">
                <div className="guided-stage-heading">
                  <span>Step 2 of 3 · Human gate</span><h3>Approve what the AI may remember</h3>
                  <p>The model prepares a schema-validated brief. The confirmation below records approval and then publication.</p>
                </div>
                {!createdReview && <div className="guided-loading"><span />Creating evidence-backed candidate…</div>}
                {createdReview && (
                  <>
                    <div className="guided-candidate-summary">
                      <div><span>Candidate</span><strong>{createdReview.candidate_object.title}</strong></div>
                      <div><span>Type</span><strong>{createdReview.candidate_object.type}</strong></div>
                      <div><span>Owner</span><strong>{createdReview.candidate_object.owner ?? "Needs review"}</strong></div>
                    </div>
                    <blockquote>{createdReview.candidate_object.summary}</blockquote>
                    <div className="guided-ai-brief">
                      <span>AI review brief · advisory only</span>
                      {busy === "enrich" && !createdReview.ai_enrichment && <p>Checking clarity, caveats, ownership, and evidence…</p>}
                      {createdReview.ai_enrichment ? (
                        <>
                          <p>{createdReview.ai_enrichment.review_brief.summary}</p>
                          {createdReview.ai_enrichment.validation_findings[0] && (
                            <div className="guided-finding">
                              <strong>{createdReview.ai_enrichment.validation_findings[0].severity} check</strong>
                              <span>{createdReview.ai_enrichment.validation_findings[0].message}</span>
                            </div>
                          )}
                        </>
                      ) : busy !== "enrich" ? <p>No AI brief is available; review may continue from evidence.</p> : null}
                    </div>
                    {!confirming ? (
                      <div className="guided-decision-row">
                        <button type="button" className="guided-primary" onClick={() => setConfirming(true)}>Approve and publish this memory</button>
                        <button type="button" className="guided-text-button" onClick={onOpenAdvanced}>Open full review controls →</button>
                      </div>
                    ) : (
                      <div className="guided-confirm" role="group" aria-label="Confirm publication">
                        <div><strong>Approve, then publish this candidate?</strong><span>Two auditable state transitions will be recorded.</span></div>
                        <button type="button" className="guided-primary" onClick={approveAndPublish} disabled={busy === "publish"}>
                          {busy === "publish" ? "Publishing…" : "Yes, publish it"}
                        </button>
                        <button type="button" className="guided-secondary" onClick={() => setConfirming(false)}>Keep reviewing</button>
                      </div>
                    )}
                  </>
                )}
              </article>
            )}

            {stage === "ask" && (
              <form className="guided-ask-card" onSubmit={ask}>
                <div className="guided-stage-heading">
                  <span>Step 3 of 3</span><h3>Ask the approved brain</h3>
                  <p>Only published objects and permission-allowed evidence can enter the context pack.</p>
                </div>
                <div className="guided-published-note"><span>Published memory</span><strong>{createdObject?.title ?? submittedTitle}</strong></div>
                <label>Question<input value={question} onChange={(event) => setQuestion(event.target.value)} required /></label>
                <button type="submit" className="guided-primary" disabled={busy === "ask" || !question.trim()}>
                  {busy === "ask" ? "Building governed context…" : "Build the context pack"}
                </button>
              </form>
            )}

            {stage === "result" && contextPack && (
              <article className="guided-result-card">
                <div className="guided-result-status"><span>{contextPack.access_decision}</span><strong>{Math.round(contextPack.confidence * 100)}% confidence</strong></div>
                <div className="guided-stage-heading">
                  <span>Demo complete</span><h3>The AI receives governed context—not a pile of files.</h3><p>{contextPack.answer_guidance}</p>
                </div>
                {contextPack.ai_guidance && <div className="guided-result-block"><span>Guidance for the downstream AI</span><p>{contextPack.ai_guidance}</p></div>}
                <div className="guided-result-grid">
                  <div>
                    <span>Evidence used</span>
                    <ul>
                      {(contextPack.citations?.length ? contextPack.citations : contextPack.evidence).slice(0, 3).map((item) => (
                        "citation_id" in item
                          ? <li key={item.citation_id}><strong>{item.title}</strong><p>{item.quote}</p></li>
                          : <li key={item.source_id}><strong>{item.title}</strong><p>{item.content_excerpt}</p></li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <span>Caveats and next checks</span>
                    <ul>{[...contextPack.caveats, ...(contextPack.conflicts ?? []), ...contextPack.missing_context].slice(0, 5).map((item) => <li key={item}>{item}</li>)}</ul>
                  </div>
                </div>
                <div className="guided-actions"><button type="button" className="guided-primary" onClick={reset}>Run it again</button><button type="button" className="guided-secondary" onClick={onOpenAdvanced}>Open advanced console</button></div>
              </article>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
