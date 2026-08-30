#!/usr/bin/env python3
"""Tests for the first P02 focused-face and note-petal contracts."""

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


HEAD = (
    "assets-src/game/p02/SunFlower_head.contract.json",
    "reanim/SunFlower_head.png",
    1892,
)
PETALS = (
    (
        "assets-src/game/p02/SunFlower_toppetals.contract.json",
        "reanim/SunFlower_toppetals.png",
        137,
    ),
    (
        "assets-src/game/p02/SunFlower_bottompetals.contract.json",
        "reanim/SunFlower_bottompetals.png",
        211,
    ),
)


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


class SunflowerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        decoded, entries = pak_assets.parse_pak(pak_assets.PAK_PATH)
        payloads = {
            builder.normalize_name(entry.name): builder.entry_payload(decoded, entry)
            for entry in entries
        }
        head_contract_path, head_target, head_visible = HEAD
        head_original = payloads[head_target]
        cls.head = (
            builder.load_asset_contract(head_contract_path),
            head_target,
            head_original,
            png_assets.decode_rgba8(head_original),
            head_visible,
        )
        cls.petals = []
        for contract_path, target, visible in PETALS:
            original = payloads[target]
            cls.petals.append(
                (
                    builder.load_asset_contract(contract_path),
                    target,
                    original,
                    png_assets.decode_rgba8(original),
                    visible,
                )
            )

    @staticmethod
    def focused_head_pixels(image: png_assets.RgbaPng) -> bytearray:
        pixels = bytearray(image.pixels)
        for y in range(9, 12):
            for x in list(range(18, 26)) + list(range(37, 45)):
                old = png_assets.pixel(image, x, y)
                if old[3] > 0:
                    set_pixel(pixels, image.width, x, y, (35, 25, 20, old[3]))
        for y in range(27, 32):
            for x in range(45, 51):
                old = png_assets.pixel(image, x, y)
                if old[3] > 0:
                    set_pixel(pixels, image.width, x, y, (35, 100, 160, old[3]))
        return pixels

    @staticmethod
    def note_petal_pixels(image: png_assets.RgbaPng) -> bytearray:
        pixels = bytearray(image.pixels)
        for y in range(image.height):
            for x in range(image.width):
                old = png_assets.pixel(image, x, y)
                if old[3] == 0:
                    continue
                color = (220, 225, 220, old[3]) if (x + y) % 3 == 0 else (35, 105, 165, old[3])
                set_pixel(pixels, image.width, x, y, color)
        return pixels

    def test_all_contract_baselines_match_pak_originals(self) -> None:
        for contract, target, original, image, visible in [self.head, *self.petals]:
            with self.subTest(target=target):
                validated = builder.validate_contract_baseline(
                    contract, target, original
                )
                self.assertEqual(
                    (validated.width, validated.height),
                    (image.width, image.height),
                )
                self.assertEqual(png_assets.visible_pixel_count(validated), visible)

    def test_focused_head_fixture_passes(self) -> None:
        contract, target, original, image, _ = self.head
        candidate = encode_rgba8(image, bytes(self.focused_head_pixels(image)))
        builder.validate_replacement_contract(
            contract, target, original, candidate
        )

    def test_palette_petals_can_be_replaced_by_rgba_candidates(self) -> None:
        for contract, target, original, image, _ in self.petals:
            with self.subTest(target=target):
                candidate = encode_rgba8(
                    image, bytes(self.note_petal_pixels(image))
                )
                builder.validate_replacement_contract(
                    contract, target, original, candidate
                )

    def test_eye_core_change_is_rejected(self) -> None:
        contract, target, original, image, _ = self.head
        pixels = self.focused_head_pixels(image)
        old = png_assets.pixel(image, 21, 16)
        self.assertGreater(old[3], 0)
        set_pixel(pixels, image.width, 21, 16, (255, 0, 255, old[3]))
        candidate = encode_rgba8(image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "受保护区域"):
            builder.validate_replacement_contract(
                contract, target, original, candidate
            )

    def test_missing_blue_study_cue_is_rejected(self) -> None:
        contract, target, original, image, _ = self.head
        pixels = self.focused_head_pixels(image)
        for y in range(27, 32):
            for x in range(45, 51):
                old = png_assets.pixel(image, x, y)
                if old[3] > 0:
                    set_pixel(pixels, image.width, x, y, (130, 90, 45, old[3]))
        candidate = encode_rgba8(image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "ustc-blue-study-cue"):
            builder.validate_replacement_contract(
                contract, target, original, candidate
            )

    def test_single_color_petals_are_rejected(self) -> None:
        contract, target, original, image, _ = self.petals[0]
        pixels = bytearray(image.pixels)
        for y in range(image.height):
            for x in range(image.width):
                old = png_assets.pixel(image, x, y)
                if old[3] > 0:
                    set_pixel(pixels, image.width, x, y, (35, 105, 165, old[3]))
        candidate = encode_rgba8(image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "white-paper"):
            builder.validate_replacement_contract(
                contract, target, original, candidate
            )


if __name__ == "__main__":
    unittest.main()
