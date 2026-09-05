#!/usr/bin/env python3
"""Apply or reverse a hash-gated AOB patch manifest on a development copy."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from baseline_inputs import source_path as baseline_source_path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "patches" / "manifests" / "v0.3-constant-proof.json"
DIST_ROOT = (ROOT / "dist").resolve()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def parse_hex_bytes(value: str, field: str) -> bytes:
    try:
        result = bytes.fromhex(value)
    except ValueError as error:
        raise ValueError(f"{field} 不是有效的十六进制字节串") from error
    if not result:
        raise ValueError(f"{field} 不能为空")
    return result


def compile_aob(value: str) -> tuple[re.Pattern[bytes], int]:
    tokens = value.split()
    if not tokens:
        raise ValueError("AOB 不能为空")
    parts: list[bytes] = []
    for token in tokens:
        if token in {"?", "??"}:
            parts.append(b".")
            continue
        if not re.fullmatch(r"[0-9A-Fa-f]{2}", token):
            raise ValueError(f"AOB 标记无效：{token}")
        parts.append(re.escape(bytes([int(token, 16)])))
    return re.compile(b"".join(parts), re.DOTALL), len(tokens)


def find_aob(data: bytes, value: str) -> tuple[list[int], int]:
    pattern, length = compile_aob(value)
    return [match.start() for match in pattern.finditer(data)], length


def parse_offset(value: str | int) -> int:
    if isinstance(value, int):
        return value
    return int(value, 0)


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != 1:
        raise ValueError("只支持 schemaVersion 1")
    if not manifest.get("patches"):
        raise ValueError("补丁清单没有 patches")
    return manifest


def resolve_repo_path(value: str) -> Path:
    return (ROOT / value).resolve()


def require_dist_output(path: Path) -> None:
    resolved = path.resolve()
    if resolved != DIST_ROOT and DIST_ROOT not in resolved.parents:
        raise ValueError(f"输出只能写入 dist：{resolved}")


def section_body(text: str, section: str) -> str:
    marker = f"[{section}]"
    start = text.find(marker)
    if start < 0:
        raise ValueError(f"文案缺少节：{section}")
    body_start = start + len(marker)
    next_marker = re.search(r"(?m)^\[[^\]\r\n]+\]\s*$", text[body_start:])
    body_end = body_start + next_marker.start() if next_marker else len(text)
    return text[body_start:body_end]


def check_text_assertions(manifest: dict[str, Any]) -> None:
    for assertion in manifest.get("textAssertions", []):
        path = resolve_repo_path(assertion["path"])
        text = path.read_bytes().decode(assertion.get("encoding", "utf-8"), errors="strict")
        body = section_body(text, assertion["section"])
        missing = [value for value in assertion.get("contains", []) if value not in body]
        if missing:
            raise ValueError(
                f"{assertion['id']} 文案断言失败，缺少：{'、'.join(missing)}"
            )
        print(f"文案断言通过：{assertion['id']}")


def transform(
    source: bytes, manifest: dict[str, Any], *, reverse: bool
) -> tuple[bytes, list[tuple[str, int, str]]]:
    result = bytearray(source)
    applied: list[tuple[str, int, str]] = []
    for patch in manifest["patches"]:
        matches, pattern_length = find_aob(bytes(result), patch["aob"])
        expected_matches = int(patch.get("expectedMatches", 1))
        if len(matches) != expected_matches:
            raise ValueError(
                f"{patch['id']} AOB 应匹配 {expected_matches} 次，实际 {len(matches)} 次"
            )
        match_offset = matches[0]
        patch_offset = int(patch["patchOffset"])
        before = parse_hex_bytes(patch["before"], f"{patch['id']}.before")
        after = parse_hex_bytes(patch["after"], f"{patch['id']}.after")
        rollback = parse_hex_bytes(patch["rollback"], f"{patch['id']}.rollback")
        expected = after if reverse else before
        replacement = rollback if reverse else after
        if len(before) != len(after) or len(after) != len(rollback):
            raise ValueError(f"{patch['id']} 的前后与回滚字节长度不同")
        if patch_offset < 0 or patch_offset + len(expected) > pattern_length:
            raise ValueError(f"{patch['id']} 的 patchOffset 超出 AOB 范围")
        target = match_offset + patch_offset
        actual = bytes(result[target : target + len(expected)])
        if actual != expected:
            raise ValueError(
                f"{patch['id']} 旧字节不匹配 @ 0x{target:08X}："
                f"预期 {expected.hex(' ').upper()}，实际 {actual.hex(' ').upper()}"
            )
        baseline_offset = parse_offset(patch["baselineFileOffset"])
        if target != baseline_offset:
            raise ValueError(
                f"{patch['id']} AOB 定位到 0x{target:08X}，"
                f"但基线证据记录为 0x{baseline_offset:08X}"
            )
        result[target : target + len(replacement)] = replacement
        direction = "回滚" if reverse else "应用"
        applied.append((patch["id"], target, direction))
    return bytes(result), applied


def expected_hash(manifest: dict[str, Any], reverse: bool) -> str | None:
    if reverse:
        return manifest["baseline"]["sha256"].upper()
    value = manifest["outputs"].get("patchedSha256")
    return value.upper() if value else None


def validate_source_hash(data: bytes, manifest: dict[str, Any], reverse: bool) -> str:
    actual = sha256(data)
    expected = (
        manifest["outputs"].get("patchedSha256")
        if reverse
        else manifest["baseline"]["sha256"]
    )
    if not expected:
        raise ValueError("清单尚未记录 patchedSha256，不能执行回滚")
    if actual != expected.upper():
        label = "已补丁副本" if reverse else "原版基线"
        raise ValueError(f"{label}哈希不匹配：{actual}")
    return actual


def atomic_write(path: Path, data: bytes, force: bool) -> tuple[str, bool]:
    require_dist_output(path)
    result_hash = sha256(data)
    if path.exists():
        existing_hash = sha256(path.read_bytes())
        if existing_hash == result_hash:
            print(f"输出已存在且内容一致：{path}")
            return result_hash, False
        if not force:
            raise ValueError(f"输出已存在且内容不同；如需替换请显式使用 --force：{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return result_hash, True


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="simulate forward patching")
    mode.add_argument("--apply", action="store_true", help="write the patched copy")
    mode.add_argument("--reverse", action="store_true", help="write a restored copy")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    manifest_path = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    manifest = load_manifest(manifest_path.resolve())
    reverse = bool(args.reverse)
    if args.source:
        source_path = args.source if args.source.is_absolute() else ROOT / args.source
    elif reverse:
        source_path = resolve_repo_path(manifest["outputs"]["patchedPath"])
    else:
        source_path = baseline_source_path(manifest["baseline"]["path"])
    source_path = source_path.resolve()
    source = source_path.read_bytes()
    source_hash = validate_source_hash(source, manifest, reverse)
    check_text_assertions(manifest)
    transformed, applied = transform(source, manifest, reverse=reverse)
    transformed_hash = sha256(transformed)
    expected = expected_hash(manifest, reverse)
    if expected and transformed_hash != expected:
        raise ValueError(
            f"生成结果哈希不匹配：预期 {expected}，实际 {transformed_hash}"
        )

    print(f"源文件：{source_path}")
    print(f"源哈希：{source_hash}")
    for patch_id, offset, direction in applied:
        print(f"{direction} {patch_id} @ 0x{offset:08X}")
    print(f"结果哈希：{transformed_hash}")

    if args.check:
        print("补丁预演通过，未写入文件")
        return 0

    if args.output:
        output_path = args.output if args.output.is_absolute() else ROOT / args.output
    else:
        key = "restoredPath" if reverse else "patchedPath"
        output_path = resolve_repo_path(manifest["outputs"][key])
    output_path = output_path.resolve()
    if output_path == source_path:
        raise ValueError("拒绝覆盖输入文件")
    written_hash, wrote = atomic_write(output_path, transformed, args.force)
    action = "已写入" if wrote else "已验证"
    print(f"{action}：{output_path}")
    print(f"写入哈希：{written_hash}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"补丁工具失败：{error}", file=sys.stderr)
        raise SystemExit(1)
