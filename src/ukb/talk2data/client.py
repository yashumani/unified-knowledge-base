from __future__ import annotations

from datetime import datetime
from typing import Any, TypeVar
from uuid import uuid4

import httpx
from pydantic import BaseModel, TypeAdapter

from ukb.talk2data.models import (
    ContextCoverageReceipt,
    ContextCoverageRequest,
    DomainClassificationResult,
    DomainPackVersionList,
    GraphAdapterStatus,
    IndexWatermark,
    MemoryQuery,
    MemoryQueryResult,
    SourceIngestionHealth,
    TenantDomainPack,
    TimelineRequest,
    VocabularyResolution,
    VocabularyResolutionRequest,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class Talk2DataClientError(RuntimeError):
    """Raised when the governed-memory API cannot satisfy a client request."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id


class Talk2DataMemoryClient:
    """Thin typed client for the versioned Talk2Data memory contract.

    Authorization remains a server responsibility. The client forwards the
    bearer token and validates only the shape of already-filtered responses.
    """

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/") + "/",
            timeout=timeout_seconds,
            transport=transport,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "UKB-Talk2Data-Client/1.0",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Talk2DataMemoryClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get_current_domain_pack(
        self,
        *,
        effective_at: datetime | None = None,
    ) -> TenantDomainPack:
        params = {"effective_at": effective_at.isoformat()} if effective_at else None
        return self._model("GET", "v1/domain-packs/current", TenantDomainPack, params=params)

    def list_domain_pack_versions(self) -> list[TenantDomainPack]:
        response = self._model(
            "GET",
            "v1/domain-packs/versions",
            DomainPackVersionList,
        )
        return response.domain_packs

    def resolve_vocabulary(self, term: str) -> VocabularyResolution:
        return self._model(
            "POST",
            "v1/domain-packs/resolve",
            VocabularyResolution,
            payload=VocabularyResolutionRequest(term=term),
        )

    def classify_question(self, question: str) -> DomainClassificationResult:
        return self._model(
            "POST",
            "v1/domain-packs/classify",
            DomainClassificationResult,
            payload={"question": question},
        )

    def query_memory(self, request: MemoryQuery) -> MemoryQueryResult:
        return self._model(
            "POST",
            "v1/memory/query",
            MemoryQueryResult,
            payload=request,
        )

    def query_memory_with_graph(self, request: MemoryQuery) -> MemoryQueryResult:
        return self._model(
            "POST",
            "v1/memory/query/graph",
            MemoryQueryResult,
            payload=request,
        )

    def entity_timeline(
        self,
        identifier: str,
        *,
        effective_at: datetime | None = None,
        limit: int = 100,
    ) -> MemoryQueryResult:
        return self._model(
            "POST",
            "v1/memory/timelines/entities",
            MemoryQueryResult,
            payload=TimelineRequest(
                identifier=identifier,
                effective_at=effective_at,
                limit=limit,
            ),
        )

    def metric_timeline(
        self,
        identifier: str,
        *,
        effective_at: datetime | None = None,
        limit: int = 100,
    ) -> MemoryQueryResult:
        return self._model(
            "POST",
            "v1/memory/timelines/metrics",
            MemoryQueryResult,
            payload=TimelineRequest(
                identifier=identifier,
                effective_at=effective_at,
                limit=limit,
            ),
        )

    def prior_investigations(self, request: MemoryQuery) -> MemoryQueryResult:
        return self._model(
            "POST",
            "v1/memory/investigations",
            MemoryQueryResult,
            payload=request,
        )

    def get_context_coverage_receipt(
        self,
        request: ContextCoverageRequest,
    ) -> ContextCoverageReceipt:
        return self._model(
            "POST",
            "v1/memory/context-coverage",
            ContextCoverageReceipt,
            payload=request,
        )

    def list_source_health(self) -> list[SourceIngestionHealth]:
        payload = self._json("GET", "v1/memory/source-health")
        return TypeAdapter(list[SourceIngestionHealth]).validate_python(payload)

    def list_index_watermarks(self) -> list[IndexWatermark]:
        payload = self._json("GET", "v1/memory/index-watermarks")
        return TypeAdapter(list[IndexWatermark]).validate_python(payload)

    def graph_status(self) -> GraphAdapterStatus:
        return self._model("GET", "v1/graph/status", GraphAdapterStatus)

    def _model(
        self,
        method: str,
        path: str,
        model: type[ModelT],
        *,
        payload: BaseModel | dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> ModelT:
        return model.model_validate(
            self._json(method, path, payload=payload, params=params)
        )

    def _json(
        self,
        method: str,
        path: str,
        *,
        payload: BaseModel | dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        request_id = f"t2d_{uuid4().hex[:16]}"
        json_payload: dict[str, Any] | None
        if isinstance(payload, BaseModel):
            json_payload = payload.model_dump(mode="json", exclude_none=True)
        else:
            json_payload = payload
        try:
            response = self._client.request(
                method,
                path,
                json=json_payload,
                params=params,
                headers={"X-Request-ID": request_id},
            )
        except httpx.TimeoutException as exc:
            raise Talk2DataClientError(
                f"Talk2Data memory request timed out: {method} {path}",
                request_id=request_id,
            ) from exc
        except httpx.HTTPError as exc:
            raise Talk2DataClientError(
                f"Talk2Data memory request failed: {method} {path}: {exc}",
                request_id=request_id,
            ) from exc

        response_request_id = response.headers.get("X-Request-ID", request_id)
        if not response.is_success:
            message = response.text
            try:
                detail = response.json().get("detail")
                if detail:
                    message = str(detail)
            except (ValueError, AttributeError):
                pass
            raise Talk2DataClientError(
                message,
                status_code=response.status_code,
                request_id=response_request_id,
            )
        try:
            return response.json()
        except ValueError as exc:
            raise Talk2DataClientError(
                f"Talk2Data memory API returned invalid JSON for {method} {path}.",
                status_code=response.status_code,
                request_id=response_request_id,
            ) from exc
