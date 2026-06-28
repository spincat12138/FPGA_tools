# -*- coding: utf-8 -*-

from .widget import CreateProjectWidget, TOOL_ID, TOOL_NAME


def create_widget(parent=None, services=None):
    widget = CreateProjectWidget(parent=parent, services=services)
    widget.setWindowTitle(TOOL_NAME)
    return widget
