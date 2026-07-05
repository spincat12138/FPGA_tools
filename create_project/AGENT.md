# Create_Project 子工具 Agent 准则

## 工具定位

- 本工具用于创建 Vivado 工程目录结构，或基于目录下已有源码生成 TCL 并调用 Vivado 构建工程。
- GUI 使用 `PyQt5`，通过主界面 `tools_registry.py` 加载为独立标签页。

## 文件职责

- `create_project.py` 保存可复用核心逻辑和命令行入口。
- `widget.py` 保存 PyQt 界面、信号槽、后台线程和 `ToolServices` 交互。
- `__init__.py` 暴露主界面稳定入口：`TOOL_ID`、`TOOL_NAME`、`create_widget()`。

## 路径与模式

- `mkdir` 模式在 `<root_dir>/<project_name>/source/` 下创建 `hdl`、`sim`、`xdc` 目录。
- `project` 模式要求 `<root_dir>/<project_name>` 已存在，在该目录下生成 `<project_name>_create_project.tcl`，再通过 GUI 或命令行提供的 Vivado 路径调用 batch 模式执行该脚本。
- `project_name` 只允许作为单级目录名使用，不能包含路径分隔符。

## 验证建议

- 修改核心逻辑后，至少运行 `python -m py_compile Create_Project/create_project.py Create_Project/widget.py Create_Project/__init__.py`。
- 目录创建可用临时目录冒烟验证。
- 构建工程会调用本机 Vivado，缺少 Vivado 或 FPGA 源文件时不应作为 GUI 加载失败处理。
