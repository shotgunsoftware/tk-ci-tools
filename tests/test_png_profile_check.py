# Copyright (c) 2026 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import pathlib
import struct
import subprocess
import sys
import zlib

import pytest
import yaml

TEST_IMAGES_DIR = os.path.join(os.path.dirname(__file__), "test_images")
GOOD_PROFILE_PNG = os.path.join(TEST_IMAGES_DIR, "good_profile.png")
WRONG_PROFILE_PNG = os.path.join(TEST_IMAGES_DIR, "wrong_profile.png")

# Offset of the rendering intent in the ICC profile header.
ICC_INTENT_OFFSET = 67


def test_corrupt_profile(checker: str, tmp_path: pathlib.Path) -> None:
    """A truncated iCCP stream is reported as corrupt."""
    path = tmp_path / "corrupt.png"
    path.write_bytes(
        replace_iccp_chunk(read_png(WRONG_PROFILE_PNG), b"name\x00\x00garbage")
    )
    assert "iCCP: corrupt profile" in run_checker(checker, path)


def test_good_profile(checker: str) -> None:
    """good_profile.png has no iCCP chunk and passes."""
    assert run_checker(checker, GOOD_PROFILE_PNG) == ""


def test_huge_profile(checker: str, tmp_path: pathlib.Path) -> None:
    """A profile inflating to 64 MB can't match a known one and passes."""
    compressor = zlib.compressobj()
    chunk = b"\x00" * (1 << 20)
    compressed = b"".join(compressor.compress(chunk) for _ in range(64))
    compressed += compressor.flush()
    path = tmp_path / "huge.png"
    path.write_bytes(
        replace_iccp_chunk(read_png(WRONG_PROFILE_PNG), b"name\x00\x00" + compressed)
    )
    assert run_checker(checker, path) == ""


def test_truncated_profile(checker: str, tmp_path: pathlib.Path) -> None:
    """A profile stream cut short is reported as corrupt."""
    data = read_png(WRONG_PROFILE_PNG)
    _, _, body = find_iccp_chunk(data)
    path = tmp_path / "truncated.png"
    path.write_bytes(replace_iccp_chunk(data, body[: len(body) // 2]))
    assert "iCCP: corrupt profile: truncated stream" in run_checker(checker, path)


def test_known_incorrect_media_relative(checker: str) -> None:
    """wrong_profile.png embeds the HP-Microsoft sRGB v2 media-relative profile."""
    output = run_checker(checker, WRONG_PROFILE_PNG)
    assert "iCCP: known incorrect sRGB profile" in output


def test_known_incorrect_perceptual(checker: str, tmp_path: pathlib.Path) -> None:
    """The HP-Microsoft sRGB v2 perceptual variant only differs by its intent."""
    path = tmp_path / "perceptual.png"
    path.write_bytes(with_profile_intent(read_png(WRONG_PROFILE_PNG), 0))
    assert "iCCP: known incorrect sRGB profile" in run_checker(checker, path)


def test_unknown_profile(checker: str, tmp_path: pathlib.Path) -> None:
    """A valid profile that is not in the known-incorrect list passes."""
    path = tmp_path / "unknown.png"
    path.write_bytes(with_profile_intent(read_png(WRONG_PROFILE_PNG), 2))
    assert run_checker(checker, path) == ""


@pytest.fixture(scope="module")
def checker(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Write the PNG profile checker extracted from the pipeline YAML to disk."""
    path = tmp_path_factory.mktemp("checker") / "check_png_profile.py"
    path.write_text(extract_checker_from_yaml())
    return str(path)


def extract_checker_from_yaml() -> str:
    """
    Extract the heredoc Python script from the 'Write PNG profile checker' step
    so we test the exact code that runs in CI.
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
            if step.get("displayName") != "Write PNG profile checker":
                continue
            script = step["script"]
            start = script.index("<<'EOF'\n") + len("<<'EOF'\n")
            end = script.index("\nEOF", start)
            return script[start:end]

    raise RuntimeError(
        "Could not find the 'Write PNG profile checker' step in "
        "resources-validation.yml"
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


def run_checker(checker: str, path) -> str:
    result = subprocess.run(
        [sys.executable, checker, str(path)],
        capture_output=True,
        check=True,
        text=True,
    )
    return result.stdout.strip()


def with_profile_intent(data: bytes, intent: int) -> bytes:
    """:returns: The PNG data with the embedded ICC profile intent changed."""
    _, _, body = find_iccp_chunk(data)
    name, _, compressed = body.partition(b"\x00")
    profile = bytearray(zlib.decompress(compressed[1:]))
    profile[ICC_INTENT_OFFSET] = intent
    new_body = name + b"\x00\x00" + zlib.compress(bytes(profile))
    return replace_iccp_chunk(data, new_body)
