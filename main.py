# -*- coding: utf-8 -*-
import importlib
import sys
import traceback
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from common.services import ToolServices
from tools_registry import TOOLS


APP_NAME = "FPGA 工具集合"
ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_TOOL_SIZE = QtCore.QSize(900, 640)
MIN_REASONABLE_TOOL_SIZE = QtCore.QSize(120, 80)
MIN_WINDOW_SIZE = QtCore.QSize(480, 360)
SCREEN_MARGIN = 80
TOOL_PREFERRED_SIZE_PROPERTY = "_fpga_tools_preferred_size"
EXTERNAL_TOOL_SIZE_PROPERTY = "preferred_size"


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("mainWindow")
        self.setWindowTitle(APP_NAME)
        self.resize(DEFAULT_TOOL_SIZE)
        self._resize_to_tool_pending = False
        self._resizing_to_tool = False

        icon_path = ROOT_DIR / "RBT2ATP" / "logo.ico"
        if icon_path.exists():
            self.setWindowIcon(QtGui.QIcon(str(icon_path)))

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setObjectName("toolTabs")
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(False)
        self.tabs.currentChanged.connect(self._schedule_resize_to_current_tool)
        self.setCentralWidget(self.tabs)

        self.menuBar().setObjectName("mainMenuBar")
        self.statusBar().setObjectName("mainStatusBar")
        self.services = ToolServices(
            main_window=self,
            status_bar=self.statusBar(),
            root_dir=ROOT_DIR,
        )

        self._build_menu()
        self.apply_visual_style()
        self._load_tools()

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule_resize_to_current_tool()

    def eventFilter(self, watched, event):
        resize_events = {
            QtCore.QEvent.LayoutRequest,
            QtCore.QEvent.PolishRequest,
            QtCore.QEvent.Show,
        }
        if watched is self.tabs.currentWidget() and event.type() in resize_events:
            self._schedule_resize_to_current_tool()
        return super().eventFilter(watched, event)

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("文件")
        reload_action = QtWidgets.QAction("重新加载工具", self)
        reload_action.triggered.connect(self._load_tools)
        file_menu.addAction(reload_action)
        file_menu.addSeparator()

        exit_action = QtWidgets.QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = self.menuBar().addMenu("帮助")
        about_action = QtWidgets.QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def apply_visual_style(self):
        self.setStyleSheet("""
            QMainWindow#mainWindow {
            background-color: #f5f7fa;
            }


            QMenuBar#mainMenuBar {
            background-color: #ffffff;
            border-bottom: 1px solid #dcdfe6;
            color: #2c3e50;
            padding: 2px 6px;
            }


            QMenuBar#mainMenuBar::item {
            background-color: transparent;
            border-radius: 4px;
            padding: 5px 10px;
            }


            QMenuBar#mainMenuBar::item:selected {
            background-color: #ecf5ff;
            color: #409eff;
            }


            QMenu {
            background-color: #ffffff;
            border: 1px solid #dcdfe6;
            padding: 4px;
            }


            QMenu::separator {
            height: 1px;
            background-color: #ebeef5;
            margin: 4px 6px;
            }


            QMenu::item {
            color: #2c3e50;
            border-radius: 4px;
            padding: 6px 28px 6px 20px;
            }


            QMenu::item:selected {
            background-color: #409eff;
            color: #ffffff;
            }


            QTabWidget#toolTabs::pane {
            background-color: #f5f7fa;
            border-top: 1px solid #dcdfe6;
            }


            QTabWidget#toolTabs::tab-bar {
            left: 8px;
            }


            QTabWidget#toolTabs QTabBar::tab {
            background-color: #f8f9fb;
            border: 1px solid #dcdfe6;
            border-bottom-color: #dcdfe6;
            color: #2c3e50;
            padding: 6px 24px;
            min-width: 136px;
            }


            QTabWidget#toolTabs QTabBar::tab:hover:!selected {
            background-color: #ecf5ff;
            color: #409eff;
            }


            QTabWidget#toolTabs QTabBar::tab:selected {
            background-color: #ffffff;
            border-top: 2px solid #409eff;
            border-bottom-color: #ffffff;
            color: #409eff;
            font-weight: bold;
            }


            QStatusBar#mainStatusBar {
            background-color: #ffffff;
            border-top: 1px solid #dcdfe6;
            color: #606266;
            }


            QWidget#mainEmptyPage,
            QWidget#mainErrorPage {
            background-color: #f5f7fa;
            }


            QLabel#emptyPageLabel,
            QLabel#errorSummary {
            color: #606266;
            }


            QLabel#errorTitle {
            color: #2c3e50;
            font-size: 16px;
            font-weight: bold;
            }


            QPlainTextEdit#errorDetail {
            background-color: #ffffff;
            border: 1px solid #dcdfe6;
            border-radius: 4px;
            color: #303133;
            padding: 6px;
            }


            QPushButton#openToolDocButton {
            background-color: #409eff;
            color: white;
            border-radius: 4px;
            padding: 5px 15px;
            font-weight: bold;
            }


            QPushButton#openToolDocButton:hover {
            background-color: #66b1ff;
            }
        """)

    def _load_tools(self):
        self.tabs.clear()
        enabled_tools = [tool for tool in TOOLS if tool.get("enabled", True)]
        if not enabled_tools:
            self._add_tab(self._empty_page("暂无已启用工具"), "空")
            self.statusBar().showMessage("暂无已启用工具")
            self._schedule_resize_to_current_tool()
            return

        for tool in enabled_tools:
            self._add_tool_tab(tool)

        self.statusBar().showMessage("已加载 {count} 个工具".format(count=self.tabs.count()))
        self._schedule_resize_to_current_tool()

    def _add_tool_tab(self, tool):
        try:
            module = importlib.import_module(tool["package"])
            factory = getattr(module, tool.get("entry", "create_widget"))
            widget = factory(parent=self.tabs, services=self.services)
            if not isinstance(widget, QtWidgets.QWidget):
                raise TypeError("工具入口没有返回 QWidget 实例")
            self._add_tab(widget, tool["name"])
        except Exception as exc:
            detail = traceback.format_exc()
            self.services.log(tool.get("id", "unknown"), str(exc), level="error")
            self._add_tab(self._error_page(tool, exc, detail), tool.get("name", "加载失败"))

    def _add_tab(self, widget, title):
        self._prepare_tool_widget(widget)
        self.tabs.addTab(widget, title)

    def _prepare_tool_widget(self, widget):
        widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        widget.setProperty(TOOL_PREFERRED_SIZE_PROPERTY, self._preferred_tool_size(widget, use_stored=False))
        widget.installEventFilter(self)

    def _schedule_resize_to_current_tool(self, *_args):
        if self._resize_to_tool_pending:
            return
        self._resize_to_tool_pending = True
        QtCore.QTimer.singleShot(0, self._resize_to_current_tool)

    def _resize_to_current_tool(self):
        self._resize_to_tool_pending = False
        if self._resizing_to_tool or self.isMaximized() or self.isFullScreen():
            return

        current_widget = self.tabs.currentWidget()
        if current_widget is None:
            return

        tool_size = self._preferred_tool_size(current_widget)
        target_size = self._target_window_size(current_widget, tool_size)
        if target_size == self.size():
            return

        self._resizing_to_tool = True
        try:
            self.resize(target_size)
        finally:
            self._resizing_to_tool = False

    def _preferred_tool_size(self, widget, use_stored=True):
        explicit_size = self._property_size(widget, EXTERNAL_TOOL_SIZE_PROPERTY)
        if explicit_size is not None:
            return explicit_size

        size_hint = widget.sizeHint()
        if self._is_reasonable_size(size_hint):
            return size_hint

        if use_stored:
            stored_size = self._property_size(widget, TOOL_PREFERRED_SIZE_PROPERTY)
            if stored_size is not None:
                return stored_size

        for size in (widget.minimumSizeHint(), widget.minimumSize(), widget.size()):
            if self._is_reasonable_size(size):
                return size

        return DEFAULT_TOOL_SIZE

    def _property_size(self, widget, name):
        value = widget.property(name)
        if isinstance(value, QtCore.QSize) and self._is_reasonable_size(value):
            return value
        return None

    def _is_reasonable_size(self, size):
        return (
            isinstance(size, QtCore.QSize)
            and size.isValid()
            and size.width() >= MIN_REASONABLE_TOOL_SIZE.width()
            and size.height() >= MIN_REASONABLE_TOOL_SIZE.height()
        )

    def _target_window_size(self, current_widget, tool_size):
        self.layout().activate()
        extra_width = max(0, self.width() - current_widget.width())
        extra_height = max(0, self.height() - current_widget.height())
        target_size = QtCore.QSize(tool_size.width() + extra_width, tool_size.height() + extra_height)
        target_size = target_size.expandedTo(MIN_WINDOW_SIZE)
        return self._fit_to_screen(target_size)

    def _fit_to_screen(self, size):
        screen = self.screen() or QtWidgets.QApplication.primaryScreen()
        if screen is None:
            return size

        available = screen.availableGeometry().size()
        max_size = QtCore.QSize(
            max(MIN_WINDOW_SIZE.width(), available.width() - SCREEN_MARGIN),
            max(MIN_WINDOW_SIZE.height(), available.height() - SCREEN_MARGIN),
        )
        return size.boundedTo(max_size)

    def _empty_page(self, message):
        page = QtWidgets.QWidget()
        page.setObjectName("mainEmptyPage")
        layout = QtWidgets.QVBoxLayout(page)
        label = QtWidgets.QLabel(message)
        label.setObjectName("emptyPageLabel")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)
        return page

    def _error_page(self, tool, exc, detail):
        page = QtWidgets.QWidget()
        page.setObjectName("mainErrorPage")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("{name} 加载失败".format(name=tool.get("name", "工具")))
        title.setObjectName("errorTitle")
        title_font = title.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)

        summary = QtWidgets.QLabel(str(exc))
        summary.setObjectName("errorSummary")
        summary.setWordWrap(True)

        detail_box = QtWidgets.QPlainTextEdit()
        detail_box.setObjectName("errorDetail")
        detail_box.setReadOnly(True)
        detail_box.setPlainText(detail)

        open_doc = QtWidgets.QPushButton("打开子工具文档")
        open_doc.setObjectName("openToolDocButton")
        open_doc.clicked.connect(lambda: self._open_tool_doc(tool))

        layout.addWidget(title)
        layout.addWidget(summary)
        layout.addWidget(detail_box, 1)
        layout.addWidget(open_doc, 0, QtCore.Qt.AlignLeft)
        return page

    def _open_tool_doc(self, tool):
        doc = ROOT_DIR / tool.get("doc", "")
        if doc.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(doc)))
        else:
            self.services.show_error("文档不存在", "未找到子工具文档：{path}".format(path=doc))

    def _show_about(self):
        self.services.show_info(
            "关于",
            "{app}\n\n运行环境：项目虚拟环境 py38\nGUI 技术栈：PyQt5".format(app=APP_NAME),
            parent=self,
        )


def main():
    QtCore.QCoreApplication.setOrganizationName("FPGA-tools")
    QtCore.QCoreApplication.setApplicationName(APP_NAME)
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
