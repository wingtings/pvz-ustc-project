# 独立开发运行目录

R1 已提供原件选择、完整目录装配、文件校验与启动入口。构建使用当前仓库的制作脚本与文案，原件来自明确指定的干净目录；已有的开发 PAK 留在原处。

## 两种运行配置

| 配置 | P01 费用 | P04 耐久 | 美术 |
| --- | ---: | ---: | --- |
| `visuals` | 100 | 4000 | 首批五槽位、16 项累计替换 |
| `constant-proof` | 75 | 4200 | 同一份 16 项资源包；数值仅用于补丁验证 |

每个目录包含 96 个游戏文件，以及一份 `runtime.json`。记录包含配置、数值说明、EXE/PAK 哈希和全部文件的哈希。不会把原版文件打成可公开下载的游戏包。

## 使用

在仓库根目录执行，示例中的 `C:\Games\PvZ-clean` 替换为匹配项目基线的本地合法原件目录。该目录需包含 EXE、PAK、两份 DLL 以及 `data/images/particles/reanim`；具体 90 个配套文件由[原件清单](../patches/manifests/runtime-baseline.json)校验。文案等四个 `properties` 文件从当前工程读取。

```powershell
python tools/runtime_workspace.py --inspect --baseline-dir C:\Games\PvZ-clean
python tools/check_project.py --baseline-dir C:\Games\PvZ-clean
python tools/runtime_workspace.py --build --baseline-dir C:\Games\PvZ-clean --profile visuals
python tools/runtime_workspace.py --verify --profile visuals
python tools/runtime_workspace.py --launch --profile visuals
```

临时数值测试版：

```powershell
python tools/runtime_workspace.py --build --baseline-dir C:\Games\PvZ-clean --profile constant-proof
python tools/runtime_workspace.py --verify --profile constant-proof
python tools/runtime_workspace.py --launch --profile constant-proof
```

默认输出分别是 `dist/runtime/visuals` 和 `dist/runtime/constant-proof`。启动前校验文件，随后以该目录为工作目录启动 EXE。**运行目录隔离不等于存档隔离**：游戏仍使用原有用户数据位置，实机验收应先备份存档并使用独立测试玩家。

内容完全相同的重复构建只验证已有目录，不改写文件或运行日志。已有目录与新构建不同时工具会停止；使用新目录保留旧版：

```powershell
python tools/runtime_workspace.py --build --baseline-dir C:\Games\PvZ-clean --profile visuals --output dist/runtime/visuals-next
python tools/runtime_workspace.py --launch --output dist/runtime/visuals-next
```

`--output` 只接受 `dist/runtime` 下的子目录。装配中断时清理临时目录，不留下看似完整的成品。未知或缺失输入停止处理；不自动恢复、替换或删除用户的原件。

## 单独使用已有工具

需要手动运行素材工具时，可显式选择同一原件目录：

```powershell
$env:PVZ_USTC_BASELINE_DIR = 'C:\Games\PvZ-clean'
python tools/build_p01_sprites.py --check
python tools/build_pak_overlay.py --roundtrip-check
python tools/apply_binary_patches.py --check
python -m unittest discover -s tests -p "test_*.py"
Remove-Item Env:PVZ_USTC_BASELINE_DIR
```

该变量只改变干净 EXE/PAK 的默认读取位置，不改变清单哈希、制作配方、输出目录或游戏文案来源。没有变量时保留旧工具的仓库根目录默认行为；如果根目录已经是开发 PAK，校验仍会正确拒绝。

## 公开 CI 与本地完整检查

```powershell
python tools/check_project.py --public
python tools/check_project.py --baseline-dir C:\Games\PvZ-clean
```

公开检查覆盖 GBK 文案、同步幂等性和合成数据的运行目录测试，不需要原版 EXE、PAK 或图像。完整检查另执行原件相关测试、补丁预演、PAK 往返、资源盘点和契约检查。

[GitHub Actions](https://github.com/wingtings/pvz-ustc-project/actions/workflows/checks.yml) 在 Windows 与 Ubuntu 上执行公开检查。工作流稀疏检出所需源码和文案；不生成或上传原版游戏产物。所用操作固定到核对过的提交，参照 [checkout](https://github.com/actions/checkout) 和 [setup-python](https://github.com/actions/setup-python) 官方说明。

当前构建与实机验证状态见 [R1 验收记录](../tests/checklists/r1-runtime-workspace.md)。
