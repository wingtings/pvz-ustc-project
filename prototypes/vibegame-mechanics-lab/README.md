# PvZ-USTC VibeGame 机制沙盘

这是一个独立、无原版素材的可执行规格，用来验证 v0.4 三项机制的边界条件。它不会生成或修改 `PlantsVsZombies.exe`、`main.pak`、PAK 资源或 `reanim.compiled`。

当前切片包含：

- 敌人基准移动速度。
- 暖气片范围内 `0.8` 倍速，重叠范围不叠加。
- 寒冰 `0.5` 倍速并优先于暖气片。
- GPA 初值 100、自动退课保险扣 8。
- DDL 成功离场扣 4，被阻止不扣，同关最多计算四次。
- VibeGame 运行时快照中可检查全部验收状态。

![机制沙盘：两台暖气片重叠、寒冰开启、GPA 与 DDL 上限已触发](../../docs/images/vibegame/mechanics-lab-v01.png)

## 运行

先在另一个目录克隆固定版本的 VibeGame。本沙盘不把 VibeGame 引擎复制进当前仓库。

```powershell
git clone https://github.com/tettethu/VibeGame.git C:\work\VibeGame
git -C C:\work\VibeGame checkout cab478bf2dafe93bd586aa1043a1e2182f4da197

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

uv run --project C:\work\VibeGame vibegame check .
uv run --project C:\work\VibeGame vibegame run . --activate
```

上面的命令要在本目录中执行。`check` 会提示本目录没有自带 `engine/`；这是本试验刻意采用外部源码引擎造成的已知警告。

启动后可按：

| 按键 | 行为 |
| --- | --- |
| `P` | 把敌人放入两个暖气片的重叠范围 |
| `I` | 开关寒冰状态 |
| `Q` | 触发一次自动退课保险 |
| `D` | 记录一次成功离场的 DDL 空投 |
| `F` | 记录一次被阻止的 DDL 空投 |
| `R` | 重置全部状态 |

## 逐帧检查

在另一个终端、仍以本目录为工作目录执行：

```powershell
uv run --project C:\work\VibeGame vibegame play snapshot
uv run --project C:\work\VibeGame vibegame play input -a place_overlap
uv run --project C:\work\VibeGame vibegame play continue -f 1
uv run --project C:\work\VibeGame vibegame play snapshot

uv run --project C:\work\VibeGame vibegame play input -a toggle_ice
uv run --project C:\work\VibeGame vibegame play continue -f 1
uv run --project C:\work\VibeGame vibegame play snapshot
```

第一次放入重叠范围后，`Enemy.runtime.activeHeaterCount` 应为 2，`speedMultiplier` 仍应为 `0.8`。开启寒冰后，`speedMultiplier` 应变为 `0.5`。

连续触发五次 `ddl_success` 后，`ddlSuccessCount` 应停在 4，GPA 应从 100 降至 84；`ddl_blocked` 只增加被阻止计数，不改变 GPA。

也可以让仓库中的无模型 bot 自动完成全部断言并生成 trace、结果和录像：

```powershell
uv run --project C:\work\VibeGame vibegame run . --bot tests/bot/mechanics_smoke.py
```

bot 不调用 VLM 或图片生成服务。通过条件是 `result.json` 的 `status` 为 `done`，并且 trace 中依次出现暖气片重叠、寒冰优先、保险扣分、四次 DDL 扣分、第五次封顶和被阻止不扣分。

本次已通过的环境和关键状态见 [`tests/evidence/v0.1-runtime.md`](tests/evidence/v0.1-runtime.md)。

## 边界

沙盘通过只表示规则和状态转换成立。它不能证明原版 PvZ 的对象字段、调用时机、暂停行为或关卡清理路径已经找到；这些仍需按现有 v0.4 路线在 Ghidra/x32dbg 和实际游戏中验证。

VibeGame 采用 Apache License 2.0，固定来源见[VibeGame 仓库](https://github.com/tettethu/VibeGame/tree/cab478bf2dafe93bd586aa1043a1e2182f4da197)。本目录没有复制其引擎源码或随附素材。
