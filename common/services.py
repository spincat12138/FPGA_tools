# -*- coding: utf-8 -*-
from pathlib import Path

from PyQt5 import QtCore, QtWidgets


class ToolServices:
    """Application services exposed by the main GUI to child tools."""

    def __init__(self, main_window, status_bar=None, root_dir=None):
        self.main_window = main_window
        self.status_bar = status_bar
        self.root_dir = Path(root_dir) if root_dir else Path.cwd()

    def log(self, tool_id, message, level="info"):
        text = "[{tool_id}] {message}".format(tool_id=tool_id, message=message)
        timeout = 10000 if level in {"warning", "error"} else 5000
        if self.status_bar is not None:
            self.status_bar.showMessage(text, timeout)
        print(text)

    def show_info(self, title, message, parent=None):
        QtWidgets.QMessageBox.information(parent or self.main_window, title, message)

    def show_error(self, title, message, detail=None, parent=None):
        dialog = QtWidgets.QMessageBox(parent or self.main_window)
        dialog.setIcon(QtWidgets.QMessageBox.Critical)
        dialog.setWindowTitle(title)
        dialog.setText(message)
        if detail:
            dialog.setDetailedText(str(detail))
        dialog.exec_()

    def select_file(
        self,
        parent=None,
        title="选择文件",
        filters="All Files (*)",
        start_dir=None,
    ):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent or self.main_window,
            title,
            str(start_dir or self.root_dir),
            filters,
        )
        return file_path or None

    def select_directory(self, parent=None, title="选择文件夹", start_dir=None):
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            parent or self.main_window,
            title,
            str(start_dir or self.root_dir),
        )
        return directory or None

    def config_dir(self, tool_id):
        return self._app_dir(QtCore.QStandardPaths.AppConfigLocation, tool_id)

    def data_dir(self, tool_id):
        return self._app_dir(QtCore.QStandardPaths.AppDataLocation, tool_id)

    def report_progress(self, tool_id, value, message=None):
        if message:
            self.log(tool_id, message)

    def set_busy(self, tool_id, busy=True, message=None):
        cursor = QtCore.Qt.WaitCursor if busy else QtCore.Qt.ArrowCursor
        QtWidgets.QApplication.setOverrideCursor(cursor) if busy else QtWidgets.QApplication.restoreOverrideCursor()
        if message:
            self.log(tool_id, message)

    def _app_dir(self, location, tool_id):
        base = QtCore.QStandardPaths.writableLocation(location)
        if not base:
            base = str(self.root_dir / ".fpga_tools")
        path = Path(base) / tool_id
        path.mkdir(parents=True, exist_ok=True)
        return path
