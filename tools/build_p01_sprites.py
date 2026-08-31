#!/usr/bin/env python3
"""Build the first P01 sprites as deterministic edits on a verified main.pak.

The generated PNGs contain pixels from the original game and are local build
artifacts.  Git keeps this overlay recipe, not the generated derivatives.
"""

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
OUTPUT_ROOT = ROOT / "assets-src" / "game" / "p01"
PREVIEW_PATH = ROOT / ".work" / "previews" / "p01-sprites-10x.png"
PROJECTILE_PREVIEW_PATH = (
    ROOT / ".work" / "previews" / "p01-green-circle-before-after-16x.png"
)

HEAD_TARGET = "reanim/PeaShooter_Head.png"
LEAF_TARGET = "reanim/PeaShooter_frontleaf.png"
PROJECTILE_TARGET = "images/ProjectilePea.png"
HEAD_SHA256 = "89489D1DF066B4C89541455525447220437C5913F0F1E3E850A7A6116F241882"
LEAF_SHA256 = "26CE3AFA0788A624D8A1747DAB2BA51223489A04AED61F08A453C0D073BFBDDD"
PROJECTILE_SHA256 = "24A9BE5E2DB62312BA359B15C367B8A8FB6D1764E4AF3A221D178622BEA7CAA9"

FRAME_DARK = (10, 22, 31)
FRAME_EDGE = (37, 54, 47)
COVER_BLUE = (18, 73, 151, 255)
COVER_LIGHT = (37, 102, 188, 255)
COVER_DARK = (5, 31, 82, 255)
PAGE_CREAM = (244, 232, 203, 255)
TITLE_WHITE = (244, 246, 238, 255)
BOOKMARK_GOLD = (234, 185, 55, 255)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pak_payloads() -> dict[str, bytes]:
    decoded, entries = pak_assets.parse_pak(pak_assets.PAK_PATH)
    wanted = {HEAD_TARGET, LEAF_TARGET, PROJECTILE_TARGET}
    result: dict[str, bytes] = {}
    for entry in entries:
        target = pak_assets.normalize_name(entry.name)
        if target in wanted:
            result[target] = decoded[entry.offset : entry.offset + entry.size]
    missing = sorted(wanted - result.keys())
    if missing:
        raise ValueError(f"main.pak 缺少 P01 原件：{', '.join(missing)}")
    expected = {
        HEAD_TARGET: HEAD_SHA256,
        LEAF_TARGET: LEAF_SHA256,
        PROJECTILE_TARGET: PROJECTILE_SHA256,
    }
    for target, payload in result.items():
        actual = sha256(payload)
        if actual != expected[target]:
            raise ValueError(f"{target} 原件哈希不匹配：{actual}")
    return result


def offset(width: int, x: int, y: int) -> int:
    return (y * width + x) * 4


def rgba_at(pixels: bytearray | bytes, width: int, x: int, y: int) -> tuple[int, int, int, int]:
    start = offset(width, x, y)
    return tuple(pixels[start : start + 4])  # type: ignore[return-value]


def set_rgba(pixels: bytearray, width: int, x: int, y: int, color: tuple[int, int, int, int]) -> None:
    start = offset(width, x, y)
    pixels[start : start + 4] = bytes(color)


def protected_eye_core(x: int, y: int) -> bool:
    return (43 <= x <= 46 and 21 <= y <= 25) or (54 <= x <= 57 and 16 <= y <= 19)


def paint_frame_pixel(
    pixels: bytearray,
    image: png_assets.RgbaPng,
    x: int,
    y: int,
    color: tuple[int, int, int] = FRAME_DARK,
) -> None:
    if not (34 <= x <= 65 and 7 <= y <= 32) or protected_eye_core(x, y):
        return
    _, _, _, alpha = rgba_at(pixels, image.width, x, y)
    if alpha == 0:
        return
    set_rgba(pixels, image.width, x, y, (*color, alpha))


