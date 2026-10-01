"""Minimal, dependency-free PDF writer — the One-Pager as ONE page of vector ink (ADR-0544).

The third carrier beside the PowerPoint and Excel exports: a single 960 x 540 pt page (the slide's
own point grid — one layout unit = one PDF user-space unit, with y running UP, so every slide
``y`` lands at ``540 - y``) painted in the SAME order and the SAME colours as
:mod:`schedule_forensics.reports.pptx` paints the slide, so the page, the deck and the PDF are
three views of one :class:`~schedule_forensics.reports.onepager.Layout`. The geometry is NOT
computed here: a bar is a rounded rectangle at the layout's ``x0..x1``, a milestone the layout's
diamond, a risk (ADR-0544) an UPWARD triangle in its probability colour, a logic link the
layout's own polyline and head — nothing is placed, measured or nudged in this module except
the text squeeze below.

**Text.** The page sets its labels in the base-14 faces every PDF reader carries (Helvetica,
Helvetica-Bold, Symbol) — no font is embedded, so the file is small and carries nothing but the
slide. Those faces have no Unicode, so a label is ENCODED: WinAnsi for every Latin-1 letter and
the typographic marks the layouts use (the middle dot, the en and em dashes, the ellipsis,
the curly quotes, plus-minus), Symbol for the two arrows and the real minus (U+2192, U+2190,
U+2212), and ``?`` for anything else —
never a crash, never a dropped glyph (:func:`encode_runs`). The Adobe Core 14 AFM advance
widths of both Helvetica faces (and the three Symbol glyphs) are typed in below, so a centred or
right-aligned run lands where the layout says, and a run that measures WIDER than the width the
layout reserved for it (a label's ``label_w``, a summary box, a tag) is squeezed horizontally
(``Tz``) to that width — the PDF twin of the page's ``textLength`` fit — so no text ever paints
outside its box (the Change Summary defect the operator reported, 2026-10-01).

**Payload.** With ``payload`` (the LODESTAR session JSON, opaque bytes owned by
``reports/session_payload.py``) the PDF carries it as a standard EmbeddedFile named
:data:`ATTACHMENT_NAME` in the catalog's ``/EmbeddedFiles`` name tree — what ``pdfdetach`` lists
and any reader's attachment pane shows — so the export re-imports into the studio with its logic
and risks intact (:mod:`schedule_forensics.reports.pdf_read`). Std-lib only (``zlib``), the
bytes DETERMINISTIC for the same inputs: no clock is read — ``CreationDate`` is written only
from the ``made`` argument — and the cross-reference table is checked before the bytes leave
(:func:`schedule_forensics.reports.pdf_read.check_xref`). Like the deck, the page carries the
session's CUI marking top and bottom (Law 1).
"""

from __future__ import annotations

import datetime as dt
import zlib
from collections.abc import Sequence
from typing import Any

from schedule_forensics.reports.onepager import Layout
from schedule_forensics.reports.onepager_compare import CompareLayout
from schedule_forensics.reports.onepager_links import LINK_W, PlacedLink
from schedule_forensics.reports.pdf_read import check_xref
from schedule_forensics.reports.pptx import (
    _CUI,
    _DONE,
    _DUP,
    _GRID,
    _INK,
    _LINE,
    _LINK,
    _MUTED,
    _NEW,
    _PULL,
    _REMOVED,
    _SHAFT,
    _SLIP,
    _SYMBOL,
    _TODAY,
    _WHITE,
    _YEAR_SHADE,
    LANE_PALETTE,
    PRODUCT,
    RISK_COLORS,
    tint,
)

#: The page: the slide's own 960 x 540 pt frame (16:9 at 72 dpi — the layouts' unit).
PAGE_W, PAGE_H = 960.0, 540.0
#: The attachment's name in the ``/EmbeddedFiles`` tree and in a reader's attachment pane.
ATTACHMENT_NAME = "lodestar-session.json"
#: What the attachment pane says the file is.
ATTACHMENT_DESC = "LODESTAR session (lists, logic links, risks) - re-import to rebuild this slide"
#: The risk probability palette on white (ADR-0544): high / medium / low / unknown — the deck
#: writer's own ``RISK_COLORS``, one table for both carriers (the page's ``is-risk-*`` tokens
#: are their screen twins).
RISK_PALETTE = RISK_COLORS
#: A badge's text is the slide's white (the deck's ``_BADGE_INK``).
_BADGE_INK = _WHITE
#: A text's baseline sits this fraction of its size below the centre of its box: Helvetica's cap
#: height is 0.718 em, so caps centred on the box's middle put the baseline 0.36 em under it
#: (the deck's ``anchor="ctr"`` centres the line box; this centres the caps — a hair lower).
_BASELINE_F = 0.36
#: Line pitch of a multi-line block (a wrapped swimlane name, a summary strip), in ems — the
#: deck's single-spaced paragraph pitch.
_LINE_PITCH = 1.2
#: The halo under a label outside its bar and under a link's type tag: a white stroke of this
#: width BEHIND the glyphs (the deck's 1.5-pt glow, the page's ``paint-order: stroke``).
_HALO_W = 1.2
#: DrawingML's ``roundRect`` default corner: 16.667 % of the shorter side.
_ROUND_F = 0.16667
#: The Bézier arc constant for a quarter circle.
_KAPPA = 0.5522847498
#: Dash patterns in multiples of the line width: ``sysDot`` is a dot and two widths of gap,
#: ``dash`` four on and three off (DrawingML's presets, as LibreOffice renders them).
_DASHES = {"sysDot": (1.0, 2.0), "dash": (4.0, 3.0)}
#: The legend's risk triangle: the page's ``triangle(e.x + 5, cy, 3.6)`` (``lodestar_slide.js``).
_LEGEND_RISK_DX, _LEGEND_RISK_H = 5.0, 3.6
#: The legend's slip / pull-in arrowhead (``onepager_compare.js`` draws it 2.2 pt long).
_LEGEND_ARROW_HEAD = 2.2

