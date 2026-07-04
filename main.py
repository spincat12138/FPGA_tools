# -*- coding: utf-8 -*-
import datetime
import importlib
import os
import sys
import traceback
from pathlib import Path

APP_NAME = "FPGA 工具集合"
LOG_DIR_NAME = "FPGA-tools"


def _startup_log_dir():
    candidates = [
        os.environ.get("LOCALAPPDATA"),
        os.environ.get("APPDATA"),
        os.environ.get("TEMP"),
    ]
    for base_dir in candidates:
        if not base_dir:
            continue
        try:
            log_dir = Path(base_dir) / LOG_DIR_NAME
            log_dir.mkdir(parents=True, exist_ok=True)
            return log_dir
        except OSError:
            continue
    return None


def _write_startup_error(title, detail):
    log_dir = _startup_log_dir()
    if log_dir is None:
        return None

    log_path = log_dir / "startup-error.log"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write("[{timestamp}] {title}\n".format(timestamp=timestamp, title=title))
            handle.write(detail.rstrip())
            handle.write("\n\n")
        return log_path
    except OSError:
        return None


def _startup_error_message(summary, log_path=None):
    message = summary
    if log_path is not None:
        message += "\n\n详细日志：{path}".format(path=log_path)
    return message


def _show_native_startup_error(title, summary, log_path=None):
    message = _startup_error_message(summary, log_path)
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    except Exception:
        sys.stderr.write("{title}\n{message}\n".format(title=title, message=message))


try:
    from PyQt5 import QtCore, QtGui, QtWidgets

    from common.services import ToolServices
    from tools_registry import TOOLS
except Exception:
    error_detail = traceback.format_exc()
    error_log_path = _write_startup_error("程序启动失败", error_detail)
    _show_native_startup_error(
        "程序启动失败",
        "程序启动时发生错误，可能是运行库、Qt 组件或打包依赖缺失。",
        error_log_path,
    )
    raise SystemExit(1)


def _show_qt_startup_error(title, summary, log_path=None):
    if QtWidgets.QApplication.instance() is None:
        _show_native_startup_error(title, summary, log_path)
        return

    message = _startup_error_message(summary, log_path)
    try:
        QtWidgets.QMessageBox.critical(None, title, message)
    except Exception:
        _show_native_startup_error(title, summary, log_path)


def _handle_unhandled_exception(exc_type, exc, tb):
    detail = "".join(traceback.format_exception(exc_type, exc, tb))
    log_path = _write_startup_error("程序发生未处理错误", detail)
    _show_qt_startup_error(
        "程序发生错误",
        "程序运行时发生未处理错误，已记录详细日志。",
        log_path,
    )


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_TOOL_SIZE = QtCore.QSize(900, 640)
MIN_REASONABLE_TOOL_SIZE = QtCore.QSize(120, 80)
MIN_WINDOW_SIZE = QtCore.QSize(480, 360)
SCREEN_MARGIN = 80
TOOL_PREFERRED_SIZE_PROPERTY = "_fpga_tools_preferred_size"
EXTERNAL_TOOL_SIZE_PROPERTY = "preferred_size"
SIDEBAR_EXPANDED_MIN_WIDTH = 210
SIDEBAR_EXPANDED_MAX_WIDTH = 260
NAV_ICON_SIZE = 24
NAV_ITEM_SIZE = QtCore.QSize(176, 46)
SIDEBAR_DECOR_HEIGHT = 234
SIDEBAR_DECOR_ASSET = ROOT_DIR / "common" / "assets" / "sidebar_chip_decor.png"
NAV_TITLE_ROLE = QtCore.Qt.UserRole + 1
NAV_TOOL_ID_ROLE = QtCore.Qt.UserRole + 2
NAV_ICON_ROLE = QtCore.Qt.UserRole + 3

TOOL_ICON_TYPES = {
    "rbt2atp": "bolt",
    "rbt_file_organization": "folder",
    "rbt_bit_converter": "swap",
    "rbt2vcd": "wave",
    "create_project": "wand",
    "config_board_v2": "chip",
    "generate_ucf": "file",
}


