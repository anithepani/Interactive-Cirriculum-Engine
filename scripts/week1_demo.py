"""Week 1 demo: transcribe a video/audio file and ask the LLM for its main topic.

Usage:
    python scripts/week1_demo.py --video path/to/sample.wav
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "libs", "ai", "llm", "src")
    ),
)
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "libs", "ai", "transcript", "src")
    ),
)

import argparse
import json

from ice_llm.client import LLMClient
from ice_transcript.transcribe import transcribe
from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcribe a video/audio file and summarize its main topic."
    )
    parser.add_argument(
        "--video",
        required=True,
        help="Path to the audio/video file to transcribe (e.g. sample.wav).",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.video):
        print(f"Error: file not found: {args.video}", file=sys.stderr)
        return 1

    print(f"Transcribing: {args.video}")
    result = transcribe(args.video)

    segments = result["segments"]
    print(f"\nDetected language: {result['language']} (confidence={result['confidence']:.3f})")
    print(f"Total segments: {len(segments)}")
    print("\n--- First 19 segments ---")
    print(json.dumps(segments[:19], indent=2, ensure_ascii=False))

    context = " ".join(seg["text"] for seg in segments[:3]).strip()
    prompt = (
        "Here are the first few sentences of a technical tutorial transcript: "
        f"{context}. What is the single main topic of this tutorial? "
        "Keep your answer under 20 words."
    )

    print("\n--- Asking the LLM for the main topic ---")
    client = LLMClient()
    answer = client.complete(prompt)
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
