#!/usr/bin/env python3
"""Build Z01 worn-calculus-paper body parts from a verified original PAK."""

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
OUTPUT_DIR = ROOT / "assets-src" / "game" / "z01"
OUTPUT_PATH = OUTPUT_DIR / "Zombie_body.png"
PREVIEW_PATH = ROOT / ".work" / "previews" / "z01-body-before-after-10x.png"
SLEEVE_PREVIEW_PATH = (
    ROOT / ".work" / "previews" / "z01-sleeves-before-after-12x.png"
)
TARGET = "reanim/Zombie_body.png"
ORIGINAL_SHA256 = "7A455D5AA3BC3DFCFBD5C8D7E16C01948BB3EE3AB210894B446D8ADD04CE194D"
ASSET_SPECS = {
    "Zombie_body.png": (
        TARGET,
        ORIGINAL_SHA256,
        (53, 63),
    ),
    "Zombie_innerarm_upper.png": (
        "reanim/Zombie_innerarm_upper.png",
        "343CA5D76242394B329F49F3FA82C2AC1EF478504CF5B59B54090E9F7324DFB6",
        (15, 25),
    ),
    "Zombie_outerarm_upper.png": (
        "reanim/Zombie_outerarm_upper.png",
        "27B13FB81C6835F66F90CC51712F1622A6D955EAC91301FAC15A7E7BC2D8634B",
        (17, 35),
    ),
    "Zombie_outerarm_upper2.png": (
        "reanim/Zombie_outerarm_upper2.png",
        "5D1363D989A5F988ACFE50C49188971D786FFA506CCF43BF30120187A1A72ADC",
        (17, 35),
    ),
}
SLEEVE_NAMES = tuple(name for name in ASSET_SPECS if name != "Zombie_body.png")

PAPER_DARK = (166, 152, 126)
PAPER_MID = (198, 184, 153)
PAPER_LIGHT = (224, 211, 182)
PENCIL = (104, 104, 101)
PENCIL_LIGHT = (132, 130, 124)
CORRECTION_RED = (178, 55, 50)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pak_payloads(pak_path: Path = pak_assets.PAK_PATH) -> dict[str, bytes]:
    decoded, entries = pak_assets.parse_pak(pak_path)
    expected_by_target = {
        target: (name, expected_hash, canvas)
        for name, (target, expected_hash, canvas) in ASSET_SPECS.items()
    }
    found: dict[str, bytes] = {}
    for entry in entries:
        target = pak_assets.normalize_name(entry.name)
        spec = expected_by_target.get(target)
        if spec is None:
            continue
        name, expected_hash, canvas = spec
        payload = decoded[entry.offset : entry.offset + entry.size]
        actual_hash = sha256(payload)
        if actual_hash != expected_hash:
            raise ValueError(f"{target} 原件哈希不匹配：{actual_hash}")
        image = png_assets.decode_rgba8(payload)
        if (image.width, image.height) != canvas:
            raise ValueError(
                f"{target} 原件画布不匹配：{image.width}×{image.height}"
            )
        found[name] = payload
    missing = [name for name in ASSET_SPECS if name not in found]
    if missing:
        raise ValueError(f"{pak_path} 缺少 Z01 原件：{', '.join(missing)}")
    return {name: found[name] for name in ASSET_SPECS}


def pak_payload(pak_path: Path = pak_assets.PAK_PATH) -> bytes:
    """Compatibility wrapper for tests and callers that only need the body."""

    return pak_payloads(pak_path)["Zombie_body.png"]


def pixel_offset(width: int, x: int, y: int) -> int:
    return (y * width + x) * 4


def rgba_at(
    pixels: bytearray | bytes, width: int, x: int, y: int
) -> tuple[int, int, int, int]:
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


def protected_dark(rgba: tuple[int, int, int, int]) -> bool:
    red, green, blue, alpha = rgba
    return alpha >= 80 and red <= 60 and green <= 55 and blue <= 50


def protected_sleeve_ink(rgba: tuple[int, int, int, int]) -> bool:
    red, green, blue, alpha = rgba
    return alpha >= 80 and red <= 35 and green <= 30 and blue <= 25


def paper_surface(rgba: tuple[int, int, int, int]) -> bool:
    red, green, blue, alpha = rgba
    original_tie = (
        red >= 70 and red * 2 >= green * 3 and red * 10 >= blue * 14
    )
    return (
        alpha > 0
        and not protected_dark(rgba)
        and not original_tie
        and red >= 55
        and red >= green + 5
        and green >= blue + 2
    )


