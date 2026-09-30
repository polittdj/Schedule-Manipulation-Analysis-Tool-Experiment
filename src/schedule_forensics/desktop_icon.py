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

LODESTAR (ADR-0541) has an icon of its OWN — the ✦ lodestar in gold on a dark rounded square —
so the two programs are told apart on a Desktop that carries both. It is not a shipped picture
but a picture this module DRAWS (:func:`lodestar_ico_bytes`: a four-point star rasterised with
16x supersampling at 256 / 128 / 64 / 32 / 16 pixels, packed as a Windows icon of PNG frames),
committed as ``web/static/lodestar.ico`` so LODESTAR serves it as its favicon; a test decodes
the committed file and holds its pixels to a fresh render (the PNG's deflate stream is not
byte-pinned — zlib builds differ; the pixels cannot). The same three forms, from that picture:

    python -m schedule_forensics.desktop_icon lodestar-ico  <out.ico>
    python -m schedule_forensics.desktop_icon lodestar-png  <out.png>
    python -m schedule_forensics.desktop_icon lodestar-icns <out.icns>

Standard library only, as everything the deployed tool runs (Law 1); nothing here reads a schedule.
"""

from __future__ import annotations

import math
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


# ── LODESTAR's own icon, drawn here (ADR-0541) ───────────────────────────────────────────────

#: The picture: the lodestar's gold on the boot screen's dark ground (the two colours of
#: LODESTAR's launch page), the square's corners rounded to a fifth of its side.
LODESTAR_GOLD = (0xF0, 0xC2, 0x4B)
LODESTAR_GROUND = (0x0B, 0x12, 0x20)
LODESTAR_SIZES = (256, 128, 64, 32, 16)
_SS = 4  # supersampling per axis (16 samples a pixel)


def _star(size: float) -> list[tuple[float, float]]:
    """A four-point star (U+2726's shape): points at the compass headings, the waist between
    them — eight vertices about the square's centre."""
    cx = cy = size / 2
    outer, inner = size * 0.42, size * 0.13
    pts: list[tuple[float, float]] = []
    for k in range(8):
        r = outer if k % 2 == 0 else inner
        ang = math.pi / 4 * k - math.pi / 2
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return pts


def _in_polygon(x: float, y: float, pts: list[tuple[float, float]]) -> bool:
    inside = False
    n = len(pts)
    for i in range(n):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def _in_rounded_square(x: float, y: float, size: float) -> bool:
    r = size / 5
    cx = min(max(x, r), size - r)
    cy = min(max(y, r), size - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def lodestar_rgba(size: int) -> bytes:
    """The picture at ``size`` pixels as RGBA rows (top to bottom), anti-aliased by sampling
    ``_SS x _SS`` points a pixel: the star's gold over the ground where the star is, the ground
    inside the rounded square, transparent outside it."""
    star = _star(float(size))
    out = bytearray()
    n = _SS * _SS
    for py in range(size):
        for px in range(size):
            ground = gold = 0
            for sy in range(_SS):
                y = py + (sy + 0.5) / _SS
                for sx in range(_SS):
                    x = px + (sx + 0.5) / _SS
                    if _in_rounded_square(x, y, size):
                        ground += 1
                        if _in_polygon(x, y, star):
                            gold += 1
            if ground == 0:
                out += b"\x00\x00\x00\x00"
                continue
            t = gold / ground
            rgb = tuple(
                round(g + (s - g) * t) for g, s in zip(LODESTAR_GROUND, LODESTAR_GOLD, strict=True)
            )
            out += bytes(rgb) + bytes((round(255 * ground / n),))
    return bytes(out)


def _chunk(kind: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)


def png_encode(rgba: bytes, size: int) -> bytes:
    """A truecolour-with-alpha PNG of ``size`` square from RGBA rows (filter 0 on every row)."""
    row = size * 4
    raw = b"".join(b"\x00" + rgba[y * row : (y + 1) * row] for y in range(size))
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (
        _PNG_MAGIC
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )


def lodestar_ico_bytes() -> bytes:
    """LODESTAR's icon: a Windows icon holding one PNG frame per size in :data:`LODESTAR_SIZES`,
    the same package shape as the shipped favicon (:func:`ico_frames` reads it back)."""
    frames = [(size, png_encode(lodestar_rgba(size), size)) for size in LODESTAR_SIZES]
    head = b"\x00\x00\x01\x00" + struct.pack("<H", len(frames))
    offset = 6 + 16 * len(frames)
    entries = b""
    for size, png in frames:
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
    return head + entries + b"".join(png for _size, png in frames)


def png_pixels(png: bytes) -> tuple[int, int, bytes]:
    """``(width, height, RGBA rows)`` of an 8-bit RGBA, filter-0 PNG — the decoder the pixel
    pin uses (it accepts exactly what :func:`png_encode` writes, and refuses anything else)."""
    width, height = _png_size(png)
    if png[24:29] != b"\x08\x06\x00\x00\x00":
        raise ValueError("not an 8-bit RGBA non-interlaced PNG")
    at, idat = 8, b""
    while at + 12 <= len(png):
        (length,) = struct.unpack(">I", png[at : at + 4])
        kind = png[at + 4 : at + 8]
        if kind == b"IDAT":
            idat += png[at + 8 : at + 8 + length]
        at += 12 + length
    raw = zlib.decompress(idat)
    row = width * 4
    rows = b""
    for y in range(height):
        if raw[y * (row + 1)] != 0:
            raise ValueError("a row uses a filter other than 0")
        rows += raw[y * (row + 1) + 1 : (y + 1) * (row + 1)]
    return width, height, rows


def write(kind: str, out: Path) -> Path:
    """Write the icon as ``kind`` — ``ico`` / ``png`` / ``icns`` of the shipped favicon, or
    ``lodestar-ico`` / ``lodestar-png`` / ``lodestar-icns`` of LODESTAR's own picture — to
    ``out``; returns ``out``."""
    source: bytes | None = None
    if kind.startswith("lodestar-"):
        source, kind = lodestar_ico_bytes(), kind[len("lodestar-") :]
    if kind == "ico":
        data = favicon_bytes() if source is None else source
        ico_frames(data)  # a shipped icon that no longer parses (any chunk's CRC) is refused
    elif kind == "png":
        data = png_bytes(source)
    elif kind == "icns":
        data = icns_bytes(source)
    else:
        raise ValueError(f"unknown icon kind {kind!r} — ico, png or icns")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return out


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print(
            "usage: python -m schedule_forensics.desktop_icon "
            "{ico|png|icns|lodestar-ico|lodestar-png|lodestar-icns} <out>",
            file=sys.stderr,
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
