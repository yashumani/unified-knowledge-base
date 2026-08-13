from __future__ import annotations

from ukb.ai.providers.base import AIProvider, AIProviderError
from ukb.ai.providers.noop import NoopProvider
from ukb.ai.providers.ollama import OllamaProvider
from ukb.ai.providers.openai_provider import OpenAIProvider
from ukb.config import Settings, get_settings
from ukb.models import (
    AIEnrichmentMode,
    AIEnrichmentResult,
    AIProviderHealth,
    AIProviderName,
    AIProviderStatus,
    AIReviewBrief,
    AITaskStatus,
    ContextPack,
    EmbeddingResponse,
    KnowledgeObject,
    SourceClassification,
    SourceEvidence,
)


class AIEnrichmentService:
    """Governed AI enrichment facade.

    The service owns provider routing and safe fallback behavior. Providers may
    enrich source context and context packs, but they never approve or publish
    knowledge. This use case is optimized for local Ollama first.
    """

    def __init__(self, *, settings: Settings | None = None, provider: AIProvider | None = None):
        self.settings = settings or get_settings()
        self.provider = provider or self._build_provider(self.settings)
        self.fallback = NoopProvider()

    def status(self) -> AIProviderStatus:
        return AIProviderStatus(
            provider=AIProviderName(self.provider.name),
            mode=self._mode(),
            enabled=self.settings.ai_enrichment_enabled,
            model=getattr(self.provider, "model", "deterministic"),
            embedding_model=self.settings.ai_embedding_model,
            base_url=self._safe_base_url(),
            hosted_allowed_for_restricted=self.settings.allow_hosted_ai_for_restricted,
            local_only=self.provider.name != AIProviderName.openai.value,
            capabilities=self._capabilities(),
        )

    def health(self) -> AIProviderHealth:
        try:
            return self.provider.health_check()
        except (AIProviderError, AttributeError) as exc:
            return AIProviderHealth(
                provider=AIProviderName(self.provider.name),
                reachable=False,
                message=f"AI provider health check failed: {exc}",
                base_url=self._safe_base_url(),
                model=getattr(self.provider, "model", "unknown"),
                embedding_model=self.settings.ai_embedding_model,
            )

    def enrich_source(
        self,
        *,
        source: SourceEvidence,
        content: str,
        baseline_candidate: KnowledgeObject,
    ) -> AIEnrichmentResult:
        truncated = content[: self.settings.ai_max_input_chars]
        if not self.settings.ai_enrichment_enabled:
            return self._skipped_result(source=source, baseline_candidate=baseline_candidate)

        if self._must_block_hosted_for_sensitivity(source):
            return self.fallback.enrich_source(
                source=source,
                content=truncated,
                baseline_candidate=baseline_candidate,
            )

        try:
            return self.provider.enrich_source(
                source=source,
                content=truncated,
                baseline_candidate=baseline_candidate,
            )
        except AIProviderError as exc:
            result = self.fallback.enrich_source(
                source=source,
                content=truncated,
                baseline_candidate=baseline_candidate,
            )
            return result.model_copy(
                update={
                    "status": AITaskStatus.failed,
                    "error_message": str(exc),
                    "review_brief": result.review_brief.model_copy(
                        update={
                            "risk_flags": [*result.review_brief.risk_flags, "provider_fallback"],
                        }
                    ),
                }
            )

    def enrich_context_pack(self, *, context_pack: ContextPack) -> ContextPack:
        if not self.settings.ai_enrichment_enabled:
            return context_pack
        try:
            return self.provider.enrich_context_pack(context_pack=context_pack)
        except AIProviderError:
            return self.fallback.enrich_context_pack(context_pack=context_pack)

    def embed_texts(self, *, texts: list[str], model: str | None = None) -> EmbeddingResponse:
        if not self.settings.ai_enrichment_enabled:
            return self.fallback.embed_texts(texts=texts, model=model)
        try:
            return self.provider.embed_texts(texts=texts, model=model)
        except (AIProviderError, AttributeError):
            return self.fallback.embed_texts(texts=texts, model=model)

    def _build_provider(self, settings: Settings) -> AIProvider:
        provider = settings.ai_provider.lower().strip()
        if provider == AIProviderName.ollama.value:
            return OllamaProvider(
                base_url=settings.ai_base_url,
                model=settings.ai_chat_model,
                embedding_model=settings.ai_embedding_model,
                timeout_seconds=settings.ai_timeout_seconds,
            )
        if provider == AIProviderName.openai.value:
            return OpenAIProvider(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=settings.openai_model,
                timeout_seconds=settings.ai_timeout_seconds,
            )
        return NoopProvider()

    def _mode(self) -> AIEnrichmentMode:
        try:
            return AIEnrichmentMode(self.settings.ai_mode)
        except ValueError:
            return AIEnrichmentMode.local_ai

    def _safe_base_url(self) -> str | None:
        if self.provider.name == AIProviderName.noop.value:
            return None
        if self.provider.name == AIProviderName.openai.value:
            return self.settings.openai_base_url
        return self.settings.ai_base_url

    def _must_block_hosted_for_sensitivity(self, source: SourceEvidence) -> bool:
        if self.provider.name != AIProviderName.openai.value:
            return False
        if self.settings.allow_hosted_ai_for_restricted:
            return False
        return source.sensitivity.value in {"confidential", "restricted"}

    def _capabilities(self) -> list[str]:
        if self.provider.name == AIProviderName.noop.value:
            return ["deterministic_classification", "deterministic_review_brief", "hash_embedding_fallback"]
        if self.provider.name == AIProviderName.ollama.value:
            return [
                "local_source_classification",
                "local_review_brief",
                "local_context_pack_guidance",
                "local_embeddings",
                "deterministic_fallback",
            ]
        return ["source_classification", "review_brief", "context_pack_guidance", "deterministic_fallback"]

    def _skipped_result(
        self,
        *,
        source: SourceEvidence,
        baseline_candidate: KnowledgeObject,
    ) -> AIEnrichmentResult:
        return AIEnrichmentResult(
            provider=AIProviderName.noop,
            model="disabled",
            status=AITaskStatus.skipped,
            source_classification=SourceClassification(
                source_kind="not_enriched",
                domain=source.domain,
                summary="AI enrichment is disabled by server configuration.",
                confidence=0.0,
            ),
            extracted_objects=[baseline_candidate],
            review_brief=AIReviewBrief(
                summary="AI enrichment is disabled. Review the deterministic candidate manually.",
                recommended_action="needs_review",
                reviewer_questions=["Is this candidate correct and sufficiently evidenced?"],
                risk_flags=["ai_enrichment_disabled"],
            ),
            confidence=0.0,
        )