def sleeve_surface(rgba: tuple[int, int, int, int]) -> bool:
    red, green, blue, alpha = rgba
    return (
        alpha > 0
        and not protected_sleeve_ink(rgba)
        and red >= 45
        and red >= green + 6
        and green >= blue + 6
    )


def paper_color(rgba: tuple[int, int, int, int]) -> tuple[int, int, int]:
    red, green, blue, _ = rgba
    luminance = (red * 30 + green * 59 + blue * 11) // 100
    if luminance < 82:
        return PAPER_DARK
    if luminance < 128:
        return PAPER_MID
    return PAPER_LIGHT


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


def paint_mark(
    pixels: bytearray,
    image: png_assets.RgbaPng,
    paper_mask: set[tuple[int, int]],
    x: int,
    y: int,
    color: tuple[int, int, int],
) -> None:
    if (x, y) in paper_mask:
        set_rgb_preserve_alpha(pixels, image.width, x, y, color)


def paint_line(
    pixels: bytearray,
    image: png_assets.RgbaPng,
    paper_mask: set[tuple[int, int]],
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
    thickness: int = 1,
) -> None:
    for x, y in line_points(*start, *end):
        for offset_y in range(thickness):
            paint_mark(pixels, image, paper_mask, x, y + offset_y, color)


def paint_glyph(
    pixels: bytearray,
    image: png_assets.RgbaPng,
    paper_mask: set[tuple[int, int]],
    left: int,
    top: int,
    rows: tuple[str, ...],
    color: tuple[int, int, int],
) -> None:
    for y, row in enumerate(rows):
        for x, bit in enumerate(row):
            if bit == "1":
                paint_mark(pixels, image, paper_mask, left + x, top + y, color)


def repaint_jacket(
    pixels: bytearray, image: png_assets.RgbaPng
) -> set[tuple[int, int]]:
    paper_mask: set[tuple[int, int]] = set()
    for y in range(image.height):
        for x in range(image.width):
            original = rgba_at(image.pixels, image.width, x, y)
            if not paper_surface(original):
                continue
            paper_mask.add((x, y))
            set_rgb_preserve_alpha(
                pixels, image.width, x, y, paper_color(original)
            )
    return paper_mask


def repaint_sleeve(
    pixels: bytearray, image: png_assets.RgbaPng
) -> set[tuple[int, int]]:
    paper_mask: set[tuple[int, int]] = set()
    for y in range(image.height):
        for x in range(image.width):
            original = rgba_at(image.pixels, image.width, x, y)
            if not sleeve_surface(original):
                continue
            paper_mask.add((x, y))
            set_rgb_preserve_alpha(
                pixels, image.width, x, y, paper_color(original)
            )
    return paper_mask


def add_pencil_work(
    pixels: bytearray,
    image: png_assets.RgbaPng,
    paper_mask: set[tuple[int, int]],
) -> None:
    # Faint ruled lines make the jacket read as a used problem sheet at game scale.
    for y in (12, 18, 24, 30, 36, 42, 48):
        for x in range(18, 49):
            if (x + y) % 3 != 0:
                paint_mark(pixels, image, paper_mask, x, y, PENCIL_LIGHT)

    glyphs = {
        "L": ("100", "100", "100", "100", "111"),
        "I": ("111", "010", "010", "010", "111"),
        "M": ("10001", "11011", "10101", "10001", "10001"),
        "X": ("101", "101", "010", "101", "101"),
        "0": ("111", "101", "101", "101", "111"),
    }
    left = 24
    for glyph, width in (("L", 3), ("I", 3), ("M", 5)):
        paint_glyph(
            pixels, image, paper_mask, left, 15, glyphs[glyph], PENCIL
        )
        left += width + 1
    paint_line(pixels, image, paper_mask, (25, 27), (40, 27), PENCIL)
    paint_line(pixels, image, paper_mask, (29, 32), (37, 32), PENCIL)
    paint_glyph(pixels, image, paper_mask, 25, 34, glyphs["X"], PENCIL)
    paint_glyph(pixels, image, paper_mask, 40, 34, glyphs["0"], PENCIL)
    paint_line(pixels, image, paper_mask, (33, 36), (38, 36), PENCIL)
    paint_line(pixels, image, paper_mask, (36, 34), (39, 36), PENCIL)

    # Keep the pencil count comfortably above the contract floor without
    # turning the tiny sprite into uniform noise.
    pencil_pixels = 0
    for x, y in sorted(paper_mask, key=lambda point: (point[1], point[0])):
        red, green, blue, alpha = rgba_at(pixels, image.width, x, y)
        if (
            alpha >= 140
            and 75 <= red <= 155
            and 75 <= green <= 155
            and 70 <= blue <= 150
        ):
            pencil_pixels += 1
    if pencil_pixels < 135:
        for x, y in sorted(paper_mask, key=lambda point: (point[1], point[0])):
            if (x * 7 + y * 11) % 19 != 0:
                continue
            paint_mark(pixels, image, paper_mask, x, y, PENCIL_LIGHT)
            pencil_pixels += 1
            if pencil_pixels >= 135:
                break


