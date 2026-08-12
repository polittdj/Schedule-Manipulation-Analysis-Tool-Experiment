"""The /briefing page family: the Executive Briefing document, its header and its export title.

Monolith split, phase 4 slice 23 (ADR-0388), extracted VERBATIM from ``web/app.py``: every
function and constant moves byte-for-byte -- docstrings, comments and HTML f-strings
unchanged -- and only the module boundary is new.

The seam is the AST transitive closure of the family's entry points, seeded on the EXACT route
list ``/briefing`` + ``/api/ai/briefing`` + ``/export/{fmt}/briefing`` -- never a substring.
``brief`` is a PREFIX of ``briefing``, so a substring seed fuses the two families into one
census in both directions (ADR-0386); the walk is the definition and the prefix only a finder.

**This family carries ZERO descents, and the record said three.** ADR-0383's table -- carried
forward by ADR-0386 and ADR-0387 -- priced ``briefing`` at three AI-backend descents
(``_ollama_or_none``, ``_openai_or_none``, ``_active_backend``). Re-walked here, none of them
is reachable from a briefing MOVER: the first two are needed by ``_ai_status_note`` and
``_settings_body``, which belong to the ``settings`` family, and ``_active_backend`` is reached
only from the ``/api/ai/briefing`` ROUTE. A route-only referrer never forces a descent, because
routes live in ``create_app`` and import downward (ADR-0378, ADR-0387). All three stay in
``app.py`` and are ``settings``' problem to solve.

Layering: ``app`` -> ``briefing`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

from schedule_forensics.ai.briefing import BriefingSection, ExecutiveBriefing
from schedule_forensics.engine import audit_schedule, recommend
from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.dcma_audit import Citation
from schedule_forensics.engine.metrics._common import CheckStatus
from schedule_forensics.engine.recommendations import Severity
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.components import (
    _panel_head,
    _shell_tools,
    _stat_cards,
    _status_stack,
)

#: ⤓ EXCEL hover text for the /briefing document page (ADR-0337). It names a REAL endpoint the
#: page already offers in its export bar — ``/export/xlsx/briefing`` — so the glyph never points
#: at a route that does not exist. Its twin ``_BRIEF_XLSX_TITLE`` left with the /brief family in
#: ADR-0387 and carries the other half of this note; this half followed it out in ADR-0388, so
#: the two halves now sit beside the two constants they each describe.
_BRIEFING_XLSX_TITLE = (
    "Export the executive briefing workbook (this document's sections are its sheets) — "
    "opens in Excel"
)


def _cite_tag(citations: tuple[Citation, ...]) -> str:
    shown = "; ".join(str(c) for c in citations[:3])
    extra = f"; +{len(citations) - 3} more" if len(citations) > 3 else ""
    return f"{shown}{extra}"


def _briefing_table_html(section: BriefingSection) -> str:
    """A section's cited table: engine figures verbatim, a citation column per row."""
    table = section.table
    if table is None or not table.rows:
        return ""
    head = ""
    if table.headers:
        head = (
            "<tr>"
            + "".join(f"<th scope=col>{_e(h)}</th>" for h in table.headers)
            + "<th scope=col>Citation</th></tr>"
        )
    body = "".join(
        "<tr>"
        + "".join(f"<td>{_e(cell)}</td>" for cell in row)
        + f"<td class=cite>{_e(_cite_tag(cites))}</td></tr>"
        for row, cites in zip(table.rows, table.row_citations, strict=True)
    )
    # .brief-scroll: a table whose column minimums exceed the card scrolls sideways inside it
    # instead of crushing its neighbours to a character a line (operator report 2026-07-08)
    return f"<div class=brief-scroll><table class=brief-table>{head}{body}</table></div>"


