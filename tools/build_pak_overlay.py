#!/usr/bin/env python3
"""Build a development PAK from original data plus committed replacement assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import tempfile
from pathlib import Path
from typing import Any

import pak_assets


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = (ROOT / "assets-src").resolve()
DIST_ROOT = (ROOT / "dist").resolve()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def normalize_name(name: str) -> str:
    return name.replace("\\", "/")


def entry_payload(decoded: bytes, entry: pak_assets.PakEntry) -> bytes:
    return decoded[entry.offset : entry.offset + entry.size]


def rebuild_pak(
    decoded: bytes,
    entries: list[pak_assets.PakEntry],
    replacements: dict[str, bytes],
) -> bytes:
    normalized_entries = {normalize_name(entry.name): entry for entry in entries}
    if len(normalized_entries) != len(entries):
        raise ValueError("PAK 中存在重复资源路径，不能安全重建")
    unknown = sorted(set(replacements) - set(normalized_entries))
    if unknown:
        raise ValueError(f"替换目标不在 PAK 中：{'、'.join(unknown)}")

    table = bytearray(struct.pack("<II", pak_assets.MAGIC, 0))
    payloads: list[bytes] = []
    for entry in entries:
        normalized = normalize_name(entry.name)
        name = entry.name.encode("cp1252")
        if not name or len(name) > 255:
            raise ValueError(f"PAK 路径长度无效：{entry.name}")
        payload = replacements.get(normalized, entry_payload(decoded, entry))
        table.append(0)
        table.append(len(name))
        table.extend(name)
        table.extend(struct.pack("<I", len(payload)))
        table.extend(struct.pack("<Q", entry.file_time))
        payloads.append(payload)
    table.append(0x80)
    for payload in payloads:
        table.extend(payload)
    return bytes(table).translate(pak_assets.XOR_TABLE)


def png_size(data: bytes) -> tuple[int, int] | None:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
        return None
    if data[12:16] != b"IHDR":
        raise ValueError("PNG 缺少 IHDR")
    return struct.unpack(">II", data[16:24])


def resolve_asset_source(value: str) -> Path:
    path = (ROOT / value).resolve()
    if path != ASSET_ROOT and ASSET_ROOT not in path.parents:
        raise ValueError(f"替换源只能来自 assets-src：{path}")
    return path


def require_dist_output(path: Path) -> None:
    resolved = path.resolve()
    if resolved != DIST_ROOT and DIST_ROOT not in resolved.parents:
        raise ValueError(f"输出只能写入 dist：{resolved}")


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != 1:
        raise ValueError("只支持 schemaVersion 1")
    if "baseline" not in manifest or "replacements" not in manifest:
        raise ValueError("素材清单缺少 baseline 或 replacements")
    return manifest


def load_replacements(
    manifest: dict[str, Any], decoded: bytes, entries: list[pak_assets.PakEntry]
) -> dict[str, bytes]:
    by_name = {normalize_name(entry.name): entry for entry in entries}
    loaded: dict[str, bytes] = {}
    for replacement in manifest["replacements"]:
        target = normalize_name(replacement["pakPath"])
        if target in loaded:
            raise ValueError(f"重复替换目标：{target}")
        if target not in by_name:
            raise ValueError(f"替换目标不在 PAK 中：{target}")
        source_path = resolve_asset_source(replacement["source"])
        source = source_path.read_bytes()
        source_hash = sha256(source)
        expected_source_hash = replacement.get("sha256")
        if not expected_source_hash:
            raise ValueError(f"{target} 未记录替换源 sha256")
        if source_hash != expected_source_hash.upper():
            raise ValueError(f"{target} 替换源哈希不匹配：{source_hash}")

        original = entry_payload(decoded, by_name[target])
        original_hash = sha256(original)
        expected_original_hash = replacement.get("originalSha256")
        if not expected_original_hash:
            raise ValueError(f"{target} 未记录 originalSha256")
        if original_hash != expected_original_hash.upper():
            raise ValueError(f"{target} 原资源哈希不匹配：{original_hash}")

        if replacement.get("preserveCanvas", True):
            original_size = png_size(original)
            source_size = png_size(source)
            if original_size is None or source_size is None:
                raise ValueError(f"{target} 要求保持画布，但原件或替换件不是 PNG")
            if original_size != source_size:
                raise ValueError(
                    f"{target} 画布尺寸不一致：原件 {original_size[0]}×{original_size[1]}，"
                    f"替换件 {source_size[0]}×{source_size[1]}"
                )
        loaded[target] = source
        print(f"替换源通过：{target} <- {source_path.relative_to(ROOT)}")
    return loaded


def verify_rebuilt_pak(encoded: bytes, expected_entries: int) -> str:
    output_hash = sha256(encoded)
    _, parsed = pak_assets.parse_pak_bytes(encoded, output_hash)
    if len(parsed) != expected_entries:
        raise ValueError(
            f"重建 PAK 条目数异常：预期 {expected_entries}，实际 {len(parsed)}"
        )
    return output_hash


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


def roundtrip_check() -> None:
    encoded = pak_assets.PAK_PATH.read_bytes()
    decoded, entries = pak_assets.parse_pak_bytes(encoded, pak_assets.PAK_SHA256)
    rebuilt = rebuild_pak(decoded, entries, {})
    rebuilt_hash = verify_rebuilt_pak(rebuilt, len(entries))
    if rebuilt != encoded:
        raise ValueError(
            f"零替换重建不等于基线：原 {pak_assets.PAK_SHA256}，重建 {rebuilt_hash}"
        )
    print(f"PAK 零替换往返通过：{len(entries)} 个资源，SHA-256 {rebuilt_hash}")


def build_from_manifest(manifest: dict[str, Any]) -> tuple[bytes, str]:
    baseline = manifest["baseline"]
    baseline_path = (ROOT / baseline["path"]).resolve()
    encoded = baseline_path.read_bytes()
    baseline_hash = sha256(encoded)
    if baseline_hash != baseline["sha256"].upper():
        raise ValueError(f"PAK 基线哈希不匹配：{baseline_hash}")
    decoded, entries = pak_assets.parse_pak_bytes(encoded, baseline_hash)
    replacements = load_replacements(manifest, decoded, entries)
    rebuilt = rebuild_pak(decoded, entries, replacements)
    output_hash = verify_rebuilt_pak(rebuilt, len(entries))
    expected_output_hash = manifest.get("output", {}).get("sha256")
    if expected_output_hash and output_hash != expected_output_hash.upper():
        raise ValueError(
            f"PAK 输出哈希不匹配：预期 {expected_output_hash}，实际 {output_hash}"
        )
    print(f"PAK 构建通过：{len(entries)} 个资源，替换 {len(replacements)} 个")
    print(f"结果哈希：{output_hash}")
    return rebuilt, output_hash


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--roundtrip-check", action="store_true")
    mode.add_argument("--check", type=Path, metavar="MANIFEST")
    mode.add_argument("--build", type=Path, metavar="MANIFEST")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.roundtrip_check:
        roundtrip_check()
        return 0

    manifest_path = args.check or args.build
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path
    manifest = load_manifest(manifest_path.resolve())
    rebuilt, output_hash = build_from_manifest(manifest)
    if args.check:
        print("素材构建预演通过，未写入文件")
        return 0

    if args.output:
        output_path = args.output if args.output.is_absolute() else ROOT / args.output
    else:
        output_value = manifest.get("output", {}).get("path")
        if not output_value:
            raise ValueError("素材清单没有 output.path，且未传入 --output")
        output_path = ROOT / output_value
    output_path = output_path.resolve()
    baseline_path = (ROOT / manifest["baseline"]["path"]).resolve()
    if output_path == baseline_path:
        raise ValueError("拒绝覆盖输入 PAK")
    written_hash, wrote = atomic_write(output_path, rebuilt, args.force)
    action = "已写入" if wrote else "已验证"
    print(f"{action}：{output_path}")
    print(f"写入哈希：{written_hash or output_hash}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError, struct.error) as error:
        print(f"PAK 构建失败：{error}", file=sys.stderr)
        raise SystemExit(1)
