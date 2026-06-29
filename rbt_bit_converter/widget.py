# -*- coding: utf-8 -*-
import traceback
from pathlib import Path

from PyQt5 import QtCore, QtWidgets

from .bit2rbt import bit2rbt
from .metadata import TOOL_ID, TOOL_NAME
from .rbt2bit import rbt2bit


class ConvertWorker(QtCore.QObject):
    progress = QtCore.pyqtSignal(int, str)
    finished = QtCore.pyqtSignal(object)

    def __init__(self, mode, input_files, bit_rename=False):
        super().__init__()
        self.mode = mode
        self.input_files = input_files
        self.bit_rename = bit_rename

    @QtCore.pyqtSlot()
    def run(self):
        results = []
        total = len(self.input_files)

        for index, input_file in enumerate(self.input_files, start=1):
            input_path = Path(input_file)
            try:
                if self.mode == "rbt2bit":
                    output_path = rbt2bit(input_path, logger=self._log)
                else:
                    output_path = bit2rbt(
                        input_path,
                        rename=self.bit_rename,
                        logger=self._log,
                    )
                results.append({
                    "input": str(input_path),
                    "output": str(output_path),
                    "ok": True,
                    "error": "",
                    "detail": "",
                })
                self._log("完成：{source} -> {target}".format(
                    source=input_path,
                    target=output_path,
                ))
            except Exception as exc:
                detail = traceback.format_exc()
                results.append({
                    "input": str(input_path),
                    "output": "",
                    "ok": False,
                    "error": str(exc),
                    "detail": detail,
                })
                self._log("失败：{source}，{error}".format(
                    source=input_path,
                    error=exc,
                ))

            value = int(index * 100 / total) if total else 100
            self.progress.emit(value, "已处理 {index}/{total}".format(
                index=index,
                total=total,
            ))

        self.finished.emit(results)

    def _log(self, message):
        self.progress.emit(-1, message)


class RbtBitConverterWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, services=None):
        super().__init__(parent)
        self.services = services
        self._thread = None
        self._worker = None
        self.setObjectName("rbtBitConverterWidget")
        self.setProperty("preferred_size", QtCore.QSize(800, 500))
        self._build_ui()
        self.apply_visual_style()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(24, 22, 24, 18)
        main_layout.setSpacing(14)

        title = QtWidgets.QLabel(TOOL_NAME)
        title.setObjectName("title")

        converter_row = QtWidgets.QHBoxLayout()
        converter_row.setSpacing(16)

        rbt_group = QtWidgets.QGroupBox("RBT 转 BIT")
        rbt_panel = QtWidgets.QVBoxLayout(rbt_group)
        rbt_panel.setSpacing(8)
        rbt_panel.setContentsMargins(12, 18, 12, 12)
        rbt_file_row = QtWidgets.QHBoxLayout()
        rbt_file_row.setSpacing(8)
        rbt_label = QtWidgets.QLabel("RBT文件")
        self.rbt_edit = QtWidgets.QLineEdit()
        self.rbt_edit.setPlaceholderText("选择一个或多个 .rbt 文件")
        self.rbt_browse_button = QtWidgets.QPushButton("浏览...")
        self.rbt_browse_button.clicked.connect(self._browse_rbt_files)
        self.rbt_to_bit_button = QtWidgets.QPushButton("RBT 转 BIT")
        self.rbt_to_bit_button.clicked.connect(lambda: self._start_conversion("rbt2bit"))
        rbt_file_row.addWidget(rbt_label)
        rbt_file_row.addWidget(self.rbt_edit, 1)
        rbt_file_row.addWidget(self.rbt_browse_button)
        rbt_panel.addLayout(rbt_file_row)
        rbt_panel.addWidget(self.rbt_to_bit_button, 0, QtCore.Qt.AlignLeft)
        rbt_panel.addStretch(1)

        bit_group = QtWidgets.QGroupBox("BIT 转 RBT")
        bit_panel = QtWidgets.QVBoxLayout(bit_group)
        bit_panel.setSpacing(8)
        bit_panel.setContentsMargins(12, 18, 12, 12)
        bit_file_row = QtWidgets.QHBoxLayout()
        bit_file_row.setSpacing(8)
        bit_label = QtWidgets.QLabel("BIT文件")
        self.bit_edit = QtWidgets.QLineEdit()
        self.bit_edit.setPlaceholderText("选择一个或多个 .bit 文件")
        self.bit_browse_button = QtWidgets.QPushButton("浏览...")
        self.bit_browse_button.clicked.connect(self._browse_bit_files)
        self.bit_to_rbt_button = QtWidgets.QPushButton("BIT 转 RBT")
        self.bit_to_rbt_button.clicked.connect(lambda: self._start_conversion("bit2rbt"))
        self.bit_rename_checkbox = QtWidgets.QCheckBox("提取码流编号")
        self.bit_rename_checkbox.setChecked(False)
        bit_file_row.addWidget(bit_label)
        bit_file_row.addWidget(self.bit_edit, 1)
        bit_file_row.addWidget(self.bit_browse_button)
        bit_action_row = QtWidgets.QHBoxLayout()
        bit_action_row.setSpacing(12)
        bit_action_row.addWidget(self.bit_to_rbt_button)
        bit_action_row.addWidget(self.bit_rename_checkbox)
        bit_action_row.addStretch(1)
        bit_panel.addLayout(bit_file_row)
        bit_panel.addLayout(bit_action_row)
        bit_panel.addStretch(1)

        converter_row.addWidget(rbt_group, 1)
        converter_row.addWidget(bit_group, 1)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.log_view = QtWidgets.QTextBrowser()
        self.log_view.setOpenExternalLinks(False)

        main_layout.addWidget(title)
        main_layout.addLayout(converter_row)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.log_view, 1)

    def apply_visual_style(self):
        self.setStyleSheet("""
            QWidget#rbtBitConverterWidget {
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

    def _browse_rbt_files(self):
        self._browse_files(
            edit=self.rbt_edit,
            title="选择RBT文件",
            filters="RBT Files (*.rbt);;All Files (*)",
        )

    def _browse_bit_files(self):
        self._browse_files(
            edit=self.bit_edit,
            title="选择BIT文件",
            filters="BIT Files (*.bit);;All Files (*)",
        )

    def _browse_files(self, edit, title, filters):
        start_dir = self._start_dir_from_text(edit.text())
        files, _selected_filter = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            title,
            start_dir,
            filters,
        )
        if files:
            edit.setText("; ".join(files))

    def _start_conversion(self, mode):
        source_edit = self.rbt_edit if mode == "rbt2bit" else self.bit_edit
        input_files = self._parse_paths(source_edit.text())
        if not input_files:
            self._show_error("输入不完整", "请先选择要转换的{kind}文件".format(
                kind="RBT" if mode == "rbt2bit" else "BIT",
            ))
            return

        suffix = ".rbt" if mode == "rbt2bit" else ".bit"
        invalid_files = [path for path in input_files if path.suffix.lower() != suffix]
        if invalid_files:
            self._show_error(
                "文件类型不匹配",
                "以下文件不是 {suffix} 文件：\n{files}".format(
                    suffix=suffix,
                    files="\n".join(str(path) for path in invalid_files),
                ),
            )
            return

        missing_files = [path for path in input_files if not path.is_file()]
        if missing_files:
            self._show_error(
                "文件不存在",
                "以下文件不存在：\n{files}".format(
                    files="\n".join(str(path) for path in missing_files),
                ),
            )
            return

        self.log_view.clear()
        self.progress_bar.setValue(0)
        self._append_log("开始批量转换：{name}".format(
            name="RBT 转 BIT" if mode == "rbt2bit" else "BIT 转 RBT",
        ))
        self._append_log("共 {count} 个文件".format(count=len(input_files)))

        self._set_running(True)
        self._thread = QtCore.QThread(self)
        self._worker = ConvertWorker(
            mode,
            input_files,
            bit_rename=self.bit_rename_checkbox.isChecked(),
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_worker_refs)
        self._thread.start()

    def _on_progress(self, value, message):
        if value >= 0:
            self.progress_bar.setValue(value)
        self._append_log(message)

    def _on_finished(self, results):
        self._set_running(False)
        ok_count = sum(1 for item in results if item["ok"])
        fail_count = len(results) - ok_count
        self.progress_bar.setValue(100 if results else 0)

        message = "转换完成，成功 {ok} 个，失败 {failed} 个。".format(
            ok=ok_count,
            failed=fail_count,
        )
        self._append_log(message)
        if fail_count:
            detail = "\n\n".join(
                item["detail"] for item in results if not item["ok"]
            )
            self._show_error("转换完成但存在失败", message, detail=detail)
        elif self.services is not None:
            self.services.show_info("转换完成", message, parent=self)

    def _set_running(self, running):
        self.rbt_edit.setEnabled(not running)
        self.bit_edit.setEnabled(not running)
        self.rbt_browse_button.setEnabled(not running)
        self.bit_browse_button.setEnabled(not running)
        self.bit_rename_checkbox.setEnabled(not running)
        self.rbt_to_bit_button.setEnabled(not running)
        self.bit_to_rbt_button.setEnabled(not running)
        if self.services is not None:
            self.services.set_busy(TOOL_ID, running, "正在执行RBT/BIT转换" if running else None)

    def _clear_worker_refs(self):
        self._thread = None
        self._worker = None

    def _parse_paths(self, text):
        return [
            Path(item.strip().strip('"'))
            for item in text.replace("\n", ";").split(";")
            if item.strip()
        ]

    def _start_dir_from_text(self, text):
        paths = self._parse_paths(text)
        if paths:
            first_path = paths[0]
            if first_path.is_dir():
                return str(first_path)
            if first_path.parent.exists():
                return str(first_path.parent)
        return str(Path.cwd())

    def _append_log(self, message):
        self.log_view.append(">>{message}".format(message=message))
        if self.services is not None:
            self.services.log(TOOL_ID, message)

    def _show_error(self, title, message, detail=None):
        if self.services is not None:
            self.services.show_error(title, message, detail=detail, parent=self)
        else:
            QtWidgets.QMessageBox.critical(self, title, message)
