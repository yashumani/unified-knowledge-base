import { useState } from "react";
import { ConfirmAction } from "../common/ConfirmAction";
import { StatusPill } from "../common/StatusPill";
import { formatRelative } from "../../utils/format";
import type { KnowledgeObject, ReviewItem } from "../../types";

export function PublishStep({
  approvedItems = [],
  objects,
  onPublish = async () => undefined,
  demoMode = false
}: {
  approvedItems?: ReviewItem[];
  objects: KnowledgeObject[];
  onPublish?: (id: string, comment: string | null) => Promise<void>;
  demoMode?: boolean;
}) {
  const [comments, setComments] = useState<Record<string, string>>({});

  return (
    <div className="panel wide-panel publish-layout">
      <section className="publication-queue" aria-labelledby="publication-queue-title">
        <header>
          <div><span className="badge">Publication gate</span><h3 id="publication-queue-title">Approved, not yet retrievable</h3></div>
          <strong>{approvedItems.length}</strong>
        </header>
        {approvedItems.length === 0 && (
          <div className="empty-state">Human-approved candidates will wait here for an explicit publication decision.</div>
        )}
        <div className="publication-list">
          {approvedItems.map((item) => (
            <article key={item.id} className="publication-card">
              <div className="object-card-head"><span className="badge">{item.candidate_object.type}</span><StatusPill status={item.status} /></div>
              <h4>{item.candidate_object.title}</h4>
              <p>{item.candidate_object.summary}</p>
              <dl className="object-meta">
                <div><dt>Owner</dt><dd>{item.candidate_object.owner ?? "Not assigned"}</dd></div>
                <div><dt>Revision</dt><dd>{item.revision ?? 1}</dd></div>
                <div><dt>Evidence</dt><dd>{item.candidate_object.evidence_refs?.length ?? 0} links</dd></div>
                <div><dt>Approved by</dt><dd>{item.approved_by ?? item.reviewer ?? "Reviewer"}</dd></div>
              </dl>
              <label>
                Publication note
                <textarea
                  rows={2}
                  value={comments[item.id] ?? ""}
                  onChange={(event) => setComments((current) => ({ ...current, [item.id]: event.target.value }))}
                  placeholder="Why is this ready to become official memory?"
                />
              </label>
              <ConfirmAction
                label={demoMode ? "Simulate publication" : "Publish official memory"}
                confirmLabel="Confirm publication"
                disabled={!item.candidate_object.owner}
                disabledReason="A responsible owner is required before publication."
                onConfirm={() => onPublish(item.id, comments[item.id]?.trim() || null)}
              />
            </article>
          ))}
        </div>
      </section>

      <section aria-labelledby="published-memory-title">
        <header className="published-memory-heading">
          <div><span className="badge">Retrievable memory</span><h3 id="published-memory-title">Published knowledge objects</h3></div>
          <strong>{objects.length}</strong>
        </header>
        <div className="object-grid">
          {objects.length === 0 && (
            <div className="empty-state">Nothing is retrievable until an approved candidate is explicitly published.</div>
          )}
          {objects.map((object) => (
            <article className="object-card" key={object.id}>
              <div className="object-card-head"><span className="badge">{object.type}</span><StatusPill status={object.status} /></div>
              <h3>{object.title}</h3>
              <p>{object.summary}</p>
              <dl className="object-meta">
                <div><dt>Owner</dt><dd>{object.owner ?? "Not assigned"}</dd></div>
                <div><dt>Domain</dt><dd>{object.domain}</dd></div>
                <div><dt>Sensitivity</dt><dd>{object.sensitivity}</dd></div>
                <div><dt>Version</dt><dd>{object.version ?? 1}</dd></div>
                <div><dt>Authority</dt><dd>Tier {object.authority_tier ?? 3}</dd></div>
                <div><dt>Evidence</dt><dd>{object.evidence_refs?.length ?? 0} links</dd></div>
                <div><dt>Published by</dt><dd>{object.published_by ?? "Governance"}</dd></div>
                <div><dt>Updated</dt><dd>{formatRelative(object.updated_at)}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
