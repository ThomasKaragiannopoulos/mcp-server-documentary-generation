"""
TTS tool using Chatterbox Multilingual TTS for Greek narration.
Usage: py tts.py "Το κείμενο εδώ" output.wav
       py tts.py --file script.txt output.wav
"""

import argparse
import torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

LANGUAGE = "el"

def load_model():
    print("Loading Chatterbox Multilingual model...")
    model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    return model

def synthesize(text: str, model: ChatterboxMultilingualTTS) -> tuple:
    print(f"Synthesizing {len(text)} characters...")
    wav = model.generate(text, language_id=LANGUAGE)
    return wav, model.sr

def main():
    parser = argparse.ArgumentParser(description="Greek TTS via Chatterbox Multilingual")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("text", nargs="?", help="Text to synthesize")
    group.add_argument("--file", help="Path to text file")
    parser.add_argument("output", help="Output WAV file path")
    args = parser.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read().strip()
    else:
        text = args.text

    model = load_model()
    wav, sr = synthesize(text, model)

    ta.save(args.output, wav, sr)
    duration = wav.shape[-1] / sr
    print(f"Saved {args.output} ({duration:.1f}s, {sr}Hz)")

if __name__ == "__main__":
    main()
