#!/usr/bin/env python3
"""Tests for the deterministic P02 study-expression and note-petal overlays."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_p02_sprites as sprites  # noqa: E402
import build_pak_overlay as pak_builder  # noqa: E402
import png_assets  # noqa: E402


EXPECTED_HASHES = {
    "SunFlower_head.png": "AA1798442092C73A0FF301DB46BFFB2D5B9F90543987B5E328F46592223D564B",
    "SunFlower_toppetals.png": "F7689588A98A398BD4B508F8D82ACAAB135D87115E862B6B85E13CF2599BC67A",
    "SunFlower_bottompetals.png": "598695E935B0D099A9463BE1F366E47355BC34A145ADC679BA3DA8F58F0D3604",
}
CONTRACTS = {
    "reanim/SunFlower_head.png": "assets-src/game/p02/SunFlower_head.contract.json",
    "reanim/SunFlower_toppetals.png": "assets-src/game/p02/SunFlower_toppetals.contract.json",
    "reanim/SunFlower_bottompetals.png": "assets-src/game/p02/SunFlower_bottompetals.contract.json",
}


class P02SpriteBuilderTests(unittest.TestCase):
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
            output_name = sprites.SPECS[target][0]
            contract = pak_builder.load_asset_contract(contract_path)
            pak_builder.validate_replacement_contract(
                contract,
                target,
                self.originals[target],
                self.candidates[output_name],
            )


if __name__ == "__main__":
    unittest.main()
