# FPGA-tools

PyQt5 桌面端 FPGA 工具集合，集成 RBT 转 ATP、RBT 文件整理、RBT/BIT 互转、RBT 转 VCD、Vivado 工程创建和 FTDI 配置板烧写/回读验证。

## 项目简介

`FPGA-tools` 是一个个人 FPGA 辅助工具箱。项目用统一的 PyQt5 主界面管理多个子工具，通过左侧导航切换工具、右侧显示对应工具页面，也保留部分独立命令行或 GUI 入口，适合在 FPGA 日常开发、码流处理和配置板调试流程中复用。

当前包含的工具：

| 工具 | 入口 | 功能 |
| --- | --- | --- |
| RBT 转 ATP | `RBT2ATP/` | 将 `.rbt` 配置数据转换为 `.atp` 向量文件，支持单文件和批量目录转换 |
| RBT 文件整理 | `rbt_file_organization/` | 扫描目录中的 `.rbt` 文件并整理复制到 `rbt/` 子目录 |
| RBT/BIT 互转 | `rbt_bit_converter/` | 支持 `.rbt` 转 `.bit` 和 `.bit` 转 `.rbt`，GUI 可多文件批量转换 |
| RBT 转 VCD | `RBT2VCD/` | 将 Xilinx ASCII `.rbt` 文件转换为 SelectMAP 风格 `.vcd` 文件，GUI 可多文件批量转换 |
| 创建 Vivado 工程 | `create_project/` | 创建 Vivado 工程目录结构，或生成 Tcl 并调用 Vivado batch 构建工程 |
| 配置板烧写程序 V2 | `config_board_v2/` | 通过 FTDI USB 设备执行握手、擦除、配置、ReadBack、回读验证和码流转换 |
| 生成 UCF 约束 | `GenerateUcf/` | 使用 JSON profile 配置模块、层级模板和坐标规则，生成 `.ucf` 约束文件 |

## 环境要求

- Windows 环境优先，部分工具默认路径和硬件依赖面向 Windows。
- Python 3.8+。
- PyQt5，用于主界面和各子工具 GUI。
- Vivado，仅在使用“创建 Vivado 工程”的构建功能时需要。
- FTDI D2XX 驱动和 `ftd2xx` Python 包，仅在使用“配置板烧写程序 V2”的 USB 硬件功能时需要。

项目文档中推荐使用项目内 `py38` 虚拟环境；如果本地没有该环境，可以自行创建虚拟环境后安装依赖。

```powershell
python -m venv py38
.\py38\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install PyQt5
```

使用配置板烧写功能时，再安装：

```powershell
python -m pip install ftd2xx
```

## 快速开始

启动统一主界面：

```powershell
python main.py
```

主界面会按 `tools_registry.py` 中的注册顺序加载所有启用工具。单个子工具加载失败时，主界面仍会打开，并在对应工具页面展示错误信息。

## 独立工具入口

部分工具可以单独运行，便于调试或脚本化调用。

### RBT 转 ATP

```powershell
python .\RBT2ATP\rbt2atp_gui.py
```

### RBT 文件整理

```powershell
python .\rbt_file_organization\rbt_file_organization.py <待整理目录>
```

整理规则：

- 输出目录固定为输入目录下的 `rbt/`。
- `.rbt` 扩展名匹配不区分大小写。
- 扫描时跳过输出目录，避免重复整理。
- 目标文件已存在时会覆盖，并在结果中标记。

### RBT/BIT 互转

```powershell
python .\rbt_bit_converter\rbt2bit.py .\example.rbt
python .\rbt_bit_converter\bit2rbt.py .\example.bit
```

GUI 中可以分别选择多个 `.rbt` 或 `.bit` 文件批量转换。RBT 转 BIT 默认输出 `<原文件名>.bit`，BIT 转 RBT 默认输出 `<原文件名>.rbt`；勾选界面中的 `提取码流编号` 后，会输出 `No<原文件名>.rbt`。

### RBT 转 VCD

```powershell
python .\RBT2VCD\rbt2vcd.py .\example.rbt .\example.vcd
```

GUI 中可以选择多个 `.rbt` 文件批量转换。默认输出到每个输入文件所在目录，也可以指定统一输出目录。

### 创建 Vivado 工程

创建工程目录结构：

```powershell
python .\create_project\create_project.py demo_project mkdir --root-dir D:\fpga
```

基于已有目录生成 Tcl 并调用 Vivado：

