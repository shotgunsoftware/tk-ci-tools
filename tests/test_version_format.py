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
import sys

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "internal",
    ),
)

import validate_version_format


def test_valid():
    assert validate_version_format.validate("v1.2.3")
    assert validate_version_format.validate("v12.34.56")
    assert validate_version_format.validate("v12.34.56-rc1")
    assert validate_version_format.validate("v12.34.56-beta1")


def test_invalid():
    assert not validate_version_format.validate("")
    assert not validate_version_format.validate("v")
    assert not validate_version_format.validate("v1")
    assert not validate_version_format.validate("v1.")
    assert not validate_version_format.validate("v1.2")
    assert not validate_version_format.validate("v1.2.")
    assert not validate_version_format.validate("v1.2.3.")

    assert not validate_version_format.validate("v.1.2.3")
    assert not validate_version_format.validate("a1.2.3")
    assert not validate_version_format.validate("b")
