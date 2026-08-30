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

## Z03 三档书套契约

`Zombie_cone1.png`、`Zombie_cone2.png`、`Zombie_cone3.png` 都是 59×57，并由共享的 `anim_cone` 轨道以相同锚点绘制。原路障是三角形，厚书套需要更接近倾斜矩形；如果像 P04 一样锁死整张 Alpha，成品只会像蓝色路障。因此 Z03 使用“受控轮廓重构”模式：

- 画布和 PAK 路径不变，不修改 `Zombie.reanim.compiled`。
- `y=43..56` 的头部接触带逐像素保留 Alpha，书套不会在动画中跳位。
- 上半部允许有限新增与删除，候选总体积、与原件重叠量、增量和删减量都有上下限。
- 完整、轻伤、重伤必须保留深蓝封面；白色页块最低像素依次为 100、180、260，损伤越重，露页越多。
- 只把原路障整体涂蓝、完全不改变轮廓会因新增和删除像素不足而被拒绝。

| 阶段 | 契约 | 原件可见像素 | 校准测试件新增/删除 |
| --- | --- | ---: | ---: |
| 完整 | `assets-src/game/z03/Zombie_cone1.contract.json` | 1582 | 509 / 125 |
| 轻伤 | `assets-src/game/z03/Zombie_cone2.contract.json` | 1642 | 375 / 253 |
| 重伤 | `assets-src/game/z03/Zombie_cone3.contract.json` | 1624 | 287 / 345 |

原路障三档的可见像素数并非单调递减，因为破损碎片会横向展开；这里用露出白页的递增量表达损伤，而不是错误地要求整张 PNG 像素越来越少。

目前契约使用的 Alpha 模式覆盖三类修改：

| 模式 | 用途 | 当前对象 |
| --- | --- | --- |
| `preserve` | 整张 Alpha 完全不变 | P01 眼镜头、P04 三档墙体 |
| `add-only` | 可增加部件，不得削掉原件 | P01 前叶蓝书 |
| `bounded` | 可受限增删，同时保护指定锚点带 | Z03 三档书套 |

## P02 首轮三部件契约

当前 `SunFlower.reanim.compiled` 的战斗动画引用基础头部、两张眨眼覆盖层和分散花瓣轨道。PAK 中另外存在五张 `head_sing` 与一张 `head_wink`，但它们不在这份战斗 reanim 的图像引用中；首轮不为未引用资源制作重复稿。

P02 的最小可辨切片是三张：

| 部件 | 契约 | 作用 |
| --- | --- | --- |
| `SunFlower_head.png`，57×43 | `assets-src/game/p02/SunFlower_head.contract.json` | 保留眼睛核心和暖色脸，加入专注眉形及小块科大蓝学习标记 |
| `SunFlower_toppetals.png`，16×10 | `assets-src/game/p02/SunFlower_toppetals.contract.json` | 把顶部成组花瓣改成蓝白便签 |
| `SunFlower_bottompetals.png`，19×15 | `assets-src/game/p02/SunFlower_bottompetals.contract.json` | 把底部成组花瓣改成蓝白便签 |

其余 17 张独立小花瓣暂时保留暖黄，让玩家仍能一眼识别生产单位。首轮实机确认蓝白点缀在战场缩放下可见后，再决定是否扩到更多花瓣，而不是一次修改全部 29 张资源。

上下花瓣原件是 8 位索引色 PNG，头部是 RGBA PNG。像素检查器会读取原调色板与 `tRNS` 透明表，统一解码为 RGBA 进行比较；候选可以保存为 RGBA，不需要为了匹配容器格式重新量化成索引色。测试已经覆盖“索引色原件→RGBA 候选”且保持画布与 Alpha 不变的路径。

## Z01 共享躯干契约

普通微积分与 B 系列淑芬等装备型基础敌人共用 `Zombie.reanim.compiled`。首轮只替换 53×63 的 `Zombie_body.png`：把破西装改成写有演算和批改痕迹的旧卷面。`Zombie_head.png`、`Zombie_jaw.png` 与红领带暂时复用原版；领带本身已经提供稳定的批改红点缀，头和下颌则作为跨槽位回归对照。

`assets-src/game/z01/Zombie_body.contract.json` 要求：

- 画布与整张 Alpha 不变。
- 原件中满足深色墨线阈值的轮廓、衣物破口和阴影逐像素不变。
- 候选必须同时包含足量旧纸米白、铅笔灰和批改红。
- 改动量须在 1000–1700 个可见像素；测试件实际改动 1415 个。

“按原色保护”与矩形保护区不同：它会在整张图片中找出原始深色笔触，无论这些像素位于边缘还是内部破口都不能覆盖。这使新卷面继续沿用原版手绘线条，而不是只保留外框后把内部涂成一块平面。

这张躯干会同时出现在 Z01、Z03、Z05 以及其他调用基础僵尸骨架的槽位中。共享是有意的：书套或铁皮封面脱落后应回到同一张“普通微积分”本体；但实际候选进入 PAK 后必须跨装备槽位检查，不能只截 Z01 一张图就宣称通过。

## 首批契约注册表

`patches/manifests/v0.5-first-slice-contracts.json` 是 P01、P02、P04、Z01、Z03 的完整注册表，当前包含 12 份契约和 12 个唯一 PAK 目标。它不是候选贴图清单，不会生成带替换资源的 PAK；作用是证明首批门禁本身没有漏项。

一条命令同时检查：

```powershell
python tools/check_game_asset.py `
  --registry patches/manifests/v0.5-first-slice-contracts.json
```

注册表校验会比较磁盘实际发现的 `assets-src/game/**/*.contract.json`：

- 新增契约但忘记登记时失败。
- 登记不存在的文件时失败。
- 槽位/角色、契约路径或 PAK 目标重复时失败。
- 预期五槽位集合不一致时失败。
- 任一原件哈希、尺寸、格式或像素规则不匹配时失败。

候选图完成后仍需单独建立 PAK 替换清单，记录候选 SHA-256，并让每个 replacement 引用这里登记的契约。注册表通过不等于已有美术成品。

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
