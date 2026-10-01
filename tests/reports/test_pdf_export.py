"""The One-Pager PDF export and its payload reader (ADR-0544).

Oracles, in order of independence from the module under test:

* **poppler** (``pdfinfo`` / ``pdftotext`` / ``pdfdetach`` / ``pdftoppm``, run as subprocesses;
  a missing binary SKIPS the test by name) reads the file back with a parser this repo did not
  write: the page size, the title and labels as text, the attachment's name and BYTES, a
  rendered bitmap whose pixels are sampled, and — through ``pdftotext -bbox`` — poppler's OWN
  base-14 metrics, against which every one of the 430 (code, face) pairs of the typed AFM
  tables is compared, and inside which every word of the Change Summary must stay.
* **the raw content stream**, inflated by the test's own four lines, where every shape the
  painter drew is counted by the ``%`` marker that precedes it.
* **a hand-built PDF** (the refuter's std-lib builder, copied here) for the reader: direct and
  indirect ``/Length``, the compact no-space syntax a re-save writes, a raw (unfiltered)
  stream, a browser-like file with no attachment, an attachment that is some other JSON.

Every load-bearing check has a ``test_mutation_*`` twin that breaks the product in memory and
asserts the SAME checker goes red by name (QC-1). ``Hello`` in Helvetica 10 pt measures 22.78
(H 722 + e 556 + l 222 + l 222 + o 556 = 2278 / 1000 x 10) — the kickoff's "22.24" was an
arithmetic slip; its own formula and poppler both give 22.78.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import re
import shutil
import subprocess
import zlib
from collections.abc import Callable
from dataclasses import dataclass, fields, replace
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest

from schedule_forensics.reports import pdf, pdf_read
from schedule_forensics.reports.onepager import (
    Layout,
    LegendEntry,
    OnePagerDoc,
    Placed,
    build_layout,
    parse_rows,
    parse_workbook,
)
from schedule_forensics.reports.onepager_compare import (
    CompareLayout,
    PlacedCompare,
    build_compare_layout,
    compare_onepager_docs,
    compare_subtitle,
)
from schedule_forensics.reports.pdf import render_onepager_compare_pdf, render_onepager_pdf
from schedule_forensics.reports.pdf_read import check_xref, read_pdf_payload
from schedule_forensics.reports.xlsx_read import read_xlsx
from web.onepager_twin import TWIN_ROWS, twin_xlsx

TODAY = dt.date(2026, 9, 1)
MARKING = "CUI // SP-PROPIN"
PRODUCT = "LODESTAR 2.1.0"
PAYLOAD = json.dumps(
    {
        "lodestar": {
            "format": 1,
            "program": PRODUCT,
            "page": "timeline",
            "title": "Twin One-Pager",
            "window": None,
            "today": "2026-09-01",
            "marking": "cui",
            "lists": {
                "list": {"source": "twin.xlsx", "sheet": "Sheet1", "layout": None, "rows": []}
            },
            "links": [],
            "risks": None,
        }
    },
    indent=1,
).encode("utf-8")

PRIOR_ROWS = [
    ["Swimlane Name", "Task", "Date"],
    ["Lane A", "Slips", "1/10/2027 - 3/1/2027"],
    ["Lane A", "Pulls in", "2/1/2027 - 6/30/2027"],
    ["Lane A", "Steady", "4/1/2027 - 5/1/2027"],
    ["Lane A", "Old name", "7/7/2027"],
    ["Lane B", "Gone", "10/1/2027"],
    ["Lane B", "Was a milestone", "9/9/2027"],
]
CURRENT_ROWS = [
    ["Swimlane Name", "Task", "Date"],
    ["Lane A", "Slips", "1/10/2027 - 3/31/2027"],
    ["Lane A", "Pulls in", "2/1/2027 - 6/15/2027"],
    ["Lane A", "Steady", "4/1/2027 - 5/1/2027"],
    ["Lane A", "New name", "7/7/2027"],
    ["Lane A", "Brand new", "8/8/2027"],
    ["Lane B", "Was a milestone", "9/1/2027 - 9/30/2027"],
]
COMPARE_TODAY = dt.date(2027, 6, 1)
#: A Change Summary strip wider than its box at 6 pt: the squeeze case, forced.
LONG_STRIP = (
    "slipped 1 \u00b7 pulled in 1 \u00b7 unchanged 1 \u00b7 new 2 \u00b7 "
    "worst slip: Slips (+30 cal d) and more words here"
)


# ── helpers ───────────────────────────────────────────────────────────────────────────────────


def _tool(name: str) -> str:
    exe = shutil.which(name)
    if not exe:
        pytest.skip(f"poppler's {name} is not on PATH: nothing independent to read the PDF with")
    return exe


def _run(*args: str | Path) -> str:
    done = subprocess.run([str(a) for a in args], capture_output=True, text=True, check=True)
    return done.stdout


def _content(data: bytes) -> bytes:
    """The page's content stream, inflated by the test — not by the module under test."""
    m = re.search(rb"\n4 0 obj\n<< /Filter /FlateDecode /Length (\d+) >>\nstream\n", data)
    assert m, "object 4 (the page's content) is not where the writer says it puts it"
    return zlib.decompress(data[m.end() : m.end() + int(m.group(1))])


