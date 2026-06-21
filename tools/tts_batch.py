"""
TTS batch tool — generates one WAV per scene from a storyboard JSON.
Saves audio to generated/<title>/scene_XX/audio.wav.
Skips scenes that already have a WAV (checkpointing).

Usage:
    py tools/tts_batch.py generated/Title/scenes.json --title "Title"
"""

import os
import sys
import json
import argparse
import torch
import torchaudio as ta
import librosa
from tools.project import scene_paths

sys.stdout.reconfigure(encoding="utf-8")

LANGUAGE = "el"
CFG_WEIGHT = 0.3
SPEED = 0.85


def load_model():
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    print("Loading Chatterbox Multilingual model...")
    return ChatterboxMultilingualTTS.from_pretrained(device="cpu")


def synthesize(text: str, model) -> tuple:
    wav = model.generate(text, language_id=LANGUAGE, cfg_weight=CFG_WEIGHT)
    return wav, model.sr


def stretch_audio(wav: torch.Tensor, sr: int, speed: float) -> torch.Tensor:
    if speed == 1.0:
        return wav
    audio_np = wav.squeeze().numpy()
    stretched = librosa.effects.time_stretch(audio_np, rate=speed)
    return torch.tensor(stretched).unsqueeze(0)


def process_batch(storyboard_path: str, title: str, speed: float = SPEED) -> list[dict]:
    with open(storyboard_path, encoding="utf-8") as f:
        scenes = json.load(f)

    pending = []
    for scene in scenes:
        paths = scene_paths(title, scene["id"])
        out_path = paths["audio"]
        if os.path.exists(out_path):
            print(f"[{scene['id']}] Skipping — audio already exists")
            scene["audio_path"] = out_path
        else:
            pending.append((scene, out_path))

    if not pending:
        print("All scenes already generated.")
        return scenes

    model = load_model()

    for scene, out_path in pending:
        print(f"\n[{scene['id']}] {scene['section']} — {len(scene['narration'])} chars")
        wav, sr = synthesize(scene["narration"], model)
        wav = stretch_audio(wav, sr, speed)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        ta.save(out_path, wav, sr)
        duration = wav.shape[-1] / sr
        scene["audio_path"] = out_path
        scene["duration"] = round(duration, 2)
        print(f"    Saved {out_path} ({duration:.1f}s)")

    with open(storyboard_path, "w", encoding="utf-8") as f:
        json.dump(scenes, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Storyboard updated with audio paths and durations.")
    return scenes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch TTS for all scenes in storyboard")
    parser.add_argument("storyboard", help="Path to scenes.json")
    parser.add_argument("--title", required=True, help="Documentary title (matches project folder)")
    parser.add_argument("--speed", type=float, default=SPEED, help="Playback speed")
    args = parser.parse_args()

    process_batch(args.storyboard, args.title, args.speed)
