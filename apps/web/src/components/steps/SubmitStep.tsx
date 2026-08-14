import { useState, type FormEvent } from "react";
import type { IngestionPayload, SourceType } from "../../types";

export function SubmitStep({
  onSubmit,
  demoMode
}: {
  onSubmit: (payload: IngestionPayload) => Promise<void>;
  demoMode: boolean;
}) {
  const [title, setTitle] = useState("Incident Resolution Time Definition");
  const [domain, setDomain] = useState("support");
  const [sourceType, setSourceType] = useState<SourceType>("document");
  const [content, setContent] = useState(
    "Incident Resolution Time is the average elapsed time from incident creation to resolved status for product support cases, excluding duplicate incidents and customer-wait periods. It appears in the SLA Review Dashboard and is owned by Support Operations. Recently resolved incidents may need 24 hours for quality review tags to settle."
  );
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit({
        title,
        domain,
        source_type: sourceType,
        submitted_by: "ui.submitter",
        content,
        sensitivity: "internal",
        tags: ["ui", domain]
      });
      setTitle("");
      setContent("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="panel panel-accent">
      <form onSubmit={submit} className="stack">
        <label>Title<input value={title} onChange={(event) => setTitle(event.target.value)} required /></label>
        <div className="form-row">
          <label>Domain<input value={domain} onChange={(event) => setDomain(event.target.value)} required /></label>
          <label>Source type
            <select value={sourceType} onChange={(event) => setSourceType(event.target.value as SourceType)}>
              <option value="document">Document</option>
              <option value="markdown">Markdown</option>
              <option value="sql">SQL</option>
              <option value="dashboard">Dashboard</option>
              <option value="manual">Manual</option>
            </select>
          </label>
        </div>
        <label>Context<textarea value={content} onChange={(event) => setContent(event.target.value)} rows={8} required /></label>
        <button type="submit" disabled={submitting || !title || !content}>
          {submitting ? "Submitting..." : demoMode ? "Simulate submission" : "Submit for review"}
        </button>
      </form>
    </div>
  );
}
