"""Failure and integrity checks using synthetic files, never game assets."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import baseline_inputs as inputs
import runtime_workspace as runtime


class BaselineInputTests(unittest.TestCase):
    def test_explicit_directory_wins_over_environment(self):
        with tempfile.TemporaryDirectory() as temporary:
            chosen = Path(temporary)
            with mock.patch.dict(os.environ, {inputs.BASELINE_ENV: "unused-location"}):
                self.assertEqual(inputs.source_path("main.pak", baseline_dir=chosen), chosen / "main.pak")

    def test_environment_selects_input_without_changing_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(os.environ, {inputs.BASELINE_ENV: temporary}):
                self.assertEqual(inputs.source_path("main.pak"), Path(temporary) / "main.pak")
                self.assertEqual(runtime.RUNTIME_ROOT, ROOT / "dist/runtime")

    def test_parent_and_absolute_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for value in ("../outside", str(root / "absolute"), "."):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    inputs.contained_path(root, value)

    def test_baseline_development_unknown_and_missing_are_distinct(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "main.pak"
            hashes = {"baseline": inputs.sha256(b"original"), "visuals": inputs.sha256(b"modified")}
            self.assertEqual(inputs.classify_file(path, hashes)["state"], "missing")
            for data, state in ((b"original", "baseline"), (b"modified", "visuals"), (b"other", "unknown")):
                path.write_bytes(data)
                self.assertEqual(inputs.classify_file(path, hashes)["state"], state)
                self.assertEqual(path.read_bytes(), data)

    def test_modified_input_is_rejected_and_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "main.pak"
            path.write_bytes(b"already modified")
            with self.assertRaisesRegex(ValueError, "哈希不匹配"):
                runtime.checked_payloads(path.parent, {path.name: inputs.sha256(b"clean")})
            self.assertEqual(path.read_bytes(), b"already modified")

    def test_missing_support_file_stops_preflight(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "缺失"):
                runtime.checked_payloads(Path(temporary), {"required.dll": inputs.sha256(b"dll")})


class RuntimeAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runtime_root = self.root / "dist/runtime"
        self.output = self.runtime_root / "visuals"
        self.patch = mock.patch.object(runtime, "RUNTIME_ROOT", self.runtime_root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.payloads = {"PlantsVsZombies.exe": b"exe", "main.pak": b"pak", "data/font.txt": b"font"}
        self.metadata = {"schemaVersion": 1, "profile": "visuals"}

    def test_complete_install_is_idempotent_and_preserves_runtime_logs(self):
        first = runtime.install_payloads(self.output, self.payloads, self.metadata)
        before = (self.output / "PlantsVsZombies.exe").stat().st_mtime_ns
        (self.output / "log.txt").write_bytes(b"runtime observation")
        second = runtime.install_payloads(self.output, self.payloads, self.metadata)
        self.assertEqual(first, second)
        self.assertEqual((self.output / "PlantsVsZombies.exe").stat().st_mtime_ns, before)
        self.assertEqual((self.output / "log.txt").read_bytes(), b"runtime observation")
        self.assertEqual((self.output / "data/font.txt").read_bytes(), b"font")

    def test_changed_build_requires_a_new_directory(self):
        runtime.install_payloads(self.output, self.payloads, self.metadata)
        old_report = (self.output / "runtime.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "已有运行目录"):
            runtime.install_payloads(self.output, {**self.payloads, "main.pak": b"new"}, self.metadata)
        self.assertEqual((self.output / "main.pak").read_bytes(), b"pak")
        self.assertEqual((self.output / "runtime.json").read_bytes(), old_report)

    def test_unmanaged_directory_is_not_overwritten(self):
        self.output.mkdir(parents=True)
        (self.output / "notes.txt").write_bytes(b"keep")
        with self.assertRaises(ValueError):
            runtime.install_payloads(self.output, self.payloads, self.metadata)
        self.assertEqual(list(self.output.iterdir()), [self.output / "notes.txt"])

    def test_corrupt_installed_payload_does_not_pass_idempotency(self):
        report = runtime.install_payloads(self.output, self.payloads, self.metadata)
        (self.output / "main.pak").write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "哈希不匹配"):
            runtime.verify_files(self.output, report["files"])
        with self.assertRaises(ValueError):
            runtime.install_payloads(self.output, self.payloads, self.metadata)
        self.assertEqual((self.output / "main.pak").read_bytes(), b"corrupt")

    def test_interrupted_assembly_leaves_no_partial_runtime(self):
        write = Path.write_bytes

        def interrupted(path, data):
            if path.name == "font.txt":
                raise OSError("simulated disk failure")
            return write(path, data)

        with mock.patch.object(Path, "write_bytes", interrupted), self.assertRaises(OSError):
            runtime.install_payloads(self.output, self.payloads, self.metadata)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.runtime_root.iterdir()), [])

    def test_output_must_be_a_child_of_runtime_root(self):
        for path in (self.root, self.runtime_root, self.runtime_root / "../outside"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                runtime.install_payloads(path, self.payloads, self.metadata)

    def test_payload_cannot_escape_output_or_replace_build_record(self):
        for name in ("../escape", "runtime.json"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                runtime.install_payloads(self.output, {name: b"x"}, self.metadata)
        self.assertFalse(self.output.exists())

    def test_missing_installed_file_is_detected(self):
        report = runtime.install_payloads(self.output, self.payloads, self.metadata)
        (self.output / "data/font.txt").unlink()
        with self.assertRaisesRegex(ValueError, "缺失"):
            runtime.verify_files(self.output, report["files"])

    def test_profile_verification_rejects_forged_executable_record(self):
        spec = {"exeSha256": inputs.sha256(b"exe"), "supportFiles": {"data/font.txt": inputs.sha256(b"font")}, "projectFiles": []}
        report = runtime.install_payloads(self.output, self.payloads, {**self.metadata, "balance": runtime.PROFILES["visuals"]})
        real_read = runtime.read_json

        def fixture_read(path):
            if path == runtime.SPEC_PATH:
                return spec
            if path == runtime.ROOT / runtime.PAK_MANIFEST:
                return {"output": {"sha256": inputs.sha256(b"pak")}}
            if path == runtime.ROOT / runtime.PATCH_MANIFEST:
                return {"outputs": {"patchedSha256": inputs.sha256(b"patched")}}
            return real_read(path)

        with mock.patch.object(runtime, "read_json", fixture_read):
            self.assertEqual(runtime.verify_runtime(self.output)["profile"], "visuals")
            (self.output / "PlantsVsZombies.exe").write_bytes(b"other executable")
            report["files"]["PlantsVsZombies.exe"] = inputs.sha256(b"other executable")
            (self.output / "runtime.json").write_bytes(runtime.encode_json(report))
            with self.assertRaisesRegex(ValueError, "不属于所选配置"):
                runtime.verify_runtime(self.output)


if __name__ == "__main__":
    unittest.main()
