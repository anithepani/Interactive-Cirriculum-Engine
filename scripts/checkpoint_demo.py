"""Demo: place checkpoints at segment boundaries and print the results.

Usage:
    python scripts/checkpoint_demo.py \
        --segments data/fixtures/sample_segments.json \
        --graph data/fixtures/sample_concept_graph.json
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "libs", "ai", "checkpoints", "src"
        )
    ),
)

import argparse
import json

from dotenv import load_dotenv

load_dotenv()

from ice_checkpoints.placer import place_checkpoints, _AVOID_FINAL_SEC

DEFAULT_SEGMENTS = os.path.join(
    os.path.dirname(__file__), "..", "data", "fixtures", "sample_segments.json"
)
DEFAULT_GRAPH = os.path.join(
    os.path.dirname(__file__), "..", "data", "fixtures", "sample_concept_graph.json"
)


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Place checkpoints at segment boundaries."
    )
    parser.add_argument(
        "--segments", default=DEFAULT_SEGMENTS,
        help="Path to M4 segments JSON file.",
    )
    parser.add_argument(
        "--graph", default=DEFAULT_GRAPH,
        help="Path to M5 concept graph JSON file.",
    )
    parser.add_argument(
        "--min-gap", type=float, default=90.0,
        help="Minimum seconds between checkpoints (default: 90s for production).",
    )
    parser.add_argument(
        "--min-start-sec", type=float, default=0.0,
        help="Minimum seconds before the first checkpoint (default: 0s for "
        "demos; production worker uses 60s).",
    )
    parser.add_argument(
        "--avoid-final-sec", type=float, default=30.0,
        help="Avoid placing checkpoints in the final N seconds, except for "
        "the final segment (default: 30s; matches production).",
    )
    args = parser.parse_args()

    if args.min_gap == 15.0:
        print(
            "WARNING: Demo mode active (15s gap). Production uses 90s.",
            file=sys.stderr,
        )

    segments_path = os.path.abspath(args.segments)
    graph_path = os.path.abspath(args.graph)

    for label, path in [("segments", segments_path), ("graph", graph_path)]:
        if not os.path.isfile(path):
            print(f"Error: {label} file not found: {path}", file=sys.stderr)
            return 1

    with open(segments_path, encoding="utf-8-sig") as f:
        segments = json.load(f)
    with open(graph_path, encoding="utf-8-sig") as f:
        graph = json.load(f)

    print(f"Loaded {len(segments)} segments from: {segments_path}")
    print(f"Loaded {len(graph.get('concepts', []))} concepts from: {graph_path}")
    print()

    checkpoints = place_checkpoints(
        segments,
        graph,
        min_gap_sec=args.min_gap,
        min_start_sec=args.min_start_sec,
        avoid_final_sec=args.avoid_final_sec,
    )

    if not checkpoints:
        print("No checkpoints placed (all segments filtered by density/final-30s rules).")
        return 0

    video_dur = max(seg["end"] for seg in segments)
    print(f"Video duration: {_fmt_time(video_dur)} ({video_dur:.1f}s)")
    print(f"Avoid zone: final {_AVOID_FINAL_SEC}s (after {_fmt_time(video_dur - _AVOID_FINAL_SEC)})")
    print(f"Min gap: {args.min_gap}s")
    print(f"Min start: {args.min_start_sec}s")
    print(f"Avoid final: {args.avoid_final_sec}s")
    print(f"Placed {len(checkpoints)} checkpoint(s):\n")
    print("=" * 70)
    for cp in checkpoints:
        print(f"  {cp['id']}")
        print(f"    Timestamp:     {_fmt_time(cp['ts'])} ({cp['ts']:.1f}s)")
        print(f"    Segment:       {cp['segment_id']}")
        print(f"    Concept:       {cp['concept_id']}")
        print(f"    Exercise type: {cp['exercise_type']}")
        print(f"    Difficulty:    {cp['difficulty']}/5")
        print("-" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
