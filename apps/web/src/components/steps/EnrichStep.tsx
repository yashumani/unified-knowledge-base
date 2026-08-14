import { useEffect, useState } from "react";
import type { AIProviderStatus, ReviewItem } from "../../types";

const MODE_EXPLANATION: Record<string, string> = {
  offline_no_model: "No model runtime is connected. Deterministic offline checks only.",
  local_ai: "A local model runtime performs enrichment. Nothing leaves this machine.",
  hosted_ai: "A hosted model performs enrichment. Restricted material is withheld from it.",
  hybrid: "Local and hosted providers are both configured."
};

/**
 * Step 2 had no home before this: enrichment existed only as a button hidden
 * inside the review inspector, behind a condition that removed it in demo mode
 * — which is the only mode the public build ever runs in.
 */
export function EnrichStep({
  items,
  aiStatus,
  onEnrich,
  enrichingId
}: {
  items: ReviewItem[];
  aiStatus: AIProviderStatus;
  onEnrich: (id: string) => Promise<void>;
  enrichingId: string | null;
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

  const selected = selectedId ? items.find((item) => item.id === selectedId) : undefined;
  const enrichment = selected?.ai_enrichment;
  const busy = enrichingId !== null;

  return (
    <div className="panel">
      <div className="provider-strip">
        <div>
          <span className="provider-label">Enrichment provider</span>
          <strong>{aiStatus.provider} · {aiStatus.model}</strong>
          <p>{MODE_EXPLANATION[aiStatus.mode] ?? aiStatus.mode}</p>
        </div>
        <dl>
          <div><dt>Status</dt><dd>{aiStatus.enabled ? "Enabled" : "Disabled by server"}</dd></div>
          <div><dt>Runs locally</dt><dd>{aiStatus.local_only === false ? "No" : "Yes"}</dd></div>
          {aiStatus.embedding_model && (
            <div><dt>Embeddings</dt><dd>{aiStatus.embedding_model}</dd></div>
          )}
        </dl>
      </div>

      {aiStatus.capabilities && aiStatus.capabilities.length > 0 && (
        <ul className="capability-list">
          {aiStatus.capabilities.map((capability) => (
            <li key={capability} className="chip">{capability.replace(/_/g, " ")}</li>
          ))}
        </ul>
      )}

      <div className="review-layout">
        <ul className="scroll-list">
          {items.length === 0 && (
            <li className="empty-state">No candidates yet. Submit context to create one.</li>
          )}
          {items.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className={selectedId === item.id ? "review-item selected-review" : "review-item"}
                aria-pressed={selectedId === item.id}
                onClick={() => setSelectedId(item.id)}
              >
                <span className="badge">{item.candidate_object.type}</span>
                <strong>{item.candidate_object.title}</strong>
                <small>{item.ai_enrichment ? "Brief ready" : "No brief yet"}</small>
              </button>
            </li>
          ))}
        </ul>

        <aside className="candidate-inspector" aria-busy={busy}>
          {!selected && <div className="empty-state">Select a candidate to enrich.</div>}
          {selected && (
            <>
              <span className="badge">Candidate</span>
              <h3>{selected.candidate_object.title}</h3>
              {!enrichment && (
                <p className="panel-copy">
                  No brief has been generated for this candidate. Enrichment is optional —
                  a reviewer may approve from the source evidence alone.
                </p>
              )}
              {enrichment && (
                <div className="ai-brief">
                  <div className="ai-brief-header">
                    <strong>AI review brief</strong>
                    <span>{enrichment.provider} · {enrichment.model}</span>
                  </div>
                  <p>{enrichment.review_brief.summary}</p>
                  {enrichment.validation_findings.length > 0 && (
                    <ul className="finding-list">
                      {enrichment.validation_findings.map((finding) => (
                        <li
                          key={`${finding.finding_type}-${finding.message}`}
                          className={`finding finding-${finding.severity}`}
                        >
                          <strong>{finding.severity}</strong>
                          <span>{finding.message}</span>
                          {finding.source_span && (
                            <blockquote className="finding-span">{finding.source_span}</blockquote>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                  {enrichment.review_brief.reviewer_questions.length > 0 && (
                    <div className="question-stack">
                      <strong>Questions to answer before approving</strong>
                      {enrichment.review_brief.reviewer_questions.map((question) => (
                        <span key={question}>{question}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
              <div className="actions">
                <button
                  type="button"
                  onClick={() => onEnrich(selected.id)}
                  disabled={busy || !aiStatus.enabled}
                >
                  {enrichingId === selected.id
                    ? "Analyzing source…"
                    : enrichment
                      ? "Run enrichment again"
                      : "Run AI enrichment"}
                </button>
              </div>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
