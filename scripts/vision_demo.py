#!/usr/bin/env python3
"""vision_demo.py: Demo script for the M3 vision module.

Runs the `extract_visuals` pipeline on a sample video and prints the results.
Usage:
    python scripts/vision_demo.py path/to/video.mp4 [--device cuda]
"""
import argparse
import sys
from pathlib import Path

from ice_vision import extract_visuals


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo for M3 Vision Extraction")
    parser.add_argument("video_path", type=str, help="Path to the video file")
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        choices=["cpu", "cuda"],
        help="Device to run on (cpu or cuda)",
    )
    args = parser.parse_args()

    video_path = Path(args.video_path)
    if not video_path.exists():
        print(f"Error: Video file not found at {video_path}")
        sys.exit(1)

    print(f"Running extract_visuals on {video_path} (device={args.device})...")
    visual_items = extract_visuals(str(video_path), extract_rate_sec=1.0, device=args.device)
    
    print(f"\nExtracted {len(visual_items)} visual items:")
    for i, item in enumerate(visual_items):
        print(f"--- Item {i} ---")
        print(f"Frame: {item.frame_idx} | Timestamp: {item.ts:.2f}s")
        print(f"Type: {item.type.value}")
        print(f"Confidence: {item.confidence:.2f}")
        print(f"Bbox: {item.bbox}")
        text_snippet = item.text[:100].replace("\n", " ") + ("..." if len(item.text) > 100 else "")
        print(f"Text Snippet: {text_snippet}\n")


if __name__ == "__main__":
    main()
