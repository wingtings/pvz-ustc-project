# 原创素材 PAK 开发构建

状态：可重复构建链和 P01 头部、前叶像素契约已完成；尚无原尺寸角色替换件进入游戏。

验证日期：2026-08-30

## 为什么单独做构建链

直接解包、覆盖 PNG、再手工打包很难审查，也容易把整套原版素材提交进仓库。这里采用增量清单：仓库只保存原创替换件和它们的哈希，构建工具从本地 `main.pak` 取其余原资源，在 `dist` 生成开发用完整 PAK。

这条链与美术创作分开验收。构建通过只表示资源容器没有被破坏，不表示角色画得合适，也不表示游戏内动画已经正常。

## 安全边界

- 输入 `main.pak` 必须匹配 SHA-256 `3B5291C6600076AAF1791AE1FB2DBF247290A23E903D1D376413DA17358E049D`。
- 替换源必须位于 Git 可审查的 `assets-src`，不能从 `.work/pak-reference` 偷带原图。
- 每个替换件必须同时记录自己的 SHA-256 和目标原资源的 SHA-256。
- PNG 默认必须保持原画布宽高；改变动画锚点前不能靠放大画布“硬塞”。
- 替换目标必须在 PAK 中存在且只能声明一次。
- 输出只能写到被 Git 忽略的 `dist`，不能覆盖 `main.pak`。
- 重建后会再次解析 PAK，确认 2413 个条目、尺寸和数据边界仍然成立。

## P01 像素契约

两份契约把“在原版素材上局部修改”写成了机器可检查的条件，而不是只靠肉眼判断。

### 圆框眼镜头部

`assets-src/game/p01/PeaShooter_Head.contract.json` 约束第一张 70×65 头部。

| 条件 | 当前门禁 |
| --- | --- |
| PAK 目标 | `reanim/PeaShooter_Head.png` |
| 原件 | SHA-256 `89489D1DF066B4C89541455525447220437C5913F0F1E3E850A7A6116F241882` |
| 格式与画布 | 8 位非隔行 RGBA PNG，70×65 |
| 轮廓 | 4550 个像素的 Alpha 值必须逐一保持不变 |
| 允许改色范围 | 双眼周围 `x=34..65, y=7..32` |
| 保护范围 | 两只眼睛的瞳孔核心不得改色 |
| 改动规模 | 24–260 个可见像素 |
| 镜框要求 | 至少 18 个像素相对原件明显变暗 |

这里的 Alpha 门禁保留全部半透明抗锯齿值，不只是要求四角透明。允许区域之外的可见 RGB 也必须与原件一致，因此放大重绘、整体调色、改变脸型、棋盘格背景和误伤喷口都会被拒绝。

### 蓝色课本前叶

原 `PeaShooter_frontleaf.png` 为 67×40，动画会以约 0.555 倍缩放并跟随前叶摆动。中央 `x=20..48, y=0..32` 有足够透明空间容纳一本紧凑的竖向蓝书，因此首版可以把书本合入前叶，不必修改 `PeaShooter.reanim.compiled`。

`assets-src/game/p01/PeaShooter_frontleaf.contract.json` 要求：

- 不允许降低原件任何像素的 Alpha，原叶片不会被擦除。
- 只能在中央矩形新增或覆盖 180–650 个可见像素。
- 新增 Alpha 像素必须在 80–320 之间，防止整块画布变成不透明背景。
- 至少包含 120 个深蓝封面像素和 8 个浅色书页或书名像素。
- 外侧叶片、画布尺寸和动画锚点保持原样。

书名在游戏中会缩到十余像素高，不以逐字可读为验收条件；静态原尺寸稿可排“电磁”或简化白色题签，战场上优先保证蓝书轮廓可辨。

只检查契约与 PAK 原件是否吻合：

```powershell
python tools/check_game_asset.py --contract assets-src/game/p01/PeaShooter_Head.contract.json
python tools/check_game_asset.py --contract assets-src/game/p01/PeaShooter_frontleaf.contract.json
```

