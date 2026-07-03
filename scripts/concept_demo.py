"""Demo: build a concept graph from M4 segments and print as JSON.

Usage:
    python scripts/concept_demo.py --segments data/fixtures/sample_segments.json
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
            os.path.dirname(__file__), "..", "libs", "ai", "concept_graph", "src"
        )
    ),
)

import argparse
import json

from dotenv import load_dotenv

load_dotenv()

from ice_concept_graph.extractor import extract_concepts_and_edges

DEFAULT_FIXTURE = os.path.join(
    os.path.dirname(__file__), "..", "data", "fixtures", "sample_segments.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a concept graph from M4 segments."
    )
    parser.add_argument(
        "--segments",
        default=DEFAULT_FIXTURE,
        help="Path to a JSON file containing a list of M4 segment dicts.",
    )
    args = parser.parse_args()

    segments_path = os.path.abspath(args.segments)
    if not os.path.isfile(segments_path):
        print(f"Error: segments file not found: {segments_path}", file=sys.stderr)
        return 1

    with open(segments_path, encoding="utf-8-sig") as f:
        segments = json.load(f)

    print(f"Loaded {len(segments)} segment(s) from: {segments_path}")
    print()

    graph = extract_concepts_and_edges(segments)

    print(f"Concepts ({len(graph['concepts'])}):")
    print(json.dumps(graph["concepts"], indent=2, ensure_ascii=False))
    print()
    print(f"Edges ({len(graph['edges'])}):")
    print(json.dumps(graph["edges"], indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
