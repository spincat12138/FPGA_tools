# -*- coding: utf-8 -*-
import traceback
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from .core import copy_and_rename_rbt_files


TOOL_ID = "rbt_file_organization"
TOOL_NAME = "RBT文件整理"


class OrganizationWorker(QtCore.QObject):
    progress = QtCore.pyqtSignal(int, str)
    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str, str)

    def __init__(self, source_root):
        super().__init__()
        self.source_root = source_root

    @QtCore.pyqtSlot()
    def run(self):
        try:
            result = copy_and_rename_rbt_files(
                self.source_root,
                progress_callback=self._on_progress,
            )
        except Exception as exc:
            self.failed.emit(str(exc), traceback.format_exc())
            return

        self.finished.emit(result)

    def _on_progress(self, index, total, record):
        value = int(index * 100 / total) if total else 100
        action = "覆盖" if record.overwritten else "复制"
        message = "{action}: {source} -> {destination}".format(
            action=action,
            source=record.source,
            destination=record.destination,
        )
        self.progress.emit(value, message)


class RbtFileOrganizationWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, services=None):
        super().__init__(parent)
        self.services = services
        self._thread = None
        self._worker = None
        self._last_target_dir = None
        self.setObjectName("rbtOrganizationWidget")
        self.setProperty("preferred_size", QtCore.QSize(760, 430))
        self._build_ui()
        self.apply_visual_style()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(24, 22, 24, 18)
        main_layout.setSpacing(14)

        title = QtWidgets.QLabel(TOOL_NAME)
        title.setObjectName("title")

        form_row = QtWidgets.QHBoxLayout()
        form_row.setSpacing(8)
        path_label = QtWidgets.QLabel("整理路径")
        self.path_edit = QtWidgets.QLineEdit()
        self.path_edit.setPlaceholderText("选择包含 rbt 文件的文件夹")
        self.browse_button = QtWidgets.QPushButton("浏览...")
        self.browse_button.clicked.connect(self._browse_directory)
        form_row.addWidget(path_label)
        form_row.addWidget(self.path_edit, 1)
        form_row.addWidget(self.browse_button)

        button_row = QtWidgets.QHBoxLayout()
        button_row.setSpacing(8)
        self.start_button = QtWidgets.QPushButton("开始整理")
        self.open_output_button = QtWidgets.QPushButton("打开输出目录")
        self.clear_log_button = QtWidgets.QPushButton("清空日志")
        self.open_output_button.setEnabled(False)
        self.start_button.clicked.connect(self._start_organization)
        self.open_output_button.clicked.connect(self._open_output_directory)
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.open_output_button)
        button_row.addWidget(self.clear_log_button)
        button_row.addStretch(1)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.log_view = QtWidgets.QTextBrowser()
        self.log_view.setOpenExternalLinks(False)
        self.clear_log_button.clicked.connect(self.log_view.clear)

        main_layout.addWidget(title)
        main_layout.addLayout(form_row)
        main_layout.addLayout(button_row)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.log_view, 1)

    def apply_visual_style(self):
        self.setStyleSheet("""
            QWidget#rbtOrganizationWidget {
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

            QProgressBar {
            border: 1px solid #dcdfe6;
            border-radius: 4px;
            text-align: center;
            background-color: #ffffff;
            }

            QProgressBar::chunk {
            background-color: #67c23a;
            }

            QTextBrowser {
            border: 1px solid #dcdfe6;
            background-color: #ffffff;
            color: #303133;
            }
        """)

    def _browse_directory(self):
        start_dir = self.path_edit.text().strip() or None
        if self.services is not None:
            directory = self.services.select_directory(
                parent=self,
                title="选择整理路径",
                start_dir=start_dir,
            )
        else:
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "选择整理路径",
                start_dir or str(Path.cwd()),
            )
        if directory:
            self.path_edit.setText(directory)

    def _start_organization(self):
        source_root = self.path_edit.text().strip()
        if not source_root:
            self._show_error("路径不能为空", "请先输入要整理的路径")
            return

        self._append_log("开始整理：{path}".format(path=source_root))
        self._set_running(True)
        self.progress_bar.setValue(0)
        self.open_output_button.setEnabled(False)

        self._thread = QtCore.QThread(self)
        self._worker = OrganizationWorker(source_root)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_worker_refs)
        self._thread.start()

    def _on_progress(self, value, message):
        self.progress_bar.setValue(value)
        self._append_log(message)

    def _on_finished(self, result):
        self.progress_bar.setValue(100)
        self._last_target_dir = result.target_dir
        self.open_output_button.setEnabled(True)
        self._set_running(False)
        message = "整理完成，共复制 {count} 个 rbt 文件。".format(count=result.copied_count)
        self._append_log(message)
        if self.services is not None:
            self.services.show_info("整理完成", message, parent=self)

    def _on_failed(self, message, detail):
        self.progress_bar.setValue(0)
        self._set_running(False)
        self._append_log("整理失败：{message}".format(message=message))
        self._show_error("整理失败", message, detail=detail)

    def _open_output_directory(self):
        if self._last_target_dir is None:
            return
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl.fromLocalFile(str(self._last_target_dir))
        )

    def _set_running(self, running):
        self.start_button.setEnabled(not running)
        self.browse_button.setEnabled(not running)
        self.path_edit.setEnabled(not running)
        if self.services is not None:
            self.services.set_busy(TOOL_ID, running, "正在整理RBT文件" if running else None)

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