def ellipse_ring(
    pixels: bytearray,
    image: png_assets.RgbaPng,
    center_x: float,
    center_y: float,
    radius_x: float,
    radius_y: float,
) -> None:
    left = int(center_x - radius_x - 1)
    right = int(center_x + radius_x + 1)
    top = int(center_y - radius_y - 1)
    bottom = int(center_y + radius_y + 1)
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            distance = ((x - center_x) / radius_x) ** 2 + ((y - center_y) / radius_y) ** 2
            if 0.70 <= distance <= 1.28:
                edge_color = FRAME_EDGE if distance < 0.82 and (x + y) % 3 == 0 else FRAME_DARK
                paint_frame_pixel(pixels, image, x, y, edge_color)


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


def build_head(original: bytes) -> bytes:
    image = png_assets.decode_rgba8(original)
    if (image.width, image.height) != (70, 65):
        raise ValueError("P01 头部画布不是 70×65")
    pixels = bytearray(image.pixels)

    ellipse_ring(pixels, image, 45.0, 22.0, 6.5, 7.5)
    ellipse_ring(pixels, image, 55.5, 17.5, 5.0, 6.0)
    for x, y in line_points(50, 18, 51, 18):
        paint_frame_pixel(pixels, image, x, y)
    for x, y in line_points(39, 25, 34, 29):
        paint_frame_pixel(pixels, image, x, y)
    for x, y in line_points(60, 15, 65, 13):
        paint_frame_pixel(pixels, image, x, y)

    return png_assets.encode_rgba8(
        png_assets.RgbaPng(image.width, image.height, bytes(pixels))
    )


def point_in_polygon(x: float, y: float, polygon: tuple[tuple[int, int], ...]) -> bool:
    inside = False
    previous_x, previous_y = polygon[-1]
    for current_x, current_y in polygon:
        crosses = (current_y > y) != (previous_y > y)
        if crosses:
            intersection = (previous_x - current_x) * (y - current_y) / (previous_y - current_y) + current_x
            if x < intersection:
                inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


def fill_polygon(
    pixels: bytearray,
    image: png_assets.RgbaPng,
    polygon: tuple[tuple[int, int], ...],
    color: tuple[int, int, int, int],
) -> None:
    left = min(x for x, _ in polygon)
    right = max(x for x, _ in polygon)
    top = min(y for _, y in polygon)
    bottom = max(y for _, y in polygon)
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            if point_in_polygon(x + 0.5, y + 0.5, polygon):
                old = rgba_at(pixels, image.width, x, y)
                set_rgba(pixels, image.width, x, y, (*color[:3], max(old[3], color[3])))


def paint_book_pixel(
    pixels: bytearray,
    image: png_assets.RgbaPng,
    x: int,
    y: int,
    color: tuple[int, int, int, int],
) -> None:
    if not (20 <= x <= 48 and 0 <= y <= 32):
        raise ValueError(f"书本像素越过契约范围：({x}, {y})")
    old = rgba_at(pixels, image.width, x, y)
    set_rgba(pixels, image.width, x, y, (*color[:3], max(old[3], color[3])))


def paint_book_line(
    pixels: bytearray,
    image: png_assets.RgbaPng,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int, int],
) -> None:
    for x, y in line_points(*start, *end):
        paint_book_pixel(pixels, image, x, y, color)


