from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from importlib.metadata import version


async def validate() -> dict[str, object]:
    from graphiti_core import Graphiti

    uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "ukb-graphiti-password")
    graphiti = Graphiti(uri=uri, user=user, password=password)
    try:
        await graphiti.build_indices_and_constraints()
        records, _, _ = await graphiti.driver.execute_query(
            "RETURN 1 AS value",
            routing_="r",
        )
        if not records or records[0].get("value") != 1:
            raise RuntimeError("Graphiti connected, but the Neo4j read probe failed.")
        return {
            "status": "ok",
            "graphiti_core_version": version("graphiti-core"),
            "backend": "neo4j",
            "uri": uri,
            "indices_and_constraints_initialized": True,
            "read_probe": records[0].get("value"),
            "canonical_storage": "external_to_graphiti",
        }
    finally:
        await graphiti.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the pinned Graphiti SDK against a real Neo4j runtime."
    )
    parser.add_argument("--expect-version", default="0.29.3")
    args = parser.parse_args()
    # Graphiti constructs default OpenAI-compatible clients even though this
    # connectivity smoke test performs no LLM or embedding calls.
    os.environ.setdefault("OPENAI_API_KEY", "graphiti-smoke-not-used")
    result = asyncio.run(validate())
    print(json.dumps(result, indent=2))
    return 0 if result["graphiti_core_version"] == args.expect_version else 1


if __name__ == "__main__":
    sys.exit(main())
