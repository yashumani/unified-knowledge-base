from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlsplit

from ukb.connectors.html_extract import extract_page
from ukb.connectors.web_fetcher import WebFetcher
from ukb.connectors.web_models import (
    WebArtifactMetadata,
    WebCaptureRequest,
    WebCaptureResponse,
    WebConnectorStatus,
)
from ukb.connectors.web_policy import WebConnectorError, WebUrlPolicy
from ukb.models import IngestionSubmission, SourceType
from ukb.services.compiler import BrainCompiler
from ukb.storage.objects import LocalObjectStore


class WebKnowledgeConnector:
    """Preserve one configured web source and create a review candidate."""

    extensions = {
        "text/html": ".html",
        "text/plain": ".txt",
        "text/markdown": ".md",
        "application/json": ".json",
        "application/xml": ".xml",
        "text/xml": ".xml",
    }

    def __init__(
        self,
        *,
        compiler: BrainCompiler,
        object_store: LocalObjectStore,
        fetcher: WebFetcher,
        policy: WebUrlPolicy,
        max_extracted_chars: int,
    ):
        self.compiler = compiler
        self.object_store = object_store
        self.fetcher = fetcher
        self.policy = policy
        self.max_extracted_chars = max_extracted_chars

    def capture(self, request: WebCaptureRequest) -> WebCaptureResponse:
        page = self.fetcher.fetch(request.url)
        extracted = extract_page(
            body=page.body,
            content_type=page.content_type,
            charset=page.charset,
            base_url=page.final_url,
        )
        content = extracted.text[: self.max_extracted_chars].strip()
        if not content:
            raise WebConnectorError("The source page did not contain usable text.")

        canonical_url = page.final_url
        if extracted.canonical_url:
            try:
                canonical_url = self.policy.validate(extracted.canonical_url).url
            except WebConnectorError:
                canonical_url = page.final_url

        digest = hashlib.sha256(page.body).hexdigest()
        host = urlsplit(page.final_url).hostname or "source"
        extension = self.extensions.get(page.content_type, ".bin")
        object_key = f"web/{host}/{digest}{extension}"
        stored = self.object_store.put_bytes(object_key, page.body)

        title = request.title or extracted.title or Path(urlsplit(page.final_url).path).stem
        title = (title or f"Web source from {host}").strip()
        if len(title) < 3:
            title = f"Web source {title}"
        source_type = SourceType.api if page.content_type == "application/json" else SourceType.document
        submission = IngestionSubmission(
            title=title,
            source_type=source_type,
            submitted_by=request.submitted_by,
            content=content,
            source_uri=canonical_url,
            domain=request.domain,
            sensitivity=request.sensitivity,
            tags=sorted(set(["web-connector", host, *request.tags])),
        )
        source, review_item = self.compiler.compile_submission(submission)
        source.source_uri = canonical_url

        return WebCaptureResponse(
            source=source,
            review_item=review_item,
            artifact=WebArtifactMetadata(
                requested_url=page.requested_url,
                final_url=page.final_url,
                canonical_url=canonical_url,
                content_type=page.content_type,
                object_key=stored.key,
                object_uri=stored.uri,
                content_digest=stored.sha256,
                size_bytes=stored.size_bytes,
                discovered_links=extracted.links,
            ),
            extracted_text=content,
        )


__all__ = [
    "WebCaptureRequest",
    "WebCaptureResponse",
    "WebConnectorError",
    "WebConnectorStatus",
    "WebKnowledgeConnector",
]
