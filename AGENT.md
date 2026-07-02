# FPGA-tools 主界面 Agent 准则

本文件只描述统一主界面、子工具注册方式，以及主界面暴露给子工具的公共接口。每个子工具的内部结构、业务规则、文件格式、测试样例和维护约定，由该子工具目录内的 `AGENT.md` 单独维护。

## 项目定位

- 本项目是个人 FPGA 工具集合，使用一个统一桌面 GUI 管理多个子工具。
- 主界面通过左侧工具导航切换不同工具；每个子工具在右侧内容区中表现为一个独立页面。
- 主界面只管理应用壳、工具发现、公共服务和跨工具一致性，不实现具体 FPGA 转换或解析逻辑。

## 运行环境与 GUI 技术栈

- 本项目默认使用项目内虚拟环境 `py38`；运行、测试、安装依赖时优先使用该环境。
- GUI 统一使用 `PyQt5` 开发，主界面和子工具页面都应保持 PyQt5 兼容。
- 不要在未说明原因的情况下引入其他 GUI 框架、切换 Python 环境或升级 Qt 主版本。

## 文档分层

- 根目录 `AGENT.md`：只维护主界面契约、注册表约定、公共服务接口和子工具入口清单。
- 子工具 `AGENT.md`：维护该工具自己的业务边界、文件格式假设、内部目录、依赖、测试和验证方式。
- 新增或改造子工具时，必须先确认该工具目录下有自己的 `AGENT.md`，再把入口登记到本文档的“子工具入口清单”。

## 主界面职责

主界面负责：

- 创建 `QApplication`、`QMainWindow`、菜单栏、状态栏、左侧工具导航和右侧页面容器。
- 从 `tools_registry.py` 读取子工具元数据，按注册顺序创建导航项和工具页面。
- 向子工具传入统一的 `ToolServices`，提供日志、配置路径、文件对话框、错误提示和进度上报等公共能力。
- 捕获子工具加载失败并在主界面中给出可见错误，避免单个工具失败导致整个应用崩溃。
- 保持跨工具一致的窗口标题、图标、状态提示和异常展示风格。
- 根据当前工具页面的推荐尺寸调整主窗口大小，避免主界面固定尺寸遮挡或浪费空间。

主界面不负责：

- 解析、转换、生成任何具体 FPGA 文件格式。
- 读取或修改子工具内部控件状态。
- 保存子工具私有配置。
- 直接 import 子工具内部实现模块；只能通过注册入口加载。

## 推荐主界面结构

```text
FPGA-tools/
  AGENT.md
  main.py
  tools_registry.py
  common/
    __init__.py
    services.py
    paths.py
    qt_helpers.py
  <tool_name>/
    AGENT.md
```

- `main.py` 是统一 GUI 入口。
- `tools_registry.py` 只保存子工具注册信息和懒加载入口。
- `common/services.py` 定义主界面暴露给子工具的服务接口。
- `common/paths.py` 处理应用级路径、配置目录和资源定位。
- `common/qt_helpers.py` 放跨工具复用的 Qt 辅助函数。

## 子工具注册契约

每个子工具目录必须暴露稳定入口，推荐在该目录的 `__init__.py` 中提供：

```python
TOOL_ID = "rbt2atp"
TOOL_NAME = "RBT 转 ATP"

def create_widget(parent=None, services=None):
    ...
```

要求：

- `TOOL_ID` 使用小写英文、数字和下划线，作为配置、日志、目录和注册表的稳定键。
- `TOOL_NAME` 是子工具导出的显示名，可以使用中文，并应与注册表显示名保持一致。
- 主界面导航项文字以 `tools_registry.py` 中的 `name` 为准；修改显示名时同步检查子工具 `TOOL_NAME` 和本文档入口清单。
- `create_widget()` 必须返回 `QWidget` 或其子类。
- `create_widget()` 只接收主界面传入的 `parent` 和 `services`，不要反向 import 主窗口。
- 子工具应通过有效的 `sizeHint()`、`minimumSize()`、初始窗口尺寸或 `preferred_size` 动态属性表达推荐显示尺寸。
- 子工具加载失败时应抛出清晰异常；主界面负责展示加载失败状态。

`tools_registry.py` 推荐保存以下信息：

```python
TOOLS = [
    {
        "id": "rbt2atp",
        "name": "RBT 转 ATP",
        "package": "RBT2ATP",
        "doc": "RBT2ATP/AGENT.md",
        "entry": "create_widget",
        "enabled": True,
    },
]
```

## ToolServices 接口

主界面向子工具传入 `services`，子工具只能通过该对象使用跨工具公共能力。推荐接口如下：

