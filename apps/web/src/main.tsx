import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/pipeline.css";
import "./styles/graph.css";
import "./styles/ai-enrichment.css";
// Loaded last because it deliberately re-themes every existing console surface
// into the editorial one-page system without duplicating feature components.
import "./styles/editorial.css";

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <App />
  </StrictMode>
);
