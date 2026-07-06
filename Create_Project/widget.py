# -*- coding: utf-8 -*-
import traceback
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from .create_project import (
    DEFAULT_DEVICE,
    DEFAULT_VIVADO_PATH,
    build_vivado_project,
    create_project_structure,
)


TOOL_ID = "create_project"
TOOL_NAME = "创建Vivado工程"


class CreateProjectWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str, str)

    def __init__(self, mode, root_dir, project_name, device, vivado_path):
        super().__init__()
        self.mode = mode
        self.root_dir = root_dir
        self.project_name = project_name
        self.device = device
        self.vivado_path = vivado_path

    @QtCore.pyqtSlot()
    def run(self):
        try:
            if self.mode == "mkdir":
                project_dir, created_dirs = create_project_structure(
                    self.root_dir,
                    self.project_name,
                )
                result = {
                    "mode": self.mode,
                    "project_dir": project_dir,
                    "created_dirs": created_dirs,
                }
            else:
                project_dir, tcl_file, vivado_output, warnings = build_vivado_project(
                    self.root_dir,
                    self.project_name,
                    device=self.device,
                    vivado_path=self.vivado_path,
                )
                result = {
                    "mode": self.mode,
                    "project_dir": project_dir,
                    "tcl_file": tcl_file,
                    "vivado_output": vivado_output,
                    "warnings": warnings,
                }
        except Exception as exc:
            self.failed.emit(str(exc), traceback.format_exc())
            return

        self.finished.emit(result)


class CreateProjectWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, services=None):
        super().__init__(parent)
        self.services = services
        self._thread = None
        self._worker = None
        self._last_project_dir = None
        self.setObjectName("createProjectWidget")
        self.setProperty("preferred_size", QtCore.QSize(760, 460))
        self._build_ui()
        self.apply_visual_style()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(24, 22, 24, 18)
        main_layout.setSpacing(14)

        title = QtWidgets.QLabel(TOOL_NAME)
        title.setObjectName("title")

        root_row = QtWidgets.QHBoxLayout()
        root_row.setSpacing(8)
        root_label = QtWidgets.QLabel("根目录")
        self.root_edit = QtWidgets.QLineEdit()
        self.root_edit.setPlaceholderText("选择或输入工程根目录")
        self.browse_button = QtWidgets.QPushButton("浏览...")
        self.browse_button.clicked.connect(self._browse_root_dir)
        root_row.addWidget(root_label)
        root_row.addWidget(self.root_edit, 1)
        root_row.addWidget(self.browse_button)

        info_row = QtWidgets.QHBoxLayout()
        info_row.setSpacing(8)
        project_label = QtWidgets.QLabel("project_name")
        self.project_name_edit = QtWidgets.QLineEdit()
        self.project_name_edit.setPlaceholderText("例如 my_project")
        device_label = QtWidgets.QLabel("device")
        self.device_edit = QtWidgets.QLineEdit(DEFAULT_DEVICE)
        info_row.addWidget(project_label)
        info_row.addWidget(self.project_name_edit, 1)
        info_row.addWidget(device_label)
        info_row.addWidget(self.device_edit, 1)

        vivado_row = QtWidgets.QHBoxLayout()
        vivado_row.setSpacing(8)
        vivado_label = QtWidgets.QLabel("Vivado路径")
        self.vivado_path_edit = QtWidgets.QLineEdit(DEFAULT_VIVADO_PATH)
        self.vivado_path_edit.setPlaceholderText("选择或输入 vivado.bat 路径")
        self.vivado_browse_button = QtWidgets.QPushButton("浏览...")
        self.vivado_browse_button.clicked.connect(self._browse_vivado_path)
        vivado_row.addWidget(vivado_label)
        vivado_row.addWidget(self.vivado_path_edit, 1)
        vivado_row.addWidget(self.vivado_browse_button)

        button_row = QtWidgets.QHBoxLayout()
        button_row.setSpacing(8)
        self.mkdir_button = QtWidgets.QPushButton("创建目录结构")
        self.project_button = QtWidgets.QPushButton("构建工程")
        self.open_project_button = QtWidgets.QPushButton("打开工程目录")
        self.clear_log_button = QtWidgets.QPushButton("清空日志")
        self.open_project_button.setEnabled(False)
        self.mkdir_button.clicked.connect(lambda: self._start("mkdir"))
        self.project_button.clicked.connect(lambda: self._start("project"))
        self.open_project_button.clicked.connect(self._open_project_directory)
        button_row.addWidget(self.mkdir_button)
        button_row.addWidget(self.project_button)
        button_row.addWidget(self.open_project_button)
        button_row.addWidget(self.clear_log_button)
        button_row.addStretch(1)

        self.log_view = QtWidgets.QTextBrowser()
        self.log_view.setOpenExternalLinks(False)
        self.clear_log_button.clicked.connect(self.log_view.clear)

        main_layout.addWidget(title)
        main_layout.addLayout(root_row)
        main_layout.addLayout(info_row)
        main_layout.addLayout(vivado_row)
        main_layout.addLayout(button_row)
        main_layout.addWidget(self.log_view, 1)

    def apply_visual_style(self):
        self.setStyleSheet("""
            QWidget#createProjectWidget {
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

            QLineEdit {
            background-color: #ffffff;
            border: 1px solid #dcdfe6;
            border-radius: 4px;
            padding: 5px;
            }

            QLineEdit:focus {
            border-color: #409eff;
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

            QTextBrowser {
            border: 1px solid #dcdfe6;
            background-color: #ffffff;
            color: #303133;
            }
        """)

    def _browse_root_dir(self):
        start_dir = self.root_edit.text().strip() or None
        if self.services is not None:
            directory = self.services.select_directory(
                parent=self,
                title="选择工程根目录",
                start_dir=start_dir,
            )
        else:
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "选择工程根目录",
                start_dir or str(Path.cwd()),
            )
        if directory:
            self.root_edit.setText(directory)

    def _browse_vivado_path(self):
        start_path = self.vivado_path_edit.text().strip()
        start_dir = str(Path(start_path).parent) if start_path else None
        if self.services is not None:
            file_path = self.services.select_file(
                parent=self,
                title="选择 Vivado 可执行文件",
                filters="Vivado Batch (vivado.bat);;Executable Files (*.exe *.bat);;All Files (*)",
                start_dir=start_dir,
            )
        else:
            file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "选择 Vivado 可执行文件",
                start_dir or str(Path.cwd()),
                "Vivado Batch (vivado.bat);;Executable Files (*.exe *.bat);;All Files (*)",
            )
        if file_path:
            self.vivado_path_edit.setText(file_path)

    def _start(self, mode):
        root_dir = self.root_edit.text().strip()
        project_name = self.project_name_edit.text().strip()
        device = self.device_edit.text().strip()
        vivado_path = self.vivado_path_edit.text().strip()

        if not root_dir:
            self._show_error("输入不完整", "请先输入根目录")
            return
        if not project_name:
            self._show_error("输入不完整", "请先输入 project_name")
            return
        if mode == "project" and not device:
            self._show_error("输入不完整", "请先输入 device")
            return
        if mode == "project" and not vivado_path:
            self._show_error("输入不完整", "请先输入 Vivado 路径")
            return

        self.log_view.clear()
        self._last_project_dir = None
        self.open_project_button.setEnabled(False)
        self._append_log("开始执行：{mode}".format(mode="创建目录结构" if mode == "mkdir" else "构建工程"))
        self._append_log("根目录：{path}".format(path=root_dir))
        self._append_log("project_name：{name}".format(name=project_name))
        if mode == "project":
            self._append_log("device：{device}".format(device=device))
            self._append_log("Vivado路径：{path}".format(path=vivado_path))

        self._set_running(True)
        self._thread = QtCore.QThread(self)
        self._worker = CreateProjectWorker(mode, root_dir, project_name, device, vivado_path)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_worker_refs)
        self._thread.start()

    def _on_finished(self, result):
        self._set_running(False)
        project_dir = result["project_dir"]
        self._last_project_dir = project_dir
        self.open_project_button.setEnabled(True)

        if result["mode"] == "mkdir":
            self._append_log("工程目录：{path}".format(path=project_dir))
            for path in result["created_dirs"]:
                self._append_log("创建成功：{path}".format(path=path))
            message = "目录结构创建完成"
        else:
            self._append_log("工程目录：{path}".format(path=project_dir))
            self._append_log("TCL脚本：{path}".format(path=result["tcl_file"]))
            for warning in result.get("warnings", []):
                self._append_log(warning)
            output = result.get("vivado_output") or ""
            if output:
                self._append_log(output.rstrip())
            message = "Vivado工程构建完成"

        if self.services is not None:
            self.services.show_info("执行完成", message, parent=self)

    def _on_failed(self, message, detail):
        self._set_running(False)
        self._append_log("执行失败：{message}".format(message=message))
        self._show_error("执行失败", message, detail=detail)

    def _open_project_directory(self):
        if self._last_project_dir is None:
            return
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl.fromLocalFile(str(self._last_project_dir))
        )

    def _set_running(self, running):
        self.root_edit.setEnabled(not running)
        self.project_name_edit.setEnabled(not running)
        self.device_edit.setEnabled(not running)
        self.vivado_path_edit.setEnabled(not running)
        self.browse_button.setEnabled(not running)
        self.vivado_browse_button.setEnabled(not running)
        self.mkdir_button.setEnabled(not running)
        self.project_button.setEnabled(not running)
        self.open_project_button.setEnabled((not running) and self._last_project_dir is not None)
        self.clear_log_button.setEnabled(not running)
        if self.services is not None:
            self.services.set_busy(TOOL_ID, running, "正在执行create_project" if running else None)

    def _clear_worker_refs(self):
        self._thread = None
        self._worker = None

    def _append_log(self, message):
        self.log_view.append(">>{message}".format(message=message))
        if self.services is not None:
            self.services.log(TOOL_ID, message)

    def _show_error(self, title, message, detail=None):
        if self.services is not None:
            self.services.show_error(title, message, detail=detail, parent=self)
        else:
            QtWidgets.QMessageBox.critical(self, title, message)
