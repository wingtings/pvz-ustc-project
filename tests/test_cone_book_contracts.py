#!/usr/bin/env python3
"""Tests for the Z03 blue exercise-book damage-stage contracts."""

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


STAGES = (
    (
        "assets-src/game/z03/Zombie_cone1.contract.json",
        "reanim/Zombie_cone1.png",
        1582,
        5,
        37,
    ),
    (
        "assets-src/game/z03/Zombie_cone2.contract.json",
        "reanim/Zombie_cone2.png",
        1642,
        8,
        33,
    ),
    (
        "assets-src/game/z03/Zombie_cone3.contract.json",
        "reanim/Zombie_cone3.png",
        1624,
        10,
        29,
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


class ConeBookContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        decoded, entries = pak_assets.parse_pak(pak_assets.PAK_PATH)
        payloads = {
            builder.normalize_name(entry.name): builder.entry_payload(decoded, entry)
            for entry in entries
        }
        cls.stage_data = []
        for contract_path, target, visible, book_top, page_top in STAGES:
            original = payloads[target]
            cls.stage_data.append(
                (
                    builder.load_asset_contract(contract_path),
                    target,
                    original,
                    png_assets.decode_rgba8(original),
                    visible,
                    book_top,
                    page_top,
                )
            )

    @staticmethod
    def inside_damage_cut(stage: int, x: int, y: int) -> bool:
        if stage == 1:
            return x >= 43 and y <= 16
        if stage == 2:
            return (x >= 39 and y <= 21) or (x <= 15 and y <= 16)
        return False

    def valid_candidate_pixels(
        self,
        stage: int,
        image: png_assets.RgbaPng,
        book_top: int,
        page_top: int,
    ) -> bytearray:
        pixels = bytearray(image.pixels)
        for y in range(43):
            for x in range(image.width):
                old = png_assets.pixel(image, x, y)
                in_book = (
                    10 <= x <= 50
                    and book_top <= y <= 42
                    and not self.inside_damage_cut(stage, x, y)
                )
                if in_book:
                    color = (225, 220, 200, 255) if y >= page_top else (35, 75, 145, 255)
                    set_pixel(pixels, image.width, x, y, color)
                elif old[3] > 0:
                    set_pixel(pixels, image.width, x, y, (0, 0, 0, 0))

        for y in range(43, image.height):
            for x in range(image.width):
                old = png_assets.pixel(image, x, y)
                if old[3] > 0:
                    color = (225, 220, 200, old[3]) if y <= 48 else (35, 75, 145, old[3])
                    set_pixel(pixels, image.width, x, y, color)
        return pixels

    def test_all_contract_baselines_match_their_pak_stage(self) -> None:
        for contract, target, original, _, visible, _, _ in self.stage_data:
            with self.subTest(target=target):
                image = builder.validate_contract_baseline(contract, target, original)
                self.assertEqual((image.width, image.height), (59, 57))
                self.assertEqual(png_assets.visible_pixel_count(image), visible)

    def test_all_blue_book_fixtures_pass(self) -> None:
        for stage, data in enumerate(self.stage_data):
            contract, target, original, image, _, book_top, page_top = data
            with self.subTest(target=target):
                candidate = encode_rgba8(
                    image,
                    bytes(
                        self.valid_candidate_pixels(
                            stage, image, book_top, page_top
                        )
                    ),
                )
                builder.validate_replacement_contract(
                    contract, target, original, candidate
                )

    def test_page_requirement_increases_with_damage(self) -> None:
        minimum_pages = [
            contract["pixelPolicy"]["colorRequirements"][1]["minPixels"]
            for contract, *_ in self.stage_data
        ]
        self.assertEqual(minimum_pages, [100, 180, 260])

    def test_head_contact_alpha_change_is_rejected(self) -> None:
        contract, target, original, image, _, book_top, page_top = self.stage_data[0]
        pixels = self.valid_candidate_pixels(0, image, book_top, page_top)
        old = png_assets.pixel(image, 20, 50)
        self.assertGreater(old[3], 0)
        set_pixel(pixels, image.width, 20, 50, (*old[:3], 0))
        candidate = encode_rgba8(image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "锚点保护带 Alpha"):
            builder.validate_replacement_contract(
                contract, target, original, candidate
            )

    def test_blue_cone_without_silhouette_change_is_rejected(self) -> None:
        contract, target, original, image, _, _, _ = self.stage_data[0]
        pixels = bytearray(image.pixels)
        for y in range(image.height):
            for x in range(image.width):
                old = png_assets.pixel(image, x, y)
                if old[3] > 0:
                    set_pixel(pixels, image.width, x, y, (35, 75, 145, old[3]))
        candidate = encode_rgba8(image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "新增可见像素"):
            builder.validate_replacement_contract(
                contract, target, original, candidate
            )

    def test_missing_exposed_pages_is_rejected(self) -> None:
        stage = 2
        contract, target, original, image, _, book_top, page_top = self.stage_data[stage]
        pixels = self.valid_candidate_pixels(stage, image, book_top, page_top)
        for y in range(page_top, 49):
            for x in range(image.width):
                current_offset = (y * image.width + x) * 4
                alpha = pixels[current_offset + 3]
                if alpha > 0:
                    set_pixel(pixels, image.width, x, y, (35, 75, 145, alpha))
        candidate = encode_rgba8(image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "white-page-block"):
            builder.validate_replacement_contract(
                contract, target, original, candidate
            )


if __name__ == "__main__":
    unittest.main()
