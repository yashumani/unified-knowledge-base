import { StatusPill } from "../common/StatusPill";
import { formatRelative } from "../../utils/format";
import type { KnowledgeObject } from "../../types";

export function PublishStep({ objects }: { objects: KnowledgeObject[] }) {
  return (
    <div className="panel wide-panel">
      <div className="object-grid">
        {objects.length === 0 && (
          <div className="empty-state">Approved knowledge will appear here after review.</div>
        )}
        {objects.map((object) => (
          <article className="object-card" key={object.id}>
            <div className="object-card-head">
              <span className="badge">{object.type}</span>
              <StatusPill status={object.status} />
            </div>
            <h3>{object.title}</h3>
            <p>{object.summary}</p>
            {/* Publication metadata the governance docs require and the card
                never showed: owner, sensitivity, and when it last changed. */}
            <dl className="object-meta">
              <div><dt>Owner</dt><dd>{object.owner ?? "Not assigned"}</dd></div>
              <div><dt>Domain</dt><dd>{object.domain}</dd></div>
              <div><dt>Sensitivity</dt><dd>{object.sensitivity}</dd></div>
              <div><dt>Updated</dt><dd>{formatRelative(object.updated_at)}</dd></div>
            </dl>
          </article>
        ))}
      </div>
    </div>
  );
}
