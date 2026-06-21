"""
Project structure helper.
All generated content lives under generated/<title>/scene_XX/.
"""

import re
import os
import json


def slugify(title: str) -> str:
    return re.sub(r"[^\w]", "_", title.strip())[:60].strip("_")


def scene_dir(title: str, scene_id: int) -> str:
    return os.path.join("generated", slugify(title), f"scene_{scene_id:02d}")


def scene_paths(title: str, scene_id: int) -> dict:
    d = scene_dir(title, scene_id)
    return {
        "dir": d,
        "script": os.path.join(d, "script.txt"),
        "prompt": os.path.join(d, "prompt.txt"),
        "audio": os.path.join(d, "audio.wav"),
        "image": os.path.join(d, "image.png"),
    }


def init_scene(title: str, scene: dict) -> dict:
    """Create scene folder and write script.txt and prompt.txt."""
    paths = scene_paths(title, scene["id"])
    os.makedirs(paths["dir"], exist_ok=True)

    with open(paths["script"], "w", encoding="utf-8") as f:
        f.write(scene["narration"])

    if scene.get("image_prompt"):
        with open(paths["prompt"], "w", encoding="utf-8") as f:
            f.write(scene["image_prompt"])

    return paths


def init_project(title: str, scenes: list[dict]) -> str:
    """Create full project folder structure and write all scene files."""
    project_dir = os.path.join("generated", slugify(title))
    os.makedirs(project_dir, exist_ok=True)

    for scene in scenes:
        init_scene(title, scene)

    index_path = os.path.join(project_dir, "scenes.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(scenes, f, ensure_ascii=False, indent=2)

    return project_dir
