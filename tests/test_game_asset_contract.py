#!/usr/bin/env python3
"""Tests for the P01 pixel-preservation contract."""

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


HEAD_CONTRACT_PATH = "assets-src/game/p01/PeaShooter_Head.contract.json"
HEAD_TARGET = "reanim/PeaShooter_Head.png"
BOOK_CONTRACT_PATH = "assets-src/game/p01/PeaShooter_frontleaf.contract.json"
BOOK_TARGET = "reanim/PeaShooter_frontleaf.png"


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


def set_pixel(pixels: bytearray, width: int, x: int, y: int, rgba: tuple[int, ...]) -> None:
    offset = (y * width + x) * 4
    pixels[offset : offset + 4] = bytes(rgba)


class GameAssetContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = builder.load_asset_contract(HEAD_CONTRACT_PATH)
        decoded, entries = pak_assets.parse_pak(pak_assets.PAK_PATH)
        entry = next(
            item
            for item in entries
            if builder.normalize_name(item.name) == HEAD_TARGET
        )
        cls.original = builder.entry_payload(decoded, entry)
        cls.image = png_assets.decode_rgba8(cls.original)

    def valid_candidate_pixels(self) -> bytearray:
        pixels = bytearray(self.image.pixels)
        policy = self.contract["pixelPolicy"]
        allowed = builder._rect(
            policy["allowedChangeRect"],
            "allowedChangeRect",
            self.image.width,
            self.image.height,
        )
        protected = [
            builder._rect(
                value,
                "protected",
                self.image.width,
                self.image.height,
            )
            for value in policy["protectedRects"]
        ]
        changed = 0
        for y in range(allowed[1], allowed[3] + 1):
            for x in range(allowed[0], allowed[2] + 1):
                if any(builder._inside(x, y, rect) for rect in protected):
                    continue
                old = png_assets.pixel(self.image, x, y)
                if old[3] > 0 and sum(old[:3]) >= 180:
                    set_pixel(pixels, self.image.width, x, y, (0, 0, 0, old[3]))
                    changed += 1
                    if changed == 30:
                        return pixels
        self.fail("测试原件的允许区域内没有 30 个可用亮色像素")

    def test_contract_baseline_matches_pak_original(self) -> None:
        image = builder.validate_contract_baseline(
            self.contract, HEAD_TARGET, self.original
        )
        self.assertEqual((image.width, image.height), (70, 65))
        self.assertEqual(png_assets.visible_pixel_count(image), 3332)

    def test_minimal_dark_glasses_fixture_passes(self) -> None:
        candidate = encode_rgba8(self.image, bytes(self.valid_candidate_pixels()))
        builder.validate_replacement_contract(
            self.contract, HEAD_TARGET, self.original, candidate
        )

    def test_unchanged_original_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "可见改动像素数异常"):
            builder.validate_replacement_contract(
                self.contract, HEAD_TARGET, self.original, self.original
            )

    def test_alpha_change_is_rejected(self) -> None:
        pixels = self.valid_candidate_pixels()
        old = png_assets.pixel(self.image, 40, 15)
        set_pixel(pixels, self.image.width, 40, 15, (*old[:3], 0))
        candidate = encode_rgba8(self.image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "Alpha 蒙版"):
            builder.validate_replacement_contract(
                self.contract, HEAD_TARGET, self.original, candidate
            )

    def test_visible_change_outside_allowed_rect_is_rejected(self) -> None:
        pixels = self.valid_candidate_pixels()
        old = png_assets.pixel(self.image, 10, 30)
        self.assertGreater(old[3], 0)
        set_pixel(pixels, self.image.width, 10, 30, (0, 0, 0, old[3]))
        candidate = encode_rgba8(self.image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "允许区域外"):
            builder.validate_replacement_contract(
                self.contract, HEAD_TARGET, self.original, candidate
            )

    def test_protected_eye_core_change_is_rejected(self) -> None:
        pixels = self.valid_candidate_pixels()
        old = png_assets.pixel(self.image, 44, 22)
        self.assertGreater(old[3], 0)
        replacement = (255, 0, 255, old[3]) if old[:3] != (255, 0, 255) else (0, 0, 0, old[3])
        set_pixel(pixels, self.image.width, 44, 22, replacement)
        candidate = encode_rgba8(self.image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "受保护区域"):
            builder.validate_replacement_contract(
                self.contract, HEAD_TARGET, self.original, candidate
            )


class BookAssetContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = builder.load_asset_contract(BOOK_CONTRACT_PATH)
        decoded, entries = pak_assets.parse_pak(pak_assets.PAK_PATH)
        entry = next(
            item
            for item in entries
            if builder.normalize_name(item.name) == BOOK_TARGET
        )
        cls.original = builder.entry_payload(decoded, entry)
        cls.image = png_assets.decode_rgba8(cls.original)

    def valid_candidate_pixels(self) -> bytearray:
        pixels = bytearray(self.image.pixels)
        for y in range(3, 29):
            for x in range(25, 44):
                set_pixel(pixels, self.image.width, x, y, (35, 80, 150, 255))
        for x in range(27, 41):
            set_pixel(pixels, self.image.width, x, 6, (225, 230, 235, 255))
        return pixels

    def test_book_contract_baseline_matches_pak_original(self) -> None:
        image = builder.validate_contract_baseline(
            self.contract, BOOK_TARGET, self.original
        )
        self.assertEqual((image.width, image.height), (67, 40))
        self.assertEqual(png_assets.visible_pixel_count(image), 1620)

    def test_blue_book_fixture_passes(self) -> None:
        candidate = encode_rgba8(self.image, bytes(self.valid_candidate_pixels()))
        builder.validate_replacement_contract(
            self.contract, BOOK_TARGET, self.original, candidate
        )

    def test_removing_original_leaf_alpha_is_rejected(self) -> None:
        pixels = self.valid_candidate_pixels()
        old = png_assets.pixel(self.image, 21, 31)
        self.assertGreater(old[3], 0)
        set_pixel(pixels, self.image.width, 21, 31, (*old[:3], 0))
        candidate = encode_rgba8(self.image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "削减了原件 Alpha"):
            builder.validate_replacement_contract(
                self.contract, BOOK_TARGET, self.original, candidate
            )

    def test_added_alpha_outside_book_area_is_rejected(self) -> None:
        pixels = self.valid_candidate_pixels()
        old = png_assets.pixel(self.image, 10, 2)
        self.assertEqual(old[3], 0)
        set_pixel(pixels, self.image.width, 10, 2, (35, 80, 150, 255))
        candidate = encode_rgba8(self.image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "允许区域外"):
            builder.validate_replacement_contract(
                self.contract, BOOK_TARGET, self.original, candidate
            )

    def test_missing_blue_cover_is_rejected(self) -> None:
        pixels = self.valid_candidate_pixels()
        for y in range(3, 29):
            for x in range(25, 44):
                set_pixel(pixels, self.image.width, x, y, (170, 55, 40, 255))
        for x in range(27, 41):
            set_pixel(pixels, self.image.width, x, 6, (225, 230, 235, 255))
        candidate = encode_rgba8(self.image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "deep-blue-cover"):
            builder.validate_replacement_contract(
                self.contract, BOOK_TARGET, self.original, candidate
            )

    def test_missing_light_page_detail_is_rejected(self) -> None:
        pixels = self.valid_candidate_pixels()
        for x in range(27, 41):
            set_pixel(pixels, self.image.width, x, 6, (35, 80, 150, 255))
        candidate = encode_rgba8(self.image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "light-page-or-title"):
            builder.validate_replacement_contract(
                self.contract, BOOK_TARGET, self.original, candidate
            )


if __name__ == "__main__":
    unittest.main()
