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

CHECKER = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "internal", "check_png_profile.py"
)
TEST_IMAGES_DIR = os.path.join(os.path.dirname(__file__), "test_images")
GOOD_PROFILE_PNG = os.path.join(TEST_IMAGES_DIR, "good_profile.png")
WRONG_PROFILE_PNG = os.path.join(TEST_IMAGES_DIR, "wrong_profile.png")

# Offset of the rendering intent in the ICC profile header.
ICC_INTENT_OFFSET = 67


def test_corrupt_profile(tmp_path: pathlib.Path) -> None:
    """A truncated iCCP stream is reported as corrupt."""
    path = tmp_path / "corrupt.png"
    path.write_bytes(
        replace_iccp_chunk(read_png(WRONG_PROFILE_PNG), b"name\x00\x00garbage")
    )
    assert "iCCP: corrupt profile" in run_checker(path)


def test_good_profile() -> None:
    """good_profile.png has no iCCP chunk and passes."""
    assert run_checker(GOOD_PROFILE_PNG) == ""


def test_known_incorrect_media_relative() -> None:
    """wrong_profile.png embeds the HP-Microsoft sRGB v2 media-relative profile."""
    output = run_checker(WRONG_PROFILE_PNG)
    assert "iCCP: known incorrect sRGB profile" in output


def test_known_incorrect_perceptual(tmp_path: pathlib.Path) -> None:
    """The HP-Microsoft sRGB v2 perceptual variant only differs by its intent."""
    path = tmp_path / "perceptual.png"
    path.write_bytes(with_profile_intent(read_png(WRONG_PROFILE_PNG), 0))
    assert "iCCP: known incorrect sRGB profile" in run_checker(path)


def test_unknown_profile(tmp_path: pathlib.Path) -> None:
    """A valid profile that is not in the known-incorrect list passes."""
    path = tmp_path / "unknown.png"
    path.write_bytes(with_profile_intent(read_png(WRONG_PROFILE_PNG), 2))
    assert run_checker(path) == ""


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


def run_checker(path) -> str:
    result = subprocess.run(
        [sys.executable, CHECKER, str(path)],
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