# ── the Adobe Core 14 AFM advance widths (WinAnsiEncoding, codes 32..255) ────────────────────
# Each table is 224 entries, one per code point 32..255, in 1/1000 em. Typed from the Adobe
# Core 14 AFM files (Helvetica.afm / Helvetica-Bold.afm) in WinAnsi code order; the five codes
# WinAnsi leaves undefined (0x81 0x8D 0x8F 0x90 0x9D) and 0x7F take the bullet's 350, which the
# encoder never produces (cp1252 has no glyph there, so the character becomes ``?``).
# fmt: off
_HELVETICA: tuple[int, ...] = (
    # 0x20..0x2F   space ! " # $ % & ' ( ) * + , - . /
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    # 0x30..0x3F   0-9 : ; < = > ?
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    # 0x40..0x4F   @ A-O
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    # 0x50..0x5F   P-Z [ \ ] ^ _
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    # 0x60..0x6F   ` a-o
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    # 0x70..0x7F   p-z { | } ~ DEL
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584, 350,
    # 0x80..0x8F   Euro . quotesinglbase florin quotedblbase ellipsis dagger daggerdbl
    #              circumflex perthousand Scaron guilsinglleft OE . Zcaron .
    556, 350, 222, 556, 333, 1000, 556, 556, 333, 1000, 667, 333, 1000, 350, 611, 350,
    # 0x90..0x9F   . quoteleft quoteright quotedblleft quotedblright bullet endash emdash
    #              tilde trademark scaron guilsinglright oe . zcaron Ydieresis
    350, 222, 222, 333, 333, 350, 556, 1000, 333, 1000, 500, 333, 944, 350, 500, 667,
    # 0xA0..0xAF   nbsp exclamdown cent sterling currency yen brokenbar section dieresis
    #              copyright ordfeminine guillemotleft logicalnot shy registered macron
    278, 333, 556, 556, 556, 556, 260, 556, 333, 737, 370, 556, 584, 333, 737, 333,
    # 0xB0..0xBF   degree plusminus twosuperior threesuperior acute mu paragraph
    #              periodcentered cedilla onesuperior ordmasculine guillemotright
    #              onequarter onehalf threequarters questiondown
    400, 584, 333, 333, 333, 556, 537, 278, 333, 333, 365, 556, 834, 834, 834, 611,
    # 0xC0..0xCF   Agrave..Aring AE Ccedilla Egrave..Edieresis Igrave..Idieresis
    667, 667, 667, 667, 667, 667, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278,
    # 0xD0..0xDF   Eth Ntilde Ograve..Odieresis multiply Oslash Ugrave..Udieresis Yacute
    #              Thorn germandbls
    722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
    # 0xE0..0xEF   agrave..aring ae ccedilla egrave..edieresis igrave..idieresis
    556, 556, 556, 556, 556, 556, 889, 500, 556, 556, 556, 556, 278, 278, 278, 278,
    # 0xF0..0xFF   eth ntilde ograve..odieresis divide oslash ugrave..udieresis yacute
    #              thorn ydieresis
    556, 556, 556, 556, 556, 556, 556, 584, 611, 556, 556, 556, 556, 500, 556, 500,
)
_HELVETICA_BOLD: tuple[int, ...] = (
    # 0x20..0x2F
    278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278,
    # 0x30..0x3F
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611,
    # 0x40..0x4F
    975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
    # 0x50..0x5F
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
    # 0x60..0x6F
    333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611,
    # 0x70..0x7F
    611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584, 350,
    # 0x80..0x8F
    556, 350, 278, 556, 500, 1000, 556, 556, 333, 1000, 667, 333, 1000, 350, 611, 350,
    # 0x90..0x9F
    350, 278, 278, 500, 500, 350, 556, 1000, 333, 1000, 556, 333, 944, 350, 500, 667,
    # 0xA0..0xAF
    278, 333, 556, 556, 556, 556, 280, 556, 333, 737, 370, 556, 584, 333, 737, 333,
    # 0xB0..0xBF
    400, 584, 333, 333, 333, 611, 556, 278, 333, 333, 365, 556, 834, 834, 834, 611,
    # 0xC0..0xCF
    722, 722, 722, 722, 722, 722, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278,
    # 0xD0..0xDF
    722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
    # 0xE0..0xEF
    556, 556, 556, 556, 556, 556, 889, 556, 556, 556, 556, 556, 278, 278, 278, 278,
    # 0xF0..0xFF
    611, 611, 611, 611, 611, 611, 611, 584, 611, 611, 611, 611, 611, 556, 611, 556,
)
# fmt: on
assert len(_HELVETICA) == 224 and len(_HELVETICA_BOLD) == 224  # nosec B101  # table shape
#: The Symbol glyphs a layout uses, by Symbol code: ``arrowright`` ``arrowleft`` ``minus``.
_SYMBOL_CODES = {"\u2192": 0xAE, "\u2190": 0xAC, "\u2212": 0x2D}
_SYMBOL_W = {0xAE: 987, 0xAC: 987, 0x2D: 549}
#: The three page fonts' resource names.
_F_REGULAR, _F_BOLD, _F_SYMBOL = "F1", "F2", "F3"


def encode_runs(text: str, bold: bool) -> list[tuple[str, bytes]]:
    """``text`` as ``(font, bytes)`` pieces: WinAnsi (cp1252 — the same table, byte for byte,
    for every glyph the layouts use) in the Helvetica face asked for, the three Symbol glyphs
    in Symbol, and ``?`` for a character neither face carries. A ``\\r`` / ``\\n`` becomes a
    space — a run is one line."""
    face = _F_BOLD if bold else _F_REGULAR
    out: list[tuple[str, bytes]] = []
    buf = bytearray()
    for ch in text:
        code = _SYMBOL_CODES.get(ch)
        if code is not None:
            if buf:
                out.append((face, bytes(buf)))
                buf = bytearray()
            out.append((_F_SYMBOL, bytes([code])))
            continue
        if ch in "\r\n":
            ch = " "
        buf += ch.encode("cp1252", errors="replace")
    if buf:
        out.append((face, bytes(buf)))
    return out


def text_width(text: str, size: float, bold: bool = False) -> float:
    """The advance of ``text`` at ``size`` pt in Helvetica (``bold``: Helvetica-Bold), the
    Symbol pieces at their own widths — the AFM tables above, exactly."""
    total = 0
    for face, raw in encode_runs(text, bold):
        if face == _F_SYMBOL:
            total += sum(_SYMBOL_W[b] for b in raw)
        else:
            table = _HELVETICA_BOLD if face == _F_BOLD else _HELVETICA
            total += sum(table[b - 32] if b >= 32 else 0 for b in raw)
    return total * size / 1000.0