def _stroke_icon(icon_type, color, size=NAV_ICON_SIZE):
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    pen = QtGui.QPen(QtGui.QColor(color), 2.0, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QtCore.Qt.NoBrush)

    if icon_type == "bolt":
        path = QtGui.QPainterPath()
        path.moveTo(13, 2.5)
        path.lineTo(5.5, 13)
        path.lineTo(12, 13)
        path.lineTo(10, 21.5)
        path.lineTo(18.8, 9.6)
        path.lineTo(12.4, 9.6)
        path.closeSubpath()
        painter.drawPath(path)
    elif icon_type == "folder":
        path = QtGui.QPainterPath()
        path.moveTo(3, 7)
        path.lineTo(9, 7)
        path.lineTo(11, 9.3)
        path.lineTo(21, 9.3)
        path.lineTo(21, 20)
        path.lineTo(3, 20)
        path.closeSubpath()
        painter.drawPath(path)
    elif icon_type == "swap":
        painter.drawLine(5, 8, 18, 8)
        painter.drawLine(15, 5, 19, 8)
        painter.drawLine(15, 11, 19, 8)
        painter.drawLine(19, 16, 6, 16)
        painter.drawLine(9, 13, 5, 16)
        painter.drawLine(9, 19, 5, 16)
    elif icon_type == "wave":
        painter.drawRoundedRect(QtCore.QRectF(4, 5, 16, 14), 2, 2)
        path = QtGui.QPainterPath()
        path.moveTo(6.5, 14)
        path.lineTo(9, 14)
        path.lineTo(10.5, 10)
        path.lineTo(13.5, 17)
        path.lineTo(15, 12)
        path.lineTo(18, 12)
        painter.drawPath(path)
    elif icon_type == "wand":
        painter.drawLine(6, 18, 18, 6)
        painter.drawLine(15, 4, 20, 9)
        painter.drawLine(4, 7, 7, 7)
        painter.drawLine(QtCore.QPointF(5.5, 5.5), QtCore.QPointF(5.5, 8.5))
        painter.drawLine(16, 18, 20, 18)
        painter.drawLine(18, 16, 18, 20)
    elif icon_type == "chip":
        painter.drawRoundedRect(QtCore.QRectF(7, 7, 10, 10), 1.8, 1.8)
        painter.drawRoundedRect(QtCore.QRectF(10, 10, 4, 4), 0.8, 0.8)
        for pos in (5, 19):
            painter.drawLine(pos, 9, pos, 9)
            painter.drawLine(pos, 12, pos, 12)
            painter.drawLine(pos, 15, pos, 15)
            painter.drawLine(9, pos, 9, pos)
            painter.drawLine(12, pos, 12, pos)
            painter.drawLine(15, pos, 15, pos)
        painter.drawLine(3, 9, 7, 9)
        painter.drawLine(3, 12, 7, 12)
        painter.drawLine(3, 15, 7, 15)
        painter.drawLine(17, 9, 21, 9)
        painter.drawLine(17, 12, 21, 12)
        painter.drawLine(17, 15, 21, 15)
        painter.drawLine(9, 3, 9, 7)
        painter.drawLine(12, 3, 12, 7)
        painter.drawLine(15, 3, 15, 7)
        painter.drawLine(9, 17, 9, 21)
        painter.drawLine(12, 17, 12, 21)
        painter.drawLine(15, 17, 15, 21)
    elif icon_type == "file":
        path = QtGui.QPainterPath()
        path.moveTo(7, 3.5)
        path.lineTo(15, 3.5)
        path.lineTo(20, 8.5)
        path.lineTo(20, 20.5)
        path.lineTo(7, 20.5)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QtCore.QPointF(15, 3.5), QtCore.QPointF(15, 9))
        painter.drawLine(15, 9, 20, 9)
        painter.drawLine(10, 13, 17, 13)
        painter.drawLine(QtCore.QPointF(10, 16.5), QtCore.QPointF(15, 16.5))
    else:
        painter.drawRoundedRect(QtCore.QRectF(5, 5, 14, 14), 3, 3)

    painter.end()
    return QtGui.QIcon(pixmap)


def _nav_icon(icon_type, active=False):
    return _stroke_icon(icon_type, "#ffffff" if active else "#2f7df6")


