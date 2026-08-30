#!/usr/bin/env python3
"""Small, dependency-free helpers for validating RGBA game sprites."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class RgbaPng:
    width: int
    height: int
    pixels: bytes


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    if up_distance <= upper_left_distance:
        return up
    return upper_left


def decode_rgba8(data: bytes) -> RgbaPng:
    """Decode an 8-bit, non-interlaced RGBA PNG and verify chunk CRCs."""

    if data[:8] != PNG_SIGNATURE:
        raise ValueError("文件不是 PNG")

    position = 8
    width = height = 0
    compressed = bytearray()
    saw_header = False
    saw_end = False
    while position < len(data):
        if position + 12 > len(data):
            raise ValueError("PNG 块头被截断")
        length = struct.unpack_from(">I", data, position)[0]
        chunk_end = position + 12 + length
        if chunk_end > len(data):
            raise ValueError("PNG 块数据被截断")
        chunk_type = data[position + 4 : position + 8]
        chunk = data[position + 8 : position + 8 + length]
        expected_crc = struct.unpack_from(">I", data, position + 8 + length)[0]
        actual_crc = zlib.crc32(chunk_type + chunk) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            name = chunk_type.decode("ascii", errors="replace")
            raise ValueError(f"PNG 块 {name} 的 CRC 无效")
        position = chunk_end

        if chunk_type == b"IHDR":
            if saw_header or length != 13:
                raise ValueError("PNG 的 IHDR 无效")
            (
                width,
                height,
                bit_depth,
                color_type,
                compression,
                filtering,
                interlace,
            ) = struct.unpack(">IIBBBBB", chunk)
            if width <= 0 or height <= 0:
                raise ValueError("PNG 画布尺寸无效")
            if (bit_depth, color_type, compression, filtering, interlace) != (
                8,
                6,
                0,
                0,
                0,
            ):
                raise ValueError("PNG 必须是 8 位 RGBA、非隔行格式")
            saw_header = True
        elif chunk_type == b"IDAT":
            if not saw_header:
                raise ValueError("PNG 的 IDAT 出现在 IHDR 之前")
            compressed.extend(chunk)
        elif chunk_type == b"IEND":
            saw_end = True
            break

    if not saw_header or not saw_end or not compressed:
        raise ValueError("PNG 缺少 IHDR、IDAT 或 IEND")

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
                current[column] = (
                    current[column] + _paeth(left, up, upper_left)
                ) & 0xFF
            elif filter_type != 0:
                raise ValueError(f"不支持的 PNG 过滤器：{filter_type}")
        start = row * stride
        pixels[start : start + stride] = current

    return RgbaPng(width=width, height=height, pixels=bytes(pixels))


def pixel(image: RgbaPng, x: int, y: int) -> tuple[int, int, int, int]:
    offset = (y * image.width + x) * 4
    return tuple(image.pixels[offset : offset + 4])  # type: ignore[return-value]


def visible_pixel_count(image: RgbaPng) -> int:
    return sum(alpha > 0 for alpha in image.pixels[3::4])
