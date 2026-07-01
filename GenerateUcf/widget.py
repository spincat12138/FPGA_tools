   # -*- coding: utf-8 -*-
import copy
import sys
import traceback
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from .core import (
    PROFILE_DIR,
    builtin_profile_paths,
    generate_text,
    load_profile,
    profile_from_json,
    profile_to_json,
    save_profile,
    write_ucf,
)
from .metadata import TOOL_ID, TOOL_NAME


PREVIEW_LINES = 80
ASSET_DIR = Path(__file__).resolve().parent / "assets"
COMBO_ARROW_PATH = (ASSET_DIR / "combo_down_arrow.svg").as_posix()
SPIN_UP_ARROW_PATH = (ASSET_DIR / "spin_up_arrow.svg").as_posix()
SCROLLBAR_STYLE = """
    QScrollBar:vertical {
    width: 8px;
    background: transparent;
    margin: 0px 0px 0px 0px;
    }

    QScrollBar::handle:vertical {
    background: #add8e6;
    min-height: 20px;
    border-radius: 4px;
    }

    QScrollBar::handle:vertical:hover {
    background: #87ceeb;
    }

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
    height: 0px;
    width: 0px;
    background: none;
    border: none;
    }

    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {
    background: transparent;
    }

    QScrollBar:horizontal {
    height: 8px;
    background: transparent;
    margin: 0px 0px 0px 0px;
    }

    QScrollBar::handle:horizontal {
    background: #add8e6;
    min-width: 20px;
    border-radius: 4px;
    }

    QScrollBar::handle:horizontal:hover {
    background: #87ceeb;
    }

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {
    width: 0px;
    height: 0px;
    background: none;
    border: none;
    }

    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {
    background: transparent;
    }
"""
COMBOBOX_STYLE = """
    QComboBox {
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 4px 26px 4px 6px;
    background-color: white;
    }

    QComboBox:focus {
    border: 1px solid #87ceeb;
    }

    QComboBox:disabled {
    background-color: #f5f7fa;
    border-color: #e4e7ed;
    color: #909399;
    }

    QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid #ccc;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
    background-color: #f5f5f5;
    }

    QComboBox::drop-down:hover {
    background-color: #e8e8e8;
    }

    QComboBox::down-arrow {
    image: url("__COMBO_ARROW_PATH__");
    width: 8px;
    height: 6px;
    margin-right: 7px;
    }

    QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #ccc;
    selection-background-color: #87ceeb;
    selection-color: #333;
    outline: 0;
    }
""".replace("__COMBO_ARROW_PATH__", COMBO_ARROW_PATH)
SPINBOX_STYLE = """
    QSpinBox {
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 2px 5px;
    background-color: white;
    }

    QSpinBox:focus {
    border: 1px solid #87ceeb;
    }

    QSpinBox:disabled {
    background-color: #f5f7fa;
    border-color: #e4e7ed;
    color: #909399;
    }

    QSpinBox::up-button,
    QSpinBox::down-button {
    width: 16px;
    background: #f0f0f0;
    border: 1px solid #dcdcdc;
    }

    QSpinBox::up-button {
    border-top-right-radius: 3px;
    }

    QSpinBox::down-button {
    border-bottom-right-radius: 3px;
    }

    QSpinBox::up-button:hover,
    QSpinBox::down-button:hover {
    background: #dce6f0;
    }

    QSpinBox::up-arrow {
    image: url("C:/Personal/Code/FPGA-tools/GenerateUcf/assets/spin_up_arrow.svg");
    width: 8px;
    height: 6px;
    }

    QSpinBox::down-arrow {
    image: url("C:/Personal/Code/FPGA-tools/GenerateUcf/assets/spin_down_arrow.svg");
    width: 8px;
    height: 6px;
    }
"""
SECTION_GROUP_STYLE = """
    QGroupBox {
    font-weight: bold;
    border: 1px solid #dcdcdc;
    border-radius: 6px;
    margin-top: 10px;
    padding: 10px;
    background-color: #f9f9f9;
    }

    QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 3px;
    }

    QLabel {
    color: #333;
    padding-right: 5px;
    }
"""


class GenerateUcfWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, services=None):
        super().__init__(parent)
        self.services = services
        self.current_profile = None
        self.current_profile_path = None
        self._updating_fields = False
        self._field_update_timer = None
        self.setObjectName("generateUcfWidget")
        self.setProperty("preferred_size", QtCore.QSize(1360, 640))
        self._build_ui()
        self._connect_field_updates()
        self.apply_visual_style()
        self._load_profile_choices()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(24, 22, 24, 18)
        main_layout.setSpacing(14)

        title = QtWidgets.QLabel(TOOL_NAME)
        title.setObjectName("title")

        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(8)
        self.profile_combo = QtWidgets.QComboBox()
        self._apply_combobox_style(self.profile_combo)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_selected)
        self.open_button = QtWidgets.QPushButton("打开JSON")
        self.reload_button = QtWidgets.QPushButton("重新加载")
        self.save_button = QtWidgets.QPushButton("保存JSON")
        self.save_as_button = QtWidgets.QPushButton("另存为")
        self.open_button.clicked.connect(self._open_profile_file)
        self.reload_button.clicked.connect(self._reload_current_profile)
        self.save_button.clicked.connect(self._save_current_profile)
        self.save_as_button.clicked.connect(self._save_profile_as)
        top_row.addWidget(QtWidgets.QLabel("Profile"))
        top_row.addWidget(self.profile_combo, 1)
        top_row.addWidget(self.open_button)
        top_row.addWidget(self.reload_button)
        top_row.addWidget(self.save_button)
        top_row.addWidget(self.save_as_button)

        body_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        body_splitter.setChildrenCollapsible(False)
        body_splitter.addWidget(self._build_editor_panel())
        body_splitter.addWidget(self._build_preview_panel())
        body_splitter.setStretchFactor(0, 0)
        body_splitter.setStretchFactor(1, 1)
        body_splitter.setSizes([600, 760])

        output_row = QtWidgets.QHBoxLayout()
        output_row.setSpacing(8)
        self.output_edit = QtWidgets.QLineEdit(str(Path.cwd() / "constraints.ucf"))
        self.output_edit.setPlaceholderText("选择输出 .ucf 文件")
        self.output_browse_button = QtWidgets.QPushButton("浏览...")
        self.generate_button = QtWidgets.QPushButton("生成UCF")
        self.open_output_button = QtWidgets.QPushButton("打开输出目录")
        self.open_output_button.setEnabled(False)
        self.output_browse_button.clicked.connect(self._browse_output)
        self.generate_button.clicked.connect(self._generate_ucf)
        self.open_output_button.clicked.connect(self._open_output_dir)
        output_row.addWidget(QtWidgets.QLabel("输出文件"))
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(self.output_browse_button)
        output_row.addWidget(self.generate_button)
        output_row.addWidget(self.open_output_button)

        self.status_label = QtWidgets.QLabel("")
        self.status_label.setObjectName("statusLabel")

        main_layout.addWidget(title)
        main_layout.addLayout(top_row)
        main_layout.addWidget(body_splitter, 1)
        main_layout.addLayout(output_row)
        main_layout.addWidget(self.status_label)

    def _build_editor_panel(self):
        group = QtWidgets.QGroupBox("参数设置")
        group.setMinimumWidth(580)
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(12, 18, 12, 12)
        layout.setSpacing(10)

        self.name_edit = QtWidgets.QLineEdit()
        self.line_mode_combo = QtWidgets.QComboBox()
        self._apply_combobox_style(self.line_mode_combo)
        self.line_mode_combo.addItems(["single", "paired"])
        self.path_template_edit = QtWidgets.QLineEdit()

        self.module_kind_combo = QtWidgets.QComboBox()
        self._apply_combobox_style(self.module_kind_combo)
        self.module_kind_combo.addItems(["range", "list"])
        self.module_template_edit = QtWidgets.QLineEdit()
        self.module_start_spin = self._spin(-100000, 100000, 0)
        self.module_stop_spin = self._spin(-100000, 100000, 1)
        self.module_range_row = self._two_widget_row(
            "起始", self.module_start_spin, "结束", self.module_stop_spin
        )
        self.module_values_edit = QtWidgets.QPlainTextEdit()
        self.module_values_edit.setFixedHeight(70)
        self.module_values_edit.setPlaceholderText("每行一个模块名")

        self.uxx_kind_combo = QtWidgets.QComboBox()
        self._apply_combobox_style(self.uxx_kind_combo)
        self.uxx_kind_combo.addItems(["range", "list"])
        self.uxx_start_spin = self._spin(-100000, 100000, 0)
        self.uxx_stop_spin = self._spin(-100000, 100000, 31)
        self.uxx_range_row = self._two_widget_row(
            "起始", self.uxx_start_spin, "结束", self.uxx_stop_spin
        )
        self.uxx_format_edit = QtWidgets.QLineEdit("u%02d")
        self.uxx_values_edit = QtWidgets.QLineEdit()
        self.uxx_values_edit.setPlaceholderText("例如 u00,u01,u02")

        self.uy_kind_combo = QtWidgets.QComboBox()
        self._apply_combobox_style(self.uy_kind_combo)
        self.uy_kind_combo.addItems(["range", "list", "none"])
        self.uy_start_spin = self._spin(-100000, 100000, 1)
        self.uy_stop_spin = self._spin(-100000, 100000, 8)
        self.uy_range_row = self._two_widget_row(
            "起始", self.uy_start_spin, "结束", self.uy_stop_spin
        )
        self.uy_format_edit = QtWidgets.QLineEdit("u%d")
        self.uy_values_edit = QtWidgets.QLineEdit()
        self.uy_values_edit.setPlaceholderText("例如 A,B,C,D")

        self.x_base_spin = self._spin(-100000, 100000, 0)
        self.x_jump_spin = self._spin(-100000, 100000, 1)
        self.x_row = self._two_widget_row("起点", self.x_base_spin, "步进", self.x_jump_spin)
        self.y_slice_spin = self._spin(1, 100000, 80)
        self.y_jump_spin = self._spin(1, 100000, 1)
        self.y_row = self._two_widget_row("范围", self.y_slice_spin, "步进", self.y_jump_spin)
        self.block_a_edit = QtWidgets.QLineEdit("TestBlockA")
        self.block_b_edit = QtWidgets.QLineEdit("TestBlockB")
        self.block_b_y_offset_spin = self._spin(-100000, 100000, 0)

        output_group, output_form = self._form_group("输出设置")
        output_form.addRow("名称", self.name_edit)
        output_form.addRow("输出模式", self.line_mode_combo)
        output_form.addRow("路径模板", self.path_template_edit)
        output_form.addRow("X", self.x_row)
        output_form.addRow("Y", self.y_row)
        output_form.addRow("第一列名称", self.block_a_edit)
        output_form.addRow("第二列名称", self.block_b_edit)
        output_form.addRow("Y相对偏移", self.block_b_y_offset_spin)

        module_group, module_form = self._form_group("模块")
        module_form.addRow("类型", self.module_kind_combo)
        module_form.addRow("模板", self.module_template_edit)
        module_form.addRow("范围", self.module_range_row)
        module_form.addRow("列表", self.module_values_edit)

        uxx_group, uxx_form = self._form_group("uxx")
        uxx_form.addRow("类型", self.uxx_kind_combo)
        uxx_form.addRow("范围", self.uxx_range_row)
        uxx_form.addRow("格式", self.uxx_format_edit)
        uxx_form.addRow("列表", self.uxx_values_edit)

        uy_group, uy_form = self._form_group("uy")
        uy_form.addRow("类型", self.uy_kind_combo)
        uy_form.addRow("范围", self.uy_range_row)
        uy_form.addRow("格式", self.uy_format_edit)
        uy_form.addRow("列表", self.uy_values_edit)

        form_widget = QtWidgets.QWidget()
        form_layout = QtWidgets.QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(10)
        form_layout.addWidget(output_group)
        form_layout.addWidget(module_group)
        form_layout.addWidget(uxx_group)
        form_layout.addWidget(uy_group)
        form_layout.addStretch(1)
        form_scroll = QtWidgets.QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        form_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        form_scroll.setWidget(form_widget)
        self._apply_scrollbar_style(form_scroll)

        layout.addWidget(form_scroll, 2)
        return group

    def _build_preview_panel(self):
        group = QtWidgets.QGroupBox("输出示例")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(12, 18, 12, 12)
        layout.setSpacing(8)

        self.preview_edit = QtWidgets.QPlainTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        font = QtGui.QFont("Consolas")
        font.setStyleHint(QtGui.QFont.Monospace)
        self.preview_edit.setFont(font)
        self._apply_scrollbar_style(self.preview_edit)

        preview_hint = QtWidgets.QLabel("右侧显示前 {count} 行生成结果。".format(count=PREVIEW_LINES))
        preview_hint.setObjectName("hintLabel")
        layout.addWidget(preview_hint)
        layout.addWidget(self.preview_edit, 1)
        return group

    def apply_visual_style(self):
        self.setStyleSheet("""
            QWidget#generateUcfWidget {
            background-color: #f5f7fa;
            }

            QLabel#title {
            color: #2c3e50;
            font-size: 24px;
            font-weight: bold;
            font-family: '微软雅黑';
            }

            QLabel {
            color: #2c3e50;
            }

            QLabel#hintLabel,
            QLabel#statusLabel {
            color: #606266;
            }

            QGroupBox {
            background-color: #ffffff;
            border: 1px solid #dcdfe6;
            border-radius: 4px;
            margin-top: 8px;
            color: #2c3e50;
            font-weight: bold;
            }

            QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 6px;
            left: 8px;
            }

            QGroupBox#sectionGroup {
            background-color: #ffffff;
            border: 1px solid #dcdfe6;
            border-radius: 6px;
            margin-top: 12px;
            color: #2c3e50;
            font-weight: bold;
            }

            QGroupBox#sectionGroup::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 6px;
            left: 10px;
            top: 1px;
            background-color: #ffffff;
            }

            QLineEdit,
            QComboBox,
            QSpinBox,
            QPlainTextEdit {
            background-color: #ffffff;
            border: 1px solid #dcdfe6;
            border-radius: 4px;
            padding: 5px 7px;
            color: #303133;
            min-height: 20px;
            }

            QLineEdit:focus,
            QComboBox:focus,
            QSpinBox:focus,
            QPlainTextEdit:focus {
            border-color: #409eff;
            }

            QLineEdit:disabled,
            QComboBox:disabled,
            QSpinBox:disabled,
            QPlainTextEdit:disabled {
            background-color: #f5f7fa;
            border-color: #e4e7ed;
            color: #909399;
            }

            QComboBox {
            padding-right: 26px;
            }

            QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 24px;
            border-left: 1px solid #dcdfe6;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
            background-color: #f5f7fa;
            }

            QComboBox::drop-down:hover {
            background-color: #ecf5ff;
            border-left-color: #409eff;
            }

            QComboBox::down-arrow {
            image: none;
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #606266;
            margin-right: 8px;
            }

            QSpinBox {
            padding-right: 22px;
            }

            QSpinBox::up-button,
            QSpinBox::down-button {
            subcontrol-origin: border;
            width: 20px;
            border-left: 1px solid #dcdfe6;
            background-color: #f5f7fa;
            }

            QSpinBox::up-button {
            subcontrol-position: top right;
            border-top-right-radius: 4px;
            }

            QSpinBox::down-button {
            subcontrol-position: bottom right;
            border-bottom-right-radius: 4px;
            }

            QSpinBox::up-button:hover,
            QSpinBox::down-button:hover {
            background-color: #ecf5ff;
            border-left-color: #409eff;
            }

            QSpinBox::up-arrow {
            image: none;
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid #606266;
            }

            QSpinBox::down-arrow {
            image: none;
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #606266;
            }

            QPushButton {
            background-color: #409eff;
            color: white;
            border-radius: 4px;
            padding: 5px 15px;
            font-weight: bold;
            }

            QPushButton:hover {
            background-color: #66b1ff;
            }

            QPushButton:disabled {
            background-color: #c0c4cc;
            color: #ffffff;
            }

            QCheckBox {
            color: #2c3e50;
            }

            QScrollArea {
            background-color: transparent;
            border: none;
            }
        """)

    def _apply_scrollbar_style(self, widget):
        widget.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        widget.horizontalScrollBar().setStyleSheet(SCROLLBAR_STYLE)

    def _apply_combobox_style(self, widget):
        widget.setStyleSheet(COMBOBOX_STYLE)

    def _apply_spinbox_style(self, widget):
        widget.setStyleSheet(SPINBOX_STYLE)

    def _load_profile_choices(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for path in builtin_profile_paths():
            self.profile_combo.addItem("内置：{name}".format(name=path.stem), str(path))
        self.profile_combo.blockSignals(False)
        if self.profile_combo.count():
            self.profile_combo.setCurrentIndex(0)
            self._on_profile_selected(0)

    def _on_profile_selected(self, index):
        path = self.profile_combo.itemData(index)
        if not path:
            return
        self._load_profile_path(Path(path))

    def _load_profile_path(self, path):
        try:
            profile = load_profile(path)
        except Exception as exc:
            self._show_error("加载失败", str(exc), detail=traceback.format_exc())
            return
        self.current_profile = profile
        self.current_profile_path = Path(path)
        self._show_profile(profile)
        self._set_status("已加载：{path}".format(path=path))

    def _show_profile(self, profile):
        self._updating_fields = True
        try:
            self._populate_fields(profile)
        finally:
            self._updating_fields = False
        self._refresh_preview(profile)

    def _populate_fields(self, profile):
        self.name_edit.setText(str(profile.get("name", "")))
        self.line_mode_combo.setCurrentText(profile["output"].get("line_mode", "single"))
        self.path_template_edit.setText(profile.get("path_template", ""))

        modules = profile["modules"]
        self.module_kind_combo.setCurrentText(modules.get("kind", "range"))
        self.module_template_edit.setText(modules.get("template", "A[{i}].u"))
        self.module_start_spin.setValue(int(modules.get("start", 0)))
        self.module_stop_spin.setValue(int(modules.get("stop", 1)))
        self.module_values_edit.setPlainText("\n".join(str(value) for value in modules.get("values", [])))

        uxx = self._normalize_uxx_for_fields(profile["uxx"])
        self.uxx_kind_combo.setCurrentText(uxx.get("kind", "range"))
        self.uxx_start_spin.setValue(int(uxx.get("start", 0)))
        self.uxx_stop_spin.setValue(int(uxx.get("stop", 31)))
        self.uxx_format_edit.setText(uxx.get("format", "u%02d"))
        self.uxx_values_edit.setText(",".join(str(value) for value in uxx.get("values", [])))

        uy = profile["uy"]
        self.uy_kind_combo.setCurrentText(uy.get("kind", "none"))
        self.uy_start_spin.setValue(int(uy.get("start", 1)))
        self.uy_stop_spin.setValue(int(uy.get("stop", 8)))
        self.uy_format_edit.setText(uy.get("format", "u%d"))
        self.uy_values_edit.setText(",".join(str(value) for value in uy.get("values", [])))

        placement = profile["placement"]
        self.x_base_spin.setValue(int(placement.get("x_base", 0)))
        self.x_jump_spin.setValue(int(placement.get("x_jump", 1)))
        self.y_slice_spin.setValue(int(placement.get("y_slice", 80)))
        self.y_jump_spin.setValue(int(placement.get("y_jump", 1)))

        blocks = profile.get("blocks", [])
        self.block_a_edit.setText(self._block_name(blocks, 0))
        self.block_b_edit.setText(self._block_name(blocks, 1))
        self.block_b_y_offset_spin.setValue(int(blocks[1].get("y_offset", 0)) if len(blocks) > 1 else 0)
        self._update_field_states()

    def _connect_field_updates(self):
        self._field_update_timer = QtCore.QTimer(self)
        self._field_update_timer.setSingleShot(True)
        self._field_update_timer.setInterval(250)
        self._field_update_timer.timeout.connect(lambda: self._apply_fields_to_profile(show_errors=False))

        for widget in (
            self.name_edit,
            self.path_template_edit,
            self.module_template_edit,
            self.uxx_format_edit,
            self.uxx_values_edit,
            self.uy_format_edit,
            self.uy_values_edit,
            self.block_a_edit,
            self.block_b_edit,
        ):
            widget.textChanged.connect(self._schedule_field_apply)

        for widget in (
            self.line_mode_combo,
            self.module_kind_combo,
            self.uxx_kind_combo,
            self.uy_kind_combo,
        ):
            widget.currentIndexChanged.connect(self._schedule_field_apply)
            widget.currentIndexChanged.connect(self._update_field_states)
        self.line_mode_combo.currentIndexChanged.connect(self._sync_path_template_for_line_mode)
        self.uxx_kind_combo.currentIndexChanged.connect(self._sync_uxx_format_for_kind)

        for widget in (
            self.module_start_spin,
            self.module_stop_spin,
            self.uxx_start_spin,
            self.uxx_stop_spin,
            self.uy_start_spin,
            self.uy_stop_spin,
            self.x_base_spin,
            self.x_jump_spin,
            self.y_slice_spin,
            self.y_jump_spin,
            self.block_b_y_offset_spin,
        ):
            widget.valueChanged.connect(self._schedule_field_apply)

        self.module_values_edit.textChanged.connect(self._schedule_field_apply)

    def _schedule_field_apply(self):
        if self._updating_fields or self._field_update_timer is None:
            return
        self._field_update_timer.start()

    def _apply_fields_to_profile(self, show_errors=True):
        try:
            base = self.current_profile or {}
            updated = self._profile_from_fields(base)
            profile_from_json(profile_to_json(updated))
        except Exception as exc:
            if show_errors:
                self._show_error("参数无效", str(exc), detail=traceback.format_exc())
            else:
                self.preview_edit.setPlainText("参数无效：{error}".format(error=exc))
                self._set_status("参数尚未通过校验")
            return

        self.current_profile = updated
        self._refresh_preview(updated)
        if show_errors:
            self._set_status("参数已应用")

    def _profile_from_fields(self, base):
        profile = copy.deepcopy(base)
        profile["name"] = self.name_edit.text().strip() or "custom"
        profile.setdefault("output", {})["line_mode"] = self.line_mode_combo.currentText()
        profile["path_template"] = self.path_template_edit.text().strip()
        profile.pop("inst", None)

        module_kind = self.module_kind_combo.currentText()
        if module_kind == "range":
            profile["modules"] = {
                "kind": "range",
                "template": self.module_template_edit.text().strip() or "A[{i}].u",
                "start": self.module_start_spin.value(),
                "stop": self.module_stop_spin.value(),
            }
        else:
            profile["modules"] = {
                "kind": "list",
                "values": self._lines_to_values(self.module_values_edit.toPlainText()),
            }

        uxx_kind = self.uxx_kind_combo.currentText()
        if uxx_kind == "range":
            profile["uxx"] = {
                "kind": "range",
                "start": self.uxx_start_spin.value(),
                "stop": self.uxx_stop_spin.value(),
                "format": self.uxx_format_edit.text().strip() or "u%02d",
            }
        else:
            profile["uxx"] = {
                "kind": "list",
                "values": self._comma_to_values(self.uxx_values_edit.text()),
                "format": self.uxx_format_edit.text().strip() or "%s",
            }

        uy_kind = self.uy_kind_combo.currentText()
        if uy_kind == "none":
            profile["uy"] = {"kind": "none"}
        elif uy_kind == "range":
            profile["uy"] = {
                "kind": "range",
                "start": self.uy_start_spin.value(),
                "stop": self.uy_stop_spin.value(),
                "format": self.uy_format_edit.text().strip() or "u%d",
            }
        else:
            profile["uy"] = {
                "kind": "list",
                "values": self._comma_to_values(self.uy_values_edit.text()),
                "format": self.uy_format_edit.text().strip() or "%s",
            }

        profile["placement"] = {
            "x_base": self.x_base_spin.value(),
            "x_jump": self.x_jump_spin.value(),
            "y_slice": self.y_slice_spin.value(),
            "y_jump": self.y_jump_spin.value(),
        }

        if self.line_mode_combo.currentText() == "single":
            profile["blocks"] = [{
                "name": self._empty_to_none(self.block_a_edit.text()),
                "x_offset": 0,
                "y_offset": 0,
            }]
        else:
            profile["blocks"] = [
                {
                    "name": self._empty_to_none(self.block_a_edit.text()),
                    "x_offset": 0,
                    "y_offset": 0,
                },
                {
                    "name": self._empty_to_none(self.block_b_edit.text()),
                    "x_offset": 0,
                    "y_offset": self.block_b_y_offset_spin.value(),
                },
            ]
        return profile

    def _refresh_preview(self, profile):
        try:
            preview = generate_text(profile, limit=PREVIEW_LINES, include_end_marker=False)
        except Exception as exc:
            self.preview_edit.setPlainText("生成预览失败：{error}".format(error=exc))
            return
        self.preview_edit.setPlainText(preview)
        self._set_status("预览已更新，显示前 {count} 行".format(count=PREVIEW_LINES))

    def _open_profile_file(self):
        start_dir = str(PROFILE_DIR)
        path = self._select_file(
            title="选择 UCF Profile JSON",
            filters="JSON Files (*.json);;All Files (*)",
            start_dir=start_dir,
        )
        if not path:
            return
        self._load_external_profile(Path(path))

    def _load_external_profile(self, path):
        self._load_profile_path(path)
        display = "外部：{name}".format(name=path.name)
        existing_index = self._combo_index_for_path(path)
        if existing_index >= 0:
            self.profile_combo.setCurrentIndex(existing_index)
            return
        self.profile_combo.addItem(display, str(path))
        self.profile_combo.setCurrentIndex(self.profile_combo.count() - 1)

    def _reload_current_profile(self):
        if self.current_profile_path is None:
            return
        self._load_profile_path(self.current_profile_path)

    def _save_current_profile(self):
        if self.current_profile_path is None:
            self._save_profile_as()
            return
        try:
            profile = self._current_valid_profile()
            save_profile(profile, self.current_profile_path)
        except Exception as exc:
            self._show_error("保存失败", str(exc), detail=traceback.format_exc())
            return
        self.current_profile = profile
        self._set_status("已保存：{path}".format(path=self.current_profile_path))

    def _save_profile_as(self):
        start_dir = str(self.current_profile_path.parent if self.current_profile_path else PROFILE_DIR)
        path, _selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "另存为 Profile JSON",
            str(Path(start_dir) / "custom_profile.json"),
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return
        target = Path(path)
        if target.suffix.lower() != ".json":
            target = target.with_suffix(".json")
        try:
            profile = self._current_valid_profile()
            save_profile(profile, target)
        except Exception as exc:
            self._show_error("保存失败", str(exc), detail=traceback.format_exc())
            return
        self.current_profile = profile
        self.current_profile_path = target
        self._load_external_profile(target)
        self._set_status("已另存为：{path}".format(path=target))

    def _browse_output(self):
        current = Path(self.output_edit.text().strip() or "constraints.ucf")
        start = current if current.suffix else current / "constraints.ucf"
        path, _selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "选择输出 UCF 文件",
            str(start),
            "UCF Files (*.ucf);;All Files (*)",
        )
        if path:
            target = Path(path)
            if target.suffix.lower() != ".ucf":
                target = target.with_suffix(".ucf")
            self.output_edit.setText(str(target))

    def _generate_ucf(self):
        try:
            profile = self._current_valid_profile()
        except Exception as exc:
            self._show_error("Profile 无效", str(exc), detail=traceback.format_exc())
            return

        output_text = self.output_edit.text().strip()
        if not output_text:
            self._show_error("输出路径为空", "请先选择输出 .ucf 文件")
            return

        try:
            output_path = write_ucf(profile, output_text)
        except Exception as exc:
            self._show_error("生成失败", str(exc), detail=traceback.format_exc())
            return

        self.open_output_button.setEnabled(True)
        self._set_status("已生成：{path}".format(path=output_path))
        if self.services is not None:
            self.services.show_info("生成完成", "已生成：{path}".format(path=output_path), parent=self)

    def _open_output_dir(self):
        output_text = self.output_edit.text().strip()
        if not output_text:
            return
        path = Path(output_text)
        directory = path.parent if path.suffix else path
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(directory)))

    def _select_file(self, title, filters, start_dir):
        if self.services is not None:
            return self.services.select_file(
                parent=self,
                title=title,
                filters=filters,
                start_dir=start_dir,
            )
        path, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            title,
            start_dir,
            filters,
        )
        return path or None

    def _combo_index_for_path(self, path):
        target = str(Path(path))
        for index in range(self.profile_combo.count()):
            if self.profile_combo.itemData(index) == target:
                return index
        return -1

    def _spin(self, minimum, maximum, value):
        widget = QtWidgets.QSpinBox()
        widget.setRange(minimum, maximum)
        widget.setValue(value)
        self._apply_spinbox_style(widget)
        return widget

    def _form_group(self, title):
        group = QtWidgets.QGroupBox(title)
        group.setObjectName("sectionGroup")
        group.setStyleSheet(SECTION_GROUP_STYLE)
        form = QtWidgets.QFormLayout(group)
        form.setLabelAlignment(QtCore.Qt.AlignRight)
        form.setFormAlignment(QtCore.Qt.AlignTop)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.setContentsMargins(12, 18, 12, 12)
        return group, form

    def _two_widget_row(self, first_label, first_widget, second_label, second_widget):
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(QtWidgets.QLabel(first_label))
        layout.addWidget(first_widget, 1)
        layout.addWidget(QtWidgets.QLabel(second_label))
        layout.addWidget(second_widget, 1)
        return row

    def _update_field_states(self):
        module_is_range = self.module_kind_combo.currentText() == "range"
        self._set_widgets_enabled(
            [self.module_template_edit, self.module_start_spin, self.module_stop_spin, self.module_range_row],
            module_is_range,
        )
        self._set_widgets_enabled([self.module_values_edit], not module_is_range)

        uxx_is_range = self.uxx_kind_combo.currentText() == "range"
        self._set_widgets_enabled(
            [self.uxx_start_spin, self.uxx_stop_spin, self.uxx_range_row],
            uxx_is_range,
        )
        self._set_widgets_enabled([self.uxx_values_edit], not uxx_is_range)

        uy_kind = self.uy_kind_combo.currentText()
        uy_is_range = uy_kind == "range"
        uy_is_list = uy_kind == "list"
        self._set_widgets_enabled([self.uy_start_spin, self.uy_stop_spin, self.uy_range_row], uy_is_range)
        self._set_widgets_enabled([self.uy_values_edit], uy_is_list)
        self._set_widgets_enabled([self.uy_format_edit], uy_is_range or uy_is_list)

        paired = self.line_mode_combo.currentText() == "paired"
        self._set_widgets_enabled([self.block_a_edit], True)
        self._set_widgets_enabled(
            [self.block_b_edit, self.block_b_y_offset_spin],
            paired,
        )

    def _sync_path_template_for_line_mode(self):
        if self._updating_fields:
            return
        current = self.path_template_edit.text().strip()
        updated = self._path_template_for_line_mode(
            current,
            self.line_mode_combo.currentText(),
        )
        if updated != current:
            self.path_template_edit.setText(updated)

    def _path_template_for_line_mode(self, template, line_mode):
        placeholder = "{test_name}" if line_mode == "single" else "{block}"
        other_placeholder = "{block}" if line_mode == "single" else "{test_name}"
        if other_placeholder in template:
            return template.replace(other_placeholder, placeholder)
        if placeholder in template:
            return template
        if not template:
            return "{module}/{placeholder}/{uxx}/{uy}/*".format(placeholder=placeholder)
        if template.startswith("{module}/"):
            parts = template.split("/")
            if len(parts) >= 2:
                if parts[1] in {"{uxx}", "{uy}", "*"}:
                    parts.insert(1, placeholder)
                else:
                    parts[1] = placeholder
                return "/".join(parts)
        return template

    def _sync_uxx_format_for_kind(self):
        if self._updating_fields:
            return
        current = self.uxx_format_edit.text().strip()
        if self.uxx_kind_combo.currentText() == "list" and current == "u%02d":
            self.uxx_format_edit.setText("%s")
        elif self.uxx_kind_combo.currentText() == "range" and current == "%s":
            self.uxx_format_edit.setText("u%02d")

    def _set_widgets_enabled(self, widgets, enabled):
        for widget in widgets:
            widget.setEnabled(enabled)

    def _block_name(self, blocks, index):
        if len(blocks) <= index:
            return ""
        value = blocks[index].get("name")
        return "" if value is None else str(value)

    def _empty_to_none(self, text):
        value = text.strip()
        return value or None

    def _lines_to_values(self, text):
        return [line.strip() for line in text.splitlines() if line.strip()]

    def _comma_to_values(self, text):
        return [item.strip() for item in text.split(",") if item.strip()]

    def _normalize_uxx_for_fields(self, config):
        if config.get("kind") is None and "count" in config:
            return {
                "kind": "range",
                "start": 0,
                "stop": config.get("count", 32) - 1,
                "format": config.get("format", "u%02d"),
            }
        return config

    def _set_status(self, message):
        self.status_label.setText(message)
        if self.services is not None:
            self.services.log(TOOL_ID, message)

    def _show_error(self, title, message, detail=None):
        if self.services is not None:
            self.services.show_error(title, message, detail=detail, parent=self)
        else:
            QtWidgets.QMessageBox.critical(self, title, message)

    def _current_valid_profile(self):
        base = self.current_profile or {}
        profile = self._profile_from_fields(base)
        return profile_from_json(profile_to_json(profile))


def main():
    app = QtWidgets.QApplication(sys.argv)
    widget = GenerateUcfWidget()
    widget.resize(1360, 640)
    widget.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
