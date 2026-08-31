#!/usr/bin/env python3
"""Tests for the deterministic P01 glasses, textbook, and green-circle overlays."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_p01_sprites as sprites  # noqa: E402
import build_pak_overlay as pak_builder  # noqa: E402
import png_assets  # noqa: E402


HEAD_CONTRACT = "assets-src/game/p01/PeaShooter_Head.contract.json"
LEAF_CONTRACT = "assets-src/game/p01/PeaShooter_frontleaf.contract.json"
PROJECTILE_CONTRACT = "assets-src/game/p01/ProjectilePea.contract.json"
EXPECTED_HASHES = {
    "PeaShooter_Head.png": "DE8EBE694C2AEF2D477EA3866332B32B5BC11F2F03B170EE2C47BDACBA7B5610",
    "PeaShooter_frontleaf.png": "5814BE53B1EE2A122726FD1EE6E83C43A9599B529BA2E00B14B973BA4AC3624C",
    "ProjectilePea.png": "901888ADB37A41E275B5CF52321D10B200F6D48ADA311099D2665D8AEC25488A",
}


class P01SpriteBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.originals = sprites.pak_payloads()
        cls.candidates = sprites.build_all()

    def test_output_hashes_are_deterministic(self) -> None:
        self.assertEqual(
            {name: sprites.sha256(payload) for name, payload in self.candidates.items()},
            EXPECTED_HASHES,
        )

    def test_png_encoder_round_trips_rgba(self) -> None:
        for payload in self.candidates.values():
            image = png_assets.decode_rgba8(payload)
            encoded = png_assets.encode_rgba8(image)
            self.assertEqual(png_assets.decode_rgba8(encoded), image)

    def test_head_candidate_satisfies_contract(self) -> None:
        contract = pak_builder.load_asset_contract(HEAD_CONTRACT)
        pak_builder.validate_replacement_contract(
            contract,
            sprites.HEAD_TARGET,
            self.originals[sprites.HEAD_TARGET],
            self.candidates["PeaShooter_Head.png"],
        )

    def test_frontleaf_candidate_satisfies_contract(self) -> None:
        contract = pak_builder.load_asset_contract(LEAF_CONTRACT)
        pak_builder.validate_replacement_contract(
            contract,
            sprites.LEAF_TARGET,
            self.originals[sprites.LEAF_TARGET],
            self.candidates["PeaShooter_frontleaf.png"],
        )

    def test_projectile_candidate_satisfies_contract(self) -> None:
        contract = pak_builder.load_asset_contract(PROJECTILE_CONTRACT)
        pak_builder.validate_replacement_contract(
            contract,
            sprites.PROJECTILE_TARGET,
            self.originals[sprites.PROJECTILE_TARGET],
            self.candidates["ProjectilePea.png"],
        )

    def test_projectile_has_a_hole_and_preserves_outer_alpha(self) -> None:
        original = png_assets.decode_rgba8(self.originals[sprites.PROJECTILE_TARGET])
        candidate = png_assets.decode_rgba8(self.candidates["ProjectilePea.png"])
        self.assertEqual(png_assets.pixel(candidate, 13, 13)[3], 0)
        self.assertEqual(png_assets.pixel(candidate, 14, 14)[3], 0)
        for x, y in ((13, 2), (13, 25), (2, 13), (25, 13)):
            self.assertEqual(
                png_assets.pixel(candidate, x, y)[3],
                png_assets.pixel(original, x, y)[3],
            )
        self.assertLess(
            png_assets.visible_pixel_count(candidate),
            png_assets.visible_pixel_count(original),
        )


if __name__ == "__main__":
    unittest.main()
