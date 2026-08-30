# 原创素材 PAK 开发构建

状态：可重复构建链已完成；尚无原尺寸角色替换件进入游戏。

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
  "preserveCanvas": true
}
```

`pakPath` 使用 PAK 内的正斜杠路径。`preserveCanvas` 默认为 `true`；只有已经修改 reanim 锚点并有对应测试时，才允许显式关闭。

## 绿圈科豆如何进入这条链

1. 以[概念稿](../assets-src/concepts/p01-greencircle-pea-concept.png)确定眼镜、蓝书和蓝白书签的造型。
2. 单独制作 70×65 的带眼镜头部，不移动原眼睛、嘴和喷口锚点。
3. 书本先作为独立透明工作件，确认能否合入前叶画布；放不下时再修改 reanim，而不是缩成看不清的一团。
4. 为每个游戏部件记录原图哈希、新图哈希、尺寸和目标 PAK 路径。
5. 用新清单生成 `dist` PAK，再进行待机、眨眼、发射、选卡和图鉴实机检查。

公开发行时仍只提供原创素材、清单和应用工具，不提供这里生成的完整 PAK。
