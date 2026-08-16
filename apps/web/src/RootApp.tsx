import { useEffect, useState } from "react";
import AdvancedApp from "./App";
import { GuidedDemo } from "./components/GuidedDemo";

type Experience = "guided" | "advanced";

function experienceFromLocation(): Experience {
  if (typeof window === "undefined") return "guided";
  return new URLSearchParams(window.location.search).get("view") === "advanced"
    ? "advanced"
    : "guided";
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
    if (next === "advanced") {
      url.searchParams.set("view", "advanced");
      url.hash = "";
    } else {
      url.searchParams.delete("view");
      url.hash = "";
    }
    window.history.pushState({}, "", url);
    setExperience(next);
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  if (experience === "advanced") {
    return (
      <div className="advanced-experience-shell">
        <AdvancedApp />
        <button
          type="button"
          className="experience-switcher"
          onClick={() => navigate("guided")}
        >
          ← Guided demo
        </button>
      </div>
    );
  }

  return <GuidedDemo onOpenAdvanced={() => navigate("advanced")} />;
}
