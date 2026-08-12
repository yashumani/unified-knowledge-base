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


def load_brain_project(path: str | Path) -> BrainProjectConfig:
    """Load a brain.config.yaml file from a project directory or exact path."""

    candidate = Path(path)
    config_path = candidate / "brain.config.yaml" if candidate.is_dir() else candidate
    if not config_path.exists():
        raise FileNotFoundError(f"Brain config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    brain = raw.get("brain", raw)
    runtime_raw = raw.get("runtime", {})

    return BrainProjectConfig(
        id=brain["id"],
        name=brain["name"],
        version=str(brain.get("version", "0.1.0")),
        description=brain.get("description"),
        domains=list(raw.get("domains", brain.get("domains", []))),
        runtime=BrainRuntimeConfig(
            mode=runtime_raw.get("mode", "offline_first"),
            require_human_review=raw.get("governance", {}).get("require_human_review", True),
            local_ai_enabled=runtime_raw.get("ai", {}).get("local", {}).get("enabled", False),
            hosted_ai_enabled=runtime_raw.get("ai", {}).get("hosted", {}).get("enabled", False),
        ),
        plugins=[BrainPluginConfig(**plugin) for plugin in raw.get("plugins", [])],
    )
