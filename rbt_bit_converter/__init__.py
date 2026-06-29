# -*- coding: utf-8 -*-

from .metadata import TOOL_ID, TOOL_NAME


def create_widget(parent=None, services=None):
    from .widget import RbtBitConverterWidget

    widget = RbtBitConverterWidget(parent=parent, services=services)
    widget.setWindowTitle(TOOL_NAME)
    return widget
