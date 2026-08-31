#!/usr/bin/env python3
"""Tests for the complete first-slice game-asset contract registry."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_game_asset as checker  # noqa: E402


REGISTRY_PATH = "patches/manifests/v0.5-first-slice-contracts.json"


class AssetContractRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = checker.load_registry(REGISTRY_PATH)
        cls.payloads = checker.pak_payloads()

    def test_registry_covers_all_first_slice_contracts(self) -> None:
        contract_count, slot_count = checker.validate_registry(
            self.registry, self.payloads
        )
        self.assertEqual(contract_count, 16)
        self.assertEqual(slot_count, 5)

    def test_registry_paths_equal_discovered_contract_paths(self) -> None:
        declared = {
            entry["contract"] for entry in self.registry["entries"]
        }
        self.assertEqual(declared, checker.discover_contract_paths())

    def test_unregistered_contract_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["entries"].pop()
        with self.assertRaisesRegex(ValueError, "未登记"):
            checker.validate_registry(registry, self.payloads)

    def test_duplicate_contract_path_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["entries"][-1]["contract"] = registry["entries"][-2]["contract"]
        with self.assertRaisesRegex(ValueError, "重复 PAK 目标|重复 contract 路径"):
            checker.validate_registry(registry, self.payloads)

    def test_expected_slot_set_is_enforced(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["expectedSlots"].append("Z99")
        with self.assertRaisesRegex(ValueError, "槽位不一致"):
            checker.validate_registry(registry, self.payloads)


if __name__ == "__main__":
    unittest.main()
