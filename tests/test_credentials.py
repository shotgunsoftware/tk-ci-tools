# Copyright (c) 2020 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from tk_toolchain.authentication import get_toolkit_user

# This test is meant to be called from the command-line and not by pytest.
if __name__ == "__main__":
    # This ensures that tk-toolchain was able to build credentials that are valid.
    # Hit the server just to make sure the credentials are all good.
    get_toolkit_user().create_sg_connection().find_one("HumanUser", [])
