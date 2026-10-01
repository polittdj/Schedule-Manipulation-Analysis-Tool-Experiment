"""LODESTAR's icons — 33 Lucide glyphs as ONE inline SVG sprite (ADR-0543).

The studio's buttons name their icon (``icon("undo-2")``) and the page carries the sprite once, at
the top of ``<body>``: a hidden ``<svg>`` of ``<symbol>`` elements each ``<use href="#i-…">``
points at. Inline markup, not a fetched file — so no request, no CSP question, and the icons work
with scripting off. The glyphs are Lucide's (``lucide-static`` 1.49.0, the ISC licence below),
copied path for path: a 24-unit view box, a 2-unit round-capped, round-joined ``currentColor``
stroke and no fill — each icon takes its colour from the text around it. Std-lib only.

ISC License — Copyright (c) 2026 Lucide Icons and Contributors. Permission to use, copy, modify,
and/or distribute this software for any purpose with or without fee is hereby granted, provided
that the above copyright notice and this permission notice appear in all copies. THE SOFTWARE IS
PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING
ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""

from __future__ import annotations

#: ``name -> the glyph's inner SVG`` (Lucide's own markup, whitespace collapsed).
GLYPHS: dict[str, str] = {
    "arrow-left-right": (
        '<path d="M8 3 4 7l4 4"/><path d="M4 7h16"/><path d="m16 21 4-4-4-4"/><path d="M20 17H4"/>'
    ),
    "arrow-right": ('<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>'),
    "check": ('<path d="M20 6 9 17l-5-5"/>'),
    "chevron-down": ('<path d="m6 9 6 6 6-6"/>'),
    "circle-alert": (
        '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" '
        'x2="12.01" y1="16" y2="16"/>'
    ),
    "circle-check": ('<circle cx="12" cy="12" r="10"/><path d="m16 9-5.5 5.5L8 12"/>'),
    "circle-help": (
        '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 '
        '3"/><path d="M12 17h.01"/>'
    ),
    "compass": (
        '<circle cx="12" cy="12" r="10"/><path d="m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 '
        '1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z"/>'
    ),
    "download": (
        '<path d="M12 15V3"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path '
        'd="m7 10 5 5 5-5"/>'
    ),
    "file-down": (
        '<path d="M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 '
        '3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z"/><path d="M14 2v5a1 1 0 0 0 1 '
        '1h5"/><path d="M12 18v-6"/><path d="m9 15 3 3 3-3"/>'
    ),
    "file-spreadsheet": (
        '<path d="M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 '
        '3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z"/><path d="M14 2v5a1 1 0 0 0 1 '
        '1h5"/><path d="M8 13h2"/><path d="M14 13h2"/><path d="M8 17h2"/><path d="M14 17h2"/>'
    ),
    "git-compare-arrows": (
        '<circle cx="5" cy="6" r="3"/><path d="M12 6h5a2 2 0 0 1 2 2v7"/><path d="m15 9-3-3 '
        '3-3"/><circle cx="19" cy="18" r="3"/><path d="M12 18H7a2 2 0 0 1-2-2V9"/><path '
        'd="m9 15 3 3-3 3"/>'
    ),
    "grid-3x3": (
        '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 '
        '15h18"/><path d="M9 3v18"/><path d="M15 3v18"/>'
    ),
    "hard-drive": (
        '<path d="M10 16h.01"/><path d="M2.212 11.577a2 2 0 0 0-.212.896V18a2 2 0 0 0 2 '
        "2h16a2 2 0 0 0 2-2v-5.527a2 2 0 0 0-.212-.896L18.55 5.11A2 2 0 0 0 16.76 4H7.24a2 2 "
        '0 0 0-1.79 1.11z"/><path d="M21.946 12.013H2.054"/><path d="M6 16h.01"/>'
    ),
    "history": (
        '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 '
        '3v5h5"/><path d="M12 7v5l4 2"/>'
    ),
    "info": ('<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>'),
    "link-2": (
        '<path d="M9 17H7A5 5 0 0 1 7 7h2"/><path d="M15 7h2a5 5 0 1 1 0 10h-2"/><line '
        'x1="8" x2="16" y1="12" y2="12"/>'
    ),
    "map": (
        '<path d="M14.106 5.553a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 4.619v12.764a1 1 0 '
        "0 1-.553.894l-4.553 2.277a2 2 0 0 1-1.788 0l-4.212-2.106a2 2 0 0 0-1.788 0l-3.659 "
        "1.83A1 1 0 0 1 3 19.381V6.618a1 1 0 0 1 .553-.894l4.553-2.277a2 2 0 0 1 1.788 "
        '0z"/><path d="M15 5.764v15"/><path d="M9 3.236v15"/>'
    ),
    "maximize-2": (
        '<path d="M15 3h6v6"/><path d="m21 3-7 7"/><path d="m3 21 7-7"/><path d="M9 21H3v-6"/>'
    ),
    "play": (
        '<path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 '
        '1 5 19z"/>'
    ),
    "power": ('<path d="M12 2v10"/><path d="M18.4 6.6a9 9 0 1 1-12.77.04"/>'),
    "presentation": (
        '<path d="M2 3h20"/><path d="M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3"/><path d="m7 '
        '21 5-5 5 5"/>'
    ),
    "printer": (
        '<path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 '
        '2h-2"/><path d="M6 9V3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v6"/><rect x="6" y="14" '
        'width="12" height="8" rx="1"/>'
    ),
    "redo-2": (
        '<path d="m15 14 5-5-5-5"/><path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5A5.5 5.5 0 0 0 9.5 '
        '20H13"/>'
    ),
    "rotate-ccw": (
        '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>'
    ),
    "rows-3": (
        '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M21 9H3"/><path d="M21 15H3"/>'
    ),
    "search": ('<path d="m21 21-4.34-4.34"/><circle cx="11" cy="11" r="8"/>'),
    "sheet": (
        '<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><line x1="3" x2="21" y1="9" '
        'y2="9"/><line x1="3" x2="21" y1="15" y2="15"/><line x1="9" x2="9" y1="9" '
        'y2="21"/><line x1="15" x2="15" y1="9" y2="21"/>'
    ),
    "shield": (
        '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 '
        "0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 "
        '1 1z"/>'
    ),
    "triangle-alert": (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 '
        '1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>'
    ),
    "undo-2": (
        '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5a5.5 5.5 0 0 1-5.5 '
        '5.5H11"/>'
    ),
    "upload": (
        '<path d="M12 3v12"/><path d="m17 8-5-5-5 5"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 '
        '0 0 1-2-2v-4"/>'
    ),
    "x": ('<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'),
}


def sprite() -> str:
    """The hidden sprite every LODESTAR page carries once, at the top of ``<body>``."""
    symbols = "".join(
        f'<symbol id="i-{name}" viewBox="0 0 24 24">{body}</symbol>'
        for name, body in GLYPHS.items()
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" hidden aria-hidden="true" '
        'style="position:absolute">'
        f"{symbols}</svg>"
    )


def icon(name: str, size: int = 16, cls: str = "") -> str:
    """One icon — ``<svg>`` pointing at the sprite's symbol — sized ``size`` px, the Lucide stroke
    (2 units, round caps and joins, ``currentColor``). An unknown name is a ``KeyError``: a typo
    must fail the page's test, never ship an empty square."""
    if name not in GLYPHS:
        raise KeyError(f"no LODESTAR icon named {name!r}")
    extra = f" {cls}" if cls else ""
    return (
        f'<svg class="aismat-icon{extra}" width="{size}" height="{size}" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true" focusable="false">'
        f'<use href="#i-{name}"/></svg>'
    )
