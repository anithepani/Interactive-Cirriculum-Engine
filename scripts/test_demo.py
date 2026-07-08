"""Demo: generate + validate tests for a coding exercise (M8).

Usage:
    uv run python scripts/test_demo.py
    uv run python scripts/test_demo.py --exercise data/fixtures/sample_coding_exercise.json

Loads a coding exercise (with a reference_solution), calls ``generate_tests()``,
and prints the validated visible + hidden tests plus the mutation score. Exits 0
when ``validation_passed`` is True, 1 otherwise.

Requires GROQ_API_KEY in the environment (.env).
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv
from ice_test_gen import generate_tests

load_dotenv()

DEFAULT_EXERCISE = os.path.join(
    os.path.dirname(__file__), "..", "data", "fixtures", "sample_coding_exercise.json"
)


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate + validate tests for a coding exercise (M8)."
    )
    parser.add_argument(
        "--exercise",
        default=DEFAULT_EXERCISE,
        help="Path to a coding exercise JSON (CodingExercise envelope).",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.exercise):
        print(f"Error: exercise file not found: {args.exercise}", file=sys.stderr)
        return 1

    exercise = _load_json(args.exercise)
    coding = exercise.get("coding", {})

    print("=" * 70)
    print("  M8 Test Generation & Validation")
    print("=" * 70)
    print(f"  Exercise:      {exercise.get('id', '?')}  [{exercise.get('type', '?')}]")
    print(f"  Prompt:        {exercise.get('prompt', '')}")
    print(f"  Difficulty:    {exercise.get('difficulty', '?')}/5")
    print("  Reference solution:")
    for line in coding.get("reference_solution", "").splitlines():
        print(f"    | {line}")
    if coding.get("constraints"):
        print(f"  Constraints:   {coding['constraints']}")
    print()

    print("Generating candidate tests + running CodeT consensus + mutation testing...")
    print("(this may take a few LLM calls)...")
    print()

    result = generate_tests(exercise)

    print("-" * 70)
    print(f"  Validation:    {'PASSED' if result['validation_passed'] else 'FAILED'}")
    print(f"  Mutation score: {result['mutation_score']:.2f}")
    print()
    print(f"  Visible tests ({len(result['tests_visible'])}):")
    for t in result["tests_visible"]:
        print(f"    + {t}")
    print()
    print(f"  Hidden tests ({len(result['tests_hidden'])}):")
    for t in result["tests_hidden"]:
        print(f"    + {t}")
    print("-" * 70)

    return 0 if result["validation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
