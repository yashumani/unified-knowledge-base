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


def _mapping(value: Any, *, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a mapping.")
    return {str(key): item for key, item in value.items()}


def _string_list(value: Any, *, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list.")
    return [str(item) for item in value]


def load_brain_project(path: str | Path) -> BrainProjectConfig:
    """Load and validate a brain.config.yaml file."""

    candidate = Path(path)
    config_path = candidate / "brain.config.yaml" if candidate.is_dir() else candidate
    if not config_path.exists():
        raise FileNotFoundError(f"Brain config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        raw = _mapping(yaml.safe_load(handle), field="brain.config.yaml")

    brain = _mapping(raw.get("brain", raw), field="brain")
    runtime_raw = _mapping(raw.get("runtime"), field="runtime")
    governance_raw = _mapping(raw.get("governance"), field="governance")
    ai_raw = _mapping(runtime_raw.get("ai"), field="runtime.ai")
    local_ai_raw = _mapping(ai_raw.get("local"), field="runtime.ai.local")
    hosted_ai_raw = _mapping(ai_raw.get("hosted"), field="runtime.ai.hosted")

    brain_id = brain.get("id")
    brain_name = brain.get("name")
    if not isinstance(brain_id, str) or not brain_id.strip():
        raise ValueError("brain.id is required and must be a non-empty string.")
    if not isinstance(brain_name, str) or not brain_name.strip():
        raise ValueError("brain.name is required and must be a non-empty string.")

    domains = _string_list(
        raw.get("domains", brain.get("domains", [])),
        field="domains",
    )
    plugins_value = raw.get("plugins", [])
    if not isinstance(plugins_value, list):
        raise ValueError("plugins must be a list.")
    plugins: list[BrainPluginConfig] = []
    for index, plugin_value in enumerate(plugins_value):
        plugins.append(
            BrainPluginConfig.model_validate(
                _mapping(plugin_value, field=f"plugins[{index}]")
            )
        )

    description = brain.get("description")
    if description is not None and not isinstance(description, str):
        description = str(description)

    return BrainProjectConfig(
        id=brain_id,
        name=brain_name,
        version=str(brain.get("version", "0.1.0")),
        description=description,
        domains=domains,
        runtime=BrainRuntimeConfig(
            mode=str(runtime_raw.get("mode", "offline_first")),
            require_human_review=bool(
                governance_raw.get("require_human_review", True)
            ),
            local_ai_enabled=bool(local_ai_raw.get("enabled", False)),
            hosted_ai_enabled=bool(hosted_ai_raw.get("enabled", False)),
        ),
        plugins=plugins,
    )
