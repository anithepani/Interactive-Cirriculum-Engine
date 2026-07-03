"""Demo: segment a transcript JSON file into topics and print the results.

Usage:
    python scripts/segment_demo.py --transcript data/fixtures/sample_transcript.json
    python scripts/segment_demo.py   # uses the default fixture
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
        os.path.join(
            os.path.dirname(__file__), "..", "libs", "ai", "segmentation", "src"
        )
    ),
)

import argparse
import json

from ice_segmentation.segmenter import segment_transcript
from dotenv import load_dotenv

load_dotenv()

DEFAULT_FIXTURE = os.path.join(
    os.path.dirname(__file__), "..", "data", "fixtures", "sample_transcript.json"
)


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Segment a transcript into topics and print the results."
    )
    parser.add_argument(
        "--transcript",
        default=DEFAULT_FIXTURE,
        help="Path to a transcript JSON file (canonical schema).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output only the segments as valid JSON (no headers/progress).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write JSON output to this file (UTF-8). Implies --json. "
             "Use this instead of shell '>' to avoid PowerShell UTF-16 encoding issues.",
    )
    args = parser.parse_args()

    json_mode = args.json or args.output is not None

    transcript_path = os.path.abspath(args.transcript)
    if not os.path.isfile(transcript_path):
        print(f"Error: transcript file not found: {transcript_path}", file=sys.stderr)
        return 1

    with open(transcript_path, encoding="utf-8-sig") as f:
        transcript = json.load(f)

    segments = segment_transcript(transcript)

    if json_mode:
        out = json.dumps(segments, indent=2, ensure_ascii=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"Wrote {len(segments)} segments to {args.output}", file=sys.stderr)
        else:
            print(out)
        return 0

    n_input = len(transcript.get("segments", []))
    print(f"Loaded transcript: {transcript_path}")
    print(f"  Language: {transcript.get('language', '?')}")
    print(f"  Input segments: {n_input}")
    print()

    print(f"Detected {len(segments)} topic segment(s):\n")
    print("=" * 70)
    for seg in segments:
        print(f"  Segment {seg['id']}")
        print(f"    Time:          {_fmt_time(seg['start'])} - {_fmt_time(seg['end'])}")
        print(f"    Title:         {seg['title']}")
        print(f"    Summary:       {seg['summary']}")
        print(f"    Topic label:   {seg.get('topic_label', 'n/a')}")
        print(f"    Concepts:      {', '.join(seg['concepts']) if seg['concepts'] else '(none)'}")
        print(f"    Structuredness: {seg['structuredness']:.2f}")
        print("-" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
