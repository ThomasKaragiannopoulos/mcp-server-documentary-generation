"""
MCP Server — Documentary Generation
Registers tools for Claude Code to orchestrate autonomous documentary production.
"""

import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from tools.research import research

app = Server("mcp-server-documentary-generation")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="research",
            description=(
                "Fetch Wikipedia content for a documentary topic and build a structured outline. "
                "Tries Greek Wikipedia first, falls back to English. "
                "Saves outline to research/<topic>/outline.txt and returns it."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The documentary topic (e.g. 'Άλωση της Κωνσταντινούπολης')"
                    }
                },
                "required": ["topic"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "research":
        result = research(arguments["topic"])
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
