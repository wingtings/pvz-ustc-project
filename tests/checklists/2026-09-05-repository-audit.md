# 2026-09-05 仓库核查

核查范围：GitHub 当前版本、本地工作目录、构建与自动测试。环境为 Windows / Python 3.12.8。本轮未重新启动原版游戏或 VibeGame；实机完成度依据此前已存档的观察记录，机制原型另检查了本地脚本与 bot 的实际覆盖范围。

## GitHub 快照

通过 Git 远端查询与 GitHub API 读取；以下统计固定于本次文档修改前。

| 项目 | 结果 |
| --- | --- |
| 仓库 | [wingtings/pvz-ustc-project](https://github.com/wingtings/pvz-ustc-project)，公开、未归档 |
| 默认分支 | `main`，远端仅见这一分支 |
| 远端与本地 HEAD | [`3fd3d3a4b5271bad4b01043e1b42aab8b0f6d253`](https://github.com/wingtings/pvz-ustc-project/commit/3fd3d3a4b5271bad4b01043e1b42aab8b0f6d253)，提交日期 2026-08-31 |
| 提交数 | 共 30 次；相比 v0.1（`7f44e19`）新增 28 次 |
| 版本标签 / Release | 0 / 0 |
| 开放 Issue / PR | 0 / 0 |
| GitHub Actions | API 返回 0 次运行；当前提交没有 `.github` 工作流文件 |

核查入口：[分支](https://github.com/wingtings/pvz-ustc-project/branches)、[Release](https://github.com/wingtings/pvz-ustc-project/releases)、[Issue](https://github.com/wingtings/pvz-ustc-project/issues)、[PR](https://github.com/wingtings/pvz-ustc-project/pulls)、[Actions](https://github.com/wingtings/pvz-ustc-project/actions)。

## 改动规模与实际覆盖

`git diff 7f44e19..3fd3d3a --shortstat`：102 个文件改变，12,104 行增加，978 行删除。文件分布如下；这是版本间内容差异，不等于游戏完成率。

| 目录 | 改变文件数 | 主要内容 |
| --- | ---: | --- |
| 根目录 | 2 | README、忽略规则 |
| `assets-src` | 18 | 概念资料与 16 份素材契约 |
| `docs` | 26 | 设计、实现说明、实机截图 |
| `patches` | 10 | 常量清单、资源包清单、契约注册表 |
| `properties` | 1 | GBK 游戏文案 |
| `tests` | 31 | 13 个自动测试模块、18 份验收记录 |
| `tools` | 14 | 13 个 Python 工具及说明 |

文案覆盖 49 个植物与 26 个图鉴敌人；视觉定向制作覆盖 P01、P02、P04、Z01、Z03 五个槽位，共 16 项资源。当前改版仍复用原版动画骨架；上述版本差异中未改变基线 EXE、PAK 或根目录的 `reanim/`、`images/`、`particles/`、`data/`，二进制与美术改动由本地构建生成。

因此评估为：工程、文案和验证资料已较充实，视觉仍是首批局部替换，独特玩法尚未进入原版。三项机制接入为 0/3；五章自定义关卡尚无配置/补丁与完整通关证据。

## 本地未提交状态

开始核查时已有修改：`.gitignore`、根 README、文档索引、`main.pak`；另有未跟踪的 `docs/vibegame-evaluation.md`、`docs/images/vibegame/` 与 `prototypes/`。

本地 PAK 哈希与十六项累计清单的预期输出完全一致，是已知开发包。EXE 仍匹配基线。本轮保留这些文件及修改，用当前提交的独立导出副本完成基线验证。

| 文件角色 | SHA-256 |
| --- | --- |
| 基线 EXE | `6F1729369AC9C5F859E8F3B55FE7D513FBC20B5C54127FD3A1C7E500237FDE6F` |
| 临时数值补丁 EXE | `CB0E0FFF4A530164582E3E0A86FA046A5217AC4293F961A75FB3097C853899B8` |
| 基线 PAK | `3B5291C6600076AAF1791AE1FB2DBF247290A23E903D1D376413DA17358E049D` |
| 十六项累计 PAK / 核查时本地 PAK | `9DB70BB44031EF6B12ED92FF9F79BC9737B382D2F0D0383607DA1AAABAADB90B` |

## 本轮执行结果

| 检查 | 当前工作目录 | 独立干净副本 |
| --- | --- | --- |
| 文案编码、869 键与同步幂等性 | 通过 | 通过 |
| EXE 补丁预演 | 通过 | 通过 |
| 自动测试 | 发现 77 项；仅运行 7 项，13 个测试类初始化因 PAK 哈希不匹配报错 | **77 项全部通过，0 失败/错误/跳过** |
| PAK 零替换逐字节往返 | 基线哈希校验拒绝 | 通过，2,413 个资源 |
| 美术盘点与概念稿检查 | 未重复执行 | 通过 |
| 16 份契约注册表 | 未重复执行 | 通过，5 个槽位，无漏登记/重复目标 |
| 五槽位候选生成及累计 PAK 构建 | 未覆盖现有候选或运行包 | 通过，替换 16 项，输出与上表开发包哈希一致 |
| 数值补丁应用与回滚 | 仅预演 | 通过；回滚副本与基线逐字节一致 |

当前工作目录的报错来自开发 PAK 被用作原件输入；没有据此判定补丁或素材算法损坏，也没有修改哈希门禁。

可复现命令见[README 开发检查](../../README.md#运行与开发检查)。本轮隔离副本和输出日志保存在被忽略的 `.work/repository-audit-20260905/`，不作为发行内容。

## 历史实机证据的边界

- [v0.2 文案冒烟](v0.2-text-smoke.md)：首轮启动、部分图鉴及 1-4 短时观察，尚非新存档或五场景完整验收。
- [v0.3 常量验证](v0.3-constant-patches.md)：P01 费用 75、P04 新对象耐久 4200 有实机证据，尚缺五场景与三类小游戏完整回归。DDL 的 450 本轮只验证文本断言。
- [首批动作与书套](v0.5-z01-z03-actions-runtime.md)：Z01 啃食/头部脱落、Z03 四阶段有证据；Z01 断臂实例重叠，替代袖片与死亡收尾仍需单体复核。
- [绿色圆圈复用与火化](v0.5-p01-family-fire-runtime.md)：已看到双发、三线和切换到原版火球；未测伤害倍率，未完成全部射手/场景回归，也不包含范围减速。
- [本地沙盘运行记录](../../prototypes/vibegame-mechanics-lab/tests/evidence/v0.1-runtime.md)：2026-09-04 有 11 次决策的 bot 通过记录。本轮源码确认 DDL 通过模拟输入直接计数，暖气片只按横坐标判断范围；尚无真实空投链、逐帧位移独立校验、多行空间规则、关末评级与原版逻辑钩子。

下一轮按[路线图](../../docs/roadmap.md)推进运行目录装配、首章连续试玩与暖气片原版接入；后续验收新增记录，不回写历史切片为“完整通过”。
