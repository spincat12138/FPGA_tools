# -*- coding: utf-8 -*-
import traceback
from pathlib import Path
import time

from PyQt5 import QtCore, QtGui, QtWidgets

from .metadata import TOOL_ID, TOOL_NAME
from .rbt2vcd import convert_rbt_to_vcd, format_elapsed_seconds, load_rbt2vcd_profile


class ConvertWorker(QtCore.QObject):
    progress = QtCore.pyqtSignal(int, str)
    finished = QtCore.pyqtSignal(object)

    def __init__(self, jobs, period_ps=20000, profile=None):
        super().__init__()
        self.jobs = jobs
        self.period_ps = period_ps
        self.profile = profile

    @QtCore.pyqtSlot()
    def run(self):
        batch_start_time = time.time()
        results = []
        total = len(self.jobs)

        for index, job in enumerate(self.jobs, start=1):
            input_path = job["input"]
            output_path = job["output"]
            try:
                result = convert_rbt_to_vcd(
                    input_path,
                    output_path,
                    period_ps=self.period_ps,
                    profile=self.profile,
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
                self._log("读取 {words} 个 RBT 数据字，写入 {vectors} 个 VCD 向量".format(
                    words=result["word_count"],
                    vectors=result["vector_count"],
                ))
                self._log("用时{time}".format(
                    time=result["elapsed_text"],
                ))
            except Exception as exc:
                detail = traceback.format_exc()
                results.append({
                    "input": str(input_path),
                    "output": str(output_path),
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

        self._log("批量转换总用时{time}".format(
            time=format_elapsed_seconds(time.time() - batch_start_time),
        ))
        self.finished.emit(results)

    def _log(self, message):
        self.progress.emit(-1, message)


class Rbt2VcdWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, services=None):
        super().__init__(parent)
        self.services = services
        self._thread = None
        self._worker = None
        self._last_output_dir = None
        self.setObjectName("rbt2VcdWidget")
        self.setProperty("preferred_size", QtCore.QSize(780, 460))
        self._build_ui()
        self.apply_visual_style()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(24, 22, 24, 18)
        main_layout.setSpacing(14)

        title = QtWidgets.QLabel(TOOL_NAME)
        title.setObjectName("title")

        input_row = QtWidgets.QHBoxLayout()
        input_row.setSpacing(8)
        input_label = QtWidgets.QLabel("RBT文件")
        self.input_edit = QtWidgets.QLineEdit()
        self.input_edit.setPlaceholderText("选择一个或多个 .rbt 文件")
        self.input_browse_button = QtWidgets.QPushButton("浏览...")
        self.input_browse_button.clicked.connect(self._browse_input_files)
        input_row.addWidget(input_label)
        input_row.addWidget(self.input_edit, 1)
        input_row.addWidget(self.input_browse_button)

        output_row = QtWidgets.QHBoxLayout()
        output_row.setSpacing(8)
        output_label = QtWidgets.QLabel("输出目录")
        self.output_edit = QtWidgets.QLineEdit()
        self.output_edit.setPlaceholderText("可选；留空则输出到每个输入文件所在目录")
        self.output_browse_button = QtWidgets.QPushButton("浏览...")
        self.output_browse_button.clicked.connect(self._browse_output_directory)
        output_row.addWidget(output_label)
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(self.output_browse_button)

        profile_row = QtWidgets.QHBoxLayout()
        profile_row.setSpacing(8)
        profile_label = QtWidgets.QLabel("配置JSON")
        self.profile_edit = QtWidgets.QLineEdit()
        self.profile_edit.setPlaceholderText("可选；自定义 SIGNALS 和 CTRL_* 控制值")
        self.profile_browse_button = QtWidgets.QPushButton("浏览...")
        self.profile_browse_button.clicked.connect(self._browse_profile_file)
        profile_row.addWidget(profile_label)
        profile_row.addWidget(self.profile_edit, 1)
        profile_row.addWidget(self.profile_browse_button)

        button_row = QtWidgets.QHBoxLayout()
        button_row.setSpacing(8)
        self.convert_button = QtWidgets.QPushButton("开始转换")
        self.open_output_button = QtWidgets.QPushButton("打开输出目录")
        self.clear_log_button = QtWidgets.QPushButton("清空日志")
        self.open_output_button.setEnabled(False)
        self.convert_button.clicked.connect(self._start_conversion)
        self.open_output_button.clicked.connect(self._open_output_directory)
        button_row.addWidget(self.convert_button)
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
        main_layout.addLayout(input_row)
        main_layout.addLayout(output_row)
        main_layout.addLayout(profile_row)
        main_layout.addLayout(button_row)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.log_view, 1)

    def apply_visual_style(self):
        self.setStyleSheet("""
            QWidget#rbt2VcdWidget {
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

    def _browse_input_files(self):
        start_dir = self._start_dir_from_text(self.input_edit.text())
        files, _selected_filter = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "选择RBT文件",
            start_dir,
            "RBT Files (*.rbt);;All Files (*)",
        )
        if files:
            self.input_edit.setText("; ".join(files))

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

    def _browse_profile_file(self):
        start_dir = self._start_dir_from_text(self.profile_edit.text() or self.input_edit.text())
        file_name, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择RBT2VCD配置JSON",
            start_dir,
            "JSON Files (*.json);;All Files (*)",
        )
        if file_name:
            self.profile_edit.setText(file_name)

    def _start_conversion(self):
        input_files = self._parse_paths(self.input_edit.text())
        if not input_files:
            self._show_error("输入不完整", "请先选择要转换的 RBT 文件")
            return

        profile_info = self._load_profile()
        if profile_info is None:
            return
        profile, profile_path = profile_info

        jobs = self._build_jobs(input_files)
        if jobs is None:
            return

        self.log_view.clear()
        self.progress_bar.setValue(0)
        self.open_output_button.setEnabled(False)
        self._append_log("开始批量转换：RBT 转 VCD")
        self._append_log("共 {count} 个文件".format(count=len(jobs)))
        if profile_path is not None:
            self._append_log("使用配置：{path}".format(path=profile_path))
        self._append_log("VCD信号数量：{count}".format(count=profile.signal_count))

        self._set_running(True)
        self._thread = QtCore.QThread(self)
        self._worker = ConvertWorker(jobs, profile=profile)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_worker_refs)
        self._thread.start()

    def _build_jobs(self, input_files):
        invalid_files = [path for path in input_files if path.suffix.lower() != ".rbt"]
        if invalid_files:
            self._show_error(
                "文件类型不匹配",
                "以下文件不是 .rbt 文件：\n{files}".format(
                    files="\n".join(str(path) for path in invalid_files),
                ),
            )
            return None

        missing_files = [path for path in input_files if not path.is_file()]
        if missing_files:
            self._show_error(
                "文件不存在",
                "以下文件不存在：\n{files}".format(
                    files="\n".join(str(path) for path in missing_files),
                ),
            )
            return None

        output_dir_text = self.output_edit.text().strip()
        output_dir = Path(output_dir_text) if output_dir_text else None
        if output_dir is not None:
            if output_dir.exists() and not output_dir.is_dir():
                self._show_error("输出目录无效", "输出路径不是文件夹：{path}".format(path=output_dir))
                return None
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                self._show_error("输出目录创建失败", str(exc))
                return None

        jobs = []
        for input_path in input_files:
            output_path = (output_dir / input_path.with_suffix(".vcd").name) if output_dir else input_path.with_suffix(".vcd")
            jobs.append({
                "input": input_path,
                "output": output_path,
            })

        duplicate_outputs = self._duplicate_paths(job["output"] for job in jobs)
        if duplicate_outputs:
            self._show_error(
                "输出文件冲突",
                "以下输出文件会被多个输入文件同时生成，请调整输入或输出目录：\n{files}".format(
                    files="\n".join(str(path) for path in duplicate_outputs),
                ),
            )
            return None

        if output_dir is not None:
            self._last_output_dir = output_dir
        elif len(jobs) == 1:
            self._last_output_dir = jobs[0]["output"].parent
        else:
            self._last_output_dir = None

        return jobs

    def _on_progress(self, value, message):
        if value >= 0:
            self.progress_bar.setValue(value)
        self._append_log(message)

    def _on_finished(self, results):
        self._set_running(False)
        ok_count = sum(1 for item in results if item["ok"])
        fail_count = len(results) - ok_count
        self.progress_bar.setValue(100 if results else 0)
        self.open_output_button.setEnabled(self._last_output_dir is not None and self._last_output_dir.exists())

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

    def _open_output_directory(self):
        if self._last_output_dir is None:
            return
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl.fromLocalFile(str(self._last_output_dir))
        )

    def _set_running(self, running):
        self.input_edit.setEnabled(not running)
        self.output_edit.setEnabled(not running)
        self.profile_edit.setEnabled(not running)
        self.input_browse_button.setEnabled(not running)
        self.output_browse_button.setEnabled(not running)
        self.profile_browse_button.setEnabled(not running)
        self.convert_button.setEnabled(not running)
        if self.services is not None:
            self.services.set_busy(TOOL_ID, running, "正在执行RBT转VCD" if running else None)

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

    def _load_profile(self):
        profile_text = self.profile_edit.text().strip().strip('"')
        profile_path = Path(profile_text) if profile_text else None
        if profile_path is not None and not profile_path.is_file():
            self._show_error("配置文件不存在", "找不到配置JSON：{path}".format(path=profile_path))
            return None

        try:
            profile = load_rbt2vcd_profile(profile_path)
        except Exception as exc:
            self._show_error(
                "配置文件无效",
                str(exc),
                detail=traceback.format_exc(),
            )
            return None

        return profile, profile_path

    def _duplicate_paths(self, paths):
        seen = set()
        duplicates = []
        for path in paths:
            key = str(path.resolve() if path.exists() else path.absolute()).casefold()
            if key in seen:
                duplicates.append(path)
            else:
                seen.add(key)
        return duplicates

    def _append_log(self, message):
        self.log_view.append(">>{message}".format(message=message))
        if self.services is not None:
            self.services.log(TOOL_ID, message)

    def _show_error(self, title, message, detail=None):
        if self.services is not None:
            self.services.show_error(title, message, detail=detail, parent=self)
        else:
            QtWidgets.QMessageBox.critical(self, title, message)
