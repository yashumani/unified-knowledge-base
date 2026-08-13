import { useState, type FormEvent } from "react";

import { API_BASE } from "../api/brainClient";

interface FileUploadCardProps {
  demoMode: boolean;
  onUploaded: () => Promise<void>;
}

export function FileUploadCard({ demoMode, onUploaded }: FileUploadCardProps) {
  const [message, setMessage] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const fileInput = form.elements.namedItem("file") as HTMLInputElement;
    const file = fileInput.files?.[0];
    if (!file) return;
    if (demoMode) {
      setMessage("Connect the backend to preserve source files.");
      return;
    }

    const payload = new FormData();
    payload.append("file", file);
    payload.append("submitted_by", "ui.submitter");
    payload.append("domain", "support");
    payload.append("sensitivity", "internal");

    setUploading(true);
    setMessage(null);
    try {
      const response = await fetch(`${API_BASE}/ingestion/files`, { method: "POST", body: payload });
      if (!response.ok) throw new Error(await response.text());
      const result = (await response.json()) as { review_item: { id: string } };
      setMessage(`Source preserved. Review ID: ${result.review_item.id}`);
      form.reset();
      await onUploaded();
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="panel" id="file-ingestion">
      <div className="panel-header">
        <div><p className="eyebrow">Source preservation</p><h2>Upload a source file</h2></div>
        <span className="chip">File → Evidence → Review</span>
      </div>
      <p className="panel-copy">Preserve a text-oriented source before local AI enrichment and human review.</p>
      <form className="stack" onSubmit={submit}>
        <input name="file" type="file" accept=".txt,.md,.markdown,.sql,.csv,.json,.yaml,.yml" disabled={uploading} required />
        <button type="submit" disabled={uploading || demoMode}>{uploading ? "Uploading..." : "Upload and enrich"}</button>
      </form>
      {message && <div className="notice">{message}</div>}
    </section>
  );
}
