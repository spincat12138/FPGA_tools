# -*- coding: utf-8 -*-

from .metadata import TOOL_ID, TOOL_NAME


def create_widget(parent=None, services=None):
    from .widget import Rbt2VcdWidget

    widget = Rbt2VcdWidget(parent=parent, services=services)
    widget.setWindowTitle(TOOL_NAME)
    return widget
