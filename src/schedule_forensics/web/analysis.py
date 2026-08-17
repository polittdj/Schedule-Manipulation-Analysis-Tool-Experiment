"""The /analysis page family: the per-schedule forensic report, chapter 01 "Where we stand".

Monolith split, phase 3 slice 12 (ADR-0376), extracted VERBATIM from ``web/app.py``: every
function, docstring and comment moves byte-for-byte, only the module boundary changes.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour (the
``/analysis/{name}`` and ``/api/analysis/{name}`` routes): 25 names in nine regions - the report
body and its chapter-01 "Where we stand" header, the DCMA table cell / JSON-card builders, the
findings citation cell, the JSON dataset, and the per-schedule panels the body composes (float
bands, completion, structural health, schedule variance, float erosion, constraint health,
vertical integration, logic integrity, margin, scatter, float histogram, calendar, stoplight
board). Every mover's external referrers are the family's routes - ``create_app`` closures,
which import downward and stay put. One descent rides the same slice: ``_target_panel`` (three
families: ``_analysis_body`` plus the /card and /wbs routes) drops to ``web/components.py``
under the ADR-0350 3+-family threshold. The export route (``/export/{fmt}/analysis/{name}``)
contributes no movers - engine tables + the shared export machinery, the mission shape.

Layering: ``app`` -> ``analysis`` -> ``components`` -> ``chrome`` -> ``state`` ->
engine/ai/model. Nothing here imports ``web.app``.
"""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import quote

from schedule_forensics.ai.citations import Narrative
from schedule_forensics.engine.cpm import CPMResult, off_project_calendars, offset_to_datetime
from schedule_forensics.engine.dcma_audit import AuditCheck
from schedule_forensics.engine.forecast import compute_finish_forecasts
from schedule_forensics.engine.metrics import compute_activity_makeup
from schedule_forensics.engine.metrics._common import (
    effective_total_float,
    is_effective_critical,
    non_summary,
    percent,
)
from schedule_forensics.engine.metrics.constraint_health import compute_constraint_health
from schedule_forensics.engine.metrics.evm import ActivityVariance, compute_schedule_variance
from schedule_forensics.engine.metrics.float_erosion import compute_float_erosion
from schedule_forensics.engine.metrics.health_extra import compute_health_checks
from schedule_forensics.engine.metrics.logic_integrity import compute_logic_integrity
from schedule_forensics.engine.metrics.margin import (
    MarginCandidate,
    compute_margin,
    margin_candidates,
)
from schedule_forensics.engine.metrics.vertical_integration import compute_vertical_integration
from schedule_forensics.engine.recommendations import Finding
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.chrome import _e, _expandable_more
from schedule_forensics.web.components import (
    _ANALYSIS_XLSX_TITLE,
    _HB,
    _HB_MARGIN_SEC,
    _analysis_export_attr,
    _export_bar,
    _margin_terminology,
    _mdY,
    _metric_help_cell,
    _panel_head,
    _prov_chip,
    _shell_tools,
    _stat_cards,
    _status_class,
    _status_stack,
    _target_panel,
    _user_tip,
)
from schedule_forensics.web.help import METRIC_DICTIONARY
from schedule_forensics.web.state import _Analysis


def _stoplight_board(checks: tuple[AuditCheck, ...]) -> str:
    """The handbook's canonical at-a-glance metric stoplight (Figs 7-10..7-38): one chip per DCMA-14
    check, green PASS / red FAIL / grey N/A, with the value + threshold. Pure presentation over the
    existing ``AuditCheck.status`` — adds no new threshold or number."""
    if not checks:
        return ""
    chips = []
    for c in checks:
        cls = _status_class(c.status)
        thr = "" if c.threshold is None else f" (≤ {c.threshold:g}{_e(c.unit)})"
        title = f"{c.name}: {c.value:g}{c.unit} vs threshold{thr or ' n/a'} — {c.status}"
        chips.append(
            f'<span class="sl-chip sl-{cls}" title="{_e(title)}">'
            f"<span class=sl-name>{_e(c.name)}</span> "
            f"<b>{c.value:g}{_e(c.unit)}</b></span>"
        )
    legend = (
        '<div class=sl-legend><span class="sl-key sl-pass">pass</span>'
        '<span class="sl-key sl-fail">fail</span>'
        '<span class="sl-key sl-na">n/a</span></div>'
    )
    return f'<div class=stoplight-board role=list aria-label="DCMA-14 stoplight">{"".join(chips)}</div>{legend}'


def _float_bands_panel(analysis: _Analysis, *, key: str = "", prov: str = "") -> str:
    """The deck-style low-float bands (M15/ADR-0030): to-go work running out of room."""
    fb = analysis.float_bands

    def cell(mid: str) -> str:
        r = fb[mid]
        return f"<td>{r.count} <span class=muted>({r.value:g}%)</span></td>"

    pop = fb["float_total_0"].population
    z, lt5 = fb["float_total_0"], fb["float_total_lt5"]
    tools = _shell_tools(export_title=_ANALYSIS_XLSX_TITLE if key else "")
    head = _panel_head("Float analysis &mdash; low-float bands", tools=tools, prov=prov)
    take = (
        f"<p class=sf-take data-no-i18n>{z.count} of {pop} incomplete activities sit at 0 days "
        f"of total float; {lt5.count} sit under 5 working days.</p>"
    )
    return f"""
<div class=panel{_analysis_export_attr(key)}>{head}{take}
<p class=muted>Of the {pop} incomplete activities, how many are running out of room: at 0 days
of float (critical or negative), under 5, and under 10 working days &mdash; cumulative bands on
this schedule's calendar. A swelling low-float band is the early warning that the schedule is
losing its ability to absorb slips.</p>
<table><tr><th scope=col></th><th scope=col>0 days</th><th scope=col>&lt; 5 days</th><th scope=col>&lt; 10 days</th></tr>
<tr><th scope=col class=metric-th>{_metric_help_cell("Total float", "total_float")}</th>{cell("float_total_0")}{cell("float_total_lt5")}{cell("float_total_lt10")}</tr>
<tr><th scope=col class=metric-th>{_metric_help_cell("Free float", "free_float")}</th>{cell("float_free_0")}{cell("float_free_lt5")}{cell("float_free_lt10")}</tr>
</table></div>"""


def _completion_panel(analysis: _Analysis, *, key: str = "", prov: str = "") -> str:
    """The deck-style completion-performance read-out (M15/ADR-0030)."""
    cp = analysis.completion

    def fmt(mid: str) -> str:
        r = cp[mid]
        if r.unit == "%":
            return f"{r.count} of {r.population} ({r.value:g}%)" if r.population else "—"
        if r.unit == "days":
            return f"{r.value:g} days (over {r.count})" if r.count else "—"
        return f"{r.value:g}" if r.population else "—"

    rows = "".join(
        f"<tr><th scope=col class=metric-th>{_metric_help_cell(label, mid)}</th>"
        f"<td>{fmt(mid)}</td></tr>"
        for mid, label in (
            ("completed_ahead", "Completed ahead of baseline"),
            ("completed_on_schedule", "Completed on schedule"),
            ("completed_behind", "Completed behind baseline"),
            ("avg_days_ahead", "Average days ahead (early finishers)"),
            ("avg_days_late", "Average days late (late finishers)"),
            ("avg_completion_variance", "Average completion variance (+ = late)"),
            ("longer_than_planned", "Activities longer than planned"),
            ("shorter_than_planned", "Activities shorter than baseline"),
            ("duration_ratio_min", "Duration ratio (actual / baseline) — min"),
            ("duration_ratio_avg", "Duration ratio — average"),
            ("duration_ratio_max", "Duration ratio — max"),
            ("mei", "MEI (milestones finished / milestones due)"),
            ("epi", "EPI (execution events recorded / events expected)"),
            ("start_finish_ratio", "Start-to-Finish Ratio (scheduled pairs / actual pairs)"),
            ("elapsed_since_last_finish", "Schedule elapsed since latest actual finish"),
        )
    )
    ahead, on_sched, behind = (
        cp["completed_ahead"],
        cp["completed_on_schedule"],
        cp["completed_behind"],
    )
    tools = _shell_tools(export_title=_ANALYSIS_XLSX_TITLE if key else "")
    head = _panel_head("Completion performance", tools=tools, prov=prov)
    take = (
        f"<p class=sf-take data-no-i18n>Completed work: {ahead.count} finished ahead of baseline "
        f"&middot; {on_sched.count} on schedule &middot; {behind.count} behind.</p>"
    )
    return f"""
<div class=panel{_analysis_export_attr(key)}>{head}{take}
<p class=muted>How the completed work actually performed against its baseline: the
ahead / on-schedule / behind split, the days gained and lost, and actual-vs-baseline
durations. Day variances are calendar days.</p>
<table>{rows}</table></div>"""


_WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _health_checks_panel(sch: Schedule, cpm: CPMResult, *, prov: str = "") -> str:
    """Extra structural health checks (handbook Fig. 6-9) as a stoplight list — green when clear,
    else the count + the first offending UIDs, with a plain-English reason for each."""
    checks = compute_health_checks(sch, cpm).checks
    cards = []
    for c in checks:
        ok = c.count == 0
        badge_cls = "rk-min" if ok else "rk-high"
        badge = "✓ clear" if ok else str(c.count)
        offs = ""
        if c.offenders:
            shown = ", ".join(f"UID {u}" for u in c.offenders[:8])
            hidden = [_e(f"UID {u}") for u in c.offenders[8:]]
            if c.count > len(c.offenders):
                hidden.append(f"&hellip; and {c.count - len(c.offenders)} beyond the citation cap")
            offs = f"<p class=cite>{_expandable_more(_e(shown), hidden)}</p>"
        cards.append(
            f'<div class="finding cite-card sev-{"INFO" if ok else "MEDIUM"}">'
            f'<div class=finding-head><span class="rk-score {badge_cls}">{badge}</span> '
            f"<b>{_e(c.label)}</b></div><p>{_e(c.description)}</p>{offs}</div>"
        )
    flagged = sum(1 for c in checks if c.count)
    take = (
        f"<p class=sf-take data-no-i18n>{flagged} of {len(checks)} structural checks flag "
        "activities.</p>"
        if flagged
        else f"<p class=sf-take data-no-i18n>All {len(checks)} structural checks are clear.</p>"
    )
    return (
        "<div class=panel>"
        + _panel_head("Structural health checks", tools=_shell_tools(), prov=prov)
        + take
        + "<p class=muted>Deterministic schedule-construction checks from the NASA Schedule "
        "Management Handbook (Fig. 6-9), beyond DCMA-14 &mdash; green = clear, otherwise the count "
        "and the first offending activities (the activity grid above is the full record).</p>"
        + "".join(cards)
        + "</div>"
    )


def _schedule_variance_panel(sch: Schedule, *, prov: str = "") -> str:
    """Schedule variance in TIME (handbook §7.3.3.1): project SVt = ES - AT (working days), plus the
    per-activity finish slip (actual - baseline). Favorable when ahead of plan (SVt >= 0)."""
    sv = compute_schedule_variance(sch, non_summary(sch))
    if sv.svt_days is None and sv.completed == 0 and sv.started == 0:
        # Distinguish a baselined-but-un-statused plan (has baselines, no actuals) from a file
        # with no baseline at all — the operator's Hard_File pair is exactly the former for the
        # first version, and the message should point them at the statused version.
        if sv.baselined > 0:
            hint = (
                f"This is the <b>baselined plan</b> ({sv.baselined} activities carry a baseline) "
                "with <b>no progress statused yet</b> &mdash; there are no actual start/finish "
                "dates to measure against it. Open the <b>statused version</b> of this schedule "
                "(the later data date, with actuals recorded) to see the schedule variance."
            )
        else:
            hint = (
                "This schedule carries no baseline dates, so there is no plan to measure progress "
                "against. Baseline the schedule in the source tool, then status it with progress."
            )
        return (
            "<div class=panel>"
            + _panel_head("Schedule variance (time)", tools=_shell_tools(), prov=prov)
            + "<p class=sf-take data-no-i18n>Schedule variance is not computable on this file "
            "&mdash; no actual start/finish dates are recorded yet.</p>"
            f"<p class=muted>Not computable on this file &mdash; {hint}</p></div>"
        )
    if sv.svt_days is None:
        svt_val = "n/a"
    else:
        favorable = sv.svt_days >= 0
        sign = "+" if sv.svt_days > 0 else ""
        # SVt > 0 = ES ahead of AT = ahead of plan (favorable); < 0 = behind (unfavorable)
        svt_val = f"{sign}{sv.svt_days:g} wd ({'ahead' if favorable else 'behind'})"
    cards = _stat_cards(
        [
            ("Schedule variance (SVt = ES - AT)", svt_val),
            ("Earned Schedule (ES)", "n/a" if sv.es_days is None else f"{sv.es_days:g} wd"),
            ("Actual Time (AT)", "n/a" if sv.at_days is None else f"{sv.at_days:g} wd"),
            ("Completed (finish variance)", str(sv.completed)),
            (
                "Mean finish variance",
                "n/a"
                if sv.mean_activity_variance_days is None
                else f"{sv.mean_activity_variance_days:+g} wd",
            ),
            ("Started (start variance)", str(sv.started)),
            (
                "Mean start variance",
                "n/a"
                if sv.mean_start_variance_days is None
                else f"{sv.mean_start_variance_days:+g} wd",
            ),
        ]
    )
    names = sch.tasks_by_id

    def _var_table(title: str, rows_data: tuple[ActivityVariance, ...], kind: str) -> str:
        if not rows_data:
            return ""
        rows = "".join(
            f"<tr><td>{v.unique_id}</td>"
            f"<td>{_e(names[v.unique_id].name) if v.unique_id in names else ''}</td>"
            f'<td class="rk-score {"rk-high" if v.variance_days > 0 else "rk-min"}">'
            f"{v.variance_days:+g}</td></tr>"
            for v in rows_data
        )
        return (
            f"<h3>{title}</h3>"
            "<table><tr><th scope=col>UID</th><th scope=col>Activity</th>"
            f"<th scope=col>{kind} variance (wd)</th></tr>{rows}</table>"
        )

    table = _var_table("Largest finish variances (actual &minus; baseline)", sv.worst, "Finish")
    table += _var_table(
        "Largest start variances (actual &minus; baseline)", sv.worst_start, "Start"
    )
    take = (
        f"<p class=sf-take data-no-i18n>Schedule variance SVt reads {_e(svt_val)} &mdash; "
        f"{sv.completed} completed activities carry a finish variance.</p>"
    )
    return (
        "<div class=panel>"
        + _panel_head("Schedule variance (time)", tools=_shell_tools(), prov=prov)
        + take
        + "<p class=muted>The NASA Schedule Management Handbook (&sect;7.3.3.1) time view of progress. "
        "<b>SVt = ES &minus; AT</b> (Earned Schedule minus Actual Time): positive is "
        "<b>ahead</b> of plan (favorable), negative is <b>behind</b> (unfavorable) &mdash; the "
        "count-based Earned-Schedule companion to SPI(t). Per-activity <b>finish</b> variance is a "
        "completed activity's actual finish minus its baseline finish; <b>start</b> variance is a "
        "started activity's actual start minus its baseline start (in working days, positive = "
        "late) &mdash; the latter surfaces in-progress slippage before tasks complete.</p>"
        f"{cards}{table}</div>"
    )


#: float-erosion stoplight → the shared 5-level risk badge classes (green / amber / red)
_EROSION_BADGE = {"green": "rk-min", "yellow": "rk-mod", "red": "rk-extreme"}


