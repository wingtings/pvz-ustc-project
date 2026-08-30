#!/usr/bin/env python3
"""Build P02 study-expression and note-petal overlays from a verified main.pak."""

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
OUTPUT_ROOT = ROOT / "assets-src" / "game" / "p02"
PREVIEW_PATH = ROOT / ".work" / "previews" / "p02-sprites-10x.png"

SPECS = {
    "reanim/SunFlower_head.png": (
        "SunFlower_head.png",
        "3813EA881B25465DEC25E75B7FA2A20FDE4B421E7DD7C3B1FFABF4EB1FD61FB3",
        (57, 43),
    ),
    "reanim/SunFlower_toppetals.png": (
        "SunFlower_toppetals.png",
        "DADBD5ED1F98867E35A29164F83E735C14554ADBE1E62A41C8588E07017C1B07",
        (16, 10),
    ),
    "reanim/SunFlower_bottompetals.png": (
        "SunFlower_bottompetals.png",
        "034CE4342F4C972ECF9E5DF758164AC35E1E7B96972FCCE022BA992C6E5256FE",
        (19, 15),
    ),
}

USTC_BLUE = (22, 83, 165)
USTC_BLUE_LIGHT = (45, 117, 198)
INK_DARK = (25, 20, 18)
PAPER_WHITE = (239, 239, 222)
NOTE_BLUE = (25, 102, 184)
NOTE_DIVIDER = (9, 40, 98)


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
        raise ValueError(f"main.pak 缺少 P02 原件：{', '.join(missing)}")
    for target, payload in result.items():
        _, expected_hash, expected_size = SPECS[target]
        actual_hash = sha256(payload)
        if actual_hash != expected_hash:
            raise ValueError(f"{target} 原件哈希不匹配：{actual_hash}")
        image = png_assets.decode_rgba8(payload)
        if (image.width, image.height) != expected_size:
            raise ValueError(f"{target} 原件画布不匹配：{image.width}×{image.height}")
    return result


def pixel_offset(width: int, x: int, y: int) -> int:
    return (y * width + x) * 4


def rgba_at(pixels: bytearray | bytes, width: int, x: int, y: int) -> tuple[int, int, int, int]:
    start = pixel_offset(width, x, y)
    return tuple(pixels[start : start + 4])  # type: ignore[return-value]


def set_rgb_preserve_alpha(
    pixels: bytearray,
    width: int,
    x: int,
    y: int,
    color: tuple[int, int, int],
) -> None:
    start = pixel_offset(width, x, y)
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


def protected_eye_core(x: int, y: int) -> bool:
    return (19 <= x <= 24 and 12 <= y <= 22) or (38 <= x <= 43 and 12 <= y <= 22)


def paint_head_line(
    pixels: bytearray,
    image: png_assets.RgbaPng,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
    thickness: int = 1,
) -> None:
    for x, y in line_points(*start, *end):
        for offset_y in range(thickness):
            target_y = y + offset_y
            if 0 <= x < image.width and 0 <= target_y < image.height and not protected_eye_core(x, target_y):
                set_rgb_preserve_alpha(pixels, image.width, x, target_y, color)


def build_head(original: bytes) -> bytes:
    image = png_assets.decode_rgba8(original)
    pixels = bytearray(image.pixels)

    # A narrow blue study headband keeps the warm face recognizable while
    # surviving the battle-scale reduction.
    for start, end in (
        ((12, 8), (22, 5)),
        ((22, 5), (34, 5)),
        ((34, 5), (45, 8)),
    ):
        paint_head_line(pixels, image, start, end, USTC_BLUE, thickness=2)
    paint_head_line(pixels, image, (26, 5), (31, 5), USTC_BLUE_LIGHT, thickness=1)

    # Inward-sloping eyebrows create a focused expression without touching
    # either eye core or the blink overlays.
    paint_head_line(pixels, image, (17, 10), (25, 8), INK_DARK, thickness=2)
    paint_head_line(pixels, image, (37, 8), (45, 10), INK_DARK, thickness=2)

    return png_assets.encode_rgba8(
        png_assets.RgbaPng(image.width, image.height, bytes(pixels))
    )


def recolor_notes(
    original: bytes,
    *,
    separator_x: int,
    left_color: tuple[int, int, int],
    right_color: tuple[int, int, int],
) -> bytes:
    image = png_assets.decode_rgba8(original)
    pixels = bytearray(image.pixels)
    for y in range(image.height):
        for x in range(image.width):
            if rgba_at(pixels, image.width, x, y)[3] == 0:
                continue
            if x < separator_x:
                color = left_color
            elif x == separator_x:
                color = NOTE_DIVIDER
            else:
                color = right_color
            set_rgb_preserve_alpha(pixels, image.width, x, y, color)
    return png_assets.encode_rgba8(
        png_assets.RgbaPng(image.width, image.height, bytes(pixels))
    )


def build_all() -> dict[str, bytes]:
    originals = pak_payloads()
    return {
        "SunFlower_head.png": build_head(originals["reanim/SunFlower_head.png"]),
        "SunFlower_toppetals.png": recolor_notes(
            originals["reanim/SunFlower_toppetals.png"],
            separator_x=7,
            left_color=PAPER_WHITE,
            right_color=NOTE_BLUE,
        ),
        "SunFlower_bottompetals.png": recolor_notes(
            originals["reanim/SunFlower_bottompetals.png"],
            separator_x=8,
            left_color=NOTE_BLUE,
            right_color=PAPER_WHITE,
        ),
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
    scale = 10
    images = [nearest(png_assets.decode_rgba8(candidates[name]), scale) for name in candidates]
    gap = 4 * scale
    width = sum(image.width for image in images) + gap * (len(images) - 1)
    height = max(image.height for image in images)
    canvas = bytearray(width * height * 4)
    left = 0
    for image in images:
        top = (height - image.height) // 2
        for y in range(image.height):
            source = y * image.width * 4
            destination = ((top + y) * width + left) * 4
            canvas[destination : destination + image.width * 4] = image.pixels[
                source : source + image.width * 4
            ]
        left += image.width + gap
    return png_assets.encode_rgba8(png_assets.RgbaPng(width, height, bytes(canvas)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只计算并报告确定性哈希")
    parser.add_argument("--build", action="store_true", help="生成本地候选 PNG")
    parser.add_argument("--preview", action="store_true", help="生成十倍静态预览到 .work")
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
        print(f"P02 贴图构建失败：{error}", file=sys.stderr)
        raise SystemExit(1)
