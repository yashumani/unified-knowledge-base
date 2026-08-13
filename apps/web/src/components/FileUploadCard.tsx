import { useState, type FormEvent } from "react";

import { API_BASE } from "../api/brainClient";
import type { Sensitivity } from "../types";

interface FileUploadCardProps {
  demoMode: boolean;
  onUploaded: () => Promise<void>;
}

export function FileUploadCard({ demoMode, onUploaded }: FileUploadCardProps) {
  const [message, setMessage] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(demoMode ? "Connect the backend to upload source files." : API_BASE);
    if (!demoMode) await onUploaded();
  }

  return (
    <section className="panel" id="file-ingestion">
      <div className="panel-header">
        <div><p className="eyebrow">Source preservation</p><h2>Upload a source file</h2></div>
        <span className="chip">File → Evidence → Review</span>
      </div>
      <form className="stack" onSubmit={submit}>
        <input name="file" type="file" disabled={demoMode} required />
        <button type="submit" disabled={demoMode}>Upload and enrich</button>
      </form>
      {message && <div className="notice">{message}</div>}
    </section>
  );
}
