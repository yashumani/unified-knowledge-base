from __future__ import annotations

from typing import Protocol, runtime_checkable

from ukb.models import (
    AIEnrichmentResult,
    AIProviderHealth,
    ContextPack,
    EmbeddingResponse,
    KnowledgeObject,
    SourceEvidence,
)


class AIProviderError(RuntimeError):
    """Raised when an AI provider cannot complete an enrichment task."""


@runtime_checkable
class AIProvider(Protocol):
    """Minimal contract for AI enrichment providers.

    Providers may call a local model, a hosted model, or no model at all. They
    must return structured, reviewable data. They must not publish knowledge.
    """

    name: str
    model: str

    def health_check(self) -> AIProviderHealth:
        """Return local provider readiness without exposing secrets."""

    def enrich_source(
        self,
        *,
        source: SourceEvidence,
        content: str,
        baseline_candidate: KnowledgeObject,
    ) -> AIEnrichmentResult:
        """Extract candidate knowledge, relationships, findings, and a review brief."""

    def enrich_context_pack(self, *, context_pack: ContextPack) -> ContextPack:
        """Improve context-pack guidance without adding unapproved facts."""

    def embed_texts(self, *, texts: list[str], model: str | None = None) -> EmbeddingResponse:
        """Generate local embeddings for future semantic retrieval and duplicate checks."""
