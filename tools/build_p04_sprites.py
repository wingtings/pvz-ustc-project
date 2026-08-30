#!/usr/bin/env python3
"""Build the three P04 campus-wall damage stages from verified Wall-nut sprites."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
from pathlib import Path

import pak_assets
import png_assets


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "assets-src" / "game" / "p04"
PREVIEW_PATH = ROOT / ".work" / "previews" / "p04-damage-stages-5x.png"

SPECS = {
    "reanim/Wallnut_body.png": (
        "Wallnut_body.png",
        "5B38DC3365F2D1BA44AF43A979E328973C2B1AE9E1A4371857A00310518911BA",
    ),
    "reanim/Wallnut_cracked1.png": (
        "Wallnut_cracked1.png",
        "13C3533479147545823144AC5816FBA137F5900E6065E38B7C4A4CAA64A4DACD",
    ),
    "reanim/Wallnut_cracked2.png": (
        "Wallnut_cracked2.png",
        "A7F68DE19400558089B6D1AEED2696C56BFF8CCB51965776FB93C46588D9666C",
    ),
}

STONE_DARK = (48, 47, 43)
MORTAR_DARK = (58, 57, 54)
PLATE_BORDER = (8, 34, 78)
PLATE_BLUE = (25, 91, 166)
PLATE_LIGHT = (48, 126, 197)
PLATE_TEXT = (231, 235, 222)

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pak_payloads() -> dict[str, bytes]:
    decoded, entries = pak_assets.parse_pak(pak_assets.PAK_PATH)
    wanted = set(SPECS)
    result: dict[str, bytes] = {}
    for entry in entries:
        target = pak_assets.normalize_name(entry.name)
        if target in wanted:
            result[target] = decoded[entry.offset : entry.offset + entry.size]
    missing = sorted(wanted - result.keys())
    if missing:
        raise ValueError(f"main.pak 缺少 P04 原件：{', '.join(missing)}")
    for target, payload in result.items():
        _, expected_hash = SPECS[target]
        actual_hash = sha256(payload)
        if actual_hash != expected_hash:
            raise ValueError(f"{target} 原件哈希不匹配：{actual_hash}")
        image = png_assets.decode_rgba8(payload)
        if (image.width, image.height) != (100, 100):
            raise ValueError(f"{target} 原件画布不匹配：{image.width}×{image.height}")
    return result


def pixel_offset(width: int, x: int, y: int) -> int:
    return (y * width + x) * 4


def rgba_at(pixels: bytearray | bytes, width: int, x: int, y: int) -> tuple[int, int, int, int]:
    start = pixel_offset(width, x, y)
    return tuple(pixels[start : start + 4])  # type: ignore[return-value]


def protected_original_color(rgba: tuple[int, int, int, int]) -> bool:
    red, green, blue, alpha = rgba
    dark_detail = alpha >= 120 and red <= 75 and green <= 65 and blue <= 50
    eye_white = alpha >= 180 and red >= 190 and green >= 175 and blue >= 130
    return dark_detail or eye_white


def paint_pixel(
    pixels: bytearray,
    image: png_assets.RgbaPng,
    x: int,
    y: int,
    color: tuple[int, int, int],
) -> None:
    if not (8 <= x <= 93 and 0 <= y < image.height):
        return
    if protected_original_color(rgba_at(image.pixels, image.width, x, y)):
        return
    start = pixel_offset(image.width, x, y)
    alpha = pixels[start + 3]
    if alpha > 0:
        pixels[start : start + 4] = bytes((*color, alpha))


def line_points(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    delta_x = abs(x1 - x0)
    step_x = 1 if x0 < x1 else -1
    delta_y = -abs(y1 - y0)
    step_y = 1 if y0 < y1 else -1
    error = delta_x + delta_y
    while True:
        points.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return points
        doubled = 2 * error
        if doubled >= delta_y:
            error += delta_y
            x0 += step_x
        if doubled <= delta_x:
            error += delta_x
            y0 += step_y


def paint_line(
    pixels: bytearray,
    image: png_assets.RgbaPng,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
    thickness: int = 1,
) -> None:
    for x, y in line_points(*start, *end):
        for offset_y in range(thickness):
            paint_pixel(pixels, image, x, y + offset_y, color)


def stone_color(red: int, green: int, blue: int) -> tuple[int, int, int]:
    luminance = (red * 30 + green * 59 + blue * 11) // 100
    if luminance < 52:
        return STONE_DARK
    value = min(174, 73 + (luminance * 2) // 5)
    return value + 7, value + 2, max(60, value - 8)


def repaint_shell(pixels: bytearray, image: png_assets.RgbaPng) -> None:
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = rgba_at(pixels, image.width, x, y)
            if alpha == 0 or not (8 <= x <= 93):
                continue
            paint_pixel(pixels, image, x, y, stone_color(red, green, blue))


def paint_masonry(pixels: bytearray, image: png_assets.RgbaPng) -> None:
    for start, end in (
        ((16, 18), (86, 18)),
        ((14, 69), (88, 69)),
        ((18, 86), (83, 86)),
        ((31, 2), (31, 18)),
        ((69, 18), (69, 27)),
        ((59, 69), (59, 86)),
        ((35, 86), (35, 97)),
    ):
        paint_line(pixels, image, start, end, MORTAR_DARK)

    for start, end in (
        ((20, 22), (29, 20)),
        ((75, 74), (84, 72)),
        ((48, 91), (55, 90)),
    ):
        paint_line(pixels, image, start, end, (162, 154, 137))


def paint_plate(pixels: bytearray, image: png_assets.RgbaPng) -> None:
    for y in range(72, 85):
        for x in range(24, 45):
            border = x in {24, 44} or y in {72, 84}
            paint_pixel(pixels, image, x, y, PLATE_BORDER if border else PLATE_BLUE)
    paint_line(pixels, image, (26, 74), (42, 74), PLATE_LIGHT)

    glyphs = {
        "1": ("010", "110", "010", "010", "010", "010", "111"),
        "4": ("101", "101", "111", "001", "001", "001", "001"),
    }
    for character, left in (("1", 29), ("4", 37)):
        for row, bits in enumerate(glyphs[character]):
            for column, bit in enumerate(bits):
                if bit == "1":
                    paint_pixel(pixels, image, left + column, 76 + row, PLATE_TEXT)


def build_stage(original: bytes) -> bytes:
    image = png_assets.decode_rgba8(original)
    pixels = bytearray(image.pixels)
    repaint_shell(pixels, image)
    paint_masonry(pixels, image)
    paint_plate(pixels, image)
    return png_assets.encode_rgba8(
        png_assets.RgbaPng(image.width, image.height, bytes(pixels))
    )


def build_all() -> dict[str, bytes]:
    originals = pak_payloads()
    return {
        output_name: build_stage(originals[target])
        for target, (output_name, _) in SPECS.items()
    }


def atomic_write(path: Path, payload: bytes, force: bool) -> None:
    if path.exists() and path.read_bytes() == payload:
        print(f"已验证：{path.relative_to(ROOT)}")
        return
    if path.exists() and not force:
        raise ValueError(f"输出已存在且内容不同；如需替换请使用 --force：{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    print(f"已生成：{path.relative_to(ROOT)}")


def nearest(image: png_assets.RgbaPng, scale: int) -> png_assets.RgbaPng:
    width = image.width * scale
    height = image.height * scale
    pixels = bytearray(width * height * 4)
    for y in range(height):
        for x in range(width):
            source = pixel_offset(image.width, x // scale, y // scale)
            destination = pixel_offset(width, x, y)
            pixels[destination : destination + 4] = image.pixels[source : source + 4]
    return png_assets.RgbaPng(width, height, bytes(pixels))


def preview(candidates: dict[str, bytes]) -> bytes:
    scale = 5
    images = [nearest(png_assets.decode_rgba8(candidates[name]), scale) for name in candidates]
    gap = 4 * scale
    width = sum(image.width for image in images) + gap * (len(images) - 1)
    height = max(image.height for image in images)
    canvas = bytearray(width * height * 4)
    left = 0
    for image in images:
        for y in range(image.height):
            source = y * image.width * 4
            destination = (y * width + left) * 4
            canvas[destination : destination + image.width * 4] = image.pixels[
                source : source + image.width * 4
            ]
        left += image.width + gap
    return png_assets.encode_rgba8(png_assets.RgbaPng(width, height, bytes(canvas)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只计算并报告确定性哈希")
    parser.add_argument("--build", action="store_true", help="生成本地候选 PNG")
    parser.add_argument("--preview", action="store_true", help="生成五倍三档预览到 .work")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not (args.check or args.build or args.preview):
        parser.error("至少选择 --check、--build 或 --preview 之一")

    candidates = build_all()
    for name, payload in candidates.items():
        print(f"{name}: {sha256(payload)}")
        if args.build:
            atomic_write(OUTPUT_ROOT / name, payload, args.force)
    if args.preview:
        atomic_write(PREVIEW_PATH, preview(candidates), args.force)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"P04 贴图构建失败：{error}", file=sys.stderr)
        raise SystemExit(1)
