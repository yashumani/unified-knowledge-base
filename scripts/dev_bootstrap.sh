#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,mcp]"
cp -n .env.example .env || true

echo "Development environment ready."
echo "Run: source .venv/bin/activate && make run"
