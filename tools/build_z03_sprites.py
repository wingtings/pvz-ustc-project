#!/usr/bin/env python3
"""Build the three Z03 blue exercise-book helmet stages from verified cone sprites."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pak_assets
import png_assets


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "assets-src" / "game" / "z03"
PREVIEW_PATH = ROOT / ".work" / "previews" / "z03-book-stages-8x.png"


@dataclass(frozen=True)
class StageSpec:
    output_name: str
    original_sha256: str
    top_y: int
    page_top: int
    damage: int


SPECS = {
    "reanim/Zombie_cone1.png": StageSpec(
        "Zombie_cone1.png",
        "F534854721CDC25FE57DCB4862CC5FB583F3F6F282192A9E8378BD4960988B79",
        5,
        35,
        0,
    ),
    "reanim/Zombie_cone2.png": StageSpec(
        "Zombie_cone2.png",
        "2D2D522BFCF885B9EB07A5E015F627CB71D863DC88F4D7DD0908E9BBA1A38C26",
        8,
        31,
        1,
    ),
    "reanim/Zombie_cone3.png": StageSpec(
        "Zombie_cone3.png",
        "51FB258E0974447418AE845A2284DE55957DD8199D18AB7D1DF3F3CAA36FA30C",
        10,
        29,
        2,
    ),
}

INK = (8, 25, 55)
SPINE = (13, 51, 111)
COVER = (26, 81, 158)
COVER_LIGHT = (48, 119, 194)
COVER_SHADOW = (17, 55, 112)
PAGE = (229, 224, 205)
PAGE_SHADOW = (174, 174, 160)
LABEL = (236, 237, 224)
BOOKMARK = (187, 42, 48)


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
        raise ValueError(f"main.pak 缺少 Z03 原件：{', '.join(missing)}")
    for target, payload in result.items():
        spec = SPECS[target]
        actual_hash = sha256(payload)
        if actual_hash != spec.original_sha256:
            raise ValueError(f"{target} 原件哈希不匹配：{actual_hash}")
        image = png_assets.decode_rgba8(payload)
        if (image.width, image.height) != (59, 57):
            raise ValueError(f"{target} 原件画布不匹配：{image.width}×{image.height}")
    return result


def pixel_offset(width: int, x: int, y: int) -> int:
    return (y * width + x) * 4


def rgba_at(
    pixels: bytearray | bytes, width: int, x: int, y: int
) -> tuple[int, int, int, int]:
    start = pixel_offset(width, x, y)
    return tuple(pixels[start : start + 4])  # type: ignore[return-value]


def set_rgba(
    pixels: bytearray,
    width: int,
    x: int,
    y: int,
    color: tuple[int, int, int],
    alpha: int = 255,
) -> None:
    if 0 <= x < width and 0 <= y < len(pixels) // (width * 4):
        start = pixel_offset(width, x, y)
        pixels[start : start + 4] = bytes((*color, alpha))


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


def on_segment(
    point: tuple[int, int], start: tuple[int, int], end: tuple[int, int]
) -> bool:
    x, y = point
    x0, y0 = start
    x1, y1 = end
    cross = (x - x0) * (y1 - y0) - (y - y0) * (x1 - x0)
    return (
        cross == 0
        and min(x0, x1) <= x <= max(x0, x1)
        and min(y0, y1) <= y <= max(y0, y1)
    )


def inside_polygon(point: tuple[int, int], polygon: tuple[tuple[int, int], ...]) -> bool:
    if any(
        on_segment(point, polygon[index], polygon[(index + 1) % len(polygon)])
        for index in range(len(polygon))
    ):
        return True
    x, y = point
    inside = False
    previous = polygon[-1]
    for current in polygon:
        x0, y0 = previous
        x1, y1 = current
        if (y0 > y) != (y1 > y):
            intersection = (x1 - x0) * (y - y0) / (y1 - y0) + x0
            if x < intersection:
                inside = not inside
        previous = current
    return inside


def book_polygon(spec: StageSpec) -> tuple[tuple[int, int], ...]:
    if spec.damage == 0:
        return ((14, 5), (51, 10), (47, 42), (8, 37))
    if spec.damage == 1:
        return ((14, 8), (49, 12), (47, 42), (8, 38))
    return ((15, 10), (47, 15), (47, 42), (8, 39))


def damage_cut(spec: StageSpec, x: int, y: int) -> bool:
    if spec.damage == 1:
        return (
            (x >= 44 and y <= 16)
            or (x >= 41 and y <= 13 and (x + y) % 2 == 0)
        )
    if spec.damage == 2:
        return (
            (x >= 40 and y <= 22)
            or (x <= 15 and y <= 17)
            or (27 <= x <= 31 and y <= 14 + (x % 2))
        )
    return False


def page_boundary(spec: StageSpec, x: int) -> int:
    return spec.page_top + max(0, x - 10) // 13


def is_outline(
    x: int,
    y: int,
    polygon: tuple[tuple[int, int], ...],
    spec: StageSpec,
) -> bool:
    for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
        if not inside_polygon(neighbor, polygon) or damage_cut(spec, *neighbor):
            return True
    return False


def draw_cover(pixels: bytearray, image: png_assets.RgbaPng, spec: StageSpec) -> None:
    polygon = book_polygon(spec)
    for y in range(43):
        for x in range(image.width):
            if not inside_polygon((x, y), polygon) or damage_cut(spec, x, y):
                continue
            if is_outline(x, y, polygon, spec):
                color = INK
            elif y >= page_boundary(spec, x):
                color = PAGE_SHADOW if (y + x) % 4 == 0 else PAGE
            elif x <= 13:
                color = SPINE
            elif y <= spec.top_y + 5:
                color = COVER_LIGHT
            else:
                color = COVER
            set_rgba(pixels, image.width, x, y, color)

    # Page lines remain readable after battle-scale reduction.
    for y in range(spec.page_top + 2, 43, 3):
        for x in range(12, 46):
            if (
                inside_polygon((x, y), polygon)
                and not damage_cut(spec, x, y)
                and y >= page_boundary(spec, x)
            ):
                set_rgba(pixels, image.width, x, y, PAGE_SHADOW)


def draw_label(pixels: bytearray, image: png_assets.RgbaPng, spec: StageSpec) -> None:
    if spec.damage == 0:
        label = ((20, 16), (40, 19), (38, 30), (18, 27))
    elif spec.damage == 1:
        label = ((19, 17), (38, 20), (36, 30), (17, 27))
    else:
        label = ((20, 18), (34, 20), (33, 29), (18, 27))

    cover = book_polygon(spec)
    for y in range(15, 31):
        for x in range(16, 42):
            if (
                inside_polygon((x, y), label)
                and inside_polygon((x, y), cover)
                and not damage_cut(spec, x, y)
            ):
                edge = any(
                    not inside_polygon(neighbor, label)
                    for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
                )
                set_rgba(pixels, image.width, x, y, INK if edge else LABEL)

    glyph = (
        "1110",
        "1001",
        "1001",
        "1110",
        "1001",
        "1001",
        "1110",
    )
    glyph_left = 24 if spec.damage < 2 else 22
    glyph_top = 19 if spec.damage == 0 else 20
    for row, bits in enumerate(glyph):
        for column, bit in enumerate(bits):
            x = glyph_left + column
            y = glyph_top + row
            if (
                bit == "1"
                and inside_polygon((x, y), label)
                and not damage_cut(spec, x, y)
            ):
                set_rgba(pixels, image.width, x, y, COVER_SHADOW)

    # A red bookmark survives as a small correction-mark cue without
    # competing with the blue-and-white book silhouette.
    if spec.damage < 2:
        for y in range(31, 39):
            x = 33 + (y - 31) // 4
            if inside_polygon((x, y), cover) and not damage_cut(spec, x, y):
                set_rgba(pixels, image.width, x, y, BOOKMARK)


def repaint_contact_band(
    pixels: bytearray, image: png_assets.RgbaPng, spec: StageSpec
) -> None:
    page_bottom = 47 + spec.damage
    for y in range(43, image.height):
        for x in range(image.width):
            if rgba_at(image.pixels, image.width, x, y)[3] == 0:
                continue
            if y <= page_bottom:
                color = PAGE_SHADOW if (x + y) % 5 == 0 else PAGE
            elif y >= 53:
                color = INK
            else:
                color = COVER_SHADOW
            set_rgb_preserve_alpha(pixels, image.width, x, y, color)


def add_damage_details(
    pixels: bytearray, image: png_assets.RgbaPng, spec: StageSpec
) -> None:
    if spec.damage == 0:
        return
    cover = book_polygon(spec)
    tears = [
        ((42, 18), (37, 24)),
        ((37, 24), (42, 28)),
    ]
    if spec.damage == 2:
        tears.extend(
            [
                ((16, 18), (21, 22)),
                ((21, 22), (17, 27)),
                ((30, 15), (32, 21)),
                ((32, 21), (29, 25)),
            ]
        )
    for start, end in tears:
        x0, y0 = start
        x1, y1 = end
        steps = max(abs(x1 - x0), abs(y1 - y0))
        for step in range(steps + 1):
            x = round(x0 + (x1 - x0) * step / steps)
            y = round(y0 + (y1 - y0) * step / steps)
            if inside_polygon((x, y), cover) and not damage_cut(spec, x, y):
                set_rgba(pixels, image.width, x, y, PAGE_SHADOW if step % 2 else INK)


def build_stage(original: bytes, spec: StageSpec) -> bytes:
    image = png_assets.decode_rgba8(original)
    pixels = bytearray(image.pixels)

    # Rebuild only the upper silhouette. The lower contact band keeps the
    # source Alpha byte-for-byte so the shared anim_cone anchor remains stable.
    for y in range(43):
        for x in range(image.width):
            set_rgba(pixels, image.width, x, y, (0, 0, 0), 0)

    draw_cover(pixels, image, spec)
    draw_label(pixels, image, spec)
    add_damage_details(pixels, image, spec)
    repaint_contact_band(pixels, image, spec)
    return png_assets.encode_rgba8(
        png_assets.RgbaPng(image.width, image.height, bytes(pixels))
    )


def build_all() -> dict[str, bytes]:
    originals = pak_payloads()
    return {
        spec.output_name: build_stage(originals[target], spec)
        for target, spec in SPECS.items()
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


def blend(
    canvas: bytearray,
    canvas_width: int,
    x: int,
    y: int,
    source: tuple[int, int, int, int],
) -> None:
    red, green, blue, alpha = source
    if alpha == 0:
        return
    start = pixel_offset(canvas_width, x, y)
    old_red, old_green, old_blue, _ = canvas[start : start + 4]
    inverse = 255 - alpha
    result = (
        (red * alpha + old_red * inverse) // 255,
        (green * alpha + old_green * inverse) // 255,
        (blue * alpha + old_blue * inverse) // 255,
        255,
    )
    canvas[start : start + 4] = bytes(result)


def preview(candidates: dict[str, bytes]) -> bytes:
    scale = 8
    gap = 3 * scale
    padding = 2 * scale
    images = [
        nearest(png_assets.decode_rgba8(candidates[spec.output_name]), scale)
        for spec in SPECS.values()
    ]
    width = padding * 2 + sum(image.width for image in images) + gap * (len(images) - 1)
    height = padding * 2 + max(image.height for image in images)
    canvas = bytearray(width * height * 4)
    for y in range(height):
        for x in range(width):
            shade = (40, 44, 52) if (x // 16 + y // 16) % 2 == 0 else (59, 64, 74)
            start = pixel_offset(width, x, y)
            canvas[start : start + 4] = bytes((*shade, 255))
    left = padding
    for image in images:
        for y in range(image.height):
            for x in range(image.width):
                blend(
                    canvas,
                    width,
                    left + x,
                    padding + y,
                    rgba_at(image.pixels, image.width, x, y),
                )
        left += image.width + gap
    return png_assets.encode_rgba8(png_assets.RgbaPng(width, height, bytes(canvas)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只计算并报告确定性哈希")
    parser.add_argument("--build", action="store_true", help="生成本地候选 PNG")
    parser.add_argument("--preview", action="store_true", help="生成八倍三档预览到 .work")
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
        print(f"Z03 贴图构建失败：{error}", file=sys.stderr)
        raise SystemExit(1)
