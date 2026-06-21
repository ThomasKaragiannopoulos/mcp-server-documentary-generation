"""
Storyboard tool — parses a script into scenes and initialises the project folder structure.
Image prompts are passed in by the orchestrator (Claude) — this tool only handles
parsing and persistence.

Usage (standalone):
    py tools/storyboard.py script/my_script.txt --title "Άλωση 1453"

Output structure:
    generated/<title>/
        scenes.json
        scene_01/
            script.txt
            prompt.txt
        scene_02/
            ...
"""

import re
import json
import os
import argparse
from tools.project import init_project

STYLE_SUFFIX = (
    "Byzantine manuscript illustration, pencil sketch on aged parchment, "
    "charcoal drawing, film grain, vignette, 16:9, no text, no modern elements"
)

SECTION_PATTERN = re.compile(r"\[([^\]]+?)\s*—\s*[\d:–]+\]")


def parse_script(script_path: str) -> list[dict]:
    with open(script_path, encoding="utf-8") as f:
        content = f.read()

    # Split on section markers
    parts = SECTION_PATTERN.split(content)

    scenes = []
    # parts = [pre_text, section_name, section_text, section_name, section_text, ...]
    i = 1
    scene_id = 1
    while i < len(parts) - 1:
        section_name = parts[i].strip()
        section_text = parts[i + 1].strip()

        # Remove markdown separators and blank lines
        narration = re.sub(r"^---+$", "", section_text, flags=re.MULTILINE).strip()
        narration = re.sub(r"\n{3,}", "\n\n", narration).strip()

        if narration:
            scenes.append({
                "id": scene_id,
                "section": section_name,
                "narration": narration,
                "image_prompt": "",  # filled by orchestrator
                "sound_effects": []
            })
            scene_id += 1

        i += 2

    return scenes


def save_storyboard(scenes: list[dict], output_path: str) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scenes, f, ensure_ascii=False, indent=2)
    return output_path


def load_storyboard(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_storyboard(script_path: str, title: str, output_path: str = None) -> dict:
    """Parse script, initialise project folder structure, write scene files."""
    scenes = parse_script(script_path)
    project_dir = init_project(title, scenes)
    index_path = output_path or os.path.join(project_dir, "scenes.json")
    return {
        "project_dir": project_dir,
        "index_path": index_path,
        "scene_count": len(scenes),
        "scenes": scenes
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Parse script into storyboard scenes")
    parser.add_argument("script", help="Path to script .txt file")
    parser.add_argument("--title", required=True, help="Documentary title (used as folder name)")
    args = parser.parse_args()

    result = build_storyboard(args.script, args.title)
    print(f"Parsed {result['scene_count']} scenes → {result['project_dir']}")
    for scene in result["scenes"]:
        print(f"\n[{scene['id']}] {scene['section']}")
        print(scene["narration"][:120])
