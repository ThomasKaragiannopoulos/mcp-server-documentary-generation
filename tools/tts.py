"""
TTS tool using Chatterbox Multilingual TTS for Greek narration.
Usage: py tts.py "Το κείμενο εδώ" output.wav
       py tts.py --file script.txt output.wav
       py tts.py "..." output.wav --speed 0.8
"""

import argparse
import torch
import torchaudio as ta
import torchaudio.functional as F
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

LANGUAGE = "el"
CFG_WEIGHT = 0.3  # lower = slower, more deliberate pacing

def load_model():
    print("Loading Chatterbox Multilingual model...")
    model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    return model

def synthesize(text: str, model: ChatterboxMultilingualTTS) -> tuple:
    print(f"Synthesizing {len(text)} characters...")
    wav = model.generate(text, language_id=LANGUAGE, cfg_weight=CFG_WEIGHT)
    return wav, model.sr

def stretch_audio(wav: torch.Tensor, sr: int, speed: float) -> torch.Tensor:
    """Slow down or speed up audio while preserving pitch."""
    if speed == 1.0:
        return wav
    effects = [["tempo", str(speed)]]
    wav_stretched, _ = ta.sox_effects.apply_effects_tensor(wav, sr, effects)
    return wav_stretched

def main():
    parser = argparse.ArgumentParser(description="Greek TTS via Chatterbox Multilingual")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("text", nargs="?", help="Text to synthesize")
    group.add_argument("--file", help="Path to text file")
    parser.add_argument("output", help="Output WAV file path")
    parser.add_argument("--speed", type=float, default=0.85, help="Playback speed (default 0.85, slower than original)")
    args = parser.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read().strip()
    else:
        text = args.text

    model = load_model()
    wav, sr = synthesize(text, model)

    wav = stretch_audio(wav, sr, args.speed)

    ta.save(args.output, wav, sr)
    duration = wav.shape[-1] / sr
    print(f"Saved {args.output} ({duration:.1f}s, {sr}Hz, speed={args.speed})")

if __name__ == "__main__":
    main()
