# -*- coding: utf-8 -*-
import sys
import os
import json
from importlib import resources
from math import ceil
from pathlib import Path
import time

from PyQt5 import QtCore, QtGui, QtWidgets, uic

SELECTED_COLUMN_COLOR = QtGui.QColor(220, 246, 230)
REPEAT_COLUMN_COLOR = QtGui.QColor(226, 242, 255)
UNSELECTED_COLUMN_COLOR = QtGui.QColor(255, 255, 255)
PRESET_CONFIG_FILENAME = "presets.json"
TOOL_PACKAGE_NAME = "RBT2ATP"
TABLE_COLUMNS = ("REPEAT", "CCLK", "CSI", "RDWR", "PROG", "INIT", "DONE", "MODE", "PUDC", "BVS", "POR")
SIGNAL_COLUMNS = TABLE_COLUMNS[1:]
CONFIGURATION_MODES = ("x32", "x16", "x8", "x1")


class CompactTableEditDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QtWidgets.QLineEdit):
            editor.setFrame(False)
            editor.setAutoFillBackground(True)
            editor.setTextMargins(0, 0, 0, 0)
            editor.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            editor.setStyleSheet("""
                QLineEdit {
                    background-color: #ffffff;
                    border: 0px;
                    margin: 0px;
                    padding: 0px;
                    selection-background-color: #409eff;
                    selection-color: #ffffff;
                }
            """)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        rect = option.rect.adjusted(2, 3, -2, -3)
        editor.setGeometry(rect)


