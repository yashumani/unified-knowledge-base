from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml
from pydantic import ValidationError

from ukb.talk2data.models import (
    MemoryStatus,
    ObsidianFrontmatter,
    ObsidianValidationResult,
)


@dataclass(frozen=True)
class ParsedObsidianNote:
    frontmatter: ObsidianFrontmatter
    body: str
    wiki_links: list[str]
    source_relationships: list[str]


class ObsidianNoteValidator:
    """Validate Obsidian Markdown before it can be promoted to canonical memory."""

    FRONTMATTER = re.compile(r"\A---\s*\n(?P<yaml>.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
    WIKI_LINK = re.compile(r"\[\[([^\]]+)\]\]")

    def validate(self, markdown: str) -> ObsidianValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        match = self.FRONTMATTER.match(markdown)
        if match is None:
            return ObsidianValidationResult(
                valid=False,
                authoritative=False,
                errors=["The note must begin with YAML frontmatter enclosed by --- delimiters."],
            )

        try:
            raw = yaml.safe_load(match.group("yaml")) or {}
        except yaml.YAMLError as exc:
            return ObsidianValidationResult(
                valid=False,
                authoritative=False,
                errors=[f"Invalid YAML frontmatter: {exc}"],
            )
        if not isinstance(raw, dict):
            return ObsidianValidationResult(
                valid=False,
                authoritative=False,
                errors=["YAML frontmatter must be an object."],
            )

        normalized = self._normalize_frontmatter(raw)
        try:
            frontmatter = ObsidianFrontmatter.model_validate(normalized)
        except ValidationError as exc:
            for error in exc.errors(include_url=False):
                location = ".".join(str(value) for value in error.get("loc", ()))
                errors.append(f"{location}: {error.get('msg', 'invalid value')}")
            return ObsidianValidationResult(
                valid=False,
                authoritative=False,
                errors=errors,
                body=markdown[match.end() :].strip(),
            )

        body = markdown[match.end() :].strip()
        if not body:
            errors.append("The note body is empty.")
        wiki_links = self._wiki_links(body)
        relationships = [f"wiki_link:{link}" for link in wiki_links]
        authoritative = (
            frontmatter.status in {MemoryStatus.approved, MemoryStatus.published}
            and bool(frontmatter.approved_by)
        )
        if frontmatter.status in {MemoryStatus.approved, MemoryStatus.published} and not frontmatter.approved_by:
            errors.append("Approved or published notes require approved_by.")
        if not authoritative and not errors:
            warnings.append(
                "The note is structurally valid but is not authoritative until status is approved or published and approved_by is set."
            )
        if frontmatter.version < 1:
            errors.append("version must be at least 1.")
        return ObsidianValidationResult(
            valid=not errors,
            authoritative=authoritative and not errors,
            errors=errors,
            warnings=warnings,
            frontmatter=frontmatter,
            body=body,
            wiki_links=wiki_links,
            source_relationships=relationships,
        )

    def parse_authoritative(self, markdown: str) -> ParsedObsidianNote:
        result = self.validate(markdown)
        if not result.valid:
            raise ValueError("; ".join(result.errors))
        if not result.authoritative or result.frontmatter is None:
            raise ValueError(
                "The Obsidian note is not approved organizational knowledge and cannot be promoted."
            )
        return ParsedObsidianNote(
            frontmatter=result.frontmatter,
            body=result.body,
            wiki_links=result.wiki_links,
            source_relationships=result.source_relationships,
        )

    @staticmethod
    def _normalize_frontmatter(raw: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(raw)
        for name in (
            "related_metrics",
            "related_entities",
            "allowed_roles",
            "denied_roles",
            "tags",
        ):
            value = normalized.get(name)
            if value is None:
                normalized[name] = []
            elif isinstance(value, str):
                normalized[name] = [part.strip() for part in value.split(",") if part.strip()]
        return normalized

    @classmethod
    def _wiki_links(cls, body: str) -> list[str]:
        links: list[str] = []
        for raw in cls.WIKI_LINK.findall(body):
            target = raw.split("|", 1)[0].split("#", 1)[0].strip()
            if target and target not in links:
                links.append(target)
        return links
