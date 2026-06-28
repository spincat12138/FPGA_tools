#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyQt5 GUI entry for usbtest_py.py."""

from __future__ import annotations

import sys

from PyQt5 import QtWidgets

try:
    from .widget import create_standalone_widget
except ImportError:  # pragma: no cover - supports direct script execution.
    from widget import create_standalone_widget


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    widget = create_standalone_widget()
    widget.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
