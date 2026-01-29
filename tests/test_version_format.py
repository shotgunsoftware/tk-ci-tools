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
import tempfile
import types
import typing

import pytest
import yaml


def test_valid(validate_version_format: types.ModuleType) -> None:
    """Test valid version formats."""
    assert validate_version_format.validate("v1.2.3")
    assert validate_version_format.validate("v12.34.56")
    assert validate_version_format.validate("v12.34.56-rc1")
    assert validate_version_format.validate("v12.34.56-beta1")


def test_invalid(validate_version_format: types.ModuleType) -> None:
    """Test invalid version formats."""
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


@pytest.fixture(scope="module")
def validate_version_format() -> typing.Generator[types.ModuleType, None, None]:
    """
    Pytest fixture that extracts the validation script from YAML and
    imports it as a module using a temporary file.
    The temporary directory and file are automatically cleaned up after
    tests complete. Uses current directory instead of system temp to
    avoid Windows permission issues.
    """
    # Extract the script content by display name
    script_content = extract_script_from_yaml("Validate Git tag version format")

    # Create a temporary directory in the current folder
    current_dir = os.path.dirname(__file__)

    # Use TemporaryDirectory for automatic cleanup
    with tempfile.TemporaryDirectory(
        prefix=".temp_test_scripts_",
        dir=current_dir,
    ) as temp_dir:
        # Create the script file in the temporary directory
        script_filename = "validate_version_format.py"
        temp_file_path = os.path.join(temp_dir, script_filename)

        # Write the script to the temporary file
        with open(temp_file_path, "w") as f:
            f.write(script_content)

        # Get the module name
        module_name = script_filename[:-3]  # Remove .py extension

        if temp_dir not in sys.path:
            sys.path.insert(0, temp_dir)

        try:
            # Import the module dynamically
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                module_name, temp_file_path
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            yield module

        finally:
            # Remove from sys.modules
            if module_name in sys.modules:
                del sys.modules[module_name]
        # Directory and all contents automatically deleted when exiting
        # the with block


def extract_script_from_yaml(display_name: str) -> str:
    """
    Extract the inline Python script from release.yml PythonScript@0 task
    by matching the displayName.
    This ensures we test the actual script that will run in CI.
    Unfortuantely, we cannot use the scriptPath parameter because it is not
    supported in the Azure Pipelines YAML file when using a template external
    repository. So exctracting the script from the YAML file was the next best
    option.

    This function is used to test the actual script that will run in CI.
    Args:
        display_name: The displayName of the PythonScript@0 task to extract

    Returns:
        str: The Python script content

    Raises:
        RuntimeError: If the task with the specified displayName is not found
    """
    yaml_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "internal",
        "release.yml",
    )

    with open(yaml_path, "r") as f:
        yaml_content = yaml.safe_load(f)

    # Navigate the YAML structure to find the PythonScript@0 task
    # Structure: jobs -> [job] -> steps -> [step with task: PythonScript@0]
    jobs = yaml_content.get("jobs", [])

    for job in jobs:
        steps = job.get("steps", [])
        for step in steps:
            # Check if this is a PythonScript@0 task with matching displayName
            if not isinstance(step, dict):
                continue

            if step.get("task") != "PythonScript@0":
                continue

            if step.get("displayName") != display_name:
                continue

            inputs = step.get("inputs", {})
            script_content = inputs.get("script")

            if not script_content:
                continue

            return script_content

    raise RuntimeError(
        f"Could not find PythonScript@0 task with displayName='{display_name}' "
        f"in release.yml"
    )
