import { formatRelative } from "../utils/format";
import type { ReviewDecisionRecord } from "../pipeline/types";

const ACTION_LABEL: Record<ReviewDecisionRecord["action"], string> = {
  approved: "Approved",
  rejected: "Rejected",
  changes_requested: "Changes requested"
};

/**
 * The governance audit surface.
 *
 * docs/GOVERNANCE_WORKFLOW.md defines an audit event vocabulary and requires
 * reviewer actions to be attributable — who, what, when, with a comment. The
 * backend records all of it and the console had no surface for any of it.
 */
export function ActivityLedger({ records }: { records: ReviewDecisionRecord[] }) {
  return (
    <section id="activity" className="section-shell" aria-labelledby="activity-heading">
      <div className="section-heading">
        <h2 id="activity-heading">
          <span className="step-kicker">Governance trail</span>
          Every decision, attributable
        </h2>
        <p>
          Each entry records who decided, what they decided, when, and why. Rejections stay
          visible here even though the candidate leaves the queue.
        </p>
      </div>

      <div className="panel wide-panel">
        {records.length === 0 ? (
          <div className="empty-state">
            No decisions yet. Approve, reject or send back a candidate in step 3 and it will
            appear here.
          </div>
        ) : (
          <ol className="ledger-list">
            {records.slice(0, 8).map((entry) => (
              <li key={`${entry.reviewItemId}-${entry.at}`} className={`ledger-entry is-${entry.action}`}>
                <div className="ledger-head">
                  <strong>{ACTION_LABEL[entry.action]}</strong>
                  <span>{entry.candidateTitle}</span>
                  <small>{formatRelative(entry.at)}</small>
                </div>
                <small className="ledger-actor">
                  by {entry.reviewer}
                  {!entry.hadAIBrief && " · decided without an AI brief"}
                </small>
                {entry.comment && <p className="ledger-comment">“{entry.comment}”</p>}
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}
