"""The tool's own icon for a desktop shortcut, in the form each desktop wants (ADR-0540).

The installers put ONE icon on the Desktop — "Polaris²" — and the operator asked that it carry
the tool's own picture, not the Python interpreter's. The picture already ships: the favicon the
app serves (``web/static/favicon.ico``), a Windows icon holding PNG frames at 256, 128, 64, 32
and 16 pixels. Windows takes that ``.ico`` as it is; a Linux ``.desktop`` entry wants a PNG; a
macOS application bundle wants an ``.icns`` — which may carry PNG frames directly (``ic07`` 128,
``ic08`` 256 pixels). So the installers ask the installed package for the file they need:

    python -m schedule_forensics.desktop_icon ico  <out.ico>
    python -m schedule_forensics.desktop_icon png  <out.png>
    python -m schedule_forensics.desktop_icon icns <out.icns>

Standard library only, as everything the deployed tool runs (Law 1); nothing here reads a schedule.
"""

from __future__ import annotations

import struct
import sys
import zlib
from importlib.resources import files
from pathlib import Path

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
#: icns frame types by the PNG's pixel size (Apple's PNG-bearing types).
_ICNS_TYPES = {128: b"ic07", 256: b"ic08", 512: b"ic09"}


def favicon_bytes() -> bytes:
    """The shipped ``favicon.ico``, from the installed package."""
    return files("schedule_forensics.web").joinpath("static", "favicon.ico").read_bytes()


def _png_size(png: bytes) -> tuple[int, int]:
    """``(width, height)`` from the PNG's own IHDR, after EVERY chunk's CRC has been checked —
    a frame whose bytes no longer match their CRC is refused by name, never copied."""
    if png[:8] != _PNG_MAGIC or png[12:16] != b"IHDR":
        raise ValueError("frame is not a PNG")
    at = 8
    while True:
        if at + 12 > len(png):
            raise ValueError("PNG frame has no IEND")
        (length,) = struct.unpack(">I", png[at : at + 4])
        kind, end = png[at + 4 : at + 8], at + 12 + length
        if end > len(png):
            raise ValueError(f"PNG chunk {kind!r} is truncated")
        (crc,) = struct.unpack(">I", png[end - 4 : end])
        if zlib.crc32(png[at + 4 : end - 4]) & 0xFFFFFFFF != crc:
            raise ValueError(f"PNG chunk {kind!r} fails its CRC")
        if kind == b"IEND":
            break
        at = end
    width, height = struct.unpack(">II", png[16:24])
    return int(width), int(height)


def ico_frames(ico: bytes) -> dict[int, bytes]:
    """``{pixel size: PNG bytes}`` for every PNG-compressed frame of a Windows icon (a BMP
    frame, which this favicon never carries, is left out). The size is the frame's OWN (its
    IHDR, every chunk CRC-checked); a directory entry that disagrees with it is refused."""
    if len(ico) < 6 or ico[:4] != b"\x00\x00\x01\x00":
        raise ValueError("not a Windows icon")
    (count,) = struct.unpack("<H", ico[4:6])
    out: dict[int, bytes] = {}
    for i in range(count):
        entry = ico[6 + 16 * i : 22 + 16 * i]
        if len(entry) < 16:
            raise ValueError("truncated icon directory")
        width, _h, _c, _r, _planes, _bpp, size, offset = struct.unpack("<BBBBHHII", entry)
        frame = ico[offset : offset + size]
        if len(frame) != size:
            raise ValueError("truncated icon frame")
        if frame[:8] == _PNG_MAGIC:
            w, h = _png_size(frame)
            if (width or 256) != w or w != h:
                raise ValueError(f"icon directory says {width or 256} pixels, the frame is {w}x{h}")
            out[w] = frame
    if not out:
        raise ValueError("the icon carries no PNG frame")
    return out


def png_bytes(ico: bytes | None = None) -> bytes:
    """The largest PNG frame — the picture a Linux desktop entry shows."""
    frames = ico_frames(favicon_bytes() if ico is None else ico)
    return frames[max(frames)]


def icns_bytes(ico: bytes | None = None) -> bytes:
    """An Apple icon holding every frame of a size ``.icns`` takes as PNG (256 and 128 pixels
    here): the ``icns`` header with the file's length, then one ``type + length + PNG`` entry per
    frame, lengths big-endian and including their own 8-byte header."""
    frames = ico_frames(favicon_bytes() if ico is None else ico)
    entries = b"".join(
        _ICNS_TYPES[size] + struct.pack(">I", 8 + len(png)) + png
        for size, png in sorted(frames.items())
        if size in _ICNS_TYPES
    )
    if not entries:
        raise ValueError("no frame of a size an .icns carries as PNG (128, 256 or 512)")
    return b"icns" + struct.pack(">I", 8 + len(entries)) + entries


def write(kind: str, out: Path) -> Path:
    """Write the icon as ``kind`` (``ico`` / ``png`` / ``icns``) to ``out``; returns ``out``."""
    if kind == "ico":
        data = favicon_bytes()
        ico_frames(data)  # a shipped icon that no longer parses (any chunk's CRC) is refused
    elif kind == "png":
        data = png_bytes()
    elif kind == "icns":
        data = icns_bytes()
    else:
        raise ValueError(f"unknown icon kind {kind!r} — ico, png or icns")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return out


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print(
            "usage: python -m schedule_forensics.desktop_icon {ico|png|icns} <out>", file=sys.stderr
        )
        return 2
    try:
        write(args[0], Path(args[1]))
    except (ValueError, OSError) as exc:
        print(f"desktop icon not written: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover — the installers' entry point
    raise SystemExit(main())
