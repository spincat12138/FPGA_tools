# -*- coding: utf-8 -*-
from importlib import import_module

from PyQt5 import QtCore


TOOL_ID = "rbt2atp"
TOOL_NAME = "RBT转ATP"


def create_widget(parent=None, services=None):
    module = import_module(".RBT2ATP软件", __name__)
    widget = module.RBT2ATP(parent=parent)
    widget.setWindowFlags(QtCore.Qt.Widget)
    widget.setWindowTitle(TOOL_NAME)
    return widget
