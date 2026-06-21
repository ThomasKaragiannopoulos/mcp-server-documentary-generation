"""
MCP Server — Documentary Generation
Registers tools for Claude Code to orchestrate autonomous documentary production.
"""

import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from tools.research import research
from tools.storyboard import build_storyboard, save_storyboard

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
        Tool(
            name="build_storyboard",
            description=(
                "Parse a script file into scenes and save a storyboard JSON skeleton. "
                "Returns scenes with narration text ready for image prompt injection by the orchestrator. "
                "Saves to storyboard/scenes.json."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "script_path": {
                        "type": "string",
                        "description": "Path to the script .txt file"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output JSON path (default: storyboard/scenes.json)"
                    }
                },
                "required": ["script_path"]
            }
        ),
        Tool(
            name="save_storyboard",
            description=(
                "Save a completed storyboard (with image prompts filled in) to disk. "
                "Called after the orchestrator has generated image prompts for each scene."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "scenes": {
                        "type": "array",
                        "description": "List of scene objects with image_prompt filled"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output JSON path (default: storyboard/scenes.json)"
                    }
                },
                "required": ["scenes"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "research":
        result = research(arguments["topic"])
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    if name == "build_storyboard":
        result = build_storyboard(
            arguments["script_path"],
            arguments.get("output_path", "storyboard/scenes.json")
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    if name == "save_storyboard":
        path = save_storyboard(
            arguments["scenes"],
            arguments.get("output_path", "storyboard/scenes.json")
        )
        return [TextContent(type="text", text=json.dumps({"path": path, "scene_count": len(arguments["scenes"])}))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