def _n(v: float) -> str:
    """A number for the content stream: at most three decimals, no trailing zeros, no ``-0``."""
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _rgb(hex6: str) -> str:
    return " ".join(_n(int(hex6[i : i + 2], 16) / 255.0) for i in (0, 2, 4))


def _lit(raw: bytes) -> bytes:
    """A PDF literal string of ``raw``: the three delimiters escaped, every byte outside
    printable ASCII written as an octal escape (so the stream stays 7-bit and diff-able)."""
    out = bytearray(b"(")
    for b in raw:
        if b in (0x28, 0x29, 0x5C):
            out += b"\\" + bytes([b])
        elif 32 <= b < 127:
            out.append(b)
        else:
            out += b"\\%03o" % b
    out += b")"
    return bytes(out)


def _text_string(s: str) -> bytes:
    """A PDF text string for the Info dictionary: ASCII as a literal, anything else as
    UTF-16BE with a byte-order mark in a hex string."""
    if all(32 <= ord(c) < 127 for c in s):
        return _lit(s.encode("ascii"))
    return b"<" + ("﻿" + s).encode("utf-16-be").hex().upper().encode("ascii") + b">"


class _Page:
    """Accumulates the one page's content stream, in paint order. The method set mirrors the
    deck writer's ``_Slide`` (``shape`` / ``arrow`` / ``segment`` / ``text`` / ``text_runs`` /
    ``vline`` / ``hline`` / ``freeform``) so the two painters read line for line; every call
    takes SLIDE points (y down) and the page flips them. Each shape is preceded by a ``%``
    comment carrying the deck's shape name, so a reader of the raw stream — and the tests —
    can count what was drawn, item by item."""

    def __init__(self) -> None:
        self.ops: list[bytes] = []

    def _mark(self, name: str) -> None:
        self.ops.append(b"% " + name.replace("\r", " ").replace("\n", " ").encode("utf-8"))

    @staticmethod
    def _py(y: float) -> float:
        return PAGE_H - y

    def _paint(
        self, fill: str | None, line: str | None, line_pt: float, dash: str | None
    ) -> tuple[str, str]:
        """The colour / width / dash state and the painting operator for one path."""
        state = []
        if fill:
            state.append(f"{_rgb(fill)} rg")
        if line:
            state.append(f"{_rgb(line)} RG {_n(line_pt)} w")
            if dash:
                on, off = _DASHES[dash]
                state.append(f"[{_n(on * line_pt)} {_n(off * line_pt)}] 0 d")
        op = "B" if fill and line else "f" if fill else "S" if line else "n"
        return " ".join(state), op

    def _path(self, prst: str, x: float, y: float, w: float, h: float) -> str:
        """The preset's outline in page space: ``rect`` / ``roundRect`` / ``diamond`` /
        ``ellipse`` / ``triangle`` (apex UP — a risk's glyph, ADR-0544)."""
        py = self._py
        if prst == "rect":
            return f"{_n(x)} {_n(py(y + h))} {_n(w)} {_n(h)} re"
        if prst == "roundRect":
            r = min(w, h) * _ROUND_F
            k = r * _KAPPA
            x1, y1 = x + w, y + h  # slide space; converted per vertex
            return " ".join(
                [
                    f"{_n(x + r)} {_n(py(y))} m",
                    f"{_n(x1 - r)} {_n(py(y))} l",
                    f"{_n(x1 - r + k)} {_n(py(y))} {_n(x1)} {_n(py(y + r - k))} "
                    f"{_n(x1)} {_n(py(y + r))} c",
                    f"{_n(x1)} {_n(py(y1 - r))} l",
                    f"{_n(x1)} {_n(py(y1 - r + k))} {_n(x1 - r + k)} {_n(py(y1))} "
                    f"{_n(x1 - r)} {_n(py(y1))} c",
                    f"{_n(x + r)} {_n(py(y1))} l",
                    f"{_n(x + r - k)} {_n(py(y1))} {_n(x)} {_n(py(y1 - r + k))} "
                    f"{_n(x)} {_n(py(y1 - r))} c",
                    f"{_n(x)} {_n(py(y + r))} l",
                    f"{_n(x)} {_n(py(y + r - k))} {_n(x + r - k)} {_n(py(y))} "
                    f"{_n(x + r)} {_n(py(y))} c",
                    "h",
                ]
            )
        if prst == "diamond":
            cx, cy = x + w / 2, y + h / 2
            return (
                f"{_n(cx)} {_n(py(y))} m {_n(x + w)} {_n(py(cy))} l "
                f"{_n(cx)} {_n(py(y + h))} l {_n(x)} {_n(py(cy))} l h"
            )
        if prst == "triangle":
            return (
                f"{_n(x + w / 2)} {_n(py(y))} m {_n(x + w)} {_n(py(y + h))} l "
                f"{_n(x)} {_n(py(y + h))} l h"
            )
        if prst == "ellipse":
            rx, ry = w / 2, h / 2
            cx, cy = x + rx, y + ry
            kx, ky = rx * _KAPPA, ry * _KAPPA
            return " ".join(
                [
                    f"{_n(cx + rx)} {_n(py(cy))} m",
                    f"{_n(cx + rx)} {_n(py(cy + ky))} {_n(cx + kx)} {_n(py(cy + ry))} "
                    f"{_n(cx)} {_n(py(cy + ry))} c",
                    f"{_n(cx - kx)} {_n(py(cy + ry))} {_n(cx - rx)} {_n(py(cy + ky))} "
                    f"{_n(cx - rx)} {_n(py(cy))} c",
                    f"{_n(cx - rx)} {_n(py(cy - ky))} {_n(cx - kx)} {_n(py(cy - ry))} "
                    f"{_n(cx)} {_n(py(cy - ry))} c",
                    f"{_n(cx + kx)} {_n(py(cy - ry))} {_n(cx + rx)} {_n(py(cy - ky))} "
                    f"{_n(cx + rx)} {_n(py(cy))} c h",
                ]
            )
        raise ValueError(f"unknown preset {prst!r}")

    def shape(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str | None,
        *,
        prst: str = "rect",
        line: str | None = None,
        line_pt: float = 0.5,
        dash: str | None = None,
        name: str,
    ) -> None:
        self._mark(name)
        state, op = self._paint(fill, line, line_pt, dash)
        self.ops.append(f"q {state} {self._path(prst, x, y, w, h)} {op} Q".encode("ascii"))

    def arrow(
        self,
        x0: float,
        x1: float,
        y: float,
        color: str,
        width_pt: float,
        *,
        head: float,
        name: str,
    ) -> None:
        """A horizontal line from ``x0`` to ``x1`` with a solid head ``head`` long at ``x1``,
        pointing the way it runs — the page's ``arrow()`` (``onepager_compare.js``); ``head``
        is the layout's own ``arrow_head`` for an item, the legend's 2.2 for a legend entry."""
        self._mark(name)
        d = 1.0 if x1 >= x0 else -1.0
        py = self._py(y)
        bx = x1 - d * head
        self.ops.append(
            (
                f"q {_rgb(color)} RG {_rgb(color)} rg {_n(width_pt)} w "
                f"{_n(x0)} {_n(py)} m {_n(bx)} {_n(py)} l S "
                f"{_n(x1)} {_n(py)} m {_n(bx)} {_n(py + head * 0.5)} l "
                f"{_n(bx)} {_n(py - head * 0.5)} l h f Q"
            ).encode("ascii")
        )

    def segment(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        color: str,
        width_pt: float,
        *,
        name: str,
    ) -> None:
        """A straight round-capped stroke — column D's check is two of them (ADR-0524)."""
        self._mark(name)
        self.ops.append(
            (
                f"q {_rgb(color)} RG {_n(width_pt)} w 1 J 1 j "
                f"{_n(x0)} {_n(self._py(y0))} m {_n(x1)} {_n(self._py(y1))} l S Q"
            ).encode("ascii")
        )

    def vline(
        self,
        x: float,
        y0: float,
        y1: float,
        color: str,
        width_pt: float,
        *,
        dash: str | None = None,
        name: str,
    ) -> None:
        self._mark(name)
        state, _op = self._paint(None, color, width_pt, dash)
        self.ops.append(
            (f"q {state} {_n(x)} {_n(self._py(y0))} m {_n(x)} {_n(self._py(y1))} l S Q").encode(
                "ascii"
            )
        )

    def hline(
        self, x0: float, x1: float, y: float, color: str, width_pt: float, *, name: str
    ) -> None:
        self._mark(name)
        py = self._py(y)
        self.ops.append(
            (
                f"q {_rgb(color)} RG {_n(width_pt)} w {_n(x0)} {_n(py)} m {_n(x1)} {_n(py)} l S Q"
            ).encode("ascii")
        )

    def freeform(
        self,
        points: Sequence[tuple[float, float]],
        *,
        line: str | None,
        line_pt: float,
        fill: str | None = None,
        closed: bool = False,
        name: str,
    ) -> None:
        """The layout's own polyline (a link's shaft, open, round-joined) or polygon (its head,
        closed and filled) — the same points the page and the deck draw."""
        if not points:
            return
        self._mark(name)
        state, op = self._paint(fill, line, line_pt, None)
        path = " ".join(
            f"{_n(x)} {_n(self._py(y))} {'m' if i == 0 else 'l'}" for i, (x, y) in enumerate(points)
        )
        if closed:
            path += " h"
        self.ops.append(f"q {state} 1 J 1 j {path} {op} Q".encode("ascii"))

    # ── text ──────────────────────────────────────────────────────────────────────────────

    def _line_ops(
        self,
        x: float,
        baseline: float,
        runs: Sequence[tuple[str, str, bool]],
        size: float,
        w: float,
        align: str,
    ) -> tuple[str, bool]:
        """One line of runs as text operators, placed by the AFM widths: ``align`` ``l`` /
        ``ctr`` / ``r`` within ``x..x + w``, and SQUEEZED (``Tz``) to ``w`` when the line
        measures wider — returns the operators and whether it had to squeeze."""
        natural = sum(text_width(t, size, b) for t, _c, b in runs)
        squeeze = w > 0 and natural > w + 1e-6
        tz = (w / natural * 100.0) if squeeze else 100.0
        drawn = min(natural, w) if squeeze else natural
        if align == "ctr":
            x = x + (w - drawn) / 2
        elif align == "r":
            x = x + w - drawn
        ops = [f"BT {_n(tz)} Tz 1 0 0 1 {_n(x)} {_n(self._py(baseline))} Tm"]
        for text, color, bold in runs:
            ops.append(f"{_rgb(color)} rg")
            for face, raw in encode_runs(text, bold):
                ops.append(f"/{face} {_n(size)} Tf {_lit(raw).decode('ascii')} Tj")
        ops.append("ET")
        return " ".join(ops), squeeze

    def _block(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        lines: Sequence[Sequence[tuple[str, str, bool]]],
        size: float,
        align: str,
        anchor: str,
        glow: bool,
        name: str,
    ) -> None:
        """Lines of runs in the box ``(x, y, w, h)``: ``anchor`` ``ctr`` centres the block
        vertically (the deck's default), ``t`` hangs it from the top. With ``glow`` every line
        is first STROKED in the slide's white (a halo behind the glyphs), then filled."""
        self._mark(name)
        pitch = size * _LINE_PITCH
        top = (y + h / 2 - len(lines) * pitch / 2) if anchor == "ctr" else y
        out: list[str] = []
        for i, runs in enumerate(lines):
            baseline = top + (i + 0.5) * pitch + size * _BASELINE_F
            ops, squeezed = self._line_ops(x, baseline, runs, size, w, align)
            if glow:
                out.append(f"q {_rgb(_WHITE)} RG {_n(_HALO_W)} w 1 j 1 Tr {ops} Q")
            out.append(f"q {ops} Q" + (" % squeezed" if squeezed else ""))
        self.ops.append("\n".join(out).encode("ascii"))

    def text(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        lines: Sequence[str],
        size_pt: float,
        color: str,
        *,
        bold: bool = False,
        align: str = "l",
        anchor: str = "ctr",
        glow: bool = False,
        name: str,
    ) -> None:
        self._block(
            x, y, w, h, [[(ln, color, bold)] for ln in lines], size_pt, align, anchor, glow, name
        )

    def text_runs(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        runs: Sequence[tuple[str, str, bool]],
        size_pt: float,
        *,
        align: str = "l",
        anchor: str = "ctr",
        glow: bool = False,
        name: str,
    ) -> None:
        """One line of several ``(text, colour, bold)`` runs — a label and its calendar-day
        delta or a risk's impact in its own colour, squeezed together as one line."""
        self._block(x, y, w, h, [list(runs)], size_pt, align, anchor, glow, name)

    def stream(self) -> bytes:
        return b"\n".join(self.ops) + b"\n"


