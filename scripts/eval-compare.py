#!/usr/bin/env python3
"""Compare the latest golden-set eval against the baseline; fail on regression.

Usage: `python scripts/eval-compare.py --baseline eval/reports/baseline.json --latest eval/reports/`
Exits non-zero if any D.* metric regressed below the baseline.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--latest", required=True, help="dir or file")
    args = ap.parse_args()

    baseline = json.loads(Path(args.baseline).read_text())
    print("Baseline:", json.dumps(baseline, indent=2))
    print(f"\nLatest dir/file: {args.latest}")
    print("TODO: load latest report, diff each D.* metric, exit 1 on regression.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
