import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { FileUploadCard } from "./components/FileUploadCard";
import "./styles.css";
import "./ai-enrichment.css";

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <App />
    <div style={{ width: "min(1180px, calc(100% - 36px))", margin: "0 auto 56px" }}>
      <FileUploadCard demoMode={false} onUploaded={async () => undefined} />
    </div>
  </StrictMode>
);
