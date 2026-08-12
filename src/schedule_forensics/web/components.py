"""Shared presentation components — the primitives every page panel is built from.

Monolith split, phase 3 (ADR-0350), following the method ADR-0297 set and ADR-0349 proved:
the extraction is VERBATIM — every function, constant, docstring and comment moves
byte-for-byte, only the module boundary changes.

Membership was MEASURED, not chosen. An AST transitive closure of each page family's entry
points showed these names are reached by THREE OR MORE families, so no single page can own
them: ``_panel_head`` is reached by 47, ``_shell_tools`` by 41, ``_prov_chip`` by 21. Leaving
them in ``app.py`` is what blocked phase 3 — any per-page cut would have dragged the shared
strip into one page's module and made 60-odd unrelated helpers import their panel header from
it. The closure of this set is CLOSED: it calls nothing that stays behind.

Nothing here imports ``web.app``; the dependency runs one way —
``app`` → ``components`` → ``chrome`` → ``state`` → engine/model. ``app.py`` re-exports every
name below with the explicit ``X as X`` idiom, so existing import paths (and the tests that use
them) keep working unchanged.

One deliberate edge: ``_e`` stays in ``chrome`` (ADR-0349 placed it there) and is imported
upward from here. That is acyclic and intentional — moving ``_e`` a second time would repoint
phase 2's source-text guards for no behavioural gain. It is a candidate to descend into this
module in a later phase.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from urllib.parse import quote

from schedule_forensics.engine.cpm import CPMError, CPMResult, offset_to_datetime
from schedule_forensics.engine.driving_slack import PathTier
from schedule_forensics.engine.metrics._common import MetricResult
from schedule_forensics.engine.sra import ScheduleRisk, SSIRiskStat
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.help import field_or_metric_doc
from schedule_forensics.web.state import SessionState, _Analysis


def _mdY(value: dt.date | dt.datetime | str | None) -> str:
    """A displayed date as ``MM/DD/YYYY`` (operator convention), never a time-of-day.

    Accepts a date, a datetime (time dropped), or an ISO ``YYYY-MM-DD[Txx]`` string; ``None``
    or an unparsable string renders as an em dash. Data payloads/exports stay ISO — this is
    the presentation boundary only."""
    if value is None:
        return "—"
    if isinstance(value, str):
        try:
            parsed: dt.date = dt.date.fromisoformat(value[:10])
        except ValueError:
            return value
    elif isinstance(value, dt.datetime):
        parsed = value.date()
    else:
        parsed = value
    return f"{parsed.month:02d}/{parsed.day:02d}/{parsed.year:04d}"


def _user_tip(text: str) -> str:
    """A small, consistent "User Tip" call-out to guide the operator on a page or control.

    ``text`` is a developer-authored static string (it may contain simple inline HTML such as
    ``<b>`` for emphasis); it is never operator input, so it is embedded as-is. Rendered the same
    way everywhere so tips read consistently across the tool.
    """
    return (
        '<p class="user-tip" role="note"><span class="ut-badge">User Tip</span> '
        f"<span>{text}</span></p>"
    )


def _status_class(status: object) -> str:
    # the values are CSS class names (not secrets); B105 is a false positive here.
    return {"PASS": "pass", "FAIL": "fail"}.get(str(status), "na")  # nosec B105


# ── Panel-contract helpers (Mission Ops rank 3, ADR-0298): the reusable headline strip +
# three-glyph tools + provenance chip for the per-schedule analysis panels. Presentation only —
# every figure a takeaway line quotes is an engine output the panel already renders verbatim.


def _prov_chip(sch: Schedule) -> str:
    """The panel-contract provenance chip — ``SOURCE: file · DD date``. i18n-inert
    (filenames and dates must never be translated — rank-3 risk note)."""
    dd = sch.status_date.date().isoformat() if sch.status_date is not None else "—"
    return (
        f"<span class=prov-chip data-no-i18n>SOURCE: {_e(sch.source_file or sch.name)}"
        f" · DD {dd}</span>"
    )


def _pair_prov_chip(prior: Schedule, current: Schedule, vfrom: int, vto: int) -> str:
    """The version-PAIR provenance chip for the compare views (Mission Ops rank 5) —
    ``v1→v2 · SOURCE: a → b · DD d1 → d2`` — the prototype's 'v4→v5' vocabulary rendered
    with the SAME .prov-chip class as :func:`_prov_chip` (never a parallel vocabulary).
    i18n-inert: version labels, filenames and dates must never be translated."""
    p_dd = prior.status_date.date().isoformat() if prior.status_date is not None else "—"
    c_dd = current.status_date.date().isoformat() if current.status_date is not None else "—"
    return (
        f"<span class=prov-chip data-no-i18n>v{vfrom}→v{vto} · "
        f"SOURCE: {_e(prior.source_file or prior.name)} → "
        f"{_e(current.source_file or current.name)} · DD {p_dd} → {c_dd}</span>"
    )


def _series_prov_chip(versions: Sequence[Schedule]) -> str:
    """The provenance chip for a panel drawn from the WHOLE loaded series (Mission Ops rank 9):
    one file → :func:`_prov_chip`; several → the first→last :func:`_pair_prov_chip`. The SAME
    ``.prov-chip`` vocabulary both already speak (never a third convention) — the pattern
    :func:`_focus_panel` established for a series panel. Empty when nothing is loaded."""
    if not versions:
        return ""
    if len(versions) == 1:
        return _prov_chip(versions[0])
    return _pair_prov_chip(versions[0], versions[-1], 1, len(versions))


def _sources_line(schedules: Sequence[Schedule]) -> str:
    """The provenance line every multi-file visual carries (ADR-0150): which loaded file(s)
    the data on this page is drawn from, so the operator always knows what they are looking
    at — one name for a single file, the full list for a mix."""
    names = [_e(s.source_file or s.name) for s in schedules]
    if not names:
        return ""
    if len(names) == 1:
        return f"<p class=muted>Source file: <b>{names[0]}</b></p>"
    return (
        f"<p class=muted>Sources ({len(names)} files, oldest first): <b>"
        + "</b>, <b>".join(names)
        + "</b></p>"
    )


def _shell_tools(*, export_title: str = "", big: bool = True) -> str:
    """The three-glyph tool strip (panelkit.js wiring): ⤓ EXCEL renders ONLY when the panel
    carries a ``data-export`` URL to an EXISTING endpoint (never a dead link — rank-3 law);
    ⛶ ENLARGE by default. ▦ DATA is omitted on the analysis panels: each one's table IS the
    data (the home-shell precedent). ``big=False`` omits the ⛶ for the ONE panel whose chart
    script supplies the panel's single ⛶ itself (the /analysis scatter — the curves.js
    pattern, ADR-0317): a second head glyph on that panel was the round-11 inert-duplicate
    defect (it flipped its label while ``:has(.sf-tilebox)`` kept the panel static)."""
    excel = (
        f'<button type=button data-sf-excel title="{_e(export_title)}" '
        'aria-label="Export this panel&#39;s data to Excel">⤓ EXCEL</button>'
        if export_title
        else ""
    )
    enlarge = (
        "<button type=button data-sf-big aria-pressed=false "
        'aria-label="Enlarge this panel">⛶ ENLARGE</button>'
        if big
        else ""
    )
    return f"<div class=sf-tools data-noprint=1>{excel}{enlarge}</div>"


def _panel_head(title: str, *, tools: str = "", prov: str = "", h2_attrs: str = "") -> str:
    """The panel-contract headline strip: h2 + tools + provenance chip. ``title`` is HTML —
    callers escape their own dynamic parts (the heading TEXT is unchanged; the uppercase
    treatment is CSS, so existing content assertions keep holding). ``h2_attrs`` carries a
    pre-existing heading attribute through a conversion (leading space included, e.g.
    ``" data-no-i18n"``) — the /margin headings were deliberately translation-pinned and
    joining the contract must not silently unpin them."""
    return f"<div class=panel-head><h2{h2_attrs}>{title}</h2>{tools}{prov}</div>"


#: ⤓ EXCEL hover text for panels whose data ships inside the existing per-schedule analysis
#: workbook export (/export/{fmt}/analysis/{name} — DCMA, float bands, completion, findings,
#: activities sheets). One string so every panel names the same real destination.
_ANALYSIS_XLSX_TITLE = (
    "Export this schedule's analysis workbook (this panel's data is one of its sheets) — "
    "opens in Excel"
)


def _analysis_export_attr(key: str) -> str:
    """The panel-level data-export URL panelkit.js follows — the EXISTING analysis workbook
    endpoint for this schedule (never a dead link)."""
    return f' data-export="/export/xlsx/analysis/{quote(key, safe="")}"' if key else ""


def _stat_cards(cards: list[tuple[str, str]]) -> str:
    """A responsive grid of label/value stat cards (the deck's KPI-card row)."""
    items = "".join(
        f"<div class=stat-card><div class=stat-value>{_e(value)}</div>"
        f"<div class=stat-label>{_e(label)}</div></div>"
        for label, value in cards
    )
    return f"<div class=stat-grid>{items}</div>"


def _metric_help_cell(label: str, metric_id: str, *, align: str = "left") -> str:
    """Inner HTML for a metric column header: the label plus a hover/focus call-out from the in-tool
    dictionary — what the metric is, how it's calculated, a real-world example of how it's used, and
    what it indicates. Falls back to the plain label when the metric isn't documented. Reuses the
    DCMA tooltip styling; wrap the result in a positioned cell (``<th class=metric-th>``). ``align``
    'right' anchors the pop-out to the cell's right edge so a wide table's right columns don't clip."""
    doc = field_or_metric_doc(metric_id)
    if doc is None:
        return _e(label)
    tip_id = f"mh-{_e(metric_id)}"
    tip_cls = "dcma-tip mtip mtip-right" if align == "right" else "dcma-tip mtip"
    used = doc.use_case or doc.importance
    rich = [
        f"<b>{_e(doc.name)}</b>",
        f"<p>{_e(doc.definition)}</p>",
        f"<p><b>How it&#39;s calculated:</b> {_e(doc.formula)}</p>",
    ]
    title = f"{doc.name}. {doc.definition} How it's calculated: {doc.formula}."
    if used:
        rich.append(f"<p><b>Real-world use:</b> {_e(used)}</p>")
        title += f" Real-world use: {used}"
    if doc.indicates:
        rich.append(f"<p><b>Indicates:</b> {_e(doc.indicates)}</p>")
        title += f" Indicates: {doc.indicates}"
    if doc.threshold:
        rich.append(f"<p><b>Threshold:</b> {_e(doc.threshold)}</p>")
    return (
        f'<span class="dcma-metric mhelp" tabindex=0 role=button aria-describedby="{tip_id}" '
        f'title="{_e(title)}">{_e(label)} '
        f"<span class=dcma-info aria-hidden=true>&#9432;</span></span>"
        f'<div class="{tip_cls}" id="{tip_id}" role=tooltip>{"".join(rich)}</div>'
    )


def _status_stack(
    title: str,
    desc: str,
    segments: list[tuple[str, int, str]],
    foot: str,
    drill: list[tuple[tuple[int, ...], str]] | None = None,
) -> str:
    """A single stacked bar with a legend of labelled counts — the redesign's composition visual
    (Activity status mix; Float remaining). ``segments`` = (label, count, css-var color).

    ``drill`` (optional, parallel to ``segments``) makes a segment CLICKABLE: entry ``i`` is
    ``(activity_uids, file_key)``; a segment with a non-empty UID set + file gets the ``sf-drill``
    hook (data-uids / data-file / data-title) that ``drilldown.js`` turns into a "list the
    activities behind this segment + add columns + Excel" grid. Omit ``drill`` (default) and every
    existing caller renders byte-for-byte as before."""
    total = sum(c for _, c, _ in segments) or 1

    def _drill_attrs(i: int, label: str) -> tuple[str, str]:
        """(extra class, extra attributes) for segment/legend ``i`` when it is drillable."""
        if not drill or i >= len(drill):
            return "", ""
        uids, fkey = drill[i]
        if not uids or not fkey:
            return "", ""
        payload = ",".join(str(u) for u in uids)
        attrs = (
            f' data-uids="{_e(payload)}" data-file="{_e(fkey)}" '
            f'data-title="{_e(f"{title} — {label}")}" role="button" tabindex="0"'
        )
        return " sf-drill", attrs

    seg_html = []
    for i, (label, c, color) in enumerate(segments):
        if c <= 0:
            continue
        cls, attrs = _drill_attrs(i, label)
        tip = f"{label}: {c}" + (" — click to list the activities" if cls else "")
        seg_html.append(
            f'<span class="stack-seg{cls}" style="width:{100.0 * c / total:.3f}%;'
            f'background:var({color})" title="{_e(tip)}"{attrs}></span>'
        )
    bar = "".join(seg_html)
    legend_html = []
    for i, (label, c, color) in enumerate(segments):
        cls, attrs = _drill_attrs(i, label)
        legend_html.append(
            f'<span class="stack-key{cls}"{attrs}>'
            f'<span class="stack-dot" style="background:var({color})"></span>'
            f"{_e(label)} <b>{c}</b></span>"
        )
    legend = "".join(legend_html)
    return (
        f'<div class="panel status-stack"><h2>{_e(title)}</h2>'
        f'<p class="muted">{_e(desc)}</p>'
        f'<div class="stack-bar" role="img" aria-label="{_e(title)}">{bar}</div>'
        f'<div class="stack-legend">{legend}</div>'
        f'<div class="stack-foot">{_e(foot)}</div></div>'
    )


def _export_bar(path: str, *, xlsx_id: str = "", docx_id: str = "") -> str:
    """The per-view 'download as Excel / Word' links (local files only — Law 1)."""
    a = f' id="{xlsx_id}"' if xlsx_id else ""
    b = f' id="{docx_id}"' if docx_id else ""
    return (
        f'<div class="export-bar"><a{a} href="/export/xlsx/{path}">&#11015; Excel</a>'
        f'<a{b} href="/export/docx/{path}">&#11015; Word</a></div>'
    )


def _latest_solvable(st: SessionState) -> tuple[str, Schedule, CPMResult] | None:
    """The newest analyzable version (key, scoped schedule, cpm), scoped to the session filter.

    The same selection ``/api/sra`` and ``POST /sra/risk`` share: iterate the loaded versions
    oldest-first, keep the last one whose CPM solves, and return its scoped schedule + CPM. Returns
    ``None`` when nothing loaded version is analyzable (the caller surfaces the empty state)."""
    chosen: tuple[str, Schedule, CPMResult] | None = None
    for key, raw in st.ordered_versions():
        try:
            analysis = st.analysis_for(key, raw)
        except CPMError:
            continue
        chosen = (key, analysis.scoped, analysis.cpm)
    return chosen


def _sra_selected(st: SessionState) -> tuple[str, Schedule, CPMResult] | None:
    """The schedule the SRA runs against — the operator's pick (``st.sra_file``) when it names a
    loaded, solvable version, otherwise the latest-solvable default. One resolver shared by the
    page, the simulation API, and the override POST so all three always agree on the file."""
    key = st.sra_file
    if key is not None and key in st.schedules:
        raw = st.schedules[key]
        try:
            analysis = st.analysis_for(key, raw)
        except CPMError:
            pass  # the chosen file no longer solves (e.g. filtered to nothing) -> fall back
        else:
            return (key, analysis.scoped, analysis.cpm)
    return _latest_solvable(st)


def _task_name_across(schedules: list[Schedule], uid: int) -> str | None:
    """The activity's name from the newest version that has it (None if no version does)."""
    for sch in reversed(schedules):
        task = sch.tasks_by_id.get(uid)
        if task is not None:
            return task.name
    return None


#: Evolution tier modes → the driving-slack tiers (ADR-0011) to include. "off" = the float
#: critical-path view (the page default, with its rich entered/left attribution).
_EVO_TIER_LABEL = {
    PathTier.DRIVING: "driving",
    PathTier.SECONDARY: "secondary",
    PathTier.TERTIARY: "tertiary",
}


# The margin-terminology glossary + its two handbook-citation constants descended here in
# the margin slice (ADR-0363): `web/margin.py` needs them (`_margin_dashboard_body`) and so
# does the /analysis margin panel still in `app.py` - and a symbol an extracted module needs
# must live at or below that module's layer (the ADR-0351 rule: the FIRST slice of a pair
# forces the descent). The sibling `_HB_CONSUME_SEC` stayed in `app.py`: nothing anywhere
# references it, so no closure claims it (adjacency is not cohesion, ADR-0349/0350).
_HB = "NASA Schedule Management Handbook"
_HB_MARGIN_SEC = "&sect;5.5.11, Establish and Allocate Margin"


def _margin_terminology() -> str:
    """A collapsed MARGIN vs CONTINGENCY vs FLOAT glossary, cited to the handbook — the three are
    routinely conflated and the distinction is load-bearing for the burn-down (F3a)."""
    return (
        "<details class=explain><summary>MARGIN vs CONTINGENCY vs FLOAT &mdash; what each term means"
        "</summary><div class=explain-body>"
        f"<h4>Schedule margin</h4><p>A <b>separately-planned, visible buffer activity</b> the planner "
        f"inserts before a committed milestone to absorb risk and uncertainty &mdash; it has a real "
        f"working-day duration in the schedule. The {_HB} ({_HB_MARGIN_SEC}) manages margin as an "
        f"explicit activity and &ldquo;places emphasis on identifying and managing schedule margin over "
        f"float.&rdquo;</p>"
        "<h4>Contingency</h4><p>Here, the schedule calendar&rsquo;s <b>non-working time</b> "
        "(weekends + holidays) between the status date and the target &mdash; unplanned cushion in the "
        "calendar, distinct from the work-day margin (no overlap).</p>"
        "<h4>Float (slack)</h4><p>A <b>computed</b> CPM quantity: how long an activity can slip without "
        "moving the finish. It is not planned buffer &mdash; the handbook manages margin <i>over</i> "
        "float, because margin that sits on a path with float protects nothing.</p>"
        "</div></details>"
    )


# The trend focus pair descended here in the trend slice (ADR-0364): `web/trend.py` needs
# `_focus_panel` (`_trend_body` embeds it) and so does the /compare route still in
# `app.py` - a symbol an extracted module needs must live at or below that module's layer
# (the ADR-0351 rule: the FIRST slice of a pair forces the descent). Both consumers are
# render-proven: /trend?target=<uid> and /compare with the session target set.
def _focus_rows(
    schedules: list[Schedule], cpms: list[CPMResult], target: int
) -> list[tuple[str, str, str]]:
    """Per version: (label, the focus UID's computed finish date, % complete) — '—' if absent."""
    rows: list[tuple[str, str, str]] = []
    for sch, cpm in zip(schedules, cpms, strict=True):
        label = sch.source_file or sch.name
        timing = cpm.timings.get(target)
        task = sch.tasks_by_id.get(target)
        if timing is None or task is None:
            rows.append((label, "—", "—"))
            continue
        finish = offset_to_datetime(sch.project_start, timing.early_finish, sch.calendar)
        rows.append((label, finish.date().isoformat(), f"{task.percent_complete:g}%"))
    return rows


def _focus_panel(schedules: list[Schedule], cpms: list[CPMResult], target: int) -> str:
    names = [s.tasks_by_id[target].name for s in schedules if target in s.tasks_by_id]
    title = f"Focus activity UID {target}" + (f" &mdash; {_e(names[0])}" if names else "")
    focus_rows = _focus_rows(schedules, cpms, target)
    rows = "".join(
        # focus_rows keeps ISO (the movement math below parses it); format at render only
        f"<tr><td>{_e(label)}</td><td>{_e(_mdY(finish))}</td><td>{_e(pct)}</td></tr>"
        for label, finish, pct in focus_rows
    )
    note = "" if names else '<p class="notice err">No loaded version contains that UniqueID.</p>'
    known = [(label, finish) for label, finish, _ in focus_rows if finish != "—"]
    movement = ""
    if len(known) >= 2:
        # same sign convention as Net Finish Impact: negative == moved later (a slip).
        # Mission Ops rank 5: the movement statement is a CITATION CARD (.finding.cite-card
        # vocabulary) — the sentence is unchanged; the cite line names the UID and the exact
        # versions/dates the figure was read between (presentation only, no new math).
        days = (dt.date.fromisoformat(known[0][1]) - dt.date.fromisoformat(known[-1][1])).days
        cls, word = ("fail", "later") if days < 0 else ("pass", "earlier or unchanged")
        sev = "MEDIUM" if days < 0 else "INFO"
        movement = (
            f'<div class="finding cite-card sev-{sev}">'
            f"<p>Computed finish moved <b class={cls}>{days:+d} calendar days</b> "
            f"({word}) between the first and last version that schedule it.</p>"
            f"<p class=cite data-no-i18n>UID {target} · {_e(known[0][0])} "
            f"({_e(_mdY(known[0][1]))}) → {_e(known[-1][0])} ({_e(_mdY(known[-1][1]))})</p></div>"
        )
    # panel contract (rank 5): headline strip + ⛶ (no endpoint serves these focus rows — no
    # dead ⤓; the table is its own drawer — no ▦ DATA) + the first→last pair provenance chip.
    head = _panel_head(
        title,
        tools=_shell_tools(),
        prov=_pair_prov_chip(schedules[0], schedules[-1], 1, len(schedules)),
    )
    return f"""
<div class=panel>{head}{note}
<p class=muted>The focus activity's computed finish and progress across the versions
(its movement is charted below).</p>
<table><tr><th scope=col>Version</th><th scope=col>Computed finish</th><th scope=col>% complete</th></tr>{rows}</table>
{movement}</div>"""


# ---- descended in ADR-0365 (phase 3, slice 7): 2-family names the ssi cut forced down ----
# `_REMAIN_DAYS_DP` / `_affected_avg_remaining_days`: `_apply_ssi_setup` moved to ``web/ssi.py``
# while `_unified_risk_section` / `_import_risk_register` stay in ``app.py`` (sra family);
# `_ssi_matrix_counts`: `_ssi_data` moved while `_sra_matrix_chart` / `_ssi_export_tables` stay.
# A symbol an extracted module needs must live at or below that module's layer (ADR-0351).

#: Decimal places for the per-task remaining-days values shared with the client SRA derive math
#: (``window.SF_REMAIN_DAYS``). The server and client MUST round each per-task value at the SAME
#: precision before averaging, or their derived days↔% magnitudes diverge for sub-day tasks
#: (audit M5). 6 dp keeps sub-day tasks from collapsing to 0 while still matching exactly.
_REMAIN_DAYS_DP = 6


def _affected_avg_remaining_days(sch: Schedule | None, uids: Sequence[int]) -> float:
    """Average REMAINING duration (working days) of the affected leaf tasks — the basis the days↔%
    auto-derive uses so the additive and multiplicative magnitudes produce the same TOTAL schedule
    impact across the affected set. 0.0 when nothing is known (then no derivation is possible)."""
    if sch is None:
        return 0.0
    mpd = sch.calendar.working_minutes_per_day or 480
    rems: list[float] = []
    for u in uids:
        t = sch.tasks_by_id.get(u)
        if t is not None and not t.is_summary:
            rem = (
                t.remaining_duration_minutes
                if t.remaining_duration_minutes is not None
                else t.duration_minutes
            )
            # round each per-task value at the SAME precision the client receives in
            # SF_REMAIN_DAYS so the two averages match exactly for sub-day tasks (audit M5)
            rems.append(round(rem / mpd, _REMAIN_DAYS_DP))
    return sum(rems) / len(rems) if rems else 0.0


def _ssi_matrix_counts(risks: Sequence[SSIRiskStat], *, opportunity: bool) -> list[list[int]]:
    """A 5x5 ``[consequence-1][probability-1]`` count grid for the risks (impact >= 0) or the
    opportunities (impact < 0) — the operator's Risk / Opportunity Assessment Matrix."""
    grid = [[0] * 5 for _ in range(5)]
    for r in risks:
        if (r.impact_days < 0) == opportunity:
            # clamp defensively: a hand-edited / third-party setup.json can carry a rating outside
            # 1..5 (the form route clamps, the load route did too after the fix below) and must never
            # IndexError or silently mis-bin a forensic export
            c = min(5, max(1, r.consequence_rating))
            p = min(5, max(1, r.probability_rating))
            grid[c - 1][p - 1] += 1
    return grid


# ---- descended in ADR-0373 (phase 3, slice 9): 2-family names the sra cut forced down ----
# `_TS_CAPTION_MARK`: `_sra_body` moved to ``web/sra.py`` while the /path, /driving-path and
# /evolution routes (create_app) also serve the marker - four hosting pages, one honest label
# (the ADR-0326 rationale rides in the #: block below, verbatim).
# `_schedule_risks`: `_ssi_export_tables` moved while `_margin_risk_data` and five /api
# routes (create_app) still derive the same ScheduleRisks from the session register.
#: The B1 timescale-caption marker (ADR-0326): a page that serves this names its time axis, and
#: gantt.js's shared buildTierScale renders ONE caption row above the tiers on every timescale
#: header the page builds (initial draw, Timescale-dialog repaints, animation frames alike).
#: All four Gantt-family consumers (path.js, path_evolution.js, driving_path.js, sra_grid.js)
#: draw calendar-date tiers, so one honest label serves them all. Hidden: the visible caption is
#: the slot the JS builds; this span only carries the text to it.
_TS_CAPTION_MARK = '<span data-ts-caption="Schedule dates" hidden></span>'


def _schedule_risks(st: SessionState) -> tuple[ScheduleRisk, ...]:
    """The SSI days-impact ScheduleRisks derived from the unified register (a fired impact
    REPLACES the affected task's remaining duration — ADR-0359)."""
    return tuple(
        ScheduleRisk(
            id=r.id,
            name=r.name,
            probability=r.probability,
            impact_days=r.impact_days,
            affected=r.affected,
            consequence_rating=r.consequence_rating,
        )
        for r in st.sra_risks
    )


# ---- descended in ADR-0376 (phase 3, slice 12): a 3-family name the analysis cut sent down ----
# `_target_panel`: `_analysis_body` moved to `web/analysis.py` while the /card and /wbs routes
# (create_app closures in `web/app.py`) render the same session-target panel — three families,
# the ADR-0350 components threshold. Verbatim, byte-identical to the app.py original.


def _target_panel(sch: Schedule, analysis: _Analysis, target: int) -> str:
    """The session target activity's metrics in THIS schedule (or a gentle absence note).

    Panel contract (codex-review round, ADR-0327 addendum): the populated panel wears the
    head strip + ⛶ ENLARGE + this file's provenance chip on all three render sites
    (/analysis, /card/{name}, /wbs/{name} — all of which load panelkit.js). The original
    ADR-0327 text claimed this helper already rendered the head strip — that was a MISREAD
    of the /path workspace head, caught by external review and corrected here. ⤓ EXCEL is
    deliberately refused: this is a single-activity view, and no export sheet carries its
    variance/flag cells as drawn (the analysis workbook's activities sheet is the whole
    population with different columns) — the round's covers-what-it-draws bar. The
    absent-UID branch is a NOTICE and stays bare."""
    row = next((r for r in analysis.activity_rows if r["unique_id"] == target), None)
    if row is None:
        return (
            f"<div class=panel><h2>Target activity UID {target}</h2>"
            f'<p class="notice err">This schedule does not contain UniqueID {target}.</p></div>'
        )
    variance = ""
    if row["finish"] and row["baseline_finish"]:
        days = (
            dt.date.fromisoformat(str(row["finish"]))
            - dt.date.fromisoformat(str(row["baseline_finish"]))
        ).days
        cls = "fail" if days > 0 else "pass"
        variance = (
            f"<tr><th scope=col>Finish vs baseline</th>"
            f"<td><b class={cls}>{days:+d} calendar days</b></td></tr>"
        )
    flags = ", ".join(
        label
        for label, on in (
            ("critical", row["is_critical"]),
            ("milestone", row["is_milestone"]),
            ("summary", row["is_summary"]),
        )
        if on
    )
    cells = "".join(
        f"<tr><th scope=col>{label}</th><td>{_e(value)}</td></tr>"
        for label, value in (
            ("Start", row["start"] or "—"),
            ("Finish", row["finish"] or "—"),
            ("Baseline finish", row["baseline_finish"] or "—"),
            (
                "Total float (days)",
                row["total_float_days"] if row["total_float_days"] is not None else "—",
            ),
            (
                "Free float (days)",
                row["free_float_days"] if row["free_float_days"] is not None else "—",
            ),
            ("% complete", row["percent_complete"]),
            ("Flags", flags or "—"),
        )
    )
    head = _panel_head(
        f"Target activity &mdash; UID {target}: {_e(row['name'])}",
        tools=_shell_tools(),
        prov=_prov_chip(sch),
    )
    return f"""
<div class=panel>{head}
<p class=muted>The session-wide target: the trace below runs to it automatically, the Trend page
focuses on it, and Compare shows its movement. Set or clear it in the header.</p>
<table>{cells}{variance}</table>
<p class=cite>{_e(row["name"])} (UID {target}, {_e(row["source_file"] or "schedule")})</p></div>"""


def _metric_scorecard_table(results: dict[str, MetricResult]) -> str:
    """A compact check/value/status table from a DCMA-14 result dict (over any (sub)schedule)."""
    rows = []
    for m in results.values():
        if m.unit == "ratio":  # CPLI / BEI — an index
            valcell = f"{round(m.value, 2)}"
        elif m.population:
            pct = m.value if m.unit == "%" else 100.0 * m.count / m.population
            valcell = f"{m.count} <span class=muted>of {m.population}</span> ({pct:.1f}%)"
        else:
            valcell = str(m.count)
        rows.append(
            f"<tr><td>{_e(m.name)}</td><td class=num>{valcell}</td>"
            f'<td class="{_status_class(m.status)}">{_e(m.status)}</td></tr>'
        )
    return (
        "<table class=card-table><tr><th scope=col>Check</th><th scope=col>Value</th>"
        f"<th scope=col>Status</th></tr>{''.join(rows)}</table>"
    )
