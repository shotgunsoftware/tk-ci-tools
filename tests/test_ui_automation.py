# Copyright (c) 2020 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

# This test is meant to be called from the command-line and not by pytest.
if __name__ == "__main__":
    import sys

    # Windows & Python 2.7 builds should be able to import
    # the automation code since it should have been cloned.
    if sys.platform == "win32":
        try:
            import MA.UI  # noqa
        except Exception as e:
            err_tuple = sys.exc_info()
            print(f"{err_tuple!r}")
    else:
        # Other platforms should not.
        try:
            import MA.UI  # noqa
        except ImportError:
            pass
