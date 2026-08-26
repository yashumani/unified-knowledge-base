from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


REQUIRED_TOOLS = {
    "runtime_status",
    "start_conversation",
    "list_conversations",
    "get_conversation",
    "ask_brain",
    "submit_context",
    "list_review_items",
    "search_brain",
    "get_context_pack",
    "get_source_lineage",
    "invalidate_cache",
    "approve_review_item",
    "publish_review_item",
}


async def validate(url: str) -> dict[str, Any]:
    async with streamablehttp_client(url) as streams:
        read_stream, write_stream = streams[0], streams[1]
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            resources_result = await session.list_resources()
            tool_names = {tool.name for tool in tools_result.tools}
            missing = sorted(REQUIRED_TOOLS - tool_names)
            if missing:
                raise RuntimeError(f"MCP server is missing required tools: {missing}")
            status_result = await session.call_tool("runtime_status", {})
            status_text = "\n".join(
                str(getattr(item, "text", "")) for item in status_result.content
            )
            if "cache_backend" not in status_text or "mcp_transport" not in status_text:
                raise RuntimeError(f"Runtime status did not expose governed cache/MCP metadata: {status_text}")
            conversation_result = await session.call_tool(
                "start_conversation",
                {"title": "MCP transport validation"},
            )
            conversation_text = "\n".join(
                str(getattr(item, "text", "")) for item in conversation_result.content
            )
            if "conversation_id" not in conversation_text:
                raise RuntimeError("MCP conversation creation did not return a conversation_id")
            resource_uris = sorted(str(resource.uri) for resource in resources_result.resources)
            required_resources = {
                "brain://runtime/status",
                "brain://objects",
                "brain://review-queue",
                "brain://conversations/recent",
            }
            if not required_resources.issubset(set(resource_uris)):
                raise RuntimeError(
                    f"MCP resources missing: {sorted(required_resources - set(resource_uris))}"
                )
            return {
                "url": url,
                "tool_count": len(tool_names),
                "tools": sorted(tool_names),
                "resources": resource_uris,
                "status": "success",
            }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the governed Streamable HTTP MCP server")
    parser.add_argument("--url", default="http://127.0.0.1:8765/mcp")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = asyncio.run(validate(args.url))
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")


if __name__ == "__main__":
    main()
