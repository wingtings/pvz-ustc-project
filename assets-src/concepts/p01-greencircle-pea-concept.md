# P01 绿圈科豆概念稿说明

状态：造型方向稿，不是游戏内可直接替换的贴图。

生成日期：2026-08-30

## 设计目标

在保留原版豌豆射手头部、喷口、茎叶、朝向和手绘质感的基础上，加入三个一眼可见的科大化识别点：小圆框眼镜、蓝色《电磁学千题解》和蓝白书签。概念稿不使用中国科大校徽，也不加入真人或校园建筑。

参考部件来自本地合法游戏副本，经 `tools/pak_assets.py` 选择性提取到 `.work/pak-reference`：

- `reanim/PeaShooter_Head.png`
- `reanim/PeaShooter_frontleaf.png`
- `reanim/PeaShooter_backleaf.png`
- `reanim/PeaShooter_stalk_top.png`
- `reanim/PeaShooter_stalk_bottom.png`

这些原版部件不提交到仓库。仓库中的 PNG 是据此生成的单张概念稿。

## 主生成提示

```text
Use case: stylized-concept
Asset type: 2D game character concept for a Plants vs. Zombies-style mod
Input images: Images 1-5 are reference parts from the original Peashooter character; preserve its recognizable head, snout, stem, leaf base, lime-green palette, dark hand-painted outlines, soft highlights, and playful proportions.
Primary request: create one full-body concept of the same plant reinterpreted as the USTC-themed character "绿圈科豆". Add small round black academic glasses fitted naturally over the existing eyes. Turn one existing leaf into a leaf-arm that supports an open compact blue textbook. The visible blue cover must read exactly "电磁学千题解" in clear Chinese, with no other cover text. Add only a subtle blue-and-white campus-style bookmark or lanyard as a secondary accent.
Style/medium: polished 2D hand-painted game sprite concept matching the supplied original raster parts, with clean transparent edges.
Composition/framing: single character, centered, complete silhouette visible, three-quarter side view facing right, neutral idle pose, generous transparent padding.
Constraints: genuinely transparent background; preserve the original plant anatomy and proportions; no human arms or hands; no official university seal; no extra characters; no scenery; no UI; no watermark.
Avoid: photorealism, anime rendering, 3D render, redesigning the snout, oversized accessories, illegible or invented text.
```

首轮结果把棋盘格画进了图像，因此又进行了一次只处理背景的编辑：

```text
Use case: background-extraction
Asset type: transparent 2D game character concept
Input images: Image 1 is the edit target.
Primary request: remove only the light gray and white checkerboard background and replace it with genuine transparent alpha.
Constraints: preserve the character pixel-for-pixel as closely as possible, including silhouette, colors, black glasses, blue book, tassel, highlights, and the exact Chinese cover text "电磁学千题解"; keep the same canvas and centered composition; clean antialiased transparent edges; no halo; no new shadows; no new objects; no watermark.
Avoid: drawing a checkerboard pattern, a white background, altering or re-rendering the character, changing the text.
```

两次处理均使用项目环境中的内置图像生成工具。首轮不透明草稿已移到被 Git 忽略的 `.work/imagegen-drafts`，不进入版本库。

## 输出检查

| 项目 | 结果 |
| --- | --- |
| 文件 | `p01-greencircle-pea-concept.png` |
| SHA-256 | `3A75B47CD7C248F7A33F975070F4744024FAFD1DB7D72F64D9B895046A17809E` |
| 画布 | 1254×1254 |
| 像素格式 | 32 位 ARGB |
| 四角 Alpha | `0, 0, 0, 0` |
| 画布边缘非透明像素 | 0 |
| 非透明包围盒 | `(71, 47)` 至 `(1191, 1227)` |
| 目视检查 | 眼镜、蓝书、蓝白书签和“电磁学千题解”均存在，朝向与原版豌豆射手一致 |

## 进入游戏前还要做什么

原版 `PeaShooter_Head.png` 只有 70×65，概念稿不能直接缩到这个尺寸。正式素材需要按原动画拆成至少“带眼镜的头”和“书本/托书叶片”两个透明部件，重新确定锚点与遮挡顺序。书名字样应在最终尺寸上手工排版，缩略状态只保证蓝书的视觉识别，不强求逐字阅读。
