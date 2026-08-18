from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class BrainRuntimeConfig(BaseModel):
    mode: str = "offline_first"
    require_human_review: bool = True
    local_ai_enabled: bool = False
    hosted_ai_enabled: bool = False


class BrainPluginConfig(BaseModel):
    name: str
    path: str | None = None
    package: str | None = None
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class BrainProjectConfig(BaseModel):
    id: str
    name: str
    version: str = "0.1.0"
    description: str | None = None
    domains: list[str] = Field(default_factory=list)
    runtime: BrainRuntimeConfig = Field(default_factory=BrainRuntimeConfig)
    plugins: list[BrainPluginConfig] = Field(default_factory=list)


def _mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def load_brain_project(path: str | Path) -> BrainProjectConfig:
    """Load a brain.config.yaml file from a project directory or exact path."""

    candidate = Path(path)
    config_path = candidate / "brain.config.yaml" if candidate.is_dir() else candidate
    if not config_path.exists():
        raise FileNotFoundError(f"Brain config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    raw = _mapping(loaded)
    brain = _mapping(raw.get("brain") or raw)
    runtime_raw = _mapping(raw.get("runtime"))
    ai_raw = _mapping(runtime_raw.get("ai"))
    local_ai = _mapping(ai_raw.get("local"))
    hosted_ai = _mapping(ai_raw.get("hosted"))
    governance = _mapping(raw.get("governance"))
    raw_plugins = raw.get("plugins")
    plugins = raw_plugins if isinstance(raw_plugins, list) else []

    project_id = str(brain.get("id") or "").strip()
    project_name = str(brain.get("name") or "").strip()
    if not project_id or not project_name:
        raise ValueError("brain.config.yaml requires brain.id and brain.name.")

    return BrainProjectConfig(
        id=project_id,
        name=project_name,
        version=str(brain.get("version") or "0.1.0"),
        description=str(brain["description"]) if brain.get("description") is not None else None,
        domains=_string_list(raw.get("domains") or brain.get("domains")),
        runtime=BrainRuntimeConfig(
            mode=str(runtime_raw.get("mode") or "offline_first"),
            require_human_review=bool(governance.get("require_human_review", True)),
            local_ai_enabled=bool(local_ai.get("enabled", False)),
            hosted_ai_enabled=bool(hosted_ai.get("enabled", False)),
        ),
        plugins=[BrainPluginConfig.model_validate(plugin) for plugin in plugins if isinstance(plugin, dict)],
    )
