"""Generate the Schedule Forensics desktop icon (`windows/schedule-forensics.ico`).

Stdlib-only (no Pillow): draws a dark, NASA-themed 64x64 RGBA tile with the accent-blue
upward triangle from the dashboard header, encodes it as PNG, and wraps it in an ICO
container (PNG-in-ICO, supported on Windows Vista+). Run: `python packaging/make_icon.py`.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIZE = 64
BG = (11, 14, 20, 255)  # #0b0e14 dashboard background
ACCENT = (74, 163, 255, 255)  # #4aa3ff


def _triangle(x: int, y: int) -> bool:
    """True if pixel (x, y) is inside a centered upward triangle (the header glyph)."""
    # apex near the top-centre, base near the bottom; widen linearly toward the base
    top, bottom = 12, 52
    if not (top <= y <= bottom):
        return False
    half = (y - top) * (SIZE / 2 - 8) / (bottom - top)
    return abs(x - SIZE / 2 + 0.5) <= half


def _png(pixels: list[tuple[int, int, int, int]]) -> bytes:
    raw = bytearray()
    for row in range(SIZE):
        raw.append(0)  # filter type 0 (none) per scanline
        for col in range(SIZE):
            raw.extend(pixels[row * SIZE + col])

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)  # RGBA, 8-bit
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def _ico(png: bytes) -> bytes:
    header = struct.pack("<HHH", 0, 1, 1)  # reserved, type=icon, count=1
    entry = struct.pack(
        "<BBBBHHII", SIZE, SIZE, 0, 0, 1, 32, len(png), 6 + 16
    )  # w, h, colors, reserved, planes, bpp, size, offset
    return header + entry + png


def main() -> None:
    pixels = [
        ACCENT if _triangle(col, row) else BG
        for row in range(SIZE)
        for col in range(SIZE)
    ]
    out = Path(__file__).parent / "windows" / "schedule-forensics.ico"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(_ico(_png(pixels)))
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
