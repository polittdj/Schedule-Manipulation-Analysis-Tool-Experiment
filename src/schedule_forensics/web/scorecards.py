"""The /scorecards page family: the NASA STAT / GAO-10 / SRA-readiness ribbons, their
export table, and the committed-date parser the reserve-sizing API reads.

Monolith split, phase 4 slice 22 (ADR-0387), extracted VERBATIM from ``web/app.py``: every
function and constant moves byte-for-byte -- docstrings, comments and HTML f-strings
unchanged -- and only the module boundary is new.

The seam is the AST transitive closure of all THREE routes -- ``/scorecards``,
``/api/scorecards/buffer`` and ``/export/{fmt}/scorecards``.  FIVE names: four in one
contiguous block (app.py 7794-7941) plus ``_parse_committed_date``, which lived 6,500
lines away at 1206 and is reached only by the buffer route.  Neither
``_parse_committed_date`` nor ``_sc_status_class`` carries a ``scorecard`` prefix.

**Unlike every family since ADR-0378, the export route DOES share the page's surface:**
``export_scorecards`` calls ``_scorecard_export_table``, so the eight
``/export/{fmt}/scorecards`` labels sit inside this family's proven surface and the
probe was anchored to reach them.

``_sources_line`` is called by ``_scorecards_body`` and by eight other page routes, so
it could not stay in ``app.py`` without this module importing UPWARD.  It descended
into ``components.py`` -- the shared kernel every view module may import -- which is
where ADR-0351, ADR-0376 and ADR-0377 each sent the same kind of name.

Layering: ``app`` -> ``scorecards`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

import datetime as dt
from urllib.parse import quote

from schedule_forensics.engine.scorecards import Scorecard, compute_scorecards
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.reports.tables import Cell, Table
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.components import (
    _panel_head,
    _prov_chip,
    _shell_tools,
    _sources_line,
)
from schedule_forensics.web.state import _Analysis


def _parse_committed_date(value: str | None) -> dt.datetime | None:
    """A committed finish date from an ``YYYY-MM-DD`` form value (midnight), or ``None``."""
    if not value:
        return None
    try:
        d = dt.date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None
    return dt.datetime(d.year, d.month, d.day)


def _sc_status_class(status: str) -> str:
    # class-name lookup (not a secret) — B105 is a false positive.
    return {"PASS": "pass", "FAIL": "fail", "INFO": "info"}.get(status, "na")  # nosec B105


def _scorecard_export_table(sc: Scorecard) -> Table:
    """One assessment scorecard as an export table (Check / Result / Detail / Source)."""
    rows: tuple[tuple[Cell, ...], ...] = tuple(
        (c.label, c.status, c.detail, c.provenance) for c in sc.checks
    )
    return Table(f"{sc.name} — {sc.framework}", ("Check", "Result", "Detail", "Source"), rows)


def _scorecard_panel(sc: Scorecard, file_key: str, *, prov: str = "", export_url: str = "") -> str:
    """One assessment scorecard as a panel: a pass/fail/info chip ribbon over a detail table.

    Pure presentation over the validated :class:`Scorecard`; every chip's figure and the source it
    is drawn from come straight from the engine (no re-scoring here). A check that cites offending
    activities gets the ``sf-drill`` hook so clicking "(N activities)" lists them (add columns +
    Excel) via ``drilldown.js`` against ``file_key``.

    Mission Ops rank 8: the panel wears the contract — headline strip + tools + provenance chip
    (``prov``), with the existing score line restyled as the ``sf-take`` (same engine figures,
    verbatim). ⤓ EXCEL renders only when ``export_url`` names an EXISTING endpoint (the
    three-scorecard workbook, /export/xlsx/scorecards); ▦ DATA is omitted — the table IS the
    data (the home-shell precedent)."""
    score = f"{sc.passed}/{sc.scored} scored checks pass" if sc.scored else "no scored checks"
    chips = "".join(
        f'<span class="sl-chip sl-{_sc_status_class(c.status)}" '
        f'title="{_e(c.label)}: {_e(c.detail)} — {_e(c.provenance)}">'
        f"<span class=sl-name>{_e(c.label)}</span> <b>{_e(c.status)}</b></span>"
        for c in sc.checks
    )
    rows = ""
    for c in sc.checks:
        if c.offender_uids:
            payload = ",".join(str(u) for u in c.offender_uids)
            drill = (
                f' <button type=button class="linkbtn sf-drill" data-uids="{_e(payload)}" '
                f'data-file="{_e(file_key)}" data-title="{_e(c.label)}">'
                f"{len(c.offender_uids)} activities</button>"
            )
        else:
            drill = ""
        rows += (
            f"<tr><td>{_e(c.label)}</td>"
            f'<td><span class="sl-chip sl-{_sc_status_class(c.status)}">'
            f"<b>{_e(c.status)}</b></span></td>"
            f"<td>{_e(c.detail)}{drill}</td>"
            f"<td class=muted>{_e(c.provenance)}</td></tr>"
        )
    export_attr = f' data-export="{_e(export_url)}"' if export_url else ""
    tools = _shell_tools(
        export_title=(
            "Export the three assessment scorecards for this version — opens in Excel"
            if export_url
            else ""
        )
    )
    return (
        f'<div class=panel data-scorecard="{_e(sc.key)}"{export_attr}>'
        + _panel_head(_e(sc.name), tools=tools, prov=prov)
        + f"<p class=muted>{_e(sc.framework)}</p>"
        + f"<p class=sf-take data-no-i18n><b>{score}</b> &middot; {sc.info} informational "
        f"&middot; {sc.na} n/a</p>"
        + f'<div class=stoplight-board role=list aria-label="{_e(sc.name)} ribbon">{chips}</div>'
        + "<table class=scorecard-table><tr><th scope=col>Check</th>"
        "<th scope=col>Result</th><th scope=col>Detail</th><th scope=col>Source</th></tr>"
        f"{rows}</table></div>"
    )


def _scorecards_body(
    versions: list[tuple[str, Schedule, _Analysis]],
    current_key: str,
    sch: Schedule,
    a: _Analysis,
) -> str:
    """The Assessment Scorecards page (issue #331): NASA STAT + GAO-10 + SRA-readiness ribbons for
    the chosen version, plus a reserve-sizing card fed by the on-demand SRA buffer API."""
    stat, gao, ready = compute_scorecards(sch, a.cpm, a.audit)

    def _clause(sc: Scorecard, noun: str) -> str:
        return f"{sc.passed}/{sc.scored} {noun}" if sc.scored else f"no scored {noun}"

    takeaway = (
        f"GAO {_clause(gao, 'best practices met')} &middot; "
        f"NASA STAT {_clause(stat, 'structural checks pass')} &middot; "
        f"SRA-readiness {_clause(ready, 'gates green')}."
    )
    opts = ""
    for key, vsch, _va in versions:
        label = vsch.source_file or vsch.name
        status = f" · {vsch.status_date.date().isoformat()}" if vsch.status_date is not None else ""
        sel = " selected" if key == current_key else ""
        opts += f'<option value="{_e(key)}"{sel}>{_e(label)}{_e(status)}</option>'
    selector = (
        "<form method=get action=/scorecards class=viz-controls>"
        "<label>Assess version <select name=file data-no-i18n "
        f"data-sf-autosubmit>{opts}</select></label>"
        f'<a class=btn href="/export/xlsx/scorecards?file={_e(current_key)}">Export (Excel)</a>'
        f'<a class=btn href="/export/docx/scorecards?file={_e(current_key)}">Export (Word)</a>'
        "</form>"
    )
    # rank 8: the panels' shared provenance chip (the assessed version) + the ⤓ EXCEL target —
    # the EXISTING three-scorecard workbook endpoint for THIS version (never a dead link).
    prov = _prov_chip(sch)
    export_url = f"/export/xlsx/scorecards?file={quote(current_key, safe='')}"
    reserve = (
        "<div class=panel>"
        + _panel_head("Reserve / buffer sizing", tools=_shell_tools(), prov=prov)
        + "<p class=muted>How much schedule reserve protects a committed <b>project finish</b> date "
        "at a chosen confidence, read from the SRA Monte-Carlo finish distribution "
        "(engine/sra.py). Enter the committed date and run — the simulation is off the page-load "
        "path so it only runs when you ask.</p>"
        f'<form id=reserveForm class=viz-controls data-file="{_e(current_key)}">'
        "<label>Committed finish date <input type=date id=reserveDate></label>"
        "<label>Iterations <input type=number id=reserveIters value=1000 min=100 max=5000 "
        "step=100></label>"
        "<button type=button id=reserveRun class=btn>Size the reserve</button>"
        "</form>"
        "<div id=reserveOut aria-live=polite></div></div>"
    )
    panels = (
        _scorecard_panel(stat, current_key, prov=prov, export_url=export_url)
        + _scorecard_panel(gao, current_key, prov=prov, export_url=export_url)
        + _scorecard_panel(ready, current_key, prov=prov, export_url=export_url)
    )
    # rank 8: the Chapter-02 beat's muted lede under the existing takeaway h1 (the kicker
    # comes from _page's spine resolution — "Assessment Scorecards" is a ch-02 title).
    lede = (
        '<p class="page-lede">Three published assessment frameworks scored on the chosen '
        "version &mdash; NASA STAT structure checks, GAO&rsquo;s 10 scheduling best "
        "practices, and the SRA-readiness gate &mdash; every check computed from the "
        "schedule itself, cited to its source, and drillable to the activities behind "
        "it.</p>"
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{takeaway}</h1>'
        f"{lede}"
        f"{_sources_line([sch])}"
        f"{selector}"
        f"{panels}"
        f"{reserve}"
        "<div id=sfDrillMount></div>"  # drilldown.js loaded globally in _LAYOUT
        '<script src="/static/scorecards.js"></script>'
        '<script src="/static/panelkit.js"></script>'
    )
