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
Reimplements the 'known incorrect sRGB profile' check removed in libpng 1.6.47,
which pngcrush relied on.

Usage: python check_png_profile.py <file.png>

Prints a line containing 'iCCP:' if the PNG embeds an incorrect profile.
"""

import struct
import sys
import zlib

# (adler32, crc32, length) of the profiles libpng flagged as broken.
KNOWN_INCORRECT_PROFILES = {
    (0x0398F3FC, 0xF29E526D, 3144),  # HP-Microsoft sRGB v2 media-relative
    (0xF784F3FB, 0x182EA552, 3144),  # HP-Microsoft sRGB v2 perceptual
}


def check(path):
    with open(path, "rb") as f:
        data = f.read()

    pos = 8
    while pos + 8 <= len(data):
        length, chunk_type = struct.unpack(">I4s", data[pos : pos + 8])
        if chunk_type == b"IDAT":
            break
        if chunk_type == b"iCCP":
            body = data[pos + 8 : pos + 8 + length]
            try:
                profile = zlib.decompress(body.partition(b"\x00")[2][1:])
            except zlib.error as e:
                print("%s: iCCP: corrupt profile: %s" % (path, e))
                break
            key = (zlib.adler32(profile), zlib.crc32(profile), len(profile))
            if key in KNOWN_INCORRECT_PROFILES:
                print("%s: iCCP: known incorrect sRGB profile" % path)
            break
        pos += 12 + length


if __name__ == "__main__":
    check(sys.argv[1])
