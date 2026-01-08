# Copyright (c) 2025 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import re


def validate(version: str) -> bool:
    return (
        re.match(
            "^v\\d+\\.\\d+\\.\\d+(-[\\w\\d-]+)?$",
            version,
        )
        is not None
    )


if __name__ == "__main__":
    git_ref = os.environ["BUILD_SOURCEBRANCH"]
    assert git_ref.startswith("refs/tags/")
    assert validate(git_ref[10:])
