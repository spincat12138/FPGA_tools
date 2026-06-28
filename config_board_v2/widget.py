# -*- coding: utf-8 -*-
from __future__ import annotations

import traceback
import sys
from pathlib import Path
from typing import Callable, Iterable, Optional

from PyQt5 import QtCore, QtGui, QtWidgets

try:
    from . import usbtest_py as core
except ImportError:  # pragma: no cover - supports direct script execution.
    import usbtest_py as core


TOOL_ID = "config_board_v2"
TOOL_NAME = "配置板烧写程序-V2"
COMPARE_OUTPUT_NAME = "compare.txt"
CONFIG_FILTERS = (
    "bit/rbt/b files (*.bit *.rbt *.b);;"
    "bit_file (*.bit);;"
    "rbt_file (*.rbt);;"
    "All File (*)"
)
VERIFY_FILTERS = (
    "bit/b/rbt/txt files (*.bit *.b *.rbt *.txt);;"
    "bit_file (*.bit);;"
    "b_file (*.b);;"
    "rbt_file (*.rbt);;"
    "txt_file (*.txt);;"
    "All File (*)"
)
CONVERT_FILTERS = (
    "rbt/txt files (*.rbt *.txt);;"
    "rbt_file (*.rbt);;"
    "txt_file (*.txt);;"
    "All File (*)"
)


class OperationWorker(QtCore.QObject):
    status = QtCore.pyqtSignal(str, str)
    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str, str)

    def __init__(self, work: Callable[[Callable[[str, str], None]], object]):
        super().__init__()
        self._work = work

    @QtCore.pyqtSlot()
    def run(self):
        try:
            result = self._work(self.status.emit)
        except Exception as exc:
            self.failed.emit(str(exc), traceback.format_exc())
            return
        self.finished.emit(result)


class ConfigBoardWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, services=None):
        super().__init__(parent)
        self.services = services
        self.ftdi: Optional[core.FtdiDevice] = None
        self.profile: Optional[core.DeviceProfile] = None
        self.output_dir = self._resolve_output_dir()
        self._thread: Optional[QtCore.QThread] = None
        self._worker: Optional[OperationWorker] = None
        self._open_device_allowed = True

        self.setObjectName("configBoardWidget")
        self.setProperty("preferred_size", QtCore.QSize(760, 500))
        self._build_ui()
        self.apply_visual_style()
        self._refresh_initial_usb_status()
        self._refresh_action_states(running=False)

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(24, 22, 24, 18)
        main_layout.setSpacing(14)

        title = QtWidgets.QLabel(TOOL_NAME)
        title.setObjectName("title")

        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(8)
        device_label = QtWidgets.QLabel("器件选型")
        self.device_combo = QtWidgets.QComboBox()
        self.device_combo.addItems(list(core.DEVICE_BY_NAME.keys()))
        self.device_combo.setCurrentText("BQ2V1000")
        erase_label = QtWidgets.QLabel("擦除地址")
        self.erase_address_edit = QtWidgets.QLineEdit()
        self.erase_address_edit.setPlaceholderText("例如 1")
        self.erase_button = QtWidgets.QPushButton("擦除")
        self.convert_button = QtWidgets.QPushButton("码流转换工具")
        self.erase_button.clicked.connect(self.erase_address)
        self.convert_button.clicked.connect(self.convert_streams)
        top_row.addWidget(device_label)
        top_row.addWidget(self.device_combo)
        top_row.addSpacing(16)
        top_row.addWidget(erase_label)
        top_row.addWidget(self.erase_address_edit)
        top_row.addWidget(self.erase_button)

        usb_row = QtWidgets.QHBoxLayout()
        usb_row.setSpacing(8)
        usb_label = QtWidgets.QLabel("USB设备状态")
        self.usb_status_edit = QtWidgets.QLineEdit("USB设备已拔出!")
        self.usb_status_edit.setReadOnly(True)
        self.open_button = QtWidgets.QPushButton("打开设备")
        self.close_button = QtWidgets.QPushButton("关闭设备")
        self.alarm_indicator = QtWidgets.QFrame()
        self.alarm_indicator.setObjectName("alarmIndicator")
        self.alarm_indicator.setFixedSize(28, 28)
        self.open_button.clicked.connect(self.open_device)
        self.close_button.clicked.connect(self.close_device)
        usb_row.addWidget(usb_label)
        usb_row.addWidget(self.usb_status_edit, 1)
        usb_row.addWidget(self.open_button)
        usb_row.addWidget(self.close_button)
        usb_row.addWidget(self.alarm_indicator)
        usb_row.addWidget(self.convert_button)
        usb_row.addStretch(1)

        work_layout = QtWidgets.QHBoxLayout()
        work_layout.setSpacing(18)

        config_group = QtWidgets.QGroupBox("配置")
        config_group.setObjectName("configGroup")
        config_layout = QtWidgets.QVBoxLayout(config_group)
        config_layout.setContentsMargins(12, 18, 12, 12)
        config_layout.setSpacing(10)
        config_button_row = QtWidgets.QHBoxLayout()
        self.config_button = QtWidgets.QPushButton("配置")
        self.config_button.clicked.connect(self.configure_files)
        config_button_row.addStretch(1)
        config_button_row.addWidget(self.config_button)
        self.config_text = QtWidgets.QPlainTextEdit()
        self.config_text.setReadOnly(True)
        self.config_text.setPlaceholderText("已选择的配置码流文件会显示在这里")
        config_layout.addLayout(config_button_row)
        config_layout.addWidget(self.config_text, 1)

        read_group = QtWidgets.QGroupBox("回读")
        read_group.setObjectName("readGroup")
        read_layout = QtWidgets.QVBoxLayout(read_group)
        read_layout.setContentsMargins(12, 18, 12, 12)
        read_layout.setSpacing(10)
        read_address_row = QtWidgets.QHBoxLayout()
        read_address_label = QtWidgets.QLabel("地址选择")
        self.read_address_edit = QtWidgets.QLineEdit()
        self.read_address_edit.setPlaceholderText("例如 1")
        read_address_row.addWidget(read_address_label)
        read_address_row.addWidget(self.read_address_edit, 1)
        self.verify_after_read_checkbox = QtWidgets.QCheckBox("与配置码流验证")
        self.verify_after_read_checkbox.setChecked(True)
        self.readback_button = QtWidgets.QPushButton("ReadBack")
        self.verify_button = QtWidgets.QPushButton("回读验证")
        self.open_compare_button = QtWidgets.QPushButton("打开验证结果")
        self.open_compare_button.setEnabled(self._compare_output_path().exists())
        self.readback_button.clicked.connect(self.readback_to_file)
        self.verify_button.clicked.connect(self.verify_files)
        self.open_compare_button.clicked.connect(self.open_compare_result)
        read_layout.addLayout(read_address_row)
        read_layout.addWidget(self.verify_after_read_checkbox)
        read_layout.addWidget(self.readback_button)
        read_layout.addWidget(self.verify_button)
        read_layout.addWidget(self.open_compare_button)
        read_layout.addStretch(1)

        work_layout.addWidget(config_group, 2)
        work_layout.addWidget(read_group, 1)

        status_row = QtWidgets.QHBoxLayout()
        status_row.setSpacing(8)
        self.status1_label = QtWidgets.QLabel("状态栏")
        self.status1_label.setObjectName("statusText")
        self.status2_label = QtWidgets.QLabel("")
        self.status2_label.setObjectName("statusText")
        self.clear_status_button = QtWidgets.QPushButton("清空状态")
        self.clear_status_button.clicked.connect(lambda: self.set_status("状态栏", ""))
        status_row.addWidget(self.status1_label, 1)
        status_row.addWidget(self.status2_label, 2)
        status_row.addWidget(self.clear_status_button)

        main_layout.addWidget(title)
        main_layout.addLayout(top_row)
        main_layout.addLayout(usb_row)
        main_layout.addLayout(work_layout, 1)
        main_layout.addLayout(status_row)

    def apply_visual_style(self):
        self.setStyleSheet("""
            QWidget#configBoardWidget {
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

            QLineEdit,
            QPlainTextEdit,
            QComboBox {
            background-color: #ffffff;
            border: 1px solid #dcdfe6;
            border-radius: 4px;
            color: #303133;
            padding: 5px;
            }

            QLineEdit:focus,
            QPlainTextEdit:focus,
            QComboBox:focus {
            border-color: #409eff;
            }

            QLineEdit:read-only {
            color: #606266;
            background-color: #ffffff;
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

            QGroupBox {
            border: 1px solid #dcdfe6;
            border-radius: 4px;
            color: #2c3e50;
            font-weight: bold;
            margin-top: 10px;
            background-color: transparent;
            }

            QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
            }

            QCheckBox {
            color: #2c3e50;
            spacing: 6px;
            }

            QFrame#alarmIndicator {
            background-color: #909399;
            border: 1px solid #dcdfe6;
            border-radius: 4px;
            }

            QLabel#statusText {
            background-color: #ffffff;
            border: 1px solid #dcdfe6;
            border-radius: 4px;
            color: #606266;
            min-height: 24px;
            padding: 3px 6px;
            }
        """)

    def _refresh_initial_usb_status(self):
        try:
            ftd2xx = core.import_ftd2xx()
            count = ftd2xx.createDeviceInfoList()
        except Exception as exc:
            self.usb_status_edit.setText("FTDI环境异常")
            self.set_status(str(exc), "")
            self._open_device_allowed = False
            self._refresh_action_states(running=False)
            return

        self._open_device_allowed = True
        self.usb_status_edit.setText("USB设备已插入!" if count else "USB设备已拔出!")
        self._refresh_action_states(running=False)

    def set_status(self, status1: str = "", status2: str = ""):
        self.status1_label.setText(status1)
        self.status2_label.setText(status2)
        if self.services is not None and (status1 or status2):
            self.services.log(TOOL_ID, " ".join(part for part in (status1, status2) if part))

    def set_usb_open_state(self, opened: bool):
        if opened:
            self.usb_status_edit.setText("USB设备已打开!")
            self.alarm_indicator.setStyleSheet("background-color: #67c23a;")
            self._refresh_action_states(running=False)
            return

        self.usb_status_edit.setText("USB设备已关闭")
        self.alarm_indicator.setStyleSheet("")
        self._refresh_action_states(running=False)

    def set_failure_state(self, message: str):
        self.usb_status_edit.setText("USB连接失败")
        self.alarm_indicator.setStyleSheet("background-color: #f56c6c;")
        self._refresh_action_states(running=False)
        self.set_status(message, "")

    def open_device(self):
        self._close_current_device()

        def work(status):
            ftdi = core.FtdiDevice(index=0)
            try:
                status("", "正在打开设备...")
                ftdi.open()
                profile = core.handshake(ftdi)
            except Exception:
                ftdi.close()
                raise
            return {"ftdi": ftdi, "profile": profile}

        self._run_background("打开设备", work, self._on_device_opened)

    def _on_device_opened(self, result):
        self.ftdi = result["ftdi"]
        self.profile = result["profile"]
        self.device_combo.setCurrentText(self.profile.name)
        self.set_usb_open_state(True)
        self.set_status("", "握手成功，设备型号：{name}，码流长度：{length}".format(
            name=self.profile.name,
            length=self.profile.bit_length,
        ))

    def _resolve_output_dir(self) -> Path:
        path = self._program_dir()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _program_dir(self) -> Path:
        if getattr(sys, "frozen", False) or getattr(sys.modules.get("__main__"), "__compiled__", None):
            return Path(sys.argv[0]).resolve().parent

        entry = Path(sys.argv[0]).resolve()
        if entry.exists():
            return entry.parent
        return Path.cwd()

    def _compare_output_path(self) -> Path:
        return self.output_dir / COMPARE_OUTPUT_NAME

    def close_device(self):
        self._close_current_device()
        self.set_usb_open_state(False)
        self.set_status("", "USB设备已关闭")

    def _close_current_device(self):
        if self.ftdi is not None:
            self.ftdi.close()
        self.ftdi = None
        self.profile = None

    def _require_ftdi(self):
        if self.ftdi is None:
            raise core.UsbTestError("设备未打开。")
        return self.ftdi

    def _selected_profile(self):
        if self.profile is not None:
            return self.profile
        return core.DEVICE_BY_NAME[self.device_combo.currentText()]

    def erase_address(self):
        address = self.erase_address_edit.text().strip()
        if not address:
            self._show_error("输入不完整", "请输入擦除地址。")
            return
        try:
            ftdi = self._require_ftdi()
        except Exception as exc:
            self._show_error("设备未打开", str(exc))
            return

        def work(_status):
            core.erase(ftdi, address)

        self._run_background("擦除", work)

    def configure_files(self):
        file_names = self._select_files("选择一个或多个文件", CONFIG_FILTERS)
        if not file_names:
            return
        self.config_text.setPlainText("\n".join(file_names))
        try:
            ftdi = self._require_ftdi()
            profile = self._selected_profile()
        except Exception as exc:
            self._show_error("设备未打开", str(exc))
            return

        def work(status):
            for index, file_name in enumerate(file_names, start=1):
                status("", "当前正在执行第{index}个文件的写入".format(index=index))
                core.program_file(ftdi, file_name, profile, output_dir=self.output_dir)
            status("", "配置程序结束")

        self._run_background("配置", work)

    def readback_to_file(self):
        address = self.read_address_edit.text().strip()
        if not address:
            self._show_error("输入不完整", "请输入回读地址。")
            return
        try:
            output_path = self._readback_output_path(address)
        except ValueError:
            self._show_error("输入不合法", "回读地址必须是数字。")
            return
        try:
            ftdi = self._require_ftdi()
            profile = self._selected_profile()
        except Exception as exc:
            self._show_error("设备未打开", str(exc))
            return
        verify_after_read = self.verify_after_read_checkbox.isChecked()

        def work(status):
            data = core.readback(ftdi, address, profile)
            output_path.write_bytes(data)
            if verify_after_read:
                status("", "ReadBack完成，已写入 {path}；请点击“回读验证”选择码流文件校验".format(
                    path=output_path,
                ))
            else:
                status("", "ReadBack完成，已写入 {path}".format(path=output_path))

        self._run_background("ReadBack", work)

    def _readback_output_path(self, address: str) -> Path:
        normalized_address = str(int(address))
        return self.output_dir / "{address}_readback.bit".format(address=normalized_address)

    def verify_files(self):
        file_names = self._select_files("选择一个或多个文件", VERIFY_FILTERS)
        if not file_names:
            return
        try:
            ftdi = self._require_ftdi()
            profile = self._selected_profile()
        except Exception as exc:
            self._show_error("设备未打开", str(exc))
            return

        def work(status):
            status("", "正在验证......")
            output_path = self._compare_output_path()
            core.verify_files(ftdi, file_names, profile, output_path, output_dir=self.output_dir)
            status("", "验证完成，结果已写入 {path}".format(path=output_path))

        self._run_background("回读验证", work, self._on_verify_finished)

    def _on_verify_finished(self, _result):
        self.open_compare_button.setEnabled(self._compare_output_path().exists())
        self.set_status("", "回读验证完成")

    def open_compare_result(self):
        output_path = self._compare_output_path()
        if not output_path.exists():
            self._show_error("文件不存在", "未找到回读验证结果：{path}".format(path=output_path))
            self.open_compare_button.setEnabled(False)
            return
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(output_path)))

    def convert_streams(self):
        file_names = self._select_files("选择 rbt/txt 文件", CONVERT_FILTERS)
        if not file_names:
            return

        def work(_status):
            core.convert_files(file_names, output_dir=self.output_dir)

        self._run_background("码流转换", work)

    def _select_files(self, title: str, filters: str) -> list[str]:
        file_names, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            title,
            str(Path.cwd()),
            filters,
        )
        return list(file_names)

    def _run_background(self, title: str, work, on_success=None):
        if self._thread is not None:
            self._show_info("提示", "当前已有操作正在执行。")
            return

        self.set_status("", title + "...")
        self._set_running(True)
        self._thread = QtCore.QThread(self)
        self._worker = OperationWorker(work)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.status.connect(self.set_status)
        self._worker.finished.connect(lambda result: self._on_operation_finished(title, result, on_success))
        self._worker.failed.connect(lambda message, detail: self._on_operation_failed(title, message, detail))
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_worker_refs)
        self._thread.start()

    def _on_operation_finished(self, title: str, result, on_success):
        self._set_running(False)
        if on_success is not None:
            on_success(result)
        else:
            self.set_status("", title + "完成")

    def _on_operation_failed(self, title: str, message: str, detail: str):
        self._set_running(False)
        self.set_failure_state("{title}失败：{message}".format(title=title, message=message))
        self._show_error(title + "失败", message, detail=detail)

    def _set_running(self, running: bool):
        controls: Iterable[QtWidgets.QWidget] = (
            self.device_combo,
            self.erase_address_edit,
            self.convert_button,
            self.open_button,
            self.close_button,
            self.erase_button,
            self.config_button,
            self.read_address_edit,
            self.verify_after_read_checkbox,
            self.readback_button,
            self.verify_button,
            self.open_compare_button,
            self.clear_status_button,
        )
        for control in controls:
            control.setEnabled(not running)
        self._refresh_action_states(running=running)
        if self.services is not None:
            self.services.set_busy(TOOL_ID, running, "正在执行config_board_v2" if running else None)

    def _refresh_action_states(self, running: bool):
        connected = self.ftdi is not None
        self.open_button.setEnabled((not running) and (not connected) and self._open_device_allowed)
        self.close_button.setEnabled((not running) and connected)
        self.erase_button.setEnabled((not running) and connected)
        self.readback_button.setEnabled((not running) and connected)
        self.verify_button.setEnabled((not running) and connected)
        self.open_compare_button.setEnabled(
            (not running) and self._compare_output_path().exists()
        )

    def _clear_worker_refs(self):
        self._thread = None
        self._worker = None

    def _show_info(self, title: str, message: str):
        if self.services is not None:
            self.services.show_info(title, message, parent=self)
        else:
            QtWidgets.QMessageBox.information(self, title, message)

    def _show_error(self, title: str, message: str, detail=None):
        if self.services is not None:
            self.services.show_error(title, message, detail=detail, parent=self)
        else:
            dialog = QtWidgets.QMessageBox(self)
            dialog.setIcon(QtWidgets.QMessageBox.Critical)
            dialog.setWindowTitle(title)
            dialog.setText(message)
            if detail:
                dialog.setDetailedText(str(detail))
            dialog.exec_()

    def closeEvent(self, event):
        self._close_current_device()
        super().closeEvent(event)


def create_standalone_widget():
    widget = ConfigBoardWidget()
    widget.setWindowTitle("USB测试")
    widget.resize(760, 500)
    icon_path = Path(__file__).resolve().parent.parent / "RBT2ATP" / "logo.ico"
    if icon_path.exists():
        widget.setWindowIcon(QtGui.QIcon(str(icon_path)))
    return widget