def _the_briefing_header(
    briefing: ExecutiveBriefing,
    sch: Schedule,
    cpm: CPMResult,
    *,
    acumen_parity: bool = False,
) -> str:
    """Chapter 12 "The briefing" (ADR-0210): the data-driven takeaway (the briefing's own
    verdict + headline figures), a KPI strip from the briefing banner, and the action-items
    and quality-snapshot bars — the executive synthesis. Every figure is one the briefing /
    audit already computes (no new math)."""
    banner = dict(briefing.banner)
    spi = banner.get("SPI (duration-based)") or banner.get("SPI")
    forecast = banner.get("Schedule-logic finish (CPM)")
    slip = banner.get("Slip")
    clauses = []
    if spi:
        clauses.append(f"SPI {spi}")
    if forecast:
        clauses.append(f"schedule logic landing on {forecast}")
    if slip:
        clauses.append(f"a {slip} slip from baseline")
    tail = f" — {', '.join(clauses)}" if clauses else ""
    takeaway = f"Bottom line: the schedule is {briefing.verdict}{tail}."

    # KPI strip = the briefing's own banner headline figures (up to six)
    kpi = _stat_cards([(label, value) for label, value in briefing.banner[:6]])

    findings = recommend(sch, current_cpm=cpm, acumen_parity=acumen_parity)
    high = sum(1 for f in findings if f.severity == Severity.HIGH)
    med = sum(1 for f in findings if f.severity == Severity.MEDIUM)
    low = sum(1 for f in findings if f.severity == Severity.LOW)
    audit = audit_schedule(sch, cpm, acumen_parity=acumen_parity)
    passed = sum(1 for c in audit.checks if c.status is CheckStatus.PASS)
    failed = sum(1 for c in audit.checks if c.status is CheckStatus.FAIL)
    na = sum(1 for c in audit.checks if c.status is CheckStatus.NOT_APPLICABLE)

    actions_bar = _status_stack(
        "Action items by severity",
        "The findings the briefing raises, ranked by severity.",
        [("High", high, "--bad"), ("Medium", med, "--warn"), ("Low", low, "--muted")],
        f"{len(findings)} finding{'s' if len(findings) != 1 else ''} in the briefing",
    )
    quality_bar = _status_stack(
        "Quality snapshot",
        "The DCMA-14 integrity checks behind the verdict.",
        [("Pass", passed, "--ok"), ("Fail", failed, "--bad"), ("N/A", na, "--muted")],
        f"{passed + failed} of {passed + failed + na} checks scored",
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{actions_bar}{quality_bar}</div>'
    )