def _markers(stream: bytes, prefix: str) -> list[str]:
    head = b"% " + prefix.encode("utf-8")
    return [
        line[len(head) :].decode("utf-8") for line in stream.split(b"\n") if line.startswith(head)
    ]


def _words(exe: str, path: Path) -> list[tuple[float, float, float, float, str]]:
    """poppler's word boxes ``(xMin, yMin, xMax, yMax, text)`` in PDF points, y DOWN from the
    page's top (``pdftotext -bbox`` writes them that way)."""
    out = _run(exe, "-bbox", path, "-")
    return [
        (float(a), float(b), float(c), float(d), html.unescape(t))
        for a, b, c, d, t in re.findall(
            r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>',
            out,
        )
    ]


def _mini_pdf(
    attachment: bytes | None,
    *,
    name: str = "lodestar-session.json",
    indirect: bool = False,
    compact: bool = False,
    flate: bool = True,
) -> bytes:
    """The refuter's std-lib one-page builder (a5-pdf/make_pdfs.py): an independent writer for
    the reader's cases. ``attachment=None`` is a browser-like file with no EmbeddedFile."""
    content = b"BT /F1 12 Tf 50 300 Td (Hello) Tj ET\n"
    cz = zlib.compress(content)
    objs: dict[int, bytes] = {
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 960 540] /Contents 4 0 R "
            b"/Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        4: b"<< /Filter /FlateDecode /Length %d >>\nstream\n" % len(cz) + cz + b"\nendstream",
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    if attachment is None:
        objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    else:
        n = name.encode("ascii")
        objs[1] = (
            b"<< /Type /Catalog /Pages 2 0 R /Names << /EmbeddedFiles << /Names [("
            + n
            + b") 7 0 R] >> >> >>"
        )
        objs[7] = b"<< /Type /Filespec /F (" + n + b") /UF (" + n + b") /EF << /F 9 0 R >> >>"
        body = zlib.compress(attachment) if flate else attachment
        length = b"10 0 R" if indirect else b"%d" % len(body)
        filt = b"/Filter/FlateDecode" if flate else b""
        if compact:
            d = (
                b"<</Params<</Size %d>>/Subtype/application#2Fjson" % len(attachment)
                + filt
                + b"/Length "
                + length
                + b"/Type/EmbeddedFile>>"
            )
        else:
            d = (
                b"<< /Type /EmbeddedFile /Subtype /application#2Fjson "
                + (b"/Filter /FlateDecode " if flate else b"")
                + b"/Length "
                + length
                + b" /Params << /Size %d >> >>" % len(attachment)
            )
        objs[9] = d + b"\nstream\r\n" + body + b"\r\nendstream"
        if indirect:
            objs[10] = b"%d" % len(body)
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: dict[int, int] = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += b"%d 0 obj\n" % num + objs[num] + b"\nendobj\n"
    xref = len(out)
    size = max(objs) + 1
    out += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for num in range(1, size):
        out += b"%010d 00000 n \n" % offsets[num] if num in offsets else b"0000000000 65535 f \n"
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, xref)
    return bytes(out)


@dataclass(frozen=True)
class _RiskPlaced(Placed):
    """A Timeline item carrying the ADR-0544 risk fields — whether or not ``Placed`` has them
    yet (the lead adds them concurrently; a redefinition with the same defaults is harmless)."""

    kind: str = "risk"
    prob: str = "high"
    impact: str = "impact +30 cal d"


@dataclass(frozen=True)
class _RiskCompare(PlacedCompare):
    kind: str = "risk"
    prob: str = "medium"
    impact: str = "impact: 6 wk"


def _as_risk(p: Placed, lay: Layout, prob: str = "high") -> _RiskPlaced:
    vals: dict[str, Any] = {f.name: getattr(p, f.name) for f in fields(Placed)}
    vals.update(
        milestone=True,
        x1=p.x0,
        ms=p.ms or lay.ms,
        label=f"RISK \u00b7 {p.name} ({p.finish})",
        kind="risk",
        prob=prob,
        impact="impact +30 cal d",
    )
    return _RiskPlaced(**vals)


def _risk_layout(lay: Layout) -> Layout:
    """The twin layout with its LAST item turned into a high-probability risk and a risk legend
    entry appended."""
    items = list(lay.items)
    items[-1] = _as_risk(items[-1], lay)
    last = lay.legend[-1]
    legend = [
        *lay.legend,
        LegendEntry("risk-high", "Risk: high", last.x + last.w + 20, last.y, 40.0, 0),
    ]
    return replace(lay, items=items, legend=legend)


# ── fixtures ──────────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def twin() -> OnePagerDoc:
    return parse_workbook(read_xlsx(twin_xlsx(TWIN_ROWS)), "twin.xlsx")


@pytest.fixture(scope="module")
def layout(twin: OnePagerDoc) -> Layout:
    return build_layout(twin.items, TODAY, "Twin One-Pager", "Prepared today")


@pytest.fixture(scope="module")
def timeline(layout: Layout) -> bytes:
    return render_onepager_pdf(
        layout,
        marking=MARKING,
        source="Source: twin.xlsx",
        product=PRODUCT,
        payload=PAYLOAD,
        made=dt.date(2026, 10, 1),
    )


def _doc(rows: list[list[str]], source: str) -> OnePagerDoc:
    items, problems, notes = parse_rows(rows)
    return OnePagerDoc(source, "Sheet1", tuple(items), tuple(problems), tuple(notes))