# ── the document ──────────────────────────────────────────────────────────────────────────


def _obj(num: int, body: bytes) -> bytes:
    return b"%d 0 obj\n" % num + body + b"\nendobj\n"


def _stream_obj(num: int, dictionary: bytes, data: bytes) -> bytes:
    """A Flate-coded stream object; ``dictionary`` is the extra entries (``/Type`` …)."""
    z = zlib.compress(data, 9)
    return _obj(
        num,
        b"<< "
        + dictionary
        + b"/Filter /FlateDecode /Length %d >>\nstream\n" % len(z)
        + z
        + b"\nendstream",
    )


def _document(
    page: _Page, *, title: str, product: str, payload: bytes | None, made: dt.date | None
) -> bytes:
    """Assemble the one-page file: catalog, pages, page, content, the three fonts, the Info
    dictionary and — with ``payload`` — the Filespec and EmbeddedFile pair the catalog's
    ``/EmbeddedFiles`` name tree points at. Objects are numbered in this fixed order, the xref
    offsets are measured as the bytes are laid down, and the finished table is re-read by the
    reader's own check before the bytes are returned."""
    name = ATTACHMENT_NAME.encode("ascii")
    names = (
        b" /Names << /EmbeddedFiles << /Names [" + _lit(name) + b" 9 0 R] >> >>"
        if payload is not None
        else b""
    )
    info = b"<< /Title " + _text_string(title) + b" /Producer " + _text_string(product)
    info += b" /Creator " + _text_string(product)
    if made is not None:
        info += b" /CreationDate (D:%04d%02d%02d000000Z)" % (made.year, made.month, made.day)
    info += b" >>"
    objs: list[bytes] = [
        _obj(1, b"<< /Type /Catalog /Pages 2 0 R" + names + b" >>"),
        _obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"),
        _obj(
            3,
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Contents 4 0 R "
            b"/Resources << /Font << /F1 5 0 R /F2 6 0 R /F3 7 0 R >> >> >>"
            % (int(PAGE_W), int(PAGE_H)),
        ),
        _stream_obj(4, b"", page.stream()),
        _obj(
            5,
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        ),
        _obj(
            6,
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
            b"/Encoding /WinAnsiEncoding >>",
        ),
        _obj(7, b"<< /Type /Font /Subtype /Type1 /BaseFont /Symbol >>"),
        _obj(8, info),
    ]
    if payload is not None:
        objs.append(
            _obj(
                9,
                b"<< /Type /Filespec /F "
                + _lit(name)
                + b" /UF "
                + _lit(name)
                + b" /Desc "
                + _lit(ATTACHMENT_DESC.encode("ascii"))
                + b" /EF << /F 10 0 R >> >>",
            )
        )
        objs.append(
            _stream_obj(
                10,
                b"/Type /EmbeddedFile /Subtype /application#2Fjson "
                b"/Params << /Size %d >> " % len(payload),
                payload,
            )
        )
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = []
    for body in objs:
        offsets.append(len(out))
        out += body
    xref_at = len(out)
    size = len(objs) + 1
    out += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R /Info 8 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        size,
        xref_at,
    )
    data = bytes(out)
    problem = check_xref(data)
    if problem:  # the writer measured its own offsets: a bug, not a case (a test forces it)
        raise RuntimeError(f"PDF cross-reference self-check failed: {problem}")
    return data


