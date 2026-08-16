import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import RootApp from "./RootApp";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/pipeline.css";
import "./styles/graph.css";
import "./styles/ai-enrichment.css";
// Loaded last because it deliberately re-themes every existing console surface
// into the editorial one-page system without duplicating feature components.
import "./styles/editorial.css";
import "./styles/editorial-fixes.css";
// The guided layer is scoped and loaded after the advanced design so its
// three-step wrapper can coexist with the complete console.
import "./styles/guided-demo.css";
import "./styles/guided-polish.css";

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <RootApp />
  </StrictMode>
);