@pytest.fixture(scope="module")
def compare_layout() -> CompareLayout:
    pair = compare_onepager_docs(_doc(PRIOR_ROWS, "prior.xlsx"), _doc(CURRENT_ROWS, "current.xlsx"))
    return build_compare_layout(
        pair, COMPARE_TODAY, "Compare", compare_subtitle(pair, COMPARE_TODAY)
    )


@pytest.fixture(scope="module")
def compare(compare_layout: CompareLayout) -> bytes:
    return render_onepager_compare_pdf(
        compare_layout,
        marking=MARKING,
        source="Source: prior.xlsx vs current.xlsx",
        product=PRODUCT,
        payload=PAYLOAD,
    )


# ── the AFM width tables ──────────────────────────────────────────────────────────────────────


def test_helvetica_hello_measures_22_78_and_a_bold_m_is_833() -> None:
    assert pdf.text_width("Hello", 10) == pytest.approx(22.78)  # 722+556+222+222+556 = 2278
    assert pdf.text_width("M", 1000, bold=True) == 833
    assert pdf.text_width("M", 1000) == 833  # the same in both faces
    assert pdf.text_width("i", 1000) == 222 and pdf.text_width("i", 1000, bold=True) == 278


def _bbox_mismatches(
    exe: str, path: Path, size: float, bold: bool
) -> list[tuple[str, float, float]]:
    """Every word poppler placed on ``path`` whose box width disagrees with :func:`text_width`
    at ``size`` in the face ``bold`` — the test's own table-versus-poppler comparison."""
    bad = []
    for xmin, _ymin, xmax, _ymax, text in _words(exe, path):
        mine = pdf.text_width(text, size, bold)
        if abs(mine - (xmax - xmin)) > 0.02:
            bad.append((text, xmax - xmin, mine))
    return bad


def _glyph_page(tmp_path: Path, bold: bool) -> Path:
    """Every WinAnsi code with a glyph as its own single-glyph word at 20 pt in one face."""
    pg = pdf._Page()
    x = y = 20.0
    for c in range(33, 256):
        if c in (127, 129, 141, 143, 144, 157, 160, 173):  # undefined, nbsp, soft hyphen
            continue
        pg.text(
            x,
            y,
            0,
            12,
            [bytes([c]).decode("cp1252")],
            20,
            "000000",
            bold=bold,
            anchor="t",
            name="g",
        )
        y += 14
        if y > 520:
            y, x = 20.0, x + 130
    path = tmp_path / f"glyphs-{'bold' if bold else 'regular'}.pdf"
    path.write_bytes(pdf._document(pg, title="glyphs", product="t", payload=None, made=None))
    return path


@pytest.mark.parametrize("bold", [False, True])
def test_every_winansi_width_matches_popplers_own_base14_metrics(
    tmp_path: Path, bold: bool
) -> None:
    """poppler draws a base-14 font with NO /Widths from its built-in AFM tables, so
    ``pdftotext -bbox``'s word width is Adobe's advance — an oracle for the typed tables that
    the module never touched. 215 glyphs per face, every one within 0.02 pt."""
    exe = _tool("pdftotext")
    path = _glyph_page(tmp_path, bold)
    words = _words(exe, path)
    assert len(words) == 215, "poppler did not see one word per glyph"
    assert _bbox_mismatches(exe, path, 20, bold) == []