# ── the two painters (the deck writer's paint order, call for call) ───────────────────────


def _risk_color(p: Any) -> str:
    return RISK_PALETTE.get(str(getattr(p, "prob", "") or "unknown"), RISK_PALETTE["unknown"])


def _is_risk(p: Any) -> bool:
    return str(getattr(p, "kind", "item")) == "risk"


def _frame(pg: _Page, lay: Layout | CompareLayout, marking: str, right: float) -> None:
    """Everything above the lanes, shared by both slides: the two CUI strips, the title and
    subtitle, the year bands and labels, the dotted month lines and labels, the year lines and
    the header rule out to ``right`` (the chart's edge, or the summary column's on Compare)."""
    pg.text(0, 1, lay.w, 8, [marking], 6, _CUI, bold=True, align="ctr", name="CUI marking (top)")
    pg.text(
        0,
        lay.h - 9,
        lay.w,
        8,
        [marking],
        6,
        _CUI,
        bold=True,
        align="ctr",
        name="CUI marking (bottom)",
    )
    pg.text(
        lay.lane_col_x0, lay.title_y - 15, 760, 18, [lay.title], 16, _INK, bold=True, name="Title"
    )
    if lay.subtitle:
        sub_w = 900 if isinstance(lay, CompareLayout) else 760
        pg.text(
            lay.lane_col_x0, lay.sub_y - 8, sub_w, 10, [lay.subtitle], 7.5, _MUTED, name="Subtitle"
        )
    top, bot = lay.year_y0, lay.lanes_y1
    for band in lay.years:
        pg.shape(
            band.x0,
            top,
            band.x1 - band.x0,
            bot - top,
            _YEAR_SHADE[band.shade],
            name=f"Year band {band.label}",
        )
        if band.x1 - band.x0 > 18:
            pg.text(
                band.x0,
                top,
                band.x1 - band.x0,
                lay.year_y1 - top,
                [band.label],
                8,
                _INK,
                bold=True,
                align="ctr",
                name=f"Year {band.label}",
            )
    for tick in lay.months:
        pg.vline(
            tick.x, lay.year_y1, bot, _GRID, 0.4, dash="sysDot", name=f"Month line {tick.x:.0f}"
        )
        if tick.label:
            half = tick.label_x - tick.x
            pg.text(
                tick.x,
                lay.year_y1,
                2 * half,
                lay.mon_y1 - lay.year_y1,
                [tick.label],
                lay.month_pt,
                _MUTED,
                align="ctr",
                name="Month label",
            )
    for band in lay.years:
        pg.vline(band.x0, top, bot, _LINE, 0.6, name="Year line")
    pg.vline(lay.x1, top, bot, _LINE, 0.6, name="Year line")
    pg.hline(lay.lane_col_x0, right, lay.mon_y1, _LINE, 0.7, name="Header line")


