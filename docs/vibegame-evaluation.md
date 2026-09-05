# VibeGame 调研与接入建议

## 结论

VibeGame 可以辅助 PvZ-USTC，但应当作为**独立的 Web 机制沙盘和开发流程参考**使用，不应直接初始化到当前仓库根目录，也不能代替现有的 EXE、PAK、`reanim.compiled` 和 GBK 文案工具链。

最值得试用的部分有三项：

1. 用可暂停、逐帧推进和读取状态的 2D Web 运行时，先验证暖气片减速、GPA 完整度和 DDL 空投扣分等 S3 规则。
2. 把“实现、静态审查、实机游玩、最终复核”分开，补强现有的回归清单和证据链。
3. 选择性使用图片分析、标注、切图、背景移除和动画预览工具处理原创素材；生成结果仍需经过本项目的尺寸契约和 PAK 构建门禁。

不建议把完整八智能体团队直接放进当前仓库。它会引入大量配置、技能、钩子、骨架和引擎文件；默认团队配置还会以跳过权限检查的方式启动部分 CLI。当前仓库同时含有原版二进制基线和未提交的本地开发包，隔离运行更安全，也更容易审查成果来源。

## 调研基线

本次调研固定到 VibeGame 提交 [`cab478bf2dafe93bd586aa1043a1e2182f4da197`](https://github.com/tettethu/VibeGame/tree/cab478bf2dafe93bd586aa1043a1e2182f4da197)，提交时间为 2026-08-30。仓库当时没有版本标签或 GitHub Release，仍应按早期版本管理，不要依赖浮动的 `main` 分支。

VibeGame 0.1.0 由以下部分组成：

- Python 3.12+ CLI，负责初始化、校验、运行、素材处理、发布和团队调度。
- Phaser 3.80.1 上的文本化 2D 引擎；项目由 `project.json`、场景 JSON、节点 JSON、JavaScript 脚本和素材清单组成。
- 八个角色：orchestrator、designer、artist、architect、programmer、auditor、player、reviewer。
- 帧同步运行接口，可暂停、逐帧推进、注入输入、读取节点状态、截图和执行受控检查。
- 可复用的 skeleton、module 和 contract。当前内置骨架包括横版 Boss、卡牌、地牢射击、切水果和弹跳跑酷，没有塔防或 PvZ 类骨架。

架构与限制见[仓库 README](https://github.com/tettethu/VibeGame/blob/cab478bf2dafe93bd586aa1043a1e2182f4da197/README.md)、[安装说明](https://github.com/tettethu/VibeGame/blob/cab478bf2dafe93bd586aa1043a1e2182f4da197/docs/SETUP.md)和[技术报告](https://github.com/tettethu/VibeGame/blob/cab478bf2dafe93bd586aa1043a1e2182f4da197/technical_report.pdf)。

## 本机实测

测试环境：Windows、Python 3.12.8、uv 0.11.14、Chrome、Codex CLI。所有操作都在系统临时目录的浅克隆和临时项目中完成，没有改写当前仓库的 `main.pak` 或安装全局 Codex 钩子。

### 已通过

- 使用隔离的 uv 环境安装全部 69 个 Python 依赖并启动 CLI。
- 对五个内置 skeleton 运行静态检查；全部通过。`roguelike-dungeon-shooter` 另有两个动态实例预加载警告，其余业务警告为 skeleton 没有自带 `engine/`、运行时采用源码回退。
- 启动 `2d-action-boss-fight`，连接 Chrome 运行时并停在第 0 帧。
- 读取完整节点快照、保存截图、精确推进 120 帧并再次读取快照。Boss 在这段时间内进入 AI 行为，玩家生命由 5 降到 4，证明状态读取、逐帧推进和运行反馈确实可用。
- 在空目录中执行中文初始化；共生成 315 个文件，约 2.20 MiB，随后 `vibegame check` 全部通过。
- 对本项目 P01 概念图试用 `art tree`、`art analyze` 和 `art label`。图片尺寸、透明度分析和辅助标注可用。
- 运行本仓库的三机制沙盘及自动 bot：重叠的两个暖气片得到 `activeHeaterCount=2` 但速度仍为 `0.8`；寒冰开启后变为 `0.5`；一次保险和五次成功空投后只计四次，GPA 为 `76`；被阻止的空投不再扣分；关闭寒冰后恢复 `0.8`。bot 返回 `status=done`，11 个决策点均通过且无控制台错误，详见[运行证据](../prototypes/vibegame-mechanics-lab/tests/evidence/v0.1-runtime.md)。

### 已确认的问题

1. **中文 Windows 控制台编码**

   默认 GBK 控制台中，`vibegame init` 打印 `✓` 时会抛出编码异常。PowerShell 中先设置以下变量可绕过：

   ```powershell
   $env:PYTHONUTF8 = '1'
   $env:PYTHONIOENCODING = 'utf-8'
   ```

2. **中文路径兼容不完整**

   `vibegame art tree` 能读取当前中文路径下的 PNG，但 `vibegame art analyze` 内部使用的 OpenCV 不能直接打开该路径。把输入复制到纯 ASCII 临时路径后可以正常分析。若正式接入素材流程，应由包装脚本自动创建临时副本，不能要求迁移整个仓库。

3. **完整团队依赖 Unix 工具**

   官方 `setup.sh` 强制检查 `tmux`。Windows 原生 PowerShell 没有 `tmux`；本机 WSL Ubuntu 有 `tmux`，但还没有 WSL 内的 uv 和 Codex CLI。CLI、静态检查和前台运行时可以在 Windows 上工作，完整八角色调度应放进准备好的 WSL 环境再试。

4. **初始化会侵入现有仓库**

   `vibegame init` 会复制 `AGENTS.md`、`.codex/config.toml`、Codex/Claude skills、项目钩子、引擎、模块、骨架和规格文档。默认还会先取消已有暂存状态，再创建 `chore: vibegame init` 提交。不得在当前仓库根目录直接运行；即使在隔离目录中试验，也应先加 `--no-commit`。

5. **运行与生成有外部依赖**

   页面入口从 jsDelivr 加载 Phaser。完整视觉工作流还需要单独配置图片生成 API 和 VLM，可能产生费用；默认模板并不包含离线 Phaser 副本。没有用户明确提供的密钥时，只使用本地静态检查、素材处理和运行时功能。

## 与 PvZ-USTC 的适配度

| VibeGame 能力 | 适配度 | 在本项目中的用途 | 边界 |
| --- | --- | --- | --- |
| GDD、PRD、contract 和角色分工 | 高 | 整理机制验收条件，分离实现与复核 | 本项目已有成熟文档，只借鉴缺失部分 |
| 帧同步运行与状态快照 | 高 | 在 Web 沙盘中验证 S3 状态机和边界条件 | 不能观察原版 PvZ 进程，也不产生 x86 补丁 |
| Phaser 文本化场景/节点 | 中高 | 快速搭建五路草坪和事件模拟器 | 结果是独立 Web 原型，不是原版关卡文件 |
| 素材分析、标注、切图、预览 | 中高 | 辅助原创 PNG 部件和 sprite sheet 制作 | 中文路径需包装；最终仍过本项目契约门禁 |
| AI 图片生成和分层 | 条件适用 | 概念图或原创部件候选 | 需要 API、人工复核和来源记录；不能生成或提交原版混合素材 |
| 内置 modules/skeletons | 中低 | 状态条、遮罩 HUD、覆盖菜单可用于机制沙盘 | 没有塔防 skeleton，不能直接拼出 PvZ |
| 完整八智能体调度 | 条件适用 | 独立原型进入较长开发后再评估 | 依赖 tmux、全局钩子和多次模型调用，当前阶段偏重 |
| 直接修改 EXE/PAK/reanim | 不适用 | 无 | 两套格式和运行时完全不同 |

## 已加入的试点：三机制 Web 沙盘

仓库已加入独立的 [`prototypes/vibegame-mechanics-lab`](../prototypes/vibegame-mechanics-lab/README.md)。它只放原创占位图形和数值，不复制 `PlantsVsZombies.exe`、`main.pak`、原版贴图或 VibeGame 引擎源码。它不是第二套正式游戏，而是 v0.4 的可执行规格；运行时从固定提交的外部 VibeGame 检出目录加载引擎。

![三机制沙盘实测画面](images/vibegame/mechanics-lab-v01.png)

第一版只做一条泳道和三个事件，确认规则后再扩成五路：

1. 敌人以基准速度 `1.0` 前进。
2. 进入暖气片范围后速度为 `0.8`；多个暖气片不叠加。
3. 寒冰状态为 `0.5`，优先于暖气片的 `0.8`。
4. GPA 初值 100；自动退课保险触发扣 8。
5. DDL 空投只有成功带走单位并离开屏幕后扣 4；被击败、被弹开或尚未离场不扣，同关最多计算四次。

运行状态至少暴露：

```json
{
  "gpa": 100,
  "insuranceTriggerCount": 0,
  "ddlSuccessCount": 0,
  "heaters": [],
  "enemies": [
    {
      "lane": 0,
      "baseSpeed": 1.0,
      "effectiveSpeed": 1.0,
      "insideHeater": false,
      "iced": false
    }
  ]
}
```

建议用 VibeGame 的逐帧接口保存以下自动证据：

- 敌人进入和离开暖气片范围前后的位移差。
- 两个暖气片重叠时仍为 `0.8`。
- 寒冰与暖气片同时存在时为 `0.5`，寒冰结束后回到 `0.8`。
- DDL 的成功离场、被击败、被弹开和第五次成功四种分支。
- 暂停、恢复、重开和离开关卡后状态是否清理。

沙盘通过后，只把**规则表、状态转换和测试序列**带回当前仓库，再进入 Ghidra/x32dbg 定位和 AOB 补丁设计。不要把 Phaser 脚本机械翻译成注入代码，也不要把 Web 原型通过视为原版实机验证。

## 建议的使用方式

### 只运行框架和骨架

官方推荐在 Linux 或 WSL 中使用：

```bash
git clone https://github.com/tettethu/VibeGame.git
cd VibeGame
./setup.sh
```

首次配置会要求选择 Claude Code 或 Codex，并配置 VLM 与图片生成服务。不要猜测或代填密钥。

创建独立实验项目时：

```bash
mkdir ../pvz-ustc-mechanics-lab
vibegame init ../pvz-ustc-mechanics-lab --lang zh-CN --no-commit
cd ../pvz-ustc-mechanics-lab
vibegame check
vibegame run --activate
```

运行后可用：

```bash
vibegame play snapshot
vibegame play continue -f 120
vibegame play screenshot -o logs/frame-120.png
```

### 只使用素材工具

素材工具可以独立于团队调度使用。对本项目最可能有用的是：

```bash
vibegame art tree <图片或目录>
vibegame art analyze <图片>
vibegame art label <图片> --bbox "x,y,w,h:名称" -o <标注图>
vibegame art cut --help
vibegame art animation --help
vibegame art rmbg --help
```

所有 AI 生成命令都应把原始提示词、模型、输出和人工修改记录进素材来源清单。当前的 `assets-src/game/*.contract.json` 仍是能否进入 PAK 的最终门禁。

## 许可证与发布

VibeGame 代码采用 [Apache License 2.0](https://github.com/tettethu/VibeGame/blob/cab478bf2dafe93bd586aa1043a1e2182f4da197/LICENSE)。可以使用和修改，但分发其代码或衍生代码时需要附带许可证、保留适用的声明，并显著标明被修改的文件。仓库 LICENSE 末尾还含第三方 MIT 声明；若复制对应内容也要一并保留。

仓库 README 中的商业部署通知被作者明确写成自愿通知，不增加 Apache 2.0 的许可限制。

VibeGame 的许可证只覆盖该仓库的代码和随附内容，不会授予 PvZ、PopCap、EA、学校标识、参考图片或生成模型输出的权利。现有“玩家自备合法原版并应用差分补丁”的发布路线不变。

## 决策

- **现在采用**：运行时逐帧验证思路、角色分离的审查流程、素材标注/分析工具。
- **小规模试点**：继续扩充现有三机制 Web 沙盘的逐帧回归序列。
- **暂缓**：完整八智能体团队、自演化写回、AI 批量生成正式素材。
- **不采用**：把当前 PvZ-USTC 根仓库初始化为 VibeGame 项目，或用 Phaser 工程取代原版补丁路线。
