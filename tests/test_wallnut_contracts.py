#!/usr/bin/env python3
"""Tests for the three P04 campus-wall damage-stage contracts."""

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
        "assets-src/game/p04/Wallnut_body.contract.json",
        "reanim/Wallnut_body.png",
        6766,
    ),
    (
        "assets-src/game/p04/Wallnut_cracked1.contract.json",
        "reanim/Wallnut_cracked1.png",
        6650,
    ),
    (
        "assets-src/game/p04/Wallnut_cracked2.contract.json",
        "reanim/Wallnut_cracked2.png",
        6414,
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


class WallnutContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        decoded, entries = pak_assets.parse_pak(pak_assets.PAK_PATH)
        payloads = {
            builder.normalize_name(entry.name): builder.entry_payload(decoded, entry)
            for entry in entries
        }
        cls.stage_data = []
        for contract_path, target, visible in STAGES:
            original = payloads[target]
            cls.stage_data.append(
                (
                    builder.load_asset_contract(contract_path),
                    target,
                    original,
                    png_assets.decode_rgba8(original),
                    visible,
                )
            )

    @staticmethod
    def valid_candidate_pixels(
        contract: dict[str, object], image: png_assets.RgbaPng
    ) -> bytearray:
        pixels = bytearray(image.pixels)
        policy = contract["pixelPolicy"]
        assert isinstance(policy, dict)
        allowed = builder._rect(
            policy["allowedChangeRect"],
            "allowedChangeRect",
            image.width,
            image.height,
        )
        protected = [
            builder._rect(value, "protected", image.width, image.height)
            for value in policy["protectedRects"]
        ]
        protected_colors = policy.get("protectedOriginalColors", [])
        for y in range(image.height):
            for x in range(image.width):
                old = png_assets.pixel(image, x, y)
                if (
                    old[3] > 0
                    and builder._inside(x, y, allowed)
                    and not any(builder._inside(x, y, rect) for rect in protected)
                    and not any(builder._matches_color(rule, old) for rule in protected_colors)
                ):
                    set_pixel(pixels, image.width, x, y, (130, 120, 105, old[3]))
        for y in range(70, 80):
            for x in range(20, 36):
                old = png_assets.pixel(image, x, y)
                if old[3] > 0 and not any(
                    builder._matches_color(rule, old) for rule in protected_colors
                ):
                    set_pixel(pixels, image.width, x, y, (35, 100, 160, old[3]))
        return pixels

    def test_all_contract_baselines_match_their_pak_stage(self) -> None:
        for contract, target, original, _, visible in self.stage_data:
            with self.subTest(target=target):
                image = builder.validate_contract_baseline(contract, target, original)
                self.assertEqual((image.width, image.height), (100, 100))
                self.assertEqual(png_assets.visible_pixel_count(image), visible)

    def test_all_grey_wall_fixtures_pass(self) -> None:
        for contract, target, original, image, _ in self.stage_data:
            with self.subTest(target=target):
                candidate = encode_rgba8(
                    image, bytes(self.valid_candidate_pixels(contract, image))
                )
                builder.validate_replacement_contract(
                    contract, target, original, candidate
                )

    def test_damage_stages_lose_visible_pixels_in_order(self) -> None:
        counts = [
            png_assets.visible_pixel_count(image)
            for _, _, _, image, _ in self.stage_data
        ]
        self.assertEqual(counts, [6766, 6650, 6414])
        self.assertGreater(counts[0], counts[1])
        self.assertGreater(counts[1], counts[2])

    def test_missing_blue_number_plate_is_rejected(self) -> None:
        contract, target, original, image, _ = self.stage_data[0]
        pixels = self.valid_candidate_pixels(contract, image)
        policy = contract["pixelPolicy"]
        assert isinstance(policy, dict)
        protected_colors = policy.get("protectedOriginalColors", [])
        for y in range(70, 80):
            for x in range(20, 36):
                old = png_assets.pixel(image, x, y)
                if old[3] > 0 and not any(
                    builder._matches_color(rule, old) for rule in protected_colors
                ):
                    set_pixel(pixels, image.width, x, y, (130, 120, 105, old[3]))
        candidate = encode_rgba8(image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "blue-number-plate"):
            builder.validate_replacement_contract(
                contract, target, original, candidate
            )

    def test_eye_detail_change_is_rejected(self) -> None:
        contract, target, original, image, _ = self.stage_data[0]
        pixels = self.valid_candidate_pixels(contract, image)
        old = png_assets.pixel(image, 44, 35)
        self.assertGreater(old[3], 0)
        replacement = (255, 0, 255, old[3])
        self.assertNotEqual(old, replacement)
        set_pixel(pixels, image.width, 44, 35, replacement)
        candidate = encode_rgba8(image, bytes(pixels))
        with self.assertRaisesRegex(ValueError, "受保护的原色"):
            builder.validate_replacement_contract(
                contract, target, original, candidate
            )

    def test_contract_cannot_be_applied_to_another_damage_stage(self) -> None:
        body_contract, body_target, _, _, _ = self.stage_data[0]
        _, _, cracked_original, _, _ = self.stage_data[1]
        with self.assertRaisesRegex(ValueError, "原件哈希不匹配"):
            builder.validate_contract_baseline(
                body_contract, body_target, cracked_original
            )


if __name__ == "__main__":
    unittest.main()