def _lanes(pg: _Page, lay: Layout | CompareLayout) -> None:
    """The swimlane bands: the 7 % tint across the chart, the 16 % name block, the solid edge,
    the wrapped name."""
    col_w = lay.lane_col_x1 - lay.lane_col_x0
    for lane in lay.lanes:
        hue = LANE_PALETTE[lane.color % len(LANE_PALETTE)]
        h = lane.y1 - lane.y0
        pg.shape(
            lay.lane_col_x0,
            lane.y0,
            lay.x1 - lay.lane_col_x0,
            h,
            tint(hue, 0.07),
            name=f"Lane: {lane.name}",
        )
        pg.shape(
            lay.lane_col_x0, lane.y0, col_w, h, tint(hue, 0.16), name=f"Lane label: {lane.name}"
        )
        pg.shape(lay.lane_col_x0, lane.y0, 3, h, hue, name="Lane edge")
        pg.text(
            lay.lane_col_x0 + 7,
            lane.y0,
            col_w - 8,
            h,
            lane.lines,
            lane.name_pt,
            _INK,
            bold=True,
            name=f"Lane name: {lane.name}",
        )


def _link_name(ln: PlacedLink) -> str:
    return f"{ln.pred_name} \u2192 {ln.succ_name} ({ln.kind})"


def _link_shafts(pg: _Page, links: Sequence[PlacedLink]) -> None:
    """Every drawn logic link's SHAFT — under every item (ADR-0543)."""
    for ln in links:
        pg.freeform(
            ln.shaft, line=_SHAFT, line_pt=LINK_W, name=f"Logic link line: {_link_name(ln)}"
        )


def _link_heads(pg: _Page, links: Sequence[PlacedLink]) -> None:
    """Every drawn logic link's ARROWHEAD and, for anything but FS, its haloed type tag — over
    the items, under the data-date line (ADR-0543). The tag's box is the deck's."""
    for ln in links:
        what = _link_name(ln)
        pg.freeform(
            ln.head, line=None, line_pt=0, fill=_LINK, closed=True, name=f"Logic link head: {what}"
        )
        if ln.tag:
            w = len(ln.tag) * ln.tag_pt * 0.62 + 1
            x = ln.tag_x if ln.tag_anchor == "start" else ln.tag_x - w
            pg.text(
                x,
                ln.tag_y - ln.tag_pt,
                w,
                ln.tag_pt * 1.3,
                [ln.tag],
                ln.tag_pt,
                _LINK,
                bold=True,
                align="l" if ln.tag_anchor == "start" else "r",
                glow=True,
                name=f"Logic link type: {what}",
            )


def _done_badge(pg: _Page, cx: float, cy: float, r: float, *, name: str) -> None:
    """Column D's check (ADR-0524): a ``--muted`` disc with a white check (the deck's points)."""
    pg.shape(cx - r, cy - r, 2 * r, 2 * r, _DONE, prst="ellipse", name=f"Done: {name}")
    w = max(0.35, r * 0.32)
    vx, vy = cx - 0.12 * r, cy + 0.42 * r
    pg.segment(cx - 0.5 * r, cy + 0.02 * r, vx, vy, _WHITE, w, name=f"Done tick: {name}")
    pg.segment(vx, vy, cx + 0.55 * r, cy - 0.4 * r, _WHITE, w, name=f"Done tick: {name}")


def _today(pg: _Page, lay: Layout | CompareLayout) -> None:
    """The data-date line and its caption."""
    if lay.today_x is None:
        return
    pg.vline(lay.today_x, lay.year_y0, lay.lanes_y1, _TODAY, 1.5, name="Data date")
    at_start = lay.today_label_anchor == "start"
    pg.text(
        lay.today_label_x if at_start else lay.today_label_x - 90,
        lay.today_label_y - 6,
        90,
        8,
        [lay.today_label],
        6,
        _TODAY,
        bold=True,
        align="l" if at_start else "r",
        name="Data date label",
    )


def _legend_glyph(pg: _Page, kind: str, label: str, x: float, cy: float, color: int) -> None:
    """The legend glyphs both slides share — and, as the deck does, a lane swatch for any kind
    neither painter names."""
    if kind == "done":
        pg.shape(x + 2, cy - 3, 6, 6, _DONE, prst="ellipse", name="Legend: complete")
        vx, vy = x + 4.64, cy + 1.26
        pg.segment(x + 3.5, cy + 0.06, vx, vy, _WHITE, 0.6, name="Done tick: legend")
        pg.segment(vx, vy, x + 6.65, cy - 1.2, _WHITE, 0.6, name="Done tick: legend")
    elif kind == "today":
        pg.vline(x + 5, cy - 4, cy + 4, _TODAY, 1.5, name="Legend: data date")
    elif kind == "link":
        pg.freeform([(x, cy), (x + 7.4, cy)], line=_SHAFT, line_pt=LINK_W, name="Legend: link")
        pg.freeform(
            [(x + 10, cy), (x + 7.4, cy - 1.3), (x + 7.4, cy + 1.3)],
            line=None,
            line_pt=0,
            fill=_LINK,
            closed=True,
            name="Legend: link head",
        )
    elif kind.startswith("risk-"):
        # the page's ``triangle(e.x + 5, cy, 3.6)``: apex up, in the probability colour
        hh = _LEGEND_RISK_H
        pg.shape(
            x + _LEGEND_RISK_DX - hh,
            cy - hh,
            2 * hh,
            2 * hh,
            RISK_PALETTE.get(kind[5:], RISK_PALETTE["unknown"]),
            prst="triangle",
            line=_WHITE,
            name=f"Legend: {kind}",
        )
    else:
        hue = LANE_PALETTE[color % len(LANE_PALETTE)]
        pg.shape(x, cy - 3, 10, 6, hue, prst="roundRect", name=f"Legend: {label}")


