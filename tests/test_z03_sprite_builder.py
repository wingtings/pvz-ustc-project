#!/usr/bin/env python3
"""Tests for the deterministic Z03 three-stage blue exercise-book helmet."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_pak_overlay as pak_builder  # noqa: E402
import build_z03_sprites as sprites  # noqa: E402
import png_assets  # noqa: E402


EXPECTED_HASHES = {
    "Zombie_cone1.png": "371FA2B9BDAA9F99B6C5855C5A5965307CB0CDC6E2BD9D49ABC339B1F8451A3B",
    "Zombie_cone2.png": "6974580329C9F460624624A20A16662D1761F2AFC1D29A3E8C367EB92EC97C07",
    "Zombie_cone3.png": "E8D9AA0A07C30429D7AF7DA1F90FD3D94E34C1FDB46E34C086C05F2E92E937C9",
}
CONTRACTS = {
    "reanim/Zombie_cone1.png": "assets-src/game/z03/Zombie_cone1.contract.json",
    "reanim/Zombie_cone2.png": "assets-src/game/z03/Zombie_cone2.contract.json",
    "reanim/Zombie_cone3.png": "assets-src/game/z03/Zombie_cone3.contract.json",
}


def page_pixel_count(image: png_assets.RgbaPng) -> int:
    count = 0
    for offset in range(0, len(image.pixels), 4):
        red, green, blue, alpha = image.pixels[offset : offset + 4]
        if red >= 165 and green >= 165 and blue >= 150 and alpha >= 180:
            count += 1
    return count


class Z03SpriteBuilderTests(unittest.TestCase):
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
            self.assertEqual(png_assets.decode_rgba8(png_assets.encode_rgba8(image)), image)

    def test_candidates_satisfy_contracts(self) -> None:
        for target, contract_path in CONTRACTS.items():
            output_name = sprites.SPECS[target].output_name
            contract = pak_builder.load_asset_contract(contract_path)
            pak_builder.validate_replacement_contract(
                contract,
                target,
                self.originals[target],
                self.candidates[output_name],
            )

    def test_exposed_pages_increase_with_damage(self) -> None:
        page_counts = [
            page_pixel_count(png_assets.decode_rgba8(payload))
            for payload in self.candidates.values()
        ]
        self.assertEqual(page_counts, sorted(page_counts))
        self.assertEqual(page_counts, [481, 652, 726])

    def test_visible_silhouette_shrinks_with_damage(self) -> None:
        visible_counts = [
            png_assets.visible_pixel_count(png_assets.decode_rgba8(payload))
            for payload in self.candidates.values()
        ]
        self.assertEqual(visible_counts, [1654, 1504, 1334])


if __name__ == "__main__":
    unittest.main()
