from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI

from ukb.talk2data.models import (
    CanonicalEpisode,
    ContextCoverageReceipt,
    DomainClassificationResult,
    GovernedMemoryObject,
    IndexWatermark,
    MemoryQuery,
    MemoryQueryResult,
    ObsidianFrontmatter,
    SourceIngestionHealth,
    TenantDomainPack,
)
from ukb.talk2data.routes import router

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "talk2data" / "v1"
OPENAPI_PATH = ROOT / "docs" / "openapi-talk2data.json"

MODELS = {
    "tenant-domain-pack.schema.json": TenantDomainPack,
    "canonical-episode.schema.json": CanonicalEpisode,
    "governed-memory-object.schema.json": GovernedMemoryObject,
    "memory-query.schema.json": MemoryQuery,
    "memory-query-result.schema.json": MemoryQueryResult,
    "context-coverage-receipt.schema.json": ContextCoverageReceipt,
    "obsidian-frontmatter.schema.json": ObsidianFrontmatter,
    "source-ingestion-health.schema.json": SourceIngestionHealth,
    "index-watermark.schema.json": IndexWatermark,
    "domain-classification-result.schema.json": DomainClassificationResult,
}


def main() -> None:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    for name, model in MODELS.items():
        path = SCHEMA_DIR / name
        path.write_text(
            json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    app = FastAPI(
        title="Talk2Data Domain Pack and Governed Memory API",
        version="1.0.0",
    )
    app.include_router(router)
    OPENAPI_PATH.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(MODELS)} JSON Schemas and {len(app.openapi()['paths'])} OpenAPI paths.")


if __name__ == "__main__":
    main()
