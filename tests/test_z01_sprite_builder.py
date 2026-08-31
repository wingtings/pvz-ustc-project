#!/usr/bin/env python3
"""Tests for deterministic Z01 worn-calculus-paper body parts."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_pak_overlay as pak_builder  # noqa: E402
import build_z01_sprites as sprites  # noqa: E402
import png_assets  # noqa: E402


CONTRACTS = {
    "Zombie_body.png": "assets-src/game/z01/Zombie_body.contract.json",
    "Zombie_innerarm_upper.png": (
        "assets-src/game/z01/Zombie_innerarm_upper.contract.json"
    ),
    "Zombie_outerarm_upper.png": (
        "assets-src/game/z01/Zombie_outerarm_upper.contract.json"
    ),
    "Zombie_outerarm_upper2.png": (
        "assets-src/game/z01/Zombie_outerarm_upper2.contract.json"
    ),
}
EXPECTED_HASHES = {
    "Zombie_body.png": (
        "DA899F703AA5322A9042281A2DE78522556D737F7D4FD456500EEA85917D3A63"
    ),
    "Zombie_innerarm_upper.png": (
        "1D5EBB886617F53761D2FB7E49E39C5116544AF5530DBCFBDCFCB3B051A1E41D"
    ),
    "Zombie_outerarm_upper.png": (
        "41BD9C001C6F58BF88FEE39F8BCF739E4E3C7716D3524C9EBE9DEC559AAB9ECB"
    ),
    "Zombie_outerarm_upper2.png": (
        "D0F2143D926AD4E7DCABFCB26E17D45CD9C80C6780CFFB75AC199084F13B8CD5"
    ),
}


class Z01SpriteBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.originals = sprites.pak_payloads()
        cls.candidates = {
            "Zombie_body.png": sprites.build_body(
                cls.originals["Zombie_body.png"]
            )
        }
        for name in sprites.SLEEVE_NAMES:
            cls.candidates[name] = sprites.build_sleeve(
                cls.originals[name], name
            )
        cls.original = cls.originals["Zombie_body.png"]
        cls.candidate = cls.candidates["Zombie_body.png"]
        cls.original_image = png_assets.decode_rgba8(cls.original)
        cls.candidate_image = png_assets.decode_rgba8(cls.candidate)

    def test_output_hash_is_deterministic(self) -> None:
        for name, expected in EXPECTED_HASHES.items():
            with self.subTest(name=name):
                self.assertEqual(sprites.sha256(self.candidates[name]), expected)

    def test_candidate_satisfies_contract(self) -> None:
        for name, contract_path in CONTRACTS.items():
            target = sprites.ASSET_SPECS[name][0]
            contract = pak_builder.load_asset_contract(contract_path)
            with self.subTest(name=name):
                pak_builder.validate_replacement_contract(
                    contract,
                    target,
                    self.originals[name],
                    self.candidates[name],
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

        for name in sprites.SLEEVE_NAMES:
            original = png_assets.decode_rgba8(self.originals[name])
            candidate = png_assets.decode_rgba8(self.candidates[name])
            self.assertEqual(
                (candidate.width, candidate.height),
                sprites.ASSET_SPECS[name][2],
            )
            for y in range(original.height):
                for x in range(original.width):
                    old = png_assets.pixel(original, x, y)
                    new = png_assets.pixel(candidate, x, y)
                    self.assertEqual(new[3], old[3])
                    if sprites.protected_sleeve_ink(old):
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

    def test_sleeve_paper_cues_remain_visible(self) -> None:
        expected = {
            "Zombie_innerarm_upper.png": (130, 15, 5),
            "Zombie_outerarm_upper.png": (308, 30, 8),
            "Zombie_outerarm_upper2.png": (266, 24, 8),
        }
        for name, counts_expected in expected.items():
            original = png_assets.decode_rgba8(self.originals[name])
            candidate = png_assets.decode_rgba8(self.candidates[name])
            counts = [0, 0, 0]
            for y in range(original.height):
                for x in range(original.width):
                    old = png_assets.pixel(original, x, y)
                    new = png_assets.pixel(candidate, x, y)
                    if old == new:
                        continue
                    red, green, blue, alpha = new
                    counts[0] += (
                        alpha >= 140
                        and 155 <= red <= 235
                        and 145 <= green <= 225
                        and 125 <= blue <= 205
                    )
                    counts[1] += (
                        alpha >= 140
                        and 75 <= red <= 155
                        and 75 <= green <= 155
                        and 70 <= blue <= 150
                    )
                    counts[2] += (
                        alpha >= 160
                        and red >= 145
                        and green <= 105
                        and blue <= 95
                    )
            with self.subTest(name=name):
                self.assertEqual(tuple(counts), counts_expected)

    def test_detached_sleeve_white_cuff_is_preserved(self) -> None:
        name = "Zombie_outerarm_upper2.png"
        original = png_assets.decode_rgba8(self.originals[name])
        candidate = png_assets.decode_rgba8(self.candidates[name])
        cuff_pixels = 0
        for y in range(original.height):
            for x in range(original.width):
                old = png_assets.pixel(original, x, y)
                red, green, blue, alpha = old
                is_white_cuff = (
                    alpha > 0
                    and min(red, green, blue) >= 175
                    and max(red, green, blue) - min(red, green, blue) <= 15
                )
                if not is_white_cuff:
                    continue
                cuff_pixels += 1
                self.assertEqual(png_assets.pixel(candidate, x, y), old)
        self.assertGreaterEqual(cuff_pixels, 10)


if __name__ == "__main__":
    unittest.main()
