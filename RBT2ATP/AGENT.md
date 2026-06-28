# RBT2ATP 子工具 Agent 准则

本文件维护 `RBT2ATP` 子工具自己的业务规则、内部结构和验证要求。主界面只通过根目录 `AGENT.md` 中定义的注册入口加载本工具。

## 工具定位

- 工具名称：RBT 转 ATP。
- 工具用途：将 `.rbt` 配置数据转换为 `.atp` 向量文件，支持单文件和批量目录转换。
- 运行环境：遵循项目根文档，默认使用项目内虚拟环境 `py38`。
- GUI 技术栈：遵循项目根文档，界面开发使用 `PyQt5`。
- 独立运行入口：`RBT2ATP软件.py`。
- 主界面接入入口：`RBT2ATP/__init__.py` 暴露的 `create_widget(parent=None, services=None)`。

## 推荐内部结构

```text
RBT2ATP/
  AGENT.md
  __init__.py
  widget.py
  core.py
  RBT2ATPgui.ui
  resources/
    logo.ico
  tests/
```

- `widget.py` 放 PyQt 界面逻辑、信号槽绑定和与 `ToolServices` 的交互。
- `core.py` 放 RBT 解析、ATP 内容生成、repeat 压缩和输出路径计算等纯业务逻辑。
- `RBT2ATPgui.ui` 是 Qt Designer 源文件，运行时由 `uic.loadUi()` 直接加载。
- 不再维护 `RBT2ATPgui.py` 这类中间生成文件，避免界面定义出现两个事实来源。
- `resources/` 放图标和小型静态资源。
- `tests/` 放最小 `.rbt` 样例、期望 `.atp` 片段和核心逻辑测试。

## 接入主界面约定

本工具接入主界面时，应提供：

```python
TOOL_ID = "rbt2atp"
TOOL_NAME = "RBT 转 ATP"

def create_widget(parent=None, services=None):
    ...
```

- 返回对象必须是 `QWidget` 或其子类，不再作为独立 `QMainWindow` 嵌入主界面。
- 不直接 import 主窗口；需要日志、弹窗、路径、进度时使用 `services`。
- 保持独立运行能力可以作为开发便利，但主界面集成路径以 `create_widget()` 为准。
- 主界面标签页文字由根目录 `tools_registry.py` 中的 `name` 控制；本工具的 `TOOL_NAME` 应与之保持一致。

## GUI 维护约定

- `RBT2ATPgui.ui` 是界面布局源文件，运行时在 `RBT2ATP软件.py` 中通过 `uic.loadUi()` 直接加载。
- 不维护 `RBT2ATPgui.py` 这类由 `pyuic` 生成的中间文件，避免 `.ui` 和 `.py` 成为两个界面事实来源。
- 当前运行时样式集中在 `RBT2ATP软件.py` 的 `apply_visual_style()`；调整视觉风格时优先修改这里的 QSS，不把样式分散到多个槽函数中。
- 表格单元格编辑器由 `CompactTableEditDelegate` 控制，用于避免默认 `QLineEdit` 编辑框过粗、遮挡文字或透出底层旧内容。
- 表格内联编辑器应保持白色实底、无外框、零 padding；不要改回透明背景，否则编辑时原单元格文字会和新输入内容叠在一起。
- 修改表格行高、字体、`QTableWidget::item` padding 或编辑器 delegate 后，必须检查 `REPEAT`、`INIT`、`DONE`、`MODE` 等可编辑单元格的编辑态显示。
- 下拉框样式由 QSS 中的 `QComboBox` 规则控制；右侧下拉区域会占用文本空间，新增更长选项时同步调整 `_set_combo_width()` 中的固定宽度和父布局宽度。
- 当前 `comboBox_vector` 和 `comboBox_mod_choose` 在运行时设置固定宽度，避免 `vm_vector`、`normal`、`extend` 等文本在主界面中显示不全。
- `comboBox_vector_2` 是预设选择框，启动时从子工具目录下的 `presets.json` 读取预设名称并填充；切换预设会应用配置模式、Vector Mode、Timing Mode、信号勾选状态和表格值。
- `presets.json` 使用 UTF-8 编码，顶层为 `{ "presets": [...] }`；每个预设至少包含唯一 `name`，其他字段可包含 `configuration_mode`、`vector_mode`、`timing_mode`、`signals` 和 `table`。
- Nuitka onefile 打包必须把 `RBT2ATP/presets.json` 作为 data file 一起包含；运行时优先读取 `FPGA_TOOLS_HOME`、Nuitka 原始启动路径或 `sys.argv[0]` 推导出的 exe 同目录下的 `RBT2ATP/presets.json` / `presets.json` 作为外置覆盖配置，再读取内置资源。不要只依赖 `sys.executable`，它在 onefile 下可能指向临时解包目录。
- 如果所有 `presets.json` 候选路径都不可用，程序会使用 `RBT2ATP软件.py` 中的内置默认预设作为兜底，避免打包资源缺失时下拉框只剩“界面默认”；修改默认预设内容时，应优先修改 `presets.json`，并同步检查内置兜底值是否仍一致。

## RBT 输入假设

- 输入文件扩展名为 `.rbt`。
- 当前实现跳过前 7 行头部数据后处理配置位流。
- 配置数据按 32 位行处理；不足 4 行倍数时使用 `00100000000000000000000000000000` 补齐。
- 支持配置位宽模式：`x32`、`x16`、`x8`、`x1`。
- GUI 表格中的 `REPEAT` 必须是数字，并受最大 repeat 计数限制。

这些格式假设属于本工具内部规则；如果硬件平台或 ATP 语法变化，应优先在本文件和 `core.py` 中同步更新。

## ATP 输出约定

- 输出目录默认位于输入文件或输入目录旁的 `生成atp文件` 目录。
- 输出文件名沿用输入 `.rbt` 主文件名，扩展名改为 `.atp`。
- 输出内容包含 opcode mode、vector 名、start label、初始化/复位/等待/配置/结束段。
- 配置段根据 timing mode 做 repeat 压缩：
  - `quad` 对应 4。
  - `normal` 对应 2。
  - `extend` 对应 1。

## 代码质量要求

- 新增或修改转换规则时，优先把逻辑放进 `core.py`，让 GUI 只负责收集输入和展示状态。
- 避免裸 `except:`；捕获具体异常，并把失败文件、失败阶段和原因传给界面。
- 文件路径使用 `pathlib.Path`，不要用字符串拼接路径。
- 文件读写显式指定编码；如果后续支持二进制输入，使用二进制模式并单独校验。
- 不在本工具中硬编码主界面路径、用户机器路径或外部 FPGA 工具路径。

## 验证要求

- 修改 RBT 解析或 ATP 生成时，添加或更新核心逻辑测试。
- 至少保留一个小型 `.rbt` 输入样例和对应 `.atp` 关键片段断言。
- 修改 GUI 时，确认单文件转换、批量目录转换、错误输入提示和进度显示可用。
- 接入主界面后，确认主 GUI 中的 `RBT 转 ATP` 标签页可以加载并执行基本工作流。

## 完成标准

- 本工具可通过主界面标签页加载。
- 单文件和批量转换的输入校验、输出路径、状态提示清晰。
- 核心转换逻辑能脱离 GUI 测试。
- 文档记录的输入假设、输出规则和代码行为一致。
