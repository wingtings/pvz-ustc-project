#!/usr/bin/env python3
"""Build and verify a complete local runtime without replacing clean inputs."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from baseline_inputs import BASELINE_ENV, classify_file, contained_path, sha256


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "dist" / "runtime"
SPEC_PATH = ROOT / "patches/manifests/runtime-baseline.json"
PAK_MANIFEST = "patches/manifests/v0.5-p01-green-circle-p02-p04-z01-sleeves-z03-ingame.json"
PATCH_MANIFEST = "patches/manifests/v0.3-constant-proof.json"
PROFILES = {
    "visuals": {"p01SeedCost": 100, "p04Health": 4000, "temporaryConstants": False},
    "constant-proof": {"p01SeedCost": 75, "p04Health": 4200, "temporaryConstants": True},
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def encode_json(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def runtime_output(path: Path) -> Path:
    path = path.resolve()
    allowed = RUNTIME_ROOT.resolve()
    if path == allowed or not path.is_relative_to(allowed):
        raise ValueError(f"运行目录必须位于 dist/runtime 的子目录：{path}")
    return path


def inspect_inputs(directory: Path) -> dict:
    spec = read_json(SPEC_PATH)
    pak = read_json(ROOT / PAK_MANIFEST)
    patch = read_json(ROOT / PATCH_MANIFEST)
    return {
        "directory": str(directory.resolve()),
        "PlantsVsZombies.exe": classify_file(
            contained_path(directory, "PlantsVsZombies.exe"),
            {"baseline": spec["exeSha256"], "constant-proof": patch["outputs"]["patchedSha256"]},
        ),
        "main.pak": classify_file(
            contained_path(directory, "main.pak"),
            {"baseline": spec["pakSha256"], "visuals": pak["output"]["sha256"]},
        ),
    }


def checked_payloads(directory: Path, expected: dict[str, str]) -> dict[str, bytes]:
    payloads = {}
    for name, digest in expected.items():
        path = contained_path(directory, name)
        if not path.is_file():
            raise ValueError(f"运行所需文件缺失：{name}")
        data = path.read_bytes()
        if sha256(data) != digest.upper():
            raise ValueError(f"输入哈希不匹配：{name}；请提供干净原件，保留当前开发文件")
        payloads[name] = data
    return payloads


def verify_files(directory: Path, hashes: dict[str, str]) -> None:
    checked_payloads(directory, hashes)


def install_payloads(output: Path, payloads: dict[str, bytes], metadata: dict) -> dict:
    output = runtime_output(output)
    for name in payloads:
        contained_path(output, name)
    if "runtime.json" in payloads:
        raise ValueError("runtime.json is reserved for the build record")
    report = {**metadata, "files": {name: sha256(data) for name, data in sorted(payloads.items())}}
    report_bytes = encode_json(report)
    if output.exists():
        record = output / "runtime.json"
        if not record.is_file() or record.read_bytes() != report_bytes:
            raise ValueError(f"已有运行目录与本次构建不同；请使用新的 --output，现有文件未改动：{output}")
        verify_files(output, report["files"])
        return report
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".assembling-", dir=output.parent)).resolve()
    runtime_output(temporary)
    try:
        for name, data in payloads.items():
            target = contained_path(temporary, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (temporary / "runtime.json").write_bytes(report_bytes)
        verify_files(temporary, report["files"])
        # The final directory appears only after the complete payload has passed verification.
        temporary.rename(output)
    finally:
        if temporary.exists():
            runtime_output(temporary)
            shutil.rmtree(temporary)
    return report


def build_runtime(baseline: Path, output: Path, profile: str) -> dict:
    output = runtime_output(output)
    baseline = baseline.resolve()
    if baseline == output or baseline.is_relative_to(output):
        raise ValueError("运行输出不能包含原件输入目录")
    spec = read_json(SPEC_PATH)
    source_hashes = {
        "PlantsVsZombies.exe": spec["exeSha256"],
        "main.pak": spec["pakSha256"],
        **spec["supportFiles"],
    }
    # Validate all inputs before running any builder or creating a runtime directory.
    payloads = checked_payloads(baseline, source_hashes)
    project_payloads = {
        name: contained_path(ROOT, name).read_bytes() for name in spec["projectFiles"]
    }
    environment = dict(os.environ, **{BASELINE_ENV: str(baseline), "PYTHONUTF8": "1"})
    commands = [
        [f"tools/build_{slot}_sprites.py", "--build", "--check"]
        for slot in ("p01", "p02", "p04", "z01", "z03")
    ]
    commands.append(["tools/build_pak_overlay.py", "--build", PAK_MANIFEST])
    if profile == "constant-proof":
        commands.append(["tools/apply_binary_patches.py", "--apply"])
    for command in commands:
        subprocess.run([sys.executable, *command], cwd=ROOT, env=environment, check=True)
    pak = read_json(ROOT / PAK_MANIFEST)
    payloads["main.pak"] = checked_payloads(
        ROOT, {pak["output"]["path"]: pak["output"]["sha256"]}
    )[pak["output"]["path"]]
    if profile == "constant-proof":
        patch = read_json(ROOT / PATCH_MANIFEST)
        name = patch["outputs"]["patchedPath"]
        payloads["PlantsVsZombies.exe"] = checked_payloads(
            ROOT, {name: patch["outputs"]["patchedSha256"]}
        )[name]
    payloads.update(project_payloads)
    metadata = {
        "schemaVersion": 1,
        "gameVersion": spec["gameVersion"],
        "profile": profile,
        "balance": PROFILES[profile],
        "pakManifest": PAK_MANIFEST,
        "pakManifestSha256": sha256((ROOT / PAK_MANIFEST).read_bytes()),
        "baseline": {"exeSha256": spec["exeSha256"], "pakSha256": spec["pakSha256"]},
    }
    return install_payloads(output, payloads, metadata)


def verify_runtime(output: Path) -> dict:
    output = runtime_output(output)
    report = read_json(contained_path(output, "runtime.json"))
    profile = report.get("profile")
    if report.get("schemaVersion") != 1 or profile not in PROFILES:
        raise ValueError("运行记录的版本或配置无效")
    spec = read_json(SPEC_PATH)
    required = {"PlantsVsZombies.exe", "main.pak", *spec["supportFiles"], *spec["projectFiles"]}
    if set(report["files"]) != required:
        raise ValueError("运行记录缺少必需文件或包含未登记文件")
    pak = read_json(ROOT / PAK_MANIFEST)
    patch = read_json(ROOT / PATCH_MANIFEST)
    exe_hash = spec["exeSha256"] if profile == "visuals" else patch["outputs"]["patchedSha256"]
    expected_critical = {"PlantsVsZombies.exe": exe_hash, "main.pak": pak["output"]["sha256"], **spec["supportFiles"]}
    if any(report["files"][name] != digest for name, digest in expected_critical.items()):
        raise ValueError("运行记录中的 EXE、PAK 或配套资源不属于所选配置")
    if report.get("balance") != PROFILES[profile]:
        raise ValueError("数值说明与运行配置不一致")
    verify_files(output, report["files"])
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect", action="store_true")
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--launch", action="store_true")
    parser.add_argument("--baseline-dir", type=Path)
    parser.add_argument("--profile", choices=PROFILES, default="visuals")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    baseline = args.baseline_dir or Path(os.environ.get(BASELINE_ENV, str(ROOT)))
    output = args.output or RUNTIME_ROOT / args.profile
    if not output.is_absolute():
        output = ROOT / output
    if args.inspect:
        print(json.dumps({"workspace": inspect_inputs(ROOT), "input": inspect_inputs(baseline)}, ensure_ascii=False, indent=2))
        return 0
    report = build_runtime(baseline, output, args.profile) if args.build else verify_runtime(output)
    print(json.dumps({"profile": report["profile"], "balance": report["balance"], "directory": str(output.resolve()), "fileCount": len(report["files"]), "exeSha256": report["files"]["PlantsVsZombies.exe"], "pakSha256": report["files"]["main.pak"]}, ensure_ascii=False, indent=2))
    if args.launch:
        if os.name != "nt":
            raise ValueError("原版游戏只在 Windows 启动")
        process = subprocess.Popen([str(output / "PlantsVsZombies.exe")], cwd=output)
        print(f"已从完整运行目录启动，PID={process.pid}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"运行目录工具失败：{error}", file=sys.stderr)
        raise SystemExit(1)
