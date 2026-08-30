# 文案工具

`LawnStrings.txt` 继续使用游戏需要的 CP936/GBK，设计文档则保持 UTF-8。不要用普通编辑器直接转换游戏文件编码。

从植物与敌人原型文档生成游戏文案：

```powershell
python tools/sync_lawnstrings.py --apply
```

检查编码、换行、869 个键名、控制标记和旧世界观残留词：

```powershell
python tools/check_lawnstrings.py
python tools/sync_lawnstrings.py --check
```

第二条命令还会验证同步是幂等的。只要设计文档和游戏文件一致，重复执行不会产生新改动。

同步工具认得当前仓库最初的文案哈希 `B974C89344A19F5A056133E1F776598693CFCD0E2C8A82E1C9535CD5CCFB131B`，但不会要求工作文件永远保持这个哈希。这样可以在后续版本继续追加文本，同时保留基线记录。

查看 PAK 内与某个单位有关的资源：

```powershell
python tools/pak_assets.py --list "*peashooter*" "*sunflower*"
```

选择性提取时，工具只允许写到被 Git 忽略的 `.work` 目录，并先校验 `main.pak` 哈希：

```powershell
python tools/pak_assets.py --extract "*peashooter*" --out .work/pak-reference
```

这些文件只用于识别原动画部件和制作本地差分，不应作为整套原版素材提交或发布。

检查首批资源数量和 P01 概念稿的 RGBA 透明边界：

```powershell
python tools/check_art_assets.py
```

## 常量补丁工具

v0.3 只在 `dist` 生成开发副本，绝不覆盖仓库中的基线 EXE：

```powershell
python tools/apply_binary_patches.py --check
python tools/apply_binary_patches.py --apply
python tools/apply_binary_patches.py --reverse
```

补丁位置、旧字节、新字节和回滚字节都在机器可读的 `patches/manifests/v0.3-constant-proof.json`。详细安全边界与哈希见 [v0.3 常量补丁文档](../docs/v0.3-patching.md)。

## PAK 增量构建

从经过验证的本地原件生成 P01 圆框眼镜和蓝色《电磁学千题解》候选，并输出十倍静态预览：

```powershell
python tools/build_p01_sprites.py --build --preview --check
```

两张候选 PNG 和预览都被 Git 忽略。仓库只保存局部像素配方、输出哈希和契约；不要手工把生成 PNG 强制加入版本控制。

验证 PAK 在没有替换件时能逐字节往返：

```powershell
python tools/build_pak_overlay.py --roundtrip-check
python tools/build_pak_overlay.py --check patches/manifests/v0.5-pak-roundtrip.json
```

生成被 Git 忽略的本地验证包：

```powershell
python tools/build_pak_overlay.py --build patches/manifests/v0.5-pak-roundtrip.json
```

生成 P01 双替换开发包：

```powershell
python tools/build_pak_overlay.py --check patches/manifests/v0.5-p01-first-ingame.json
python tools/build_pak_overlay.py --build patches/manifests/v0.5-p01-first-ingame.json
```

正式素材清单只允许引用 `assets-src` 下的原创替换件。格式与尺寸门禁见 [原创素材 PAK 构建](../docs/asset-build-pipeline.md)。

检查 P01 眼镜头部的原件契约；加入 `--candidate` 后还会逐像素检查候选图：

```powershell
python tools/check_game_asset.py --contract assets-src/game/p01/PeaShooter_Head.contract.json
python tools/check_game_asset.py --contract assets-src/game/p01/PeaShooter_frontleaf.contract.json
python tools/check_game_asset.py `
  --contract assets-src/game/p01/PeaShooter_Head.contract.json `
  --candidate assets-src/game/p01/PeaShooter_Head.png
python tools/check_game_asset.py `
  --contract assets-src/game/p01/PeaShooter_frontleaf.contract.json `
  --candidate assets-src/game/p01/PeaShooter_frontleaf.png
```

PAK 替换记录可用 `contract` 字段引用同一份契约，构建时会再次执行相同门禁。

批量检查 P04 出恭墙的完整、轻伤和重伤原件契约：

```powershell
Get-ChildItem assets-src/game/p04/*.contract.json | ForEach-Object {
  python tools/check_game_asset.py --contract $_.FullName
}
```

Z03 三档书套使用相同的批量检查方式：

```powershell
Get-ChildItem assets-src/game/z03/*.contract.json | ForEach-Object {
  python tools/check_game_asset.py --contract $_.FullName
}
```

P02 首轮三部件也可批量检查。工具能读取原版索引色花瓣 PNG，并与 RGBA 候选逐像素比较：

```powershell
Get-ChildItem assets-src/game/p02/*.contract.json | ForEach-Object {
  python tools/check_game_asset.py --contract $_.FullName
}
```

检查 Z01 共享躯干的旧卷面契约：

```powershell
python tools/check_game_asset.py --contract assets-src/game/z01/Zombie_body.contract.json
```

该契约还会保护原图中所有深色外轮廓与破损线条；这类保护由 `protectedOriginalColors` 描述，不依赖固定矩形位置。

一次检查首批五槽位全部 12 份契约，并确认没有未登记文件或重复 PAK 目标：

```powershell
python tools/check_game_asset.py `
  --registry patches/manifests/v0.5-first-slice-contracts.json
```
