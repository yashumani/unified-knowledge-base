from pathlib import Path

from ukb.services.brain_project import load_brain_project


def test_load_brain_project_reads_runtime_and_plugins(tmp_path: Path):
    config = tmp_path / "brain.config.yaml"
    config.write_text(
        """
brain:
  id: test-brain
  name: Test Brain
  version: 0.1.0

domains:
  - finance

runtime:
  mode: offline_first
  ai:
    local:
      enabled: true
    hosted:
      enabled: false

governance:
  require_human_review: true

plugins:
  - name: local.context_source
    path: ./plugins/context_source.py
    enabled: true
""".strip(),
        encoding="utf-8",
    )

    brain = load_brain_project(tmp_path)

    assert brain.id == "test-brain"
    assert brain.name == "Test Brain"
    assert brain.domains == ["finance"]
    assert brain.runtime.mode == "offline_first"
    assert brain.runtime.local_ai_enabled is True
    assert brain.runtime.hosted_ai_enabled is False
    assert brain.runtime.require_human_review is True
    assert brain.plugins[0].name == "local.context_source"
