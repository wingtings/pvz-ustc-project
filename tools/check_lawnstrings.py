#!/usr/bin/env python3
"""Validate the generated CP936 LawnStrings file without changing it."""

from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

from sync_lawnstrings import (
    CANONICAL_ALIASES,
    GENERIC_REPLACEMENTS,
    LAWNSTRINGS,
    parse_doc,
    parse_entries,
    read_cp936,
)


FORBIDDEN_TERMS = tuple(sorted({*CANONICAL_ALIASES, *GENERIC_REPLACEMENTS}, key=len, reverse=True))
CONTROL_TOKENS = ("{SHORTLINE}", "{KEYWORD}", "{STAT}", "{FLAVOR}")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def fail(message: str) -> None:
    print(f"错误：{message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    raw = LAWNSTRINGS.read_bytes()
    if raw.startswith((b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff")):
        fail("LawnStrings.txt 不应带 BOM")
    if b"\n" in raw.replace(b"\r\n", b""):
        fail("LawnStrings.txt 必须只使用 CRLF 换行")

    text = read_cp936(LAWNSTRINGS)
    entries = parse_entries(text)
    headers = re.findall(r"(?m)^\[([^\]]+)\]$", text)
    duplicates = [key for key, count in collections.Counter(headers).items() if count > 1]
    if duplicates:
        fail(f"发现重复键：{', '.join(duplicates)}")
    if len(headers) != 869:
        fail(f"键数量从基线 869 变为 {len(headers)}")

    plants = parse_doc(Path(__file__).resolve().parents[1] / "docs" / "plants.md", "P")
    zombies = parse_doc(Path(__file__).resolve().parents[1] / "docs" / "zombies.md", "Z")
    for unit in plants.values():
        expected = (unit.key, f"{unit.key}_TOOLTIP", f"{unit.key}_DESCRIPTION")
        for key in expected:
            if key not in entries:
                fail(f"缺少 [{key}]")
        if entries[unit.key].strip() != unit.name:
            fail(f"[{unit.key}] 名称未同步为 {unit.name}")
        description = entries[f"{unit.key}_DESCRIPTION"]
        for token in CONTROL_TOKENS:
            if token not in description:
                fail(f"[{unit.key}_DESCRIPTION] 缺少控制标记 {token}")

    for unit_id, unit in zombies.items():
        if unit_id == "Z27":
            continue
        for key in (unit.key, f"{unit.key}_DESCRIPTION"):
            if key not in entries:
                fail(f"缺少 [{key}]")
        if entries[unit.key].strip() != unit.name:
            fail(f"[{unit.key}] 名称未同步为 {unit.name}")
        description = entries[f"{unit.key}_DESCRIPTION"]
        for token in CONTROL_TOKENS:
            if token not in description:
                fail(f"[{unit.key}_DESCRIPTION] 缺少控制标记 {token}")

    leftovers = {term: text.count(term) for term in FORBIDDEN_TERMS if term in text}
    if leftovers:
        fail("仍有旧世界观词汇：" + ", ".join(f"{k} x{v}" for k, v in leftovers.items()))

    longest = max(
        (len(line.encode("cp936")), index + 1, line)
        for index, line in enumerate(text.splitlines())
        if not line.startswith("{")
    )
    print(
        f"文案检查通过：{len(headers)} 个唯一键，49 个植物，26 个图鉴敌人；"
        f"最长普通行 {longest[0]} 字节（第 {longest[1]} 行）"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
