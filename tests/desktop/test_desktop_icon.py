"""ADR-0540: the installers' Desktop shortcut carries the tool's OWN icon, written from the
shipped favicon by ``schedule_forensics.desktop_icon`` in the form each desktop wants. Each
writer is checked against the format's own header rules (an independent reading, not the
writer's), and the ICO frames against the real shipped file."""

from __future__ import annotations

import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

from schedule_forensics import desktop_icon as di


def _png_size(png: bytes) -> tuple[int, int]:
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and png[12:16] == b"IHDR"
    w, h = struct.unpack(">II", png[16:24])
    # the IHDR chunk's CRC, as PNG defines it — a truncated or altered frame fails here
    (crc,) = struct.unpack(">I", png[29:33])
    assert crc == zlib.crc32(png[12:29]) & 0xFFFFFFFF
    return w, h


def test_the_shipped_favicon_carries_the_five_png_frames() -> None:
    frames = di.ico_frames(di.favicon_bytes())
    assert sorted(frames) == [16, 32, 64, 128, 256]
    for size, png in frames.items():
        assert _png_size(png) == (size, size)


def test_the_png_is_the_largest_frame() -> None:
    assert _png_size(di.png_bytes()) == (256, 256)


def test_the_icns_holds_the_256_and_128_frames_with_correct_lengths() -> None:
    data = di.icns_bytes()
    assert data[:4] == b"icns"
    (total,) = struct.unpack(">I", data[4:8])
    assert total == len(data)
    at, seen = 8, {}
    while at < len(data):
        kind, length = data[at : at + 4], struct.unpack(">I", data[at + 4 : at + 8])[0]
        png = data[at + 8 : at + length]
        seen[kind] = _png_size(png)
        at += length
    assert at == len(data)
    assert seen == {b"ic07": (128, 128), b"ic08": (256, 256)}


@pytest.mark.parametrize("kind", ["ico", "png", "icns"])
def test_the_command_line_writes_each_form(tmp_path: Path, kind: str) -> None:
    out = tmp_path / f"icon.{kind}"
    proc = subprocess.run(
        [sys.executable, "-m", "schedule_forensics.desktop_icon", kind, str(out)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    data = out.read_bytes()
    assert data == {"ico": di.favicon_bytes(), "png": di.png_bytes(), "icns": di.icns_bytes()}[kind]


def test_the_command_line_refuses_an_unknown_form(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "schedule_forensics.desktop_icon", "bmp", str(tmp_path / "x")],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1 and "unknown icon kind" in proc.stderr
    assert di.main(["png"]) == 2


def test_mutation_a_bmp_only_icon_and_a_truncated_one_are_refused() -> None:
    bmp = (
        b"\x00\x00\x01\x00"
        + struct.pack("<H", 1)
        + struct.pack("<BBBBHHII", 16, 16, 0, 0, 1, 32, 4, 22)
        + b"\x28\x00\x00\x00"
    )
    with pytest.raises(ValueError, match="no PNG frame"):
        di.ico_frames(bmp)
    with pytest.raises(ValueError, match="truncated"):
        di.ico_frames(di.favicon_bytes()[:-100])
    with pytest.raises(ValueError, match="not a Windows icon"):
        di.ico_frames(b"GIF89a")


def _frame_span(ico: bytes, size: int) -> tuple[int, int]:
    """``(offset, length)`` of the directory entry whose width byte says ``size`` (0 = 256)."""
    (count,) = struct.unpack("<H", ico[4:6])
    for i in range(count):
        width, _h, _c, _r, _p, _b, length, offset = struct.unpack(
            "<BBBBHHII", ico[6 + 16 * i : 22 + 16 * i]
        )
        if (width or 256) == size:
            return offset, length
    raise AssertionError(size)


def test_review_a_frame_whose_bytes_no_longer_match_their_crc_is_refused_not_copied() -> None:
    """Review of ADR-0540 (F5): the writer copied a frame whose IDAT was corrupt — its
    docstring's "an icon that no longer parses is refused" held only for the directory. Every
    chunk's CRC is now checked, so a flipped byte anywhere in a frame refuses the icon by
    name."""
    ico = bytearray(di.favicon_bytes())
    offset, length = _frame_span(ico, 64)
    frame = bytes(ico[offset : offset + length])
    at = frame.index(b"IDAT") + 20  # well inside the IDAT data
    ico[offset + at] ^= 0x5A
    with pytest.raises(ValueError, match="CRC"):
        di.ico_frames(bytes(ico))
    with pytest.raises(ValueError, match="CRC"):
        di.icns_bytes(bytes(ico))


def test_review_the_frames_are_sized_by_their_own_header_not_the_directory() -> None:
    """Review of ADR-0540 (F5): the ICO directory's width byte sized the frames, so a directory
    that mislabels a frame put a 128-pixel picture in the .icns slot that promises 256. The
    IHDR is the picture's own word; a directory that disagrees with it is refused."""
    ico = bytearray(di.favicon_bytes())
    (count,) = struct.unpack("<H", ico[4:6])
    for i in range(count):
        if ico[6 + 16 * i] == 128:
            ico[6 + 16 * i] = 64  # the directory now calls the 128-pixel frame 64
    with pytest.raises(ValueError, match="directory"):
        di.ico_frames(bytes(ico))
    with pytest.raises(ValueError, match="directory"):
        di.icns_bytes(bytes(ico))
