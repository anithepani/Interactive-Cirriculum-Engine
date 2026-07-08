"""Demo: generate exercises (MCQ/coding/debug/conceptual) from checkpoints.

Usage:
    python scripts/exercise_demo.py \\
        --checkpoints data/fixtures/sample_checkpoints.json \\
        --segments data/fixtures/sample_segments.json \\
        --concepts data/fixtures/sample_concept_graph.json

The --concepts arg accepts either a bare list of concept dicts OR a concept
graph dict with a "concepts" key (auto-detected).
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "libs", "ai", "exercise_gen", "src")
    ),
)
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "libs", "ai", "llm", "src")),
)
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "libs", "contracts", "src")
    ),
)
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "libs", "shared", "src"))
)

import argparse
import json

from dotenv import load_dotenv

load_dotenv()

from ice_exercise_gen import generate_exercises

DEFAULT_CHECKPOINTS = os.path.join(
    os.path.dirname(__file__), "..", "data", "fixtures", "sample_checkpoints.json"
)
DEFAULT_SEGMENTS = os.path.join(
    os.path.dirname(__file__), "..", "data", "fixtures", "sample_segments.json"
)
DEFAULT_CONCEPTS = os.path.join(
    os.path.dirname(__file__), "..", "data", "fixtures", "sample_concept_graph.json"
)


def _load_json(path: str):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def _print_exercise(ex: dict, index: int) -> None:
    print("=" * 70)
    print(f"  Exercise {index}: {ex['id']}  [{ex['type']}]")
    print("=" * 70)
    print(f"  Prompt:        {ex['prompt']}")
    print(f"  Concept:       {ex['concept_id']}")
    print(f"  Difficulty:    {ex['difficulty']}/5")
    print(f"  Confidence:    {ex['confidence']}")
    print(f"  Validation:    {'passed' if ex['validation_passed'] else 'pending (M8)'}")
    if ex.get("context"):
        print(f"  Context:       {ex['context'][:120]}...")

    etype = ex["type"]
    if etype == "mcq":
        mcq = ex["mcq"]
        print(f"  Options:")
        for i, opt in enumerate(mcq["options"]):
            marker = " *" if i == mcq["answer_idx"] else "  "
            print(f"    {marker} [{i}] {opt}")
        if mcq.get("distractor_tags"):
            print(f"  Distractor tags: {mcq['distractor_tags']}")
    elif etype == "coding":
        cod = ex["coding"]
        print(f"  Starter code:")
        for line in cod["starter"].splitlines():
            print(f"    | {line}")
        print(f"  Visible tests: {cod.get('tests_visible', [])}")
        print(f"  Hidden tests:  {len(cod.get('tests_hidden', []))} test(s)")
        print(f"  Reference solution:")
        for line in cod["reference_solution"].splitlines():
            print(f"    | {line}")
        if cod.get("constraints"):
            print(f"  Constraints: {cod['constraints']}")
    elif etype == "debug":
        dbg = ex["debug"]
        print(f"  Buggy code:")
        for line in dbg["buggy_code"].splitlines():
            print(f"    | {line}")
        print(f"  Tests: {len(dbg.get('tests', []))} test(s)")
        print(f"  Bug explanation: {dbg['bug_explanation']}")
    elif etype == "conceptual":
        con = ex["conceptual"]
        print(f"  Reference answer: {con['reference_answer']}")
        print(f"  Rubric: {con['rubric']}")
        print(f"  Min similarity: {con['min_similarity']}")

    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate exercises from checkpoints, segments, and concepts."
    )
    parser.add_argument(
        "--checkpoints", default=DEFAULT_CHECKPOINTS,
        help="Path to M6 checkpoints JSON file.",
    )
    parser.add_argument(
        "--segments", default=DEFAULT_SEGMENTS,
        help="Path to M4 segments JSON file.",
    )
    parser.add_argument(
        "--concepts", default=DEFAULT_CONCEPTS,
        help="Path to concepts JSON file (list or concept-graph dict).",
    )
    parser.add_argument(
        "--instructor-code", default=None,
        help="Optional path to a JSON file/list of instructor code snippets.",
    )
    args = parser.parse_args()

    for label, path in [
        ("checkpoints", args.checkpoints),
        ("segments", args.segments),
        ("concepts", args.concepts),
    ]:
        if not os.path.isfile(path):
            print(f"Error: {label} file not found: {path}", file=sys.stderr)
            return 1

    checkpoints = _load_json(args.checkpoints)
    segments = _load_json(args.segments)
    concepts = _load_json(args.concepts)

    n_concepts = len(concepts) if isinstance(concepts, list) else len(concepts.get("concepts", []))
    print(f"Loaded {len(checkpoints)} checkpoints, {len(segments)} segments, {n_concepts} concepts")
    print(f"Exercise types: {[cp['exercise_type'] for cp in checkpoints]}")
    print()

    instructor_code = None
    if args.instructor_code:
        instructor_code = _load_json(args.instructor_code)

    exercises = generate_exercises(checkpoints, segments, concepts, instructor_code)

    if not exercises:
        print("No exercises were generated. Check the logs above for errors.")
        return 1

    print(f"Generated {len(exercises)}/{len(checkpoints)} exercises:\n")
    for i, ex in enumerate(exercises, 1):
        _print_exercise(ex, i)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
