#!/usr/bin/env python3
"""Run the full generation pipeline on a sample video (Phase-0 smoke test).

Usage: `python scripts/run-pipeline.py [video_ref]`
Defaults to a sample YouTube URL if none given.
"""
from __future__ import annotations

import sys
from uuid import uuid4


def main() -> int:
    video_ref = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=sample"
    tenant_id = uuid4()
    print(f"Submitting video for ingestion:")
    print(f"  video_ref = {video_ref}")
    print(f"  tenant_id = {tenant_id}")
    print("\nPhase 0-3 deliverable: wire this to ice_worker.pipeline.generate_curriculum")
    print("Once wired, this kicks off the async pipeline and polls for completion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
