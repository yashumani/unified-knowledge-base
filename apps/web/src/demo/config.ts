/**
 * Demo-mode constants.
 *
 * Nothing in src/demo may import from src/api. These modules are a browser
 * port of the backend's offline-safe provider, not a network client.
 */

/** Long enough to read as work happening, short enough not to bore. */
export const DEMO_ENRICHMENT_LATENCY_MS = 900;
export const DEMO_PACK_LATENCY_MS = 600;

export const DEMO_REVIEWER = "ui.reviewer";

export const PROVENANCE_NOTE =
  "Generated in your browser by the deterministic offline provider. No model, no network.";

export const newId = (prefix: string) =>
  `${prefix}_${Math.random().toString(16).slice(2, 10)}${Date.now().toString(16).slice(-4)}`;

export const collapseWhitespace = (value: string) => value.split(/\s+/).filter(Boolean).join(" ");

/** Mirrors NoopProvider._sentence_with: first sentence containing the needle. */
export function sentenceWith(text: string, needle: string): string | null {
  const sentences = text.split(/(?<=[.!?])\s+/);
  const found = sentences.find((sentence) =>
    sentence.toLowerCase().includes(needle.toLowerCase())
  );
  return found ? found.trim() : null;
}
