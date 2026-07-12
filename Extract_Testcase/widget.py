# -*- coding: utf-8 -*-
import traceback
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from .extract_test_items import (
    PLATFORMS,
    extract_file,
    iter_input_files,
    output_path_for,
    summarize_items,
    write_excel,
)
from .metadata import TOOL_ID, TOOL_NAME


COMBO_ARROW_PATH = (
    Path(__file__).resolve().parent.parent / "GenerateUcf" / "assets" / "arrow-down.png"
).as_posix()


class ExtractWorker(QtCore.QObject):
    progress = QtCore.pyqtSignal(int, str)
    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str, str)

    def __init__(self, inputs, output, platform):
        super().__init__()
        self.inputs = inputs
        self.output = output
        self.platform = platform

    @QtCore.pyqtSlot()
    def run(self):
        try:
            files = iter_input_files(self.inputs)
            if not files:
                self.failed.emit("未找到 txt 文件", "")
                return

            results = []
            total = len(files)
            multiple = total > 1
            for index, input_file in enumerate(files, start=1):
                items = extract_file(input_file, self.platform)
                output_items = summarize_items(items)
                output_path = output_path_for(input_file, self.output, multiple=multiple)
                write_excel(output_path, output_items)
                results.append({
                    "input": str(input_file),
                    "output": str(output_path),
                    "items": len(items),
                    "rows": len(output_items),
                })
                self._log("{source}: platform={platform}, items={items}, rows={rows} -> {target}".format(
                    source=input_file,
                    platform=self.platform,
                    items=len(items),
                    rows=len(output_items),
                    target=output_path,
                ))
                self.progress.emit(
                    int(index * 100 / total) if total else 100,
                    "已处理 {index}/{total}".format(index=index, total=total),
                )
        except Exception as exc:
            self.failed.emit(str(exc), traceback.format_exc())
            return

        self.finished.emit(results)

    def _log(self, message):
        self.progress.emit(-1, message)


class ExtractTestcaseWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, services=None):
        super().__init__(parent)
        self.services = services
        self._thread = None
        self._worker = None
        self._last_output_dir = None
        self.setObjectName("extractTestcaseWidget")
        self.setProperty("preferred_size", QtCore.QSize(780, 460))
        self._build_ui()
        self.apply_visual_style()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(24, 22, 24, 18)
        main_layout.setSpacing(14)

        title = QtWidgets.QLabel(TOOL_NAME)
        title.setObjectName("title")

        platform_row = QtWidgets.QHBoxLayout()
        platform_row.setSpacing(8)
        platform_label = QtWidgets.QLabel("平台选择")
        self.platform_combo = QtWidgets.QComboBox()
        self.platform_combo.addItems(PLATFORMS)
        platform_row.addWidget(platform_label)
        platform_row.addWidget(self.platform_combo)
        platform_row.addStretch(1)

        input_row = QtWidgets.QHBoxLayout()
        input_row.setSpacing(8)
        input_label = QtWidgets.QLabel("待选择文件路径")
        self.input_edit = QtWidgets.QLineEdit()
        self.input_edit.setPlaceholderText("选择 txt 文件或包含 txt 文件的目录；多个路径用分号分隔")
        self.input_file_button = QtWidgets.QPushButton("选择文件...")
        self.input_dir_button = QtWidgets.QPushButton("选择目录...")
        self.input_file_button.clicked.connect(self._browse_input_files)
        self.input_dir_button.clicked.connect(self._browse_input_directory)
        input_row.addWidget(input_label)
        input_row.addWidget(self.input_edit, 1)
        input_row.addWidget(self.input_file_button)
        input_row.addWidget(self.input_dir_button)

        output_row = QtWidgets.QHBoxLayout()
        output_row.setSpacing(8)
        output_label = QtWidgets.QLabel("输出路径")
        self.output_edit = QtWidgets.QLineEdit()
        self.output_edit.setPlaceholderText("可选；留空则输出到输入文件所在目录")
        self.output_button = QtWidgets.QPushButton("浏览...")
        self.output_button.clicked.connect(self._browse_output_directory)
        output_row.addWidget(output_label)
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(self.output_button)

        button_row = QtWidgets.QHBoxLayout()
        button_row.setSpacing(8)
        self.start_button = QtWidgets.QPushButton("开始提取")
        self.open_output_button = QtWidgets.QPushButton("打开输出目录")
        self.clear_log_button = QtWidgets.QPushButton("清空日志")
        self.open_output_button.setEnabled(False)
        self.start_button.clicked.connect(self._start_extract)
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
        main_layout.addLayout(platform_row)
        main_layout.addLayout(input_row)
        main_layout.addLayout(output_row)
        main_layout.addLayout(button_row)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.log_view, 1)

    def apply_visual_style(self):
        self.setStyleSheet("""
            QWidget#extractTestcaseWidget {
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

            QComboBox {
            border: 1px solid #ccc;
            border-radius: 4px;
            padding: 4px 26px 4px 6px;
            background-color: white;
            color: #303133;
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
            }

            QComboBox QAbstractItemView {
            background-color: #ffffff;
            border: 1px solid #ccc;
            selection-background-color: #87ceeb;
            selection-color: #333;
            outline: 0;
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
        """.replace("__COMBO_ARROW_PATH__", COMBO_ARROW_PATH))

    def _browse_input_files(self):
        start_dir = self._start_dir_from_text(self.input_edit.text())
        files, _selected_filter = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "选择TXT文件",
            start_dir,
            "Text Files (*.txt);;All Files (*)",
        )
        if files:
            self.input_edit.setText("; ".join(files))

    def _browse_input_directory(self):
        start_dir = self._start_dir_from_text(self.input_edit.text())
        if self.services is not None:
            directory = self.services.select_directory(
                parent=self,
                title="选择输入目录",
                start_dir=start_dir,
            )
        else:
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "选择输入目录",
                start_dir,
            )
        if directory:
            self.input_edit.setText(directory)

    def _browse_output_directory(self):
        start_dir = self.output_edit.text().strip() or self._start_dir_from_text(self.input_edit.text())
        if self.services is not None:
            directory = self.services.select_directory(
                parent=self,
                title="选择输出目录",
                start_dir=start_dir,
            )
        else:
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "选择输出目录",
                start_dir,
            )
        if directory:
            self.output_edit.setText(directory)

    def _start_extract(self):
        inputs = self._parse_paths(self.input_edit.text())
        if not inputs:
            self._show_error("输入不完整", "请先选择 txt 文件或输入目录")
            return

        missing_paths = [path for path in inputs if not path.exists()]
        if missing_paths:
            self._show_error(
                "路径不存在",
                "以下路径不存在：\n{paths}".format(paths="\n".join(str(path) for path in missing_paths)),
            )
            return

        invalid_files = [path for path in inputs if path.is_file() and path.suffix.lower() != ".txt"]
        if invalid_files:
            self._show_error(
                "文件类型不匹配",
                "以下文件不是 .txt 文件：\n{files}".format(files="\n".join(str(path) for path in invalid_files)),
            )
            return

        output_ok, output = self._output_path()
        if not output_ok:
            return

        self.log_view.clear()
        self.progress_bar.setValue(0)
        self.open_output_button.setEnabled(False)
        self._last_output_dir = None
        self._append_log("开始提取测试项名字")
        self._append_log("平台：{platform}".format(platform=self.platform_combo.currentText()))
        self._append_log("输入：{inputs}".format(inputs="; ".join(str(path) for path in inputs)))
        output_text = str(output) if output is not None else "与输入文件同目录"
        self._append_log("输出路径：{output}".format(output=output_text))

        self._set_running(True)
        self._thread = QtCore.QThread(self)
        self._worker = ExtractWorker(inputs, output, self.platform_combo.currentText())
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

    def _output_path(self):
        text = self.output_edit.text().strip().strip('"')
        if not text:
            return True, None

        output = Path(text)
        if output.suffix:
            try:
                output.parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                self._show_error("输出路径创建失败", str(exc))
                return False, None
            return True, output
        try:
            output.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._show_error("输出路径创建失败", str(exc))
            return False, None
        return True, output

    def _on_progress(self, value, message):
        if value >= 0:
            self.progress_bar.setValue(value)
        self._append_log(message)

    def _on_finished(self, results):
        self._set_running(False)
        self.progress_bar.setValue(100 if results else 0)
        self._last_output_dir = self._resolve_output_dir(results)
        self.open_output_button.setEnabled(self._last_output_dir is not None and self._last_output_dir.exists())
        total_items = sum(item["items"] for item in results)
        total_rows = sum(item["rows"] for item in results)
        message = "提取完成，共处理 {files} 个文件，提取 {items} 条记录，输出 {rows} 行汇总。".format(
            files=len(results),
            items=total_items,
            rows=total_rows,
        )
        self._append_log(message)
        if self.services is not None:
            self.services.show_info("提取完成", message, parent=self)

    def _on_failed(self, message, detail):
        self._set_running(False)
        self.progress_bar.setValue(0)
        self._append_log("提取失败：{message}".format(message=message))
        self._show_error("提取失败", message, detail=detail)

    def _resolve_output_dir(self, results):
        output_text = self.output_edit.text().strip().strip('"')
        if output_text:
            output = Path(output_text)
            return output.parent if output.suffix else output
        output_dirs = []
        seen = set()
        for item in results:
            output_dir = Path(item["output"]).parent
            key = str(output_dir.resolve() if output_dir.exists() else output_dir.absolute()).casefold()
            if key not in seen:
                seen.add(key)
                output_dirs.append(output_dir)
        return output_dirs[0] if len(output_dirs) == 1 else None

    def _open_output_directory(self):
        if self._last_output_dir is None:
            return
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl.fromLocalFile(str(self._last_output_dir.resolve()))
        )

    def _set_running(self, running):
        self.platform_combo.setEnabled(not running)
        self.input_edit.setEnabled(not running)
        self.output_edit.setEnabled(not running)
        self.input_file_button.setEnabled(not running)
        self.input_dir_button.setEnabled(not running)
        self.output_button.setEnabled(not running)
        self.start_button.setEnabled(not running)
        if self.services is not None:
            self.services.set_busy(TOOL_ID, running, "正在提取测试项名字" if running else None)

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
