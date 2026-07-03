#!/usr/bin/env python3
"""Bootstrap the dev environment (deps + pre-commit hooks).

Cross-platform (Windows + macOS/Linux). Run: `python scripts/bootstrap.py`
or `make bootstrap`.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=cwd or ROOT)


def main() -> int:
    if shutil.which("uv") is None:
        print("Installing uv...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--user", "uv"]
        )

    run(["uv", "sync"])

    if shutil.which("pnpm") is None:
        print("Installing pnpm...")
        subprocess.check_call(["npm", "install", "-g", "pnpm"])
    run(["pnpm", "install"])

    env_example = ROOT / ".env.example"
    env_file = ROOT / ".env"
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print(f"Copied {env_example.name} -> {env_file.name}; fill in secrets.")

    run(["uv", "run", "pre-commit", "install"])
    print("\nBootstrap complete. Run `make dev` to start the stack.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
