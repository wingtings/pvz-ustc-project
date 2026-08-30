#!/usr/bin/env python3
"""Tests for the deterministic P04 three-stage campus-wall repaint."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_p04_sprites as sprites  # noqa: E402
import build_pak_overlay as pak_builder  # noqa: E402
import png_assets  # noqa: E402


EXPECTED_HASHES = {
    "Wallnut_body.png": "182D862C209D1F4B1A26D45563BC04E49AE7BC1E1D4C96F9CAC83BA64252EE0F",
    "Wallnut_cracked1.png": "F649BAE9218B758CA1DCDA0E4E47CB5AD6D4383BF7521CB03AAD0A2FA7587113",
    "Wallnut_cracked2.png": "C2F61BA4EA797F9845FA1040A73C17C0A1727C164AD7572FA28F09C349C4DF6B",
}
CONTRACTS = {
    "reanim/Wallnut_body.png": "assets-src/game/p04/Wallnut_body.contract.json",
    "reanim/Wallnut_cracked1.png": "assets-src/game/p04/Wallnut_cracked1.contract.json",
    "reanim/Wallnut_cracked2.png": "assets-src/game/p04/Wallnut_cracked2.contract.json",
}


class P04SpriteBuilderTests(unittest.TestCase):
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