def _briefing_body(briefing: ExecutiveBriefing, *, prov: str = "") -> str:
    """Render the leadership Executive Briefing (ADR-0121): a metadata header + a verdict banner,
    then the numbered forensic sections (Bottom Line, Performance, Critical Path Then & Now, Health
    Dashboard, Risks & Opportunities, Recommended Actions, How to Verify) as a single continuous
    document. Every statement and every table row carries its file + UID + task citation (§6).

    Panel contract (ADR-0337, chapter 12): the one ``.panel.brief-doc`` this renders wears the head
    strip + ⤓ EXCEL + ⛶ and the SERIES provenance chip (a briefing is built from every solvable
    version at once), plus a single ``.sf-take``.

    ``prov`` is a PARAMETER rather than something built here, and that is load-bearing: this
    function is also what ``/api/ai/briefing`` re-renders, and ``ai_polish.js`` replaces the whole
    of ``#briefingBody`` with the result. A chip built from a schedule this function cannot see
    would simply vanish on the AI swap, leaving a polished briefing wearing no provenance — so
    both call sites pass the same chip. (The toolbar itself is safe either way: panelkit.js binds
    ONE delegated listener on ``document``, so buttons that arrive via ``innerHTML`` still work.)
    """
    verdict_slug = briefing.verdict.lower().replace(" ", "-").replace("/", "")
    meta = "".join(
        f"<tr><th scope=row>{_e(k)}</th><td>{_e(v)}</td></tr>" for k, v in briefing.meta_rows
    )
    banner = "".join(
        f"<div class=brief-stat><span class=brief-stat-label>{_e(k)}</span>"
        f"<span class=brief-stat-value>{_e(v)}</span></div>"
        for k, v in briefing.banner
    )
    # full-width header (title + meta + verdict banner), then the numbered sections tiled into a
    # responsive card grid so the briefing fills the whole page width and each section stays cleanly
    # boxed instead of running down one narrow column.
    cited = sum(len(s.statements) for s in briefing.sections)
    header = (
        '<div class="panel brief-doc" data-export="/export/xlsx/briefing">'
        + _panel_head(
            _e(briefing.title),
            tools=_shell_tools(export_title=_BRIEFING_XLSX_TITLE),
            prov=prov,
        )
        # the take counts what is rendered directly below it, so the first number the reader meets
        # is one they can verify by looking down the page
        + f"<p class=sf-take data-no-i18n>{len(briefing.sections)} sections, {cited} cited "
        f"statement{'s' if cited != 1 else ''} — the verdict reads "
        f"{_e(briefing.verdict)}.</p>" + f"<p class=brief-subtitle>{_e(briefing.subtitle)}</p>"
        f"<table class=brief-meta>{meta}</table>"
        f'<div class="brief-banner verdict-{_e(verdict_slug)}">{banner}</div>'
        "<p class=muted>Every statement and table row cites file + UniqueID + task name. "
        'Hand-out copy: <a href="/export/docx/briefing">&#11015; Word</a> &middot; '
        '<a href="/export/xlsx/briefing">&#11015; Excel</a>.</p>'
    )

    def _section_html(section: BriefingSection) -> str:
        tag = f"h{min(section.level + 2, 6)}"
        prose = "".join(
            f"<p>{_e(s.text)} <span class=cite>[{_e(_cite_tag(s.citations))}]</span></p>"
            for s in section.statements
        )
        return (
            f"<{tag} class=brief-h>{_e(section.heading)}</{tag}>"
            f"{prose}{_briefing_table_html(section)}"
        )

    # group: each top-level (level 1) section opens a new card; its sub-sections nest inside it
    cards: list[list[str]] = []
    card_is_wide: list[bool] = []
    card_heading: list[str] = []
    for section in briefing.sections:
        if section.level <= 1 or not cards:
            cards.append([])
            card_is_wide.append(False)
            card_heading.append(section.heading)
        cards[-1].append(_section_html(section))
        # a table with many columns needs the full page row, not a half-width card
        if section.table is not None and len(section.table.headers) >= 5:
            card_is_wide[-1] = True
    # Half-page partner rows (operator 2026-07-08): pair sections that otherwise land in narrow
    # auto-fit columns with wasted white space beside a short neighbour. Each ordered (A, B) group
    # becomes one full-width `.brief-duo` row split 1fr/1fr, so neither section wastes page width
    # and long tables scroll inside their half (capped in CSS) rather than towering the page.
    duo_groups = (("Critical Path", "Schedule Health"), ("Recommended Actions", "How to Verify"))

    def _group_of(heading: str) -> tuple[int, int] | None:
        for g, (first, second) in enumerate(duo_groups):
            if first in heading:
                return (g, 0)
            if second in heading:
                return (g, 1)
        return None

    card_group = [_group_of(h) for h in card_heading]
    # only pair a group when BOTH members are actually present (a briefing with an empty/skipped
    # section falls back to a normal single card)
    counts: dict[int, int] = {}
    for cg in card_group:
        if cg:
            counts[cg[0]] = counts.get(cg[0], 0) + 1
    active_groups = {g for g, c in counts.items() if c == 2}

    card_html: list[str] = []
    duo_buffers: dict[int, list[str]] = {}
    for i, body in enumerate(cards):
        # the opening "Bottom Line" card spans the full width as the headline
        cls = (
            "brief-card lead"
            if i == 0
            else ("brief-card wide" if card_is_wide[i] else "brief-card")
        )
        cg = card_group[i]
        if cg and cg[0] in active_groups:
            buf = duo_buffers.setdefault(cg[0], [])
            buf.append(f'<section class="brief-card">{"".join(body)}</section>')
            if len(buf) == 2:
                card_html.append(f"<div class=brief-duo>{''.join(buf)}</div>")
        else:
            card_html.append(f'<section class="{cls}">{"".join(body)}</section>')
    grid = f"<div class=brief-grid>{''.join(card_html)}</div>"
    return f"{header}{grid}</div>"