def _float_erosion_panel(
    sch: Schedule, cpm: CPMResult, wbs_field: str | None = None, *, prov: str = ""
) -> str:
    """Float erosion by WBS (handbook Figs 7-34/7-35): per-top-level-WBS minimum / average total
    float, critical count, and a stoplight on the group's minimum float — where buffer is thinning.

    ``wbs_field`` (ADR-0150): the operator-chosen grouping field — any custom field (e.g. a
    "CA-WBS" outline code) or the built-in WBS — selected via the panel's own form."""
    from schedule_forensics.engine.grouping import available_fields

    field = wbs_field if wbs_field else "WBS"
    fe = compute_float_erosion(sch, cpm, wbs_field=field)
    options = "".join(
        f'<option value="{_e(f)}"{" selected" if f == field else ""}>{_e(f)}</option>'
        for f in ["WBS", *sorted(x for x in available_fields(sch) if x != "WBS")]
    )
    picker = (
        '<form method=get class=viz-controls style="margin:.3em 0">'
        "<label>Group by field: "
        f"<select name=erosion_field data-no-i18n data-sf-autosubmit>{options}"
        "</select></label> "
        "<span class=muted>use a custom field (e.g. an outline code) if your WBS lives there</span>"
        "</form>"
    )
    if not fe.groups:
        return (
            "<div class=panel>"
            + _panel_head("Float erosion by WBS", tools=_shell_tools(), prov=prov)
            + picker
            + "<p class=muted>No schedulable activities to group.</p></div>"
        )
    thr = f"{fe.low_float_threshold_days:g}"
    rows = []
    for g in fe.groups:
        badge = _EROSION_BADGE.get(g.status, "rk-min")
        rows.append(
            f"<tr><td>{_e(g.wbs)}</td><td>{g.count}</td>"
            f'<td class="rk-score {badge}">{g.min_float_days:g}</td>'
            f"<td>{g.avg_float_days:g}</td><td>{g.critical_count}</td></tr>"
        )
    proj_min = "n/a" if fe.min_float_days is None else f"{fe.min_float_days:g} wd"
    cards = _stat_cards(
        [
            ("Lowest total float (any WBS)", proj_min),
            ("WBS groups", str(len(fe.groups))),
            ("Eroded groups (min float < 0)", str(sum(1 for g in fe.groups if g.status == "red"))),
        ]
    )
    eroded = sum(1 for g in fe.groups if g.status == "red")
    take = (
        f"<p class=sf-take data-no-i18n>Lowest total float across {len(fe.groups)} groups: "
        f"{proj_min} &mdash; {eroded} group(s) eroded (min float below 0).</p>"
    )
    return (
        "<div class=panel>"
        + _panel_head("Float erosion by WBS", tools=_shell_tools(), prov=prov)
        + take
        + picker
        + f"<p class=muted>Grouping field: <b>{_e(field)}</b> (top-level dotted segment). "
        "Total float grouped by top-level WBS (NASA Schedule Management Handbook) "
        "&mdash; where buffer is thinning before the project-level margin is hit. The stoplight is on "
        f"each group's <b>minimum</b> total float: <b>red</b> below 0 (eroded / behind a constraint), "
        f"<b>amber</b> 0&ndash;{thr} working days (thin buffer), <b>green</b> above {thr}. Float is "
        "read progress-aware (the source tool's stored Total Slack when present).</p>"
        f"{cards}"
        "<table><tr><th scope=col>WBS</th><th scope=col>Activities</th>"
        "<th scope=col>Min float (wd)</th><th scope=col>Avg float (wd)</th>"
        "<th scope=col>Critical</th></tr>"
        f"{''.join(rows)}</table></div>"
    )


def _constraint_checks_panel(sch: Schedule, cpm: CPMResult, *, prov: str = "") -> str:
    """Constraint-health checks (handbook Fig. 6-9): unsatisfied hard date constraints and breached
    deadlines, as a stoplight list — green when clear, else the count + the first offending UIDs."""
    checks = compute_constraint_health(sch, cpm).checks
    cards = []
    for c in checks:
        ok = c.count == 0
        badge_cls = "rk-min" if ok else "rk-high"
        badge = "✓ clear" if ok else str(c.count)
        offs = ""
        if c.offenders:
            shown = ", ".join(f"UID {u}" for u in c.offenders[:8])
            hidden = [_e(f"UID {u}") for u in c.offenders[8:]]
            if c.count > len(c.offenders):
                hidden.append(f"&hellip; and {c.count - len(c.offenders)} beyond the citation cap")
            offs = f"<p class=cite>{_expandable_more(_e(shown), hidden)}</p>"
        pop = f"<span class=muted> of {c.population}</span>" if c.population else ""
        cards.append(
            f'<div class="finding cite-card sev-{"INFO" if ok else "MEDIUM"}">'
            f'<div class=finding-head><span class="rk-score {badge_cls}">{badge}</span> '
            f"<b>{_e(c.label)}</b>{pop}</div><p>{_e(c.description)}</p>{offs}</div>"
        )
    flagged = sum(1 for c in checks if c.count)
    take = (
        f"<p class=sf-take data-no-i18n>{flagged} of {len(checks)} constraint checks flag "
        "activities.</p>"
        if flagged
        else f"<p class=sf-take data-no-i18n>All {len(checks)} constraint checks are clear.</p>"
    )
    return (
        "<div class=panel>"
        + _panel_head("Constraint health", tools=_shell_tools(), prov=prov)
        + take
        + "<p class=muted>How imposed dates fare against the network logic (NASA Schedule Management "
        "Handbook, Fig. 6-9): a <b>hard constraint</b> the CPM date runs past cannot be honored, and "
        "a <b>deadline</b> the logic finish overruns is artificial negative float. Green = clear, "
        "otherwise the count and the first offending activities.</p>" + "".join(cards) + "</div>"
    )


def _vertical_integration_panel(sch: Schedule, *, prov: str = "") -> str:
    """Vertical-integration check (handbook Fig. 6-9): summaries whose stored span does not envelope
    the work beneath them — a stoplight finding card, green when clear else the offending summaries."""
    vi = compute_vertical_integration(sch)
    ok = vi.count == 0
    badge_cls = "rk-min" if ok else "rk-high"
    badge = "✓ clear" if ok else str(vi.count)
    offs = ""
    if vi.offenders:
        shown = ", ".join(f"UID {u}" for u in vi.offenders[:8])
        hidden = [_e(f"UID {u}") for u in vi.offenders[8:]]
        if vi.count > len(vi.offenders):
            hidden.append(f"&hellip; and {vi.count - len(vi.offenders)} beyond the citation cap")
        offs = f"<p class=cite>{_expandable_more(_e(shown), hidden)}</p>"
    pop = f"<span class=muted> of {vi.population} summary group(s)</span>" if vi.population else ""
    note = (
        ""
        if vi.population
        else "<p class=muted>No summaries with a WBS code, stored dates, and dated descendants "
        "to evaluate.</p>"
    )
    take = (
        f"<p class=sf-take data-no-i18n>{vi.count} of {vi.population} summary group(s) roll up "
        "inconsistently.</p>"
        if vi.population
        else "<p class=sf-take data-no-i18n>No summary groups with dated descendants to "
        "evaluate.</p>"
    )
    return (
        "<div class=panel>"
        + _panel_head("Vertical integration", tools=_shell_tools(), prov=prov)
        + take
        + "<p class=muted>Whether each summary (rollup) bar envelopes the detail activities beneath it "
        "(by WBS nesting), using the schedule's stored dates &mdash; the handbook's vertical-"
        "traceability check. A parent that starts after its earliest child or finishes before its "
        "latest is an inconsistent rollup.</p>"
        f'<div class="finding cite-card sev-{"INFO" if ok else "MEDIUM"}">'
        f'<div class=finding-head><span class="rk-score {badge_cls}">{badge}</span> '
        f"<b>Inconsistent vertical integration</b>{pop}</div>"
        f"<p>{_e(vi.description)}</p>{offs}</div>{note}</div>"
    )


def _logic_checks_panel(sch: Schedule, *, prov: str = "") -> str:
    """Logic-integrity checks (out-of-sequence progress, redundant logic) as a stoplight list —
    green when clear, else the count + the first offending links, with a plain-English reason."""
    checks = compute_logic_integrity(sch).checks
    cards = []
    for c in checks:
        if not c.evaluated:
            cards.append(
                '<div class="finding cite-card sev-INFO">'
                '<div class=finding-head><span class="rk-score rk-min">n/a</span> '
                f"<b>{_e(c.label)}</b></div><p>{_e(c.description)}</p></div>"
            )
            continue
        ok = c.count == 0
        badge_cls = "rk-min" if ok else "rk-high"
        badge = "✓ clear" if ok else str(c.count)
        offs = ""
        if c.offenders:
            shown = ", ".join(c.offenders[:8])
            hidden = [_e(o) for o in c.offenders[8:]]
            if c.count > len(c.offenders):
                hidden.append(f"&hellip; and {c.count - len(c.offenders)} beyond the citation cap")
            offs = f"<p class=cite>{_expandable_more(_e(shown), hidden)}</p>"
        pop = (
            f"<span class=muted> of {c.population} {_e(c.population_unit)}</span>"
            if c.population
            else ""
        )
        cards.append(
            f'<div class="finding cite-card sev-{"INFO" if ok else "MEDIUM"}">'
            f'<div class=finding-head><span class="rk-score {badge_cls}">{badge}</span> '
            f"<b>{_e(c.label)}</b>{pop}</div><p>{_e(c.description)}</p>{offs}</div>"
        )
    flagged = sum(1 for c in checks if c.evaluated and c.count)
    evaluated = sum(1 for c in checks if c.evaluated)
    take = (
        f"<p class=sf-take data-no-i18n>{flagged} of {evaluated} evaluated logic checks flag "
        "links.</p>"
        if flagged
        else f"<p class=sf-take data-no-i18n>All {evaluated} evaluated logic checks are clear.</p>"
    )
    return (
        "<div class=panel>"
        + _panel_head("Logic integrity", tools=_shell_tools(), prov=prov)
        + take
        + "<p class=muted>Forensic logic-construction checks from the NASA Schedule Management "
        "Handbook (Fig. 6-9) and the Acumen metric library, beyond DCMA-14 &mdash; "
        "<b>out-of-sequence</b> progress (work recorded in an order the logic forbids), "
        "<b>redundant logic</b> (a direct link a longer path already implies), and the "
        "<b>Open start / Open finish</b> dangling checks (an activity whose only links leave "
        "its start undriven or its finish driving nothing &mdash; invisible to a blank-"
        "Predecessor/Successor count). Green = clear, otherwise the count and the first "
        "offenders.</p>" + "".join(cards) + "</div>"
    )


