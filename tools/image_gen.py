"""
Image generation tool — SD 1.5 CPU inference.
Generates one PNG per scene from its prompt.txt.
Skips scenes that already have image.png (checkpointing).

Usage:
    py -m tools.image_gen generated/<title>/scenes.json --title "Title"
    py -m tools.image_gen generated/<title>/scenes.json --title "Title" --steps 20
"""

import os
import sys
import json
import argparse
import torch
from diffusers import StableDiffusionPipeline
from tools.project import scene_paths

sys.stdout.reconfigure(encoding="utf-8")

MODEL_ID = "runwayml/stable-diffusion-v1-5"
DEFAULT_STEPS = 20
WIDTH = 768
HEIGHT = 432  # 16:9 at 768 width

NEGATIVE_PROMPT = (
    "photorealistic, photograph, modern, text, watermark, signature, "
    "blurry, low quality, deformed, ugly, nsfw"
)


def load_pipeline() -> StableDiffusionPipeline:
    print(f"Loading {MODEL_ID} (CPU)...")
    pipe = StableDiffusionPipeline.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float32,
        safety_checker=None,
    )
    pipe = pipe.to("cpu")
    pipe.enable_attention_slicing()  # reduces RAM usage
    return pipe


def generate_image(prompt: str, pipe: StableDiffusionPipeline, steps: int = DEFAULT_STEPS) -> object:
    result = pipe(
        prompt=prompt,
        negative_prompt=NEGATIVE_PROMPT,
        num_inference_steps=steps,
        width=WIDTH,
        height=HEIGHT,
    )
    return result.images[0]


def process_batch(storyboard_path: str, title: str, steps: int = DEFAULT_STEPS):
    with open(storyboard_path, encoding="utf-8") as f:
        scenes = json.load(f)

    pending = []
    for scene in scenes:
        paths = scene_paths(title, scene["id"])
        if os.path.exists(paths["image"]):
            print(f"[{scene['id']}] Skipping — image already exists")
            scene["image_path"] = paths["image"]
        elif not scene.get("image_prompt"):
            print(f"[{scene['id']}] Skipping — no image_prompt")
        else:
            pending.append((scene, paths))

    if not pending:
        print("All scenes already generated.")
        return scenes

    pipe = load_pipeline()

    for scene, paths in pending:
        print(f"\n[{scene['id']}] {scene['section']}")
        print(f"    Prompt: {scene['image_prompt'][:80]}...")
        image = generate_image(scene["image_prompt"], pipe, steps)
        os.makedirs(paths["dir"], exist_ok=True)
        image.save(paths["image"])
        scene["image_path"] = paths["image"]
        print(f"    Saved {paths['image']}")

    with open(storyboard_path, "w", encoding="utf-8") as f:
        json.dump(scenes, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(pending)} images generated.")
    return scenes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch image generation for all scenes")
    parser.add_argument("storyboard", help="Path to scenes.json")
    parser.add_argument("--title", required=True, help="Documentary title")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS, help="Diffusion steps (default 20)")
    args = parser.parse_args()

    process_batch(args.storyboard, args.title, args.steps)
