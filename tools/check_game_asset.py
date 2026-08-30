#!/usr/bin/env python3
"""Check game-sprite contracts against main.pak and optional candidates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import build_pak_overlay as builder
import pak_assets


ROOT = Path(__file__).resolve().parents[1]
GAME_ASSET_ROOT = (ROOT / "assets-src" / "game").resolve()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def pak_payloads() -> dict[str, bytes]:
    decoded, entries = pak_assets.parse_pak(pak_assets.PAK_PATH)
    payloads = {
        builder.normalize_name(entry.name): builder.entry_payload(decoded, entry)
        for entry in entries
    }
    if len(payloads) != len(entries):
        raise ValueError("PAK 中存在重复标准化路径")
    return payloads


def validate_contract_path(value: str, payloads: dict[str, bytes]) -> tuple[str, dict]:
    contract = builder.load_asset_contract(value)
    target = builder.normalize_name(str(contract.get("pakPath", "")))
    if target not in payloads:
        raise ValueError(f"契约目标在 PAK 中不存在：{target}")
    builder.validate_contract_baseline(contract, target, payloads[target])
    return target, contract


def discover_contract_paths() -> set[str]:
    return {
        path.relative_to(ROOT).as_posix()
        for path in GAME_ASSET_ROOT.rglob("*.contract.json")
    }


def load_registry(value: str) -> dict:
    path = (ROOT / value).resolve()
    if path != ROOT and ROOT not in path.parents:
        raise ValueError(f"契约清单不能位于仓库外：{path}")
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("schemaVersion") != 1:
        raise ValueError("契约清单只支持 schemaVersion 1")
    if not isinstance(registry.get("entries"), list) or not registry["entries"]:
        raise ValueError("契约清单缺少 entries")
    return registry


def validate_registry(
    registry: dict, payloads: dict[str, bytes], *, verbose: bool = False
) -> tuple[int, int]:
    declared_paths: list[str] = []
    targets: set[str] = set()
    slots: set[str] = set()
    identities: set[tuple[str, str]] = set()
    for index, entry in enumerate(registry["entries"], start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"契约清单 entries[{index}] 无效")
        slot = str(entry.get("slot", "")).upper()
        role = str(entry.get("role", ""))
        contract_path = str(entry.get("contract", "")).replace("\\", "/")
        if not slot or not role or not contract_path:
            raise ValueError(f"契约清单 entries[{index}] 缺少 slot、role 或 contract")
        identity = (slot, role)
        if identity in identities:
            raise ValueError(f"契约清单存在重复槽位角色：{slot}/{role}")
        identities.add(identity)
        slots.add(slot)
        declared_paths.append(contract_path)

        target, contract = validate_contract_path(contract_path, payloads)
        if target in targets:
            raise ValueError(f"契约清单存在重复 PAK 目标：{target}")
        targets.add(target)
        if verbose:
            print(f"清单契约通过：{slot}/{role} -> {target} ({contract['id']})")

    if len(declared_paths) != len(set(declared_paths)):
        raise ValueError("契约清单存在重复 contract 路径")
    discovered = discover_contract_paths()
    declared = set(declared_paths)
    missing = sorted(discovered - declared)
    extra = sorted(declared - discovered)
    if missing:
        raise ValueError(f"发现未登记的素材契约：{'、'.join(missing)}")
    if extra:
        raise ValueError(f"契约清单引用不存在的文件：{'、'.join(extra)}")

    expected_slots = {str(value).upper() for value in registry.get("expectedSlots", [])}
    if expected_slots and slots != expected_slots:
        missing_slots = sorted(expected_slots - slots)
        extra_slots = sorted(slots - expected_slots)
        raise ValueError(
            f"契约清单槽位不一致；缺少 {missing_slots or '无'}，多出 {extra_slots or '无'}"
        )
    return len(declared), len(slots)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--contract")
    mode.add_argument("--registry")
    parser.add_argument("--candidate")
    args = parser.parse_args()

    payloads = pak_payloads()
    if args.registry:
        if args.candidate:
            raise ValueError("清单模式不接受单个 --candidate")
        registry = load_registry(args.registry)
        contract_count, slot_count = validate_registry(registry, payloads, verbose=True)
        print(f"素材契约清单通过：{contract_count} 份契约，{slot_count} 个槽位")
        return 0

    target, contract = validate_contract_path(args.contract, payloads)
    original = payloads[target]
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