def _margin_panel(
    key: str, sch: Schedule, cpm: CPMResult, confirmed: frozenset[int] | None, *, prov: str = ""
) -> str:
    """Schedule-margin panel: BOTH margin numbers, the MARGIN/CONTINGENCY/FLOAT glossary, and the
    operator's confirm/deny overlay of the margin-task set (name-based by default).

    ``confirmed`` is this version's operator-confirmed margin UniqueIDs (``None`` ⇒ the name-based
    default). The two numbers may differ: **total margin** sums the margin activities' durations;
    **effective margin** is how far the finish pulls in if all margin were removed — the buffer
    actually on the driving chain. Margin sitting on a path with float counts toward total but not
    effective (NASA Schedule Management Handbook)."""
    candidates = margin_candidates(sch, cpm)
    if not candidates:
        return (
            "<div class=panel>"
            + _panel_head("Schedule margin", tools=_shell_tools(), prov=prov)
            + "<p class=sf-take data-no-i18n>No schedule-margin activities found on this "
            "schedule.</p>"
            + _margin_terminology()
            + "<p class=muted>No schedule-margin activities found &mdash; no non-summary activity is "
            "named &ldquo;margin&rdquo; and none carries a handbook alias (reserve / contingency / "
            f"integrated return). Margin is identified by name ({_HB} {_HB_MARGIN_SEC}); rename a "
            "buffer activity to include &ldquo;margin&rdquo; (or confirm it here once it appears) so "
            "the burn-down can measure the reserve.</p></div>"
        )
    m = compute_margin(sch, cpm, margin_uids=confirmed)
    using = (
        "operator-confirmed set"
        if confirmed is not None
        else "name-based default (activities named &ldquo;margin&rdquo;)"
    )
    plural = "activities" if m.count != 1 else "activity"
    crit_note = (
        f"{m.on_critical_count} of {m.count} on the critical path"
        if m.on_critical_count
        else f"{m.count} margin {plural}; 0 on the critical path"
    )
    gap_note = (
        " Here the two <b>differ</b>: margin sitting on a path with float counts toward total but "
        "protects nothing, so effective is lower."
        if m.total_margin_days != m.effective_margin_days
        else " Here the two <b>agree</b>: all margin is on the driving chain."
    )
    cards = _stat_cards(
        [
            ("Total margin (sum of durations)", f"{m.total_margin_days:g} wd"),
            ("Effective margin (on driving chain)", f"{m.effective_margin_days:g} wd"),
            ("Margin activities", crit_note),
        ]
    )

    def _crow(c: MarginCandidate) -> str:
        checked = (c.unique_id in confirmed) if confirmed is not None else (c.tier == "primary")
        badge_cls = "rk-min" if c.tier == "primary" else "rk-high"
        return (
            "<tr>"
            f'<td><input type=checkbox name=uid value="{c.unique_id}"'
            f'{" checked" if checked else ""} aria-label="mark UID {c.unique_id} as schedule margin">'
            "</td>"
            f"<td>{c.unique_id}</td><td>{_e(c.name)}</td>"
            f'<td><span class="rk-score {badge_cls}">{c.tier}</span></td>'
            f"<td class=num>{c.duration_days:g}</td>"
            f"<td class=num>{c.total_float_days:g}</td>"
            f'<td class="rk-score {"rk-high" if c.on_critical else "rk-min"}">'
            f"{'Yes' if c.on_critical else 'No'}</td></tr>"
        )

    rows = "".join(_crow(c) for c in candidates)
    back = f"/analysis/{quote(key, safe='')}"
    form = (
        '<form method=post action="/margin/confirm">'
        f'<input type=hidden name=key value="{_e(key)}">'
        f'<input type=hidden name=back value="{_e(back)}">'
        "<table><tr><th scope=col>Margin?</th><th scope=col>UID</th><th scope=col>Name</th>"
        "<th scope=col>Match</th><th scope=col>Days</th><th scope=col>Total float (d)</th>"
        "<th scope=col>On critical path?</th></tr>"
        f"{rows}</table>"
        '<div class=row-actions style="margin-top:8px">'
        "<button type=submit name=action value=confirm>Confirm margin set</button> "
        "<button type=submit name=action value=reset class=btn-link "
        'title="Discard the confirmed set for this version and revert to the name-based default">'
        "Reset to name-based</button></div></form>"
    )
    take = (
        f"<p class=sf-take data-no-i18n>Total margin {m.total_margin_days:g} wd &middot; "
        f"effective margin {m.effective_margin_days:g} wd ({_e(crit_note)}).</p>"
    )
    return (
        "<div class=panel>"
        + _panel_head("Schedule margin", tools=_shell_tools(), prov=prov)
        + take
        + _margin_terminology()
        + "<p class=muted>Explicit buffer activities that protect the project finish. "
        "<b>Total margin</b> sums the margin activities&rsquo; durations; <b>effective margin</b> is "
        "how far the finish would pull in if all margin were removed &mdash; the buffer actually "
        "protecting the finish."
        + gap_note
        + f" ({_HB} {_HB_MARGIN_SEC}).</p>"
        + cards
        + f"<p class=muted>Currently measuring from the <b>{using}</b>. Tick the activities that ARE "
        "schedule margin and <b>Confirm</b> to pin the set for this version (near-miss aliases are "
        "listed but unticked until you confirm them); the burn-down and erosion trend then use your "
        "confirmed set across the project&rsquo;s versions. <b>Reset</b> reverts to the name-based "
        "default.</p>"
        + form
        # ADR-0254: the Fig 5-30 band + SRA sufficiency are inherently cross-version/time-series
        # views, so they live on the Margin Dashboard — this per-version panel links, not embeds.
        + '<p style="margin-top:10px"><a class=btn-link href="/margin">Compare against the '
        "Figure 5-30 guideline band + risk-based sufficiency on the Margin Dashboard &rarr;</a></p>"
        "</div>"
    )