```python
class ToolServices:
    def log(self, tool_id, message, level="info"):
        ...

    def show_info(self, title, message, parent=None):
        ...

    def show_error(self, title, message, detail=None, parent=None):
        ...

    def select_file(self, parent=None, title="选择文件", filters="All Files (*)", start_dir=None):
        ...

    def select_directory(self, parent=None, title="选择文件夹", start_dir=None):
        ...

    def config_dir(self, tool_id):
        ...

    def data_dir(self, tool_id):
        ...

    def report_progress(self, tool_id, value, message=None):
        ...

    def set_busy(self, tool_id, busy=True, message=None):
        ...
```

接口约束：

- `log()` 面向主界面状态栏、日志面板或文件日志，不替代子工具自己的业务结果输出。
- `show_error()` 应保留 `detail` 供调试，不要吞掉原始异常上下文。
- `config_dir()` 和 `data_dir()` 返回应用统一管理的目录；子工具不要硬编码本机绝对路径。
- `report_progress()` 的 `value` 使用 `0..100`，无法量化时传 `None` 并提供 `message`。
- 耗时任务由子工具自己放到后台线程；主界面只提供状态呈现接口。

## 路径与输出约定

- GUI 业务输出文件应写到用户明确选择的目录，或需求约定的程序所在目录；不要写到 Python 模块所在目录。
- 打包为 Nuitka onefile 后，`__file__` 可能指向运行时临时解压目录，不能用它推导业务输出目录。
- 需要写到程序所在目录时，打包环境应使用可执行文件所在目录，源码运行时可使用启动脚本所在目录。
- `ToolServices.config_dir()` 和 `ToolServices.data_dir()` 只用于应用配置、缓存或内部状态，不作为用户可见业务输出的默认目录，除非该子工具文档明确要求。

路径使用应先区分文件类型：

- 源码/内置只读资源：例如 `.ui`、图标、默认 JSON/XML 配置、模板文件等。源码运行可从模块目录读取；Nuitka onefile 打包后这些文件必须作为 data file 一起打入包内，运行时只能把 `__file__` 当作“内置资源候选路径”，不能把它当作业务输出或用户可编辑位置。
- 外置用户可编辑配置：只有需求和子工具文档明确允许用户覆盖默认配置时才加入外置读取；外置配置路径必须在代码中集中表达，缺失时给出清晰状态提示，不要静默回退。未明确要求外置覆盖的业务默认配置应作为包内只读资源处理。
- 应用内部状态/缓存：使用 `ToolServices.config_dir(tool_id)` 或 `ToolServices.data_dir(tool_id)`，不要写入源码目录、Nuitka 临时解包目录或当前工作目录。
- 用户可见生成文件：写到用户选择的输入文件旁、输出目录或业务明确约定的位置；禁止默认写入 `Path(__file__).parent`，避免打包后写入临时目录或失败。
- 程序所在目录：仅在需求明确要求“exe 所在目录”或“程序旁边”时使用；Nuitka onefile 下 `sys.executable` 也可能指向临时解包程序，不能单独依赖它。应优先使用明确的外置根目录、Nuitka 原始启动路径信息或 `sys.argv[0]` 推导 exe 旁路径，再把 `sys.executable` 只作为候选之一；源码运行时用启动入口或项目根目录，并在代码中说明两种路径来源。
- 路径拼接统一使用 `pathlib.Path`；涉及用户输入路径时应校验存在性、类型和失败原因。

## 打包资源与新增文件约定

新增或引入运行时依赖文件时，必须同步判断它属于哪一类并更新对应位置：

- Python 模块：确认所在包有稳定入口，必要时更新 `__init__.py`、`tools_registry.py`、语法检查命令和相关文档。
- 运行时读取的非 Python 文件：例如 `.ui`、`.ico`、`.json`、`.xml`、`.dll`、模板、示例默认配置等，必须在 `.github/workflows/build-windows-exe.yml` 的 Nuitka 命令中添加 `--include-data-files` 或 `--include-data-dir`，并保持打包内相对路径与代码查找路径一致。
- 子工具私有资源：优先放在对应子工具目录下，由子工具文档记录文件用途、编码、查找顺序和打包要求。
- 用户编辑型配置：是否支持外置覆盖必须由需求和子工具 `AGENT.md` 明确约定；不支持外置覆盖时，配置文件应只作为包内资源读取。
- 生成文件或缓存文件：不得加入打包清单；应写入用户输出目录、`config_dir()` 或 `data_dir()`。

每次新增、移动或重命名运行时文件后，至少检查：