完成候选图后再检查实际像素；候选图必须位于 `assets-src`：

```powershell
python tools/check_game_asset.py `
  --contract assets-src/game/p01/PeaShooter_Head.contract.json `
  --candidate assets-src/game/p01/PeaShooter_Head.png

python tools/check_game_asset.py `
  --contract assets-src/game/p01/PeaShooter_frontleaf.contract.json `
  --candidate assets-src/game/p01/PeaShooter_frontleaf.png
```

契约只保证“确实是在原件上做了受控的局部改动”。镜框是否圆润、书本是否像被叶片托住、缩放后是否清楚，仍要通过静态预览与实机动画截图验收。

## P04 三档受伤契约

出恭墙继续使用 `Wallnut.reanim.compiled` 的原轨道。完整、轻伤、重伤分别由三张 100×100 主体图表达：

| 阶段 | 契约 | 原件可见像素 |
| --- | --- | ---: |
| 完整 | `assets-src/game/p04/Wallnut_body.contract.json` | 6766 |
| 轻伤 | `assets-src/game/p04/Wallnut_cracked1.contract.json` | 6650 |
| 重伤 | `assets-src/game/p04/Wallnut_cracked2.contract.json` | 6414 |

三份契约各自绑定原件哈希，不能把完整阶段误装到受伤槽位。首版要求逐像素保留每档 Alpha，从而继承原来的椭圆轮廓、缺口和裂损递进；眼睛、嘴和眨眼表演区也禁止改色。外壳必须出现足量灰褐墙面，并在左下位置保留一块缩小后仍可辨认的蓝色编号牌。

逐个检查三份基线契约：

```powershell
Get-ChildItem assets-src/game/p04/*.contract.json | ForEach-Object {
  python tools/check_game_asset.py --contract $_.FullName
}
```

绘制时应先完成无裂纹稿，再沿三张原图已有的缺口位置制作两档损伤。三档必须共享墙面纹理走向和编号牌位置，不能只做三张彼此无关的灰色贴图。

## 基线往返

先运行不写文件的底层往返检查：

```powershell
python tools/build_pak_overlay.py --roundtrip-check
```

再用机器可读的零替换清单做完整预演和输出：

```powershell
python tools/build_pak_overlay.py --check patches/manifests/v0.5-pak-roundtrip.json
python tools/build_pak_overlay.py --build patches/manifests/v0.5-pak-roundtrip.json
```

三种路径都得到与基线相同的哈希。`dist/v0.5/main-roundtrip.pak` 是本地验证产物，不进入 Git。

## 正式替换清单格式

第一张原尺寸贴图完成后，在新的清单里加入类似记录：

```json
{
  "pakPath": "reanim/PeaShooter_Head.png",
  "source": "assets-src/game/p01/PeaShooter_Head.png",
  "sha256": "替换件的 SHA-256",
  "originalSha256": "原 70×65 头部的 SHA-256",
  "preserveCanvas": true,
  "contract": "assets-src/game/p01/PeaShooter_Head.contract.json"
}
```

`pakPath` 使用 PAK 内的正斜杠路径。`preserveCanvas` 默认为 `true`；只有已经修改 reanim 锚点并有对应测试时，才允许显式关闭。

## 绿圈科豆如何进入这条链

1. 以[概念稿](../assets-src/concepts/p01-greencircle-pea-concept.png)确定眼镜、蓝书和蓝白书签的造型。
2. 单独制作 70×65 的带眼镜头部，不移动原眼睛、嘴和喷口锚点，并通过 P01 像素契约。
3. 书本已确认可以合入 67×40 前叶画布；先走同尺寸替换，只有实机遮挡失败时再改 reanim。
4. 为每个游戏部件记录原图哈希、新图哈希、尺寸和目标 PAK 路径。
5. 用新清单生成 `dist` PAK，再进行待机、眨眼、发射、选卡和图鉴实机检查。

公开发行时仍只提供原创素材、清单和应用工具，不提供这里生成的完整 PAK。
