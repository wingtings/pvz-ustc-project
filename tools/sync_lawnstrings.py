#!/usr/bin/env python3
"""Synchronize the USTC roster from the design docs into LawnStrings.txt.

The design documents stay UTF-8 for review.  The game file is always decoded and
written as strict CP936 with CRLF line endings.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAWNSTRINGS = ROOT / "properties" / "LawnStrings.txt"
PLANT_DOC = ROOT / "docs" / "plants.md"
ZOMBIE_DOC = ROOT / "docs" / "zombies.md"
BASELINE_SHA256 = "B974C89344A19F5A056133E1F776598693CFCD0E2C8A82E1C9535CD5CCFB131B"
WRAP_BYTES = 44

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


@dataclass(frozen=True)
class Unit:
    unit_id: str
    name: str
    key: str
    description: str
    flavor: str
    stat_label: str
    stat_value: str
    extra_label: str = ""
    extra_value: str = ""


UPGRADE_REQUIREMENTS = {
    "P41": "双发科豆",
    "P42": "学习蝌蝻",
    "P43": "大雾实验仪",
    "P44": "防水实验台",
    "P45": "西瓜科豆",
    "P46": "磁盘回收菇",
    "P47": "出恭草",
    "P48": "2 个黄油科豆",
}


FIXED_TEXT = {
    "SUBURBAN_ALMANAC": "科大沙盘图鉴",
    "FOUND_SUBURBAN_ALMANAC": "你发现了科大沙盘图鉴！",
    "SUBURBAN_ALMANAC_DESCRIPTION": "记录防线单位与错题潮资料的图鉴。",
    "SUBURBAN_ALMANAC_INDEX": "图鉴 - 索引",
    "SUBURBAN_ALMANAC_PLANTS": "图鉴 - 防线单位",
    "SUBURBAN_ALMANAC_ZOMBIES": "图鉴 - 错题潮",
    "VIEW_PLANTS": "查看防线单位",
    "VIEW_ZOMBIES": "查看错题潮",
    "CHOOSE_YOUR_PLANTS": "选择你的防线单位",
}


CANONICAL_ALIASES = {
    "豌豆射手": "绿圈科豆",
    "向日葵": "学习蝌蝻",
    "樱桃炸弹": "金矿炸弹",
    "坚果墙": "出恭墙",
    "土豆雷": "三星地雷",
    "寒冰豌豆": "寒冰科豆",
    "寒冰射手": "寒冰科豆",
    "大嘴花": "苕皮卷",
    "双发射手": "双发科豆",
    "双发豌豆": "双发科豆",
    "小喷菇": "小喷科豆",
    "阳光菇": "小学习蝌蝻",
    "大喷菇": "大雾实验仪",
    "墓碑吞噬者": "报告回收箱",
    "魅惑菇": "思路转换器",
    "胆小菇": "社恐科豆",
    "寒冰菇": "液氮罐",
    "毁灭菇": "大物实验",
    "睡莲": "防水实验台",
    "缠绕水草": "阴暗爬行蝌蝻",
    "火爆辣椒": "爆汁烤苕皮",
    "地刺王": "出恭草王",
    "地刺": "出恭草",
    "火炬树桩": "暖气片",
    "高坚果": "大出恭墙",
    "海蘑菇": "水上小喷科豆",
    "路灯花": "充电小台灯",
    "仙人掌": "Wi-Fi 天线",
    "三叶草": "机房排风扇",
    "裂荚射手": "双端调试科豆",
    "杨桃": "五线程科豆",
    "南瓜头": "防静电机箱",
    "磁力菇": "磁盘回收菇",
    "卷心菜投手": "卷菜科豆",
    "花盆": "培养皿",
    "玉米投手": "黄油科豆",
    "咖啡豆": "咖啡因",
    "叶子保护伞": "生物安全柜",
    "金盏花": "经费花",
    "西瓜投手": "西瓜科豆",
    "机枪射手": "四核科豆",
    "双子向日葵": "双学位蝌蝻",
    "忧郁菇": "大雾核心",
    "香蒲": "校园猫猫",
    "冰西瓜": "低温西瓜科豆",
    "吸金磁": "奖学金磁铁",
    "玉米加农炮": "合肥大炮",
    "模仿者": "复印科豆",
    "普通僵尸": "普通微积分",
    "旗帜僵尸": "摇旗微积分",
    "路障头僵尸": "B 系列淑芬",
    "路障僵尸": "B 系列淑芬",
    "撑杆僵尸": "撑杆力学",
    "铁桶僵尸": "A 系列淑芬",
    "报纸僵尸": "大雾实验报告",
    "铁栅门僵尸": "线代铁门",
    "铁门僵尸": "线代铁门",
    "橄榄球僵尸": "期末冲刺",
    "舞王僵尸": "小组作业组长",
    "伴舞僵尸": "小组作业队员",
    "鸭子救生圈僵尸": "鸭圈流体力学",
    "潜水僵尸": "潜水概率论",
    "冰车僵尸": "低温实验车",
    "雪橇僵尸小队": "四人雪橇小组",
    "海豚骑士僵尸": "海豚流体力学",
    "玩偶匣僵尸": "随机抽查盒",
    "气球僵尸": "云端作业",
    "矿工僵尸": "地道赶课题",
    "跳跳僵尸": "跳点证明题",
    "雪人僵尸": "隐藏压轴题",
    "蹦极僵尸": "DDL 空投",
    "扶梯僵尸": "扶梯证明题",
    "投石车僵尸": "作业投递车",
    "巨人僵尸": "期末周",
    "小鬼僵尸": "附加题",
    "僵王博士": "期末总控机",
    "红眼巨人僵尸": "补考周",
}


GENERIC_REPLACEMENTS = {
    "僵尸大军": "错题潮",
    "选择你的科豆": "选择你的防线单位",
    "植物槽": "选卡槽",
    "禅境花园": "科大培养区",
    "植物园": "培养区",
    "脑子": "GPA 数据",
    "豌豆": "绿圈",
    "坚果": "出恭墙",
    "僵尸": "错题",
    "教材": "错题",
    "阳光": "专注值",
    "柯南": "科豆",
    "植物": "单位",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def read_cp936(path: Path) -> str:
    data = path.read_bytes()
    text = data.decode("cp936", errors="strict")
    if text.encode("cp936", errors="strict") != data:
        raise ValueError(f"{path} 不能无损往返 CP936")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def write_cp936(path: Path, text: str) -> None:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    data = normalized.replace("\n", "\r\n").encode("cp936", errors="strict")
    path.write_bytes(data)


def parse_doc(path: Path, prefix: str) -> dict[str, Unit]:
    text = path.read_text(encoding="utf-8")
    rows: dict[str, list[str]] = {}
    for line in text.splitlines():
        if not re.match(rf"^\|\s*{prefix}\d{{2}}\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows[cells[0]] = cells

    prose: dict[str, tuple[str, str]] = {}
    section_re = re.compile(
        rf"(?ms)^### ({prefix}\d{{2}}) [^\n]+\n(.*?)(?=^### {prefix}\d{{2}} |^## |\Z)"
    )
    for match in section_re.finditer(text):
        unit_id, section = match.groups()
        body = re.search(
            r"(?ms)图鉴说明：(.*?)\n\s*\n口味文字：(.*?)(?:\n\s*\n|\Z)", section
        )
        if body:
            prose[unit_id] = tuple(part.strip() for part in body.groups())

    expected = 49 if prefix == "P" else 27
    if len(rows) != expected or len(prose) != expected:
        raise ValueError(
            f"{path.name} 解析数量异常：表格 {len(rows)}，图鉴 {len(prose)}，应为 {expected}"
        )

    result: dict[str, Unit] = {}
    for unit_id, cells in rows.items():
        name = cells[1]
        key = cells[2].strip("`")
        description, flavor = prose[unit_id]
        if prefix == "P":
            if len(cells) == 7:
                cost, cooldown = cells[3], cells[4]
            elif len(cells) == 8:
                cost, cooldown = cells[3], cells[5]
            else:
                raise ValueError(f"{unit_id} 表格列数异常：{len(cells)}")
            result[unit_id] = Unit(
                unit_id,
                name,
                key,
                description,
                flavor,
                "专注",
                cost,
                "恢复",
                cooldown,
            )
        else:
            result[unit_id] = Unit(
                unit_id,
                name,
                key,
                description,
                flavor,
                "耐久",
                cells[3],
                "速度",
                cells[4],
            )
    return result


def parse_entries(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^\[([^\]]+)\]\n", text))
    entries: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        entries[match.group(1)] = text[match.end() : end].rstrip("\n")
    return entries


def replace_entry(text: str, key: str, value: str) -> str:
    pattern = re.compile(
        rf"(?ms)^\[{re.escape(key)}\]\n.*?(?=^\[[^\]]+\]\n|\Z)"
    )
    if not pattern.search(text):
        raise KeyError(f"LawnStrings.txt 缺少 [{key}]")
    replacement = f"[{key}]\n{value.strip()}\n\n"
    return pattern.sub(lambda _: replacement, text, count=1)


def gbk_width(text: str) -> int:
    return len(text.encode("cp936", errors="strict"))


def wrap_gbk(text: str, limit: int = WRAP_BYTES) -> list[str]:
    paragraphs = [part.strip() for part in text.splitlines() if part.strip()]
    output: list[str] = []
    closing = "，。！？；：、）】》”'"
    for paragraph in paragraphs:
        line = ""
        for char in paragraph:
            if line and gbk_width(line + char) > limit and char not in closing:
                output.append(line)
                line = char
            else:
                line += char
        if line:
            output.append(line)
    return output


def first_sentence(text: str) -> str:
    match = re.match(r".*?[。！？]", text)
    return match.group(0) if match else text


def stat_lines(unit: Unit) -> list[str]:
    visible = f"{unit.stat_label}：{unit.stat_value}"
    if unit.extra_label:
        visible += f"；{unit.extra_label}：{unit.extra_value}"
    lines = wrap_gbk(visible)
    lines[0] = lines[0].replace(
        f"{unit.stat_label}：",
        f"{{KEYWORD}}{unit.stat_label}：{{STAT}}",
        1,
    )
    return lines


def render_description(unit: Unit) -> str:
    lines = wrap_gbk(unit.description)
    lines.append("{SHORTLINE}")
    lines.extend(stat_lines(unit))
    lines.append("{SHORTLINE}")
    lines.append("{FLAVOR}")
    lines.extend(wrap_gbk(unit.flavor))
    return "\n".join(lines)


def render_tooltip(unit: Unit) -> str:
    lines = wrap_gbk(first_sentence(unit.description), 52)
    requirement = UPGRADE_REQUIREMENTS.get(unit.unit_id)
    if requirement:
        lines.append(f"(需要{requirement})")
    return "\n".join(lines)


def build(current: str) -> tuple[str, dict[str, Unit], dict[str, Unit]]:
    plants = parse_doc(PLANT_DOC, "P")
    zombies = parse_doc(ZOMBIE_DOC, "Z")
    entries = parse_entries(current)

    aliases: dict[str, str] = {}
    for unit in [*plants.values(), *zombies.values()]:
        if unit.unit_id == "Z27":
            continue
        old_name = entries.get(unit.key, "").strip()
        if old_name and old_name != unit.name:
            aliases[old_name] = unit.name

    result = current
    target_names = sorted(
        {unit.name for unit in [*plants.values(), *zombies.values()]},
        key=len,
        reverse=True,
    )
    placeholders: dict[str, str] = {}
    for index, target in enumerate(target_names):
        placeholder = f"@@USTC_UNIT_{index:02d}@@"
        if placeholder in result:
            raise ValueError(f"文案意外包含内部占位符 {placeholder}")
        if target in result:
            result = result.replace(target, placeholder)
            placeholders[placeholder] = target

    canonical = dict(CANONICAL_ALIASES)
    for old, new in CANONICAL_ALIASES.items():
        if "僵尸" in old:
            canonical[old.replace("僵尸", "错题")] = new
    replacements = {**aliases, **canonical, **GENERIC_REPLACEMENTS}
    for old, new in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        result = result.replace(old, new)
    for placeholder, target in placeholders.items():
        result = result.replace(placeholder, target)

    for unit in plants.values():
        result = replace_entry(result, unit.key, unit.name)
        result = replace_entry(result, f"{unit.key}_TOOLTIP", render_tooltip(unit))
        result = replace_entry(result, f"{unit.key}_DESCRIPTION", render_description(unit))

    for unit_id, unit in zombies.items():
        if unit_id == "Z27":
            if unit.key in parse_entries(result):
                result = replace_entry(result, unit.key, unit.name)
            continue
        result = replace_entry(result, unit.key, unit.name)
        result = replace_entry(result, f"{unit.key}_DESCRIPTION", render_description(unit))

    current_keys = parse_entries(result)
    for key, value in FIXED_TEXT.items():
        if key in current_keys:
            result = replace_entry(result, key, value)

    result = "\n".join(line.rstrip() for line in result.splitlines())
    return result.rstrip("\n") + "\n", plants, zombies


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true", help="write the synchronized CP936 file")
    mode.add_argument("--check", action="store_true", help="fail when the file is not synchronized")
    args = parser.parse_args()

    raw = LAWNSTRINGS.read_bytes()
    current = read_cp936(LAWNSTRINGS)
    generated, plants, zombies = build(current)
    generated_bytes = generated.replace("\n", "\r\n").encode("cp936", errors="strict")

    if args.check:
        if generated_bytes != raw:
            print("LawnStrings.txt 尚未与设计文档同步", file=sys.stderr)
            return 1
        print(
            f"同步检查通过：{len(plants)} 个植物，{len(zombies) - 1} 个图鉴敌人，"
            f"SHA-256 {sha256(raw)}"
        )
        return 0

    before = sha256(raw)
    write_cp936(LAWNSTRINGS, generated)
    after_data = LAWNSTRINGS.read_bytes()
    print(f"已写入 {LAWNSTRINGS.relative_to(ROOT)}")
    print(f"原始基线 SHA-256：{BASELINE_SHA256}")
    print(f"写入前 SHA-256：{before}")
    print(f"写入后 SHA-256：{sha256(after_data)}")
    print(f"同步条目：{len(plants)} 个植物，{len(zombies) - 1} 个图鉴敌人")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