def _scatter_panel(key: str, sch: Schedule, cpm: CPMResult, *, prov: str = "") -> str:
    """An activity scatter (total float x duration) on the analysis page, WITH the story
    (ADR-0150): a written health analysis naming the pressure points — long, low-float
    incomplete work — plus what the float distribution says about logic quality. Every figure
    is engine-computed here; the chart (scatter.js) is presentation over the same rows."""
    per_day = sch.calendar.working_minutes_per_day or 480
    incomplete: list[tuple[float, float, Task]] = []
    for task in non_summary(sch):
        if task.percent_complete >= 100.0:
            continue
        timing = cpm.timings.get(task.unique_id)
        recomputed = float(timing.total_float) if timing is not None else 0.0
        tf_days = effective_total_float(task, recomputed) / per_day
        dur_days = task.duration_minutes / (1440 if task.duration_is_elapsed else per_day)
        incomplete.append((tf_days, dur_days, task))
    n = len(incomplete)
    story: str
    pressure_rows = ""
    if n:
        critical = sum(1 for tf, _d, task in incomplete if tf <= 0)
        thin = sum(1 for tf, _d, _t in incomplete if 0 < tf <= 10)
        high = sum(1 for tf, _d, _t in incomplete if tf > 44)
        # pressure points: the longest incomplete activities inside the thin-float band
        pressure = sorted((x for x in incomplete if x[0] <= 10), key=lambda x: -x[1])[:5]
        med = sorted(tf for tf, _d, _t in incomplete)[n // 2]
        story = (
            f"<p><b>What this data says:</b> of the <b>{n}</b> incomplete activities, "
            f"<b>{critical}</b> ({percent(critical, n):.1f}%) have zero-or-negative float "
            f"(no room to slip), <b>{thin}</b> more sit within 10 working days of it, and "
            f"<b>{high}</b> ({percent(high, n):.1f}%) carry more than 44 wd of float "
            "&mdash; float that high usually means missing logic (DCMA-06), not genuine "
            f"slack. The median float is <b>{med:.0f} wd</b>. "
            + (
                "The schedule's ability to absorb a slip rests on how the low-float band "
                "is managed; the table below names the biggest pressure points &mdash; the "
                "longest tasks with the least room."
                if (critical + thin)
                else "No incomplete work is inside the 10-day low-float band &mdash; the "
                "network currently has room to absorb slips."
            )
            + "</p>"
        )
        if pressure:
            prows = "".join(
                f"<tr><td>{task.unique_id}</td><td>{_e(task.name)}</td>"
                f"<td>{d:.0f}</td><td>{tf:.0f}</td>"
                f"<td>{round(task.percent_complete)}%</td></tr>"
                for tf, d, task in pressure
            )
            pressure_rows = (
                "<details><summary class=btn-link>Top pressure points (longest low-float "
                "work)</summary><table><tr><th scope=col>UID</th><th scope=col>Activity</th>"
                "<th scope=col>Duration (wd)</th><th scope=col>Float (wd)</th>"
                f"<th scope=col>%</th></tr>{prows}</table></details>"
            )
        take = (
            f"<p class=sf-take data-no-i18n>{critical} of {n} incomplete activities have "
            f"zero-or-negative float; {thin} more sit within 10 working days of it.</p>"
        )
    else:
        story = "<p class=muted>No incomplete activities to analyze.</p>"
        take = "<p class=sf-take data-no-i18n>No incomplete activities to analyze.</p>"
    head = _panel_head(
        "Activity scatter &mdash; float vs duration",
        # big=False: scatter.js supplies this panel's ONE ⛶ (data-sf-big, curves.js pattern,
        # ADR-0317) — a second head glyph was the round-11 inert duplicate.
        tools=_shell_tools(export_title=_ANALYSIS_XLSX_TITLE, big=False),
        prov=prov,
    )
    return (
        f"<div class=panel{_analysis_export_attr(key)}>{head}{take}"
        f"<p class=muted>Source: <b>{_e(sch.source_file or sch.name)}</b>. "
        "One dot per activity: <b>total float</b> (x) against <b>duration</b> (y), "
        "red = critical (progress-aware), diamonds = milestones. Long-duration, low-float "
        "activities sit at the lower-left &mdash; the schedule's pressure points a count "
        "metric never reveals. The full activity grid above is the accessible data table.</p>"
        f"{story}{pressure_rows}"
        f'<div class=chart-host id=scatterChart data-name="{_e(key)}"></div></div>'
        '<script src="/static/scatter.js"></script>'
    )


def _float_histogram_panel(key: str, *, prov: str = "", take: str = "") -> str:
    """An activity total-float distribution histogram on the analysis page (handbook §6.3.2.5.2.2).

    Operator 2026-07-08: the chart takes the LEFT half of the panel; clicking a bar fills the
    RIGHT half with that band's activities (UID + Name by default, any other standard or custom
    column addable like the Gantt's Columns dropdown) and an Excel export of the selection.

    ``take`` is the panel-contract takeaway line, built by the caller from figures the engine
    already computed (this helper computes nothing itself — the chart is client-rendered). The
    band drill keeps its own per-selection Excel export, so the toolbar carries no ⤓ here."""
    head = _panel_head("Total-float distribution", tools=_shell_tools(), prov=prov)
    take_html = f"<p class=sf-take data-no-i18n>{take}</p>" if take else ""
    return (
        f"<div class=panel>{head}{take_html}"
        "<p class=muted>Activities binned by <b>total float</b> (working days), in DCMA-aligned "
        "bands. Mass at <b>0 / &lt; 0</b> is the critical-and-behind core; a spike in the "
        "<b>&gt; 44 d</b> band is float padding or missing successor logic (DCMA-06). "
        "<b>Click a bar</b> to list that band's activities on the right; add columns with the "
        "selector and export the selection to Excel.</p>"
        "<div class=hist-split>"
        f'<div class="chart-host hist-left" id=floatHist data-name="{_e(key)}"></div>'
        "<div class=hist-right id=floatHistDrill><p class=muted>Click a histogram bar to see "
        "the activities in that float band here.</p></div>"
        "</div></div>"
        '<script src="/static/histogram.js"></script>'
    )


def _calendar_panel(sch: Schedule, *, prov: str = "") -> str:
    """The working calendar the analysis runs on — imported from the file (ADR-0028).

    Every computed date, float, and day-denominated threshold rides this calendar, so the
    analyst must be able to verify the time basis (and spot a fail-soft default) on the page.
    When the file assigns some activities their own calendar, the base CPM still models only the
    single project calendar (ADR-0028), so this panel discloses that single-calendar basis rather
    than letting the analyst read the project-calendar row as the whole story (#26).
    """
    cal = sch.calendar
    days = ", ".join(_WEEKDAY_NAMES[d] for d in cal.work_weekdays)
    hours_text = f"{cal.working_minutes_per_day / 60:g} h/day ({cal.working_minutes_per_day} min)"
    if cal.holidays:
        shown = ", ".join(_mdY(d) for d in cal.holidays[:10])
        holidays = _expandable_more(
            f"{len(cal.holidays)} — {shown}", [_mdY(d) for d in cal.holidays[10:]]
        )
    else:
        holidays = "none"
    # Fail-soft disclosure (#26): the base CPM solves on this ONE project calendar; when the file
    # carries per-task calendars with a different working pattern, its base-CPM dates/float are a
    # single-calendar approximation for those activities (the SSI driving path honors each task's
    # own calendar, ADR-0118). Silent on a single-calendar file (off is empty).
    off = off_project_calendars(sch)
    disclosure = ""
    if off:
        n = len(off)
        cal_word = "calendar" if n == 1 else "calendars"
        names = ", ".join(f"<b>{_e(c.name)}</b>" for c in off)
        disclosure = (
            f'<div class="notice info">Some activities run on {n} per-task {cal_word} whose working '
            f"pattern differs from the project calendar <b>{_e(cal.name)}</b> ({names}). The engine's "
            "base CPM models the single project calendar (ADR-0028), so a date or float it computes "
            "(shown where the file carries no stored value of its own) is a single-calendar "
            "approximation for those activities; the file's own stored dates and the Path Analysis / "
            "Driving Path views honor each task's own calendar (ADR-0118)."
            "</div>"
        )
    # ADR-0312: how the importer had to interpret this file, on the page rather than only in a
    # log line the analyst never sees. Empty for every file taken verbatim, which is the norm.
    for note in sch.import_notes:
        disclosure += f'<div class="notice warn">On import: {_e(note)}</div>'
    take = (
        f"<p class=sf-take data-no-i18n>Every computed date and float rides {_e(cal.name)}: "
        f"{cal.working_minutes_per_day / 60:g} h/day, a {len(cal.work_weekdays)}-day work week, "
        f"{len(cal.holidays)} holiday(s).</p>"
    )
    return f"""
<div class=panel>{_panel_head("Working calendar", tools=_shell_tools(), prov=prov)}{take}
<p class=muted>The time basis behind every computed date, float, and day-denominated
threshold — imported from the file's project calendar (the standard 8h/Mon-Fri default
when the file carries none).</p>
{disclosure}
<table>
<tr><th scope=col>Calendar</th><td>{_e(cal.name)}</td></tr>
<tr><th scope=col>Working day</th><td>{_e(hours_text)}</td></tr>
<tr><th scope=col>Work week</th><td>{_e(days)}</td></tr>
<tr><th scope=col>Holidays</th><td>{_e(holidays)}</td></tr>
</table></div>"""


def _dcma_label(metric_id: str) -> str:
    """The spaced display label the operator asked for: ``DCMA01`` -> ``DCMA 01``;
    ``DCMA04_FS`` -> ``DCMA 04 FS``. Non-DCMA ids pass through unchanged."""
    if not metric_id.startswith("DCMA"):
        return metric_id
    base, _, suffix = metric_id[4:].partition("_")
    return f"DCMA {base}" + (f" {suffix.replace('_', ' ')}" if suffix else "")


def _dcma_measure(check: AuditCheck) -> str:
    """A concise measured value to sit beside the stoplight (replacing the old bar): a percentage
    with its count for population checks, the index for CPLI/BEI, a raw count otherwise."""
    if check.unit == "ratio":  # CPLI / BEI — an index, not a count
        return f"{check.value:.2f}"
    if check.population:
        pct = check.value if check.unit == "%" else 100.0 * check.count / check.population
        return f"{pct:.1f}%  ({check.count} of {check.population})"
    if check.count:
        unit = f" {check.unit}" if check.unit and check.unit != "count" else ""
        return f"{check.count}{unit}"
    return str(check.status).title()  # e.g. the critical-path test: Pass / Fail


def _dcma_card(check: AuditCheck) -> dict[str, object]:
    """One DCMA check as Dashboard-overview JSON: the spaced label + human name, a simple measured
    value, the PASS/FAIL/NA status (the stoplight), and the help text for the hover tooltip — what
    the metric is, why it matters, the pass/fail threshold, and a pass + a fail example (operator
    request). ``status`` and ``count`` are retained for back-compatibility with existing readers."""
    doc = METRIC_DICTIONARY.get(check.metric_id)
    return {
        "label": _dcma_label(check.metric_id),
        "name": doc.name if doc else check.name,
        "status": str(check.status),
        "count": check.count,
        "value": check.value,
        "measure": _dcma_measure(check),
        "definition": doc.definition if doc else "",
        "why": doc.importance if doc else "",
        "threshold": doc.threshold if doc else "",
        "example_ok": doc.example_ok if doc else "",
        "example_fail": doc.example_fail if doc else "",
    }


def _dcma_definition_cell(metric_id: str) -> str:
    """The 'what it measures (how)' cell for a DCMA row, from the in-tool metric dictionary —
    plain-language definition + the formula/threshold, so each score is explained in place."""
    doc = METRIC_DICTIONARY.get(metric_id)
    if doc is None:
        return "<td></td>"
    return (
        f"<td class=dcma-def>{_e(doc.definition)} "
        f"<span class=muted>How: {_e(doc.formula)}</span></td>"
    )


def _dcma_metric_cell(check: AuditCheck) -> str:
    """The 'Check' cell: the metric name plus a hover/focus tooltip that explains the metric,
    its pass/fail criteria, why it matters, and what a failing value indicates (operator request).

    The tooltip is keyboard-operable (the trigger is focusable and labelled) and also carries a
    plain-text ``title=`` so the same detail is available with no CSS/JS (air-gap, a11y)."""
    doc = METRIC_DICTIONARY.get(check.metric_id)
    if doc is None:
        return f"<td>{_e(check.name)}</td>"
    display = f"{_dcma_label(check.metric_id)} — {doc.name}"
    tip_id = f"dcma-tip-{_e(check.metric_id)}"
    rich = [
        f"<b>{_e(display)}</b>",
        f"<p>{_e(doc.definition)}</p>",
        f'<p><a class=metric-info href="/help#m-{_e(check.metric_id)}">Full definition, '
        "example and decision guidance &raquo;</a></p>",
    ]
    title = f"{doc.definition}"
    threshold = doc.threshold or f"Pass criteria: {doc.formula}"
    rich.append(f"<p><b>Threshold:</b> {_e(threshold)}</p>")
    title += f" Threshold: {threshold}."
    if doc.importance:
        rich.append(f"<p><b>Why it matters:</b> {_e(doc.importance)}</p>")
        title += f" Why it matters: {doc.importance}"
    if doc.example_ok:
        rich.append(f"<p><b>Pass example:</b> {_e(doc.example_ok)}</p>")
        title += f" Pass example: {doc.example_ok}"
    if doc.example_fail:
        rich.append(f"<p><b>Fail example:</b> {_e(doc.example_fail)}</p>")
        title += f" Fail example: {doc.example_fail}"
    if doc.indicates:
        rich.append(f"<p><b>Indicates:</b> {_e(doc.indicates)}</p>")
        title += f" Indicates: {doc.indicates}"
    return (
        f"<td class=dcma-cell>"
        f'<span class=dcma-metric tabindex=0 role=button aria-describedby="{tip_id}" '
        f'title="{_e(title)}">{_e(display)} '
        f"<span class=dcma-info aria-hidden=true>&#9432;</span></span>"
        f'<div class=dcma-tip id="{tip_id}" role=tooltip>{"".join(rich)}</div></td>'
    )


def _dcma_count_cells(check: AuditCheck) -> str:
    """The Count + '% of tasks' cells, matching how Acumen Fuse shows each metric — the raw
    count over its population plus the percentage, instead of only a pass/fail colour.

    Count-based checks show ``n of population`` and the metric's percentage; the CPLI / BEI
    index checks show the index value (no count); the pass/fail critical-path test shows neither."""
    dash = "<span class=muted>&mdash;</span>"
    if check.unit == "ratio":  # CPLI / BEI — an index, not a count
        return f"<td class=num>{dash}</td><td class=num>{round(check.value, 2)}</td>"
    if check.population:
        pct = check.value if check.unit == "%" else 100.0 * check.count / check.population
        return (
            f"<td class=num>{check.count} <span class=muted>of {check.population}</span></td>"
            f"<td class=num>{pct:.1f}%</td>"
        )
    return f"<td class=num>{check.count}</td><td class=num>{dash}</td>"


def _where_we_stand_header(
    key: str,
    sch: Schedule,
    analysis: _Analysis,
    versions: Sequence[tuple[str, Schedule]] = (),
) -> str:
    """Chapter 01 "Where we stand" (ADR-0197): the data-driven takeaway h1 + the six-KPI strip +
    the Activity-status-mix and Float-remaining bars — every figure read from what the report
    already computed for this schedule (no CPM math added; missing inputs render as an em dash).

    Mission Ops rank 3 (prototype screen 'st'): ``versions`` (the session's ordered manifest,
    oldest first) feeds the SOURCE-FILE bar — filename, version position + data date, a LATEST
    pill, and a per-version chip picker. The chips are plain links to /analysis/<key>: version
    selection IS the URL (exactly the navigation the src-banner's data-sf-navselect switcher
    performs), and persist.js's per-path query-string memory rides it automatically — no second
    selection mechanism is introduced (rank-3 risk note)."""
    cpm = analysis.cpm
    cal = sch.calendar
    makeup = compute_activity_makeup(sch)
    total = makeup.total or 1
    complete_pct = 100.0 * makeup.complete / total

    cpm_finish_dt = offset_to_datetime(sch.project_start, cpm.project_finish, cal)
    cpm_finish_str = _mdY(cpm_finish_dt)

    # vs-baseline finish variance — the existing forecast helper is handed the cached CPM, so no
    # second solve; planned_finish is the latest baseline finish (None when the file carries none).
    fset = compute_finish_forecasts(sch, cpm)
    if fset.planned_finish is not None:
        var_days = (cpm_finish_dt.date() - fset.planned_finish).days
        if var_days > 0:
            vs_base = f"+{var_days}d"
            base_phrase = f"{var_days} day{'s' if var_days != 1 else ''} behind the baseline finish"
        elif var_days < 0:
            vs_base = f"{var_days}d"
            n = -var_days
            base_phrase = f"{n} day{'s' if n != 1 else ''} ahead of the baseline finish"
        else:
            vs_base = "0d"
            base_phrase = "on the baseline finish"
    else:
        vs_base = "—"
        base_phrase = "with no baseline finish to compare against"

    # plan-at-DD proxy: the share of activities the baseline scheduled to be finished by the data
    # date (compute_baseline_compliance's "Forecast to be Finished"); None when the population is 0.
    plan = analysis.compliance.get("forecast_to_be_finished")
    plan_at_dd = f"{plan.value:.0f}%" if plan is not None and plan.population else None

    # critical (incomplete) on the SAME progress-aware basis as the ribbon (ch 02) and ch 11:
    # Acumen reads MS Project's STORED Critical flag, falling back to pure-logic CPM critical only
    # when the file carries no flag (_common.is_effective_critical). Reading raw tm.total_float here
    # made a progressed file show a different Critical count than every other chapter (audit M3).
    critical = sum(
        1
        for t in non_summary(sch)
        if t.percent_complete < 100.0
        and is_effective_critical(
            t, cpm.timings[t.unique_id].total_float if t.unique_id in cpm.timings else 0
        )
    )
    data_date = _mdY(sch.status_date) if sch.status_date else "—"

    # takeaway h1 — a sentence with a number; every clause is a real figure or is omitted
    plan_clause = f" against a {plan_at_dd} baseline plan at the data date" if plan_at_dd else ""
    takeaway = f"{complete_pct:.0f}% complete{plan_clause} — computed finish {cpm_finish_str}, "
    # base_phrase / vs_base may carry an entity (&mdash;); keep the takeaway HTML-safe by escaping
    # only the parts we build from user-independent computed values (all of the above are).

    kpi = _stat_cards(
        [
            ("Activities", str(makeup.total)),
            (
                "Earned complete",
                f"{complete_pct:.0f}%" + (f" · plan {plan_at_dd}" if plan_at_dd else ""),
            ),
            ("Critical (incomplete)", str(critical)),
            ("Computed finish", cpm_finish_str),
            ("vs baseline", vs_base),
            ("Data date", data_date),
        ]
    )

    status_bar = _status_stack(
        "Activity status mix",
        "Every activity by progress state, from the file's percent-complete.",
        [
            ("Complete", makeup.complete, "--ok"),
            ("In progress", makeup.in_progress, "--warn"),
            ("Planned", makeup.planned, "--accent"),
        ],
        f"{makeup.total} activities",
    )

    # incomplete-activity float bands on the SAME progress-aware basis as the ribbon/ch 11:
    # effective total float (stored Total Slack first, else recomputed CPM float) in working days.
    # analysis.activity_rows carries the PURE-LOGIC float, which diverges on a progressed file.
    per_day = cal.working_minutes_per_day or 1
    floats: list[float] = [
        effective_total_float(t, cpm.timings[t.unique_id].total_float) / per_day
        for t in non_summary(sch)
        if t.percent_complete < 100.0 and t.unique_id in cpm.timings
    ]
    b0 = sum(1 for tf in floats if tf <= 0)
    b1 = sum(1 for tf in floats if 0 < tf <= 4)
    b2 = sum(1 for tf in floats if 4 < tf <= 9)
    b3 = sum(1 for tf in floats if tf > 9)
    float_bar = _status_stack(
        "Float remaining",
        "Incomplete activities by total-float band — how much room before a slip hits the finish.",
        [
            ("0 days", b0, "--bad"),
            ("1-4 days", b1, "--warn"),
            ("5-9 days", b2, "--accent"),
            ("10+ days", b3, "--muted"),
        ],
        f"{len(floats)} incomplete activities",
    )

    # ── SOURCE-FILE bar (rank 3, prototype 'st'): which file feeds THIS page, with the chip
    # picker for the others. data-no-i18n on the whole strip — filenames, version labels and
    # dates must never be translated (the src-banner precedent, and the chips would be mangled).
    keys = [k for k, _s in versions]
    pos = keys.index(key) + 1 if key in keys else 0
    ver_lab = (
        f"<span class=src-ver>v{pos} of {len(keys)} &middot; data date {data_date}</span>"
        if pos
        else f"<span class=src-ver>data date {data_date}</span>"
    )
    latest = "<span class=latest-pill>LATEST</span>" if pos and keys and keys[-1] == key else ""
    chips = ""
    if len(keys) > 1 and pos:
        chip_links = "".join(
            f'<a class="ver-chip{" on" if k == key else ""}"'
            + (" aria-current=page" if k == key else "")
            + f' href="/analysis/{quote(k, safe="")}" title="{_e(s.source_file or s.name)}">'
            + f"v{i}</a>"
            for i, (k, s) in enumerate(versions, start=1)
        )
        chips = (
            "<span class=src-cue data-noprint=1>View another file &rarr;</span>"
            f"<span class=ver-chips data-noprint=1>{chip_links}</span>"
        )
    src_bar = (
        "<div class=src-bar data-no-i18n>"
        "<span class=src-lab>&#128196; Source file</span>"
        f"<span class=src-file>{_e(sch.source_file or sch.name)}</span>"
        f"{ver_lab}{latest}{chips}</div>"
    )

    export_bar = _export_bar(f"analysis/{quote(key, safe='')}")
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{takeaway}{base_phrase}.</h1>'
        f"{src_bar}"
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{status_bar}{float_bar}</div>'
        f"{export_bar}"
    )


