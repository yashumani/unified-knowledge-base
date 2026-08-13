from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from ukb.ai.providers.base import AIProviderError
from ukb.ai.providers.noop import NoopProvider
from ukb.models import (
    AIEnrichmentResult,
    AIProviderHealth,
    AIProviderName,
    ContextPack,
    EmbeddingResponse,
    KnowledgeObject,
    SourceEvidence,
)


class OpenAIProvider:
    """Hosted OpenAI adapter using server-side environment configuration.

    This adapter remains an extension point. The Unified Knowledge Base local
    use case should prefer Ollama. API keys must stay on the backend and must
    never be exposed to the React app.
    """

    name = AIProviderName.openai.value

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        model: str,
        timeout_seconds: int = 45,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._fallback = NoopProvider()

    def health_check(self) -> AIProviderHealth:
        if not self.api_key:
            return AIProviderHealth(
                provider=AIProviderName.openai,
                reachable=False,
                message="Hosted provider is not configured with a backend API key.",
                base_url=self.base_url,
                model=self.model,
                embedding_model=None,
            )
        return AIProviderHealth(
            provider=AIProviderName.openai,
            reachable=True,
            message="Hosted provider is configured. Prefer local Ollama for this UKB use case.",
            base_url=self.base_url,
            model=self.model,
            embedding_model=None,
        )

    def enrich_source(
        self,
        *,
        source: SourceEvidence,
        content: str,
        baseline_candidate: KnowledgeObject,
    ) -> AIEnrichmentResult:
        if not self.api_key:
            raise AIProviderError("OpenAI provider is configured without an API key")
        payload = self._chat_json(self._source_prompt(source, content, baseline_candidate))
        fallback = self._fallback.enrich_source(
            source=source,
            content=content,
            baseline_candidate=baseline_candidate,
        )
        return fallback.model_copy(
            update={
                "provider": AIProviderName.openai,
                "model": self.model,
                "source_classification": fallback.source_classification.model_copy(
                    update={
                        "summary": payload.get("summary") or fallback.source_classification.summary,
                        "topics": payload.get("topics") or fallback.source_classification.topics,
                    }
                ),
                "review_brief": fallback.review_brief.model_copy(
                    update={
                        "summary": payload.get("review_brief") or fallback.review_brief.summary,
                        "reviewer_questions": payload.get("reviewer_questions") or fallback.review_brief.reviewer_questions,
                    }
                ),
            }
        )

    def enrich_context_pack(self, *, context_pack: ContextPack) -> ContextPack:
        if not self.api_key or not context_pack.knowledge_objects:
            return self._fallback.enrich_context_pack(context_pack=context_pack)
        try:
            payload = self._chat_json(self._context_pack_prompt(context_pack))
        except AIProviderError:
            return self._fallback.enrich_context_pack(context_pack=context_pack)
        context_pack.ai_guidance = payload.get("ai_guidance") or context_pack.ai_guidance
        for warning in payload.get("missing_context", [])[:5]:
            if warning not in context_pack.missing_context:
                context_pack.missing_context.append(warning)
        for followup in payload.get("recommended_followups", [])[:5]:
            if followup not in context_pack.recommended_followups:
                context_pack.recommended_followups.append(followup)
        return context_pack

    def embed_texts(self, *, texts: list[str], model: str | None = None) -> EmbeddingResponse:
        # Hosted embeddings are intentionally not implemented for the local UKB use case.
        return self._fallback.embed_texts(texts=texts, model=model)

    def _chat_json(self, prompt: str) -> dict[str, Any]:
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Return valid JSON only. You enrich governed knowledge candidates; you never approve or publish knowledge.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AIProviderError(f"OpenAI request failed: {exc}") from exc

        try:
            content = raw["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AIProviderError(f"OpenAI returned invalid JSON content: {exc}") from exc
        if not isinstance(parsed, dict):
            raise AIProviderError("OpenAI JSON response must be an object")
        return parsed

    def _source_prompt(
        self,
        source: SourceEvidence,
        content: str,
        baseline_candidate: KnowledgeObject,
    ) -> str:
        return f"""
Return JSON with this shape:
{{
  "summary": "short source summary",
  "topics": ["topic"],
  "review_brief": "reviewer-facing notes",
  "reviewer_questions": ["question"]
}}

Rules:
- Use only source content below.
- Do not approve, publish, or invent source evidence.
- Flag uncertainty for human review.

Source title: {source.title}
Domain: {source.domain}
Baseline candidate type: {baseline_candidate.type.value}
Baseline candidate title: {baseline_candidate.title}
Source content:
{content}
""".strip()

    def _context_pack_prompt(self, context_pack: ContextPack) -> str:
        objects = ", ".join(obj.title for obj in context_pack.knowledge_objects[:6])
        evidence = ", ".join(source.title for source in context_pack.evidence[:6])
        return f"""
Return JSON with this shape:
{{
  "ai_guidance": "guidance for an AI app using this governed context pack",
  "missing_context": ["missing context warning"],
  "recommended_followups": ["follow-up question"]
}}

Rules:
- Use only approved knowledge objects and source evidence listed below.
- Do not invent facts.
- Mention missing context instead of filling gaps.

Question: {context_pack.question}
Mode: {context_pack.mode}
Approved objects: {objects}
Evidence: {evidence}
Existing guidance: {context_pack.answer_guidance}
""".strip()
