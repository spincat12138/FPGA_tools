# FPGA-tools 代码代理规则

## 项目概况

- 这是一个 Windows 优先的 PyQt5 桌面 FPGA 工具集合。
- 统一入口是 `main.py`，子工具通过 `tools_registry.py` 注册并显示在主界面右侧页面。
- 主界面只负责应用壳、工具发现、公共服务和错误展示；具体 FPGA 文件解析、转换、硬件流程放在各子工具内部。

## 常用命令

- 创建环境：`python -m venv py38`
- 激活环境：`.\py38\Scripts\Activate.ps1`
- 安装基础依赖：`python -m pip install PyQt5`
- 启动主界面：`python main.py`
- 语法检查：`python -m compileall main.py tools_registry.py common RBT2ATP RBT_Organization RBT_BIT_Converter RBT2VCD Create_Project Config_Board_V2 GenerateUcf Extract_Testcase`
- 打包依赖：`python -m pip install -r requirements-build.txt`

## 主要目录

- `common/`：主界面提供给子工具的公共服务。
- `RBT2ATP/`、`RBT_Organization/`、`RBT_BIT_Converter/`、`RBT2VCD/`、`Create_Project/`、`Config_Board_V2/`、`GenerateUcf/`、`Extract_Testcase/`：各子工具代码。
- `docs/`：子工具业务规则、入口、资源、验证方式等详细文档。
- `.github/workflows/`：Windows exe 打包流程。

## 修改规则

- 优先小范围修改，遵循现有 PyQt5、目录和命名方式，不做无关重构。
- 新增子工具时，在独立目录的 `__init__.py` 暴露 `TOOL_ID`、`TOOL_NAME`、`create_widget(parent=None, services=None)`，并在 `tools_registry.py` 登记。
- 新增、重命名或删除 `tools_registry.py` 中动态注册的子工具时，同步更新 `.github/workflows/build-windows-exe.yml` 的 Nuitka `--include-package` 参数和语法检查清单；源码环境可导入不代表 onefile 构建会自动包含该模块。
- `TOOL_ID` 使用小写英文、数字和下划线；`create_widget()` 返回 `QWidget` 或子类，不反向 import 主窗口。
- 子工具需要日志、弹窗、目录选择、配置目录、进度或忙碌状态时，优先使用 `common/services.py` 的 `ToolServices`。
- 业务输出写到用户选择的位置、输入文件旁或文档明确约定的位置；不要默认写入源码目录、临时解包目录或当前工作目录。
- 路径使用 `pathlib.Path`；外部输入在边界处校验，失败时保留清晰错误原因。
- 不要修改 `__pycache__`、构建产物、打包输出和覆盖率目录。
- 修改 `.ui`、图标、JSON/XML 等运行时资源后，同步检查 Nuitka workflow 的 data file 清单。
- 涉及 Vivado、FTDI 或硬件协议的改动，需要在文档中说明验证边界；无硬件时至少保证 GUI 可加载并清晰展示环境异常。

## 验证要求

- 文档或注册表改动后，至少检查 `tools_registry.py` 中的 `doc` 路径存在。
- Python 代码改动后，优先运行相关目录的 `py_compile` 或 `compileall`。
- GUI 相关改动后，尽量做一次 `python main.py` 启动冒烟验证。
- 涉及转换规则时，用小样例核对关键输出；不要用静默 fallback 掩盖解析或校验失败。

## 参考文档

- 项目介绍、安装和独立工具入口见 `README.md`。
- RBT 转 ATP：`docs/rbt2atp.md`
- RBT 文件整理：`docs/rbt-organization.md`
- RBT/BIT 互转：`docs/rbt-bit-converter.md`
- RBT 转 VCD：`docs/rbt2vcd.md`
- 创建 Vivado 工程：`docs/create-project.md`
- 配置板烧写程序 V2：`docs/config-board-v2.md`
- 生成 UCF 约束：`docs/generate-ucf.md`
- 提取测试项名字：`docs/extract-testcase.md`