def _analysis_body(
    key: str,
    sch: Schedule,
    analysis: _Analysis,
    target: int | None = None,
    narrative: Narrative | None = None,
    erosion_field: str | None = None,
    margin_confirmed: frozenset[int] | None = None,
    dcma_acumen_parity: bool = False,
    versions: Sequence[tuple[str, Schedule]] = (),
) -> str:
    audit = analysis.audit
    audit_rows = "".join(
        f'<tr>{_dcma_metric_cell(c)}<td class="{_status_class(c.status)}">{_e(c.status)}</td>'
        f"{_dcma_count_cells(c)}"
        f"{_dcma_definition_cell(c.metric_id)}"
        f"<td class=muted>{_e(c.suggested_improvement)}</td></tr>"
        for c in audit.checks
    )
    findings = analysis.findings
    find_rows = "".join(
        f'<tr><td class="sev-{_e(f.severity)}">{_e(f.severity)}</td><td>{_e(f.category)}</td>'
        f"<td>{_e(f.title)}</td><td class=muted>{_e(f.course_of_action)}</td>"
        f"<td class=cite>{_cites_cell(f)}</td></tr>"
        for f in findings
    )
    story_source = narrative if narrative is not None else analysis.narrative
    story = "".join(f"<li>{_e(s.rendered())}</li>" for s in story_source.statements)
    target_panel = _target_panel(sch, analysis, target) if target is not None else ""
    # panel-contract chrome shared by every panel on this page (Mission Ops rank 3): the
    # provenance chip quotes THIS schedule's file + data date; ⤓ EXCEL rides the EXISTING
    # per-schedule analysis workbook export on the panels whose data ships inside it.
    prov = _prov_chip(sch)
    viz_head = _panel_head(
        "Interactive analysis",
        tools=_shell_tools(export_title=_ANALYSIS_XLSX_TITLE),
        prov=prov,
    )
    viz_take = (
        f"<p class=sf-take data-no-i18n>{len(analysis.activity_rows)} activities in the grid "
        "&mdash; every row drills to its metadata, and every column is exportable.</p>"
    )
    viz = f"""{target_panel}
<div class=panel{_analysis_export_attr(key)}>{viz_head}{viz_take}
{_user_tip("Click a column header to sort, use the per-column <b>Filter</b> dropdowns to scope the rows, and drag a column edge to resize it. The data columns stay locked on the left while the Gantt timeline scrolls.")}
<div id=viz data-name="{_e(key)}">
<div class="charts chart-host" id=charts></div>
<p class=muted aria-label="chart color legend" style="margin:4px 0 8px">
<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--ok)"></span> pass / on time &nbsp;
<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--warn)"></span> late / warning &nbsp;
<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--bad)"></span> fail / missed &nbsp;
<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--muted)"></span> not applicable</p>
<div class="viz-controls sf-freeze-bar" id=gridControls>Driving path to target UID:
<input id=targetUid type=number min=1 placeholder="UID" value="{target if target is not None else ""}">
secondary&le;<input id=secMax type=number value=10>d
tertiary&le;<input id=terMax type=number value=20>d
<button id=ganttBtn type=button>Trace</button>
<label><input id=showDone type=checkbox checked> show completed tasks</label>
<label><input id=showLinks type=checkbox checked> links</label>
<label>Tier <span id=ganttTier class=tier-filter></span></label>
<span class=zoom-controls>Scale <button id=zoomOut type=button class=zoom-btn title="Zoom out — fewer pixels per day">&minus;</button><button id=zoomIn type=button class=zoom-btn title="Zoom in — more pixels per day">+</button><input id=vizZoom type=hidden value=8></span>
<button id=fitBtn type=button title="Zoom out so the entire project fits on screen">Fit project</button>
<button id=timescaleBtn type=button title="Modify the timescale: tiers, units (years to hours), labels, count, alignment, fiscal year, tick lines, size and non-working-time shading (like Microsoft Project)">Timescale&hellip;</button>
<label>Find <input id=gridFind type=text placeholder="UID or name…" title="Jump to a UniqueID, or mark every task whose row contains this text"></label>
<span id=gridFindStatus class=muted aria-live=polite></span>
<label>Outline <select id=gridOutline title="Show tasks up to this outline level (like MS Project)"></select></label>
<label title="Show the start/finish dates at the ends of the Gantt bars (MS Project bar text)"><input id=gridBarDates type=checkbox> dates on bars</label></div>
<div id=gantt></div>
<h3>Activities &amp; Gantt <span class=muted>(add/remove columns; the right-hand timeline is
scalable — use the <b>Scale</b> &minus;/+ buttons to zoom (pixels/day) and scroll horizontally; red = critical,
diamonds = milestones, thin = summaries, amber line = data date; click a row to drill into its
metadata)</span></h3>
<div id=fieldToggles></div><div id=grid></div><div id=drill class=drill></div>
</div></div>
<script src="/static/app.js"></script>"""
    fb0 = analysis.float_bands["float_total_0"]
    hist_take = (
        f"{fb0.count} of {fb0.population} incomplete activities sit at 0 working days of "
        "total float — click a bar for the activities behind it."
    )
    dcma_head = _panel_head(
        f"{_e(sch.name)} &mdash; DCMA-14 audit",
        tools=_shell_tools(export_title=_ANALYSIS_XLSX_TITLE),
        prov=prov,
    )
    dcma_take = (
        f"<p class=sf-take data-no-i18n>{audit.passed} of {len(audit.checks)} DCMA checks pass "
        f"&middot; {audit.failed} fail &middot; {audit.not_applicable} N/A.</p>"
    )
    return f"""{_where_we_stand_header(key, sch, analysis, versions)}
{viz}
{_scatter_panel(key, sch, analysis.cpm, prov=prov)}
{_float_histogram_panel(key, prov=prov, take=hist_take)}
{_calendar_panel(sch, prov=prov)}
{_float_bands_panel(analysis, key=key, prov=prov)}
{_completion_panel(analysis, key=key, prov=prov)}
{_health_checks_panel(sch, analysis.cpm, prov=prov)}
{_logic_checks_panel(sch, prov=prov)}
{_constraint_checks_panel(sch, analysis.cpm, prov=prov)}
{_vertical_integration_panel(sch, prov=prov)}
{_schedule_variance_panel(sch, prov=prov)}
{_float_erosion_panel(sch, analysis.cpm, erosion_field, prov=prov)}
{_margin_panel(key, sch, analysis.cpm, margin_confirmed, prov=prov)}
<div class=panel{_analysis_export_attr(key)}>{dcma_head}{dcma_take}
<p class=muted>{audit.passed} passed &middot; {audit.failed} failed &middot; {audit.not_applicable} N/A.
Each row shows the <b>count</b> and the <b>percentage</b> of its population,
not just a pass/fail colour. <b>Hover or focus a check name</b> for its definition, pass/fail
criteria, why it matters, and what it indicates; full formulas + citations are in the
<a href="/help">Metric Dictionary</a>.</p>
<form method=post action="/dcma/scope" style="margin:0 0 8px">
<input type=hidden name=next value="/analysis/{quote(key, safe="")}">
<label><input type=checkbox name=parity value=1 {"checked" if dcma_acumen_parity else ""} data-sf-autosubmit> <b>Acumen&nbsp;Fuse&nbsp;parity&nbsp;mode</b> {"<b style='color:var(--sf-accent,#2a7)'>ON — matching Acumen Fuse</b>" if dcma_acumen_parity else "<span class=muted>OFF — pure-logic / forensic view</span>"}</label> <button type=submit class=btn-sm>Apply</button></form>
<details class=panel style="margin:0 0 10px"><summary><b>What is Acumen parity mode?</b> — the two DCMA views, with examples &amp; when to use each</summary>
<p class=muted>The 14 DCMA checks can be scored two ways. They agree on a clean, fully-baselined schedule; they diverge on real progressed schedules with milestones, un-baselined tasks, and imposed deadlines. Neither is "more correct" — they answer different questions.</p>
<table>
<tr><th scope=col>Dimension</th><th scope=col>Pure-logic / forensic (default, OFF)</th><th scope=col>Acumen&nbsp;Fuse&nbsp;parity (ON)</th></tr>
<tr><td><b>Total Float</b></td><td>The engine's freshly re-computed CPM float (independent of the file's stored dates).</td><td>The file's <b>stored, progress-aware</b> Total Slack, compared in whole days — exactly what Acumen reads.</td></tr>
<tr><td><b>Population</b></td><td>Every incomplete activity, whether or not it was baselined.</td><td>Only activities with a <b>baseline duration ≥ 1 day</b> (Acumen's <i>Baseline Duration&nbsp;&gt;&nbsp;0</i>). Milestones are kept when they carry a real baseline.</td></tr>
<tr><td><b>Resources (10)</b></td><td>Incomplete, real-duration activities with <b>no named resource</b>.</td><td>Activities with <b>no baseline cost AND no baseline work</b> (a task can lack a named resource yet still carry work).</td></tr>
<tr><td><b>CPLI (13)</b></td><td>Recomputed critical-path float — ~0 with no imposed deadline, so CPLI reads 1.0.</td><td>Stored float + stored remaining duration — reflects a behind-schedule finish (e.g. 0.97 / 0.59).</td></tr>
</table>
<p class=muted style="margin-top:6px"><b>Real-world examples:</b></p>
<ul class=muted>
<li><b>A "Project Complete" milestone with a Must-Finish-On date.</b> Pure-logic counts it under Hard Constraints; Acumen parity does not (a zero-baseline milestone fails <i>Baseline Duration&nbsp;&gt;&nbsp;0</i>) — so a schedule that "has 1 hard constraint" here shows 0 in Acumen.</li>
<li><b>A planning-package task with the MS&nbsp;Project unassigned-work placeholder but no named resource.</b> Pure-logic flags it as missing a resource; Acumen parity does not, because it carries baseline work.</li>
<li><b>A task 7 hours behind an imposed deadline (minus 0.29 day of float).</b> Pure-logic flags Negative Float; Acumen parity does not (Acumen shows float in whole days, so -0.29 reads as 0).</li>
<li><b>A behind-schedule program.</b> Pure-logic CPLI reads 1.0 (looks on-track); Acumen parity reads &lt;&nbsp;1.0, correctly showing the slip.</li>
</ul>
<p class=muted><b>When to use which:</b></p>
<ul class=muted>
<li><b>Use pure-logic (default)</b> for independent forensic analysis — delay/path analysis, an un-baselined or draft schedule, or when you want the tool's own recomputation rather than the file's stored dates. It flags <i>every</i> issue the logic exposes, baseline or not.</li>
<li><b>Use Acumen parity</b> when you need to <b>reconcile with or defend against an Acumen&nbsp;Fuse report</b> (e.g. a customer's DCMA scorecard), when the <b>baseline is authoritative</b>, or in a <b>testimony</b> context where Acumen is the reference tool. Its counts match Acumen's ribbon activity-for-activity.</li>
</ul>
<p class=muted style="font-size:0.9em">Formulas are taken verbatim from the NASA Acumen metric library and verified UID-exact against Acumen on the reference schedules (ADR-0280). The default is unchanged and the golden parity gate is unaffected.</p>
</details>
{_stoplight_board(audit.checks)}
<table><tr><th scope=col>Check</th><th scope=col>Status</th><th scope=col>Count</th><th scope=col>% of tasks</th>
<th scope=col>What it measures (how)</th>
<th scope=col>Suggested improvement</th></tr>{audit_rows}</table></div>
<div class=panel{_analysis_export_attr(key)}>{_panel_head("Risks, opportunities &amp; concerns", tools=_shell_tools(export_title=_ANALYSIS_XLSX_TITLE), prov=prov)}
<p class=sf-take data-no-i18n>{len(findings)} finding(s) on this schedule{" — " + str(sum(1 for f in findings if f.severity == "HIGH")) + " HIGH severity" if findings else " — schedule is well-formed"}.</p>
<table><tr><th scope=col>Severity</th><th scope=col>Type</th><th scope=col>Finding</th><th scope=col>Course of action</th><th scope=col>Citations</th></tr>
{find_rows or "<tr><td colspan=5 class=muted>No findings — schedule is well-formed.</td></tr>"}</table></div>
<div class=panel>{_panel_head("AI narrative (local, cited)", tools=_shell_tools(), prov=prov)}
<p class=sf-take data-no-i18n>{len(story_source.statements)} cited statements, computed deterministically — local-AI polish swaps in when a model is active.</p>
<ul class=story data-ai-endpoint="/api/ai/narrative?key={_e(quote(key))}">{story}</ul></div>
<script src="/static/ai_polish.js"></script>
<script src="/static/panelkit.js"></script>"""


