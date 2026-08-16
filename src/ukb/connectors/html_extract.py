from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit


@dataclass(frozen=True)
class ExtractedPage:
    title: str | None
    text: str
    canonical_url: str | None
    links: list[str]


class _PageParser(HTMLParser):
    ignored_tags = {"script", "style", "noscript", "template", "svg"}

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.ignored_depth = 0
        self.in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.canonical_url: str | None = None
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.casefold()
        attributes = {key.casefold(): value for key, value in attrs}
        if lowered in self.ignored_tags:
            self.ignored_depth += 1
            return
        if self.ignored_depth:
            return
        if lowered == "title":
            self.in_title = True
        if lowered == "link" and "canonical" in (attributes.get("rel") or "").casefold():
            href = attributes.get("href")
            if href:
                self.canonical_url = urljoin(self.base_url, href)
        if lowered == "a":
            href = attributes.get("href")
            if href:
                candidate = urljoin(self.base_url, href)
                if urlsplit(candidate).scheme in {"http", "https"}:
                    self.links.append(candidate)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.casefold()
        if lowered in self.ignored_tags and self.ignored_depth:
            self.ignored_depth -= 1
            return
        if lowered == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.ignored_depth:
            return
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        if self.in_title:
            self.title_parts.append(cleaned)
        self.text_parts.append(cleaned)


def extract_page(*, body: bytes, content_type: str, charset: str, base_url: str) -> ExtractedPage:
    text = body.decode(charset or "utf-8", errors="replace")
    if content_type != "text/html":
        return ExtractedPage(title=None, text=text.strip(), canonical_url=None, links=[])

    parser = _PageParser(base_url)
    parser.feed(text)
    parser.close()
    return ExtractedPage(
        title=" ".join(parser.title_parts).strip() or None,
        text="\n".join(parser.text_parts).strip(),
        canonical_url=parser.canonical_url,
        links=sorted(set(parser.links))[:200],
    )
