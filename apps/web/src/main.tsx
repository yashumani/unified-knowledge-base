import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
// Cascade order matters: tokens define the custom properties every later sheet
// reads, and graph.css relies on coming after base.css for the shared card rule.
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/pipeline.css";
import "./styles/graph.css";
import "./styles/ai-enrichment.css";

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <App />
  </StrictMode>
);
