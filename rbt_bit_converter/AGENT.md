# rbt_bit_converter Agent 准则

## 工具定位

- 本工具负责 `.rbt` 与 `.bit` 文件互转。
- GUI 通过主界面 `tools_registry.py` 加载为独立标签页，也保留 `rbt2bit.py` 和 `bit2rbt.py` 命令行入口。

## 结构约定

```text
rbt_bit_converter/
  AGENT.md
  __init__.py
  metadata.py
  widget.py
  rbt2bit.py
  bit2rbt.py
```

- `widget.py` 保存 PyQt5 界面、信号槽、后台线程和与 `ToolServices` 的交互。
- `metadata.py` 保存 `TOOL_ID` 和 `TOOL_NAME`，避免命令行入口导入 GUI 模块。
- `rbt2bit.py` 和 `bit2rbt.py` 保存转换逻辑，并提供 GUI 可复用的函数入口。
- `__init__.py` 暴露 `TOOL_ID`、`TOOL_NAME` 和 `create_widget()`。

## GUI 维护约定

- 界面风格应与主界面和其他 PyQt5 子工具保持一致：浅灰背景、白色输入/文本区域、蓝色主按钮、4px 圆角。
- 转换操作应放在后台线程执行，避免阻塞主界面。
- 支持多文件批量转换，GUI 中多个路径使用分号分隔显示。
- 日志应展示每个文件的输入、输出、成功或失败原因。

## 输出约定

- RBT 转 BIT 默认输出到输入文件同目录，文件名为 `<原文件名>.bit`。
- BIT 转 RBT 默认输出到输入文件同目录，文件名为 `<原文件名>.rbt`。
- GUI 中的 `提取码流编号` 复选框选中后，输出文件名为 `No<原文件名>.rbt`。
- 业务输出不得默认写入源码目录，除非用户选择的输入文件本身位于该目录。

## 验证建议

- 修改后至少运行：

```powershell
python -m py_compile rbt_bit_converter\rbt2bit.py rbt_bit_converter\bit2rbt.py rbt_bit_converter\metadata.py rbt_bit_converter\widget.py rbt_bit_converter\__init__.py
```

- 接入主界面后，确认 `RBT/BIT互转` 标签页可以加载。
