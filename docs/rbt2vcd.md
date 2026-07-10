# RBT2VCD 子工具文档

## 工具定位

- 本工具用于把 Xilinx ASCII `.rbt` 文件转换为 SelectMAP 风格 `.vcd` 文件。
- 命令行核心逻辑保留在 `rbt2vcd.py`；GUI 只负责文件选择、批量调度、日志和错误展示。
- 默认输出为输入文件同目录下的同名 `.vcd`；用户选择输出目录时，所有结果写入该目录。

## 入口与结构

- `__init__.py` 暴露 `TOOL_ID`、`TOOL_NAME` 和 `create_widget(parent=None, services=None)`。
- `widget.py` 实现 PyQt5 GUI，并直接调用 `rbt2vcd.py` 中的转换函数。
- `metadata.py` 维护主界面和日志使用的稳定工具标识。
- `profile.example.json` 是可编辑的外部配置示例，默认规则仍由 `rbt2vcd.py` 中的 `DEFAULT_PROFILE` 维护。

## 业务约束

- 输入必须是存在的 `.rbt` 文件，批量转换前统一校验。
- 指定统一输出目录时，如果多个输入文件会生成同名 `.vcd`，应在转换前报错，避免静默覆盖。
- 转换失败必须保留原始异常详情，并在日志和错误详情中展示。
- 自定义 profile 只通过 `rbt2vcd.py` 的 `load_rbt2vcd_profile()` 解析和校验，GUI 不重复实现配置格式规则。
- profile 只允许自定义 `SIGNALS`、四个 `CTRL_*` 控制值和 `WORD_SIZE`；header/tail 中的数据位由核心逻辑自动补 0。
- 四个 `CTRL_*` 的位宽必须等于信号数量减去 `WORD_SIZE`，header/tail 的重复次数保持核心脚本中的固定 SelectMAP 时序。

## 验证方式

- 修改后至少运行 Python 语法编译检查：

```powershell
python -m compileall RBT2VCD tools_registry.py main.py
```

- GUI 相关修改应至少做一次 widget 实例化或主界面启动冒烟验证。
