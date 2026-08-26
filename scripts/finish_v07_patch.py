from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str, *, required: bool = True) -> None:
    content = read(path)
    if old not in content:
        if required:
            raise RuntimeError(f"Expected text not found in {path}: {old[:100]!r}")
        return
    write(path, content.replace(old, new, 1))


def patch_pyproject() -> None:
    path = "pyproject.toml"
    content = read(path)
    content = content.replace('version = "0.6.0"', 'version = "0.7.0"')
    if '"redis>=5.0.0"' not in content:
        anchors = ['    "httpx>=0.27.0",\n', '    "SQLAlchemy>=2.0.36",\n']
        for anchor in anchors:
            if anchor in content:
                content = content.replace(anchor, anchor + '    "redis>=5.0.0",\n', 1)
                break
        else:
            raise RuntimeError("Could not locate the project dependency list in pyproject.toml")
    write(path, content)


def patch_package_version() -> None:
    path = "src/ukb/__init__.py"
    if not (ROOT / path).exists():
        return
    content = read(path)
    content = re.sub(r'__version__\s*=\s*"0\.6\.0"', '__version__ = "0.7.0"', content)
    write(path, content)


def patch_openwebui_shell() -> None:
    path = "apps/web/src/components/OpenWebUIBrainApp.tsx"
    content = read(path)
    import_line = 'import { IngestionStudio } from "./workspace/IngestionStudio";\n'
    guide_import = 'import { IngestionChannelGuide } from "./workspace/IngestionChannelGuide";\n'
    if guide_import not in content:
        if import_line not in content:
            raise RuntimeError("IngestionStudio import anchor missing from OpenWebUIBrainApp.tsx")
        content = content.replace(import_line, import_line + guide_import, 1)
    if "<IngestionChannelGuide />" not in content:
        marker = "<IngestionStudio"
        if marker not in content:
            raise RuntimeError("IngestionStudio render anchor missing from OpenWebUIBrainApp.tsx")
        content = content.replace(
            marker,
            '<IngestionChannelGuide />\n              <IngestionStudio',
            1,
        )
    write(path, content)


def patch_ingestion_studio() -> None:
    path = "apps/web/src/components/workspace/IngestionStudio.tsx"
    content = read(path)
    helper = '''\nconst SOURCE_MODE_IDS = new Set<IngestionSourceMode>([\n  "text", "files", "folder", "zip", "google_drive", "crawl4ai", "git", "object_store"\n]);\n\nfunction initialSourceMode(): IngestionSourceMode {\n  const requested = new URLSearchParams(window.location.search).get("source") as IngestionSourceMode | null;\n  return requested && SOURCE_MODE_IDS.has(requested) ? requested : "files";\n}\n'''
    anchor = 'type StudioStep = "source" | "governance" | "validate" | "create";\n'
    if "function initialSourceMode" not in content:
        if anchor not in content:
            raise RuntimeError("StudioStep anchor missing from IngestionStudio.tsx")
        content = content.replace(anchor, anchor + helper, 1)
    content = content.replace(
        'const [method, setMethod] = useState<IngestionSourceMode>("files");',
        'const [method, setMethod] = useState<IngestionSourceMode>(initialSourceMode);',
        1,
    )
    # Recommended path uses safe defaults and proceeds directly to validation.
    content = content.replace('setStudioStep("governance")', 'setStudioStep("validate")', 1)
    content = content.replace('Continue to governance →', 'Validate source →', 1)
    # Keep governance reachable through the explicit workflow step; describe it as optional advanced control.
    content = content.replace(
        '{ id: "governance", number: "02", label: "Governance", hint: "Set ownership and policy" }',
        '{ id: "governance", number: "Advanced", label: "Governance", hint: "Optional ownership and policy overrides" }',
        1,
    )
    if 'id="ingestion-studio"' not in content:
        content = re.sub(
            r'(return\s*\(\s*<(?:main|section|div))([^>]*className="[^"]*(?:ingestion|studio)[^"]*")',
            r'\1 id="ingestion-studio"\2',
            content,
            count=1,
        )
    write(path, content)


