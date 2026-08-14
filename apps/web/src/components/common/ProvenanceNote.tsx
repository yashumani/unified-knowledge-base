import { PROVENANCE_NOTE } from "../../demo/config";

/**
 * Says where an artifact came from.
 *
 * Demo mode must never be mistaken for connected mode. Everything the offline
 * provider produces in the browser carries this, so a viewer is never left
 * guessing whether a brief came from a real model.
 */
export function ProvenanceNote({ visible = true }: { visible?: boolean }) {
  if (!visible) return null;
  return (
    <p className="provenance-note">
      <span className="provenance-dot" aria-hidden="true" />
      {PROVENANCE_NOTE}
    </p>
  );
}
