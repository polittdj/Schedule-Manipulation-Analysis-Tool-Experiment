"""The /brief page family: the Diagnostic Brief document body and its export title.

Monolith split, phase 4 slice 22 (ADR-0387), extracted VERBATIM from ``web/app.py``: every
function and constant moves byte-for-byte -- docstrings, comments and HTML f-strings
unchanged -- and only the module boundary is new.

The seam is the AST transitive closure of the family's entry points, seeded on the
EXACT route list ``/brief`` + ``/export/{fmt}/brief`` -- never a substring, because
``brief`` is a PREFIX of ``briefing`` and seeding by substring fuses the two families
into one eight-name census (ADR-0386).  ONE function, plus the module-level export
title only it reads.

**The export route contributes NO movers, and two instruments say so.** ``export_brief``
shares only the ``DiagnosticBrief`` model with the page: it renders through
``ai.brief.brief_blocks`` for docx and builds its sheets straight off ``brief.sections`` for
xlsx, so its app-level callee set never reaches ``_brief_body``. The render probe agrees
independently -- marking ``_brief_body`` moved the four ``GET /brief`` labels and neither
``/export/{fmt}/brief`` label.

Layering: ``app`` -> ``brief`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

from schedule_forensics.ai.brief import DiagnosticBrief
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.components import _panel_head, _shell_tools

#: ⤓ EXCEL hover text for the /brief document page (ADR-0337). It names a REAL endpoint the page
#: already offers in its export bar — ``/export/xlsx/brief`` — so the glyph never points at a
#: route that does not exist. This note is one half of a ``#:`` block that documented BOTH
#: chapter-12 export titles in ``app.py``; the constant's own bytes moved verbatim, and the
#: sentence was split because "Both name a REAL endpoint" stopped being true of either file
#: alone once ``_BRIEF_XLSX_TITLE`` left. Its twin ``_BRIEFING_XLSX_TITLE`` now lives in
#: ``web/briefing.py`` (ADR-0388), so the pair is split across two modules and each half of
#: this note travels with the constant it describes.
_BRIEF_XLSX_TITLE = (
    "Export the diagnostic brief workbook (this document's sections are its sheets) — "
    "opens in Excel"
)


def _brief_body(brief: DiagnosticBrief, *, prov: str = "") -> str:
    """The Diagnostic Brief page: cited prose + the finish table, print-friendly.

    Panel contract (ADR-0337, chapter 12): every panel wears the head strip + ⤓ EXCEL + ⛶ and the
    SERIES provenance chip, and the lead panel carries the one ``.sf-take``. The chip is the series
    form because a ``DiagnosticBrief`` is built from every solvable version at once
    (:func:`_solvable_versions`), so naming a single file would misdescribe what the prose is drawn
    from — the same reasoning :func:`_series_prov_chip` was introduced for.

    ⤓ EXCEL points at ``/export/xlsx/brief``, the endpoint the page's own export bar already
    offers, so the glyph can never be a dead link (rank-3 law). ▦ DATA is deliberately absent:
    these panels ARE prose and tables, so there is no hidden drawer for it to reveal.
    """
    tools = _shell_tools(export_title=_BRIEF_XLSX_TITLE)
    export = ' data-export="/export/xlsx/brief"'
    # The take counts what the page renders directly below it — sections, and the cited statements
    # inside them — so the first number the reader meets is one they can verify by looking down.
    cited = sum(len(s.paragraphs) for s in brief.sections)
    parts = [
        f"<div class=panel{export}>",
        _panel_head(_e(brief.title), tools=tools, prov=prov),
        f"<p class=sf-take data-no-i18n>{len(brief.sections)} sections, {cited} cited "
        f"statement{'s' if cited != 1 else ''} — every one carrying its schedule, UID and "
        "activity.</p>",
        f"<p class=muted>Report generated on {brief.generated_on.strftime('%A, %B %d, %Y')}. "
        "Every claim carries its citation [schedule, UID, activity] — see the final "
        "section for how to verify.</p></div>",
    ]
    for section in brief.sections:
        parts.append(f"<div class=panel{export}>")
        parts.append(_panel_head(_e(section.heading), tools=tools, prov=prov))
        for stmt in section.paragraphs:
            parts.append(f"<p>{_e(stmt.rendered())}</p>")
        if section.table is not None:
            head = "".join(f"<th scope=col>{_e(str(h))}</th>" for h in section.table.headers)
            rows = "".join(
                "<tr>"
                + "".join(f"<td>{_e('' if c is None else str(c))}</td>" for c in row)
                + "</tr>"
                for row in section.table.rows
            )
            parts.append(f"<table><tr>{head}</tr>{rows}</table>")
        parts.append("</div>")
    return "".join(parts)
