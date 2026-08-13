from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from ukb.ai.providers.base import AIProviderError
from ukb.ai.providers.noop import NoopProvider
from ukb.models import AIEnrichmentResult, AIProviderName, ContextPack, KnowledgeObject, SourceEvidence


class OllamaProvider:
    """Local Ollama adapter.

    The provider asks a local model to produce JSON. If the model is unavailable
    or returns invalid data, callers should fall back to NoopProvider through the
    AIEnrichmentService.
    """

    name = AIProviderName.ollama.value

    def __init__(self, *, base_url: str, model: str, timeout_seconds: int = 45):
        self.base_url = base_url.rstrip("/")
        if self.base_url.endswith("/api"):
            self.api_base = self.base_url
        else:
            self.api_base = f"{self.base_url}/api"
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._fallback = NoopProvider()

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
        return fallback.model_copy(
            update={
                "provider": AIProviderName.ollama,
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
        if not context_pack.knowledge_objects:
            return self._fallback.enrich_context_pack(context_pack=context_pack)
        prompt = self._context_pack_prompt(context_pack)
        try:
            payload = self._generate_json(prompt)
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

    def _generate_json(self, prompt: str) -> dict[str, Any]:
        body = json.dumps({"model": self.model, "prompt": prompt, "stream": False, "format": "json"}).encode()
        request = urllib.request.Request(
            f"{self.api_base}/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AIProviderError(f"Ollama request failed: {exc}") from exc

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

    def _source_prompt(self, *, source: SourceEvidence, content: str, baseline_candidate: KnowledgeObject) -> str:
        return f"""
You are an AI curator for a governed knowledge-base platform. Return JSON only.
Do not approve or publish knowledge. Produce reviewer-facing enrichment.

Return shape:
{{
  "summary": "short source summary",
  "topics": ["topic"],
  "review_brief": "what should the reviewer know",
  "reviewer_questions": ["question"]
}}

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
You are enriching a governed context pack. Return JSON only.
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
