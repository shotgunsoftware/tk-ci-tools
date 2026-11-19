# Copyright (c) 2026 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Static checks of the default test matrix in build-pipeline.yml.

Azure Pipelines expands the templates on its side, so these tests can't check
the expanded matrix. They catch mistakes in the default values instead.
"""

import os
import typing

import pytest
import yaml


def build_pipeline_default(name: str) -> typing.Any:
    """Return the default value of a build-pipeline.yml parameter."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "build-pipeline.yml"
    )
    with open(path, "r") as f:
        parameters = yaml.safe_load(f)["parameters"]
    for parameter in parameters:
        if parameter["name"] == name:
            return parameter["default"]
    raise RuntimeError(f"Parameter {name} not found in build-pipeline.yml")


@pytest.fixture(scope="module")
def os_versions() -> typing.List[typing.Dict[str, str]]:
    """Default operating systems of the test matrix."""
    return build_pipeline_default("os_versions")


@pytest.fixture(scope="module")
def python_versions() -> typing.List[typing.Dict[str, typing.Any]]:
    """Default Python versions of the test matrix."""
    return build_pipeline_default("python_versions")


def test_os_defaults_use_latest_images(
    os_versions: typing.List[typing.Dict[str, str]],
) -> None:
    """Every OS defaults to its -latest runner image."""
    assert [os_version["name"] for os_version in os_versions] == [
        "Linux",
        "macOS",
        "Windows",
    ]
    for os_version in os_versions:
        assert os_version["vm_image"].endswith("-latest"), os_version["name"]
        assert os_version["codecov_download_url"].startswith("https://")


def test_python_versions(
    python_versions: typing.List[typing.Dict[str, typing.Any]],
) -> None:
    """Every default Python version is quoted and has a Qt wrapper."""
    for python in python_versions:
        # An unquoted 3.10 would be loaded as the number 3.1.
        assert isinstance(python["python_version"], str), python
        assert python["qt_wrapper"], python["python_version"]


def test_image_overrides(
    os_versions: typing.List[typing.Dict[str, str]],
    python_versions: typing.List[typing.Dict[str, typing.Any]],
) -> None:
    """Overrides target a known OS and pin a specific image, or skip."""
    os_names = {os_version["name"] for os_version in os_versions}
    for python in python_versions:
        for os_name, vm_image in python.get("vm_images", {}).items():
            assert os_name in os_names, (python["python_version"], os_name)
            assert vm_image, (python["python_version"], os_name)
            # Overriding with a -latest image would be a no-op.
            assert not vm_image.endswith("-latest"), (
                python["python_version"],
                os_name,
            )
