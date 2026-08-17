import { formatRelative } from "../utils/format";
import type { ReviewDecisionRecord } from "../pipeline/types";

const ACTION_LABEL: Record<ReviewDecisionRecord["action"], string> = {
  approved: "Approved for publication",
  published: "Published",
  rejected: "Rejected",
  changes_requested: "Changes requested"
};

export function ActivityLedger({ records }: { records: ReviewDecisionRecord[] }) {
  return (
    <section id="activity" className="section-shell" aria-labelledby="activity-heading">
      <div className="section-heading">
        <h2 id="activity-heading"><span className="step-kicker">Governance trail</span>Every decision, attributable</h2>
        <p>Approval and publication are separate records. Each entry shows who acted, when, and why.</p>
      </div>
      <div className="panel wide-panel">
        {records.length === 0 ? (
          <div className="empty-state">No decisions yet. Review and publish actions will appear here.</div>
        ) : (
          <ol className="ledger-list">
            {records.slice(0, 12).map((entry) => (
              <li key={`${entry.reviewItemId}-${entry.action}-${entry.at}`} className={`ledger-entry is-${entry.action}`}>
                <div className="ledger-head">
                  <strong>{ACTION_LABEL[entry.action]}</strong><span>{entry.candidateTitle}</span><small>{formatRelative(entry.at)}</small>
                </div>
                <small className="ledger-actor">by {entry.reviewer}{!entry.hadAIBrief && " · decided without an AI brief"}</small>
                {entry.comment && <p className="ledger-comment">“{entry.comment}”</p>}
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}
