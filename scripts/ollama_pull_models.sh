#!/usr/bin/env bash
set -euo pipefail

CHAT_MODEL="${UKB_AI_CHAT_MODEL:-llama3.1}"
EMBEDDING_MODEL="${UKB_AI_EMBEDDING_MODEL:-embeddinggemma}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "ollama CLI not found. Install Ollama first, or use Docker Compose and run:"
  echo "  docker exec unified-knowledge-base-ollama ollama pull ${CHAT_MODEL}"
  echo "  docker exec unified-knowledge-base-ollama ollama pull ${EMBEDDING_MODEL}"
  exit 1
fi

echo "Pulling UKB local chat model: ${CHAT_MODEL}"
ollama pull "${CHAT_MODEL}"

echo "Pulling UKB local embedding model: ${EMBEDDING_MODEL}"
ollama pull "${EMBEDDING_MODEL}"

echo "Ollama models ready for Unified Knowledge Base local enrichment."
