"""Run the full M2-M9 generation pipeline on a video file.

Usage:
    uv run python scripts/run_pipeline.py --video long_video.wav
    uv run python scripts/run_pipeline.py --video long_video.wav --output-dir out/ --force
    uv run python scripts/run_pipeline.py --video long_video.wav --validate --eval

Pipeline stages:
    M2  transcribe           -> {base}_transcript.json
    M4  segment_transcript   -> {base}_segments.json
    M5  extract_concepts     -> {base}_graph.json
    M6  place_checkpoints    -> {base}_checkpoints.json
    M7  generate_exercises   -> {base}_exercises.json
    M8  generate_tests       -> {base}_tests.json          (only with --validate)
    M9  evaluate             -> {base}_eval_results.json   (only with --eval)

Each stage is cached: if its output JSON already exists it is loaded instead of
re-run. Use --force to rebuild every stage from scratch.

Requires GROQ_API_KEY in the environment (.env).
"""

import argparse
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from ice_checkpoints import place_checkpoints
from ice_concept_graph import extract_concepts_and_edges
from ice_evaluation import evaluate
from ice_exercise_gen import generate_exercises
from ice_segmentation import segment_transcript
from ice_test_gen import generate_tests
from ice_transcript import transcribe

load_dotenv()

MIN_GAP_SEC_DEFAULT = 90.0
MIN_START_SEC_DEFAULT = 0.0  # demos: place from t=0; production worker uses 60
AVOID_FINAL_SEC_DEFAULT = 30.0  # matches production


def _load_or_run(path: Path, force: bool, run_fn, label: str):
    """Load a cached JSON output or run ``run_fn`` and write it to ``path``."""
    if path.exists() and not force:
        print(f"[cached] {label} -> {path.name}")
        with path.open(encoding="utf-8-sig") as f:
            return json.load(f)
    print(f"[run]   {label} ...")
    t0 = time.monotonic()
    result = run_fn()
    elapsed = time.monotonic() - t0
    with path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"[done]  {label} in {elapsed:.1f}s -> {path.name}")
    return result


def _load_json(path: Path):
    with path.open(encoding="utf-8-sig") as f:
        return json.load(f)


def _mock_response(exercise: dict) -> dict:
    """Build a 'perfect learner' response for an exercise (M9 smoke test)."""
    etype = exercise.get("type", "")
    if etype == "mcq":
        return {"answer_idx": exercise["mcq"]["answer_idx"]}
    if etype == "coding":
        return {"code": exercise["coding"]["reference_solution"]}
    if etype == "debug":
        return {
            "corrected_code": exercise["debug"]["buggy_code"],
            "explanation": exercise["debug"]["bug_explanation"],
        }
    if etype == "conceptual":
        return {"answer": exercise["conceptual"]["reference_answer"]}
    return {}


def _step_transcribe(video: Path, out: Path, force: bool) -> dict:
    return _load_or_run(out, force, lambda: transcribe(str(video)), "M2 transcribe")


def _step_segments(transcript: dict, out: Path, force: bool) -> list:
    return _load_or_run(out, force, lambda: segment_transcript(transcript), "M4 segment_transcript")


def _step_graph(segments: list, out: Path, force: bool) -> dict:
    return _load_or_run(
        out, force, lambda: extract_concepts_and_edges(segments), "M5 extract_concepts"
    )


def _step_checkpoints(segments: list, graph: dict, out: Path, force: bool, min_gap: float, min_start: float, avoid_final: float) -> list:
    return _load_or_run(
        out,
        force,
        lambda: place_checkpoints(segments, graph, min_gap_sec=min_gap, min_start_sec=min_start, avoid_final_sec=avoid_final),
        "M6 place_checkpoints",
    )


def _step_exercises(checkpoints: list, segments: list, graph: dict, out: Path, force: bool) -> list:
    return _load_or_run(
        out,
        force,
        lambda: generate_exercises(checkpoints, segments, graph),
        "M7 generate_exercises",
    )


def _step_tests(exercises: list, out: Path, force: bool) -> list:
    """Run M8 test generation on every coding exercise."""

    def run() -> list:
        results = []
        for ex in exercises:
            if ex.get("type") != "coding":
                continue
            res = generate_tests(ex)
            results.append({"exercise_id": ex.get("id"), **res})
        return results

    return _load_or_run(out, force, run, "M8 generate_tests")


def _step_eval(exercises: list, out: Path, force: bool) -> list:
    """Run M9 evaluation with mock perfect responses."""

    def run() -> list:
        results = []
        for ex in exercises:
            response = _mock_response(ex)
            if not response:
                continue
            res = evaluate(ex, response)
            results.append({"exercise_id": ex.get("id"), **res})
        return results

    return _load_or_run(out, force, run, "M9 evaluate")


