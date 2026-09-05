# R1 独立运行目录验收

日期：2026-09-05。实现与自动构建检查已通过；原版游戏的启动画面观察尚未完成。

## 自动检查

| 检查 | 结果 |
| --- | --- |
| 公开检查 | GBK 文案与同步检查通过，15 项合成数据测试通过 |
| 指定干净原件的完整检查 | 92 项测试通过；常量预演、PAK 往返、资源盘点和 16 份契约通过 |
| 原件识别 | 根目录 EXE 为 baseline，PAK 为 visuals；独立原件 EXE/PAK 均为 baseline |
| 完整目录装配 | visuals / constant-proof 均生成 96 个游戏文件及 runtime.json |
| 配套文件 | 90 个原件配套文件逐个校验，四个 properties 文件取自当前工程 |
| 输出完整性 | 两个运行目录的全部文件哈希通过校验 |
| 真实重复构建 | visuals 再次构建后，96 个游戏文件及 runtime.json 的字节和修改时间均不变 |
| 失败路径 | 原件被修改/缺失、未托管输出、不同构建覆盖、安装中断、损坏文件、越界路径和伪造 EXE 记录均有拒绝测试 |
| 原目录保持 | 根目录 EXE 与开发 PAK 保持构建前哈希 |
| GitHub Actions | [33946361436](https://github.com/wingtings/pvz-ustc-project/actions/runs/33946361436)：7d3984d 的 Windows/Ubuntu 两项任务及公开测试步骤均成功 |
| 无原件副本 | 仅复制源码、文案和清单，15 项公开测试及文案检查通过；另从 Git 暂存内容逐字节导出复测通过 |
| Web 沙盘复跑 | 固定引擎、隔离环境中 bot 返回 done；11 次决策通过，无控制台错误 |

## 两种组合

| 配置 | EXE SHA-256 | P01 / P04 |
| --- | --- | --- |
| visuals | `6F1729369AC9C5F859E8F3B55FE7D513FBC20B5C54127FD3A1C7E500237FDE6F` | 100 / 4000 |
| constant-proof | `CB0E0FFF4A530164582E3E0A86FA046A5217AC4293F961A75FB3097C853899B8` | 75 / 4200，临时验证值 |

两者 PAK 均为 `9DB70BB44031EF6B12ED92FF9F79BC9737B382D2F0D0383607DA1AAABAADB90B`。干净输入 PAK 为 `3B5291C6600076AAF1791AE1FB2DBF247290A23E903D1D376413DA17358E049D`。

输入使用本轮独立保存的干净基线，未把开发包当作原件，也没有修改前置哈希。生成目录位于被忽略的 `dist/runtime/`；构建输出与完整测试输出保存在被忽略的 `.work/r1-*.log`。

## 实机观察待补

首轮远端 [33946052556](https://github.com/wingtings/pvz-ustc-project/actions/runs/33946052556) 在两种系统上都被现有 CRLF 检查拦下：旧 Git blob 为 LF，本机自动换行转换掩盖了问题。保留 `-text` 规则并重新登记已有 GBK/CRLF 文案后，Git 中的字节与游戏工作文件一致，SHA-256 为 `967513723EA933BB5D4F98E16CDE40EC737C6E417DA25BA1E527417BCA2BA77F`；归一化换行后正文逐字节相同。未放宽检查，也未修改文字内容。

第二轮 [33946226467](https://github.com/wingtings/pvz-ustc-project/actions/runs/33946226467) 的 Ubuntu 检查通过，Windows 暴露了两个测试的路径表示假设：临时目录使用 `RUNNER~1` 短名，而工具正确返回解析后的长名。测试改为比较规范化后的路径，仍校验输入目录选择和输出目录不变。

Windows computer-use 的 JavaScript 环境初始化报告 `failed to write kernel assets: 系统找不到指定的路径。 (os error 3)`；重置环境再初始化仍报同一错误。因此本轮没有通过该工具启动或操作原版游戏，没有新增启动、选卡、关卡或存档观察证据。

待工具恢复后，分别使用[运行入口](../../docs/runtime-workspace.md)启动两个目录，观察主菜单、图鉴、选卡、实际数值与首批视觉，并确认实际进程使用正确工作目录。R2 的独立测试玩家、新存档通关和退出继续仍待执行，不能由 92 项自动测试替代。