def add_corrections(
    pixels: bytearray,
    image: png_assets.RgbaPng,
    paper_mask: set[tuple[int, int]],
) -> None:
    # One large tick and one underlined answer survive the 53×63 battle scale.
    paint_line(
        pixels,
        image,
        paper_mask,
        (34, 22),
        (38, 27),
        CORRECTION_RED,
        thickness=2,
    )
    paint_line(
        pixels,
        image,
        paper_mask,
        (38, 27),
        (47, 16),
        CORRECTION_RED,
        thickness=2,
    )
    paint_line(
        pixels,
        image,
        paper_mask,
        (25, 44),
        (46, 44),
        CORRECTION_RED,
        thickness=2,
    )


def add_sleeve_work(
    pixels: bytearray,
    image: png_assets.RgbaPng,
    paper_mask: set[tuple[int, int]],
    name: str,
) -> None:
    red_targets = {
        "Zombie_innerarm_upper.png": 4,
        "Zombie_outerarm_upper.png": 8,
        "Zombie_outerarm_upper2.png": 7,
    }
    pencil_targets = {
        "Zombie_innerarm_upper.png": 12,
        "Zombie_outerarm_upper.png": 30,
        "Zombie_outerarm_upper2.png": 24,
    }
    slash = {
        "Zombie_innerarm_upper.png": ((4, 6), (10, 12)),
        "Zombie_outerarm_upper.png": ((6, 10), (14, 16)),
        "Zombie_outerarm_upper2.png": ((5, 8), (13, 14)),
    }
    paint_line(
        pixels,
        image,
        paper_mask,
        slash[name][0],
        slash[name][1],
        CORRECTION_RED,
    )

    red_count = sum(
        rgba_at(pixels, image.width, x, y)[:3] == CORRECTION_RED
        for x, y in paper_mask
    )
    for x, y in sorted(paper_mask, key=lambda point: (point[1], point[0])):
        if red_count >= red_targets[name]:
            break
        if (x * 5 + y * 7) % 11:
            continue
        paint_mark(pixels, image, paper_mask, x, y, CORRECTION_RED)
        red_count += 1

    for y in range(3, image.height, 6):
        row = sorted(x for x, py in paper_mask if py == y)
        for index, x in enumerate(row):
            if index % 2 == 0:
                paint_mark(pixels, image, paper_mask, x, y, PENCIL_LIGHT)

    pencil_count = sum(
        rgba_at(pixels, image.width, x, y)[:3] in (PENCIL, PENCIL_LIGHT)
        for x, y in paper_mask
    )
    for x, y in sorted(paper_mask, key=lambda point: (point[1], point[0])):
        if pencil_count >= pencil_targets[name]:
            break
        current = rgba_at(pixels, image.width, x, y)[:3]
        if current == CORRECTION_RED or (x * 7 + y * 11) % 13:
            continue
        paint_mark(pixels, image, paper_mask, x, y, PENCIL_LIGHT)
        pencil_count += 1


def build_body(original: bytes) -> bytes:
    image = png_assets.decode_rgba8(original)
    pixels = bytearray(image.pixels)
    paper_mask = repaint_jacket(pixels, image)
    add_pencil_work(pixels, image, paper_mask)
    add_corrections(pixels, image, paper_mask)
    return png_assets.encode_rgba8(
        png_assets.RgbaPng(image.width, image.height, bytes(pixels))
    )


def build_sleeve(original: bytes, name: str) -> bytes:
    image = png_assets.decode_rgba8(original)
    pixels = bytearray(image.pixels)
    paper_mask = repaint_sleeve(pixels, image)
    add_sleeve_work(pixels, image, paper_mask, name)
    return png_assets.encode_rgba8(
        png_assets.RgbaPng(image.width, image.height, bytes(pixels))
    )