def _info_icon():
    pixmap = QtGui.QPixmap(18, 18)
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setPen(QtCore.Qt.NoPen)
    painter.setBrush(QtGui.QColor("#8b95a1"))
    painter.drawEllipse(QtCore.QRectF(1, 1, 16, 16))
    painter.setPen(QtGui.QPen(QtGui.QColor("#ffffff"), 1.8))
    painter.drawLine(9, 8, 9, 13)
    painter.drawPoint(9, 5)
    painter.end()
    return QtGui.QIcon(pixmap)


class SidebarDecor(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarDecor")
        self.setFixedHeight(SIDEBAR_DECOR_HEIGHT)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self._pixmap = QtGui.QPixmap(str(SIDEBAR_DECOR_ASSET))

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        if not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                width,
                height,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
            x = int((width - scaled.width()) / 2)
            y = height - scaled.height()
            painter.drawPixmap(x, y, scaled)
            painter.end()
            return

        painter.setPen(QtCore.Qt.NoPen)

        glow = QtGui.QRadialGradient(QtCore.QPointF(width * 0.40, height * 0.80), height * 0.64)
        glow.setColorAt(0.0, QtGui.QColor(72, 150, 255, 58))
        glow.setColorAt(0.52, QtGui.QColor(98, 179, 255, 26))
        glow.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))
        painter.setBrush(glow)
        painter.drawEllipse(QtCore.QRectF(-width * 0.10, height * 0.34, width * 1.08, height * 0.64))

        trace_pen = QtGui.QPen(QtGui.QColor(90, 167, 255, 42), 1.0)
        trace_pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(trace_pen)
        painter.setBrush(QtGui.QColor(111, 181, 255, 52))
        points = [
            (width * 0.34, height * 0.62, width * 0.22, height * 0.48),
            (width * 0.58, height * 0.61, width * 0.72, height * 0.46),
            (width * 0.43, height * 0.47, width * 0.50, height * 0.35),
        ]
        for x1, y1, x2, y2 in points:
            painter.drawLine(QtCore.QPointF(x1, y1), QtCore.QPointF(x2, y2))
            painter.drawEllipse(QtCore.QPointF(x2, y2), 2.2, 2.2)

        block_top = QtGui.QPolygonF([
            QtCore.QPointF(width * 0.62, height * 0.53),
            QtCore.QPointF(width * 0.80, height * 0.61),
            QtCore.QPointF(width * 0.64, height * 0.69),
            QtCore.QPointF(width * 0.46, height * 0.60),
        ])
        block_right = QtGui.QPolygonF([
            QtCore.QPointF(width * 0.80, height * 0.61),
            QtCore.QPointF(width * 0.80, height * 0.79),
            QtCore.QPointF(width * 0.64, height * 0.87),
            QtCore.QPointF(width * 0.64, height * 0.69),
        ])
        block_left = QtGui.QPolygonF([
            QtCore.QPointF(width * 0.46, height * 0.60),
            QtCore.QPointF(width * 0.64, height * 0.69),
            QtCore.QPointF(width * 0.64, height * 0.87),
            QtCore.QPointF(width * 0.46, height * 0.78),
        ])
        painter.setPen(QtGui.QPen(QtGui.QColor(89, 158, 246, 28), 1.0))
        painter.setBrush(QtGui.QColor(239, 247, 255, 76))
        painter.drawPolygon(block_top)
        painter.setBrush(QtGui.QColor(218, 237, 255, 42))
        painter.drawPolygon(block_right)
        painter.setBrush(QtGui.QColor(226, 242, 255, 54))
        painter.drawPolygon(block_left)

        board_top = QtGui.QPolygonF([
            QtCore.QPointF(width * 0.30, height * 0.72),
            QtCore.QPointF(width * 0.51, height * 0.62),
            QtCore.QPointF(width * 0.73, height * 0.75),
            QtCore.QPointF(width * 0.50, height * 0.88),
        ])
        board_side = QtGui.QPolygonF([
            QtCore.QPointF(width * 0.30, height * 0.72),
            QtCore.QPointF(width * 0.50, height * 0.88),
            QtCore.QPointF(width * 0.50, height * 0.93),
            QtCore.QPointF(width * 0.30, height * 0.78),
        ])
        board_right = QtGui.QPolygonF([
            QtCore.QPointF(width * 0.50, height * 0.88),
            QtCore.QPointF(width * 0.73, height * 0.75),
            QtCore.QPointF(width * 0.73, height * 0.80),
            QtCore.QPointF(width * 0.50, height * 0.93),
        ])
        painter.setPen(QtGui.QPen(QtGui.QColor(92, 159, 247, 74), 1.0))
        painter.setBrush(QtGui.QColor(244, 250, 255, 190))
        painter.drawPolygon(board_top)
        painter.setBrush(QtGui.QColor(211, 233, 255, 84))
        painter.drawPolygon(board_side)
        painter.setBrush(QtGui.QColor(190, 221, 255, 88))
        painter.drawPolygon(board_right)

        chip = QtGui.QPolygonF([
            QtCore.QPointF(width * 0.42, height * 0.75),
            QtCore.QPointF(width * 0.52, height * 0.70),
            QtCore.QPointF(width * 0.63, height * 0.76),
            QtCore.QPointF(width * 0.52, height * 0.82),
        ])
        painter.setPen(QtGui.QPen(QtGui.QColor(56, 137, 245, 170), 2.2))
        painter.setBrush(QtGui.QColor(232, 244, 255, 190))
        painter.drawPolygon(chip)

        painter.setPen(QtGui.QPen(QtGui.QColor(96, 166, 255, 90), 1.0))
        for start, end in [
            ((0.39, 0.74), (0.33, 0.71)),
            ((0.43, 0.82), (0.37, 0.86)),
            ((0.62, 0.74), (0.69, 0.71)),
            ((0.61, 0.81), (0.68, 0.84)),
        ]:
            painter.drawLine(
                QtCore.QPointF(width * start[0], height * start[1]),
                QtCore.QPointF(width * end[0], height * end[1]),
            )

        painter.end()



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

        self.shell = QtWidgets.QWidget()
        self.shell.setObjectName("mainShell")

        shell_layout = QtWidgets.QHBoxLayout(self.shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        self.sidebar = QtWidgets.QFrame()
        self.sidebar.setObjectName("toolSidebar")
        self.sidebar.setMinimumWidth(SIDEBAR_EXPANDED_MIN_WIDTH)
        self.sidebar.setMaximumWidth(SIDEBAR_EXPANDED_MAX_WIDTH)

        sidebar_layout = QtWidgets.QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(14)

        sidebar_header_widget = QtWidgets.QWidget()
        sidebar_header_widget.setObjectName("sidebarHeader")
        sidebar_header_widget.setAutoFillBackground(False)
        self.sidebar_header_widget = sidebar_header_widget
        sidebar_header_layout = QtWidgets.QVBoxLayout(sidebar_header_widget)
        sidebar_header_layout.setContentsMargins(20, 34, 18, 0)
        sidebar_header_layout.setSpacing(0)

        sidebar_header = QtWidgets.QHBoxLayout()
        sidebar_header.setContentsMargins(0, 0, 0, 0)
        sidebar_header.setSpacing(10)

        self.sidebar_logo = QtWidgets.QLabel()
        self.sidebar_logo.setObjectName("sidebarLogo")
        self.sidebar_logo.setPixmap(_stroke_icon("chip", "#2f7df6", 30).pixmap(30, 30))
        self.sidebar_logo.setFixedSize(36, 36)
        self.sidebar_logo.setAlignment(QtCore.Qt.AlignCenter)
        sidebar_header.addWidget(self.sidebar_logo, 0, QtCore.Qt.AlignTop)

        sidebar_text_layout = QtWidgets.QVBoxLayout()
        sidebar_text_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_text_layout.setSpacing(2)

        self.sidebar_title = QtWidgets.QLabel(APP_NAME)
        self.sidebar_title.setObjectName("sidebarTitle")
        sidebar_text_layout.addWidget(self.sidebar_title)

        self.sidebar_subtitle = QtWidgets.QLabel("高效 · 便捷 · 专业")
        self.sidebar_subtitle.setObjectName("sidebarSubtitle")
        sidebar_text_layout.addWidget(self.sidebar_subtitle)
        sidebar_header.addLayout(sidebar_text_layout, 1)

        sidebar_header_layout.addLayout(sidebar_header)
        sidebar_layout.addWidget(sidebar_header_widget)

        navigation_widget = QtWidgets.QWidget()
        navigation_widget.setObjectName("sidebarNavigationWrap")
        navigation_widget.setAutoFillBackground(False)
        self.navigation_widget = navigation_widget
        navigation_layout = QtWidgets.QVBoxLayout(navigation_widget)
        navigation_layout.setContentsMargins(20, 0, 18, 0)
        navigation_layout.setSpacing(0)
        self.navigation_layout = navigation_layout

        self.navigation = QtWidgets.QListWidget()
        self.navigation.setObjectName("toolNavigation")
        self.navigation.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.navigation.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.navigation.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.navigation.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.navigation.setIconSize(QtCore.QSize(NAV_ICON_SIZE, NAV_ICON_SIZE))
        self.navigation.viewport().setAutoFillBackground(False)
        self.navigation.currentRowChanged.connect(self._on_navigation_changed)
        navigation_layout.addWidget(self.navigation)
        sidebar_layout.addWidget(navigation_widget, 1)

        self.sidebar_decor = SidebarDecor()
        sidebar_layout.addWidget(self.sidebar_decor)

        footer_widget = QtWidgets.QWidget()
        footer_widget.setObjectName("sidebarFooter")
        footer_widget.setAutoFillBackground(False)
        self.footer_widget = footer_widget
        footer_layout_wrapper = QtWidgets.QVBoxLayout(footer_widget)
        footer_layout_wrapper.setContentsMargins(20, 0, 18, 14)
        footer_layout_wrapper.setSpacing(0)

        footer_layout = QtWidgets.QHBoxLayout()
        footer_layout.setContentsMargins(4, 0, 0, 0)
        footer_layout.setSpacing(8)

        self.sidebar_status_icon = QtWidgets.QLabel()
        self.sidebar_status_icon.setObjectName("sidebarStatusIcon")
        self.sidebar_status_icon.setPixmap(_info_icon().pixmap(18, 18))
        self.sidebar_status_icon.setFixedSize(18, 18)
        footer_layout.addWidget(self.sidebar_status_icon)

        self.sidebar_status = QtWidgets.QLabel("正在加载工具")
        self.sidebar_status.setObjectName("sidebarStatus")
        footer_layout.addWidget(self.sidebar_status, 1)
        footer_layout_wrapper.addLayout(footer_layout)
        sidebar_layout.addWidget(footer_widget)

        self.pages = QtWidgets.QStackedWidget()
        self.pages.setObjectName("toolPages")

        shell_layout.addWidget(self.sidebar)
        shell_layout.addWidget(self.pages, 1)
        self.setCentralWidget(self.shell)

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
        if watched is self.pages.currentWidget() and event.type() in resize_events:
            self._schedule_resize_to_current_tool()
        return super().eventFilter(watched, event)

    def _on_navigation_changed(self, row):
        if row < 0 or row >= self.pages.count():
            return
        self.pages.setCurrentIndex(row)
        self._sync_navigation_labels()
        self._schedule_resize_to_current_tool()

    def _sync_navigation_labels(self):
        current_row = self.navigation.currentRow()
        for row in range(self.navigation.count()):
            item = self.navigation.item(row)
            title = item.data(NAV_TITLE_ROLE) or item.text()
            icon_type = item.data(NAV_ICON_ROLE) or "default"
            item.setToolTip(title)
            item.setIcon(_nav_icon(icon_type, active=row == current_row))
            item.setText(title)
            item.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
            item.setSizeHint(NAV_ITEM_SIZE)

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


            QWidget#mainShell {
            background-color: #f8fbff;
            }


            QFrame#toolSidebar {
            background-color: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #ffffff,
                stop: 0.46 #f8fbff,
                stop: 1 #e7f3ff
            );
            border-right: 1px solid #dfe8f5;
            }


            QWidget#sidebarHeader,
            QWidget#sidebarNavigationWrap,
            QWidget#sidebarFooter,
            QWidget#sidebarDecor {
            background-color: transparent;
            }


            QLabel#sidebarLogo {
            background-color: #eff6ff;
            border: 1px solid #d8e8ff;
            border-radius: 6px;
            }


            QLabel#sidebarTitle {
            color: #10233f;
            font-size: 17px;
            font-weight: bold;
            padding: 0;
            }


            QLabel#sidebarSubtitle {
            color: #7c8da5;
            font-size: 11px;
            padding: 0;
            }


            QLabel#sidebarStatus {
            color: #4a5568;
            font-size: 12px;
            font-weight: bold;
            padding: 0;
            }


            QListWidget#toolNavigation {
            background-color: transparent;
            color: #10233f;
            border: 0;
            outline: 0;
            }


            QListWidget#toolNavigation::item {
            border-radius: 6px;
            padding: 7px 10px 7px 14px;
            margin: 4px 0;
            min-height: 32px;
            }


            QListWidget#toolNavigation::item:hover:!selected {
            background-color: rgba(232, 242, 255, 190);
            color: #1f6fe5;
            }


            QListWidget#toolNavigation::item:selected {
            background-color: #2f7df6;
            color: #ffffff;
            font-weight: bold;
            }


            QStackedWidget#toolPages {
            background-color: #f8fbff;
            }


            QStatusBar#mainStatusBar {
            background-color: #f9fcff;
            border-top: 1px solid #dfe8f5;
            color: #64748b;
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
        self.navigation.clear()
        self._clear_pages()
        enabled_tools = [tool for tool in TOOLS if tool.get("enabled", True)]
        if not enabled_tools:
            self._add_tool_page(self._empty_page("暂无已启用工具"), "空")
            self.navigation.setCurrentRow(0)
            self.sidebar_status.setText("暂无已启用工具")
            self.statusBar().showMessage("暂无已启用工具")
            self._schedule_resize_to_current_tool()
            return

        for tool in enabled_tools:
            self._add_registered_tool(tool)

        if self.pages.count():
            self.navigation.setCurrentRow(0)

        status_message = "已加载 {count} 个工具".format(count=self.pages.count())
        self.sidebar_status.setText(status_message)
        self.statusBar().showMessage(status_message)
        self._schedule_resize_to_current_tool()

    def _clear_pages(self):
        while self.pages.count():
            widget = self.pages.widget(0)
            self.pages.removeWidget(widget)
            widget.deleteLater()

    def _add_registered_tool(self, tool):
        try:
            module = importlib.import_module(tool["package"])
            factory = getattr(module, tool.get("entry", "create_widget"))
            widget = factory(parent=self.pages, services=self.services)
            if not isinstance(widget, QtWidgets.QWidget):
                raise TypeError("工具入口没有返回 QWidget 实例")
            self._add_tool_page(widget, tool["name"], tool.get("id"))
        except Exception as exc:
            detail = traceback.format_exc()
            self.services.log(tool.get("id", "unknown"), str(exc), level="error")
            self._add_tool_page(self._error_page(tool, exc, detail), tool.get("name", "加载失败"), tool.get("id"))

    def _add_tool_page(self, widget, title, tool_id=None):
        self._prepare_tool_widget(widget)
        item = QtWidgets.QListWidgetItem(title)
        item.setToolTip(title)
        item.setData(NAV_TITLE_ROLE, title)
        if tool_id:
            item.setData(NAV_TOOL_ID_ROLE, tool_id)
        item.setData(NAV_ICON_ROLE, TOOL_ICON_TYPES.get(tool_id, "default"))
        item.setIcon(_nav_icon(item.data(NAV_ICON_ROLE)))
        item.setSizeHint(NAV_ITEM_SIZE)
        self.navigation.addItem(item)
        self.pages.addWidget(widget)
        self._sync_navigation_labels()

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

        current_widget = self.pages.currentWidget()
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
    sys.excepthook = _handle_unhandled_exception
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        error_detail = traceback.format_exc()
        error_log_path = _write_startup_error("程序启动失败", error_detail)
        _show_qt_startup_error(
            "程序启动失败",
            "程序启动时发生错误，已记录详细日志。",
            error_log_path,
        )
        sys.exit(1)
