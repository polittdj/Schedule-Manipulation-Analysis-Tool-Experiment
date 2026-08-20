"""The /ribbon page family: the Acumen-Fuse-style Schedule Quality Ribbon and its cell rules.

Monolith split, phase 4 slice 24 (ADR-0389), extracted VERBATIM from ``web/app.py``: every
definition moves byte-for-byte -- docstrings, comments and HTML f-strings unchanged -- and only
the module boundary is new. The four ``#:``-documented threshold constants travel WITH their
functions: a threshold separated from the code that reads it is how a display convention becomes
a mystery number.

The seam is the AST transitive closure of the family's entry points, seeded on the EXACT route
list ``/ribbon`` + ``/export/{fmt}/ribbon`` + ``/export/{fmt}/ribbon-drill/{name}``. Nine names,
ZERO descents.

``_can_we_trust_header`` is chapter 02's header rather than the ribbon page's own, but it is a
ribbon MEMBER by measurement, not by name: it takes ``RibbonMetrics`` and is reached from no
other family's movers.

Layering: ``app`` -> ``ribbon`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

import json

from schedule_forensics.engine.metrics import RibbonMetrics, compute_activity_makeup
from schedule_forensics.engine.metrics._common import CheckStatus, MetricResult
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.components import (
    _metric_help_cell,
    _panel_head,
    _shell_tools,
    _stat_cards,
    _status_class,
    _status_stack,
)
from schedule_forensics.web.state import _Analysis

#: display convention (operator 2026-07-08): a thresholded measure that PASSES but sits at or
#: above this fraction of its threshold shows as a YELLOW warning (approaching the limit).
_RIBBON_WARN_FRACTION = 0.8

#: ribbon columns whose color comes from a zero-tolerance DCMA threshold (any offender = fail)
_RIBBON_ZERO_TOLERANCE = {"negative_float": "DCMA-07", "number_of_leads": "DCMA-02"}
#: ribbon columns colored from the DCMA-05 5%-of-activities threshold
_RIBBON_PCT5 = {"hard_constraints"}
#: ribbon float columns that are a mean/max of the incomplete-activity population — a placeholder
#: 0.0 when that population is empty, so they render "—" not a fabricated figure (audit NEW-1)
_RIBBON_FLOAT_EXTRAS = {"avg_float_days", "max_float_days"}


def _ribbon_cell_class(attr: str, r: object, quality: dict[str, MetricResult]) -> str:
    """pass (green) / warning (yellow) / fail (red) for thresholded measures; '' = no threshold.

    Thresholds come from the Bible-validated quality metrics where they exist; Negative Float
    and Leads use the DCMA zero-tolerance rule; Hard Constraints COLORS by the 5%-of-activities
    bar (the published DCMA-05 threshold) while its VALUE is the Fuse mandatory-only count
    (ADR-0429) — the bar is a display convention on the same 0-5% scale Fuse shades green.
    The warning band (PASS but >= 80% of the threshold) is a display convention, not a metric.
    """
    q = quality.get(attr)
    if q is not None and q.threshold is not None:
        if q.status is CheckStatus.FAIL:
            return "rib-fail"
        if q.status is CheckStatus.PASS:
            return "rib-warn" if q.value >= _RIBBON_WARN_FRACTION * q.threshold else "rib-pass"
        return ""
    count = getattr(r, attr, None)
    if attr in _RIBBON_ZERO_TOLERANCE and isinstance(count, int):
        return "rib-pass" if count == 0 else "rib-fail"
    if attr in _RIBBON_PCT5 and isinstance(count, int) and q is not None and q.population:
        pct = 100.0 * count / q.population
        if pct > 5.0:
            return "rib-fail"
        return "rib-warn" if pct >= _RIBBON_WARN_FRACTION * 5.0 else "rib-pass"
    return ""  # no published threshold — neutral


#: rank 8 — the tooltip's verdict WORD for each cell tone, read off the class the cell already
#: wears (single source: :func:`_ribbon_cell_class`; the title never re-judges a threshold).
_RIBBON_CLS_VERDICT = {
    "rib-pass": "PASS",
    "rib-warn": "PASS, warning band (≥80% of the threshold)",
    "rib-fail": "FAIL",
}


def _ribbon_cell_title(
    label: str, attr: str, r: object, quality: dict[str, MetricResult], cls: str
) -> str:
    """The threshold tooltip for a ribbon-matrix cell — the EXISTING native ``title=``
    mechanism these cells already carry (Mission Ops rank 8; never a second tooltip system).

    Every figure is quoted verbatim from the quality :class:`MetricResult` (value / threshold /
    direction) or the ribbon count the cell already shows; the verdict word comes from the class
    :func:`_ribbon_cell_class` already assigned, so nothing is re-judged here. Unthresholded
    measures say so — the same "neutral" vocabulary as the legend."""
    click = "Click to list the activities behind this figure."
    verdict = _RIBBON_CLS_VERDICT.get(cls, "")
    q = quality.get(attr)
    if q is not None and q.threshold is not None and verdict:
        unit = "%" if q.unit == "%" else ""
        comp = str(q.direction) if q.direction is not None else "<="
        return (
            f"{label}: {q.value:g}{unit} — published threshold {q.threshold:g}{unit} "
            f"(pass when {comp} threshold) — {verdict}. {click}"
        )
    count = getattr(r, attr, None)
    if attr in _RIBBON_ZERO_TOLERANCE and isinstance(count, int) and verdict:
        return (
            f"{label}: {count} — {_RIBBON_ZERO_TOLERANCE[attr]} zero-tolerance rule "
            f"(pass when 0) — {verdict}. {click}"
        )
    if attr in _RIBBON_PCT5 and isinstance(count, int) and verdict:
        return f"{label}: {count} — DCMA-05 5% rule — {verdict}. {click}"
    return f"{label}: no published threshold — neutral. {click}"


def _can_we_trust_header(sch: Schedule, analysis: _Analysis, ribbon: RibbonMetrics) -> str:
    """Chapter 02 "Can we trust the plan?" (ADR-0198): the data-driven takeaway + a quality-KPI
    strip + the DCMA-outcome and logic-completeness bars, for the LATEST loaded version — every
    figure read from the ribbon/audit the page already computed (no engine math; honest counts)."""
    checks = analysis.audit.checks
    passes = sum(1 for c in checks if _status_class(c.status) == "pass")
    fails = sum(1 for c in checks if _status_class(c.status) == "fail")
    na = sum(1 for c in checks if _status_class(c.status) == "na")
    scored = passes + fails
    total = compute_activity_makeup(sch).total

    # takeaway — the top one/two structural weaknesses, stated as real counts with correct
    # singular/plural agreement (or "clean" when there are none)
    def _acts(n: int) -> str:
        return "activity" if n == 1 else "activities"

    phrases: list[str] = []
    if ribbon.missing_logic:
        n = ribbon.missing_logic
        phrases.append(f"{n} {_acts(n)} {'misses' if n == 1 else 'miss'} logic")
    if ribbon.negative_float:
        n = ribbon.negative_float
        phrases.append(f"{n} {_acts(n)} {'carries' if n == 1 else 'carry'} negative float")
    if ribbon.hard_constraints:
        n = ribbon.hard_constraints
        con = "a hard constraint" if n == 1 else "hard constraints"
        phrases.append(f"{n} {_acts(n)} {'sits' if n == 1 else 'sit'} on {con}")
    if phrases:
        weak = " — " + ", and ".join(phrases[:2]) + "."
    else:
        weak = " — logic is complete, with no negative float or hard constraints."
    scored_txt = (
        f"{passes} of {scored} DCMA-14 quality checks pass"
        if scored
        else ("the DCMA-14 checks don't apply to this file")
    )
    takeaway = f"{scored_txt}{weak}"

    kpi = _stat_cards(
        [
            ("DCMA checks passed", f"{passes} / {scored}" if scored else "—"),
            ("Missing logic", str(ribbon.missing_logic)),
            ("Hard constraints", str(ribbon.hard_constraints)),
            ("Negative float", str(ribbon.negative_float)),
            ("Logic density", f"{ribbon.logic_density:g}"),
            ("Insufficient detail", str(ribbon.insufficient_detail)),
        ]
    )
    dcma_bar = _status_stack(
        "DCMA-14 checks",
        "The 14 DCMA schedule-quality checks by outcome (n/a where no threshold applies).",
        [("Pass", passes, "--ok"), ("Fail", fails, "--bad"), ("N/A", na, "--muted")],
        f"{len(checks)} checks",
    )
    wired = max(total - ribbon.missing_logic, 0)
    logic_bar = _status_stack(
        "Logic completeness",
        "Activities wired with a predecessor and successor vs those missing logic.",
        [("Logic wired", wired, "--ok"), ("Missing logic", ribbon.missing_logic, "--bad")],
        f"{total} activities",
    )
    # Mission Ops rank 8: the Chapter-02 beat's muted lede under the takeaway h1 (the kicker
    # itself comes from _page's spine resolution — "Schedule Quality Ribbon" is a ch-02 title).
    lede = (
        '<p class="page-lede">Whether the schedule is built soundly enough to trust its '
        "numbers &mdash; the DCMA-14 construct and the Fuse-validated ribbon measures for "
        "every loaded version, each count computed from the schedule&rsquo;s own logic and "
        "drillable to the activities behind it.</p>"
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{takeaway}</h1>'
        f"{lede}"
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{dcma_bar}{logic_bar}</div>'
    )


def _ribbon_body(
    rows: list[tuple[str, object, dict[str, MetricResult]]],
    note: str,
    drill: dict[str, dict[str, tuple[int, ...]]] | None = None,
    *,
    prov: str = "",
) -> str:
    """The Acumen-Fuse-style Schedule Quality Ribbon: one row per loaded schedule, one column
    per ribbon metric — the metrics validated against the operator's Fuse workbook export.
    Thresholded measures are color-coded pass/warning/fail, and every metric cell is CLICKABLE
    (operator 2026-07-08): the click lists that file's activities behind the figure below, with
    UID / name / duration / % complete / start / finish plus a set-once persistent Columns
    picker (standard + custom fields) and an Excel export of exactly the selection."""
    cols = [
        ("Missing Logic", "missing_logic"),
        ("Logic Density™", "logic_density"),
        ("Critical", "critical"),
        ("Hard Constraints", "hard_constraints"),
        ("Negative Float", "negative_float"),
        ("Number of Lags", "number_of_lags"),
        ("Number of Leads", "number_of_leads"),
        ("Merge Hotspot", "merge_hotspot"),
        ("Insufficient Detail™", "insufficient_detail"),
        ("Avg Float (d)", "avg_float_days"),
        ("Max Float (d)", "max_float_days"),
    ]
    midcol = len(cols) // 2
    head_row = "<th scope=col>Schedule</th>" + "".join(
        f"<th scope=col class=metric-th>"
        f"{_metric_help_cell(label, attr, align='right' if i >= midcol else 'left')}</th>"
        for i, (label, attr) in enumerate(cols)
    )
    body = ""
    for key, r, quality in rows:
        cells = ""
        # A fully-progressed schedule has an empty incomplete-activity float population, so
        # avg/max_float_days are a placeholder 0.0 — render "—" (not a fabricated mean/max), and
        # make the cell non-clickable since there is nothing to drill (audit NEW-1).
        na_floats = getattr(r, "incomplete_float_count", 0) == 0
        for label, attr in cols:
            if attr in _RIBBON_FLOAT_EXTRAS and na_floats:
                cells += (
                    '<td class="rib-na" title="No incomplete activities — '
                    'this measure is not applicable">—</td>'
                )
                continue
            cls = _ribbon_cell_class(attr, r, quality)
            # rank 8: the threshold tooltip rides the EXISTING title= these cells already carry
            # (no second tooltip system); every figure/verdict quoted from the engine's own
            # MetricResult and the class the cell already wears — never re-judged here.
            title = _ribbon_cell_title(label, attr, r, quality, cls)
            cells += (
                f'<td class="rib-cell {cls}" data-file="{_e(key)}" data-metric="{attr}" '
                f'tabindex=0 role=button title="{_e(title)}">'
                f"{_e(getattr(r, attr))}</td>"
            )
        # rank 8: the row label wears the 3px LEFT edge (the k-edge / cite-card family) and is
        # i18n-inert (a filename must never be translated).
        body += f"<tr><td class=rib-row-label data-no-i18n>{_e(key)}</td>{cells}</tr>"
    labels = {attr: label for label, attr in cols}
    # <-escape the inline-JSON embeds like every sibling embed (audit ADR-0250): a </script> in a
    # schedule key can't currently arise (keys are Path.name, no slash) but the escape is the
    # explicit barrier, not an implicit Path.name side effect, and keeps the pattern uniform.
    drill_json = json.dumps(
        {k: {m: list(u) for m, u in v.items()} for k, v in (drill or {}).items()}
    ).replace("<", "\\u003c")
    labels_json = json.dumps(labels).replace("<", "\\u003c")  # uniform <-escape (static labels)
    drill_script = (
        f'<script id=sfRibbonDrillData type="application/json">'
        f'{{"drill": {drill_json}, "labels": {labels_json}}}</script>'
        "<div id=ribbonDrill class=ribbon-drill></div>"
        '<script src="/static/ribbon_drill.js"></script>'
    )
    # ── rank 8: the matrix panel wears the contract — headline strip + ⤓/⛶ tools + prov chip +
    # a one-line sf-take quoting totals the page already renders (row/column counts — never a
    # re-derived metric). ▦ DATA is omitted (the matrix IS the data); ⤓ EXCEL rides the EXISTING
    # /export/xlsx/ribbon endpoint via the panel's data-export (the home/portfolio precedent). ──
    n_rows = len(rows)
    take = (
        f"<p class=sf-take data-no-i18n>{n_rows} schedule version{'s' if n_rows != 1 else ''} "
        f"&times; {len(cols)} Fuse-validated measures — colored where a published threshold "
        "exists; hover any cell for its threshold, click it to list the activities behind the "
        "figure.</p>"
    )
    tools = _shell_tools(
        export_title="Export the quality ribbon — one row per loaded file — opens in Excel"
    )
    head = _panel_head("Schedule Quality Ribbon", tools=tools, prov=prov)
    return f"""{note}
