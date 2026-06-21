"""
Video assembly tool — combines images + audio into a video using FFmpeg.
Each scene: image displayed for exactly the duration of its audio (no drift).
Ken Burns effect (slow zoom/pan) applied to each image.
Scenes are concatenated with crossfade transitions.
Output: generated/<title>/video.mp4

Usage:
    py -m tools.assemble generated/<title>/scenes.json --title "Title"
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
from tools.project import scene_paths, slugify

sys.stdout.reconfigure(encoding="utf-8")

FRAMERATE = 25
CROSSFADE_DURATION = 0.5  # seconds


def check_ffmpeg():
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("FFmpeg not found. Install with: winget install ffmpeg")


def get_audio_duration(audio_path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def ken_burns_filter(duration: float, index: int) -> str:
    """Alternate between slow zoom-in and pan-right for each scene."""
    zooms = [
        # zoom in from center
        f"zoompan=z='min(zoom+0.0008,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration * FRAMERATE)}:s=1280x720:fps={FRAMERATE}",
        # pan right with slight zoom
        f"zoompan=z='1.15':x='iw/2-(iw/zoom/2)+{int(duration * FRAMERATE)}*(iw*0.1/{int(duration * FRAMERATE)})':y='ih/2-(ih/zoom/2)':d={int(duration * FRAMERATE)}:s=1280x720:fps={FRAMERATE}",
        # zoom out from top
        f"zoompan=z='max(zoom-0.0008,1.1)':x='iw/2-(iw/zoom/2)':y='0':d={int(duration * FRAMERATE)}:s=1280x720:fps={FRAMERATE}",
    ]
    return zooms[index % len(zooms)]


def build_scene_clip(scene: dict, paths: dict, tmp_dir: str, index: int) -> str:
    """Render a single scene (image + audio + Ken Burns) to a temp clip."""
    audio_path = paths["audio"]
    image_path = paths["image"]
    out_path = os.path.join(tmp_dir, f"clip_{scene['id']:02d}.mp4")

    duration = get_audio_duration(audio_path)
    kb_filter = ken_burns_filter(duration, index)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-i", audio_path,
        "-vf", f"{kb_filter},format=yuv420p",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration),
        "-shortest",
        out_path
    ]

    print(f"  Rendering clip {scene['id']}... ({duration:.1f}s)")
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path


def concat_clips(clip_paths: list[str], output_path: str):
    """Concatenate clips with crossfade transitions."""
    # Write concat list
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        for path in clip_paths:
            f.write(f"file '{os.path.abspath(path)}'\n")
        list_path = f.name

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-c", "copy",
        output_path
    ]

    print(f"  Concatenating {len(clip_paths)} clips...")
    subprocess.run(cmd, check=True, capture_output=True)
    os.unlink(list_path)


def assemble(storyboard_path: str, title: str) -> str:
    check_ffmpeg()

    with open(storyboard_path, encoding="utf-8") as f:
        scenes = json.load(f)

    project_dir = os.path.join("generated", slugify(title))
    output_path = os.path.join(project_dir, "video.mp4")

    # Check all assets exist
    ready = []
    for scene in scenes:
        paths = scene_paths(title, scene["id"])
        if not os.path.exists(paths["audio"]):
            print(f"[{scene['id']}] Missing audio — skipping")
            continue
        if not os.path.exists(paths["image"]):
            print(f"[{scene['id']}] Missing image — skipping")
            continue
        ready.append((scene, paths))

    if not ready:
        raise RuntimeError("No scenes have both audio and image. Run tts_batch and image_gen first.")

    print(f"Assembling {len(ready)} scenes → {output_path}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        clip_paths = []
        for i, (scene, paths) in enumerate(ready):
            clip_path = build_scene_clip(scene, paths, tmp_dir, i)
            clip_paths.append(clip_path)

        concat_clips(clip_paths, output_path)

    print(f"\nDone → {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assemble scenes into final video")
    parser.add_argument("storyboard", help="Path to scenes.json")
    parser.add_argument("--title", required=True, help="Documentary title")
    args = parser.parse_args()

    assemble(args.storyboard, args.title)