def patch_css() -> None:
    candidates = [
        "apps/web/src/styles.css",
        "apps/web/src/index.css",
        "apps/web/src/App.css",
    ]
    path = next((value for value in candidates if (ROOT / value).exists()), None)
    if path is None:
        raise RuntimeError("Could not locate the web stylesheet")
    content = read(path)
    if ".ingestion-channel-guide" in content:
        return
    content += '''\n\n/* Governed v0.7 multi-channel ingestion launchpad */\n.ingestion-channel-guide {\n  margin: 0 0 1rem;\n  padding: 1.1rem;\n  border: 1px solid var(--owui-border, rgba(127, 127, 127, 0.2));\n  border-radius: 1.25rem;\n  background: var(--owui-panel, rgba(255, 255, 255, 0.72));\n}\n\n.ingestion-channel-guide__header {\n  display: grid;\n  grid-template-columns: minmax(0, 1fr) minmax(17rem, 0.55fr);\n  gap: 1rem;\n  align-items: start;\n}\n\n.ingestion-channel-guide__header h2 {\n  margin: 0.25rem 0 0.4rem;\n  font-size: clamp(1.25rem, 2vw, 1.8rem);\n}\n\n.ingestion-channel-guide__header p {\n  margin: 0;\n  max-width: 60rem;\n  color: var(--owui-muted, #6b7280);\n}\n\n.ingestion-channel-guide__steps {\n  display: grid;\n  gap: 0.45rem;\n  margin: 0;\n  padding: 0;\n  list-style: none;\n}\n\n.ingestion-channel-guide__steps li {\n  display: grid;\n  grid-template-columns: 1.8rem 1fr;\n  align-items: center;\n  gap: 0.55rem;\n  font-size: 0.82rem;\n}\n\n.ingestion-channel-guide__steps strong {\n  display: grid;\n  place-items: center;\n  width: 1.75rem;\n  height: 1.75rem;\n  border-radius: 999px;\n  background: var(--owui-accent, #111827);\n  color: var(--owui-accent-contrast, #fff);\n}\n\n.ingestion-channel-guide__grid {\n  display: grid;\n  grid-template-columns: repeat(4, minmax(0, 1fr));\n  gap: 0.65rem;\n  margin-top: 1rem;\n}\n\n.ingestion-channel-card {\n  position: relative;\n  display: flex;\n  min-width: 0;\n  min-height: 9.5rem;\n  flex-direction: column;\n  gap: 0.45rem;\n  padding: 0.85rem;\n  border: 1px solid var(--owui-border, rgba(127, 127, 127, 0.2));\n  border-radius: 1rem;\n  color: inherit;\n  text-decoration: none;\n  background: var(--owui-surface, rgba(255, 255, 255, 0.56));\n  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;\n}\n\n.ingestion-channel-card:hover,\n.ingestion-channel-card:focus-visible {\n  transform: translateY(-2px);\n  border-color: var(--owui-accent, #111827);\n  outline: none;\n}\n\n.ingestion-channel-card > span:not(.ingestion-channel-card__badge) {\n  color: var(--owui-muted, #6b7280);\n  font-size: 0.82rem;\n  line-height: 1.45;\n}\n\n.ingestion-channel-card small {\n  margin-top: auto;\n  font-weight: 700;\n}\n\n.ingestion-channel-card__badge {\n  align-self: flex-start;\n  padding: 0.22rem 0.45rem;\n  border-radius: 999px;\n  background: var(--owui-chip, rgba(127, 127, 127, 0.12));\n  font-size: 0.7rem;\n  font-weight: 700;\n}\n\n.ingestion-channel-guide__boundary {\n  display: flex;\n  gap: 0.6rem;\n  margin-top: 0.8rem;\n  padding: 0.7rem 0.8rem;\n  border-radius: 0.85rem;\n  background: var(--owui-chip, rgba(127, 127, 127, 0.1));\n  font-size: 0.78rem;\n}\n\n@media (max-width: 1080px) {\n  .ingestion-channel-guide__grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }\n}\n\n@media (max-width: 720px) {\n  .ingestion-channel-guide { padding: 0.85rem; }\n  .ingestion-channel-guide__header { grid-template-columns: 1fr; }\n  .ingestion-channel-guide__grid { grid-template-columns: 1fr; }\n  .ingestion-channel-card { min-height: 7.8rem; }\n  .ingestion-channel-guide__boundary { flex-direction: column; }\n}\n'''
    write(path, content)


def patch_environment_examples() -> None:
    block = '''\n# Governed runtime, durable conversations, and disposable caches\nUKB_CONVERSATION_STORE_BACKEND=sqlalchemy\nUKB_CACHE_ENABLED=true\nUKB_CACHE_BACKEND=redis\nUKB_CACHE_FAIL_OPEN=true\nUKB_REDIS_URL=redis://redis:6379/0\nUKB_RESPONSE_CACHE_TTL_SECONDS=900\nUKB_TOOL_CACHE_TTL_SECONDS=600\nUKB_RETRIEVAL_CACHE_TTL_SECONDS=300\nUKB_RUNTIME_PROMPT_VERSION=governed-brain-prefix-v1\nUKB_TOOL_SCHEMA_VERSION=mcp-tools-v2\nUKB_RESPONSE_SCHEMA_VERSION=context-pack-v2\nUKB_ACCESS_POLICY_VERSION=access-policy-v1\n\n# Governed MCP service identity and transport\nUKB_MCP_TRANSPORT=stdio\nUKB_MCP_HOST=127.0.0.1\nUKB_MCP_PORT=8765\nUKB_MCP_SUBJECT=mcp-service\nUKB_MCP_TENANT_ID=default\nUKB_MCP_ROLES=consumer,submitter\nUKB_MCP_CLEARANCE=internal\nUKB_MCP_ALLOW_CACHE_INVALIDATION=false\nUKB_MCP_ALLOW_APPROVAL=false\nUKB_MCP_ALLOW_PUBLICATION=false\n'''
    for path in (".env.example", "deploy/staging.env.example"):
        target = ROOT / path
        if not target.exists():
            continue
        content = read(path)
        if "UKB_CONVERSATION_STORE_BACKEND" not in content:
            write(path, content.rstrip() + "\n" + block)


def patch_docs_index() -> None:
    path = "docs/README.md"
    target = ROOT / path
    if not target.exists():
        return
    content = read(path)
    entry = "- [Governed runtime, caching, and MCP v0.7](GOVERNED_RUNTIME_CACHE_AND_MCP_V07.md)\n"
    if entry not in content:
        write(path, content.rstrip() + "\n\n" + entry)


def main() -> None:
    patch_pyproject()
    patch_package_version()
    patch_openwebui_shell()
    patch_ingestion_studio()
    patch_css()
    patch_environment_examples()
    patch_docs_index()


if __name__ == "__main__":
    main()
