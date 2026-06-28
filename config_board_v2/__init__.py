# -*- coding: utf-8 -*-

from .widget import ConfigBoardWidget, TOOL_ID, TOOL_NAME


def create_widget(parent=None, services=None):
    widget = ConfigBoardWidget(parent=parent, services=services)
    widget.setWindowTitle(TOOL_NAME)
    return widget
