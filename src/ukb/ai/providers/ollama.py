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


class OllamaProvider:
    """Local Ollama adapter for UKB enrichment.

    The provider asks a local model to produce JSON. If the model is unavailable
    or returns invalid data, AIEnrichmentService falls back to NoopProvider so
    the governance workflow keeps running.
    """

    name = AIProviderName.ollama.value

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        embedding_model: str,
        timeout_seconds: int = 45,
    ):
        self.base_url = base_url.rstrip("/")
        if self.base_url.endswith("/api"):
            self.api_base = self.base_url
        else:
            self.api_base = f"{self.base_url}/api"
        self.model = model
        self.embedding_model = embedding_model
        self.timeout_seconds = timeout_seconds
        self._fallback = NoopProvider()

    def health_check(self) -> AIProviderHealth:
        try:
            payload = self._get_json("/tags")
        except AIProviderError as exc:
            return AIProviderHealth(
                provider=AIProviderName.ollama,
                reachable=False,
                message=f"Ollama is not reachable: {exc}",
                base_url=self.base_url,
                model=self.model,
                embedding_model=self.embedding_model,
            )

        model_names = sorted(
            str(model.get("name", "")) for model in payload.get("models", []) if isinstance(model, dict)
        )
        chat_model_found = self._model_available(model_names, self.model)
        embedding_model_found = self._model_available(model_names, self.embedding_model)
        missing = []
        if not chat_model_found:
            missing.append(self.model)
        if self.embedding_model and not embedding_model_found:
            missing.append(self.embedding_model)

        if missing:
            message = "Ollama is reachable, but model(s) need to be pulled: " + ", ".join(missing)
        else:
            message = "Ollama is reachable and configured models are available."

        return AIProviderHealth(
            provider=AIProviderName.ollama,
            reachable=not missing,
            message=message,
            base_url=self.base_url,
            model=self.model,
            embedding_model=self.embedding_model,
            details={"available_models": model_names, "missing_models": missing},
        )

    def enrich_source(
        self,
        *,
        source: SourceEvidence,
        content: str,
        baseline_candidate: KnowledgeObject,
    ) -> AIEnrichmentResult:
        prompt = self._source_prompt(source=source, content=content, baseline_candidate=baseline_candidate)
        payload = self._generate_json(prompt)
        fallback = self._fallback.enrich_source(
            source=source,
            content=content,
            baseline_candidate=baseline_candidate,
        )
        topics = self._list_payload(payload, "topics") or fallback.source_classification.topics
        reviewer_questions = (
            self._list_payload(payload, "reviewer_questions") or fallback.review_brief.reviewer_questions
        )
        risk_flags = sorted(set([*fallback.review_brief.risk_flags, *self._list_payload(payload, "risk_flags")]))

        return fallback.model_copy(
            update={
                "provider": AIProviderName.ollama,
                "model": self.model,
                "source_classification": fallback.source_classification.model_copy(
                    update={
                        "summary": self._string_payload(payload, "summary") or fallback.source_classification.summary,
                        "topics": topics,
                    }
                ),
                "review_brief": fallback.review_brief.model_copy(
                    update={
                        "summary": self._string_payload(payload, "review_brief") or fallback.review_brief.summary,
                        "reviewer_questions": reviewer_questions,
                        "risk_flags": risk_flags,
                    }
                ),
            }
        )

    def enrich_context_pack(self, *, context_pack: ContextPack) -> ContextPack:
        if not context_pack.knowledge_objects:
            return self._fallback.enrich_context_pack(context_pack=context_pack)
        prompt = self._context_pack_prompt(context_pack)
        try:
            payload = self._generate_json(prompt)
        except AIProviderError:
            return self._fallback.enrich_context_pack(context_pack=context_pack)
        context_pack.ai_guidance = self._string_payload(payload, "ai_guidance") or context_pack.ai_guidance
        for warning in self._list_payload(payload, "missing_context")[:5]:
            if warning not in context_pack.missing_context:
                context_pack.missing_context.append(warning)
        for followup in self._list_payload(payload, "recommended_followups")[:5]:
            if followup not in context_pack.recommended_followups:
                context_pack.recommended_followups.append(followup)
        return context_pack

    def embed_texts(self, *, texts: list[str], model: str | None = None) -> EmbeddingResponse:
        embedding_model = model or self.embedding_model
        body = json.dumps({"model": embedding_model, "input": texts}).encode()
        payload = self._post_json("/embed", body)
        raw_embeddings = payload.get("embeddings")
        if not isinstance(raw_embeddings, list):
            raise AIProviderError("Ollama embed response did not include embeddings")

        embeddings: list[list[float]] = []
        for item in raw_embeddings:
            if not isinstance(item, list):
                raise AIProviderError("Ollama embedding item was not a vector")
            embeddings.append([float(value) for value in item])

        return EmbeddingResponse(
            provider=AIProviderName.ollama,
            model=embedding_model,
            dimensions=len(embeddings[0]) if embeddings else 0,
            embeddings=embeddings,
            fallback_used=False,
        )

    def _generate_json(self, prompt: str) -> dict[str, Any]:
        body = json.dumps({"model": self.model, "prompt": prompt, "stream": False, "format": "json"}).encode()
        raw = self._post_json("/generate", body)
        response_text = raw.get("response")
        if not isinstance(response_text, str):
            raise AIProviderError("Ollama response did not include a text response")
        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise AIProviderError(f"Ollama returned invalid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise AIProviderError("Ollama JSON response must be an object")
        return parsed

    def _get_json(self, path: str) -> dict[str, Any]:
        request = urllib.request.Request(f"{self.api_base}{path}", method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AIProviderError(str(exc)) from exc
        if not isinstance(payload, dict):
            raise AIProviderError("Ollama returned a non-object response")
        return payload

    def _post_json(self, path: str, body: bytes) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.api_base}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AIProviderError(f"Ollama request failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise AIProviderError("Ollama returned a non-object response")
        return payload

    def _source_prompt(self, *, source: SourceEvidence, content: str, baseline_candidate: KnowledgeObject) -> str:
        return f"""
You are an AI curator for Unified Knowledge Base, a governed knowledge-base platform. Return JSON only.
Do not approve or publish knowledge. Produce reviewer-facing enrichment grounded only in the source text.

Return shape:
{{
  "summary": "short source summary",
  "topics": ["topic"],
  "review_brief": "what should the reviewer know",
  "reviewer_questions": ["question"],
  "risk_flags": ["short_risk_flag"]
}}

Source title: {source.title}
Domain: {source.domain}
Sensitivity: {source.sensitivity.value}
Baseline candidate type: {baseline_candidate.type.value}
Baseline candidate title: {baseline_candidate.title}
Source content:
{content}
""".strip()

    def _context_pack_prompt(self, context_pack: ContextPack) -> str:
        objects = ", ".join(obj.title for obj in context_pack.knowledge_objects[:6])
        evidence = ", ".join(source.title for source in context_pack.evidence[:6])
        return f"""
You are enriching a governed Unified Knowledge Base context pack. Return JSON only.
Use only these approved objects and evidence. Do not invent facts.

Return shape:
{{
  "ai_guidance": "short guidance for an AI app using this context pack",
  "missing_context": ["missing context warning"],
  "recommended_followups": ["follow-up question"]
}}

Question: {context_pack.question}
Mode: {context_pack.mode}
Approved objects: {objects}
Evidence: {evidence}
Existing guidance: {context_pack.answer_guidance}
""".strip()

    def _list_payload(self, payload: dict[str, Any], key: str) -> list[str]:
        value = payload.get(key)
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _string_payload(self, payload: dict[str, Any], key: str) -> str | None:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _model_available(self, model_names: list[str], configured_model: str | None) -> bool:
        if not configured_model:
            return True
        return any(name == configured_model or name.startswith(f"{configured_model}:") for name in model_names)
