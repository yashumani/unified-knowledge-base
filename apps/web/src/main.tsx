import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import RootApp from "./RootApp";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/pipeline.css";
import "./styles/graph.css";
import "./styles/ai-enrichment.css";
import "./styles/editorial.css";
import "./styles/editorial-fixes.css";
import "./styles/guided-demo.css";
import "./styles/workspace.css";
import "./styles/brand-reveal.css";
import "./styles/architecture-hardening.css";
import "./styles/knowledge-operations.css";

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode><RootApp /></StrictMode>
);
