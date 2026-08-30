# PvZ-USTC

一个以中国科学技术大学校园生活为背景的《植物大战僵尸》一代同人改版。玩家在教学沙盘里用科豆、蝌蝻和实验器材抵挡课程、报告与截止日期形成的"错题潮"，守住成绩终端里的 GPA 数据。

项目最早来自 2025 年新生科学社会研讨课，搁置一年后于 2026 年重新开始。旧版完成了部分中文文案和界面文字，原创贴图、动画与主要机制还没有真正落地。本轮先把设定和数值写清楚，再按可验证的小版本推进。

## 当前状态

| 内容 | 状态 |
| --- | --- |
| 运行基线 | PC 版 `1.0.0.1051` |
| USTC 文案 | 49 个植物和 26 个图鉴敌人已同步，完整回归测试中 |
| 世界观与五章结构 | 设计完成 |
| 49 个植物槽位原型 | 设计完成，包含数值、机制与图鉴文案 |
| 26 个敌人图鉴槽位 | 设计完成，另含补考周变体 |
| 原创贴图与 reanim 动画 | P01 已通过白天实机观察；P02 学习造型与 P04 三档墙体已完成静态差分，并进入八替换累计 PAK，实机观察待完成 |
| 数值补丁 | v0.3 可重复构建与回滚已建立；P01 费用 100→75 已实机确认，P04 耐久与跨场景回归待完成 |
| 暖气片减速、GPA 评级、DDL 空投扣分 | 设计中，计划在逻辑钩子阶段实现 |

"设计完成"表示原型文档已经定稿，不表示对应内容已经写进游戏。

## 设计文档

- [文档入口](docs/README.md)
- [世界观与战役](docs/worldbuilding.md)
- [改版技术调研](docs/modding-research.md)
- [数值与关卡规范](docs/balance-and-levels.md)
- [植物原型](docs/plants.md)
- [敌人原型](docs/zombies.md)
- [首批美术资源清单](docs/art-resource-inventory.md)
- [v0.3 常量补丁](docs/v0.3-patching.md)
- [原创素材 PAK 构建](docs/asset-build-pipeline.md)
- [开发路线图](docs/roadmap.md)

## 五章方向

| 章节 | 场景 | 主要规则 |
| --- | --- | --- |
| 数院草坪 | 东区草坪意象 | 白天基础教学，建立专注值经济 |
| 物院实验夜 | 一教实验区域 | 夜间、报告墓碑、穿透和全屏控制 |
| 化院花园 | 花园与实验水槽 | 水道、防水实验台、冰道和车辆 |
| 计算机雾夜 | 西区机房意象 | 雾、云端作业、地下与空投威胁 |
| 生院温室顶 | 虚构屋顶温室 | 培养皿、抛射、投递车和最终首领 |

战斗资源暂定名为"专注值"，沿用原版阳光经济。GPA 是 v0.4 计划加入的关末完整度评级，不会被拿来支付卡片费用。

## 技术基线

当前仓库中的关键文件：

| 文件 | SHA-256 |
| --- | --- |
| `PlantsVsZombies.exe` | `6F1729369AC9C5F859E8F3B55FE7D513FBC20B5C54127FD3A1C7E500237FDE6F` |
| `main.pak` | `3B5291C6600076AAF1791AE1FB2DBF247290A23E903D1D376413DA17358E049D` |

`properties/LawnStrings.txt` 使用 CP936/GBK。不要直接转成 UTF-8，也不要把其他版本教程中的地址写入当前 EXE。资源、动画和玩法修改的具体方法见[改版技术调研](docs/modding-research.md)。

## 当前开发阶段

v0.2 只做完整文案版。目前全量名称、卡片提示和图鉴正文已经写入 GBK 游戏文件，并通过自动检查和首轮游戏内冒烟测试。尚未完成的是逐项截断检查、五种场景回归和新存档完整通关。

1. 统一全部植物、敌人、选卡、商店、小游戏和通关文字。
2. 保留原版槽位与大部分数值，不增加新角色数量。
3. 检查 GBK 编码、控制标记、图鉴换行和五种场景。
4. 首批资源清单已经完成；P01 的白天垂直切片已通过，P02 与 P04 的静态候选也已纳入累计补丁，其余槽位继续按独立提交推进。

文案由[同步工具](tools/README.md)从设计文档生成，测试范围记录在 [v0.2 文案冒烟测试](tests/checklists/v0.2-text-smoke.md)。首批美术对象和概念稿见[资源清单](docs/art-resource-inventory.md)。P01 的圆框眼镜与《电磁学千题解》、P02 的学习头带与便签花瓣、P04 的三档校园墙体，都由差分脚本从本地合法原件生成；Git 不保存混有原版像素的合成 PNG。构建细节见[原创素材 PAK 构建](docs/asset-build-pipeline.md)，P01 的实机证据见[白天垂直切片](tests/checklists/v0.5-p01-ingame.md)。v0.3 的[常量补丁框架](docs/v0.3-patching.md)已经能生成和逐字节回滚开发副本，下一步要补齐 P02 动画观察、P04 耐久切换和跨场景回归。完整安排见[开发路线图](docs/roadmap.md)。

## 开发记录

- 2025-02-25：记录最初背景、暖气片、绿色圆圈、五个专业章节等想法。
- 2025-03-03：确认 `LawnStrings.txt`、PAK 解包和反汇编修改路线。
- 2025-04-14：提交 v0.1 小型文案修改。
- 2026-08-30：重启项目，建立完整设计文档与技术路线。

去年的原始记录仍可在[开发日志](https://wingtings.pages.dev/2025/02/25/pvz-ustc%E5%BC%80%E5%8F%91%E6%97%A5%E5%BF%97/)查看。

## 分发与声明

本项目是非官方、非商业的学习与同人创作，不代表中国科学技术大学、Electronic Arts、PopCap 或其许可方。仓库保留了早期开发快照中的游戏文件，但公开发行前需要单独审查仓库历史，并改为让玩家自备合法原版文件后应用差分补丁。不要把原版 EXE、PAK、音乐或整套贴图打入发布包。

This project is not endorsed by or affiliated with EA or its licensors. It is also not endorsed by or affiliated with PopCap or the University of Science and Technology of China.

使用或分发前请自行核对 [EA 用户协议](https://www.ea.com/legal/user-agreement?isLocalized=true)和 [EA 内容政策](https://help.ea.com/en/articles/security-and-rules/ea-content-policy/)。
