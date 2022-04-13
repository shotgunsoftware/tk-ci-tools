# Copyright (c) 2020 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sys
import subprocess
import os

# This test is meant to be called from the command-line and not by pytest.
# The ssh key to clone repos has been installed only for Python2.7+Windows,
# so this is the only circumstance for which we can test cloning the repo.
# Unfortunately we can't just install the ssh key before running this test
# because it has already been installed once of the Windows+2.7 build and the
# task will fail if you install it a second time.
if __name__ == "__main__" and sys.platform == "win32":
    try:
        subprocess.check_call(
            [
                "git",
                "clone",
                "--depth",
                "1",
                os.path.expandvars("git@github.com:${RELEASE_REPO}"),
                "../release_scripts",
            ]
        )
    except subprocess.CalledProcessError:
        # Catch the error so we don't leak the repository location when running the tests.
        sys.exit(1)