<div class=panel data-export="/export/xlsx/ribbon">{head}
{take}
<p class=muted>The schedule-quality ribbon metrics, one row per loaded
schedule. <b>Missing Logic</b> = activities missing a predecessor and/or successor;
<b>Logic Density™</b> = logic links per activity (2&times;links &divide; activities);
<b>Critical</b> = activities the source tool flags critical (its stored Critical / Total Slack);
<b>Lags</b> / <b>Leads</b> = activities whose predecessors carry a positive / negative offset,
counted across all statuses (planned, in-progress, or complete &mdash; unlike the
incomplete-only DCMA-14 checks); <b>Hard Constraints</b> = activities pinned by a
<i>must / mandatory</i> date (Must&nbsp;Start/Finish&nbsp;On, Mandatory&nbsp;Start/Finish),
counted across all statuses per the NASA Acumen library's ribbon formula &mdash; the
no-later-than caps (SNLT/FNLT) belong to DCMA-05, a different metric of the same name;
<b>Negative Float</b> = incomplete activities whose <i>stored</i> Total Slack (the source
tool's own value) is negative &mdash; Fuse's arithmetic; the DCMA-07 card scopes and rounds
differently by design; <b>Merge Hotspot</b> = activities with more than two predecessors. <b>Insufficient Detail™</b> = activities whose duration exceeds 10% of the
project span (the NASA Acumen library formula, Fuse-validated). These are validated against the
reference schedule-quality export. <i>Float Ratio™ is omitted pending its exact definition.</i>
<span class=rib-legend><span class=rib-pass>pass</span> <span class=rib-warn>warning
(&ge;80% of threshold)</span> <span class=rib-fail>fail</span> &mdash; colored where a
published threshold exists; unthresholded measures stay neutral.</span>
<b>Click any metric cell</b> to list the activities behind that figure below.</p>
<table><tr>{head_row}</tr>{body}</table></div>{drill_script}
<script src="/static/panelkit.js"></script>"""
