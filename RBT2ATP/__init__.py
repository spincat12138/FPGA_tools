# -*- coding: utf-8 -*-
from PyQt5 import QtCore

from .rbt2atp_gui import RBT2ATP


TOOL_ID = "rbt2atp"
TOOL_NAME = "RBT转ATP"


def create_widget(parent=None, services=None):
    widget = RBT2ATP(parent=parent)
    widget.setWindowFlags(QtCore.Qt.Widget)
    widget.setWindowTitle(TOOL_NAME)
    return widget
