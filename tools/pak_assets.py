#!/usr/bin/env python3
"""List or selectively extract assets from the project's PC main.pak.

Extracted files are local references under .work and are never release assets.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import struct
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from baseline_inputs import source_path


ROOT = Path(__file__).resolve().parents[1]
PAK_PATH = source_path("main.pak")
DEFAULT_OUT = ROOT / ".work" / "pak-reference"
PAK_SHA256 = "3B5291C6600076AAF1791AE1FB2DBF247290A23E903D1D376413DA17358E049D"
MAGIC = 0xBAC04AC0
XOR_TABLE = bytes(value ^ 0xF7 for value in range(256))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


@dataclass(frozen=True)
class PakEntry:
    name: str
    size: int
    file_time: int
    offset: int


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def parse_pak_bytes(
    encoded: bytes, expected_hash: str | None = None
) -> tuple[bytes, list[PakEntry]]:
    actual_hash = sha256(encoded)
    if expected_hash and actual_hash != expected_hash.upper():
        raise ValueError(f"main.pak 哈希不匹配：{actual_hash}")

    data = encoded.translate(XOR_TABLE)
    magic, version = struct.unpack_from("<II", data, 0)
    if magic != MAGIC or version != 0:
        raise ValueError(f"不支持的 PAK 头：{magic:08X}, version {version}")

    position = 8
    table: list[tuple[str, int, int]] = []
    while True:
        marker = data[position]
        position += 1
        if marker == 0x80:
            break
        if marker != 0:
            raise ValueError(f"PAK 表标记异常：0x{marker:02X} @ {position - 1}")
        name_size = data[position]
        position += 1
        name = data[position : position + name_size].decode("cp1252")
        position += name_size
        size = struct.unpack_from("<I", data, position)[0]
        position += 4
        file_time = struct.unpack_from("<Q", data, position)[0]
        position += 8
        table.append((name, size, file_time))

    entries: list[PakEntry] = []
    data_offset = position
    for name, size, file_time in table:
        if data_offset + size > len(data):
            raise ValueError(f"{name} 超出 PAK 数据范围")
        entries.append(PakEntry(name, size, file_time, data_offset))
        data_offset += size
    if data_offset != len(data):
        raise ValueError(f"PAK 末尾存在 {len(data) - data_offset} 个未解释字节")
    return data, entries


def parse_pak(path: Path) -> tuple[bytes, list[PakEntry]]:
    return parse_pak_bytes(path.read_bytes(), PAK_SHA256)


def normalize_name(name: str) -> str:
    return name.replace("\\", "/")


def matches(entry: PakEntry, patterns: list[str]) -> bool:
    name = normalize_name(entry.name).lower()
    return any(fnmatch.fnmatch(name, pattern.replace("\\", "/").lower()) for pattern in patterns)


def safe_target(root: Path, entry: PakEntry) -> Path:
    relative = PurePosixPath(normalize_name(entry.name))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"拒绝不安全的 PAK 路径：{entry.name}")
    target = root.joinpath(*relative.parts).resolve()
    resolved_root = root.resolve()
    if target != resolved_root and resolved_root not in target.parents:
        raise ValueError(f"拒绝越界写入：{target}")
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", nargs="+", metavar="GLOB", help="list matching PAK entries")
    mode.add_argument("--extract", nargs="+", metavar="GLOB", help="extract matching entries")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    data, entries = parse_pak(PAK_PATH)
    patterns = args.list or args.extract
    selected = [entry for entry in entries if matches(entry, patterns)]
    if not selected:
        print("没有匹配的资源", file=sys.stderr)
        return 1

    if args.list:
        for entry in selected:
            print(f"{entry.size:>8}  {normalize_name(entry.name)}")
        print(f"匹配 {len(selected)} / {len(entries)} 个资源")
        return 0

    out = args.out if args.out.is_absolute() else (ROOT / args.out)
    out = out.resolve()
    allowed_root = (ROOT / ".work").resolve()
    if out != allowed_root and allowed_root not in out.parents:
        raise ValueError("参考素材只能解包到仓库的 .work 目录")
    for entry in selected:
        target = safe_target(out, entry)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data[entry.offset : entry.offset + entry.size])
        print(f"已提取 {normalize_name(entry.name)}")
    print(f"共提取 {len(selected)} 个参考资源到 {out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, struct.error) as error:
        print(f"PAK 资源工具失败：{error}", file=sys.stderr)
        raise SystemExit(1)
