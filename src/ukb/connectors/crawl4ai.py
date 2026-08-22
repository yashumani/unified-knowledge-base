from __future__ import annotations

import hashlib
import re
import time
from collections import deque
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

from ukb.config import Settings
from ukb.connectors.web_policy import WebConnectorError, WebUrlPolicy
from ukb.ingestion_models import CrawlIngestionRequest
from ukb.services.ingestion import RawIngestionItem


class Crawl4AIConnectorError(RuntimeError):
    pass


@dataclass(frozen=True)
class CrawlCollection:
    items: list[RawIngestionItem]
    warnings: list[str]
    discovered_links: list[str]


class Crawl4AIConnector:
    """Private Crawl4AI sidecar adapter with UKB policy and provenance checks."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.policy = WebUrlPolicy(
            allowed_hosts=settings.web_hosts,
            allowed_ports=settings.web_ports,
            allow_private_networks=settings.web_allow_private_networks,
        )

    def collect(self, request: CrawlIngestionRequest) -> CrawlCollection:
        if not self.settings.crawl4ai_enabled:
            raise Crawl4AIConnectorError("Crawl4AI ingestion is disabled.")
        if not self.settings.web_hosts:
            raise Crawl4AIConnectorError(
                "Configure UKB_WEB_ALLOWED_HOSTS before using Crawl4AI."
            )
        max_pages = min(request.max_pages, self.settings.crawl4ai_max_pages)
        start = self._validate(str(request.url))
        queue: deque[tuple[str, int]] = deque([(start, 0)])
        visited: set[str] = set()
        discovered: set[str] = set()
        items: list[RawIngestionItem] = []
        warnings: list[str] = []
        headers = {"Content-Type": "application/json"}
        if self.settings.crawl4ai_api_token:
            headers["Authorization"] = f"Bearer {self.settings.crawl4ai_api_token}"

        with httpx.Client(
            base_url=self.settings.crawl4ai_base_url.rstrip("/"),
            headers=headers,
            timeout=self.settings.crawl4ai_timeout_seconds,
            follow_redirects=False,
        ) as client:
            while queue and len(items) < max_pages:
                url, depth = queue.popleft()
                if url in visited:
                    continue
                visited.add(url)
                try:
                    result = self._crawl_one(client, url, request)
                except Crawl4AIConnectorError as exc:
                    warnings.append(f"{url}: {exc}")
                    continue
                markdown = result["markdown"].strip()
                if not markdown:
                    warnings.append(f"{url}: Crawl4AI returned no usable Markdown.")
                    continue
                title = result.get("title") or urlsplit(url).path.rsplit("/", 1)[-1] or "page"
                path = self._path(url, len(items))
                items.append(
                    RawIngestionItem(
                        name=f"{self._safe_name(title)}.md",
                        path=path,
                        data=markdown.encode("utf-8"),
                        content_type="text/markdown",
                        source_uri=url,
                    )
                )
                for raw_link in result.get("links", []):
                    candidate = urljoin(url, raw_link)
                    try:
                        validated = self._validate(candidate)
                    except Crawl4AIConnectorError:
                        continue
                    discovered.add(validated)
                    if depth < request.max_depth and validated not in visited:
                        queue.append((validated, depth + 1))

        if queue:
            warnings.append(f"Stopped after the configured {max_pages}-page limit.")
        if request.respect_robots:
            warnings.append("Crawl4AI robots checking was requested for every page.")
        if not items:
            warnings.append("No authorized page produced usable Markdown.")
        return CrawlCollection(
            items=items,
            warnings=warnings,
            discovered_links=sorted(discovered),
        )

    def _crawl_one(
        self,
        client: httpx.Client,
        url: str,
        request: CrawlIngestionRequest,
    ) -> dict:
        payload = {
            "urls": [url],
            "priority": 10,
            "browser_config": {
                "type": "BrowserConfig",
                "params": {
                    "headless": True,
                    "text_mode": not request.render_javascript,
                },
            },
            "crawler_config": {
                "type": "CrawlerRunConfig",
                "params": {
                    "check_robots_txt": request.respect_robots,
                    "word_count_threshold": 10,
                    "remove_overlay_elements": True,
                    "exclude_external_links": False,
                },
            },
        }
        response = client.post("/crawl", json=payload)
        if response.status_code >= 400:
            raise Crawl4AIConnectorError(
                f"sidecar returned {response.status_code}: {response.text[:300]}"
            )
        raw = response.json()
        if isinstance(raw, dict) and raw.get("task_id") and not raw.get("results"):
            raw = self._wait_for_task(client, str(raw["task_id"]))
        result = self._first_result(raw)
        markdown = self._markdown(result)
        if len(markdown) > self.settings.max_extracted_chars:
            markdown = markdown[: self.settings.max_extracted_chars]
        metadata = result.get("metadata") if isinstance(result, dict) else {}
        title = metadata.get("title") if isinstance(metadata, dict) else None
        return {
            "title": str(title or "").strip() or None,
            "markdown": markdown,
            "links": self._links(result),
        }

    def _wait_for_task(self, client: httpx.Client, task_id: str) -> object:
        deadline = time.monotonic() + self.settings.crawl4ai_timeout_seconds
        while time.monotonic() < deadline:
            response = client.get(f"/task/{task_id}")
            if response.status_code >= 400:
                raise Crawl4AIConnectorError(
                    f"task status returned {response.status_code}: {response.text[:200]}"
                )
            payload = response.json()
            status = str(payload.get("status", "")).casefold() if isinstance(payload, dict) else ""
            if status in {"completed", "success", "done"}:
                return payload
            if status in {"failed", "error", "cancelled"}:
                raise Crawl4AIConnectorError(str(payload.get("error") or status))
            time.sleep(0.5)
        raise Crawl4AIConnectorError("Crawl4AI task timed out.")

    @staticmethod
    def _first_result(payload: object) -> dict:
        if isinstance(payload, dict):
            raw_results = payload.get("results") or payload.get("result")
            if isinstance(raw_results, list) and raw_results:
                return raw_results[0] if isinstance(raw_results[0], dict) else {}
            if isinstance(raw_results, dict):
                return raw_results
            if any(key in payload for key in ("markdown", "cleaned_html", "url")):
                return payload
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            return payload[0]
        raise Crawl4AIConnectorError("Crawl4AI response did not include a crawl result.")

    @staticmethod
    def _markdown(result: dict) -> str:
        raw = result.get("markdown", "")
        if isinstance(raw, str):
            return raw
        if isinstance(raw, dict):
            for key in ("fit_markdown", "raw_markdown", "markdown_with_citations"):
                value = raw.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        return ""

    @staticmethod
    def _links(result: dict) -> list[str]:
        raw = result.get("links", [])
        values: list[object] = []
        if isinstance(raw, list):
            values.extend(raw)
        elif isinstance(raw, dict):
            for collection in raw.values():
                if isinstance(collection, list):
                    values.extend(collection)
        links: list[str] = []
        for value in values:
            if isinstance(value, str):
                links.append(value)
            elif isinstance(value, dict):
                href = value.get("href") or value.get("url")
                if isinstance(href, str):
                    links.append(href)
        return links

    def _validate(self, url: str) -> str:
        try:
            return self.policy.validate(url).url
        except WebConnectorError as exc:
            raise Crawl4AIConnectorError(str(exc)) from exc

    @staticmethod
    def _path(url: str, index: int) -> str:
        parsed = urlsplit(url)
        path = parsed.path.strip("/") or "index"
        path = re.sub(r"[^A-Za-z0-9._/-]+", "-", path)
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
        return f"crawl/{parsed.hostname}/{index + 1:03d}-{path}-{digest}.md"

    @staticmethod
    def _safe_name(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")[:120] or "page"
