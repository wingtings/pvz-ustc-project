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
