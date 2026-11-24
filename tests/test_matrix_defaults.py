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
Static checks of the default test matrix in internal/run-tests.yml.

Azure Pipelines expands the templates on its side, so these tests can't check
the expanded matrix. They catch mistakes in the default values instead.
"""

import os
import typing

import pytest
import yaml


@pytest.fixture(scope="module")
def run_tests_parameters() -> typing.Dict[str, typing.Any]:
    """Default parameters of internal/run-tests.yml."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "internal", "run-tests.yml"
    )
    with open(path, "r") as f:
        return yaml.safe_load(f)["parameters"]


def test_platforms(run_tests_parameters: typing.Dict[str, typing.Any]) -> None:
    """Every platform has a quoted Python version, a Qt wrapper and valid overrides."""
    os_names = {
        os_version["name"] for os_version in run_tests_parameters["os_versions"]
    }
    for platform in run_tests_parameters["platforms"]:
        # An unquoted 3.10 would be loaded as the number 3.1.
        assert isinstance(platform["python_version"], str), platform["name"]
        assert platform["qt_wrapper"], platform["name"]
        overrides = platform.get("os_versions", {})
        # An unknown OS name would be silently ignored.
        assert set(overrides) <= os_names, platform["name"]
        assert all(overrides.values()), platform["name"]


def test_os_versions(run_tests_parameters: typing.Dict[str, typing.Any]) -> None:
    """Every OS defaults to its -latest image and has a Codecov uploader."""
    assert [
        os_version["name"] for os_version in run_tests_parameters["os_versions"]
    ] == ["Linux", "macOS", "Windows"]
    for os_version in run_tests_parameters["os_versions"]:
        assert os_version["image"].endswith("-latest"), os_version["name"]
        assert os_version["codecov_download_url"].startswith("https://")


def test_coverage_is_on_by_default(run_tests_parameters) -> None:
    """Toolkit repositories keep measuring and uploading their coverage."""
    assert run_tests_parameters["coverage"] is True
