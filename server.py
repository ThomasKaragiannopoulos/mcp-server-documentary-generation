"""
MCP Server — Documentary Generation
Registers tools for Claude Code to orchestrate autonomous documentary production.
"""

import json
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from tools.research import research
from tools.storyboard import build_storyboard, save_storyboard
from tools.tts_batch import process_batch as tts_batch
from tools.image_gen import process_batch as image_gen
from tools.assemble import assemble as assemble_video
from tools.image_gen_chatgpt import process_batch as image_gen_chatgpt

app = Server("mcp-server-documentary-generation")

FFMPEG_BIN = (
    r"C:\Users\thkaragi\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-8.1.1-full_build\bin"
)


def _ensure_ffmpeg():
    if FFMPEG_BIN not in os.environ.get("PATH", ""):
        os.environ["PATH"] = FFMPEG_BIN + ";" + os.environ.get("PATH", "")


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
                "Saves to generated/<title>/scenes.json."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "script_path": {
                        "type": "string",
                        "description": "Path to the script .txt file"
                    },
                    "title": {
                        "type": "string",
                        "description": "Documentary title (used as folder name)"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Override output JSON path (optional)"
                    }
                },
                "required": ["script_path", "title"]
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
        Tool(
            name="tts_batch",
            description=(
                "Generate narration audio (WAV) for all scenes in a storyboard using Chatterbox TTS. "
                "Skips scenes that already have audio (checkpointing). "
                "Saves to generated/<title>/scene_XX/audio.wav."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "storyboard_path": {
                        "type": "string",
                        "description": "Path to scenes.json"
                    },
                    "title": {
                        "type": "string",
                        "description": "Documentary title (matches project folder)"
                    },
                    "speed": {
                        "type": "number",
                        "description": "Playback speed ratio (default 0.85 for deliberate pacing)"
                    }
                },
                "required": ["storyboard_path", "title"]
            }
        ),
        Tool(
            name="image_gen",
            description=(
                "Generate images for all scenes using Stable Diffusion 1.5 (CPU). "
                "Skips scenes that already have image.png (checkpointing). "
                "Saves to generated/<title>/scene_XX/image.png."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "storyboard_path": {
                        "type": "string",
                        "description": "Path to scenes.json"
                    },
                    "title": {
                        "type": "string",
                        "description": "Documentary title (matches project folder)"
                    },
                    "steps": {
                        "type": "integer",
                        "description": "Diffusion steps (default 20)"
                    }
                },
                "required": ["storyboard_path", "title"]
            }
        ),
        Tool(
            name="assemble",
            description=(
                "Assemble all scene images and audio into a final video with Ken Burns effect. "
                "Requires both audio.wav and image.png per scene. "
                "Output: generated/<title>/video.mp4."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "storyboard_path": {
                        "type": "string",
                        "description": "Path to scenes.json"
                    },
                    "title": {
                        "type": "string",
                        "description": "Documentary title (matches project folder)"
                    }
                },
                "required": ["storyboard_path", "title"]
            }
        ),
        Tool(
            name="image_gen_chatgpt",
            description=(
                "Generate images via ChatGPT DALL-E 3 using Playwright browser automation. "
                "Higher quality than local SD 1.5. Requires ChatGPT Plus. "
                "First run opens browser for manual login; subsequent runs are headless. "
                "Skips scenes that already have image.png (checkpointing)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "storyboard_path": {
                        "type": "string",
                        "description": "Path to scenes.json"
                    },
                    "title": {
                        "type": "string",
                        "description": "Documentary title (matches project folder)"
                    }
                },
                "required": ["storyboard_path", "title"]
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
            arguments["title"],
            arguments.get("output_path"),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    if name == "save_storyboard":
        path = save_storyboard(
            arguments["scenes"],
            arguments.get("output_path", "storyboard/scenes.json")
        )
        return [TextContent(type="text", text=json.dumps({"path": path, "scene_count": len(arguments["scenes"])}))]

    if name == "tts_batch":
        result = tts_batch(
            arguments["storyboard_path"],
            arguments["title"],
            arguments.get("speed", 0.85),
        )
        return [TextContent(type="text", text=json.dumps({"scenes_processed": len(result)}))]

    if name == "image_gen":
        result = image_gen(
            arguments["storyboard_path"],
            arguments["title"],
            arguments.get("steps", 20),
        )
        return [TextContent(type="text", text=json.dumps({"scenes_processed": len(result)}))]

    if name == "assemble":
        _ensure_ffmpeg()
        output_path = assemble_video(
            arguments["storyboard_path"],
            arguments["title"],
        )
        return [TextContent(type="text", text=json.dumps({"output": output_path}))]

    if name == "image_gen_chatgpt":
        result = image_gen_chatgpt(
            arguments["storyboard_path"],
            arguments["title"],
        )
        return [TextContent(type="text", text=json.dumps({"scenes_processed": len(result)}))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
