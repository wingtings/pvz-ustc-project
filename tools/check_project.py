#!/usr/bin/env python3
"""Run public checks, or the full checks against explicitly selected clean inputs."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from baseline_inputs import BASELINE_ENV


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public", action="store_true", help="No original game files required")
    parser.add_argument("--baseline-dir", type=Path)
    args = parser.parse_args()
    environment = dict(os.environ, PYTHONUTF8="1")
    if args.baseline_dir:
        environment[BASELINE_ENV] = str(args.baseline_dir.resolve())
    commands = [
        ["tools/check_lawnstrings.py"],
        ["tools/sync_lawnstrings.py", "--check"],
        ["-m", "unittest", "discover", "-s", "tests/unit" if args.public else "tests", "-p", "test_*.py"],
    ]
    if not args.public:
        commands.extend([
            ["tools/apply_binary_patches.py", "--check"],
            ["tools/build_pak_overlay.py", "--roundtrip-check"],
            ["tools/check_art_assets.py"],
            ["tools/check_game_asset.py", "--registry", "patches/manifests/v0.5-first-slice-contracts.json"],
        ])
    for command in commands:
        result = subprocess.run([sys.executable, *command], cwd=ROOT, env=environment)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
