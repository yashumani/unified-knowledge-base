from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ukb.models import ReviewItem, Sensitivity, SourceEvidence, utc_now


class WebCaptureRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=2048)
    submitted_by: str = Field(..., min_length=1, max_length=200)
    domain: str = Field(default="general", min_length=1, max_length=200)
    sensitivity: Sensitivity = Sensitivity.internal
    title: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=50)


class WebArtifactMetadata(BaseModel):
    requested_url: str
    final_url: str
    canonical_url: str
    content_type: str
    object_key: str
    object_uri: str
    content_digest: str
    size_bytes: int
    resolved_ips: list[str] = Field(default_factory=list)
    discovered_links: list[str] = Field(default_factory=list)
    retrieved_at: datetime = Field(default_factory=utc_now)


class WebCaptureResponse(BaseModel):
    source: SourceEvidence
    review_item: ReviewItem
    artifact: WebArtifactMetadata


class WebConnectorStatus(BaseModel):
    enabled: bool
    ready: bool
    allowed_hosts: list[str] = Field(default_factory=list)
    allowed_ports: list[int] = Field(default_factory=list)
    allow_private_networks: bool = False
    respect_robots: bool = True
    robots_fail_closed: bool = True
    max_response_bytes: int
    user_agent: str
    message: str
