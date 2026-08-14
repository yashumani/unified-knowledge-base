import { useEffect, useState } from "react";
import type { ReviewItem } from "../../types";

export function ReviewStep({
  items,
  onApprove,
  onReject,
  onEnrich,
  demoMode
}: {
  items: ReviewItem[];
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string) => Promise<void>;
  onEnrich: (id: string) => Promise<void>;
  demoMode: boolean;
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

  const selectedItem = selectedId ? items.find((item) => item.id === selectedId) : undefined;
  const enrichment = selectedItem?.ai_enrichment;

  return (
    <section className="panel review-panel" id="review-queue">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Human validation</p>
          <h2>Review queue</h2>
        </div>
        <span className="chip warning-chip">{items.length} pending</span>
      </div>
      <div className="review-layout">
        <ul className="scroll-list">
          {items.length === 0 && (
            <li className="empty-state">No candidate knowledge is waiting for review.</li>
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
                <small>
                  {item.status} · {Math.round(item.candidate_object.confidence * 100)}% confidence ·{" "}
                  {item.ai_enrichment ? "AI brief" : "No AI brief"}
                </small>
              </button>
            </li>
          ))}
        </ul>
        <aside className="candidate-inspector">
          {selectedItem ? (
            <>
              <span className="badge">Candidate</span>
              <h3>{selectedItem.candidate_object.title}</h3>
              <p>{selectedItem.candidate_object.summary}</p>
              {enrichment && (
                <div className="ai-brief">
                  <div className="ai-brief-header">
                    <strong>AI review brief</strong>
                    <span>{enrichment.provider} · {Math.round(enrichment.confidence * 100)}%</span>
                  </div>
                  <p>{enrichment.review_brief.summary}</p>
                  {enrichment.validation_findings.length > 0 && (
                    <ul className="finding-list">
                      {enrichment.validation_findings.slice(0, 3).map((finding) => (
                        <li
                          key={`${finding.finding_type}-${finding.message}`}
                          className={`finding finding-${finding.severity}`}
                        >
                          <strong>{finding.severity}</strong>
                          <span>{finding.message}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                  {enrichment.review_brief.reviewer_questions.length > 0 && (
                    <div className="question-stack">
                      <strong>Reviewer questions</strong>
                      {enrichment.review_brief.reviewer_questions.slice(0, 3).map((question) => (
                        <span key={question}>{question}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
              <dl>
                <div><dt>Status</dt><dd>{selectedItem.status}</dd></div>
                <div><dt>Domain</dt><dd>{selectedItem.candidate_object.domain}</dd></div>
                <div><dt>Owner</dt><dd>{selectedItem.candidate_object.owner ?? "Not assigned"}</dd></div>
              </dl>
              <div className="actions">
                {!demoMode && !enrichment && (
                  <button type="button" className="secondary" onClick={() => onEnrich(selectedItem.id)}>
                    Run AI enrichment
                  </button>
                )}
                <button type="button" onClick={() => onApprove(selectedItem.id)}>
                  {demoMode ? "Simulate approval" : "Approve and publish"}
                </button>
                <button type="button" className="secondary" onClick={() => onReject(selectedItem.id)}>
                  {demoMode ? "Simulate rejection" : "Reject"}
                </button>
              </div>
            </>
          ) : (
            <div className="empty-state">Select a candidate to inspect before approving.</div>
          )}
        </aside>
      </div>
    </section>
  );
}