def _print_summary(transcript, segments, graph, checkpoints, exercises, tests, evals):
    print()
    print("=" * 70)
    print("  PIPELINE SUMMARY")
    print("=" * 70)
    tsegs = transcript.get("segments", [])
    dur = tsegs[-1]["end"] if tsegs else 0.0
    print(
        f"  M2 transcript:   {len(tsegs)} segments, {dur / 60:.1f} min, lang={transcript.get('language', '?')}"
    )
    print(f"  M4 segments:     {len(segments)} topic segments")
    print(
        f"  M5 concept graph: {len(graph.get('concepts', []))} concepts, {len(graph.get('edges', []))} edges"
    )
    print(f"  M6 checkpoints:  {len(checkpoints)} placed")
    if checkpoints:
        types = {}
        for cp in checkpoints:
            t = cp.get("exercise_type", "?")
            types[t] = types.get(t, 0) + 1
        print(f"                   types: {types}")
    print(f"  M7 exercises:    {len(exercises)} generated")
    if exercises:
        types = {}
        for ex in exercises:
            t = ex.get("type", "?")
            types[t] = types.get(t, 0) + 1
        print(f"                   types: {types}")
    if tests is not None:
        passed = sum(1 for t in tests if t.get("validation_passed"))
        print(f"  M8 tests:        {passed}/{len(tests)} coding exercises validated")
        scores = [t.get("mutation_score", 0) for t in tests]
        if scores:
            print(f"                   mutation scores: {scores}")
    if evals is not None:
        verdicts = {}
        for e in evals:
            v = e.get("verdict", "?")
            verdicts[v] = verdicts.get(v, 0) + 1
        print(f"  M9 eval:         {verdicts}")
        scores = [e.get("score", 0) for e in evals]
        if scores:
            print(f"                   scores: {scores}")
    print("=" * 70)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the full M2-M9 generation pipeline on a video file."
    )
    parser.add_argument(
        "--video",
        required=True,
        help="Path to a .wav audio file.",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory for intermediate JSON files (default: current dir).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild all stages (ignore cache).",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run M8 test generation on coding exercises.",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Run M9 evaluation with mock perfect responses.",
    )
    parser.add_argument(
        "--min-gap-sec",
        type=float,
        default=MIN_GAP_SEC_DEFAULT,
        help=f"Min seconds between checkpoints (default: {MIN_GAP_SEC_DEFAULT}).",
    )
    parser.add_argument(
        "--min-start-sec",
        type=float,
        default=MIN_START_SEC_DEFAULT,
        help=f"Min seconds before the first checkpoint (default: {MIN_START_SEC_DEFAULT}; production worker uses 60).",
    )
    parser.add_argument(
        "--avoid-final-sec",
        type=float,
        default=AVOID_FINAL_SEC_DEFAULT,
        help=f"Avoid placing checkpoints in the final N seconds, except the final segment (default: {AVOID_FINAL_SEC_DEFAULT}).",
    )
    args = parser.parse_args()

    video = Path(args.video).resolve()
    if not video.is_file():
        print(f"Error: video file not found: {video}", file=sys.stderr)
        return 1
    if video.suffix.lower() != ".wav":
        print(f"Warning: expected a .wav file, got {video.name}", file=sys.stderr)

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    base = video.stem

    f_transcript = out_dir / f"{base}_transcript.json"
    f_segments = out_dir / f"{base}_segments.json"
    f_graph = out_dir / f"{base}_graph.json"
    f_checkpoints = out_dir / f"{base}_checkpoints.json"
    f_exercises = out_dir / f"{base}_exercises.json"
    f_tests = out_dir / f"{base}_tests.json"
    f_evals = out_dir / f"{base}_eval_results.json"

    print(f"Video:      {video}")
    print(f"Output dir: {out_dir}")
    print(f"Base name:  {base}")
    print(f"Force:      {args.force}")
    print()

    t_start = time.monotonic()
    try:
        transcript = _step_transcribe(video, f_transcript, args.force)
        segments = _step_segments(transcript, f_segments, args.force)
        graph = _step_graph(segments, f_graph, args.force)
        checkpoints = _step_checkpoints(
            segments, graph, f_checkpoints, args.force, args.min_gap_sec, args.min_start_sec, args.avoid_final_sec
        )
        exercises = _step_exercises(checkpoints, segments, graph, f_exercises, args.force)

        tests = None
        if args.validate:
            tests = _step_tests(exercises, f_tests, args.force)

        evals = None
        if args.eval:
            evals = _step_eval(exercises, f_evals, args.force)
    except Exception as exc:
        elapsed = time.monotonic() - t_start
        print(f"\nPipeline FAILED after {elapsed:.1f}s: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    elapsed = time.monotonic() - t_start
    _print_summary(transcript, segments, graph, checkpoints, exercises, tests, evals)
    print(f"\nTotal time: {elapsed:.1f}s ({elapsed / 60:.1f} min)")
    print(f"Output files in: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
