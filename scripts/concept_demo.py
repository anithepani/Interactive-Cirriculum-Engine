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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output only the concept graph as valid JSON (no headers).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write JSON to this file (UTF-8). Bypasses shell encoding issues.",
    )
    args = parser.parse_args()

    segments_path = os.path.abspath(args.segments)
    if not os.path.isfile(segments_path):
        print(f"Error: segments file not found: {segments_path}", file=sys.stderr)
        return 1

    with open(segments_path, encoding="utf-8-sig") as f:
        segments = json.load(f)

    graph = extract_concepts_and_edges(segments)

    json_mode = args.json or args.output is not None
    if json_mode:
        out = json.dumps(graph, indent=2, ensure_ascii=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"Wrote {len(graph['concepts'])} concepts + {len(graph['edges'])} edges to {args.output}", file=sys.stderr)
        else:
            print(out)
        return 0

    print(f"Loaded {len(segments)} segment(s) from: {segments_path}")
    print()

    print(f"Concepts ({len(graph['concepts'])}):")
    print(json.dumps(graph["concepts"], indent=2, ensure_ascii=False))
    print()
    print(f"Edges ({len(graph['edges'])}):")
    print(json.dumps(graph["edges"], indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
