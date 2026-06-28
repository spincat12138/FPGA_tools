# FPGA-tools 主界面 Agent 准则

本文件只描述统一主界面、子工具注册方式，以及主界面暴露给子工具的公共接口。每个子工具的内部结构、业务规则、文件格式、测试样例和维护约定，由该子工具目录内的 `AGENT.md` 单独维护。

## 项目定位

- 本项目是个人 FPGA 工具集合，使用一个统一桌面 GUI 管理多个子工具。
- 主界面通过标签页切换不同工具；每个子工具在主界面中表现为一个独立 Tab。
- 主界面只管理应用壳、工具发现、公共服务和跨工具一致性，不实现具体 FPGA 转换或解析逻辑。

## 运行环境与 GUI 技术栈

- 本项目默认使用项目内虚拟环境 `py38`；运行、测试、安装依赖时优先使用该环境。
- GUI 统一使用 `PyQt5` 开发，主界面和子工具标签页都应保持 PyQt5 兼容。
- 不要在未说明原因的情况下引入其他 GUI 框架、切换 Python 环境或升级 Qt 主版本。

## 文档分层

- 根目录 `AGENT.md`：只维护主界面契约、注册表约定、公共服务接口和子工具入口清单。
- 子工具 `AGENT.md`：维护该工具自己的业务边界、文件格式假设、内部目录、依赖、测试和验证方式。
- 新增或改造子工具时，必须先确认该工具目录下有自己的 `AGENT.md`，再把入口登记到本文档的“子工具入口清单”。

## 主界面职责

主界面负责：

- 创建 `QApplication`、`QMainWindow`、菜单栏、状态栏和中心 `QTabWidget`。
- 从 `tools_registry.py` 读取子工具元数据，按注册顺序创建标签页。
- 向子工具传入统一的 `ToolServices`，提供日志、配置路径、文件对话框、错误提示和进度上报等公共能力。
- 捕获子工具加载失败并在主界面中给出可见错误，避免单个工具失败导致整个应用崩溃。
- 保持跨工具一致的窗口标题、图标、状态提示和异常展示风格。
- 根据当前标签页子工具的推荐尺寸调整主窗口大小，避免主界面固定尺寸遮挡或浪费空间。

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
- 主界面标签页文字以 `tools_registry.py` 中的 `name` 为准；修改标签名时同步检查子工具 `TOOL_NAME` 和本文档入口清单。
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

## 主界面加载流程

1. 启动 `QApplication`。
2. 创建主窗口和中心 `QTabWidget`。
3. 创建 `ToolServices` 实例。
4. 读取 `tools_registry.py` 中启用的工具。
5. 对每个工具执行懒加载，调用 `create_widget(parent=tab_widget, services=services)`。
6. 将返回的 `QWidget` 添加到 `QTabWidget`，标签名使用注册表中的 `name`。
7. 加载完成或切换标签页时，根据当前页推荐尺寸调整主窗口。
8. 如果加载失败，创建一个错误占位页，显示工具名、文档入口和错误摘要。

## 主界面视觉与尺寸约定

- 主界面壳层样式集中在 `main.py` 的 `apply_visual_style()`，只负责菜单栏、标签页、状态栏、空页面和错误页。
- 主界面样式通过对象名限定范围，例如 `mainWindow`、`mainMenuBar`、`toolTabs`、`mainStatusBar`，避免通用 QSS 泄漏到子工具内部控件。
- 子工具内部控件样式由子工具自行维护；主界面不要用宽泛选择器统一改写 `QPushButton`、`QComboBox`、`QTableWidget` 等子控件。
- 标签页文字宽度由 `QTabWidget#toolTabs QTabBar::tab` 的 `min-width` 和 `padding` 控制；新增长名称工具时优先调整主界面标签样式，而不是截短工具名。
- 主窗口根据当前标签页推荐尺寸调整大小，优先使用子工具 `preferred_size` 动态属性，其次使用有效 `sizeHint()`、`minimumSize()` 或加载时记录的初始尺寸。
- 主窗口尺寸会限制在当前屏幕可用区域内；子工具不应假设主窗口一定等于自己的 `.ui` 原始尺寸。

## 子工具入口清单

| TOOL_ID | 标签页名称 | 目录 | 子工具文档 | 独立运行入口 | 主界面接入入口 |
| --- | --- | --- | --- | --- | --- |
| `rbt2atp` | RBT 转 ATP | `RBT2ATP/` | `RBT2ATP/AGENT.md` | `RBT2ATP/RBT2ATP软件.py` | `RBT2ATP.create_widget` |
| `rbt_file_organization` | RBT文件整理 | `rbt_file_organization/` | `rbt_file_organization/AGENT.md` | `rbt_file_organization/rbt_file_organization.py` | `rbt_file_organization.create_widget` |
| `create_project` | 创建Vivado工程 | `create_project/` | `create_project/AGENT.md` | `create_project/create_project.py` | `create_project.create_widget` |
| `config_board_v2` | 配置板烧写程序-V2 | `config_board_v2/` | `config_board_v2/AGENT.md` | `config_board_v2/usbtest_gui.py` | `config_board_v2.create_widget` |

## 新增子工具登记要求

- 子工具必须有独立目录和该目录下的 `AGENT.md`。
- 子工具目录必须提供稳定 `TOOL_ID`、`TOOL_NAME` 和 `create_widget()`。
- 在 `tools_registry.py` 登记工具后，同步更新本文档的“子工具入口清单”。
- 根文档不写子工具内部实现细节；只写主界面需要知道的入口和契约。

## 主界面完成标准

- 主 GUI 可以启动，且标签页按注册表顺序加载。
- 任一子工具加载失败时，主界面仍可打开并展示错误占位页。
- 主界面只通过 `create_widget()` 和 `ToolServices` 与子工具交互。
- 根文档中的入口清单和 `tools_registry.py` 保持一致。
- 主界面相关修改完成后，至少进行一次启动冒烟验证。
