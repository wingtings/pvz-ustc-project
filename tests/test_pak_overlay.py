#!/usr/bin/env python3
"""Tests for deterministic PAK rebuilding and overlay safety."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_pak_overlay as builder  # noqa: E402
import pak_assets  # noqa: E402


class PakOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.encoded = pak_assets.PAK_PATH.read_bytes()
        cls.decoded, cls.entries = pak_assets.parse_pak_bytes(
            cls.encoded, pak_assets.PAK_SHA256
        )

    def test_zero_replacement_roundtrip_is_byte_exact(self) -> None:
        rebuilt = builder.rebuild_pak(self.decoded, self.entries, {})
        self.assertEqual(rebuilt, self.encoded)

    def test_same_payload_replacement_is_byte_exact(self) -> None:
        entry = self.entries[0]
        replacements = {
            builder.normalize_name(entry.name): builder.entry_payload(
                self.decoded, entry
            )
        }
        rebuilt = builder.rebuild_pak(self.decoded, self.entries, replacements)
        self.assertEqual(rebuilt, self.encoded)

    def test_changed_size_rebuild_remains_parseable(self) -> None:
        entry = self.entries[0]
        target = builder.normalize_name(entry.name)
        rebuilt = builder.rebuild_pak(
            self.decoded, self.entries, {target: b"pvz-ustc-fixture"}
        )
        decoded, parsed = pak_assets.parse_pak_bytes(rebuilt, builder.sha256(rebuilt))
        self.assertEqual(len(parsed), len(self.entries))
        changed = next(item for item in parsed if builder.normalize_name(item.name) == target)
        self.assertEqual(builder.entry_payload(decoded, changed), b"pvz-ustc-fixture")

    def test_unknown_target_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            builder.rebuild_pak(
                self.decoded, self.entries, {"reanim/not-a-real-part.png": b"x"}
            )

    def test_asset_source_must_stay_under_assets_src(self) -> None:
        with self.assertRaises(ValueError):
            builder.resolve_asset_source(".work/pak-reference/reanim/PeaShooter_Head.png")

    def test_output_must_stay_under_dist(self) -> None:
        with self.assertRaises(ValueError):
            builder.require_dist_output(ROOT / "main-modified.pak")


if __name__ == "__main__":
    unittest.main()
