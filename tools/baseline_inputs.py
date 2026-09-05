"""Explicit, read-only selection of the user's clean game inputs."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE_ENV = "PVZ_USTC_BASELINE_DIR"


def contained_path(root: Path, relative: str) -> Path:
    root = root.resolve()
    part = Path(relative)
    if part.is_absolute() or ".." in part.parts:
        raise ValueError(f"Expected a relative path within {root}: {relative}")
    path = (root / part).resolve()
    if path == root or not path.is_relative_to(root):
        raise ValueError(f"Path escapes its input directory: {relative}")
    return path


def source_path(relative: str, *, baseline_dir: Path | None = None) -> Path:
    selected = baseline_dir if baseline_dir is not None else os.environ.get(BASELINE_ENV)
    root = Path(selected).expanduser().resolve() if selected else ROOT
    return contained_path(root, relative)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def classify_file(path: Path, known_hashes: dict[str, str]) -> dict:
    if not path.exists():
        return {"state": "missing", "sha256": None}
    actual = sha256(path.read_bytes())
    state = next(
        (label for label, digest in known_hashes.items() if actual == digest.upper()),
        "unknown",
    )
    return {"state": state, "sha256": actual}