1. 源码运行路径是否仍能找到该文件。
2. GitHub Action/Nuitka 打包清单是否包含该文件。
3. 打包后相对路径是否与代码查找路径一致。
4. 缺失文件时界面是否给出明确错误或状态提示。
5. 相关子工具 `AGENT.md` 是否记录了该文件的用途和维护方式。

## 主界面加载流程

1. 启动 `QApplication`。
2. 创建主窗口、左侧工具导航和右侧 `QStackedWidget` 页面容器。
3. 创建 `ToolServices` 实例。
4. 读取 `tools_registry.py` 中启用的工具。
5. 对每个工具执行懒加载，调用 `create_widget(parent=pages, services=services)`。
6. 将返回的 `QWidget` 添加到 `QStackedWidget`，并在左侧导航中添加注册表 `name`。
7. 加载完成或切换导航项时，根据当前页推荐尺寸调整主窗口。
8. 如果加载失败，创建一个错误占位页，显示工具名、文档入口和错误摘要。

## 主界面视觉与尺寸约定

- 主界面壳层样式集中在 `main.py` 的 `apply_visual_style()`，只负责菜单栏、左侧导航、状态栏、空页面和错误页。
- 主界面样式通过对象名限定范围，例如 `mainWindow`、`mainMenuBar`、`toolNavigation`、`toolPages`、`mainStatusBar`，避免通用 QSS 泄漏到子工具内部控件。
- 子工具内部控件样式由子工具自行维护；主界面不要用宽泛选择器统一改写 `QPushButton`、`QComboBox`、`QTableWidget` 等子控件。
- 导航项宽度由左侧栏宽度控制；新增长名称工具时优先调整 `toolSidebar` 宽度或工具显示名，而不是截短工具名。
- 主窗口根据当前工具页面推荐尺寸调整大小，优先使用子工具 `preferred_size` 动态属性，其次使用有效 `sizeHint()`、`minimumSize()` 或加载时记录的初始尺寸。
- 主窗口尺寸会限制在当前屏幕可用区域内；子工具不应假设主窗口一定等于自己的 `.ui` 原始尺寸。

## 子工具入口清单

| TOOL_ID | 导航名称 | 目录 | 子工具文档 | 独立运行入口 | 主界面接入入口 |
| --- | --- | --- | --- | --- | --- |
| `rbt2atp` | RBT 转 ATP | `RBT2ATP/` | `RBT2ATP/AGENT.md` | `RBT2ATP/rbt2atp_gui.py` | `RBT2ATP.create_widget` |
| `rbt_file_organization` | RBT文件整理 | `rbt_file_organization/` | `rbt_file_organization/AGENT.md` | `rbt_file_organization/rbt_file_organization.py` | `rbt_file_organization.create_widget` |
| `rbt_bit_converter` | RBT/BIT互转 | `rbt_bit_converter/` | `rbt_bit_converter/AGENT.md` | `rbt_bit_converter/rbt2bit.py`, `rbt_bit_converter/bit2rbt.py` | `rbt_bit_converter.create_widget` |
| `rbt2vcd` | RBT转VCD | `RBT2VCD/` | `RBT2VCD/AGENT.md` | `RBT2VCD/rbt2vcd.py` | `RBT2VCD.create_widget` |
| `create_project` | 创建Vivado工程 | `create_project/` | `create_project/AGENT.md` | `create_project/create_project.py` | `create_project.create_widget` |
| `config_board_v2` | 配置板烧写程序-V2 | `config_board_v2/` | `config_board_v2/AGENT.md` | `config_board_v2/usbtest_gui.py` | `config_board_v2.create_widget` |
| `generate_ucf` | 生成UCF约束 | `GenerateUcf/` | `GenerateUcf/AGENT.md` | `GenerateUcf/generate_ucf.py` | `GenerateUcf.create_widget` |

## 新增子工具登记要求

- 子工具必须有独立目录和该目录下的 `AGENT.md`。
- 子工具目录必须提供稳定 `TOOL_ID`、`TOOL_NAME` 和 `create_widget()`。
- 在 `tools_registry.py` 登记工具后，同步更新本文档的“子工具入口清单”。
- 根文档不写子工具内部实现细节；只写主界面需要知道的入口和契约。

## 主界面完成标准

- 主 GUI 可以启动，且左侧导航项按注册表顺序加载。
- 任一子工具加载失败时，主界面仍可打开并展示错误占位页。
- 主界面只通过 `create_widget()` 和 `ToolServices` 与子工具交互。
- 根文档中的入口清单和 `tools_registry.py` 保持一致。
- 主界面相关修改完成后，至少进行一次启动冒烟验证。
