import { useEffect, useRef, useState } from "react";
import { ConfirmAction } from "../common/ConfirmAction";
import { ReviewSignal } from "../common/ReviewSignal";
import { StatusPill } from "../common/StatusPill";
import { formatRelative } from "../../utils/format";
import type { ReviewItem } from "../../types";

export function ReviewStep({
  items,
  reviewer,
  onApprove,
  onReject,
  onRequestChanges,
  demoMode
}: {
  items: ReviewItem[];
  reviewer: string;
  onApprove: (id: string, comment: string | null) => Promise<void>;
  onReject: (id: string, comment: string | null) => Promise<void>;
  onRequestChanges: (id: string, comment: string | null) => Promise<void>;
  demoMode: boolean;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(items[0]?.id ?? null);
  const [comment, setComment] = useState("");
  const previousNewestId = useRef<string | null>(items[0]?.id ?? null);

  useEffect(() => {
    const newestId = items[0]?.id ?? null;
    if (!newestId) {
      previousNewestId.current = null;
      setSelectedId(null);
      return;
    }

    // Keep the end-to-end thread intact: when submission inserts a new item at
    // the front of the queue, review that item instead of retaining an older
    // seeded selection.
    if (newestId !== previousNewestId.current) {
      previousNewestId.current = newestId;
      setSelectedId(newestId);
      return;
    }

    if (!selectedId || !items.some((item) => item.id === selectedId)) {
      setSelectedId(newestId);
    }
  }, [items, selectedId]);

  // A comment belongs to the candidate being judged, not to the panel.
  useEffect(() => setComment(""), [selectedId]);

  const selectedItem = selectedId ? items.find((item) => item.id === selectedId) : undefined;
  const enrichment = selectedItem?.ai_enrichment;
  const trimmed = comment.trim();
  const needsComment = trimmed.length === 0;

  async function act(
    handler: (id: string, comment: string | null) => Promise<void>,
    id: string
  ) {
    await handler(id, trimmed || null);
    setComment("");
  }

  return (
    <div className="panel review-panel">
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
                <span className="review-item-meta">
                  <StatusPill status={item.status} />
                  <small>
                    {item.ai_enrichment ? "AI brief attached" : "No AI brief"} ·{" "}
                    {formatRelative(item.created_at)}
                  </small>
                </span>
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

              <ReviewSignal confidence={selectedItem.candidate_object.confidence} />

              {enrichment && (
                <div className="ai-brief">
                  <div className="ai-brief-header">
                    <strong>AI review brief</strong>
                    <span>{enrichment.provider} · {enrichment.model}</span>
                  </div>
                  <p>{enrichment.review_brief.summary}</p>
                  <p className="advisory">
                    <strong>
                      AI suggests: {enrichment.review_brief.recommended_action.replace(/_/g, " ")}
                    </strong>
                    {" — advisory only. The decision below is yours."}
                  </p>
                </div>
              )}

              {!enrichment && (
                <p className="step-locked" role="note">
                  No AI brief was generated for this candidate. Approving is allowed — the
                  decision is yours — and the activity log records that it happened without one.
                </p>
              )}

              <dl>
                <div><dt>Status</dt><dd><StatusPill status={selectedItem.status} /></dd></div>
                <div><dt>Domain</dt><dd>{selectedItem.candidate_object.domain}</dd></div>
                <div>
                  <dt>Owner</dt>
                  <dd>{selectedItem.candidate_object.owner ?? "Not assigned"}</dd>
                </div>
                <div><dt>Sensitivity</dt><dd>{selectedItem.candidate_object.sensitivity}</dd></div>
                <div><dt>Submitted</dt><dd>{formatRelative(selectedItem.created_at)}</dd></div>
                <div><dt>Acting as</dt><dd>{reviewer}</dd></div>
              </dl>

              {!selectedItem.candidate_object.owner && (
                <button
                  type="button"
                  className="secondary"
                  onClick={() =>
                    setComment(
                      "Please assign a responsible owner before this is published."
                    )
                  }
                >
                  Request changes to assign an owner
                </button>
              )}

              {selectedItem.review_comment && (
                <p className="prior-comment">
                  <strong>{selectedItem.reviewer ?? "Reviewer"} said:</strong>{" "}
                  {selectedItem.review_comment}
                </p>
              )}

              <label>
                Reviewer comment
                <textarea
                  value={comment}
                  rows={3}
                  onChange={(event) => setComment(event.target.value)}
                  placeholder="Required when rejecting or requesting changes."
                />
              </label>

              <div className="actions">
                <ConfirmAction
                  label={demoMode ? "Simulate approval" : "Approve and publish"}
                  confirmLabel="Confirm approval"
                  onConfirm={() => act(onApprove, selectedItem.id)}
                />
                <ConfirmAction
                  label="Request changes"
                  confirmLabel="Confirm request"
                  tone="secondary"
                  disabled={needsComment}
                  disabledReason="Add a comment explaining what needs to change."
                  onConfirm={() => act(onRequestChanges, selectedItem.id)}
                />
                <ConfirmAction
                  label={demoMode ? "Simulate rejection" : "Reject"}
                  confirmLabel="Confirm rejection"
                  tone="secondary"
                  disabled={needsComment}
                  disabledReason="Add a comment explaining the rejection."
                  onConfirm={() => act(onReject, selectedItem.id)}
                />
              </div>
              {needsComment && (
                <small className="action-hint">
                  Approving may proceed without a comment. Rejecting or requesting changes
                  needs one, because a negative decision has to be explainable later.
                </small>
              )}
            </>
          ) : (
            <div className="empty-state">Select a candidate to inspect before approving.</div>
          )}
        </aside>
      </div>
    </div>
  );
}
