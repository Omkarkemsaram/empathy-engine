#!/usr/bin/env python3
"""
Empathy Engine CLI — Run emotion-modulated TTS from the command line.

Usage:
    python cli.py "Your text here"
    python cli.py "Your text here" --style dramatic
    python cli.py "Your text here" --output my_output.wav --style professional
    python cli.py --interactive
"""

import argparse
import os
import sys
import json
import uuid

from emotion_engine import EmotionEngine
from voice_synthesizer import VoiceSynthesizer

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)


def run_pipeline(text: str, style: str, output_path: str):
    engine = EmotionEngine()
    synth = VoiceSynthesizer(audio_dir=AUDIO_DIR)

    print("\n🧠 EMOTION ANALYSIS")
    print("─" * 50)
    emotion = engine.analyze(text)
    print(f"  Primary:   {emotion['emoji']} {emotion['primary_emotion'].upper()}")
    print(f"  Intensity: {emotion['intensity_label']} ({emotion['intensity']:.0%})")
    print(f"  Valence:   {'+' if emotion['valence'] >= 0 else ''}{emotion['valence']:.1f}")
    if emotion['runner_up']:
        ru = emotion['runner_up']
        print(f"  Runner-up: {ru['emotion']} ({ru['score']:.2f})")

    print("\n🎚  VOCAL PARAMETERS")
    print("─" * 50)
    params = engine.get_vocal_params(emotion, style)
    print(f"  Speech Rate:  {params['rate']:.2f}x  ({params['rate_words_per_minute']} wpm)")
    print(f"  Pitch:        {params['pitch']:.2f}x  ({params['pitch_semitones']:+.1f} semitones)")
    print(f"  Volume:       {params['volume']:.2f}x")
    print(f"  Pause Factor: {params['pause_factor']:.2f}x")
    print(f"  Emphasis:     {params['emphasis']}")

    print("\n📝 SSML MARKUP")
    print("─" * 50)
    ssml = params['ssml_template'].replace('{TEXT}', text)
    print(ssml)

    print("\n🔊 SYNTHESIZING AUDIO")
    print("─" * 50)
    success, notes = synth.synthesize(text, params, output_path)
    print(f"  {notes}")

    if success and os.path.exists(output_path):
        size = os.path.getsize(output_path)
        print(f"\n✅ Audio saved: {output_path} ({size:,} bytes)")
        print(f"   Open with any media player.")
    else:
        print(f"\n❌ Synthesis failed.")
        sys.exit(1)

    return emotion, params


def interactive_mode():
    engine = EmotionEngine()
    synth = VoiceSynthesizer(audio_dir=AUDIO_DIR)

    print("\n🎙  THE EMPATHY ENGINE — Interactive Mode")
    print("=" * 50)
    print("Type text and press Enter to synthesize. Type 'quit' to exit.\n")

    while True:
        try:
            text = input("📝 Enter text: ").strip()
            if text.lower() in ("quit", "exit", "q"):
                break
            if not text:
                continue

            style = input("🎨 Voice style [auto/professional/warm/dramatic] (Enter = auto): ").strip() or "auto"
            filename = f"cli_{uuid.uuid4().hex[:6]}.wav"
            output_path = os.path.join(AUDIO_DIR, filename)

            run_pipeline(text, style, output_path)
            print()

        except KeyboardInterrupt:
            print("\n\nBye!")
            break


def main():
    parser = argparse.ArgumentParser(
        description="The Empathy Engine — Emotionally Intelligent TTS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py "I'm absolutely thrilled about this!"
  python cli.py "This is frustrating and broken again" --style dramatic
  python cli.py --interactive
        """
    )
    parser.add_argument("text", nargs="?", help="Text to synthesize")
    parser.add_argument("--style", default="auto",
                        choices=["auto", "professional", "warm", "dramatic"],
                        help="Voice modulation style overlay")
    parser.add_argument("--output", default=None,
                        help="Output WAV file path (default: auto-named in static/audio/)")
    parser.add_argument("--interactive", action="store_true",
                        help="Run in interactive mode")

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
        return

    if not args.text:
        parser.print_help()
        sys.exit(1)

    output = args.output or os.path.join(AUDIO_DIR, f"cli_{uuid.uuid4().hex[:8]}.wav")
    run_pipeline(args.text, args.style, output)


if __name__ == "__main__":
    main()
