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
import shutil
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
    assert_fails(run_checker(checker, path), "iCCP: corrupt profile")


def test_good_profile(checker: str) -> None:
    """good_profile.png has no iCCP chunk and passes."""
    assert_passes(run_checker(checker, GOOD_PROFILE_PNG))


def test_huge_profile(checker: str, tmp_path: pathlib.Path) -> None:
    """A profile inflating past libpng's 8 MB limit is reported."""
    compressor = zlib.compressobj()
    chunk = b"\x00" * (1 << 20)
    compressed = b"".join(compressor.compress(chunk) for _ in range(64))
    compressed += compressor.flush()
    path = tmp_path / "huge.png"
    path.write_bytes(with_compressed_profile(read_png(WRONG_PROFILE_PNG), compressed))
    assert_fails(run_checker(checker, path), "iCCP: profile exceeds 8000000 bytes")


def test_large_profile(checker: str, tmp_path: pathlib.Path) -> None:
    """A valid profile larger than the known ones passes."""
    compressed = zlib.compress(bytes(range(256)) * 400)
    path = tmp_path / "large.png"
    path.write_bytes(with_compressed_profile(read_png(WRONG_PROFILE_PNG), compressed))
    assert_passes(run_checker(checker, path))


def test_truncated_profile(checker: str, tmp_path: pathlib.Path) -> None:
    """A profile stream cut short is reported as corrupt."""
    data = read_png(WRONG_PROFILE_PNG)
    _, _, body = find_iccp_chunk(data)
    path = tmp_path / "truncated.png"
    path.write_bytes(replace_iccp_chunk(data, body[: len(body) // 2]))
    assert_fails(run_checker(checker, path), "iCCP: corrupt profile: truncated stream")


def test_truncated_oversized_profile(checker: str, tmp_path: pathlib.Path) -> None:
    """A profile larger than the known ones missing its zlib checksum is corrupt."""
    # Drop the trailing adler32 so the stream inflates fully but never ends.
    compressed = zlib.compress(bytes(range(256)) * 16)[:-4]
    path = tmp_path / "truncated_oversized.png"
    path.write_bytes(with_compressed_profile(read_png(WRONG_PROFILE_PNG), compressed))
    assert_fails(run_checker(checker, path), "iCCP: corrupt profile: truncated stream")


def test_known_incorrect_media_relative(checker: str) -> None:
    """wrong_profile.png embeds the HP-Microsoft sRGB v2 media-relative profile."""
    assert_fails(
        run_checker(checker, WRONG_PROFILE_PNG), "iCCP: known incorrect sRGB profile"
    )


def test_known_incorrect_perceptual(checker: str, tmp_path: pathlib.Path) -> None:
    """The HP-Microsoft sRGB v2 perceptual variant only differs by its intent."""
    path = tmp_path / "perceptual.png"
    path.write_bytes(with_profile_intent(read_png(WRONG_PROFILE_PNG), 0))
    assert_fails(run_checker(checker, path), "iCCP: known incorrect sRGB profile")


def test_unknown_profile(checker: str, tmp_path: pathlib.Path) -> None:
    """A valid profile that is not in the known-incorrect list passes."""
    path = tmp_path / "unknown.png"
    path.write_bytes(with_profile_intent(read_png(WRONG_PROFILE_PNG), 2))
    assert_passes(run_checker(checker, path))


def test_not_a_png(checker: str, tmp_path: pathlib.Path) -> None:
    """A file that is not a PNG is reported."""
    path = tmp_path / "fake.png"
    path.write_bytes(b"not a png")
    assert_fails(run_checker(checker, path), "not a PNG file")


def test_directory(checker: str, tmp_path: pathlib.Path) -> None:
    """Directories are searched recursively and every bad PNG is counted."""
    (tmp_path / "nested").mkdir()
    shutil.copy(GOOD_PROFILE_PNG, tmp_path / "good.png")
    shutil.copy(WRONG_PROFILE_PNG, tmp_path / "wrong.png")
    shutil.copy(WRONG_PROFILE_PNG, tmp_path / "nested" / "wrong.PNG")
    result = run_checker(checker, tmp_path)
    assert_fails(result, "2 PNG file(s) have profile errors")
    assert "good.png" not in result.stdout


def test_directory_without_pngs(checker: str, tmp_path: pathlib.Path) -> None:
    """A directory without PNG files passes."""
    assert_passes(run_checker(checker, tmp_path))


def test_expect_invalid(checker: str) -> None:
    """--expect-invalid succeeds on an invalid PNG and fails on a valid one."""
    result = run_checker(checker, "--expect-invalid", WRONG_PROFILE_PNG)
    assert result.returncode == 0
    assert "is invalid as expected" in result.stdout

    result = run_checker(checker, "--expect-invalid", GOOD_PROFILE_PNG)
    assert result.returncode == 1
    assert "expected to be invalid but passed" in result.stdout


def test_crash_exit_code(checker: str, tmp_path: pathlib.Path) -> None:
    """A crash exits with 2 so it can't be mistaken for an invalid PNG."""
    for args in ((str(tmp_path / "missing.png"),), ("--expect-invalid",), ()):
        result = run_checker(checker, *args)
        assert result.returncode == 2, args


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


def assert_fails(result: subprocess.CompletedProcess, message: str) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    assert message in result.stdout


def assert_passes(result: subprocess.CompletedProcess) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""


def run_checker(checker: str, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, checker, *[str(arg) for arg in args]],
        capture_output=True,
        text=True,
    )


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
