from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

from ukb.connectors.web_policy import WebConnectorError, WebUrlPolicy


@dataclass(frozen=True)
class FetchedWebPage:
    requested_url: str
    final_url: str
    status_code: int
    content_type: str
    charset: str
    body: bytes
    headers: dict[str, str]


class WebFetcher(Protocol):
    def fetch(self, url: str) -> FetchedWebPage: ...


class HttpWebFetcher:
    """Collect one configured source page with bounded size and redirects."""

    accepted_types = {
        "text/html",
        "text/plain",
        "text/markdown",
        "application/json",
        "application/xml",
        "text/xml",
    }

    def __init__(
        self,
        *,
        policy: WebUrlPolicy,
        user_agent: str,
        timeout_seconds: int,
        max_response_bytes: int,
        max_redirects: int,
    ):
        self.policy = policy
        self.user_agent = user_agent
        self.max_response_bytes = max_response_bytes
        self.max_redirects = max_redirects
        self.client = httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=False,
            headers={"User-Agent": user_agent, "Accept-Encoding": "identity"},
        )

    def fetch(self, url: str) -> FetchedWebPage:
        requested_url = url
        current_url = url
        for _ in range(self.max_redirects + 1):
            validated = self.policy.validate(current_url)
            try:
                response = self.client.get(validated.url)
            except httpx.HTTPError as exc:
                raise WebConnectorError(f"Source request failed: {exc}") from exc
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise WebConnectorError("Source redirect did not include a destination.")
                current_url = str(response.url.join(location))
                continue
            if not response.is_success:
                raise WebConnectorError(f"Source returned HTTP status {response.status_code}.")
            content_type = response.headers.get("content-type", "").split(";", 1)[0].casefold()
            if content_type not in self.accepted_types:
                raise WebConnectorError(f"Unsupported source content type: {content_type}")
            body = response.content
            if len(body) > self.max_response_bytes:
                raise WebConnectorError("Source response exceeds the configured size limit.")
            return FetchedWebPage(
                requested_url=requested_url,
                final_url=str(response.url),
                status_code=response.status_code,
                content_type=content_type,
                charset=response.encoding or "utf-8",
                body=body,
                headers=dict(response.headers),
            )
        raise WebConnectorError("Source exceeded the configured redirect limit.")

    def close(self) -> None:
        self.client.close()


class RobotsAwareWebFetcher:
    """Apply the site's robots policy before collecting a page."""

    def __init__(self, *, fetcher: HttpWebFetcher, user_agent: str, fail_closed: bool):
        self.fetcher = fetcher
        self.user_agent = user_agent
        self.fail_closed = fail_closed

    def fetch(self, url: str) -> FetchedWebPage:
        parsed = urlsplit(url)
        robots_url = urlunsplit((parsed.scheme, parsed.netloc, "/robots.txt", "", ""))
        try:
            robots = self.fetcher.fetch(robots_url)
        except WebConnectorError as exc:
            message = str(exc)
            if "HTTP status 404" not in message and "HTTP status 410" not in message:
                if self.fail_closed:
                    raise WebConnectorError("Robots policy could not be verified.") from exc
            return self.fetcher.fetch(url)

        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(robots.body.decode(robots.charset, errors="replace").splitlines())
        if not parser.can_fetch(self.user_agent, url):
            raise WebConnectorError("The site's robots policy does not allow collection.")
        return self.fetcher.fetch(url)

    def close(self) -> None:
        self.fetcher.close()