def test_mutation_a_wrong_width_is_caught_by_the_poppler_comparison(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = _tool("pdftotext")
    table = list(pdf._HELVETICA_BOLD)
    table[ord("M") - 32] = 600  # the real advance is 833
    monkeypatch.setattr(pdf, "_HELVETICA_BOLD", tuple(table))
    path = _glyph_page(tmp_path, bold=True)
    bad = _bbox_mismatches(exe, path, 20, True)
    assert [b[0] for b in bad] == ["M"] and bad[0][1] == pytest.approx(16.66, abs=0.02)


def test_the_three_symbol_glyphs_and_the_winansi_marks_round_trip_through_pdftotext(
    tmp_path: Path,
) -> None:
    """The refuter's verdict: Symbol 0xAE / 0xAC / 0x2D read back as the arrows and the minus,
    WinAnsi 0x96 / 0x97 / 0x85 / 0xB7 as the dashes, the ellipsis and the middle dot."""
    exe = _tool("pdftotext")
    pg = pdf._Page()
    pg.text(20, 40, 0, 12, ["A \u2192 B \u2190 C \u2212 D"], 12, "000000", anchor="t", name="s")
    marks = "en\u2013dash em\u2014dash dots\u2026 mid\u00b7dot \u00b15"
    pg.text(20, 60, 0, 12, [marks], 12, "000000", anchor="t", name="w")
    pg.text(20, 80, 0, 12, ["kanji \u65e5\u672c stays ?"], 12, "000000", anchor="t", name="q")
    path = tmp_path / "glyphs.pdf"
    path.write_bytes(pdf._document(pg, title="g", product="t", payload=None, made=None))
    text = _run(exe, path, "-")
    # poppler's plain text merges a word across the font switch (measured: "A\u2192B...");
    # the GLYPHS and their order are the claim, and the bbox below proves the spaces are real
    assert re.search("A\\s*\u2192\\s*B\\s*\u2190\\s*C\\s*\u2212\\s*D", text)
    assert "en\u2013dash em\u2014dash dots\u2026 mid\u00b7dot \u00b15" in text
    assert "kanji ?? stays ?" in text
    words = [w for w in _words(exe, path) if w[1] < 60]
    assert [w[4] for w in words] == ["A", "\u2192", "B", "\u2190", "C", "\u2212", "D"]
    for prev, nxt in pairwise(words):
        assert nxt[0] == pytest.approx(prev[2] + 3.336, abs=0.01)  # one 12-pt Helvetica space
    assert words[1][2] - words[1][0] == pytest.approx(11.844, abs=0.01)  # arrowright 987/1000
    assert words[5][2] - words[5][0] == pytest.approx(6.588, abs=0.01)  # minus 549/1000
    stream = _content(path.read_bytes())
    assert b"/F3 12 Tf (\\256) Tj" in stream and b"/F3 12 Tf (\\254) Tj" in stream
    assert b"/F3 12 Tf (-) Tj" in stream  # Symbol's minus is code 0x2D
    assert b"(en\\226dash em\\227dash dots\\205 mid\\267dot \\2615) Tj" in stream


def test_mutation_dropping_the_symbol_map_loses_the_arrow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = _tool("pdftotext")
    monkeypatch.setattr(pdf, "_SYMBOL_CODES", {})
    pg = pdf._Page()
    pg.text(20, 40, 0, 12, ["A \u2192 B"], 12, "000000", anchor="t", name="s")
    path = tmp_path / "noarrow.pdf"
    path.write_bytes(pdf._document(pg, title="g", product="t", payload=None, made=None))
    assert re.search(r"A\s*\?\s*B", _run(exe, path, "-"))


def test_encode_runs_never_crashes_and_splits_the_symbol_pieces() -> None:
    assert pdf.encode_runs("a\u2192b", bold=False) == [("F1", b"a"), ("F3", b"\xae"), ("F1", b"b")]
    assert pdf.encode_runs("x", bold=True) == [("F2", b"x")]
    assert pdf.encode_runs("\u65e5\n\U0001f600", bold=False) == [("F1", b"? ?")]
    assert pdf.encode_runs("", bold=False) == []


# ── the poppler oracles on the exports ────────────────────────────────────────────────────────


def test_pdfinfo_reads_one_page_of_960_by_540_with_the_products_name(
    tmp_path: Path, timeline: bytes
) -> None:
    exe = _tool("pdfinfo")
    path = tmp_path / "t.pdf"
    path.write_bytes(timeline)
    info = _run(exe, path)
    assert "Pages:           1\n" in info
    assert "Page size:       960 x 540 pts\n" in info
    assert f"Producer:        {PRODUCT}\n" in info and f"Creator:         {PRODUCT}\n" in info
    assert "Title:           Twin One-Pager\n" in info
    assert "CreationDate:    Thu Oct  1 00:00:00 2026" in info
    assert "Encrypted:       no\n" in info


def test_pdftotext_finds_the_title_the_labels_and_the_marking_top_and_bottom(
    tmp_path: Path, timeline: bytes, layout: Layout
) -> None:
    exe = _tool("pdftotext")
    path = tmp_path / "t.pdf"
    path.write_bytes(timeline)
    text = _run(exe, "-layout", path, "-")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    assert lines[0] == MARKING and lines[-1] == MARKING  # Law 1: the marking top and bottom
    assert "Twin One-Pager" in text and "Prepared today" in text
    for p in layout.items:
        assert p.label in text, f"label not read back: {p.label!r}"
    assert "Source: twin.xlsx" in text and "red line = data date" in text


def test_pdftotext_reads_the_compare_deltas_with_a_real_minus(
    tmp_path: Path, compare: bytes, compare_layout: CompareLayout
) -> None:
    exe = _tool("pdftotext")
    path = tmp_path / "c.pdf"
    path.write_bytes(compare)
    text = _run(exe, "-layout", path, "-")
    assert "+30 cal d" in text and "\u221215 cal d" in text and "CHANGE SUMMARY" in text
    assert "NEW" in text and "REMOVED" in text
    for box in compare_layout.summaries:
        for line in box.lines:
            assert line in text, f"summary line not read back: {line!r}"


def test_pdfdetach_lists_the_attachment_and_saves_the_same_bytes(
    tmp_path: Path, timeline: bytes, compare: bytes
) -> None:
    exe = _tool("pdfdetach")
    for i, data in enumerate((timeline, compare)):
        path = tmp_path / f"p{i}.pdf"
        path.write_bytes(data)
        listing = _run(exe, "-list", path)
        assert "1 embedded files\n1: lodestar-session.json\n" in listing
        out = tmp_path / f"det{i}"
        out.mkdir()
        _run(exe, "-saveall", "-o", out, path)
        assert (out / "lodestar-session.json").read_bytes() == PAYLOAD


def test_without_a_payload_there_is_no_attachment(tmp_path: Path, layout: Layout) -> None:
    exe = _tool("pdfdetach")
    data = render_onepager_pdf(layout, marking=MARKING, source="s", product=PRODUCT)
    path = tmp_path / "bare.pdf"
    path.write_bytes(data)
    assert _run(exe, "-list", path).startswith("0 embedded files")
    assert b"/EmbeddedFile" not in data and read_pdf_payload(data) is None


def _png_size(data: bytes) -> tuple[int, int]:
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def test_pdftoppm_renders_both_exports_at_the_slides_pixel_size(
    tmp_path: Path, timeline: bytes, compare: bytes
) -> None:
    exe = _tool("pdftoppm")
    for name, data in (("t", timeline), ("c", compare)):
        path = tmp_path / f"{name}.pdf"
        path.write_bytes(data)
        _run(exe, "-r", "72", "-png", path, tmp_path / name)
        assert _png_size((tmp_path / f"{name}-1.png").read_bytes()) == (960, 540)


def _ppm_pixel(data: bytes, x: int, y: int) -> tuple[int, int, int]:
    """One pixel of a binary PPM (P6) — pdftoppm's default output, parsed by the test."""
    m = re.match(rb"P6\s+(\d+)\s+(\d+)\s+255\s", data)
    assert m, "not a P6 PPM"
    w = int(m.group(1))
    at = m.end() + 3 * (y * w + x)
    return data[at], data[at + 1], data[at + 2]


def test_a_risk_renders_as_a_triangle_in_its_probability_colour(
    tmp_path: Path, layout: Layout
) -> None:
    """The user's rule: a risk is a single moment, an UP triangle, red / amber / green by
    probability, never a diamond. Checked in the stream (three vertices, apex at
    ``y - ms/2``, base at ``y + ms/2``) and on the bitmap (the pixel inside the glyph is the
    print palette's high red)."""
    exe = _tool("pdftoppm")
    lay = _risk_layout(layout)
    risk = lay.items[-1]
    data = render_onepager_pdf(lay, marking=MARKING, source="s", product=PRODUCT)
    stream = _content(data)
    assert _markers(stream, "Risk: ") == [risk.name]
    assert _markers(stream, "Milestone: ") == [p.name for p in lay.items[:-1] if p.milestone]
    at = stream.index(b"% Risk: " + risk.name.encode("utf-8"))
    op = stream[at : stream.index(b"\n", stream.index(b"\n", at) + 1)].split(b"\n")[1].decode()
    ms = risk.ms
    apex = (
        f"{risk.x0:.3f}".rstrip("0").rstrip(".")
        + " "
        + f"{540 - (risk.y - ms / 2):.3f}".rstrip("0").rstrip(".")
    )
    assert "0.702 0.149 0.118 rg" in op and f" {apex} m " in op and op.endswith(" l h B Q")
    assert op.count(" l ") == 2  # a triangle: a move and two lines, closed
    leg = stream.index(b"% Legend: risk-high\n")
    leg_op = stream[leg : stream.index(b"\n% ", leg)].split(b"\n")[1]
    assert leg_op.count(b" l ") == 2 and leg_op.endswith(b" l h B Q")  # a triangle, not a diamond
    assert b"0.702 0.149 0.118 rg" in leg_op
    assert b"( impact +30 cal d) Tj" in stream and b"(RISK \\267 " in stream
    path = tmp_path / "risk.pdf"
    path.write_bytes(data)
    _run(exe, "-r", "72", path, tmp_path / "risk")
    ppm = (tmp_path / "risk-1.ppm").read_bytes()
    r, g, b = _ppm_pixel(ppm, round(risk.x0), round(risk.y + ms * 0.15))
    assert max(abs(r - 0xB3), abs(g - 0x26), abs(b - 0x1E)) < 12, (r, g, b)


def test_mutation_a_risk_painted_as_a_milestone_is_caught(
    layout: Layout, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pdf, "_is_risk", lambda p: False)
    lay = _risk_layout(layout)
    stream = _content(render_onepager_pdf(lay, marking=MARKING, source="s", product=PRODUCT))
    assert _markers(stream, "Risk: ") == []
    assert lay.items[-1].name in _markers(stream, "Milestone: ")


def test_a_compare_risk_is_a_triangle_with_its_impact_in_the_probability_colour(
    compare_layout: CompareLayout,
) -> None:
    lay = compare_layout
    src = next(p for p in lay.items if p.x0 is not None)
    vals: dict[str, Any] = {f.name: getattr(src, f.name) for f in fields(PlacedCompare)}
    vals.update(
        name="Vendor slip",
        status="risk",
        milestone=True,
        x1=src.x0,
        ms=lay.ms,
        ghost_x0=None,
        ghost_x1=None,
        arrow_x0=None,
        arrow_x1=None,
        badge="",
        delta="impact: 6 wk",
        label="RISK \u00b7 Vendor slip (7/1/27)",
        kind="risk",
        prob="medium",
        impact="impact: 6 wk",
    )
    risk = _RiskCompare(**vals)
    mutated = replace(lay, items=[*lay.items, risk])
    stream = _content(
        render_onepager_compare_pdf(mutated, marking=MARKING, source="s", product=PRODUCT)
    )
    assert _markers(stream, "Risk: ") == [risk.name]
    at = stream.index(b"% Risk: ")
    assert b"0.722 0.525 0.043 rg" in stream[at : at + 400]  # medium: B8860B
    label_at = stream.index(b"% Label: " + risk.name.encode("utf-8"))
    assert b"0.722 0.525 0.043 rg /F2" in stream[label_at : label_at + 600]
    assert b"( impact: 6 wk) Tj" in stream[label_at : label_at + 600]


# ── every item the layout holds is painted ────────────────────────────────────────────────────


def _painted_timeline(stream: bytes) -> dict[str, list[str]]:
    return {
        "shapes": _markers(stream, "Activity: ") + _markers(stream, "Milestone: "),
        "labels": _markers(stream, "Label: "),
        "lanes": _markers(stream, "Lane name: "),
        "legend": _markers(stream, "Legend text: "),
    }


def test_the_timeline_pdf_paints_every_item_lane_and_legend_entry(
    timeline: bytes, layout: Layout
) -> None:
    got = _painted_timeline(_content(timeline))
    assert sorted(got["shapes"]) == sorted(p.name for p in layout.items)
    assert sorted(got["labels"]) == sorted(p.name for p in layout.items)
    assert got["lanes"] == [ln.name for ln in layout.lanes]
    assert got["legend"] == [e.label for e in layout.legend]
    stream = _content(timeline)
    for p in layout.items:
        lit = p.label.encode("cp1252").replace(b"(", b"\\(").replace(b")", b"\\)")
        assert b"(" + lit + b") Tj" in stream, p.label
    assert stream.count(b"% Data date\n") == 1 and stream.count(b"% Data date label\n") == 1
    assert stream.count(b"% Month line ") == len(layout.months)


def test_mutation_a_dropped_item_is_named_by_the_count(timeline: bytes, layout: Layout) -> None:
    short = replace(layout, items=layout.items[:-1])
    data = render_onepager_pdf(short, marking=MARKING, source="s", product=PRODUCT, payload=PAYLOAD)
    got = _painted_timeline(_content(data))
    missing = {p.name for p in layout.items} - set(got["shapes"])
    assert missing == {layout.items[-1].name}


def test_the_compare_pdf_paints_every_ghost_arrow_shape_label_tag_and_summary(
    compare: bytes, compare_layout: CompareLayout
) -> None:
    lay = compare_layout
    stream = _content(compare)
    ghosts = [p.name for p in lay.items if p.ghost_x0 is not None]
    assert sorted(
        _markers(stream, "Prior activity: ") + _markers(stream, "Prior milestone: ")
    ) == sorted(ghosts)
    arrows = [p.name for p in lay.items if p.arrow_x0 is not None]
    assert sorted(_markers(stream, "Slip: ") + _markers(stream, "Pull-in: ")) == sorted(arrows)
    current = [p.name for p in lay.items if p.x0 is not None]
    assert sorted(_markers(stream, "Activity: ") + _markers(stream, "Milestone: ")) == sorted(
        current
    )
    assert sorted(_markers(stream, "Label: ")) == sorted(p.name for p in lay.items)
    tags = [f"{p.badge} \u2014 {p.name}" for p in lay.items if p.badge]
    assert sorted(_markers(stream, "Tag: ")) == sorted(tags)
    assert _markers(stream, "Summary: ") == [lay.lanes[b.lane].name for b in lay.summaries]
    assert ghosts and arrows and tags  # the fixture exercises every branch
    assert b"% Logic link" not in stream  # no links in this pair


# ── no text outside its box (the operator's Change Summary defect) ────────────────────────────


def _overflowing_words(exe: str, path: Path, lay: CompareLayout) -> list[tuple[str, float]]:
    """Every word poppler placed in the summary column that runs past a summary box's right
    edge, by how much — the PDF twin of the page's "text falls outside the coloured boxes"."""
    out = []
    for xmin, ymin, xmax, _ymax, text in _words(exe, path):
        if xmin < lay.summary_x0 or ymin < lay.lanes_y0 or ymin > lay.lanes_y1:
            continue
        box = next((b for b in lay.summaries if b.y0 <= ymin <= b.y1), None)
        if box is not None and xmax > box.x1 - 1.5 + 0.05:
            out.append((text, xmax - (box.x1 - 1.5)))
    return out


def test_summary_text_is_squeezed_to_its_box_never_past_it(
    tmp_path: Path, compare_layout: CompareLayout
) -> None:
    """A strip wider than its box is squeezed (``Tz``) to the box: poppler's word boxes all end
    inside it. The long line is forced in — the lead's wrap fix (ADR-0544) keeps a real strip
    narrower than Helvetica, so the squeeze would otherwise never be exercised here."""
    exe = _tool("pdftotext")
    box = compare_layout.summaries[0]
    long = LONG_STRIP
    wide = replace(box, lines=[long, *box.lines[1:]], pt=6.0)
    lay = replace(compare_layout, summaries=[wide, *compare_layout.summaries[1:]])
    assert pdf.text_width(long, 6.0) > box.x1 - box.x0 - 4  # the case is real
    data = render_onepager_compare_pdf(lay, marking=MARKING, source="s", product=PRODUCT)
    path = tmp_path / "squeeze.pdf"
    path.write_bytes(data)
    assert _overflowing_words(exe, path, lay) == []
    stream = _content(data)
    at = stream.index(b"% Summary text: Lane A")
    block = stream[at : stream.index(b"\n% ", at + 2)]
    assert re.search(rb"BT \d\d\.\d+ Tz ", block) and b"% squeezed" in block
    assert b"BT 100 Tz " in block  # the box's other, shorter lines are not squeezed


def test_mutation_without_the_squeeze_the_summary_runs_past_its_box(
    tmp_path: Path, compare_layout: CompareLayout, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = _tool("pdftotext")
    original: Callable[..., tuple[str, bool]] = pdf._Page._line_ops

    def never_squeeze(
        self: pdf._Page, x: float, baseline: float, runs: Any, size: float, w: float, align: str
    ) -> tuple[str, bool]:
        return original(self, x, baseline, runs, size, 0.0, align)

    monkeypatch.setattr(pdf._Page, "_line_ops", never_squeeze)
    box = compare_layout.summaries[0]
    long = LONG_STRIP
    lay = replace(
        compare_layout,
        summaries=[replace(box, lines=[long], pt=6.0), *compare_layout.summaries[1:]],
    )
    path = tmp_path / "nosqueeze.pdf"
    path.write_bytes(render_onepager_compare_pdf(lay, marking=MARKING, source="s", product=PRODUCT))
    over = _overflowing_words(exe, path, lay)
    # poppler drops the words past the page's edge, so the LAST word it still sees is "wor(st)"
    assert over and max(by for _w, by in over) > 15, over


def test_every_word_of_both_exports_lies_on_the_page(
    tmp_path: Path, timeline: bytes, compare: bytes
) -> None:
    exe = _tool("pdftotext")
    for name, data in (("t", timeline), ("c", compare)):
        path = tmp_path / f"{name}.pdf"
        path.write_bytes(data)
        for xmin, ymin, xmax, ymax, text in _words(exe, path):
            assert 0 <= xmin < xmax <= 960 and 0 <= ymin < ymax <= 540, (name, text)


# ── the reader ────────────────────────────────────────────────────────────────────────────────


def test_the_reader_round_trips_both_exports(timeline: bytes, compare: bytes) -> None:
    assert read_pdf_payload(timeline) == PAYLOAD
    assert read_pdf_payload(compare) == PAYLOAD


@pytest.mark.parametrize(
    ("indirect", "compact", "flate"),
    [
        (False, False, True),
        (True, False, True),
        (False, True, True),
        (True, True, True),
        (False, False, False),
    ],
)
def test_the_reader_takes_direct_and_indirect_lengths_compact_syntax_and_raw_streams(
    indirect: bool, compact: bool, flate: bool
) -> None:
    data = _mini_pdf(PAYLOAD, indirect=indirect, compact=compact, flate=flate)
    assert read_pdf_payload(data) == PAYLOAD


def test_the_reader_agrees_with_pdfdetach_on_the_hand_built_variants(tmp_path: Path) -> None:
    exe = _tool("pdfdetach")
    for i, (indirect, compact) in enumerate([(True, True), (False, False)]):
        path = tmp_path / f"v{i}.pdf"
        path.write_bytes(_mini_pdf(PAYLOAD, indirect=indirect, compact=compact))
        out = tmp_path / f"d{i}"
        out.mkdir()
        _run(exe, "-saveall", "-o", out, path)
        assert (
            (out / "lodestar-session.json").read_bytes()
            == PAYLOAD
            == read_pdf_payload(path.read_bytes())
        )


def test_the_reader_returns_none_on_a_browser_like_pdf_and_on_other_attachments() -> None:
    assert read_pdf_payload(_mini_pdf(None)) is None  # no attachment at all
    assert read_pdf_payload(_mini_pdf(b'{"other": 1}')) is None  # JSON without the key
    assert read_pdf_payload(_mini_pdf(b"[1, 2]")) is None  # JSON, not an object
    assert read_pdf_payload(_mini_pdf(b"PK\x03\x04 not json", name="schedule.xlsx")) is None
    assert read_pdf_payload(_mini_pdf(b"\xff\xfe not utf-8")) is None
    assert read_pdf_payload(b"") is None and read_pdf_payload(b"<html>not a pdf</html>") is None


def test_the_reader_takes_the_first_lodestar_attachment_among_several() -> None:
    other = _mini_pdf(b'{"other": 1}')
    # a second EmbeddedFile object appended after the first, as an incremental update would
    second = (
        b"\n11 0 obj\n<< /Type /EmbeddedFile /Length %d >>\nstream\n" % len(PAYLOAD)
        + PAYLOAD
        + b"\nendstream\nendobj\n"
    )
    assert read_pdf_payload(other + second) == PAYLOAD


def test_mutation_a_payload_without_the_key_is_not_a_payload() -> None:
    bad = PAYLOAD.replace(b'"lodestar"', b'"tasks_of_mine"')
    assert read_pdf_payload(_mini_pdf(bad)) is None
    assert read_pdf_payload(_mini_pdf(PAYLOAD)) == PAYLOAD  # the same builder, the key present


def test_the_reader_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    data = _mini_pdf(PAYLOAD)
    monkeypatch.setattr(pdf_read, "MAX_PDF_BYTES", len(data) - 1)
    assert read_pdf_payload(data) is None
    monkeypatch.setattr(pdf_read, "MAX_PDF_BYTES", len(data))
    assert read_pdf_payload(data) == PAYLOAD
    monkeypatch.setattr(pdf_read, "MAX_PAYLOAD_BYTES", len(PAYLOAD) - 1)
    assert read_pdf_payload(data) is None  # the inflate stops at the cap
    assert read_pdf_payload(_mini_pdf(PAYLOAD, flate=False)) is None  # and so does a raw one
    monkeypatch.setattr(pdf_read, "MAX_PAYLOAD_BYTES", len(PAYLOAD))
    assert read_pdf_payload(data) == PAYLOAD


def test_a_lying_length_falls_back_to_the_endstream_scan() -> None:
    data = _mini_pdf(PAYLOAD)
    at = data.index(b"/Type /EmbeddedFile")
    m = re.compile(rb"/Length (\d+)").search(data, at)
    assert m
    lied = data[: m.start(1)] + b"7" + data[m.end(1) :]  # a wrong direct length
    assert read_pdf_payload(lied) == PAYLOAD
    unresolved = _mini_pdf(PAYLOAD, indirect=True).replace(b"10 0 obj", b"99 0 obj")
    assert read_pdf_payload(unresolved) == PAYLOAD  # an indirect length nothing resolves


# ── the writer's cross-reference self-check ───────────────────────────────────────────────────


def test_both_exports_pass_the_xref_check_and_the_hand_built_file_too(
    timeline: bytes, compare: bytes
) -> None:
    assert check_xref(timeline) == "" and check_xref(compare) == ""
    assert check_xref(_mini_pdf(PAYLOAD, indirect=True)) == ""


def test_mutation_a_shifted_xref_offset_is_caught_by_name(timeline: bytes) -> None:
    shifted = re.sub(
        rb"(\d{10}) 00000 n ", lambda m: b"%010d 00000 n " % (int(m.group(1)) + 7), timeline
    )
    assert shifted != timeline
    assert check_xref(shifted) == "xref entry for object 1 points at 22, not at its header"
    broken = timeline.replace(b"startxref\n", b"startxref\n1")
    assert check_xref(broken).startswith(
        "startxref 1"
    ) and "does not point at 'xref'" in check_xref(broken)
    assert check_xref(timeline[: timeline.rindex(b"startxref")]) == "no startxref"


def test_mutation_the_writer_refuses_its_own_broken_table(
    layout: Layout, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pdf, "check_xref", lambda data: "deliberately broken")
    with pytest.raises(RuntimeError, match="deliberately broken"):
        render_onepager_pdf(layout, marking=MARKING, source="s", product=PRODUCT)


# ── determinism and the document's own shape ──────────────────────────────────────────────────


def test_the_bytes_are_deterministic_and_never_read_the_clock(
    layout: Layout, compare_layout: CompareLayout, timeline: bytes, compare: bytes
) -> None:
    again = render_onepager_pdf(
        layout,
        marking=MARKING,
        source="Source: twin.xlsx",
        product=PRODUCT,
        payload=PAYLOAD,
        made=dt.date(2026, 10, 1),
    )
    assert again == timeline
    assert (
        render_onepager_compare_pdf(
            compare_layout,
            marking=MARKING,
            source="Source: prior.xlsx vs current.xlsx",
            product=PRODUCT,
            payload=PAYLOAD,
        )
        == compare
    )
    assert b"/CreationDate (D:20261001000000Z)" in timeline and b"/CreationDate" not in compare


def test_the_document_carries_the_embedded_file_the_way_the_contract_says(timeline: bytes) -> None:
    assert (
        b"/Type /Catalog /Pages 2 0 R /Names << /EmbeddedFiles "
        b"<< /Names [(lodestar-session.json) 9 0 R] >> >>" in timeline
    )
    assert (
        b"/Type /Filespec /F (lodestar-session.json) /UF (lodestar-session.json) /Desc ("
        in timeline
    )
    assert b"/EF << /F 10 0 R >>" in timeline
    assert re.search(
        rb"/Type /EmbeddedFile /Subtype /application#2Fjson /Params << /Size %d >> "
        rb"/Filter /FlateDecode /Length \d+ >>" % len(PAYLOAD),
        timeline,
    )
    assert b"/MediaBox [0 0 960 540]" in timeline
    assert b"/BaseFont /Helvetica /Encoding /WinAnsiEncoding" in timeline
    assert b"/BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding" in timeline
    assert b"/BaseFont /Symbol >>" in timeline
    assert timeline.startswith(b"%PDF-1.4\n") and timeline.endswith(b"%%EOF\n")
    assert b'"tasks"' not in timeline  # never the CUI guard's Save-.json signature


def test_a_non_ascii_product_is_written_as_utf16_and_read_back(
    tmp_path: Path, layout: Layout
) -> None:
    exe = _tool("pdfinfo")
    data = render_onepager_pdf(layout, marking=MARKING, source="s", product="POLARIS\u00b2")
    assert b"/Producer <FEFF0050004F004C0041005200490053" in data
    path = tmp_path / "p.pdf"
    path.write_bytes(data)
    assert "Producer:        POLARIS\u00b2\n" in _run(exe, path)


def test_the_painters_mirror_the_deck_writers_paint_order(timeline: bytes, compare: bytes) -> None:
    """The deck's z-order (ADR-0543): lanes, then link shafts, then items, then link heads, then
    the data date, then the legend, then the footer — read off the markers' first positions."""
    for data in (timeline, compare):
        stream = _content(data)
        top, bottom = stream.index(b"% CUI marking (top)"), stream.index(b"% CUI marking (bottom)")
        assert top < bottom < stream.index(b"% Title")  # the two strips first, as the deck
        order = [
            top,
            stream.index(b"% Title"),
            stream.index(b"% Year band "),
            stream.index(b"% Month line "),
            stream.index(b"% Header line"),
            stream.index(b"% Lane: "),
            stream.index(b"% Label: "),
            stream.index(b"% Data date\n"),
            stream.index(b"% Legend line"),
            stream.index(b"% Legend text: "),
            stream.index(b"% Source"),
            stream.index(b"% Read-me"),
        ]
        assert order == sorted(order)
