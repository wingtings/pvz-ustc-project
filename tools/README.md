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

验证 PAK 在没有替换件时能逐字节往返：

```powershell
python tools/build_pak_overlay.py --roundtrip-check
python tools/build_pak_overlay.py --check patches/manifests/v0.5-pak-roundtrip.json
```

生成被 Git 忽略的本地验证包：

```powershell
python tools/build_pak_overlay.py --build patches/manifests/v0.5-pak-roundtrip.json
```

正式素材清单只允许引用 `assets-src` 下的原创替换件。格式与尺寸门禁见 [原创素材 PAK 构建](../docs/asset-build-pipeline.md)。
