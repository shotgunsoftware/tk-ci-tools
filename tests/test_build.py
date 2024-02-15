# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sys

from sgtk.platform.qt import QtGui


def test_qt():
    """
    Ensure we can show a Qt dialog on Azure-Pipelines and interact with it.
    """
    app = QtGui.QApplication(sys.argv)
    button = QtGui.QPushButton("Hello World")
    button.show()
    app.processEvents()
    button.close()
    app.processEvents()
