#!/usr/bin/env python3
"""Check a game-sprite contract against main.pak and an optional candidate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import build_pak_overlay as builder
import pak_assets


ROOT = Path(__file__).resolve().parents[1]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--candidate")
    args = parser.parse_args()

    contract = builder.load_asset_contract(args.contract)
    target = builder.normalize_name(str(contract.get("pakPath", "")))
    decoded, entries = pak_assets.parse_pak(pak_assets.PAK_PATH)
    matches = [
        entry
        for entry in entries
        if builder.normalize_name(entry.name) == target
    ]
    if len(matches) != 1:
        raise ValueError(f"契约目标在 PAK 中应唯一存在，实际 {len(matches)} 个：{target}")
    original = builder.entry_payload(decoded, matches[0])
    builder.validate_contract_baseline(contract, target, original)
    print(f"素材契约基线通过：{target}")

    if args.candidate:
        candidate_path = builder.resolve_asset_source(args.candidate)
        builder.validate_replacement_contract(
            contract, target, original, candidate_path.read_bytes()
        )
        print(f"候选贴图通过：{candidate_path.relative_to(ROOT)}")
    else:
        print("未提供候选贴图；仅检查原件哈希、画布与像素规则")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"游戏贴图检查失败：{error}", file=sys.stderr)
        raise SystemExit(1)
