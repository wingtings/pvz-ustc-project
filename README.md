# PvZ-USTC

一个以中国科学技术大学校园生活为背景的《植物大战僵尸》一代同人改版。玩家用科豆、蝌蝻和实验器材抵挡课程、报告与截止日期形成的“错题潮”，守住成绩终端里的 GPA 数据。

项目起于 2025 年新生科学社会研讨课，2026 年 8 月重启。当前处于**可运行的早期改版阶段：全量文案已同步，首批局部美术已进入游戏，构建与回滚可复现；招牌机制和五章关卡重排仍待接入。** 日常战斗主要沿用原版规则。

## 当前完成度

初次核查日期：**2026-09-05**，核查基线为 [`3fd3d3a`](https://github.com/wingtings/pvz-ustc-project/commit/3fd3d3a4b5271bad4b01043e1b42aab8b0f6d253)。随后已整理机制沙盘入库，并实现 R1 独立运行目录；当前阶段验证见 [R1 记录](tests/checklists/r1-runtime-workspace.md)。下表分别统计文案、资源与玩法。

| 方向 | 已有成果 | 距离完成还缺什么 |
| --- | --- | --- |
| 运行基线 | Windows PC `1.0.0.1051`；已有图鉴、白天与泳池等实机切片记录 | 新存档连续通关、五场景完整回归、第二台 Windows 验证 |
| USTC 文案 | **49/49 植物、26/26 图鉴敌人**的名称与说明已同步；869 个文本键通过检查 | 75 个槽位逐项截断检查，商店、小游戏、结局及跨场景人工验收 |
| 角色美术 | **5 个目标槽位、16 项资源替换**：P01、P02、P04、Z01、Z03；已有局部实机验证 | 首批动作与场景缺口，其他角色、场景和界面；现阶段仍复用原版动画骨架 |
| 数值与构建 | 两处常量补丁、确定性 PAK、逐字节回滚；独立运行目录已装配；完整检查 **92 项测试通过** | 两种运行目录的启动画面观察，最终平衡、五场景及三个小游戏回归 |
| 三项招牌机制 | 原版游戏接入 **0/3**；已入库 Web 沙盘有减速与扣分规则的初步验证 | 暖气片范围减速、GPA 结算评级、DDL 真实离场事件及逻辑钩子 |
| 五章战役 | 世界观、50 关节奏与解锁方向已写入设计文档 | 可审查的关卡配置/补丁，以及逐章通关证据 |
| 发布与协作 | 构建脚本、清单和测试记录已入库；[Windows/Ubuntu 公开 CI 均通过](https://github.com/wingtings/pvz-ustc-project/actions/runs/33946361436) | 尚无 Release，玩家用安装与回滚流程待完成 |

首批视觉覆盖的是 75 个目标槽位中的 5 个，约 **6.7% 的槽位已开始定向制作**，并不表示这五个角色已完成全部美术验收。共享弹丸和躯干会影响更多单位，也不据此增加“已完成角色”数量。

[VibeGame 机制沙盘](prototypes/vibegame-mechanics-lab/README.md)和[调研记录](docs/vibegame-evaluation.md)已随 `485559f` 提交到 GitHub。沙盘用模拟输入验证速度倍率、扣分与上限；它还没有真实空投事件链或关末评级界面，不能算作原版机制已实现。

## 改动是否丰富

**文案、制作工具和验证资料已经比较充实，玩家可感知的新玩法仍然偏少。** 相比 2025 年 v0.1 提交 `7f44e19`，初次核查基线 `3fd3d3a` 新增 28 次提交，涉及 102 个文件，增加 12,104 行、删除 978 行。其中有 13 个 Python 工具、13 个自动测试模块、16 份素材契约和 18 份已有验收记录；这是核查时的历史统计，行数包含文档、测试和配置。

现在能在游戏里看到眼镜与蓝书、学习便签花瓣、三档校园墙体、卷面衣袖、破损书套和绿色圆圈。场景、音效、主要动画动作与关卡规则仍大量沿用原版。下一阶段最能提高辨识度的工作是**让第一章形成完整试玩体验，并把暖气片范围减速接入原版**。

![白天实机切片：眼镜蓝书科豆、绿色圆圈、校园墙体、卷面本体与蓝色书套](docs/images/v0.5/p01-z01-z03-adventure-v01.png)

上图来自 2026-08-31 的局部实机观察，不代表整章验收。更多证据见[绿色圆圈飞行与共享躯干](tests/checklists/v0.5-p01-z01-z03-runtime.md)、[双发/三线复用与火化](tests/checklists/v0.5-p01-family-fire-runtime.md)、[Z01 动作与 Z03 书套四阶段](tests/checklists/v0.5-z01-z03-actions-runtime.md)。火化仍使用原版火球资源，暖气片的范围减速尚未生效。

## 运行与开发检查

现在可用[独立运行目录工具](docs/runtime-workspace.md)指定干净输入，在根目录仍保留开发 PAK 的情况下构建。将示例路径换为匹配哈希的合法原件目录：

```powershell
python tools/check_project.py --baseline-dir C:\Games\PvZ-clean
python tools/runtime_workspace.py --build --baseline-dir C:\Games\PvZ-clean --profile visuals
python tools/runtime_workspace.py --launch --profile visuals
```

工具会生成含 96 个游戏文件的 `dist/runtime/visuals`，记录全部文件哈希，并以该目录为工作目录启动。临时数值版使用 `--profile constant-proof`。当前已完成装配与自动校验，新的启动实机观察仍待补；存档需要另行备份并使用独立测试玩家。

目前提供的是开发工程，尚无面向玩家的一键安装包。游戏需要匹配基线的合法原版文件。在包含 EXE、DLL、PAK 和配套资源的完整运行目录中启动：

```powershell
.\PlantsVsZombies.exe
```

工作目录必须是该完整运行目录。只运行 `dist` 里的补丁 EXE 不会自动带齐资源。干净仓库基线包含文案改动，首批美术需要另行构建并装入独立的运行副本。

以下命令在**EXE 和 PAK 均匹配基线哈希的独立工作副本根目录**执行。本轮使用 Windows / Python 3.12.8 验证；原版改版工具不依赖 VibeGame。

```powershell
python tools/check_lawnstrings.py
python tools/sync_lawnstrings.py --check
python -m unittest discover -s tests -p "test_*.py"
python tools/apply_binary_patches.py --check
python tools/build_pak_overlay.py --roundtrip-check
python tools/check_game_asset.py --registry patches/manifests/v0.5-first-slice-contracts.json
```

生成首批五槽位的本地候选，再构建十六项累计资源包：

```powershell
python tools/build_p01_sprites.py --build --check
python tools/build_p02_sprites.py --build --check
python tools/build_p04_sprites.py --build --check
python tools/build_z01_sprites.py --build --check
python tools/build_z03_sprites.py --build --check
python tools/build_pak_overlay.py --build patches/manifests/v0.5-p01-green-circle-p02-p04-z01-sleeves-z03-ingame.json
```

输出为 `dist/v0.5/main-p01-green-circle-p02-p04-z01-sleeves-z03-ingame.pak`，不是完整游戏目录。数值验证副本可用 `python tools/apply_binary_patches.py --apply` 生成，用 `--reverse` 另行生成回滚副本；**P01 费用 75、P04 耐久 4200 是临时测试值**，基线仍为 100 和 4000。详细参数见[工具说明](tools/README.md)和[PAK 构建说明](docs/asset-build-pipeline.md)。

### 基线与开发包

| 文件角色 | SHA-256 |
| --- | --- |
| 干净基线 `PlantsVsZombies.exe` | `6F1729369AC9C5F859E8F3B55FE7D513FBC20B5C54127FD3A1C7E500237FDE6F` |
| 干净基线 `main.pak` | `3B5291C6600076AAF1791AE1FB2DBF247290A23E903D1D376413DA17358E049D` |
| 十六项美术累计 PAK | `9DB70BB44031EF6B12ED92FF9F79BC9737B382D2F0D0383607DA1AAABAADB90B` |

2026-09-05 核查时，本地根目录的 `main.pak` 已是上表第三项开发包，因此直接在该目录运行资源检查会报“基线哈希不匹配”。本次在独立的干净副本中完成了 77 项测试、完整素材构建和补丁回滚，未覆盖现有开发包。遇到同样情况，应保留当前文件并换用干净的构建副本；不能把开发包哈希改填为原件哈希来绕过校验。具体结果见[本轮仓库核查](tests/checklists/2026-09-05-repository-audit.md)。

`properties/LawnStrings.txt` 使用 CP936/GBK 和 CRLF；设计文档使用 UTF-8。通过同步工具更新游戏文案，避免直接改变编码。不同 EXE 版本的地址与数据布局不能混用。

## 下一步开发方向

1. **补齐运行目录实机验收。** 干净输入、生成包和运行目录已分离，沙盘已入库，公开 CI 已通过；下一步观察两种配置的实际启动与游戏表现。
2. **交付第一章完整试玩。** 沿用当前关序，从新存档连续完成 1-1 至 1-10；补齐关键文案、Z01 单体断臂/死亡、P01 眨眼与必要场景检查。这一步验收现有改版，不提前算作自定义关卡完成。
3. **让暖气片成为第一项原版新机制。** 先补规则沙盘边界，再在独立测试关验证 80% 范围减速、不叠加、寒冰优先及独立开关。
4. **随后接 GPA 与 DDL，再扩关卡和美术。** 第二批视觉优先服务暖气片、寒冰科豆、专注值图标和首章界面；其余四章逐章制作可玩切片。

完整依赖、验收条件与首批遗留项见[开发路线图](docs/roadmap.md)。`v0.2/v0.3/v0.4/v0.5` 是沿用的工作轨道编号，当前存在交叉推进，不表示已发布到 v0.5。

## 世界与文档

| 章节方向 | 场景意象 | 设计重点 |
| --- | --- | --- |
| 数院草坪 | 东区草坪 | 白天教学、专注值经济 |
| 物院实验夜 | 一教实验区域 | 夜间、报告墓碑、穿透与控制 |
| 化院花园 | 花园与实验水槽 | 水道、防水实验台、冰道与车辆 |
| 计算机雾夜 | 西区机房 | 雾、云端作业、地下与空投 |
| 生院温室顶 | 虚构屋顶温室 | 培养皿、抛射与最终首领 |

战斗资源“专注值”沿用原版阳光经济。GPA 计划用于关末完整度评级，不用于支付卡片费用。上表是章节设计方向，尚未完成对应场景重绘和关卡重排。

- [文档入口](docs/README.md) · [世界观与战役](docs/worldbuilding.md)
- [植物原型](docs/plants.md) · [敌人原型](docs/zombies.md) · [数值与关卡规范](docs/balance-and-levels.md)
- [改版技术调研](docs/modding-research.md) · [首批美术资源清单](docs/art-resource-inventory.md)
- [v0.3 常量补丁](docs/v0.3-patching.md) · [原创素材 PAK 构建](docs/asset-build-pipeline.md)
- [VibeGame 调研与接入建议（本地试验）](docs/vibegame-evaluation.md) · [开发路线图](docs/roadmap.md)

## 开发记录

- 2025-02-25：记录暖气片、绿色圆圈、五个专业章节等初始想法。
- 2025-03-03：确认文案、PAK 解包和反汇编路线。
- 2025-04-14：提交 v0.1 小型文案修改。
- 2026-08-30：重启，完成设计基线与全量文案同步，建立常量补丁、PAK 构建和首批美术流程。
- 2026-08-31：累计到 16 项资源，补充绿色圆圈复用、火化、Z01 动作和 Z03 书套实机证据。
- 2026-09-04：本地机制沙盘留下首轮规则验证记录，尚未接入原版。
- 2026-09-05：核查 GitHub 与工作目录，重跑干净基线测试、构建与回滚，更新开发优先级。

最初的想法见[开发日志](https://wingtings.pages.dev/2025/02/25/pvz-ustc%E5%BC%80%E5%8F%91%E6%97%A5%E5%BF%97/)。

## 分发与声明

本项目是非官方、非商业的学习与同人创作，不代表中国科学技术大学、Electronic Arts、PopCap 或其许可方。仓库保留了早期开发快照中的游戏文件；公开发行前需要审查仓库历史，并改为让玩家自备合法原版文件后应用差分补丁。发布包不应包含原版 EXE、PAK、音乐或整套贴图。

混有原版像素的合成 PNG 和生成包仅用于本地构建，Git 保存制作配方、契约和验证记录。

This project is not endorsed by or affiliated with EA or its licensors. It is also not endorsed by or affiliated with PopCap or the University of Science and Technology of China.

使用或分发前请自行核对 [EA 用户协议](https://www.ea.com/legal/user-agreement?isLocalized=true)和 [EA 内容政策](https://help.ea.com/en/articles/security-and-rules/ea-content-policy/)。