def _footer(pg: _Page, lay: Layout | CompareLayout, source: str, right: float, readme: str) -> None:
    w = 380 if isinstance(lay, CompareLayout) else 300
    pg.text(lay.lane_col_x0, lay.h - 18, 500, 8, [source], 5.5, _MUTED, name="Source")
    pg.text(right - w, lay.h - 18, w, 8, [readme], 5.5, _MUTED, align="r", name="Read-me")


def render_onepager_pdf(
    layout: Layout,
    *,
    marking: str,
    source: str,
    product: str = PRODUCT,
    payload: bytes | None = None,
    made: dt.date | None = None,
) -> bytes:
    """The Timeline layout as one 960 x 540 pt PDF page, painted in the deck writer's order.
    ``marking`` is the session's CUI banner text (top and bottom strips), ``source`` the
    provenance footer, ``product`` the program named as the file's Producer, ``payload`` the
    session JSON to embed (``None``: no attachment), ``made`` the date written as
    ``CreationDate`` (``None``: omitted — the bytes never depend on the clock)."""
    lay = layout
    pg = _Page()
    _frame(pg, lay, marking, lay.x1)
    _lanes(pg, lay)
    _link_shafts(pg, lay.links)  # under every item (ADR-0543)
    for p in lay.items:
        hue = LANE_PALETTE[lay.lanes[p.lane].color % len(LANE_PALETTE)]
        risk = _is_risk(p)
        if risk:
            ms = p.ms or lay.ms
            pg.shape(
                p.x0 - ms / 2,
                p.y - ms / 2,
                ms,
                ms,
                _risk_color(p),
                prst="triangle",
                line=_WHITE,
                name=f"Risk: {p.name}",
            )
        elif p.milestone:
            ms = p.ms or lay.ms  # its own size at the chart's edge (ADR-0540 review F1)
            pg.shape(
                p.x0 - ms / 2,
                p.y - ms / 2,
                ms,
                ms,
                hue,
                prst="diamond",
                line=_WHITE,
                name=f"Milestone: {p.name}",
            )
        else:
            pg.shape(
                p.x0,
                p.y - lay.bar_h / 2,
                p.x1 - p.x0,
                lay.bar_h,
                hue,
                prst="roundRect",
                line=_WHITE,
                name=f"Activity: {p.name}",
            )
        if p.done and p.done_x is not None:
            _done_badge(pg, p.done_x, p.y, p.done_r, name=p.name)
        box_w, box_y = p.label_w + 4, p.y - lay.row_h / 2
        ink = _WHITE if p.inside else _INK
        runs: list[tuple[str, str, bool]] = [(p.label, ink, bool(p.inside))]
        impact = str(getattr(p, "impact", "") or "") if risk else ""
        if impact:
            runs.append((" " + impact, _risk_color(p), True))
        if p.inside or p.label_anchor == "start":
            pg.text_runs(
                p.label_x,
                box_y,
                box_w,
                lay.row_h,
                runs,
                lay.label_pt,
                glow=not p.inside,
                name=f"Label: {p.name}",
            )
        else:
            pg.text_runs(
                p.label_x - box_w,
                box_y,
                box_w,
                lay.row_h,
                runs,
                lay.label_pt,
                align="r",
                glow=True,
                name=f"Label: {p.name}",
            )
    _link_heads(pg, lay.links)  # over every item, under the data-date line (ADR-0543)
    _today(pg, lay)
    pg.hline(lay.lane_col_x0, lay.x1, lay.legend_y0, _LINE, 0.7, name="Legend line")
    lp = lay.legend_pt
    for e in lay.legend:
        cy = e.y - 2.5
        if e.kind == "activity":
            pg.shape(e.x, cy - 2.5, 10, 5, _SYMBOL, prst="roundRect", name="Legend: activity")
        elif e.kind == "milestone":
            pg.shape(e.x + 1.5, cy - 3.5, 7, 7, _SYMBOL, prst="diamond", name="Legend: milestone")
        else:
            _legend_glyph(pg, e.kind, e.label, e.x, cy, e.color)
        pg.text(
            e.x + 13, e.y - lp - 2, e.w, lp + 4, [e.label], lp, _INK, name=f"Legend text: {e.label}"
        )
    _footer(
        pg,
        lay,
        source,
        lay.x1,
        "Timeline: months and years \u00b7 bars = activities \u00b7 diamonds = milestones \u00b7 "
        "red line = data date",
    )
    return _document(pg, title=lay.title, product=product, payload=payload, made=made)


def _tag_color(badge: str) -> str:
    return {"NEW": _NEW, "REMOVED": _REMOVED}.get(badge, _DUP)


