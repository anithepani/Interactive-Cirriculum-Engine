"""Demo: evaluate learner responses for all exercise types (M9).

Usage:
    uv run python scripts/eval_demo.py
    uv run python scripts/eval_demo.py --cases data/fixtures/sample_eval_cases.json

Loads a list of {exercise, response, label} cases, calls ``evaluate()`` for each,
and prints the verdict, score, explanation, hints, and anti-cheat flag.

Requires GROQ_API_KEY in the environment (.env).
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv
from ice_evaluation import evaluate

load_dotenv()

DEFAULT_CASES = os.path.join(
    os.path.dirname(__file__), "..", "data", "fixtures", "sample_eval_cases.json"
)


def _load_json(path: str) -> list:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def _print_result(label: str, exercise: dict, result: dict, index: int) -> None:
    print("=" * 70)
    print(f"  Case {index}: {label}")
    print("=" * 70)
    print(f"  Exercise: {exercise.get('id', '?')}  [{exercise.get('type', '?')}]")
    print(f"  Verdict:        {result['verdict'].upper()}")
    print(f"  Score:          {result['score']:.2f}")
    print(f"  Anti-cheat:     {'FLAGGED' if result['anti_cheat_flag'] else 'clear'}")
    print(f"  Explanation:    {result['explanation']}")
    if result["hints"]:
        print("  Hints:")
        for h in result["hints"]:
            print(f"    - {h}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate learner responses across all exercise types (M9)."
    )
    parser.add_argument(
        "--cases",
        default=DEFAULT_CASES,
        help="Path to a JSON list of {exercise, response, label} cases.",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.cases):
        print(f"Error: cases file not found: {args.cases}", file=sys.stderr)
        return 1

    cases = _load_json(args.cases)
    print(f"Loaded {len(cases)} evaluation cases.\n")

    passes = 0
    for i, case in enumerate(cases, 1):
        exercise = case["exercise"]
        response = case["response"]
        label = case.get("label", f"Case {i}")
        result = evaluate(exercise, response)
        _print_result(label, exercise, result, i)
        if result["verdict"] == "pass":
            passes += 1

    print("-" * 70)
    print(f"  Summary: {passes}/{len(cases)} cases passed")
    print("-" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
