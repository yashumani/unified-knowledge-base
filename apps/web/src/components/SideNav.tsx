import type { AIProviderStatus } from "../types";

const navItems = [
  { label: "Map", href: "#brain-map" },
  { label: "Submit", href: "#context-ingestion" },
  { label: "Review", href: "#review-queue" },
  { label: "Context Pack", href: "#context-pack" },
  { label: "Published", href: "#published-objects" }
];

export function SideNav({ aiStatus }: { aiStatus: AIProviderStatus }) {
  return (
    <aside className="side-nav" aria-label="Console navigation">
      <div className="brand-lockup">
        <span className="brand-mark">UKB</span>
        <div>
          <strong>AI Brain</strong>
          <span>Governed context OS</span>
        </div>
      </div>
      <nav>
        {navItems.map((item) => (
          <a href={item.href} key={item.href}>{item.label}</a>
        ))}
      </nav>
      <div className="nav-callout">
        <span>AI enrichment</span>
        <strong>{aiStatus.provider} · {aiStatus.mode}</strong>
        <p>{aiStatus.enabled ? `Model: ${aiStatus.model}` : "Disabled by server config"}</p>
      </div>
      <div className="nav-callout">
        <span>Demo domain</span>
        <strong>Support Ops</strong>
        <p>Uses only synthetic, workplace-safe examples.</p>
      </div>
    </aside>
  );
}
