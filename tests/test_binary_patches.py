#!/usr/bin/env python3
"""Tests for the v0.3 hash-gated binary patch manifest."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import apply_binary_patches as patcher  # noqa: E402


MANIFEST_PATH = ROOT / "patches" / "manifests" / "v0.3-constant-proof.json"


class BinaryPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = patcher.load_manifest(MANIFEST_PATH)
        cls.baseline = (ROOT / cls.manifest["baseline"]["path"]).read_bytes()

    def test_baseline_hash(self) -> None:
        self.assertEqual(
            patcher.sha256(self.baseline), self.manifest["baseline"]["sha256"]
        )

    def test_aob_is_unique_and_offsets_match(self) -> None:
        for patch in self.manifest["patches"]:
            matches, _ = patcher.find_aob(self.baseline, patch["aob"])
            self.assertEqual(matches, [
                patcher.parse_offset(patch["baselineFileOffset"])
                - int(patch["patchOffset"])
            ])

    def test_forward_and_reverse_are_exact(self) -> None:
        patched, forward = patcher.transform(
            self.baseline, self.manifest, reverse=False
        )
        self.assertEqual(len(forward), 2)
        self.assertEqual(
            patcher.sha256(patched),
            self.manifest["outputs"]["patchedSha256"],
        )
        restored, reverse = patcher.transform(patched, self.manifest, reverse=True)
        self.assertEqual(len(reverse), 2)
        self.assertEqual(restored, self.baseline)

    def test_tampered_baseline_is_rejected(self) -> None:
        tampered = bytearray(self.baseline)
        tampered[0x1000] ^= 0x01
        with self.assertRaises(ValueError):
            patcher.validate_source_hash(bytes(tampered), self.manifest, False)

    def test_expected_bytes(self) -> None:
        patched, _ = patcher.transform(self.baseline, self.manifest, reverse=False)
        for patch in self.manifest["patches"]:
            offset = patcher.parse_offset(patch["baselineFileOffset"])
            after = patcher.parse_hex_bytes(patch["after"], patch["id"])
            self.assertEqual(patched[offset : offset + len(after)], after)

    def test_text_assertions(self) -> None:
        patcher.check_text_assertions(self.manifest)

    def test_output_must_stay_under_dist(self) -> None:
        with self.assertRaises(ValueError):
            patcher.require_dist_output(ROOT / "PlantsVsZombies-copy.exe")


if __name__ == "__main__":
    unittest.main()
