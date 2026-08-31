#!/usr/bin/env python3
"""Tests for the deterministic Z01 worn-calculus-paper body overlay."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_pak_overlay as pak_builder  # noqa: E402
import build_z01_sprites as sprites  # noqa: E402
import png_assets  # noqa: E402


CONTRACT = "assets-src/game/z01/Zombie_body.contract.json"
EXPECTED_HASH = "DA899F703AA5322A9042281A2DE78522556D737F7D4FD456500EEA85917D3A63"


class Z01SpriteBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original = sprites.pak_payload()
        cls.candidate = sprites.build_body(cls.original)
        cls.original_image = png_assets.decode_rgba8(cls.original)
        cls.candidate_image = png_assets.decode_rgba8(cls.candidate)

    def test_output_hash_is_deterministic(self) -> None:
        self.assertEqual(sprites.sha256(self.candidate), EXPECTED_HASH)

    def test_candidate_satisfies_contract(self) -> None:
        contract = pak_builder.load_asset_contract(CONTRACT)
        pak_builder.validate_replacement_contract(
            contract,
            sprites.TARGET,
            self.original,
            self.candidate,
        )

    def test_canvas_alpha_and_dark_ink_are_preserved(self) -> None:
        self.assertEqual(
            (self.candidate_image.width, self.candidate_image.height),
            (53, 63),
        )
        for y in range(self.original_image.height):
            for x in range(self.original_image.width):
                old = png_assets.pixel(self.original_image, x, y)
                new = png_assets.pixel(self.candidate_image, x, y)
                self.assertEqual(new[3], old[3])
                if sprites.protected_dark(old):
                    self.assertEqual(new, old)

    def test_original_red_tie_is_not_repainted(self) -> None:
        protected_tie_pixels = 0
        for y in range(self.original_image.height):
            for x in range(self.original_image.width):
                old = png_assets.pixel(self.original_image, x, y)
                red, green, blue, alpha = old
                is_tie = (
                    alpha > 0
                    and red >= 70
                    and red * 2 >= green * 3
                    and red * 10 >= blue * 14
                )
                if not is_tie:
                    continue
                protected_tie_pixels += 1
                self.assertEqual(
                    png_assets.pixel(self.candidate_image, x, y), old
                )
        self.assertGreaterEqual(protected_tie_pixels, 15)

    def test_exam_paper_cues_remain_visible(self) -> None:
        counts = {"paper": 0, "pencil": 0, "red": 0}
        for y in range(self.original_image.height):
            for x in range(self.original_image.width):
                old = png_assets.pixel(self.original_image, x, y)
                new = png_assets.pixel(self.candidate_image, x, y)
                if old == new:
                    continue
                red, green, blue, alpha = new
                if (
                    alpha >= 140
                    and 155 <= red <= 235
                    and 145 <= green <= 225
                    and 125 <= blue <= 205
                ):
                    counts["paper"] += 1
                if (
                    alpha >= 140
                    and 75 <= red <= 155
                    and 75 <= green <= 155
                    and 70 <= blue <= 150
                ):
                    counts["pencil"] += 1
                if (
                    alpha >= 160
                    and red >= 145
                    and green <= 105
                    and blue <= 95
                ):
                    counts["red"] += 1
        self.assertGreaterEqual(counts["paper"], 750)
        self.assertGreaterEqual(counts["pencil"], 120)
        self.assertGreaterEqual(counts["red"], 35)


if __name__ == "__main__":
    unittest.main()
