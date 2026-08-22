import { useEffect, useState } from "react";
import AdvancedApp from "./AdvancedApp";
import { GuidedDemoV2 } from "./components/GuidedDemoV2";
import { WorkspaceApp } from "./components/workspace/WorkspaceApp";

export type Experience = "workspace" | "guided" | "advanced";

function experienceFromLocation(): Experience {
  if (typeof window === "undefined") return "workspace";
  const view = new URLSearchParams(window.location.search).get("view");
  if (view === "advanced") return "advanced";
  if (view === "guided") return "guided";
  return "workspace";
}

export default function RootApp() {
  const [experience, setExperience] = useState<Experience>(experienceFromLocation);

  useEffect(() => {
    const update = () => setExperience(experienceFromLocation());
    window.addEventListener("popstate", update);
    return () => window.removeEventListener("popstate", update);
  }, []);

  function navigate(next: Experience) {
    const url = new URL(window.location.href);
    url.searchParams.delete("page");
    if (next === "advanced" || next === "guided") url.searchParams.set("view", next);
    else url.searchParams.delete("view");
    url.hash = "";
    window.history.pushState({}, "", url);
    setExperience(next);
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  if (experience === "advanced") {
    return (
      <div className="advanced-experience-shell">
        <AdvancedApp />
        <button type="button" className="experience-switcher" onClick={() => navigate("workspace")}>← Dashboard</button>
      </div>
    );
  }

  if (experience === "guided") {
    return (
      <div className="guided-experience-shell">
        <GuidedDemoV2 onOpenAdvanced={() => navigate("advanced")} />
        <button type="button" className="experience-switcher" onClick={() => navigate("workspace")}>← Dashboard</button>
      </div>
    );
  }

  return <WorkspaceApp onOpenAdvanced={() => navigate("advanced")} onOpenGuided={() => navigate("guided")} />;
}
