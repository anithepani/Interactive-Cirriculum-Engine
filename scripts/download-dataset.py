#!/usr/bin/env python3
"""Download subsets of the suggested open-source datasets (master plan).

Datasets: HowTo100M, How2, Multimodal-Textbook-6.5M, CodeSCAN.
Downloads go to data/raw/ (gitignored). Only fetch small subsets for dev/eval.
"""
from __future__ import annotations

import sys

DATASETS = {
    "howto100m": "https://www.di.ens.fr/willow/research/howto100m/",
    "how2": "https://srvk.github.io/how2-dataset/",
    "multimodal-textbook": "https://github.com/yaohungt/Multimodal-Textbook",
    "codescan": "https://github.com/dakshitathakur/CodeSCAN",
}


def main() -> int:
    print("Suggested open-source datasets (master plan):")
    for name, url in DATASETS.items():
        print(f"  {name:24s} {url}")
    print("\nLarge datasets are NOT downloaded automatically.")
    print("Fetch small subsets into data/raw/ (gitignored) for dev/eval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
