# Copyright (c) 2026 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import importlib.util
import os
import pathlib
import shutil
import struct
import types
import typing
import zlib

import pytest
import yaml

TEST_IMAGES_DIR = os.path.join(os.path.dirname(__file__), "test_images")
GOOD_PROFILE_PNG = os.path.join(TEST_IMAGES_DIR, "good_profile.png")
WRONG_PROFILE_PNG = os.path.join(TEST_IMAGES_DIR, "wrong_profile.png")

# Offset of the rendering intent in the ICC profile header.
ICC_INTENT_OFFSET = 67


def test_good_profile(checker: types.ModuleType) -> None:
    """good_profile.png has no iCCP chunk and passes."""
    assert checker.check_png(GOOD_PROFILE_PNG) is None


def test_known_incorrect_media_relative(checker: types.ModuleType) -> None:
    """wrong_profile.png embeds the HP-Microsoft sRGB v2 media-relative profile."""
    assert checker.check_png(WRONG_PROFILE_PNG) == "iCCP: known incorrect sRGB profile"


def test_known_incorrect_perceptual(
    checker: types.ModuleType, tmp_path: pathlib.Path
) -> None:
    """The HP-Microsoft sRGB v2 perceptual variant only differs by its intent."""
    path = tmp_path / "perceptual.png"
    path.write_bytes(with_profile_intent(read_png(WRONG_PROFILE_PNG), 0))
    assert checker.check_png(str(path)) == "iCCP: known incorrect sRGB profile"


def test_unknown_profile(checker: types.ModuleType, tmp_path: pathlib.Path) -> None:
    """A valid profile that is not in the known-incorrect list passes."""
    path = tmp_path / "unknown.png"
    path.write_bytes(with_profile_intent(read_png(WRONG_PROFILE_PNG), 2))
    assert checker.check_png(str(path)) is None


def test_large_profile(checker: types.ModuleType, tmp_path: pathlib.Path) -> None:
    """A valid profile larger than the known ones passes."""
    compressed = zlib.compress(bytes(range(256)) * 400)
    path = tmp_path / "large.png"
    path.write_bytes(with_compressed_profile(read_png(WRONG_PROFILE_PNG), compressed))
    assert checker.check_png(str(path)) is None


def test_huge_profile(checker: types.ModuleType, tmp_path: pathlib.Path) -> None:
    """A profile inflating past libpng's 8 MB limit is reported."""
    compressor = zlib.compressobj()
    chunk = b"\x00" * (1 << 20)
    compressed = b"".join(compressor.compress(chunk) for _ in range(64))
    compressed += compressor.flush()
    path = tmp_path / "huge.png"
    path.write_bytes(with_compressed_profile(read_png(WRONG_PROFILE_PNG), compressed))
    assert checker.check_png(str(path)) == "iCCP: profile exceeds 8000000 bytes"


def test_corrupt_profile(checker: types.ModuleType, tmp_path: pathlib.Path) -> None:
    """Garbage instead of a zlib stream is reported as corrupt."""
    path = tmp_path / "corrupt.png"
    path.write_bytes(
        replace_iccp_chunk(read_png(WRONG_PROFILE_PNG), b"name\x00\x00garbage")
    )
    assert checker.check_png(str(path)).startswith("iCCP: corrupt profile")


