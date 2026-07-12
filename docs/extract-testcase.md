# Extract_Testcase 子工具文档

## 工具定位

- 本工具用于从 FPGA 相关文本日志中提取测试项名字，并输出 Excel 汇总。
- 当前支持 `ultra`、`93k`、`j750` 三种平台格式，平台必须由用户在 GUI 或命令行中显式选择。
- `extract_test_items.py` 保留命令行和核心解析逻辑；GUI 只负责路径选择、批量调度、日志和错误展示。

## 入口与结构

- `__init__.py` 暴露 `TOOL_ID`、`TOOL_NAME` 和 `create_widget(parent=None, services=None)`。
- `widget.py` 实现 PyQt5 GUI，并直接调用 `extract_test_items.py` 中的核心函数。
- `metadata.py` 维护主界面和日志使用的稳定工具标识。

## 业务约束

- 输入可以是 `.txt` 文件或目录；目录输入只扫描该目录下的 `.txt` 文件。
- 输出路径可选；留空时输出到输入文件所在目录。单文件输入时可指定具体 `.xlsx` 文件，多文件输入时输出到指定目录或指定文件的父目录。
- Excel 输出依赖 `openpyxl`，缺失时应直接报错并展示安装提示。
- 转换失败必须保留原始异常详情，并在日志和错误详情中展示。
- 核心脚本需要兼容 Python 3.8.10，避免使用 3.9+ 内置泛型和 3.10+ 联合类型语法。

## 验证方式

- 修改后至少运行 Python 语法编译检查：

```powershell
python -m compileall Extract_Testcase tools_registry.py main.py
```

- GUI 相关修改应至少做一次 widget 实例化或主界面启动冒烟验证。