def build_frontleaf(original: bytes) -> bytes:
    image = png_assets.decode_rgba8(original)
    if (image.width, image.height) != (67, 40):
        raise ValueError("P01 前叶画布不是 67×40")
    pixels = bytearray(image.pixels)

    left_cover = ((23, 8), (32, 5), (34, 8), (34, 30), (26, 29), (22, 24))
    right_cover = ((34, 8), (36, 5), (44, 8), (47, 24), (42, 29), (34, 30))
    fill_polygon(pixels, image, left_cover, COVER_BLUE)
    fill_polygon(pixels, image, right_cover, COVER_LIGHT)

    for start, end in (
        ((23, 8), (32, 5)),
        ((32, 5), (34, 8)),
        ((23, 8), (22, 24)),
        ((22, 24), (26, 29)),
        ((26, 29), (34, 30)),
        ((34, 8), (36, 5)),
        ((36, 5), (44, 8)),
        ((44, 8), (47, 24)),
        ((47, 24), (42, 29)),
        ((42, 29), (34, 30)),
        ((34, 8), (34, 30)),
    ):
        paint_book_line(pixels, image, start, end, COVER_DARK)

    paint_book_line(pixels, image, (25, 8), (32, 6), PAGE_CREAM)
    paint_book_line(pixels, image, (25, 9), (32, 7), PAGE_CREAM)
    paint_book_line(pixels, image, (36, 6), (43, 8), PAGE_CREAM)
    paint_book_line(pixels, image, (36, 7), (43, 9), PAGE_CREAM)

    # At combat scale the complete title cannot remain legible.  These compact
    # white strokes retain the visual rhythm of “电磁学千题解” on the blue cover.
    for start, end in (
        ((26, 13), (31, 13)),
        ((26, 16), (31, 16)),
        ((26, 19), (31, 19)),
        ((37, 13), (42, 15)),
        ((37, 17), (42, 19)),
    ):
        paint_book_line(pixels, image, start, end, TITLE_WHITE)
    paint_book_line(pixels, image, (34, 9), (34, 25), BOOKMARK_GOLD)

    return png_assets.encode_rgba8(
        png_assets.RgbaPng(image.width, image.height, bytes(pixels))
    )


