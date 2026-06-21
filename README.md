# mcp-server-documentary-generation

An agentic MCP server for autonomous long-form documentary generation. Orchestrated by Claude Code, powered by local and API-based tools.

## Overview

Produces 15–25 minute YouTube documentaries with minimal human intervention. Initial focus: Greek-language Byzantine history. Designed to scale across historical niches.

## Pipeline

```
Topic → Research → Script → Storyboard → Image Prompts
     → Image Generation → TTS → Video Assembly → Metadata → Upload
```

## Stack

| Stage | Tool |
|---|---|
| Orchestration | Claude Code (MCP tools) |
| Research | Wikipedia RAG (ChromaDB) |
| Script & Planning | Claude (inline, no extra API cost) |
| Image Generation | Replicate API (FLUX Dev + Medieval Manuscript LoRA) |
| TTS | Meta MMS `facebook/mms-tts-ell` (local) |
| Subtitle Sync | WhisperX forced alignment (local) |
| Video Assembly | FFmpeg (Ken Burns, crossfades, burn transitions) |
| Music | Musopen (public domain) |
| Upload | YouTube Data API v3 |

## Visual Style

Byzantine chronicle aesthetic — pencil sketches, charcoal, illuminated manuscript. Film grain, vignette, dust particles, slow pans and zooms on static images.

## Target Output

```
output/
├── video.mp4
├── subtitles.srt
├── thumbnail.png
├── title.txt
├── description.txt
└── chapters.txt
```

## Status

Early development.
