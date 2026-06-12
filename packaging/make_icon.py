"""Generate the Schedule Forensics app icon (desktop `.ico`, Linux `.png`, web favicon).

Stdlib-only (no Pillow). The mark is the tool's identity drawn from its own dashboard
palette: a dark navy rounded tile with a subtle gradient and accent edge, the white
header triangle, a red/blue/green **Gantt waterfall** (critical → in-work → complete)
cascading down-right, and the **gold dashed data-date line** cutting through it — the
one image that says "forensic schedule analysis". Rendered 4x supersampled (anti-
aliased) at 256 px and box-downsampled to 128/64/32/16, packed as a multi-entry
PNG-in-ICO (Windows Vista+). Run: ``python packaging/make_icon.py`` — it writes the
Windows icon, the Linux PNG, and the served favicon from the same bytes so they can
never drift (a test asserts the sync).
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIZE = 256  # master tile, in icon pixels
_SS = 4  # supersampling factor (anti-aliasing)
_GRID = SIZE * _SS
_ICO_SIZES = (256, 128, 64, 32, 16)  # every size divides the supersampled grid exactly

# the dashboard's own palette (web/static/app.css)
_BG_TOP = (13, 19, 32)  # deep navy, top of the gradient
_BG_BOTTOM = (22, 35, 60)  # lighter navy, bottom
_EDGE = (74, 163, 255)  # accent-blue inner edge glow
_TRIANGLE = (234, 242, 255)  # the near-white header "▲"
_BAR_CRITICAL = (255, 93, 93)  # red — the critical path
_BAR_WORK = (74, 163, 255)  # accent blue — in-progress work
_BAR_DONE = (61, 220, 132)  # green — completed
_GOLD = (240, 180, 41)  # the dashed data-date line

_CORNER_RADIUS = 56.0
_EDGE_WIDTH = 4.0

#: The waterfall bars in 256-space: (x0, y0, x1, y1, color).
_BARS = (
    (36.0, 104.0, 148.0, 132.0, _BAR_CRITICAL),
    (76.0, 144.0, 188.0, 172.0, _BAR_WORK),
    (116.0, 184.0, 220.0, 212.0, _BAR_DONE),
)
#: The gold dashed vertical data-date line: x-band, y-span, dash on/period.
_LINE_X = (162.0, 174.0)
_LINE_Y = (92.0, 226.0)
_DASH_ON, _DASH_PERIOD = 16.0, 28.0
#: The header triangle: apex, base y, base half-width.
_APEX = (74.0, 24.0)
_TRI_BASE_Y, _TRI_HALF = 86.0, 36.0


def _in_rounded_tile(x: float, y: float, inset: float) -> bool:
    """Inside the rounded-square tile shrunk by ``inset`` on every side."""
    lo, hi = inset, SIZE - inset
    if not (lo <= x <= hi and lo <= y <= hi):
        return False
    r = _CORNER_RADIUS - inset
    cx = min(max(x, lo + r), hi - r)
    cy = min(max(y, lo + r), hi - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def _color_at(x: float, y: float) -> tuple[int, int, int, int]:
    """The mark's color at one supersample point in 256-space (alpha-aware)."""
    if not _in_rounded_tile(x, y, 0.0):
        return (0, 0, 0, 0)
    # gold data-date line over everything — the forensic "now" cuts through the plan
    if (
        _LINE_X[0] <= x <= _LINE_X[1]
        and _LINE_Y[0] <= y <= _LINE_Y[1]
        and (y - _LINE_Y[0]) % _DASH_PERIOD < _DASH_ON
    ):
        return (*_GOLD, 255)
    for x0, y0, x1, y1, color in _BARS:
        if x0 <= x <= x1 and y0 <= y <= y1:
            return (*color, 255)
    if _APEX[1] <= y <= _TRI_BASE_Y:
        half = (y - _APEX[1]) * _TRI_HALF / (_TRI_BASE_Y - _APEX[1])
        if abs(x - _APEX[0]) <= half:
            return (*_TRIANGLE, 255)
    if not _in_rounded_tile(x, y, _EDGE_WIDTH):
        return (*_EDGE, 255)  # the accent edge ring
    t = y / SIZE  # vertical gradient
    return (
        round(_BG_TOP[0] + (_BG_BOTTOM[0] - _BG_TOP[0]) * t),
        round(_BG_TOP[1] + (_BG_BOTTOM[1] - _BG_TOP[1]) * t),
        round(_BG_TOP[2] + (_BG_BOTTOM[2] - _BG_TOP[2]) * t),
        255,
    )


def _render_grid() -> list[tuple[int, int, int, int]]:
    """The supersampled master (``_GRID`` x ``_GRID`` RGBA), row-major."""
    step = 1.0 / _SS
    half = step / 2.0
    return [
        _color_at(col * step + half, row * step + half)
        for row in range(_GRID)
        for col in range(_GRID)
    ]


def _downsample(grid: list[tuple[int, int, int, int]], size: int) -> bytes:
    """Box-average the supersampled grid to ``size`` px; raw RGBA bytes, row-major."""
    box = _GRID // size  # exact for every _ICO_SIZES entry
    area = box * box
    out = bytearray()
    for row in range(size):
        for col in range(size):
            r = g = b = a = 0
            for dy in range(box):
                base = (row * box + dy) * _GRID + col * box
                for dx in range(box):
                    pr, pg, pb, pa = grid[base + dx]
                    r += pr * pa
                    g += pg * pa
                    b += pb * pa
                    a += pa
            if a:
                out.extend((round(r / a), round(g / a), round(b / a), round(a / area)))
            else:
                out.extend((0, 0, 0, 0))
    return bytes(out)


def _png(rgba: bytes, size: int) -> bytes:
    raw = bytearray()
    stride = size * 4
    for row in range(size):
        raw.append(0)  # filter type 0 (none) per scanline
        raw.extend(rgba[row * stride : (row + 1) * stride])

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # RGBA, 8-bit
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def build_assets() -> tuple[bytes, bytes]:
    """(multi-entry ``.ico`` bytes, 256-px ``.png`` bytes) — deterministic."""
    grid = _render_grid()
    pngs = [(size, _png(_downsample(grid, size), size)) for size in _ICO_SIZES]
    header = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries = bytearray()
    payload = bytearray()
    for size, png in pngs:
        entries.extend(
            struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(png), offset)
        )
        payload.extend(png)
        offset += len(png)
    return header + entries + payload, pngs[0][1]


def main() -> None:
    root = Path(__file__).resolve().parent
    ico, png = build_assets()
    targets = (
        (root / "windows" / "schedule-forensics.ico", ico),
        (root / "schedule-forensics.png", png),
        # the served favicon is the same bytes — browser tab matches the desktop icon
        (root.parent / "src" / "schedule_forensics" / "web" / "static" / "favicon.ico", ico),
    )
    for path, data in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        print(f"wrote {path} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