def render_onepager_compare_pdf(
    layout: CompareLayout,
    *,
    marking: str,
    source: str,
    product: str = PRODUCT,
    payload: bytes | None = None,
    made: dt.date | None = None,
) -> bytes:
    """The Compare layout as one PDF page: the prior position a dashed ghost, the current one
    solid, an arrow per moved finish with its calendar-day delta, NEW / REMOVED / DUPLICATE NAME
    tags, the per-swimlane summary column (its strips squeezed to their boxes), and risks as
    triangles (ADR-0544). Parameters as :func:`render_onepager_pdf`."""
    lay = layout
    pg = _Page()
    _frame(pg, lay, marking, lay.summary_x1)
    pg.text(
        lay.summary_x0 + 2,
        lay.year_y1,
        lay.summary_x1 - lay.summary_x0 - 2,
        lay.mon_y1 - lay.year_y1,
        ["CHANGE SUMMARY"],
        5.5,
        _MUTED,
        bold=True,
        name="Summary header",
    )
    _lanes(pg, lay)
    for box in lay.summaries:
        hue = LANE_PALETTE[lay.lanes[box.lane].color % len(LANE_PALETTE)]
        pg.shape(
            box.x0,
            box.y0,
            box.x1 - box.x0,
            box.y1 - box.y0,
            tint(hue, 0.10),
            name=f"Summary: {lay.lanes[box.lane].name}",
        )
        pg.text(
            box.x0 + 2.5,
            box.y0,
            box.x1 - box.x0 - 4,
            box.y1 - box.y0,
            box.lines,
            box.pt,
            _INK,
            name=f"Summary text: {lay.lanes[box.lane].name}",
        )
    _link_shafts(pg, lay.links)  # under every item (ADR-0543)
    for p in lay.items:
        hue = LANE_PALETTE[lay.lanes[p.lane].color % len(LANE_PALETTE)]
        risk = _is_risk(p) or p.status == "risk"
        if p.ghost_x0 is not None and p.ghost_x1 is not None:
            if p.ghost_milestone:
                gms = p.ghost_ms or lay.ms
                pg.shape(
                    p.ghost_x0 - gms / 2,
                    p.y - gms / 2,
                    gms,
                    gms,
                    None,
                    prst="diamond",
                    line=hue,
                    line_pt=0.75,
                    dash="dash",
                    name=f"Prior milestone: {p.name}",
                )
            else:
                pg.shape(
                    p.ghost_x0,
                    p.y - lay.bar_h / 2,
                    p.ghost_x1 - p.ghost_x0,
                    lay.bar_h,
                    None,
                    prst="roundRect",
                    line=hue,
                    line_pt=0.75,
                    dash="dash",
                    name=f"Prior activity: {p.name}",
                )
        if p.arrow_x0 is not None and p.arrow_x1 is not None:
            slip = p.status == "slipped"
            pg.arrow(
                p.arrow_x0,
                p.arrow_x1,
                p.arrow_y,
                _SLIP if slip else _PULL,
                0.9,
                head=lay.arrow_head,
                name=f"{'Slip' if slip else 'Pull-in'}: {p.name}",
            )
        if p.x0 is not None and p.x1 is not None:
            if risk:
                ms = p.ms or lay.ms
                pg.shape(
                    p.x0 - ms / 2,
                    p.y - ms / 2,
                    ms,
                    ms,
                    _risk_color(p),
                    prst="triangle",
                    line=_WHITE,
                    name=f"Risk: {p.name}",
                )
            elif p.milestone:
                ms = p.ms or lay.ms
                pg.shape(
                    p.x0 - ms / 2,
                    p.y - ms / 2,
                    ms,
                    ms,
                    hue,
                    prst="diamond",
                    line=_WHITE,
                    name=f"Milestone: {p.name}",
                )
            else:
                pg.shape(
                    p.x0,
                    p.y - lay.bar_h / 2,
                    p.x1 - p.x0,
                    lay.bar_h,
                    hue,
                    prst="roundRect",
                    line=_WHITE,
                    name=f"Activity: {p.name}",
                )
        if p.done and p.done_x is not None:
            _done_badge(pg, p.done_x, p.y, p.done_r, name=p.name)
        if risk:
            delta_color = _risk_color(p)
            extra = str(getattr(p, "impact", "") or "") or p.delta
        else:
            delta_color = {"slipped": _SLIP, "pulled in": _PULL}.get(p.status, _DUP)
            extra = p.delta
        ink = _WHITE if p.inside else _INK
        runs: list[tuple[str, str, bool]] = [(p.label, ink, bool(p.inside))]
        if extra:
            runs.append((" " + extra, delta_color, True))
        box_w, box_y = p.label_w + 4, p.y - lay.row_h / 2
        if p.label_anchor == "end":
            right = p.label_x - (p.badge_w + 2 if p.badge else 0.0)
            pg.text_runs(
                right - box_w,
                box_y,
                box_w,
                lay.row_h,
                runs,
                lay.label_pt,
                align="r",
                glow=not p.inside,
                name=f"Label: {p.name}",
            )
        else:
            pg.text_runs(
                p.label_x,
                box_y,
                box_w,
                lay.row_h,
                runs,
                lay.label_pt,
                glow=not p.inside,
                name=f"Label: {p.name}",
            )
        if p.badge:
            pg.shape(
                p.badge_x,
                p.y - lay.label_pt * 0.6,
                p.badge_w,
                lay.label_pt * 1.2,
                _tag_color(p.badge),
                prst="roundRect",
                name=f"Tag: {p.badge} \u2014 {p.name}",
            )
            pg.text(
                p.badge_x,
                p.y - lay.label_pt * 0.6,
                p.badge_w,
                lay.label_pt * 1.2,
                [p.badge],
                lay.label_pt,
                _BADGE_INK,
                bold=True,
                align="ctr",
                name=f"Tag text: {p.badge} \u2014 {p.name}",
            )
    _link_heads(pg, lay.links)  # over every item, under the data-date line (ADR-0543)
    _today(pg, lay)
    pg.hline(lay.lane_col_x0, lay.summary_x1, lay.legend_y0, _LINE, 0.7, name="Legend line")
    lp = lay.legend_pt
    for e in lay.legend:
        cy = e.y - 2.5
        if e.kind == "activity":
            pg.shape(e.x, cy - 2.5, 10, 5, _SYMBOL, prst="roundRect", name="Legend: current")
        elif e.kind in ("ghost", "removed"):
            pg.shape(
                e.x,
                cy - 2.5,
                10,
                5,
                None,
                prst="roundRect",
                line=_SYMBOL,
                line_pt=0.75,
                dash="dash",
                name=f"Legend: {e.kind}",
            )
        elif e.kind == "slip":
            pg.arrow(e.x, e.x + 10, cy, _SLIP, 0.9, head=_LEGEND_ARROW_HEAD, name="Legend: slip")
        elif e.kind == "pull":
            pg.arrow(e.x + 10, e.x, cy, _PULL, 0.9, head=_LEGEND_ARROW_HEAD, name="Legend: pull-in")
        elif e.kind == "new":
            pg.shape(e.x, cy - 3, 10, 6, _NEW, prst="roundRect", name="Legend: new")
        else:
            _legend_glyph(pg, e.kind, e.label, e.x, cy, e.color)
        pg.text(
            e.x + 13, e.y - lp - 2, e.w, lp + 4, [e.label], lp, _INK, name=f"Legend text: {e.label}"
        )
    _footer(
        pg,
        lay,
        source,
        lay.summary_x1,
        "Solid = current (unchanged: once) \u00b7 ghost = prior \u00b7 arrow = finish moved "
        "(\u00b1N cal d) \u00b7 check = complete (col. D) \u00b7 red line = data date",
    )
    return _document(pg, title=lay.title, product=product, payload=payload, made=made)