def build_projectile(original: bytes) -> bytes:
    """Turn the shared pea projectile into a hand-drawn green ring.

    The original 28×28 canvas and outer antialiased silhouette stay fixed.  A
    small transparent centre makes the design read as a circle rather than a
    pea, while the recoloured rim keeps the original top-left light and
    bottom-right volume.  The shared slot intentionally covers the standard
    Peashooter family; snow and fire projectiles use separate resources.
    """

    image = png_assets.decode_rgba8(original)
    if (image.width, image.height) != (28, 28):
        raise ValueError("P01 绿圈弹丸画布不是 28×28")
    pixels = bytearray(image.pixels)

    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = rgba_at(pixels, image.width, x, y)
            if alpha == 0:
                continue

            # Doubled coordinates keep the half-pixel centre (13.5, 13.5)
            # deterministic without depending on floating-point rounding.
            delta_x = 2 * x - 27
            delta_y = 2 * y - 27
            radius_squared = delta_x * delta_x + delta_y * delta_y
            if radius_squared <= 121:
                set_rgba(pixels, image.width, x, y, (0, 0, 0, 0))
                continue

            luminance = (77 * red + 150 * green + 29 * blue) // 256
            tone = max(0, min(255, (luminance - 20) * 255 // 205))
            ring_red = 18 + tone * 182 // 255
            ring_green = 84 + tone * 161 // 255
            ring_blue = 43 + tone * 86 // 255

            # The inner edge is dark and softly antialiased.  Alpha outside
            # this narrow band stays byte-identical to the original sprite.
            if radius_squared <= 169:
                ring_red, ring_green, ring_blue = (16, 82, 43)
                alpha = max(28, alpha * (radius_squared - 121) // 48)
            elif radius_squared >= 441:
                ring_red = min(ring_red, 38)
                ring_green = min(ring_green, 118)
                ring_blue = min(ring_blue, 62)
            elif (x * 5 + y * 7) % 19 in {0, 1}:
                # Sparse pale flecks give the rim a chalk/hand-drawn texture
                # without changing the collision-sized outer silhouette.
                ring_red = min(226, ring_red + 28)
                ring_green = min(248, ring_green + 24)
                ring_blue = min(164, ring_blue + 22)

            # Two compact upper-left highlights survive at combat scale and
            # retain the volume language of the original PopCap projectile.
            if (x, y) in {
                (8, 7),
                (9, 6),
                (9, 7),
                (10, 6),
                (10, 7),
                (11, 6),
                (7, 8),
                (8, 8),
            }:
                ring_red, ring_green, ring_blue = (218, 246, 158)

            set_rgba(
                pixels,
                image.width,
                x,
                y,
                (ring_red, ring_green, ring_blue, alpha),
            )

    return png_assets.encode_rgba8(
        png_assets.RgbaPng(image.width, image.height, bytes(pixels))
    )


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
        source_y = y // scale
        for x in range(width):
            source_x = x // scale
            source = offset(image.width, source_x, source_y)
            destination = offset(width, x, y)
            pixels[destination : destination + 4] = image.pixels[source : source + 4]
    return png_assets.RgbaPng(width, height, bytes(pixels))


def preview(head: bytes, leaf: bytes) -> bytes:
    scale = 10
    head_image = nearest(png_assets.decode_rgba8(head), scale)
    leaf_image = nearest(png_assets.decode_rgba8(leaf), scale)
    gap = 4 * scale
    width = head_image.width + leaf_image.width + gap
    height = max(head_image.height, leaf_image.height)
    canvas = bytearray(width * height * 4)
    for source_image, left, top in (
        (head_image, 0, 0),
        (leaf_image, head_image.width + gap, (height - leaf_image.height) // 2),
    ):
        for y in range(source_image.height):
            source = y * source_image.width * 4
            destination = ((top + y) * width + left) * 4
            canvas[destination : destination + source_image.width * 4] = source_image.pixels[
                source : source + source_image.width * 4
            ]
    return png_assets.encode_rgba8(png_assets.RgbaPng(width, height, bytes(canvas)))


def projectile_preview(original: bytes, candidate: bytes) -> bytes:
    scale = 16
    originals = nearest(png_assets.decode_rgba8(original), scale)
    candidates = nearest(png_assets.decode_rgba8(candidate), scale)
    gap = 4 * scale
    padding = 2 * scale
    width = originals.width + candidates.width + gap + 2 * padding
    height = max(originals.height, candidates.height) + 2 * padding
    canvas = bytearray(width * height * 4)

    # Opaque checkerboard makes the new transparent centre visible in review.
    tile = 2 * scale
    for y in range(height):
        for x in range(width):
            shade = 70 if (x // tile + y // tile) % 2 == 0 else 98
            set_rgba(canvas, width, x, y, (shade, shade, shade, 255))
    for source_image, left in (
        (originals, padding),
        (candidates, padding + originals.width + gap),
    ):
        for y in range(source_image.height):
            for x in range(source_image.width):
                source_color = rgba_at(source_image.pixels, source_image.width, x, y)
                if source_color[3] == 0:
                    continue
                set_rgba(canvas, width, left + x, padding + y, source_color)
    return png_assets.encode_rgba8(png_assets.RgbaPng(width, height, bytes(canvas)))


def build_all() -> dict[str, bytes]:
    originals = pak_payloads()
    return {
        "PeaShooter_Head.png": build_head(originals[HEAD_TARGET]),
        "PeaShooter_frontleaf.png": build_frontleaf(originals[LEAF_TARGET]),
        "ProjectilePea.png": build_projectile(originals[PROJECTILE_TARGET]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只计算并报告确定性哈希")
    parser.add_argument("--build", action="store_true", help="生成本地候选 PNG")
    parser.add_argument("--preview", action="store_true", help="生成 10 倍静态预览到 .work")
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
        atomic_write(
            PREVIEW_PATH,
            preview(candidates["PeaShooter_Head.png"], candidates["PeaShooter_frontleaf.png"]),
            args.force,
        )
        atomic_write(
            PROJECTILE_PREVIEW_PATH,
            projectile_preview(
                pak_payloads()[PROJECTILE_TARGET], candidates["ProjectilePea.png"]
            ),
            args.force,
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"P01 贴图构建失败：{error}", file=sys.stderr)
        raise SystemExit(1)
