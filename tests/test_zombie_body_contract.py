#!/usr/bin/env python3
"""Tests for the shared Z01 worn-calculus-paper body contract."""

from __future__ import annotations

import struct
import sys
import unittest
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_pak_overlay as builder  # noqa: E402
import pak_assets  # noqa: E402
import png_assets  # noqa: E402


CONTRACT_PATH = "assets-src/game/z01/Zombie_body.contract.json"
TARGET = "reanim/Zombie_body.png"


def _chunk(name: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(name + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + name + payload + struct.pack(">I", checksum)


def encode_rgba8(image: png_assets.RgbaPng, pixels: bytes) -> bytes:
    stride = image.width * 4
    rows = b"".join(
        b"\x00" + pixels[row * stride : (row + 1) * stride]
        for row in range(image.height)
    )
    header = struct.pack(">IIBBBBB", image.width, image.height, 8, 6, 0, 0, 0)
    return (
        png_assets.PNG_SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(rows, level=9))
        + _chunk(b"IEND", b"")
    )


def set_pixel(
    pixels: bytearray,
    width: int,
    x: int,
    y: int,
    rgba: tuple[int, ...],
) -> None:
    offset = (y * width + x) * 4
    pixels[offset : offset + 4] = bytes(rgba)


class ZombieBodyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = builder.load_asset_contract(CONTRACT_PATH)
        decoded, entries = pak_assets.parse_pak(pak_assets.PAK_PATH)
        entry = next(
            item
            for item in entries
            if builder.normalize_name(item.name) == TARGET
        )
        cls.original = builder.entry_payload(decoded, entry)
        cls.image = png_assets.decode_rgba8(cls.original)
        cls.outline_rule = cls.contract["pixelPolicy"]["protectedOriginalColors"][0]

    def paper_body_pixels(self) -> bytearray:
        pixels = bytearray(self.image.pixels)
        for y in range(self.image.height):
            for x in range(self.image.width):
                old = png_assets.pixel(self.image, x, y)
                if old[3] == 0 or builder._matches_color(self.outline_rule, old):
                    continue
                selector = (x + 2 * y) % 17
                if selector == 0:
                    color = (175, 55, 50, old[3])
                elif selector in {1, 2, 3}:
                    color = (115, 115, 110, old[3])
                else:
                    color = (205, 195, 170, old[3])
                set_pixel(pixels, self.image.width, x, y, color)
        return pixels

    def test_contract_baseline_matches_shared_zombie_body(self) -> None:
        image = builder.validate_contract_baseline(
            self.contract, TARGET, self.original
        )
        self.assertEqual((image.width, image.height), (53, 63))
        self.assertEqual(png_assets.visible_pixel_count(image), 1932)

    def test_worn_exam_paper_fixture_passes(self) -> None:
        candidate = encode_rgba8(self.image, bytes(self.paper_body_pixels()))
        builder.validate_replacement_contract(
            self.contract, TARGET, self.original, candidate
        )

    def test_dark_original_outline_change_is_rejected(self) -> None:
        pixels = self.paper_body_pixels()
        protected_coordinate = None
        for y in range(self.image.height):
            for x in range(self.image.width):
                old = png_assets.pixel(self.image, x, y)
                if old[3] > 0 and builder._matches_color(self.outline_rule, old):
                    protected_coordinate = (x, y, old)
                    break
            if protected_coordinate:
                break
        self.assertIsNotNone(protected_coordinate)
        x, y, old = protected_coordinate
        set_pixel(pixels, self.image.width, x, y, (255, 0, 255, old[3]))
        candidate = encode_rgba8(self.image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "dark-ink-outline-and-tears"):
            builder.validate_replacement_contract(
                self.contract, TARGET, self.original, candidate
            )

    def test_missing_correction_red_is_rejected(self) -> None:
        pixels = self.paper_body_pixels()
        for y in range(self.image.height):
            for x in range(self.image.width):
                offset = (y * self.image.width + x) * 4
                red, green, blue, alpha = pixels[offset : offset + 4]
                if alpha > 0 and red >= 145 and green <= 105 and blue <= 95:
                    set_pixel(pixels, self.image.width, x, y, (205, 195, 170, alpha))
        candidate = encode_rgba8(self.image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "correction-red"):
            builder.validate_replacement_contract(
                self.contract, TARGET, self.original, candidate
            )

    def test_missing_pencil_grey_is_rejected(self) -> None:
        pixels = self.paper_body_pixels()
        for y in range(self.image.height):
            for x in range(self.image.width):
                offset = (y * self.image.width + x) * 4
                red, green, blue, alpha = pixels[offset : offset + 4]
                if (
                    alpha > 0
                    and 75 <= red <= 155
                    and 75 <= green <= 155
                    and 70 <= blue <= 150
                ):
                    set_pixel(pixels, self.image.width, x, y, (205, 195, 170, alpha))
        candidate = encode_rgba8(self.image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "pencil-grey"):
            builder.validate_replacement_contract(
                self.contract, TARGET, self.original, candidate
            )


if __name__ == "__main__":
    unittest.main()