def test_truncated_profile(checker: types.ModuleType, tmp_path: pathlib.Path) -> None:
    """A profile stream cut short is reported as corrupt."""
    data = read_png(WRONG_PROFILE_PNG)
    _, _, body = find_iccp_chunk(data)
    path = tmp_path / "truncated.png"
    path.write_bytes(replace_iccp_chunk(data, body[: len(body) // 2]))
    assert checker.check_png(str(path)) == "iCCP: corrupt profile: truncated stream"


def test_truncated_oversized_profile(
    checker: types.ModuleType, tmp_path: pathlib.Path
) -> None:
    """A profile larger than the known ones missing its zlib checksum is corrupt."""
    # Drop the trailing adler32 so the stream inflates fully but never ends.
    compressed = zlib.compress(bytes(range(256)) * 16)[:-4]
    path = tmp_path / "truncated_oversized.png"
    path.write_bytes(with_compressed_profile(read_png(WRONG_PROFILE_PNG), compressed))
    assert checker.check_png(str(path)) == "iCCP: corrupt profile: truncated stream"


def test_not_a_png(checker: types.ModuleType, tmp_path: pathlib.Path) -> None:
    """A file that is not a PNG is reported."""
    path = tmp_path / "fake.png"
    path.write_bytes(b"not a png")
    assert checker.check_png(str(path)) == "not a PNG file"


def test_find_pngs(checker: types.ModuleType, tmp_path: pathlib.Path) -> None:
    """PNG files are found recursively, whatever the extension case."""
    (tmp_path / "nested").mkdir()
    for name in ("a.png", "nested/b.PNG", "c.txt"):
        (tmp_path / name).write_bytes(b"")
    found = [os.path.relpath(p, tmp_path) for p in checker.find_pngs(str(tmp_path))]
    assert found == ["a.png", os.path.join("nested", "b.PNG")]


def test_main_valid_resources(
    checker: types.ModuleType, agent: pathlib.Path, capsys: pytest.CaptureFixture
) -> None:
    """The job passes when the resources have no incorrect profiles."""
    shutil.copy(GOOD_PROFILE_PNG, agent / "sources" / "resources" / "icon.png")
    checker.main()
    assert "All PNG profiles are valid." in capsys.readouterr().out


def test_main_no_resources(checker: types.ModuleType, agent: pathlib.Path) -> None:
    """A resources folder without PNG files passes."""
    checker.main()


def test_main_incorrect_resources(
    checker: types.ModuleType, agent: pathlib.Path, capsys: pytest.CaptureFixture
) -> None:
    """Every incorrect PNG in the resources is reported and fails the job."""
    resources = agent / "sources" / "resources"
    (resources / "nested").mkdir()
    shutil.copy(GOOD_PROFILE_PNG, resources / "good.png")
    shutil.copy(WRONG_PROFILE_PNG, resources / "wrong.png")
    shutil.copy(WRONG_PROFILE_PNG, resources / "nested" / "wrong.PNG")
    with pytest.raises(SystemExit) as exc_info:
        checker.main()
    assert "2 PNG file(s) have profile errors" in str(exc_info.value)
    output = capsys.readouterr().out
    assert "wrong.png: iCCP: known incorrect sRGB profile" in output
    assert "good.png" not in output


def test_main_self_test_valid_image_fails(
    checker: types.ModuleType, agent: pathlib.Path
) -> None:
    """The job fails if the checker flags the good test image."""
    images = agent / "tk-ci-tools" / "tests" / "test_images"
    shutil.copy(WRONG_PROFILE_PNG, images / "good_profile.png")
    with pytest.raises(SystemExit) as exc_info:
        checker.main()
    assert "good_profile.png expected to be valid" in str(exc_info.value)


def test_main_self_test_invalid_image_fails(
    checker: types.ModuleType, agent: pathlib.Path
) -> None:
    """The job fails if the checker misses the wrong test image."""
    images = agent / "tk-ci-tools" / "tests" / "test_images"
    shutil.copy(GOOD_PROFILE_PNG, images / "wrong_profile.png")
    with pytest.raises(SystemExit) as exc_info:
        checker.main()
    assert "wrong_profile.png expected to be invalid" in str(exc_info.value)


def test_main_in_tk_ci_tools(
    checker: types.ModuleType,
    agent: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In tk-ci-tools itself the test images come from the sources directory."""
    sources = agent / "tk-ci-tools"
    (sources / "resources").mkdir()
    monkeypatch.setenv("BUILD_SOURCESDIRECTORY", str(sources))
    monkeypatch.setenv("BUILD_REPOSITORY_NAME", "shotgunsoftware/tk-ci-tools")
    checker.main()


@pytest.fixture
def agent(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """
    Lay out the directories of a pipeline run on another repository: the sources
    with a resources folder next to a tk-ci-tools clone with the test images.
    """
    (tmp_path / "sources" / "resources").mkdir(parents=True)
    images = tmp_path / "tk-ci-tools" / "tests" / "test_images"
    images.mkdir(parents=True)
    shutil.copy(GOOD_PROFILE_PNG, images)
    shutil.copy(WRONG_PROFILE_PNG, images)
    monkeypatch.setenv("BUILD_SOURCESDIRECTORY", str(tmp_path / "sources"))
    monkeypatch.setenv("BUILD_REPOSITORY_NAME", "shotgunsoftware/tk-multi-testing")
    return tmp_path


@pytest.fixture(scope="module")
def checker(
    tmp_path_factory: pytest.TempPathFactory,
) -> typing.Generator[types.ModuleType, None, None]:
    """Import the PNG profile checker extracted from the pipeline YAML."""
    path = tmp_path_factory.mktemp("checker") / "check_png_profile.py"
    path.write_text(extract_script_from_yaml("Validate PNG profiles"))
    spec = importlib.util.spec_from_file_location("check_png_profile", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    yield module


def extract_script_from_yaml(display_name: str) -> str:
    """
    Extract the inline Python script of a PythonScript@0 task from
    resources-validation.yml so we test the exact code that runs in CI.
    """
    yaml_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "internal",
        "resources-validation.yml",
    )
    with open(yaml_path, "r") as f:
        yaml_content = yaml.safe_load(f)

    for job in yaml_content.get("jobs", []):
        for step in job.get("steps", []):
            if step.get("task") == "PythonScript@0" and (
                step.get("displayName") == display_name
            ):
                return step["inputs"]["script"]

    raise RuntimeError(
        f"Could not find PythonScript@0 task with displayName='{display_name}' "
        f"in resources-validation.yml"
    )


def find_iccp_chunk(data: bytes) -> tuple:
    """:returns: (start offset, end offset, chunk body) of the iCCP chunk."""
    pos = 8
    while pos + 8 <= len(data):
        length, chunk_type = struct.unpack(">I4s", data[pos : pos + 8])
        if chunk_type == b"iCCP":
            return pos, pos + 12 + length, data[pos + 8 : pos + 8 + length]
        pos += 12 + length
    raise RuntimeError("No iCCP chunk found")


def read_png(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def replace_iccp_chunk(data: bytes, body: bytes) -> bytes:
    start, end, _ = find_iccp_chunk(data)
    chunk = b"iCCP" + body
    new_chunk = (
        struct.pack(">I", len(body))
        + chunk
        + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
    )
    return data[:start] + new_chunk + data[end:]


def with_compressed_profile(data: bytes, compressed: bytes) -> bytes:
    """:returns: The PNG data with the iCCP profile stream replaced."""
    return replace_iccp_chunk(data, b"name\x00\x00" + compressed)


def with_profile_intent(data: bytes, intent: int) -> bytes:
    """:returns: The PNG data with the embedded ICC profile intent changed."""
    _, _, body = find_iccp_chunk(data)
    name, _, compressed = body.partition(b"\x00")
    profile = bytearray(zlib.decompress(compressed[1:]))
    profile[ICC_INTENT_OFFSET] = intent
    new_body = name + b"\x00\x00" + zlib.compress(bytes(profile))
    return replace_iccp_chunk(data, new_body)