class RBT2ATP(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(RBT2ATP, self).__init__(parent)
        uic.loadUi(str(Path(__file__).with_name("RBT2ATPgui.ui")), self)
        RBT2ATP.setWindowIcon(self, QtGui.QIcon(str(Path(__file__).with_name('logo.ico'))))
        self.max_count = 60001
        self.default_list = [self.checkBox_CCLK, self.checkBox_CSI,
                             self.checkBox_RDWR, self.checkBox_PROG,
                             self.checkBox_INIT, self.checkBox_DONE]
        self.undefault_list = [self.checkBox_MODE, self.checkBox_PUDC,
                               self.checkBox_BVS, self.checkBox_POR]
        self.all_cb = self.default_list + self.undefault_list
        self.num_cb = len(self.all_cb)
        self.mode = [self.radioButton_x32, self.radioButton_x16, self.radioButton_x8, self.radioButton_x1]
        self.num_mode = len(self.mode)
        self.variables = ["CFG_CCLK", "CFG_CSI", "CFG_RDWR", "CFG_PROG", "CFG_INIT",
                          "CFG_DONE", "CFG_MODE", "CFG_PUDC", "CFG_BVS", "CFG_POR"]
        self.default_init()
        # self.pushButton_default.clicked.connect(self.default_button)
        self.pushButton_openFile.clicked.connect(self.open_file_button)
        self.tableWidget.cellChanged.connect(self.mode_value_change)
        for item in self.default_list + self.undefault_list:
            item.stateChanged.connect(self.check_box_change)
        self.pushButton_exchange.clicked.connect(self.exchange)
        self.compile_mode = self.comboBox_mod_choose.currentText()
        self.vector_name = self.comboBox_vector.currentText()
        self.mode_map = {
            "quad" : 4,
            "extend" : 1,
            "normal" : 2
        }
        self.tableWidget.setItemDelegate(CompactTableEditDelegate(self.tableWidget))
        self.apply_visual_style()
        self.presets = []
        self._setup_presets()

    def default_init(self):
        self.default_button()
        self.check_box_change()

    def apply_visual_style(self):
        self._set_combo_width(self.comboBox_vector, 126)
        self._set_combo_width(self.comboBox_mod_choose, 112)
        if hasattr(self, "comboBox_vector_2"):
            self._set_combo_width(self.comboBox_vector_2, 150)
        self.setStyleSheet("""
            QMainWindow {
            background-color: #f5f7fa;
            }


            QLabel#title {
            color: #2c3e50;
            font-size: 24px;
            font-weight: bold;
            font-family: '微软雅黑';
            }


            QTableWidget {
            background-color: white;
            border: 1px solid #dcdfe6;
            gridline-color: #e4e7ed;
            selection-background-color: #409eff;
            }


            QTableWidget::item {
            padding: 5px;
            }


            QHeaderView::section {
            background-color: #f8f9fb;
            padding: 4px;
            border: 1px solid #dcdfe6;
            font-weight: bold;
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


            QLineEdit {
            border: 1px solid #dcdfe6;
            border-radius: 4px;
            padding: 5px;
            }


            QComboBox {
            background-color: #ffffff;
            border: 1px solid #dcdfe6;
            border-radius: 4px;
            padding: 4px 22px 4px 6px;
            selection-background-color: #409eff;
            }


            QComboBox:hover {
            border-color: #c0c4cc;
            }


            QComboBox:focus {
            border-color: #409eff;
            }


            QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left: 1px solid #dcdfe6;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
            background-color: #f8f9fb;
            }


            QComboBox::drop-down:hover {
            background-color: #ecf5ff;
            }


            QComboBox QAbstractItemView {
            background-color: #ffffff;
            border: 1px solid #dcdfe6;
            outline: 0px;
            selection-background-color: #409eff;
            selection-color: #ffffff;
            padding: 2px;
            }


            QTableWidget QLineEdit {
            background-color: #ffffff;
            border: 0px;
            padding: 0px;
            selection-background-color: #409eff;
            }


            QProgressBar {
            border: 1px solid #dcdfe6;
            border-radius: 4px;
            text-align: center;
            }


            QProgressBar::chunk {
            background-color: #67c23a;
            }


            QTextBrowser {
            border: 1px solid #dcdfe6;
            background-color: #ffffff;
            }
        """)

    def _set_combo_width(self, combo_box, width):
        combo_box.setMinimumWidth(width)
        combo_box.setFixedWidth(width)
        parent = combo_box.parentWidget()
        if parent is not None and parent.layout() is not None:
            geometry = parent.geometry()
            hint_width = parent.layout().sizeHint().width()
            parent.setGeometry(geometry.x(), geometry.y(), max(geometry.width(), hint_width), geometry.height())

    def _setup_presets(self):
        if not hasattr(self, "comboBox_vector_2"):
            return

        self.presets = self._load_presets()
        self.comboBox_vector_2.clear()
        for preset in self.presets:
            self.comboBox_vector_2.addItem(preset["name"], preset)

        self.comboBox_vector_2.currentIndexChanged.connect(self.apply_selected_preset)
        if self.comboBox_vector_2.count() > 0:
            self.comboBox_vector_2.setCurrentIndex(0)
            self.apply_selected_preset(0)

    def _load_presets(self):
        try:
            raw_config = self._read_packaged_preset_config()
        except FileNotFoundError as exc:
            self._append_status(">>未找到内置预设配置文件：%s" % exc)
            return []
        except json.JSONDecodeError as exc:
            self._append_status(">>内置预设配置文件格式有误：%s" % exc)
            return []
        except OSError as exc:
            self._append_status(">>读取内置预设配置文件失败：%s" % exc)
            return []

        try:
            presets = self._parse_preset_config(raw_config)
        except ValueError as exc:
            self._append_status(">>内置预设配置文件内容有误：%s" % exc)
            return []

        if not presets:
            self._append_status(">>内置预设配置文件没有可用预设。")
        return presets

    def _read_packaged_preset_config(self):
        with resources.open_text(TOOL_PACKAGE_NAME, PRESET_CONFIG_FILENAME, encoding="utf-8") as preset_file:
            return json.load(preset_file)

    def _parse_preset_config(self, raw_config):
        if isinstance(raw_config, dict):
            raw_presets = raw_config.get("presets")
        else:
            raw_presets = raw_config

        if not isinstance(raw_presets, list):
            raise ValueError("顶层应为预设列表，或包含 presets 列表的对象")

        presets = []
        used_names = set()
        for index, raw_preset in enumerate(raw_presets, start=1):
            preset = self._normalize_preset(raw_preset, index)
            if preset["name"] in used_names:
                raise ValueError("预设名称重复：%s" % preset["name"])
            used_names.add(preset["name"])
            presets.append(preset)
        return presets

    def _normalize_preset(self, raw_preset, index):
        if not isinstance(raw_preset, dict):
            raise ValueError("第%d个预设不是对象" % index)

        name = str(raw_preset.get("name", "")).strip()
        if not name:
            raise ValueError("第%d个预设缺少 name" % index)

        preset = {"name": name}

        configuration_mode = raw_preset.get("configuration_mode", raw_preset.get("config_mode"))
        if configuration_mode is not None:
            configuration_mode = str(configuration_mode)
            if configuration_mode not in CONFIGURATION_MODES:
                raise ValueError("%s 的 configuration_mode 无效：%s" % (name, configuration_mode))
            preset["configuration_mode"] = configuration_mode

        vector_mode = raw_preset.get("vector_mode")
        if vector_mode is not None:
            vector_mode = str(vector_mode)
            if self.comboBox_vector.findText(vector_mode) < 0:
                raise ValueError("%s 的 vector_mode 无效：%s" % (name, vector_mode))
            preset["vector_mode"] = vector_mode

        timing_mode = raw_preset.get("timing_mode")
        if timing_mode is not None:
            timing_mode = str(timing_mode)
            if self.comboBox_mod_choose.findText(timing_mode) < 0:
                raise ValueError("%s 的 timing_mode 无效：%s" % (name, timing_mode))
            preset["timing_mode"] = timing_mode

        signals = raw_preset.get("signals")
        if signals is not None:
            preset["signals"] = self._normalize_preset_signals(signals, name)

        table = raw_preset.get("table")
        if table is not None:
            preset["table"] = self._normalize_preset_table(table, name)

        return preset

    def _normalize_preset_signals(self, signals, preset_name):
        if not isinstance(signals, dict):
            raise ValueError("%s 的 signals 应为对象" % preset_name)

        normalized = {}
        for signal_name, enabled in signals.items():
            signal_name = str(signal_name).upper()
            if signal_name not in SIGNAL_COLUMNS:
                raise ValueError("%s 的 signals 包含未知信号：%s" % (preset_name, signal_name))
            if not isinstance(enabled, bool):
                raise ValueError("%s 的 %s 信号开关应为 true/false" % (preset_name, signal_name))
            normalized[signal_name] = enabled
        return normalized

    def _normalize_preset_table(self, table, preset_name):
        if isinstance(table, dict):
            table = self._table_dict_to_rows(table)
        if not isinstance(table, list):
            raise ValueError("%s 的 table 应为数组或按行名索引的对象" % preset_name)
        if len(table) > self.tableWidget.rowCount():
            raise ValueError("%s 的 table 行数超过界面表格行数" % preset_name)

        normalized_rows = []
        for row_index, raw_row in enumerate(table):
            if not isinstance(raw_row, dict):
                raise ValueError("%s 的 table 第%d行不是对象" % (preset_name, row_index + 1))
            normalized_row = {}
            for column_name, value in raw_row.items():
                column_name = str(column_name).upper()
                if column_name == "ROW":
                    continue
                if column_name not in TABLE_COLUMNS:
                    raise ValueError("%s 的 table 包含未知列：%s" % (preset_name, column_name))
                normalized_row[column_name] = "" if value is None else str(value)
            normalized_rows.append(normalized_row)
        return normalized_rows

    def _table_dict_to_rows(self, table):
        rows = []
        for row_index in range(self.tableWidget.rowCount()):
            header = self.tableWidget.verticalHeaderItem(row_index)
            row_name = header.text() if header is not None else str(row_index)
            row_values = table.get(row_name)
            if row_values is None:
                rows.append({})
            elif isinstance(row_values, dict):
                rows.append(row_values)
            else:
                raise ValueError("%s 行应为对象" % row_name)
        return rows

    def _current_ui_preset(self, name):
        return {
            "name": name,
            "configuration_mode": self._current_configuration_mode(),
            "vector_mode": self.comboBox_vector.currentText(),
            "timing_mode": self.comboBox_mod_choose.currentText(),
            "signals": self._current_signal_states(),
            "table": self._current_table_values(),
        }

    def _current_configuration_mode(self):
        for mode_name, button in zip(CONFIGURATION_MODES, self.mode):
            if button.isChecked():
                return mode_name
        return CONFIGURATION_MODES[0]

    def _current_signal_states(self):
        return {
            signal_name: checkbox.isChecked()
            for signal_name, checkbox in zip(SIGNAL_COLUMNS, self.all_cb)
        }

    def _current_table_values(self):
        rows = []
        for row_index in range(self.tableWidget.rowCount()):
            row = {}
            for column_index, column_name in enumerate(TABLE_COLUMNS):
                item = self.tableWidget.item(row_index, column_index)
                row[column_name] = item.text() if item is not None else ""
            rows.append(row)
        return rows

    def apply_selected_preset(self, index=None):
        if not hasattr(self, "comboBox_vector_2"):
            return False

        if index is None or isinstance(index, str):
            index = self.comboBox_vector_2.currentIndex()
        if index < 0:
            return False

        preset = self.comboBox_vector_2.itemData(index)
        if not isinstance(preset, dict):
            return False

        try:
            self.apply_preset(preset)
        except ValueError as exc:
            self._append_status(">>应用预设失败：%s" % exc)
            return False
        self._append_status(">>已应用预设：%s" % preset["name"])
        return True

    def apply_preset(self, preset):
        configuration_mode = preset.get("configuration_mode")
        if configuration_mode is not None:
            self._set_configuration_mode(configuration_mode)

        vector_mode = preset.get("vector_mode")
        if vector_mode is not None:
            self._set_combo_text(self.comboBox_vector, vector_mode, "Vector Mode")

        timing_mode = preset.get("timing_mode")
        if timing_mode is not None:
            self._set_combo_text(self.comboBox_mod_choose, timing_mode, "Timing Mode")

        signals = preset.get("signals")
        if signals is not None:
            self._set_signal_states(signals)

        table = preset.get("table")
        if table is not None:
            self._set_table_values(table)

        self.compile_mode = self.comboBox_mod_choose.currentText()
        self.vector_name = self.comboBox_vector.currentText()
        self.check_box_change()

    def _set_configuration_mode(self, mode_name):
        if mode_name not in CONFIGURATION_MODES:
            raise ValueError("配置模式无效：%s" % mode_name)
        for current_mode, button in zip(CONFIGURATION_MODES, self.mode):
            button.setChecked(current_mode == mode_name)

    def _set_combo_text(self, combo_box, value, label):
        item_index = combo_box.findText(value)
        if item_index < 0:
            raise ValueError("%s 无效：%s" % (label, value))
        combo_box.setCurrentIndex(item_index)

    def _set_signal_states(self, signals):
        signal_to_checkbox = dict(zip(SIGNAL_COLUMNS, self.all_cb))
        blockers = [QtCore.QSignalBlocker(checkbox) for checkbox in signal_to_checkbox.values()]
        try:
            for signal_name, checked in signals.items():
                checkbox = signal_to_checkbox.get(signal_name)
                if checkbox is None:
                    raise ValueError("未知信号：%s" % signal_name)
                checkbox.setChecked(checked)
        finally:
            del blockers

    def _set_table_values(self, table):
        was_blocked = self.tableWidget.blockSignals(True)
        try:
            for row_index, row in enumerate(table):
                for column_name, value in row.items():
                    column_index = TABLE_COLUMNS.index(column_name)
                    item = self.tableWidget.item(row_index, column_index)
                    if item is None:
                        item = QtWidgets.QTableWidgetItem()
                        self.tableWidget.setItem(row_index, column_index, item)
                    item.setText(value)
        finally:
            self.tableWidget.blockSignals(was_blocked)

    def _append_status(self, message):
        if hasattr(self, "textBrowser_statusBar"):
            self.textBrowser_statusBar.append(message)

    def default_button(self):
        self.radioButton_x32.setChecked(True)
        self.radioButton_multiRbt.setChecked(True)
        for item in self.default_list:
            item.setChecked(True)
        for item in self.undefault_list:
            item.setChecked(False)
        return True

    def open_file_button(self):
        status_bar = self.textBrowser_statusBar
        path = self.lineEdit_openFile
        state1 = self.radioButton_singleRbt.isChecked()
        state2 = self.radioButton_multiRbt.isChecked()
        if not (state1 or state2):
            QtWidgets.QMessageBox.critical(self, "Error", "请在“单个rbt转换”、“批量rbt转换”中选择一项!")
            status_bar.append(">>请在“单个rbt转换”、“批量rbt转换”中选择一项!")
            return False
        if state1:
            n, _ = QtWidgets.QFileDialog.getOpenFileName(self, "选择文件", ".", "RBT Files(*.rbt)")
            path.setText(n)
            status_bar.append(">>已选择文件%s" % n)
        else:
            m = QtWidgets.QFileDialog.getExistingDirectory(self, "选取文件夹")  # 起始路径
            path.setText(m)
            status_bar.append(">>已选择文件夹：%s" % m)
        return True

    def mode_value_change(self):
        status_bar = self.textBrowser_statusBar
        value = self.tableWidget.item(0, 7).text()
        try:
            int(value)
        except:
            QtWidgets.QMessageBox.critical(self, "Error", "请在MODE栏输入数字!")
            status_bar.append(">>请在MODE栏输入数字!")
            return False
        self.tableWidget.cellChanged.disconnect()
        row_num = self.tableWidget.rowCount()
        for row_mode in range(1, row_num):
            self.tableWidget.item(row_mode, 7).setText(value)
        self.tableWidget.cellChanged.connect(self.mode_value_change)
        return True

    def check_box_change(self):
        row_num = self.tableWidget.rowCount()
        # 第一列REPEAT始终被选中
        for r in range(row_num):
            brush = QtGui.QBrush(REPEAT_COLUMN_COLOR)
            self.tableWidget.item(r, 0).setBackground(brush)
        # 其余列根据复选框状态设置底色
        cb_state = []
        for item in self.all_cb:
            cb_state.append(item.isChecked())  # 被选中为True，不被选中为False
        for i in range(self.num_cb):
            if cb_state[i]:
                for r in range(row_num):
                    brush = QtGui.QBrush(SELECTED_COLUMN_COLOR)
                    self.tableWidget.item(r, i + 1).setBackground(brush)
            else:
                for r in range(row_num):
                    brush = QtGui.QBrush(UNSELECTED_COLUMN_COLOR)
                    self.tableWidget.item(r, i + 1).setBackground(brush)
        return True

    def exchange(self):
        t1 = time.time()
        status_bar = self.textBrowser_statusBar
        path = self.lineEdit_openFile.text()
        self.compile_mode = self.comboBox_mod_choose.currentText()
        self.vector_name = self.comboBox_vector.currentText()
        mode = 0
        for i in range(self.num_mode):
            if self.mode[i].isChecked():
                mode = i
        is_single_rbt = self.radioButton_singleRbt.isChecked()
        if not path:
            QtWidgets.QMessageBox.critical(self, "Error", "请先打开一个文件或文件夹!")
            status_bar.append(">>请先打开一个文件或文件夹!")
            return False

        if is_single_rbt:
            save_path = os.path.dirname(path) + "/生成atp文件"
            if not os.path.exists(save_path):
                os.mkdir(save_path)
            file = path
            self.pBar.setValue(2)
            try:
                result = self.gen_single_atp(file, mode, save_path)
                if not result:
                    self.pBar.setValue(0)
                    return False

                if result:
                    self.pBar.setValue(50)
                    t2 = time.time()
                    t = t2 - t1
                    QtWidgets.QApplication.processEvents()
                    status_bar.append(">>ATP文件已转换完毕!")
                    QtWidgets.QApplication.processEvents()
                    status_bar.append(">>用时%.1f s" % t)
                    QtWidgets.QApplication.processEvents()
                    self.pBar.setValue(100)
                    QtWidgets.QMessageBox.information(self, "Info", "ATP文件已转换完毕！")
            except:
                self.pBar.setValue(0)
                QtWidgets.QMessageBox.critical(self, "Error", "%s文件有误，请检查!" % file)
                status_bar.append(">>%s文件有误，请检查!" % file)
                return False
        else:
            save_path = path + "/生成atp文件"
            if not os.path.exists(save_path):
                try:
                    os.mkdir(save_path)
                except:
                    QtWidgets.QMessageBox.critical(self, "Error", "%s文件夹有误，请检查!" % path)
                    status_bar.append(">>%s文件夹有误，请检查!" % path)
                    return False
            file_names_all = os.listdir(path)
            file_names = []
            for file in file_names_all:
                if file.endswith(".rbt"):
                    file_names.append(file)
            file_num = len(file_names)
            self.pBar.setValue(2)
            for i in range(file_num):
                file = path + "/" + file_names[i]
                try:
                    result = self.gen_single_atp(file, mode, save_path)
                    if not result:
                        return False
                    divisor = ceil(file_num / 5) if ceil(file_num / 5) > 0 else 1
                    if (i + 1) % divisor == 0:
                        x = (i + 1) / divisor
                        QtWidgets.QApplication.processEvents()
                        # status_bar.append(">>已生成%d%s的ATP文件" % (x * 20, '%'))
                        QtWidgets.QApplication.processEvents()
                        self.pBar.setValue(2 + int(x * 20 * 0.95))
                except:
                    self.pBar.setValue(0)
                    QtWidgets.QMessageBox.critical(self, "Error", "%s文件有误，请检查!" % file)
                    status_bar.append(">>%s文件有误，请检查!" % file)
                    return False
            if self.pBar.value() != 0:
                self.pBar.setValue(100)
                t2 = time.time()
                t = t2 - t1
                QtWidgets.QApplication.processEvents()
                status_bar.append(">>ATP文件已转换完毕!")
                QtWidgets.QApplication.processEvents()
                status_bar.append(">>用时%.1f s" % t)
                QtWidgets.QApplication.processEvents()
                QtWidgets.QMessageBox.information(self, "Info", "ATP文件已转换完毕！")

    def gen_single_atp(self, file, mode, save_path):
        status_bar = self.textBrowser_statusBar
        # region 获取表格中REPEAT列以及选中变量列的值到data
        QtWidgets.QApplication.processEvents()
        status_bar.append(">>正在转换RBT文件：%s" % file)
        QtWidgets.QApplication.processEvents()
        row_num = self.tableWidget.rowCount()
        checked_column = [0]  # 被选中的列号，REPEAT必选
        cb_state = []
        variables = ""
        for i in range(self.num_cb):
            state = self.all_cb[i].isChecked()
            cb_state.append(state)  # 被选中为True，不被选中为False
            if state:
                checked_column.append(i + 1)  # 实际表格的列号要比checkbox的列号大1
                variables = variables + self.variables[i] + ", "  # 将被选中的项生成variable字符串
        cfg_data = []
        for i in range(row_num):
            cfg_data.append([])
            for j in checked_column:
                value = self.tableWidget.item(i, j).text()
                cfg_data[i].append(value)
        # for d in cfg_data:
        #     print(d)
        # endregion

        # region 头字符串，从“opcode_mode=extended;” 到“start_label”
        atp_data = ["\n", "opcode_mode={compile_mode};\n".format(compile_mode=self.compile_mode), "import tset WFT;\n"]
        temp_string = "{vector_name} ( $tset, ".format(vector_name=self.vector_name) + variables + "CFG_Data" + " )\n"
        atp_data.append(temp_string)
        atp_data.append('{\n')
        # for item in atp_data:
        #     print(item)
        file_name = file.split("/")[-1]
        file_name = file_name.split(".")[0]
        atp_data.append("start_label " + file_name + ":\n")
        QtWidgets.QApplication.processEvents()
        status_bar.append(">>已生成头字符串...")
        QtWidgets.QApplication.processEvents()
        # endregion

        # region 字符串 初始+复位+等待
        str_wft = "                        > WFT       "
        str_data_full0_mode = ["00000000000000000000000000000000 ;\n",
                               "0000000000000000 ;\n",
                               "00000000 ;\n",
                               "0 ;\n"]
        str_data_full0 = str_data_full0_mode[mode]
        # 初始1：
        temp_cfg_data = cfg_data[0]
        str_cfg = ""
        for item in temp_cfg_data[1:]:
            str_cfg = str_cfg + item + " "
        str1 = str_wft + str_cfg + str_data_full0
        for _ in range(4):
            atp_data.append(str1)
        # 初始2 & 复位1：
        for r in range(1, 3):
            temp_cfg_data = cfg_data[r]
            str_cfg = ""
            for item in temp_cfg_data[1:]:
                str_cfg = str_cfg + item + " "
            str1 = str_wft + str_cfg + str_data_full0
            for _ in range(3):
                atp_data.append(str1)
            repeat = temp_cfg_data[0]
            while len(repeat) < 5:
                repeat = " " + repeat
            str1 = "repeat" + " " * 11 + repeat + "  > WFT       " + str_cfg + str_data_full0
            atp_data.append(str1)
        # 复位2：
        temp_cfg_data = cfg_data[3]
        str_cfg = ""
        for item in temp_cfg_data[1:]:
            str_cfg = str_cfg + item + " "
        str1 = str_wft + str_cfg + str_data_full0
        for _ in range(4):
            atp_data.append(str1)
        # 等待1 & 等待2 & 等待3：
        for r in range(4, 7):
            temp_cfg_data = cfg_data[r]
            str_cfg = ""
            for item in temp_cfg_data[1:]:
                str_cfg = str_cfg + item + " "
            str1 = str_wft + str_cfg + str_data_full0
            for _ in range(3):
                atp_data.append(str1)
            repeat = temp_cfg_data[0]
            try:
                int(repeat)
            except:
                QtWidgets.QMessageBox.critical(self, "Error", "请在repeat栏中输入数字!")
                QtWidgets.QApplication.processEvents()
                status_bar.append(">>请在repeat栏中输入数字!")
                QtWidgets.QApplication.processEvents()
                self.pBar.setValue(0)
                return False
            if int(repeat) > self.max_count:
                QtWidgets.QMessageBox.critical(self, "Error", "repeat的值不能大于60000！请重新输入！")
                QtWidgets.QApplication.processEvents()
                status_bar.append(">>repeat的值不能大于60000！请重新输入！")
                QtWidgets.QApplication.processEvents()
                self.pBar.setValue(0)
                return False
            while len(repeat) < 5:
                repeat = " " + repeat
            str1 = "repeat" + " " * 11 + repeat + "  > WFT       " + str_cfg + str_data_full0
            atp_data.append(str1)
        QtWidgets.QApplication.processEvents()
        status_bar.append(">>已生成初始+复位+等待字符串...")
        QtWidgets.QApplication.processEvents()
        # endregion

        # region 字符串 配置
        rbt_data = self.rbt_process(file, mode)
        length = len(rbt_data)
        if length == 0:
            return False
        repeat_scale = self.mode_map.get(self.compile_mode, 4)
        block_num = int(length / repeat_scale)
        block = 0
        while block < block_num:
            repeat_count = 1
            while rbt_data[block * repeat_scale:(block + 1) * repeat_scale] == rbt_data[(block + 1) * repeat_scale:(block + 2) * repeat_scale] \
                    and repeat_count < self.max_count:
                repeat_count += 1
                block += 1
            if repeat_count == 1:
                # print(repeat_count, block + 1)
                temp_cfg_data = cfg_data[7]
                str_cfg = ""
                for item in temp_cfg_data[1:]:
                    str_cfg = str_cfg + item + " "
                for k in range(repeat_scale):
                    str1 = str_wft + str_cfg + rbt_data[block * repeat_scale + k]
                    atp_data.append(str1)
                block += 1
            else:
                # print(repeat_count, block + 1)
                temp_cfg_data = cfg_data[7]
                str_cfg = ""
                for item in temp_cfg_data[1:]:
                    str_cfg = str_cfg + item + " "
                for k in range(repeat_scale-1):
                    str1 = str_wft + str_cfg + rbt_data[block * repeat_scale + k]
                    atp_data.append(str1)
                repeat = str(repeat_count)
                while len(repeat) < 5:
                    repeat = " " + repeat
                str1 = "repeat" + " " * 11 + repeat + "  > WFT       " + str_cfg + rbt_data[block * repeat_scale + repeat_scale-1]
                atp_data.append(str1)
                block += 1
        QtWidgets.QApplication.processEvents()
        status_bar.append(">>已生成配置字符串...")
        QtWidgets.QApplication.processEvents()
        # endregion

        # region 字符串 结束
        str_halt = "halt                    > WFT       "
        temp_cfg_data = cfg_data[-1]
        str_cfg = ""
        for item in temp_cfg_data[1:]:
            str_cfg = str_cfg + item + " "
        str1 = str_wft + str_cfg + str_data_full0
        for _ in range(3):
            atp_data.append(str1)
        repeat = temp_cfg_data[0]
        while len(repeat) < 5:
            repeat = " " + repeat
        str2 = "repeat" + " " * 11 + repeat + "  > WFT       " + str_cfg + str_data_full0
        atp_data.append(str2)
        for _ in range(3):
            atp_data.append(str1)
        str3 = str_halt + str_cfg + str_data_full0
        atp_data.append(str3)
        atp_data.append("}\n")
        QtWidgets.QApplication.processEvents()
        status_bar.append(">>已生成结尾字符串...")
        QtWidgets.QApplication.processEvents()
        # endregion

        # region 生成ATP文件
        atp_file_name = save_path + "/" + file_name + ".atp"
        atp_file = open(atp_file_name, "w")
        atp_file.writelines(atp_data)
        atp_file.close()
        QtWidgets.QApplication.processEvents()
        status_bar.append(">>已生成ATP文件：%s" % atp_file_name)
        QtWidgets.QApplication.processEvents()
        # endregion

        return True

    def rbt_process(self, file, mode):
        status_bar = self.textBrowser_statusBar
        try:
            rbt_data = open(file).readlines()
        except:
            QtWidgets.QMessageBox.critical(self, "Error", "%s文件有误，请检查!" % file)
            status_bar.append(">>%s文件有误，请检查!" % file)
            return []
        rbt_data = rbt_data[7:]
        length = len(rbt_data)
        while length % 4 != 0:
            rbt_data.append("00100000000000000000000000000000\n")
            length = len(rbt_data)
        new_data = []
        if mode == 0:
            for i in range(length):
                new_data.append(rbt_data[i][:32] + " ;\n")
        elif mode == 1:  # 16位
            for i in range(length):
                new_data.append(rbt_data[i][:16] + " ;\n")
                new_data.append(rbt_data[i][16:32] + " ;\n")
        elif mode == 2:
            for i in range(length):
                new_data.append(rbt_data[i][:8] + " ;\n")
                new_data.append(rbt_data[i][8:16] + " ;\n")
                new_data.append(rbt_data[i][16:24] + " ;\n")
                new_data.append(rbt_data[i][24:32] + " ;\n")
        elif mode == 3:
            for i in range(length):
                for j in range(32):
                    new_data.append(rbt_data[i][j] + " ;\n")
        return new_data


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    rbt2atp = RBT2ATP()
    rbt2atp.show()
    sys.exit(app.exec_())