```powershell
python .\create_project\create_project.py demo_project project --root-dir D:\fpga --device xcvu9p-flgb2104-2L-e --vivado-path C:\Xilinx\Vivado\2019.1\bin\vivado.bat
```

`mkdir` 模式会创建：

```text
<root-dir>/<project-name>/source/hdl
<root-dir>/<project-name>/source/sim
<root-dir>/<project-name>/source/xdc
```

### 配置板烧写程序 V2

启动独立 GUI：

```powershell
python .\config_board_v2\usbtest_gui.py
```

命令行示例：

```powershell
python .\config_board_v2\usbtest_py.py handshake
python .\config_board_v2\usbtest_py.py erase 1
python .\config_board_v2\usbtest_py.py program .\example.bit
python .\config_board_v2\usbtest_py.py readback 1 -o readback.bit
python .\config_board_v2\usbtest_py.py verify .\example.bit
python .\config_board_v2\usbtest_py.py convert .\example.rbt
```

`erase` 和 `readback` 的参数是 flash 地址；需要手动指定设备型号时，可以在子命令前添加 `--device BQ2V1000`、`--device BQ2V3000` 或 `--device BQ2V6000`。该工具需要可用的 FTDI D2XX 驱动、USB 设备和对应硬件连接。无 FTDI 环境时，GUI 应能加载并显示环境异常或设备未插入状态。

### 生成 UCF 约束

命令行生成：

```powershell
python -m GenerateUcf.generate_ucf --profile type1 --output constraints.ucf
python -m GenerateUcf.generate_ucf --profile type2 --preview 10
python -m GenerateUcf.generate_ucf --profile .\my_profile.json --output .\constraints.ucf
```

也可以在主界面中打开“生成UCF约束”，选择内置或外部 JSON profile，在左侧修改参数，右侧实时预览输出示例。

## 项目结构

```text
FPGA-tools/
  main.py                      # 统一 PyQt5 主界面入口
  tools_registry.py            # 子工具注册表
  common/
    services.py                # 主界面提供给子工具的公共服务
  RBT2ATP/                     # RBT 转 ATP 工具
  rbt_file_organization/       # RBT 文件整理工具
  rbt_bit_converter/           # RBT/BIT 互转工具
  RBT2VCD/                     # RBT 转 VCD 工具
  create_project/              # Vivado 工程创建工具
  config_board_v2/             # 配置板烧写和回读工具
  GenerateUcf/                  # UCF 约束生成工具
```

新增子工具时，需要：

1. 新建独立工具目录和该目录下的 `AGENT.md`。
2. 在工具目录的 `__init__.py` 中暴露 `TOOL_ID`、`TOOL_NAME` 和 `create_widget(parent=None, services=None)`。
3. 在 `tools_registry.py` 中登记工具元数据。
4. 同步更新根目录 `AGENT.md` 的子工具入口清单。

## 开发与验证

主界面和子工具 GUI 都使用 PyQt5。修改后建议至少运行语法检查：

```powershell
python -m py_compile main.py tools_registry.py common\services.py
python -m py_compile create_project\create_project.py create_project\widget.py create_project\__init__.py
python -m py_compile rbt_file_organization\core.py rbt_file_organization\widget.py rbt_file_organization\__init__.py
python -m py_compile rbt_bit_converter\rbt2bit.py rbt_bit_converter\bit2rbt.py rbt_bit_converter\widget.py rbt_bit_converter\__init__.py
python -m py_compile RBT2VCD\rbt2vcd.py RBT2VCD\widget.py RBT2VCD\__init__.py
python -m py_compile config_board_v2\usbtest_py.py config_board_v2\widget.py config_board_v2\usbtest_gui.py config_board_v2\__init__.py
python -m py_compile GenerateUcf\core.py GenerateUcf\generate_ucf.py GenerateUcf\widget.py GenerateUcf\__init__.py
```

GUI 相关修改建议再做一次启动冒烟验证：

```powershell
python main.py
```

涉及 Vivado 或 FTDI 的功能需要在具备对应软件、驱动和硬件的机器上验证。

## 维护原则

- 主界面只负责应用壳、工具页面加载、公共服务和错误展示，不实现具体 FPGA 文件格式逻辑。
- 子工具的业务规则应放在各自目录中，GUI 只负责输入、输出、状态和交互。
- 共享能力通过 `common/services.py` 提供，避免子工具反向依赖主窗口实现。
- 新增或调整文件格式、硬件协议、Vivado 流程时，同步更新对应子工具的 `AGENT.md`。