def _cites_cell(f: Finding) -> str:
    """A findings-table citation cell: first two cited, the rest expandable in place."""
    shown = _e("; ".join(str(c) for c in f.citations[:2]))
    return _expandable_more(shown, [_e(str(c)) for c in f.citations[2:]])


def _analysis_data(sch: Schedule, analysis: _Analysis) -> dict[str, object]:
    audit = analysis.audit
    compliance = analysis.compliance
    return {
        "name": sch.name,
        "source_file": sch.source_file,
        "tasks": len(sch.tasks),
        "status_date": sch.status_date.date().isoformat() if sch.status_date else None,
        "calendar": {
            "name": sch.calendar.name,
            "working_minutes_per_day": sch.calendar.working_minutes_per_day,
            "work_weekdays": list(sch.calendar.work_weekdays),
            "holidays": [d.isoformat() for d in sch.calendar.holidays],
        },
        # every named calendar in the file — the Timescale dialog's Non-working-time tab lets
        # the operator pick which calendar's weekends/holidays to shade on the Gantt
        "calendars": [
            {
                "name": c.name,
                "work_weekdays": list(c.work_weekdays),
                "holidays": [d.isoformat() for d in c.holidays],
            }
            for c in sch.calendars
        ],
        "dcma": {c.metric_id: _dcma_card(c) for c in audit.checks},
        "baseline_compliance": {k: v.count for k, v in compliance.items()},
        "float_bands": {
            k: {"count": v.count, "population": v.population, "value": v.value}
            for k, v in analysis.float_bands.items()
        },
        "completion": {
            k: {"count": v.count, "population": v.population, "value": v.value, "unit": v.unit}
            for k, v in analysis.completion.items()
        },
        "activities": analysis.activity_rows,
        # the schedule's mapped .mpp custom/extended fields (declared order) -> optional grid columns
        "custom_field_labels": list(sch.custom_field_labels),
        "findings": [
            {
                "severity": str(f.severity),
                "category": str(f.category),
                "title": f.title,
                "citations": [
                    {"file": c.source_file, "uid": c.unique_id, "task": c.task_name}
                    for c in f.citations
                ],
            }
            for f in analysis.findings
        ],
    }