def build_all(pak_path: Path = pak_assets.PAK_PATH) -> dict[str, bytes]:
    originals = pak_payloads(pak_path)
    candidates = {"Zombie_body.png": build_body(originals["Zombie_body.png"])}
    for name in SLEEVE_NAMES:
        candidates[name] = build_sleeve(originals[name], name)
    return candidates


def atomic_write(path: Path, payload: bytes, force: bool) -> None:
    if path.exists() and path.read_bytes() == payload:
        print(f"已验证：{path.relative_to(ROOT)}")
        return
    if path.exists() and not force:
        raise ValueError(f"输出已存在且内容不同；如需替换请使用 --force：{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
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
            pixels[destination : destination + 4] = image.pixels[
                source : source + 4
            ]
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
    canvas[start : start + 4] = bytes(
        (
            (red * alpha + old_red * inverse) // 255,
            (green * alpha + old_green * inverse) // 255,
            (blue * alpha + old_blue * inverse) // 255,
            255,
        )
    )


def preview(original: bytes, candidate: bytes) -> bytes:
    scale = 10
    gap = 4 * scale
    padding = 2 * scale
    images = [
        nearest(png_assets.decode_rgba8(payload), scale)
        for payload in (original, candidate)
    ]
    width = padding * 2 + sum(image.width for image in images) + gap
    height = padding * 2 + max(image.height for image in images)
    canvas = bytearray(width * height * 4)
    for y in range(height):
        for x in range(width):
            shade = (
                (40, 44, 52)
                if (x // 16 + y // 16) % 2 == 0
                else (59, 64, 74)
            )
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
    return png_assets.encode_rgba8(
        png_assets.RgbaPng(width, height, bytes(canvas))
    )


def sleeve_preview(
    originals: dict[str, bytes], candidates: dict[str, bytes]
) -> bytes:
    scale = 12
    gap = 2 * scale
    padding = 2 * scale
    rows: list[tuple[png_assets.RgbaPng, png_assets.RgbaPng]] = []
    for name in SLEEVE_NAMES:
        rows.append(
            (
                nearest(png_assets.decode_rgba8(originals[name]), scale),
                nearest(png_assets.decode_rgba8(candidates[name]), scale),
            )
        )
    width = max(left.width + gap + right.width for left, right in rows)
    width += padding * 2
    height = sum(max(left.height, right.height) for left, right in rows)
    height += gap * (len(rows) - 1) + padding * 2
    canvas = bytearray(width * height * 4)
    for y in range(height):
        for x in range(width):
            shade = (
                (40, 44, 52)
                if (x // 16 + y // 16) % 2 == 0
                else (59, 64, 74)
            )
            start = pixel_offset(width, x, y)
            canvas[start : start + 4] = bytes((*shade, 255))
    top = padding
    for left_image, right_image in rows:
        for image, x_offset in (
            (left_image, padding),
            (right_image, padding + left_image.width + gap),
        ):
            for y in range(image.height):
                for x in range(image.width):
                    blend(
                        canvas,
                        width,
                        x_offset + x,
                        top + y,
                        rgba_at(image.pixels, image.width, x, y),
                    )
        top += max(left_image.height, right_image.height) + gap
    return png_assets.encode_rgba8(
        png_assets.RgbaPng(width, height, bytes(canvas))
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只计算并报告确定性哈希")
    parser.add_argument("--build", action="store_true", help="生成本地候选 PNG")
    parser.add_argument("--preview", action="store_true", help="生成十倍前后对照到 .work")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--pak",
        type=Path,
        default=pak_assets.PAK_PATH,
        help="经过基线哈希验证的原版 main.pak 路径",
    )
    args = parser.parse_args()
    if not (args.check or args.build or args.preview):
        parser.error("至少选择 --check、--build 或 --preview 之一")

    originals = pak_payloads(args.pak)
    candidates = {"Zombie_body.png": build_body(originals["Zombie_body.png"])}
    for name in SLEEVE_NAMES:
        candidates[name] = build_sleeve(originals[name], name)
    for name, candidate in candidates.items():
        print(f"{name}: {sha256(candidate)}")
    if args.build:
        for name, candidate in candidates.items():
            atomic_write(OUTPUT_DIR / name, candidate, args.force)
    if args.preview:
        atomic_write(
            PREVIEW_PATH,
            preview(originals["Zombie_body.png"], candidates["Zombie_body.png"]),
            args.force,
        )
        atomic_write(
            SLEEVE_PREVIEW_PATH,
            sleeve_preview(originals, candidates),
            args.force,
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"Z01 贴图构建失败：{error}", file=sys.stderr)
        raise SystemExit(1)
