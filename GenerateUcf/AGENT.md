# GenerateUCF 子工具 Agent 准则

## 工具边界

- 本工具负责基于 JSON profile 生成 Xilinx UCF 约束文件。
- 通用生成逻辑放在 `core.py`，GUI 只负责选择、编辑、预览和保存 profile，以及调用生成函数。
- 内置 profile 位于 `profiles/*.json`，作为只读默认配置；用户可通过 GUI 另存为自己的 JSON。

## 入口

- 主界面入口：`GenerateUcf.create_widget`
- 独立 GUI：`python -m GenerateUcf.widget`
- 命令行：`python -m GenerateUcf.generate_ucf --profile type1 --output constraints.ucf`

## GUI 资源

- 主界面布局位于 `generate_ucf.ui`，只保存控件层级、布局、文案和基础控件属性。
- 视觉样式、运行时默认值、信号连接和业务逻辑仍保留在 `widget.py`。
- 修改或重命名 `.ui` 时，同步更新根目录 GitHub Actions 的 Nuitka data file 清单。

## 验证

修改后至少运行：

```powershell
python -m py_compile GenerateUcf\core.py GenerateUcf\generate_ucf.py GenerateUcf\widget.py GenerateUcf\__init__.py
python -m GenerateUcf.generate_ucf --profile type1 --preview 5
python -m GenerateUcf.generate_ucf --profile type2 --preview 5
python -m GenerateUcf.generate_ucf --profile type3 --preview 5
```
