#!/usr/bin/env python3
"""Verify the first art-inventory slice without extracting original assets."""

from __future__ import annotations

import fnmatch
import struct
import sys
import zlib
from pathlib import Path

import pak_assets


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "assets-src" / "concepts" / "p01-greencircle-pea-concept.png"
EXPECTED_GROUPS = {
    "reanim/PeaShooter_*.png": 21,
    "reanim/SunFlower_*.png": 29,
    "reanim/Wallnut_*.png": 6,
    "reanim/Zombie_cone*.png": 3,
}


def paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    if up_distance <= upper_left_distance:
        return up
    return upper_left


def read_rgba_png(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} 不是 PNG")

    position = 8
    width = height = 0
    compressed = bytearray()
    while position < len(data):
        length = struct.unpack_from(">I", data, position)[0]
        chunk_type = data[position + 4 : position + 8]
        chunk = data[position + 8 : position + 8 + length]
        position += length + 12
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", chunk
            )
            if (bit_depth, color_type, compression, filtering, interlace) != (8, 6, 0, 0, 0):
                raise ValueError("概念稿必须是 8 位、RGBA、非隔行 PNG")
        elif chunk_type == b"IDAT":
            compressed.extend(chunk)
        elif chunk_type == b"IEND":
            break

    bytes_per_pixel = 4
    stride = width * bytes_per_pixel
    raw = zlib.decompress(bytes(compressed))
    if len(raw) != height * (stride + 1):
        raise ValueError("PNG 扫描线长度异常")

    pixels = bytearray(height * stride)
    source = 0
    for row in range(height):
        filter_type = raw[source]
        source += 1
        current = bytearray(raw[source : source + stride])
        source += stride
        previous_start = (row - 1) * stride
        for column in range(stride):
            left = current[column - bytes_per_pixel] if column >= bytes_per_pixel else 0
            up = pixels[previous_start + column] if row else 0
            upper_left = (
                pixels[previous_start + column - bytes_per_pixel]
                if row and column >= bytes_per_pixel
                else 0
            )
            if filter_type == 1:
                current[column] = (current[column] + left) & 0xFF
            elif filter_type == 2:
                current[column] = (current[column] + up) & 0xFF
            elif filter_type == 3:
                current[column] = (current[column] + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                current[column] = (current[column] + paeth(left, up, upper_left)) & 0xFF
            elif filter_type != 0:
                raise ValueError(f"不支持的 PNG 过滤器：{filter_type}")
        start = row * stride
        pixels[start : start + stride] = current
    return width, height, bytes(pixels)


def main() -> int:
    _, entries = pak_assets.parse_pak(pak_assets.PAK_PATH)
    if len(entries) != 2413:
        raise ValueError(f"PAK 资源数量异常：{len(entries)}")
    normalized = [pak_assets.normalize_name(entry.name) for entry in entries]
    if len(normalized) != len(set(normalized)):
        raise ValueError("PAK 中存在重复资源路径")
    for pattern, expected in EXPECTED_GROUPS.items():
        actual = sum(
            fnmatch.fnmatchcase(name.lower(), pattern.lower()) for name in normalized
        )
        if actual != expected:
            raise ValueError(f"{pattern}：预期 {expected}，实际 {actual}")

    width, height, pixels = read_rgba_png(CONCEPT)
    if (width, height) != (1254, 1254):
        raise ValueError(f"概念稿尺寸异常：{width}×{height}")
    stride = width * 4
    top_alpha = pixels[3:stride:4]
    bottom_alpha = pixels[(height - 1) * stride + 3 : height * stride : 4]
    side_alpha = bytearray()
    for row in range(1, height - 1):
        side_alpha.append(pixels[row * stride + 3])
        side_alpha.append(pixels[row * stride + stride - 1])
    if any(top_alpha) or any(bottom_alpha) or any(side_alpha):
        raise ValueError("概念稿透明边界存在非透明像素")
    if not any(pixels[3::4]):
        raise ValueError("概念稿没有任何可见像素")

    print(
        "美术资源检查通过：2413 个 PAK 资源；"
        "P01/P02/P04/Z03 部件计数为 21/29/6/3；"
        "概念稿 1254×1254 RGBA，透明边界正常"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, zlib.error) as error:
        print(f"美术资源检查失败：{error}", file=sys.stderr)
        raise SystemExit(1)
