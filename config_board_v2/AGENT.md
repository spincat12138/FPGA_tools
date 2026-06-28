# config_board_v2 子工具 Agent 准则

本文件维护 `config_board_v2` 子工具自己的业务规则、内部结构和验证要求。主界面只通过根目录 `AGENT.md` 中定义的注册入口加载本工具。

## 工具定位

- 工具名称：配置板烧写程序-V2。
- 工具用途：通过 FTDI USB 设备执行配置板握手、擦除、码流配置、ReadBack、回读验证和 rbt/txt 码流转换。
- 运行环境：遵循项目根文档，默认使用项目内虚拟环境 `py38`。
- GUI 技术栈：遵循项目根文档，界面开发使用 `PyQt5`。
- 独立运行入口：`config_board_v2/usbtest_gui.py`。
- 主界面接入入口：`config_board_v2/__init__.py` 暴露的 `create_widget(parent=None, services=None)`。

## 内部结构

```text
config_board_v2/
  AGENT.md
  __init__.py
  usbtest_py.py
  usbtest_gui.py
  widget.py
  FTD2XX_NET.dll
  FTD2XX_NET.xml
```

- `usbtest_py.py` 保存 FTDI 通信、设备握手、擦除、写入、回读、验证和码流转换核心逻辑。
- `widget.py` 保存 PyQt5 界面、信号槽、后台线程和 `ToolServices` 交互。
- `usbtest_gui.py` 保留独立运行入口，并复用 `widget.py` 中的同一套 PyQt5 界面。

## 业务规则

- 设备型号来自 `usbtest_py.DEVICE_BY_NAME`，打开设备后以握手结果更新当前型号。
- 擦除、配置、ReadBack 和回读验证都要求 USB 设备已打开。
- 配置文件支持 `.bit`、`.rbt`、`.b`；`.rbt` 会在核心逻辑中按原规则转换后写入。
- GUI 的 ReadBack 输出文件保持为本工具应用数据目录下的 `<回读地址>_readback.bit`，例如地址 `121` 输出 `121_readback.bit`。
- GUI 的回读验证输出文件保持为本工具应用数据目录下的 `compare.txt`，报告按核心脚本的追加写入格式生成。
- 回读验证支持 `.bit`、`.b`、`.rbt`、`.txt`，其中 `.rbt` 和 `.txt` 会先按核心脚本规则转换后比较。
- GUI 的码流转换支持 `.rbt` 和 `.txt`，生成的 `.txt`、`.b`、`header.txt`、`tailer.txt` 保持在本工具应用数据目录下，转换规则由 `usbtest_py.py` 维护。
- 命令行直接调用 `usbtest_py.py` 时，默认输出路径保持脚本自身默认行为；GUI 会显式传入本工具应用数据目录作为输出目录。

## GUI 维护约定

- 界面风格应与主界面和其他 PyQt5 子工具保持一致：浅灰背景、白色输入/文本区域、蓝色主按钮、4px 圆角。
- 不再引入或维护 Tkinter 界面；独立运行也必须使用 `PyQt5`。
- 耗时 USB 和文件操作必须放到后台线程，避免阻塞主界面。
- 需要日志、弹窗和忙碌状态时优先使用主界面传入的 `ToolServices`。
- USB 协议、码流转换和文件格式规则只在 `usbtest_py.py` 中维护，界面不复制核心逻辑。

## 验证要求

- 修改核心 USB 或码流规则后，至少运行相关命令行路径或用硬件做一次对应操作验证。
- 修改 GUI 时，至少运行 `python -m py_compile config_board_v2/usbtest_py.py config_board_v2/widget.py config_board_v2/usbtest_gui.py config_board_v2/__init__.py`。
- 在无 FTDI 环境中，GUI 加载不应崩溃，应显示 `FTDI环境异常` 或 USB 未插入状态。
- 接入主界面后，确认主 GUI 中的 `配置板烧写程序-V2` 标签页可以加载。

## 完成标准

- 本工具可通过主界面标签页加载。
- 独立运行入口使用 PyQt5，且功能与旧 Tk 界面一致。
- 输入校验、状态提示、失败弹窗和后台执行路径清晰。
