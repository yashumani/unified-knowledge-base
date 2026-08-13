from pathlib import Path

import pytest

from ukb.connectors.web import WebKnowledgeConnector
from ukb.connectors.web_fetcher import FetchedWebPage
from ukb.connectors.web_models import WebCaptureRequest
from ukb.connectors.web_policy import WebConnectorError, WebUrlPolicy
from ukb.models import Sensitivity
from ukb.services.compiler import BrainCompiler
from ukb.storage.objects import LocalObjectStore


class FakeFetcher:
    def __init__(self, page: FetchedWebPage):
        self.page = page

    def fetch(self, url: str) -> FetchedWebPage:
        return self.page


def build_policy() -> WebUrlPolicy:
    return WebUrlPolicy(
        allowed_hosts=["docs.example.org"],
        allowed_ports=[80, 443],
        allow_private_networks=False,
    )


def test_url_policy_requires_configured_hosts_and_web_schemes() -> None:
    source_policy = build_policy()

    assert source_policy.validate("https://docs.example.org/guide").host == "docs.example.org"
    with pytest.raises(WebConnectorError, match="not configured"):
        source_policy.validate("https://other.example.org/guide")
    with pytest.raises(WebConnectorError, match="Only HTTP and HTTPS"):
        source_policy.validate("ftp://docs.example.org/guide")


def test_url_policy_rejects_local_ip_literals() -> None:
    source_policy = WebUrlPolicy(
        allowed_hosts=["127.0.0.1"],
        allowed_ports=[80],
        allow_private_networks=False,
    )

    with pytest.raises(WebConnectorError, match="Private or special-use"):
        source_policy.validate("http://127.0.0.1/")


def test_web_connector_preserves_original_and_creates_candidate(tmp_path: Path) -> None:
    body = b"""<!doctype html><html><head>
      <title>Service Quality Guide</title>
      <link rel="canonical" href="https://docs.example.org/guides/quality" />
      <script>ignore this code</script>
      </head><body><h1>Incident quality</h1>
      <p>Resolution quality is reviewed before publication.</p>
      <a href="/guides/related">Related guide</a></body></html>"""
    page = FetchedWebPage(
        requested_url="https://docs.example.org/guides/quality",
        final_url="https://docs.example.org/guides/quality",
        status_code=200,
        content_type="text/html",
        charset="utf-8",
        body=body,
        headers={"content-type": "text/html; charset=utf-8"},
    )
    object_store = LocalObjectStore(tmp_path / "objects")
    connector = WebKnowledgeConnector(
        compiler=BrainCompiler(),
        object_store=object_store,
        fetcher=FakeFetcher(page),
        policy=build_policy(),
        max_extracted_chars=10000,
    )

    result = connector.capture(
        WebCaptureRequest(
            url=page.requested_url,
            submitted_by="web-test.submitter",
            domain="support",
            sensitivity=Sensitivity.internal,
        )
    )

    assert result.source.title == "Service Quality Guide"
    assert result.source.source_uri == "https://docs.example.org/guides/quality"
    assert "ignore this code" not in result.source.content_excerpt
    assert result.review_item.source_id == result.source.source_id
    assert object_store.get_bytes(result.artifact.object_key) == body
    assert result.artifact.discovered_links == ["https://docs.example.org/guides/related"]
