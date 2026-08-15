"""The /sra page family - the panel wall (SSI run panel, correlation matrix, JCL,
legacy-override table, risk / branch / conditional register sections), the report and
export table builders with their vector charts and NASA 5x5 constants, the page body,
and the /api/sra legacy data builder.

Monolith split, phase 3 slice 9 (ADR-0373), extracted VERBATIM from ``web/app.py``: every
function, docstring and comment moves byte-for-byte, only the module boundary changes.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour
(the ``/sra``, ``/api/sra`` and ``/export/{fmt}/sra`` + ``/export/{fmt}/sra-registry``
routes' builders): 30 names / 22 regions whose external referrers are all ``create_app``
routes, which import downward and stay put. ADR-0365 predicted this closure would claim
the census-out members it measured as /sra family - ``_ssi_panel`` and
``_ssi_export_tables`` are HERE, not in ``web/ssi.py``, exactly as its section 2 ruled.
Two 2-family names descended into ``web/components.py`` instead of moving here
(``_TS_CAPTION_MARK``: the /path, /driving-path and /evolution routes serve the same
marker; ``_schedule_risks``: ``_margin_risk_data`` and five /api routes derive the same
ScheduleRisks), per the ADR-0351 rule - a symbol an extracted module needs must live at
or below that module's layer. ``_ssi_three_point``, ``_risk_events``,
``_schedule_branches`` and ``_schedule_conditionals`` stay in ``app.py`` - shared route
machinery no page owns.

Layering: ``app`` -> ``sra`` -> ``components`` -> ``chrome`` -> ``state`` - engine/model.
Nothing here imports ``web.app`` (or ``web.ssi`` - the run machinery is upstream of the
routes, not of this page family).
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Sequence

from schedule_forensics.engine.cpm import CPMError, CPMResult, offset_to_datetime
from schedule_forensics.engine.jcl import cost_loaded_total
from schedule_forensics.engine.metrics._common import effective_total_float, non_summary
from schedule_forensics.engine.sra import (
    OATSensitivity,
    SRAResult,
    SSIResult,
    _is_completed,
    stored_finish_correction,
)
from schedule_forensics.engine.sra_conclusions import (
    conclusions_as_dicts,
    conclusions_from_sra,
    conclusions_from_ssi,
)
from schedule_forensics.importers._common import iso_duration_to_minutes
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.reports.docx import Block, Chart, ChartText, DocTable, Heading, Paragraph
from schedule_forensics.reports.tables import Cell, Table, TableSet
from schedule_forensics.web.chrome import _e, _observed_banner, _utility_takeaway
from schedule_forensics.web.components import (
    _REMAIN_DAYS_DP,
    _TS_CAPTION_MARK,
    _metric_help_cell,
    _panel_head,
    _prov_chip,
    _schedule_risks,
    _shell_tools,
    _sra_selected,
    _ssi_matrix_counts,
    _stat_cards,
    _status_stack,
    _user_tip,
)
from schedule_forensics.web.help import field_help_payload
from schedule_forensics.web.state import SessionState, UnifiedRisk

#: The panel-level export every converted /sra panel follows (ADR-0339) — the EXISTING SRA tables
#: workbook (`@app.get("/export/{fmt}/sra")`), the same one the SSI panel's own button already
#: offers. Rank-3 law: ⤓ EXCEL renders ONLY where the data really rides that workbook, so the two
#: panels whose content is NOT in it — the "which model" explainer (pure guidance, no data) and a
#: JCL panel on a file with no cost loading (its sheets ship only when the file is cost-loaded) —
#: carry the head, the ⛶ and the chip but no ⤓.
_SRA_EXPORT = ' data-export="/export/xlsx/sra"'
#: Deliberately NOT "this panel's data is one of its sheets" (the wording the /analysis and /risks
#: workbooks use). This workbook holds the SRA run setup, the focus-finish results, the OAT
#: sensitivity and the risk register — so for the three LEGACY Monte-Carlo chart panels it carries
#: the equivalent SSI-model sheet rather than that panel's own series. Naming the workbook is true
#: for all ten panels; claiming per-panel sheet identity would not be (Law 2).
_SRA_XLSX_TITLE = (
    "Export the SRA workbook — run setup, focus-finish results, OAT sensitivity and the risk "
    "register — opens in Excel"
)


def _sra_overrides_table(st: SessionState, sch: Schedule | None) -> str:
    """The current per-activity overrides as a table (UID, opt/ml/pess in days) + Remove buttons."""
    if not st.sra_overrides:
        return "<p class=muted>No per-activity overrides &mdash; every activity uses the global triangular above.</p>"
    per_day = sch.calendar.working_minutes_per_day if sch is not None else 0
    names = sch.tasks_by_id if sch is not None else {}

    def _days(minutes: int) -> str:
        return f"{minutes / per_day:g}" if per_day else str(minutes)

    rows = []
    for uid in sorted(st.sra_overrides):
        opt, ml, pess = st.sra_overrides[uid]
        name = _e(names[uid].name) if uid in names else ""
        rows.append(
            f"<tr><td>{uid}</td><td>{name}</td><td>{_days(opt)}</td><td>{_days(ml)}</td>"
            f"<td>{_days(pess)}</td><td>"
            f'<form action="/sra/risk" method=post class=navform style="display:inline">'
            f'<input type=hidden name=remove value="{uid}">'
            "<button type=submit class=linkbtn>Remove</button></form></td></tr>"
        )
    return (
        "<table><thead><tr><th scope=col>UID</th><th scope=col>Activity</th>"
        f"<th scope=col class=metric-th>{_metric_help_cell('Optimistic (d)', 'optimistic_duration')}</th>"
        f"<th scope=col class=metric-th>{_metric_help_cell('Most-likely (d)', 'most_likely_duration')}</th>"
        f"<th scope=col class=metric-th>{_metric_help_cell('Pessimistic (d)', 'pessimistic_duration')}</th>"
        "<th scope=col></th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
        + '<form action="/sra/risk" method=post class=navform style="margin-top:8px">'
        + '<input type=hidden name=clear value="1">'
        + "<button type=submit>Clear all overrides</button></form>"
    )


_CONSEQUENCE_HINT = (
    "Leave blank to auto-rate from the schedule impact (NASA Schedule guideline: the impact days "
    "converted to calendar months -- &lt;1 week=1, 1 week to &lt;1 month=2, 1 to &lt;3 months=3, "
    "3 to &lt;=6 months=4, &gt;6 months=5)."
)


def _branch_section(st: SessionState) -> str:
    """The probabilistic-branch editor (ADR-0273, Hulett #8): add / list / clear rework branches
    that fire in p% of the SSI iterations. Durations shown in working days."""
    chosen = _sra_selected(st)
    mpd = (chosen[1].calendar.working_minutes_per_day or 480) if chosen is not None else 480
    rows = ""
    for b in st.sra_branches:
        rows += (
            f"<tr><td>{_e(b.name)}</td><td>{b.after_uid}&rarr;{b.before_uid}</td>"
            f"<td>{b.probability * 100:g}%</td>"
            f"<td>{b.low / mpd:g} / {b.ml / mpd:g} / {b.high / mpd:g}</td>"
            f'<td><form action="/sra/branch" method=post style="display:inline">'
            f'<input type=hidden name=action value=remove><input type=hidden name=bid value="{b.id}">'
            f"<button type=submit class=linkbtn>remove</button></form></td></tr>"
        )
    table = (
        '<table style="width:auto"><tr><th>Rework</th><th>Tie</th><th>P</th>'
        f"<th>BC/ML/WC d</th><th></th></tr>{rows}</table>"
        if st.sra_branches
        else "<p class=muted>No probabilistic branches defined.</p>"
    )
    return f"""<details class=explainer><summary><b>Probabilistic branches</b> &mdash; discrete rework that fires in p% of iterations (the bi-modal risk view, Hulett)</summary>
<p class=muted>A <b>probabilistic branch</b> models a discrete failure/rework that, when it fires,
inserts an extra activity onto an existing Finish&ndash;to&ndash;Start tie &mdash; delaying everything
downstream by its sampled duration. Unlike a risk (whose impact replaces an <i>existing</i> task's
remaining duration while it fires), a
branch is a <b>new node</b> on the chosen link, so it only moves the finish when it becomes the
driving path, and it produces the <b>bi-modal</b> finish distribution (a spike at "no failure" plus a
shifted lump when the rework happens) the deterministic plan hides. Durations are working days; a
branch whose After&rarr;Before FS tie doesn't exist is reported <b>inert</b> after the run.</p>
<form action="/sra/branch" method=post class=viz-controls>
<label>Name <input type=text name=name placeholder="Retest after failure" required></label>
<label>After UID <input type=number name=after_uid min=1 style="width:80px" required></label>
<label>Before UID <input type=number name=before_uid min=1 style="width:80px" required></label>
<label>Probability&nbsp;% <input type=number name=prob min=0 max=100 step=1 value=20 style="width:64px"></label>
<label title="Best / Most-Likely / Worst-case rework duration in working days">BC/ML/WC days <input type=number name=low min=0 step=0.5 placeholder=BC style="width:56px">
<input type=number name=ml min=0 step=0.5 placeholder=ML style="width:56px">
<input type=number name=high min=0 step=0.5 placeholder=WC style="width:56px"></label>
<button type=submit>Add branch</button></form>
{table}
<form action="/sra/branch" method=post style="display:inline"><input type=hidden name=action value=clear>
<button type=submit class=linkbtn>Clear all branches</button></form></details>"""


def _conditional_section(st: SessionState) -> str:
    """The conditional-branch editor (ADR-0274, Hulett #9): add / list / clear contingency switches.
    Each tests a monitored activity every SSI iteration and executes the primary Plan A or the
    contingency Plan B; the run reports which plan wins how often. Durations/threshold in working
    days."""
    chosen = _sra_selected(st)
    mpd = (chosen[1].calendar.working_minutes_per_day or 480) if chosen is not None else 480
    rows = ""
    for c in st.sra_conditionals:
        cmp_sym = "&ge;" if c.trip_when == "at_or_above" else "&lt;"
        metric_lbl = "dur" if c.metric == "duration" else "finish"
        cond_txt = f"UID {c.monitor_uid} {metric_lbl} {cmp_sym} {c.threshold_minutes / mpd:g}d"
        rows += (
            f"<tr><td>{_e(c.name)}</td><td>{cond_txt}</td>"
            f"<td>{c.plan_a.after_uid}&rarr;{c.plan_a.before_uid} ({c.plan_a.ml / mpd:g}d)</td>"
            f"<td>{c.plan_b.after_uid}&rarr;{c.plan_b.before_uid} ({c.plan_b.ml / mpd:g}d)</td>"
            f'<td><form action="/sra/conditional" method=post style="display:inline">'
            f'<input type=hidden name=action value=remove><input type=hidden name=cid value="{c.id}">'
            f"<button type=submit class=linkbtn>remove</button></form></td></tr>"
        )
    table = (
        '<table style="width:auto"><tr><th>Contingency</th><th>Condition</th>'
        f"<th>Plan A (primary)</th><th>Plan B (fallback)</th><th></th></tr>{rows}</table>"
        if st.sra_conditionals
        else "<p class=muted>No conditional branches defined.</p>"
    )
    return f"""<details class=explainer><summary><b>Conditional branches</b> &mdash; contingency switching: stick with Plan A vs fall to Plan B when a condition trips (Hulett)</summary>
<p class=muted>A <b>conditional branch</b> models a <b>contingency plan</b>. Each iteration a
<b>condition</b> on a <i>monitored</i> activity decides which of two mutually-exclusive plans runs:
the primary <b>Plan A</b> when the condition does <i>not</i> trip, or the contingency <b>Plan B</b>
when it does. Unlike a probabilistic branch (a fixed-probability coin flip), the choice is driven by
the iteration's realized state, so the run reports <b>which plan wins how often</b> and the finish
distribution reflects the plan mix. The <b>Monitor</b> is the watched activity; the condition trips
on its sampled <b>duration</b> or its pre-contingency <b>finish</b> crossing the <b>threshold</b>
(working days). Each plan is a new activity on an existing Finish&ndash;to&ndash;Start tie
(<b>After&rarr;Before</b>) with a 3-point duration; a plan whose tie doesn't exist makes the
conditional <b>inert</b> (disclosed after the run). The Monitor should be <i>upstream</i> of the
plans (a finish-metric monitor is read from a per-iteration probe solve).</p>
<form action="/sra/conditional" method=post class=viz-controls>
<label>Name <input type=text name=name placeholder="Fall back to off-the-shelf part" required></label>
<label title="The watched activity whose outcome trips the contingency">Monitor UID <input type=number name=monitor_uid min=1 style="width:80px" required></label>
<label title="duration = the monitor's sampled duration; finish = its early finish (working days from start), read via a probe solve">Condition on
<select name=metric><option value=duration>duration</option><option value=finish>finish</option></select></label>
<label>trips when
<select name=trip_when><option value=at_or_above>&ge; threshold (late/long)</option><option value=below>&lt; threshold (early/short)</option></select></label>
<label title="Working days: a duration for the duration metric, or a finish offset into the project for the finish metric">Threshold&nbsp;days <input type=number name=threshold min=0 step=0.5 style="width:64px" required></label>
<fieldset style="display:inline-block;border:1px solid var(--sf-border,#888);padding:4px 8px;margin:2px">
<legend>Plan A (primary)</legend>
<label>After <input type=number name=a_after min=1 style="width:72px" required></label>
<label>Before <input type=number name=a_before min=1 style="width:72px" required></label>
<label title="Best / Most-Likely / Worst-case working days">BC/ML/WC <input type=number name=a_low min=0 step=0.5 placeholder=BC style="width:52px">
<input type=number name=a_ml min=0 step=0.5 placeholder=ML style="width:52px">
<input type=number name=a_high min=0 step=0.5 placeholder=WC style="width:52px"></label></fieldset>
<fieldset style="display:inline-block;border:1px solid var(--sf-border,#888);padding:4px 8px;margin:2px">
<legend>Plan B (contingency)</legend>
<label>After <input type=number name=b_after min=1 style="width:72px" required></label>
<label>Before <input type=number name=b_before min=1 style="width:72px" required></label>
<label title="Best / Most-Likely / Worst-case working days">BC/ML/WC <input type=number name=b_low min=0 step=0.5 placeholder=BC style="width:52px">
<input type=number name=b_ml min=0 step=0.5 placeholder=ML style="width:52px">
<input type=number name=b_high min=0 step=0.5 placeholder=WC style="width:52px"></label></fieldset>
<button type=submit>Add contingency</button></form>
{table}
<form action="/sra/conditional" method=post style="display:inline"><input type=hidden name=action value=clear>
<button type=submit class=linkbtn>Clear all conditionals</button></form></details>"""


def _unified_risk_section(st: SessionState) -> str:
    """The single 'enter once' risk/opportunity register: ONE form carrying BOTH a days magnitude
    (SSI) and a %/multiplicative magnitude (legacy), the registered-risk table (with each magnitude
    and its lock state), and the client-side days<->% auto-derive (sra_risk.js, fed a uid->remaining-
    days map). Removing/clearing posts to the same /sra/risk-register route. Both magnitudes are
    turned into the engine's ScheduleRisk / RiskEvent at the compute boundary."""
    chosen = _sra_selected(st)
    sch = chosen[1] if chosen is not None else None
    mpd = (sch.calendar.working_minutes_per_day or 480) if sch is not None else 480
    rem_map: dict[int, float] = {}
    if sch is not None:
        for t in non_summary(sch):
            rem = (
                t.remaining_duration_minutes
                if t.remaining_duration_minutes is not None
                else t.duration_minutes
            )
            rem_map[t.unique_id] = round(rem / mpd, _REMAIN_DAYS_DP)
    rem_json = json.dumps({str(u): d for u, d in rem_map.items()}).replace("<", "\\u003c")
    lock = "&#128274;"  # a small lock marks a magnitude the operator set explicitly (used verbatim)
    rows = (
        "".join(
            f"<tr><td>{_e(r.id)}</td><td>{_e(r.name)}</td><td>{r.probability * 100:g}%</td>"
            f"<td>{r.impact_days:g} d{(' ' + lock) if r.days_locked else ''}</td>"
            f"<td>{r.impact_pct:g}%{(' ' + lock) if r.pct_locked else ''}</td>"
            f"<td>{_e(', '.join(str(u) for u in r.affected))}</td>"
            f'<td><form action="/sra/risk-register" method=post style="display:inline">'
            f'<input type=hidden name=action value=remove><input type=hidden name=rid value="{_e(r.id)}">'
            "<button type=submit class=linkbtn>remove</button></form></td></tr>"
            for r in st.sra_risks
        )
        or "<tr><td colspan=7 class=muted>No risks registered.</td></tr>"
    )
    return f"""
<h3>Risk / Opportunity register</h3>
<p class=muted>Enter a risk <b>once</b> &mdash; it feeds <b>both</b> the days-impact (SSI) and the
multiplicative-% (legacy) Monte-Carlo. While the risk fires, the days impact <b>replaces</b> the
affected tasks' remaining duration (SSI semantics, ADR-0359). Type a <b>days</b> impact <i>or</i> a
<b>%</b> impact and the
other auto-calculates from the affected tasks' remaining duration; edit either to override it (it
locks {lock} and is used as-entered for that model). A negative value is an opportunity.</p>
<form id=riskForm action="/sra/risk-register" method=post class=viz-controls>
<input type=hidden name=action value=add>
<input type=hidden id=riskDaysLocked name=days_locked value="">
<input type=hidden id=riskPctLocked name=pct_locked value="">
<label>Name <input type=text name=name maxlength=80 placeholder="e.g. Permit delay"></label>
<label>Probability % <input type=number name=prob min=0 max=100 step=any placeholder="40"></label>
<label>Affected UIDs <input type=text id=riskAffected name=affected placeholder="106, 152"></label>
<label>Impact (days) <input type=number id=riskDays name=impact_days step=any placeholder="auto"></label>
<label>Impact (%) <input type=number id=riskPct name=impact_pct step=any placeholder="auto"></label>
<label title="{_CONSEQUENCE_HINT}">Consequence 1-5 <input type=number name=consequence min=1 max=5
 style="width:56px" placeholder="auto &#9432;"></label>
<button type=submit>Add risk</button></form>
<table><thead><tr><th scope=col>ID</th><th scope=col>Name</th><th scope=col>Prob</th>
<th scope=col>Impact (days)</th><th scope=col>Impact (%)</th><th scope=col>Affected</th>
<th scope=col></th></tr></thead><tbody>{rows}</tbody></table>
<form action="/sra/risk-register" method=post class=navform style="margin-top:6px">
<input type=hidden name=action value=clear><button type=submit>Clear all risks</button></form>
<script id=sfRemainDays type="application/json">{rem_json}</script>
<script src="/static/sra_risk.js"></script>"""


#: The custom-field labels MS Project files in the SSI ecosystem store their SRA inputs under
#: (verified on both committed reference families). Read VERBATIM — the same values SSI reads.
_SRA_RISK_PROB_FIELD = "SSI SRA Risk Probability"
_SRA_RISK_IMPACT_FIELD = "SSI SRA Schedule Impact"


def _file_stored_risks(sch: Schedule) -> list[UnifiedRisk]:
    """The schedule's OWN stored register risks, read verbatim (ADR-0360 closing an ADR-0356
    gap): SSI reads ``SSI SRA Risk Probability`` / ``SSI SRA Schedule Impact`` off the file, so
    "Load from schedule" must carry the register too — factors + Best/Worst alone left the
    session's register empty while SSI ran two risks, which is an input mismatch by another
    door. The days magnitude is the file's (locked); the legacy % derives from the affected
    activity's remaining duration exactly as the register form would."""
    mpd = sch.calendar.working_minutes_per_day or 480
    out: list[UnifiedRisk] = []
    for t in non_summary(sch):
        if _is_completed(t):
            continue
        fields = dict(t.custom_fields)
        prob_raw = fields.get(_SRA_RISK_PROB_FIELD)
        impact_raw = fields.get(_SRA_RISK_IMPACT_FIELD)
        impact_minutes = iso_duration_to_minutes(impact_raw) if impact_raw else None
        if not prob_raw or not impact_minutes:  # absent OR zero impact — no risk to model
            continue
        try:
            prob = max(0.0, min(1.0, float(str(prob_raw))))
        except (TypeError, ValueError):
            continue
        impact_days = impact_minutes / mpd
        rem = t.remaining_duration_minutes
        rem = rem if rem is not None else t.duration_minutes
        pct = (impact_minutes / rem * 100.0) if rem else 0.0
        out.append(
            UnifiedRisk(
                id=f"R{t.unique_id}",
                name=t.name,
                probability=prob,
                affected=(t.unique_id,),
                impact_days=round(impact_days, 2),
                impact_pct=round(pct, 2),
                days_locked=True,
                pct_locked=False,
            )
        )
    return out


def _ssi_export_tables(
    st: SessionState, sch: Schedule, result: SSIResult, oat: Sequence[OATSensitivity]
) -> TableSet:
    """The SSI hand-out (ADR-0123): the plain-language conclusions (ADR-0201) lead, then run
    setup, per-task durations, risk register, focus-finish results, OAT sensitivity, and the
    two 5x5 matrices."""
    conclusions = Table(
        "What the results mean",
        ("Topic", "Severity", "Finding", "What it means", "Evidence"),
        tuple(
            (
                c.topic,
                c.severity.upper(),
                c.finding,
                c.meaning,
                "; ".join(f"{label}: {value}" for label, value in c.evidence),
            )
            for c in conclusions_from_ssi(sch, result)
        ),
    )
    mpd = sch.calendar.working_minutes_per_day or 480
    names = sch.tasks_by_id
    focus_name = (
        names[result.target_uid].name
        if result.target_uid is not None and result.target_uid in names
        else "Project finish"
    )
    setup = Table(
        "Run setup",
        ("Field", "Value"),
        (
            (
                "Focus event",
                f"{result.target_uid} - {focus_name}"
                if result.target_uid is not None
                else focus_name,
            ),
            ("Occurrence mode", result.occurrence_mode),
            ("Correlation", result.correlation),
            ("Risk register", "on" if result.used_risks else "off"),
            ("Sampling", result.sampling),
            (
                "Probabilistic branches",
                f"on ({len(result.branches)})" if result.branches else "off",
            ),
            (
                "Conditional branches",
                f"on ({len(result.conditionals)})" if result.conditionals else "off",
            ),
            ("Iterations", result.iterations),
            ("Schedule", sch.name),
        ),
    )
    dur_rows: list[tuple[Cell, ...]] = []
    for uid in sorted(set(st.sra_factors) | set(st.sra_bcwc)):
        task = names.get(uid)
        if task is None:
            continue
        bc = st.sra_bcwc.get(uid)
        dur_rows.append(
            (
                uid,
                task.name,
                st.sra_factors.get(uid),
                round(bc[0] / mpd, 2) if bc else None,
                round(bc[1] / mpd, 2) if bc else None,
            )
        )
    durations = Table(
        "Per-task durations",
        ("UID", "Task", "Factor", "Best case d", "Worst case d"),
        tuple(dur_rows),
    )
    risk_by_id = {r.id: r for r in _schedule_risks(st)}
    risks = Table(
        "Risk register",
        (
            "ID",
            "Name",
            "Probability %",
            "Impact d",
            "Affected",
            "Consequence",
            "Hits",
            "Mean delta d",
        ),
        tuple(
            (
                rs.id,
                rs.name,
                round(rs.probability * 100, 1),
                rs.impact_days,
                ", ".join(str(u) for u in risk_by_id[rs.id].affected)
                if rs.id in risk_by_id
                else "",
                rs.consequence_rating,
                rs.hits,
                rs.mean_delta_days,
            )
            for rs in result.risks
        ),
    )
    # probabilistic-branch setup + outcomes (ADR-0273) — a branch shifts the percentiles, so the
    # export must disclose it (an undocumented modeled input makes the run unreproducible, Law 2).
    branch_by_id = {b.id: b for b in st.sra_branches}
    branches_tbl = Table(
        "Probabilistic branches",
        (
            "ID",
            "Name",
            "Probability %",
            "Tie (after->before)",
            "BC/ML/WC d",
            "Fired %",
            "Mean rework d",
            "Mean delta d",
            "Status",
        ),
        tuple(
            (
                bs.id,
                bs.name,
                round(bs.probability * 100, 1),
                f"{branch_by_id[bs.id].after_uid} -> {branch_by_id[bs.id].before_uid}"
                if bs.id in branch_by_id
                else "",
                f"{branch_by_id[bs.id].low / mpd:g} / {branch_by_id[bs.id].ml / mpd:g}"
                f" / {branch_by_id[bs.id].high / mpd:g}"
                if bs.id in branch_by_id
                else "",
                round(bs.fired_fraction * 100, 1) if bs.applied else "",
                bs.mean_fragnet_days if bs.applied else "",
                bs.mean_delta_days if bs.applied else "",
                "applied" if bs.applied else "inert (no FS tie)",
            )
            for bs in result.branches
        ),
    )
    # conditional-branch setup + outcomes (ADR-0274) — a conditional shifts the percentiles, so the
    # export must disclose which plan won how often (an undocumented modeled input is unreproducible).
    cond_by_id = {c.id: c for c in st.sra_conditionals}
    conditionals_tbl = Table(
        "Conditional branches",
        (
            "ID",
            "Name",
            "Condition",
            "Plan A (primary)",
            "Plan B (fallback)",
            "Plan A %",
            "Plan B %",
            "Mean A d",
            "Mean B d",
            "Mean delta d",
            "Status",
        ),
        tuple(
            (
                cs.id,
                cs.name,
                f"UID {cs.monitor_uid} {cs.metric}"
                f" {'>=' if cs.trip_when == 'at_or_above' else '<'} {cs.threshold_minutes / mpd:g}d",
                f"{cond_by_id[cs.id].plan_a.after_uid} -> {cond_by_id[cs.id].plan_a.before_uid}"
                f" ({cond_by_id[cs.id].plan_a.ml / mpd:g}d)"
                if cs.id in cond_by_id
                else "",
                f"{cond_by_id[cs.id].plan_b.after_uid} -> {cond_by_id[cs.id].plan_b.before_uid}"
                f" ({cond_by_id[cs.id].plan_b.ml / mpd:g}d)"
                if cs.id in cond_by_id
                else "",
                round(cs.plan_a_fraction * 100, 1) if cs.applied else "",
                round(cs.plan_b_fraction * 100, 1) if cs.applied else "",
                cs.mean_a_finish_days if cs.applied else "",
                cs.mean_b_finish_days if cs.applied else "",
                cs.mean_delta_days if cs.applied else "",
                "applied" if cs.applied else "inert (missing monitor/tie)",
            )
            for cs in result.conditionals
        ),
    )
    results = Table(
        "Focus-finish results",
        ("Measure", "Value"),
        (
            ("Deterministic finish", result.deterministic_finish_date),
            ("Deterministic percentile", round(result.deterministic_percentile * 100, 1)),
            ("P10", result.p10_date),
            ("P50", result.p50_date),
            ("P80", result.p80_date),
            ("P90", result.p90_date),
            ("Mean", result.mean_date),
            ("Std deviation (working days)", round(result.std_days, 2)),
            ("Std deviation (calendar days)", round(result.std_cal_days, 2)),
        ),
    )
    sens = Table(
        "OAT sensitivity",
        (
            "UID",
            "Task",
            "Best case d",
            "Worst case d",
            "ML d",
            "Opportunity wd",
            "Risk wd",
            "Total wd",
        ),
        tuple(
            (
                o.unique_id,
                names[o.unique_id].name if o.unique_id in names else "",
                round(o.bc_minutes / mpd, 2),
                round(o.wc_minutes / mpd, 2),
                round(o.ml_minutes / mpd, 2),
                o.opportunity_days,
                o.risk_days,
                o.total_days,
            )
            for o in oat[:200]
        ),
    )
    risk_grid = _ssi_matrix_counts(result.risks, opportunity=False)
    opp_grid = _ssi_matrix_counts(result.risks, opportunity=True)
    risk_matrix = Table(
        "Risk matrix",
        ("Consequence \\ Probability", "1", "2", "3", "4", "5"),
        tuple((c + 1, *(risk_grid[c][p] for p in range(5))) for c in reversed(range(5))),
    )
    opp_matrix = Table(
        "Opportunity matrix",
        ("Consequence \\ Probability", "1", "2", "3", "4", "5"),
        tuple((c + 1, *(opp_grid[c][p] for p in range(5))) for c in reversed(range(5))),
    )
    return TableSet(
        f"Schedule Risk & Opportunity Analysis - {sch.name}",
        (
            conclusions,
            setup,
            durations,
            risks,
            branches_tbl,
            conditionals_tbl,
            results,
            sens,
            risk_matrix,
            opp_matrix,
        ),
    )


# The NASA 5x5 priority ranks (1..25) + tri-band zones (mirrors web/static/sra_ssi.js), reused to
# render the Risk/Opportunity matrices as shaded grids in the Word report (ADR-0124).
_NASA_RANK = (
    (1, 3, 5, 8, 12),
    (2, 6, 11, 14, 17),
    (4, 9, 15, 19, 21),
    (7, 13, 18, 22, 24),
    (10, 16, 20, 23, 25),
)
_NASA_ZONE = (
    ("g", "g", "g", "g", "y"),
    ("g", "g", "y", "y", "r"),
    ("g", "y", "y", "r", "r"),
    ("g", "y", "r", "r", "r"),
    ("g", "y", "r", "r", "r"),
)
_NASA_FILL = {
    "risk": {"g": "43A047", "y": "FFD400", "r": "E53935"},
    "opp": {"g": "A8D3EA", "y": "3D8EC4", "r": "15527D"},
}
_NASA_LIK = ("Remote", "Unlikely", "Possible", "Highly Likely", "Near Certainty")
_NASA_CONS_RISK = ("Low", "Minor", "Moderate", "Significant", "Severe")
_NASA_CONS_OPP = ("Low", "Minor", "Moderate", "High", "Very High")


def _sra_chart_scurve(result: SSIResult) -> Chart | None:
    """The cumulative finish-date S-curve as a fully-labelled vector chart: gridlines + axis + dense
    curve + dashed deterministic line + P10/50/80/90 dots, with a title, y-axis confidence ticks,
    x-axis date ticks + axis title, a legend, and a parked block of the percentile dates."""
    pts = [(dt.date.fromisoformat(d), p) for d, p in result.s_curve]
    if len(pts) < 2:
        return None
    x0 = min(d.toordinal() for d, _ in pts)
    span = (max(d.toordinal() for d, _ in pts) - x0) or 1

    def fx(day: dt.date) -> float:
        return max(0.0, min(1.0, (day.toordinal() - x0) / span))

    grids = tuple((((0.0, g), (1.0, g)), "E3E8EE", 6350) for g in (0.25, 0.5, 0.75, 1.0))
    axis = (((0.0, 1.0), (0.0, 0.0), (1.0, 0.0)), "555555", 9525)
    curve = (tuple((fx(d), p) for d, p in pts), "0B6BCB", 19050)
    detf = fx(dt.date.fromisoformat(result.deterministic_finish_date))
    det_line = (((detf, 0.0), (detf, 1.0)), "D29922", 9525)
    dots = tuple(
        (fx(dt.date.fromisoformat(ds)), q, "E8352E")
        for q, ds in (
            (0.10, result.p10_date),
            (0.50, result.p50_date),
            (0.80, result.p80_date),
            (0.90, result.p90_date),
        )
    )
    start_iso, end_iso = pts[0][0].isoformat(), pts[-1][0].isoformat()
    labels = (
        ChartText(0.0, 1.15, "Finish-date confidence (S-curve)", "l", 18, "222B35", True),
        *(ChartText(-0.015, q, f"{int(q * 100)}%", "r", 12) for q in (0.0, 0.25, 0.5, 0.75, 1.0)),
        ChartText(0.0, -0.07, start_iso, "l", 12),
        ChartText(1.0, -0.07, end_iso, "r", 12),
        ChartText(
            0.5, -0.18, "Forecast finish date  (y = % chance of finishing on or before)", "c", 12
        ),
        ChartText(
            0.02,
            0.84,
            f"P10  {result.p10_date}\nP50  {result.p50_date}\nP80  {result.p80_date}\n"
            f"P90  {result.p90_date}\nDeterministic  {result.deterministic_finish_date}",
            "l",
            13,
            "33414E",
        ),
        ChartText(0.04, -0.30, "— confidence curve", "l", 11, "0B6BCB"),
        ChartText(0.40, -0.30, "- - deterministic (logic-only) finish", "l", 11, "B5790C"),
        ChartText(0.80, -0.30, "* P10-P90 markers", "l", 11, "E8352E"),
    )
    return Chart(
        kind="vector",
        width_in=6.4,
        height_in=2.7,
        polylines=(*grids, axis, curve, det_line),
        dots=dots,
        labels=labels,
    )


def _sra_chart_hist(result: SSIResult) -> Chart | None:
    """The finish-date distribution (histogram) as labelled vector bars: title, a 0..max frequency
    y-axis, x-axis date ticks + axis title, and a call-out on the most-likely (tallest) bar."""
    bins = result.finish_hist
    if not bins:
        return None
    maxc = max((c for _d, c in bins), default=0) or 1
    peak_i = max(range(len(bins)), key=lambda i: bins[i][1])
    peak_date, peak_count = bins[peak_i]
    n = len(bins)
    rects = tuple(
        (i / n + 0.008, 0.0, (i + 1) / n - 0.008, c / maxc, "3D8EC4")
        for i, (_d, c) in enumerate(bins)
    )
    grids = tuple((((0.0, g), (1.0, g)), "E3E8EE", 6350) for g in (0.5, 1.0))
    axis = (((0.0, 1.0), (0.0, 0.0), (1.0, 0.0)), "555555", 9525)
    labels = (
        ChartText(0.0, 1.15, "Finish-date distribution", "l", 18, "222B35", True),
        ChartText(-0.015, 0.0, "0", "r", 12),
        ChartText(-0.015, 0.5, f"{round(maxc / 2)}", "r", 12),
        ChartText(-0.015, 1.0, f"{maxc}", "r", 12),
        ChartText(-0.04, 1.13, "Iterations", "l", 11),
        ChartText(0.0, -0.07, bins[0][0], "l", 12),
        ChartText(1.0, -0.07, bins[-1][0], "r", 12),
        ChartText(0.5, -0.18, "Forecast finish date  (y = number of simulated finishes)", "c", 12),
        ChartText(
            (peak_i + 0.5) / n,
            min(1.07, peak_count / maxc + 0.07),
            f"most likely\n{peak_date} ({peak_count})",
            "c",
            11,
            "1A5276",
        ),
    )
    return Chart(
        kind="vector",
        width_in=6.4,
        height_in=2.5,
        polylines=(*grids, axis),
        rects=rects,
        labels=labels,
    )


def _sra_chart_tornado(oat: Sequence[OATSensitivity]) -> Chart | None:
    """The duration-sensitivity tornado: per task a centred bar — opportunity-to-accelerate (green,
    left of centre) and risk-of-delay (red, right) — scaled to the largest total swing, with a
    title, per-row UID + total-swing labels, a centre baseline, a working-day scale, and a legend."""
    rows = [o for o in oat if o.total_days > 0][:12]
    if not rows:
        return None
    maxv = max((o.opportunity_days + o.risk_days for o in rows), default=0.0) or 1.0
    n = len(rows)
    rects: list[tuple[float, float, float, float, str]] = []
    labels: list[ChartText] = [
        ChartText(
            0.0, 1.13, "Duration sensitivity (tornado) — working-day swing", "l", 18, "222B35", True
        ),
        ChartText(0.27, 1.04, "◀ opportunity (accelerate)", "c", 11, "2E7D32"),
        ChartText(0.73, 1.04, "risk (delay) ▶", "c", 11, "C62828"),
        ChartText(0.5, -0.06, "0", "c", 12),
        ChartText(0.0, -0.06, f"-{maxv:g} wd", "l", 11),
        ChartText(1.0, -0.06, f"+{maxv:g} wd", "r", 11),
        ChartText(
            0.5,
            -0.17,
            "Working days the focus finish moves when each task is swung Best↔Worst",
            "c",
            12,
        ),
    ]
    for i, o in enumerate(rows):
        y0 = 1.0 - (i + 0.85) / n
        y1 = 1.0 - (i + 0.15) / n
        yc = 1.0 - (i + 0.5) / n
        opp = (o.opportunity_days / maxv) * 0.5
        risk = (o.risk_days / maxv) * 0.5
        if opp > 0:
            rects.append((0.5 - opp, y0, 0.5, y1, "43A047"))
        if risk > 0:
            rects.append((0.5, y0, 0.5 + risk, y1, "E53935"))
        labels.append(ChartText(-0.015, yc, o.risk_id or str(o.unique_id), "r", 11, "33414E"))
        labels.append(ChartText(1.0, yc, f"{o.total_days:g} wd", "l", 11, "33414E"))
    center = (((0.5, 0.0), (0.5, 1.0)), "555555", 9525)
    return Chart(
        kind="vector",
        width_in=6.4,
        height_in=2.9,
        polylines=(center,),
        rects=tuple(rects),
        labels=tuple(labels),
    )


def _sra_matrix_chart(result: SSIResult, *, opportunity: bool) -> Chart:
    """The 5x5 Risk/Opportunity assessment matrix as a shaded grid: NASA rank (1-25) + (count)."""
    counts = _ssi_matrix_counts(result.risks, opportunity=opportunity)  # [consequence-1][prob-1]
    fam = "opp" if opportunity else "risk"
    cons = _NASA_CONS_OPP if opportunity else _NASA_CONS_RISK
    fill = _NASA_FILL[fam]

    def cell(lk: int, c: int) -> tuple[str, str, str]:
        cnt = counts[c - 1][lk - 1]
        zone = _NASA_ZONE[lk - 1][c - 1]
        text = f"{_NASA_RANK[lk - 1][c - 1]}" + (f" ({cnt})" if cnt else "")
        dark_text = zone == "r" or (opportunity and zone == "y")
        return (text, fill[zone], "FFFFFF" if dark_text else "10202E")

    header = (
        ("L \\ C", "E9EEF5", "333333"),
        *((f"{c + 1} {cons[c]}", "E9EEF5", "333333") for c in range(5)),
    )
    body = tuple(
        ((f"{lk} {_NASA_LIK[lk - 1]}", "E9EEF5", "333333"), *(cell(lk, c) for c in range(1, 6)))
        for lk in range(5, 0, -1)
    )
    return Chart(kind="matrix", grid=(header, *body))


def _sra_report_blocks(
    st: SessionState, sch: Schedule, result: SSIResult, oat: Sequence[OATSensitivity]
) -> list[Block]:
    """The comprehensive narrative SRA Word report (ADR-0124): a PM-level executive summary, then
    per-section detail (focus-finish + S-curve + distribution, duration sensitivity + tornado,
    per-task durations, risk register, the 5x5 matrices) with embedded vendor-free vector charts,
    plus a methodology & assumptions section. Reuses the export tables for the data grids."""
    names = sch.tasks_by_id
    focus = (
        names[result.target_uid].name
        if result.target_uid is not None and result.target_uid in names
        else "Project finish"
    )
    by_title = {t.title: t for t in _ssi_export_tables(st, sch, result, oat).tables}

    def doc(title: str) -> DocTable:
        t = by_title[title]
        return DocTable(t.headers, t.rows)

    top = oat[0] if oat else None
    top_txt = (
        f"{top.unique_id} {names[top.unique_id].name if top.unique_id in names else ''} "
        f"({top.total_days:g} wd total swing)"
        if top
        else "n/a"
    )
    det_pct = round(result.deterministic_percentile * 100)
    blocks: list[Block] = [Heading(f"Schedule Risk Analysis Report - {sch.name}", level=0)]
    blocks += [
        Heading("Executive summary", level=1),
        Paragraph(
            f"This Schedule Risk Analysis evaluates the finish of {focus} over {result.iterations} "
            f"Monte-Carlo iterations. The deterministic (logic-only) finish is "
            f"{result.deterministic_finish_date} (about P{det_pct}). The risk-adjusted finish is most "
            f"likely {result.p50_date} (P50); {result.p80_date} at P80 and {result.p90_date} at P90 "
            f"carry progressively more contingency. The mean outcome is {result.mean_date} with a "
            f"standard deviation of {round(result.std_days, 1)} working days "
            f"({round(result.std_cal_days, 1)} calendar days). "
            f"{len(result.risks)} discrete risk/opportunity event(s) were modeled. The largest "
            f"duration-sensitivity driver is task {top_txt}."
        ),
        DocTable(
            ("Measure", "Value"),
            (
                (
                    "Focus event",
                    f"{result.target_uid} - {focus}" if result.target_uid is not None else focus,
                ),
                (
                    "Deterministic finish",
                    f"{result.deterministic_finish_date} (P{round(result.deterministic_percentile * 100, 1)})",
                ),
                ("P50 (most likely)", result.p50_date),
                ("P80", result.p80_date),
                ("P90", result.p90_date),
                ("Mean", result.mean_date),
                ("Std deviation (working days)", round(result.std_days, 1)),
                ("Std deviation (calendar days)", round(result.std_cal_days, 1)),
                ("Risk / opportunity events", len(result.risks)),
                ("Top sensitivity driver", top_txt),
            ),
        ),
        Paragraph(
            "Read the P-values as confidence levels: a P80 date has an approximately 80% modeled "
            "chance of being met. The deterministic finish typically sits well below P50, so the gap "
            "between them is the contingency the current logic does not yet carry.",
            lead="How to read this:",
        ),
    ]
    blocks += [
        Heading("How to set up this analysis (inputs)", level=1),
        Paragraph(
            "The forecast is driven entirely by the inputs below. Enter them on the Schedule Risk & "
            "Opportunity Analysis page, then run the Monte-Carlo. This section documents exactly what "
            "was used for this report so the analysis can be reviewed and reproduced."
        ),
        DocTable(
            ("Input", "How you enter it", "What it does"),
            (
                (
                    "Focus event",
                    "Type the task UID whose finish you want to forecast (blank = project finish).",
                    "Every result (S-curve, percentiles, sensitivity) is measured at this event's finish.",
                ),
                (
                    "Risk Ranking Factor (0-5)",
                    "Per task, in the grid or the 'Assign Risk Ranking Factor' box (one value, a list of "
                    "UIDs, or paste a whole column from Excel/MS Project).",
                    "0 = no duration uncertainty (uses the Remaining Duration as-is). 1-5 widen the "
                    "Best/Worst-case spread using the Risk Factors table below.",
                ),
                (
                    "Best / Worst-case duration",
                    "Auto-calculated from the factor (ML = current Remaining Duration), or type a value "
                    "to override.",
                    "Sets the low/high ends of each task's sampled duration range.",
                ),
                (
                    "Risk / Opportunity register",
                    "Add an event with a probability %, a schedule impact in days (positive = delay/risk, "
                    "negative = acceleration/opportunity), and the affected task UID(s).",
                    "On each iteration the event may fire and add its impact to the affected tasks.",
                ),
                (
                    "Occurrence mode",
                    "Choose 'Random each iteration' or 'Exact percentage overall'.",
                    "How often registered events fire across the run (see below).",
                ),
                (
                    "Correlation",
                    "0 to 1 (0 = independent; 0.3-0.5 typical).",
                    "Couples task durations so highs/lows do not fully cancel, widening the spread.",
                ),
            ),
        ),
        Heading("Risk Factors table (factor -> Best/Worst case)", level=2),
        Paragraph(
            "Best case = ML x (best%/100); Worst case = ML x (1 + add%/100), where ML is the "
            "task's current Remaining Duration. These are the percentages used for this report:"
        ),
        DocTable(
            ("Risk Ranking Factor", "% of ML (Best case)", "% add (Worst case)"),
            (
                ("0 (no uncertainty)", "0", "0"),
                *((f, f"{s:g}", f"{a:g}") for f, s, a in st.sra_factor_rows),
            ),
        ),
        Paragraph(_OCC_RANDOM, lead="Random each iteration:"),
        Paragraph(_OCC_EXACT, lead="Exact percentage overall:"),
    ]
    blocks += [
        Heading("Focus-finish results", level=1),
        Paragraph(
            "The simulated finish-date distribution of the focus event: the deterministic finish, the "
            "P10/P50/P80/P90 confidence dates, the mean, and the spread (standard deviation)."
        ),
        doc("Focus-finish results"),
    ]
    sc = _sra_chart_scurve(result)
    if sc is not None:
        blocks += [
            Heading("Finish-date confidence (S-curve)", level=2),
            sc,
            Paragraph(
                "Cumulative probability of finishing on or before each date (blue). The dashed amber "
                "line is the deterministic finish; the red dots mark P10/P50/P80/P90.",
                italic=True,
            ),
        ]
    hc = _sra_chart_hist(result)
    if hc is not None:
        blocks += [
            Heading("Finish-date distribution", level=2),
            hc,
            Paragraph(
                "How many of the simulated runs landed on each finish date (taller = more likely). The "
                "labelled bar is the single most-likely finish date.",
                italic=True,
            ),
        ]
    blocks += [
        Heading("Duration sensitivity (one-at-a-time)", level=1),
        Paragraph(
            "Each ranked activity's Best/Worst-case duration is swung independently to measure how far "
            "it can pull in (opportunity to accelerate, green) or push out (risk of delay, red) the "
            "focus finish. This deterministic one-at-a-time method is validated against the "
            "reference tool."
        ),
    ]
    tor = _sra_chart_tornado(oat)
    if tor is not None:
        ranked = sum(1 for o in oat if o.total_days > 0)
        scope = (
            f"Top {min(12, ranked)} of {ranked} ranked activities shown"
            if ranked > 12
            else "All ranked activities shown"
        )
        blocks += [
            tor,
            Paragraph(
                "Bars centred on zero: green extends left (acceleration), red right (delay); the "
                f"longest total swing sets the scale. {scope}; the full set is in the table below.",
                italic=True,
            ),
        ]
    blocks.append(doc("OAT sensitivity"))
    blocks.append(
        Paragraph(
            "Swings are measured on pure-logic CPM float; this tool does not consume the file's "
            "stored, progress-aware Critical flag (ADR-0010). A near-critical activity that a tool "
            "reading the stored float treats as driving can show a smaller delay-swing here, and "
            "vice-versa, so the mid/low ranking may differ slightly from such a tool even though the "
            "top drivers and the Best/Worst-case inputs agree.",
            lead="Float basis:",
        )
    )
    blocks += [
        Heading("Per-task Best/Worst-case durations", level=1),
        Paragraph(
            "The Risk Ranking Factor assigned to each ranked task and the Best/Worst-case durations "
            "derived from it (ML = current Remaining Duration), or entered manually."
        ),
        doc("Per-task durations"),
    ]
    blocks += [
        Heading("Risk / Opportunity register", level=1),
        Paragraph(
            "Discrete risks and opportunities, each with its probability, additive schedule impact, "
            "simulated occurrence count, and 1-5 probability/consequence ratings."
        ),
        doc("Risk register"),
    ]
    if result.branches:  # probabilistic branches shifted the percentiles → disclose them (ADR-0273)
        blocks += [
            Heading("Probabilistic branches", level=1),
            Paragraph(
                "Discrete rework events, each inserted onto an existing logic tie and firing with "
                "its own probability — modeling a failure/retest that delays the downstream work "
                "when it occurs. The table lists each branch's tie, 3-point rework duration, fired "
                "fraction, and mean finish impact (working days); a branch whose tie was absent is "
                "reported inert."
            ),
            doc("Probabilistic branches"),
        ]
    if (
        result.conditionals
    ):  # conditional branches shifted the percentiles → disclose them (ADR-0274)
        blocks += [
            Heading("Conditional branches", level=1),
            Paragraph(
                "Contingency switches: each iteration a condition on a monitored activity executes "
                "the primary Plan A or the contingency Plan B (falling back when the monitor runs "
                "late/long or early/short past the threshold). The table lists each switch's "
                "condition, the two plans, how often each plan won, and the mean finish impact of "
                "falling to the contingency (working days); a conditional whose monitor or a plan "
                "tie was absent is reported inert."
            ),
            doc("Conditional branches"),
        ]
    blocks += [
        Heading("Risk & Opportunity assessment matrices", level=1),
        Paragraph(
            "Each event is placed by its Likelihood of Occurrence (rows, 1-5) and Consequence/Benefit "
            "of Occurrence (columns, 1-5). Each cell shows the NASA priority rank (1-25) and, in "
            "parentheses, the count of events that land there."
        ),
        Heading("Risk Assessment Matrix", level=2),
        _sra_matrix_chart(result, opportunity=False),
        Heading("Opportunity Assessment Matrix", level=2),
        _sra_matrix_chart(result, opportunity=True),
    ]
    blocks += [
        Heading("Methodology & assumptions", level=1),
        Paragraph(
            "Best/Worst-case durations use ML = the current Remaining Duration; "
            "BC = ML x (best%/100), WC = ML x (1 + add%/100) with the per-factor percentages "
            f"from the Risk Factors table. Occurrence mode: {result.occurrence_mode}. Correlation: "
            f"{result.correlation:g}. Risk register: {'on' if result.used_risks else 'off'}. "
            f"Sampling: {result.sampling}. Probabilistic branches: "
            f"{len(result.branches) if result.branches else 'none'}"
            f"{' (discrete rework on a logic tie; see the Probabilistic branches table)' if result.branches else ''}. "
            f"Conditional branches: {len(result.conditionals) if result.conditionals else 'none'}"
            f"{' (contingency switching; see the Conditional branches table)' if result.conditionals else ''}. "
            "Consequence (1-5) is auto-rated from the schedule impact via the NASA Schedule guideline "
            "(impact days converted to calendar months: <1 week=1, 1 week to <1 month=2, 1 to "
            "<3 months=3, 3 to <=6 months=4, >6 months=5)."
        ),
        Paragraph(
            "The Best/Worst-case derivation and the deterministic one-at-a-time sensitivity are "
            "validated against the reference tool. The stochastic distribution (S-curve, histogram, "
            "percentiles) uses a standard-library random generator that is statistically "
            "representative but NOT bit-identical to the reference tool's, so treat the P-values as "
            "close, not exact "
            # the exported exhibit's locality sentence follows the OBSERVED banner (DoD 001b):
            # the unconditional assurance may only print while every constructible AI candidate
            # is provably local — the SRA numbers themselves are engine-computed either way.
            + (
                "(ADR-0005/0106). All computation is local and offline; this document carries "
                "the CUI marking in its header and footer."
                if not _observed_banner(st).cloud_active
                else "(ADR-0005/0106). All SRA computation in this document is local and "
                "offline; NOTE — this session's AI backend is configured for a non-local "
                "endpoint, so AI-generated prose elsewhere in the session may have transited "
                "an external service. This document carries the CUI marking in its header and "
                "footer."
            ),
            italic=True,
        ),
    ]
    return blocks


_OCC_RANDOM = (
    "When this option is selected, the probability of risks/opportunities occurring is evaluated "
    "independently on each iteration of the SRA using the entered probability of occurrence. Over "
    "many iterations the average result will be close to the entered percentage, but the exact "
    "number of occurrences may vary each time you run the SRA."
)
_OCC_EXACT = (
    "When this option is selected, the total number of times a given risk/opportunity occurs is "
    "determined at the beginning of the SRA process based on the entered probability and the total "
    "number of SRA iterations chosen. That total is then randomly distributed across the iterations, "
    "so the risk/opportunity occurs the exact expected number of times overall."
)


def _ssi_panel(st: SessionState, *, prov: str = "", tools: str = "", export_attr: str = "") -> str:
    """The SSI Schedule Risk & Opportunity Analysis controls (ADR-0123): focus event, Risk Factors
    table + per-task ranking + auto-calc, occurrence/correlation run options, the risk register, and
    the run/sensitivity buttons feeding ``/api/sra/ssi`` and ``/api/sra/oat`` (run off page-load).

    Panel contract (ADR-0339). The take quotes the two counts the panel ALREADY renders as a
    ``<p class=muted>`` further down, so it re-states a figure the reader can verify in place
    rather than introducing one; it reads correctly at zero (an unranked schedule).
    """
    # field help for the JS-rendered SRA tables (run results + OAT sensitivity) — same hover call-out
    field_help_json = json.dumps(
        field_help_payload(
            (
                "risk_ranking_factor",
                "bc_duration",
                "wc_duration",
                "ml_duration",
                "opportunity_accelerate",
                "risk_of_delay",
                "total_sensitivity",
                "deterministic_finish",
                "mean_finish",
                "std_dev_finish",
                "eac",
                "scl",
                "ccl",
                "jcl",
            )
        )
    ).replace("<", "\\u003c")
    factor_rows = "".join(
        f"<tr><td>{f}</td>"
        f'<td><input type=number name=sub{f} min=0 max=100 step=1 value="{s:g}" style="width:60px"></td>'
        f'<td><input type=number name=add{f} min=0 max=300 step=1 value="{a:g}" style="width:60px"></td></tr>'
        for f, s, a in st.sra_factor_rows
    )
    rand_ck = " checked" if st.sra_occurrence_mode == "random_each" else ""
    exact_ck = " checked" if st.sra_occurrence_mode == "exact_overall" else ""
    mc_ck = " checked" if st.sra_sampling != "lhs" else ""
    lhs_ck = " checked" if st.sra_sampling == "lhs" else ""
    centered_ck = " checked" if st.sra_lhs_centered else ""
    iters = "".join(
        f'<option value="{n}"{" selected" if n == 1000 else ""}>{n}</option>'
        for n in (500, 1000, 2000, 5000)
    )
    ranked, bcwc = len(st.sra_factors), len(st.sra_bcwc)
    ssi_head = _panel_head("Schedule Risk &amp; Opportunity Analysis", tools=tools, prov=prov)
    ssi_take = (
        f"<p class=sf-take data-no-i18n>{ranked} task{'' if ranked == 1 else 's'} ranked; "
        f"{bcwc} with calculated Best/Worst durations.</p>"
    )
    return f"""
<div class=panel{export_attr}>{ssi_head}{ssi_take}
<p class=muted>Rank each task 1&ndash;5 (Risk Ranking Factor), auto-calculate
its Best/Worst Case from the factor table, attach discrete risks with an additive schedule impact in
days, and run a Monte-Carlo to a chosen <b>focus event</b>. The current Remaining Duration is the Most
Likely. <b>Best/Worst Case and the deterministic sensitivity are validated against the reference
tool</b>; the random distribution is statistically close, not bit-identical (a different RNG,
ADR-0005).</p>
<form action="/sra/ssi-run-config" method=post class=viz-controls>
<label>Focus event UID <input type=number name=focus_uid min=1 value="{st.sra_focus_uid or ""}"
 placeholder="project finish"></label>
<label title="{_e(_OCC_RANDOM)}"><input type=radio name=occurrence_mode value=random_each{rand_ck}>
 Random each iteration &#9432;</label>
<label title="{_e(_OCC_EXACT)}"><input type=radio name=occurrence_mode value=exact_overall{exact_ck}>
 Exact percentage overall &#9432;</label>
<label title="Blanket correlation between the task duration distributions (0 = independent; 0.3&ndash;0.5 typical) — offsets the cancelling of extreme high/low results.">Correlation
 <input type=number name=correlation min=0 max=1 step=0.05 value="{st.sra_correlation:g}" style="width:60px"></label>
<label title="Monte-Carlo draws each iteration independently at random.">
 <input type=radio name=sampling value=mc{mc_ck}> Monte-Carlo &#9432;</label>
<label title="Latin Hypercube stratifies the draws (one sample per equal-probability band per input), converging to the same distribution in far fewer iterations.">
 <input type=radio name=sampling value=lhs{lhs_ck}> Latin Hypercube &#9432;</label>
<label title="Centered LHS uses each stratum's midpoint (fully deterministic, no within-band jitter) — a smoother curve at low iteration counts.">
 <input type=checkbox name=lhs_centered value=on{centered_ck}> Centered &#9432;</label>
<label><input type=checkbox name=use_risks value=on{" checked" if st.sra_use_risk_register else ""}>
 Use risk register</label>
<button type=submit>Save run options</button></form>
<details class=explainer><summary><b>What is Correlation, and what value should I use?</b> (with examples &amp; pros/cons)</summary>
<p><b>What it is.</b> A single <b>blanket correlation</b> (0&ndash;1) that ties the task duration draws
together in the Monte-Carlo. At <b>0</b> every task's duration is sampled <i>independently</i>. At a
positive <b>r</b>, when one task draws toward its worst case the others tend to as well (and toward best
case together) &mdash; modelling a <b>common cause</b> (a shared crew, the weather, one vendor, a single
test rig) that pushes many activities the same direction at once.</p>
<p><b>Why it matters &mdash; the "cancelling" trap.</b> With <i>independent</i> draws, one task's high
swing is offset by another's low swing, so across a big schedule the extremes cancel (the central-limit
effect) and the simulated finish distribution comes out <b>too narrow</b>. That <u>understates</u> the
real spread and gives a <b>falsely optimistic</b> P50/P80. Real programs have systemic drivers, so
durations <i>are</i> correlated; adding correlation <b>widens and fattens the tails</b> of the finish
distribution for a more honest confidence.</p>
<p><b>How to choose the value.</b></p>
<ul>
<li><b>0</b> &mdash; independent. Only defensible if tasks are genuinely unrelated (rare on one program).</li>
<li><b>0.3&ndash;0.5</b> &mdash; the <b>typical, recommended</b> range (GAO/NASA SRA guidance leans here).
Start around <b>0.3&ndash;0.4</b>.</li>
<li><b>0.6&ndash;0.9</b> &mdash; strongly coupled work (one team/resource/site driving most tasks).</li>
<li><b>1.0</b> &mdash; perfect lockstep (every task moves together); usually too extreme.</li>
</ul>
<p><b>Example 1 (shared driver).</b> A 200-task program where most work flows through one integration
team. Independent run &rarr; P80 = +12 days; at <b>r&nbsp;=&nbsp;0.4</b> the P80 widens to +28 days,
because the shared team makes slips <i>compound</i> instead of cancel &mdash; the 0.4 number is the
defensible one. <b>Example 2 (truly separate).</b> Two unrelated subprojects with their own teams and
funding &rarr; <b>r&nbsp;=&nbsp;0</b> (or a low 0.1&ndash;0.2); forcing high correlation would overstate
the spread.</p>
<p><b>Pros of using it.</b> A realistic, wider, fatter-tailed finish distribution; avoids the false
precision of independent draws; aligns with GAO/NASA practice; yields defensible contingency / P-values.
<b>Cons of using it.</b> It's one blanket value &mdash; it can't say <i>which</i> task pairs are actually
correlated (a full correlation matrix could, but needs far more elicitation); set too high it overstates
risk; the "right" number is a judgement call, so document your rationale.</p>
<p><b>Not using it (r&nbsp;=&nbsp;0).</b> <b>Pro:</b> simplest, and correct when tasks really are
independent. <b>Con:</b> on a real project it almost always <u>understates</u> schedule risk (the
cancelling effect) and reads falsely optimistic &mdash; not recommended for a forecast you intend to
defend.</p>
<p class=muted>Mechanics: a single-factor Gaussian copula (one shared draw per iteration), std-lib only;
risk firing is a separate stream, and <b>r&nbsp;=&nbsp;0 reproduces the independent run exactly</b>.</p></details>
<details class=explainer><summary><b>Monte-Carlo vs Latin Hypercube &mdash; which sampler should I use?</b></summary>
<p><b>What they are.</b> Both run the <i>same</i> model &mdash; the same three-point durations, the same
correlation, the same risk register &mdash; and differ only in <b>how the random draws are chosen</b>.
<b>Monte-Carlo (MC)</b> draws every iteration purely at random. <b>Latin Hypercube (LHS)</b> divides each
input's probability range into <i>N</i> equal-probability bands (one per iteration) and takes exactly one
draw from each band, then shuffles which band pairs with which across inputs. Every region of the
distribution &mdash; especially the tails &mdash; is guaranteed representation instead of being left to
chance.</p>
<p><b>Why it matters.</b> Pure MC can clump: by luck a 1,000-run may over-sample the middle and miss the
extreme tail, so the P80/P90 wobble from run to run. LHS removes that clumping, so the percentiles
<b>converge to the same answer in far fewer iterations</b> (commonly several-fold tighter for the same
count). The distribution it converges to is <b>identical</b> to MC's &mdash; LHS is a variance-reduction
technique, not a different model, so it never changes the honest answer, only how fast you reach it.</p>
<p><b>Centered.</b> Off (default): the one draw inside each band is random, so repeated runs vary slightly
but average out. On: each band contributes its <b>midpoint</b> &mdash; fully deterministic and the smoothest
curve at low iteration counts, at the cost of never sampling the very edge of a band.</p>
<ul>
<li><b>Monte-Carlo</b> &mdash; the classic, matches the reference-tool convention; use it when you want the
textbook method or are reconciling against another tool's MC run.</li>
<li><b>Latin Hypercube</b> &mdash; <b>recommended</b> when you want stable P-values at a lower iteration
count (large schedules, quick what-ifs); same distribution, less noise.</li>
</ul>
<p class=muted>Mechanics: LHS stratifies on a dedicated, disjoint RNG stream, then feeds the same
Gaussian-copula composition (LHS-then-Cholesky under a correlation matrix), std-lib only. With no
uncertainty anywhere it falls back to the deterministic finish exactly like MC.</p></details>
<h3>Risk Factors table</h3>
<form action="/sra/factor-table" method=post>
<table style="width:auto"><tr><th>Factor</th><th>% of ML (Best Case)</th><th>% add (Worst Case)</th></tr>
{factor_rows}</table><button type=submit>Save factor table</button></form>
<h3>Assign Risk Ranking Factor &amp; calculate Best/Worst durations</h3>
<form action="/sra/factor" method=post class=viz-controls>
<label>UIDs <input type=text name=uids placeholder="101, 102 205"></label>
<label title="0 = no Best/Worst uncertainty (use the remaining duration as-is); 1-5 widen the Best/Worst spread.">Factor (0&ndash;5) <input type=number name=factor min=0 max=5 value=3 style="width:56px"></label>
<button type=submit>Set factor</button></form>
<p class=muted>{len(st.sra_factors)} task(s) ranked; {len(st.sra_bcwc)} have calculated Best/Worst durations.</p>
<form action="/sra/auto-calc" method=post style="display:inline"><input type=hidden name=scope value=all>
<button type=submit>Calculate SRA Durations — all</button></form>
<form action="/sra/auto-calc" method=post style="display:inline;margin-left:8px"><input type=hidden name=scope value=selected>
<input type=text name=uids placeholder="selected UIDs" style="width:150px">
<button type=submit>Calculate — selected</button></form>
{_unified_risk_section(st)}
{_branch_section(st)}
{_conditional_section(st)}
<h3>Editable schedule grid</h3>
<p class=muted>The whole schedule as a spreadsheet-style grid: type a <b>Risk Ranking Factor</b> (0&ndash;5) or
edit <b>Best/Worst Case</b> days inline, and pick the <b>focus</b> event with the radio. <b>Factor 0
means no duration uncertainty</b> &mdash; no Best/Worst case, the remaining duration is used as-is;
1&ndash;5 widen the Best/Worst spread. A factor auto-fills Best/Worst from the table above; an explicit
Best/Worst entry is a manual override.
<b>Paste from Excel / MS&nbsp;Project:</b> copy a whole column (or a Factor/BC/WC block) and paste it
onto the first cell to fill the column down across every task in one go. Edits queue until you press
<b>Save grid</b>. Summary rows are bold and not editable.</p>
<div class=viz-controls>
<label>Zoom <input id=ssiGridZoom type=range min=0.4 max=6 step=0.2 value=1.4></label>
<button id=ssiGridFit type=button class=linkbtn title="Auto-scale the timeline so the whole project fits">View entire project</button>
<label><input id=ssiShowDone type=checkbox checked> show completed tasks</label>
<label>Find <input id=ssiFind type=text placeholder="UID or name…" title="Jump to a UniqueID, or mark every grid task whose row contains this text"></label>
<span id=ssiFindStatus class=muted aria-live=polite></span>
<label title="Show the start/finish dates at the ends of the Gantt bars (MS Project bar text)"><input id=ssiBarDates type=checkbox> dates on bars</label>
<label title="Tint each Gantt bar by its Criticality Index from the last SRA run — the fraction of Monte-Carlo iterations the activity landed on the critical path under uncertainty (the risk-critical view, Hulett). Run the SRA first to populate it."><input id=ssiTintCrit type=checkbox> tint by criticality</label>
<span id=ssiTintLegend class="muted ci-legend" aria-live=polite></span>
<button id=timescaleBtn type=button title="Modify the timescale: tiers, units (years to hours), labels, count, alignment, fiscal year, tick lines, size and non-working-time shading (like Microsoft Project)">Timescale&hellip;</button>
<label>Group by <select id=ssiGridGroupBy data-no-i18n title="Group the grid rows under headers by any field — WBS, resources, critical, outline level, or any custom field (like the Path pages)">
<option value="">(none)</option>
<option value=wbs>WBS</option>
<option value=resource_names>Resources</option>
<option value=is_critical>Critical</option>
<option value=is_milestone>Milestone</option>
<option value=outline_level>Outline level</option>
</select></label>
<button id=ssiGridReload type=button>Refresh grid</button>
<button id=ssiGridSave type=button>Save grid</button>
<span id=ssiGridStatus class=muted aria-live=polite></span></div>
<div id=ssiGrid class=sra-grid-host></div>
<div class=viz-controls style="margin-top:12px">
<label>Iterations <select id=ssiIters>{iters}</select></label>
<label>Distribution <select id=ssiDist data-no-i18n><option value=triangular>Triangular</option>
<option value=pert>Beta-PERT</option></select></label>
<button id=ssiRun type=button>Run SRA</button>
<button id=ssiOat type=button title="Deterministic one-at-a-time Best/Worst swing on the focus event (2xN CPM solves)">Run sensitivity</button></div>
<p id=ssiStatus class=muted aria-live=polite></p>
<div id=ssiResult></div>
<div id=ssiConclusions class=sra-conclusions data-no-i18n></div>
<div id=ssiCharts class=ssi-charts></div>
<div id=ssiMatrices class=ssi-matrices></div>
<p class=muted style="font-size:11px">Tip: each chart and matrix has its own toolbar (full screen, zoom in/out, reset) to enlarge or shrink it, and hovering any point, bar, or matrix cell calls out its values (a matrix cell lists the risks that land there).</p>
<h3>Sensitivity — deterministic one-at-a-time (OAT)</h3>
<p class=muted style="font-size:11px">Swings are measured on <b>pure-logic CPM float</b> (this tool does not consume the file's stored, progress-aware Critical flag &mdash; ADR-0010). A near-critical activity that a tool reading the stored float treats as driving can therefore show a smaller delay-swing here, and vice-versa, so the mid/low ranking may differ slightly versus a stored-float tool while the top drivers agree.</p>
<div id=ssiOatOut></div>
<h3>Save / load setup &amp; export</h3>
<div class=viz-controls>
<form action="/sra/load-from-schedule" method=post style="display:inline">
<button type=submit title="Seed the grid from the schedule's OWN stored fields ('SRA Risk Ranking Factors' + Best/Worst Case Duration) — the same values SSI reads. Replaces the current factors and Best/Worst pairs.">Load from schedule</button></form>
<a class=btn href="/sra/ssi/save" download>Save setup (JSON)</a>
<form action="/sra/ssi/load" method=post enctype="multipart/form-data" style="display:inline">
<label>Load setup <input type=file name=setup accept="application/json,.json"></label>
<button type=submit>Load</button></form>
<a class=btn href="/export/xlsx/sra">Export tables (Excel)</a>
<a class=btn href="/export/docx/sra" title="A full PM-level SRA report: summary, S-curve, distribution, sensitivity tornado, risk register, and the 5x5 matrices as embedded graphics.">Download SRA report (Word)</a>
<a class=btn href="/export/xlsx/sra-registry">Download risk registry (Excel)</a>
<a class=btn href="/export/docx/sra-registry">Risk registry (Word)</a></div>
<h3>Excel fill-in templates (export &rarr; edit &rarr; re-import)</h3>
<p class=muted>Download a pre-formatted Excel workbook, fill it in offline, and re-import it &mdash; a
faster way to build the register or rank many tasks than the forms above. The <b>Risk Register</b>
template carries a read-only task-reference sheet (valid UIDs + names); the <b>Task Risk</b> template
has one row per activity. On re-import, unmatched UIDs are dropped and an inverted Best/Worst pair is
skipped &mdash; nothing is fabricated, and you get a summary of exactly what landed.</p>
{_user_tip("Re-importing the Risk Register REPLACES the whole register; re-importing Task Risk UPDATES only the rows you filled in (blank cells are left untouched). Both round-trip the same figures the forms above use.")}
<div class=viz-controls>
<a class=btn href="/export/xlsx/risk-register-template" download>Risk Register template (Excel)</a>
<form action="/sra/import/risk-register" method=post enctype="multipart/form-data" style="display:inline">
<label>Import filled register <input type=file name=file accept=".xlsx" required></label>
<button type=submit>Import</button></form></div>
<div class=viz-controls style="margin-top:6px">
<a class=btn href="/export/xlsx/task-risk-template" download>Task Risk template (Excel)</a>
<form action="/sra/import/task-risk" method=post enctype="multipart/form-data" style="display:inline">
<label>Import filled task risk <input type=file name=file accept=".xlsx" required></label>
<button type=submit>Import</button></form></div>
<script id=sfFieldHelp type="application/json">{field_help_json}</script>
<script src="/static/gantt.js"></script><script src="/static/sra_ssi.js"></script>
<script src="/static/sra_grid.js"></script></div>"""  # nosec B608 (HTML, not SQL)


def _correlation_matrix_panel(
    st: SessionState, *, prov: str = "", tools: str = "", export_attr: str = ""
) -> str:
    """The correlation-matrix editor (ADR-0270): pairwise correlations + shared-driver groups
    over the uncertain activities, a clear control, and a post-run feasibility badge host. A
    non-empty matrix overrides the blanket scalar correlation and drives a multivariate copula.

    Panel contract (ADR-0339). The take counts what is entered and names which correlation is
    therefore driving the run — the fact that actually changes the answer — so it stays true on
    an empty matrix (the blanket scalar) as well as a populated one.
    """
    pairs = st.sra_corr_pairs
    groups = st.sra_corr_groups
    rows = ""
    for a, b, r in pairs:
        rows += f"<tr><td>pair</td><td>{a} &harr; {b}</td><td>{r:g}</td></tr>"
    for members, r in groups:
        ids = ", ".join(str(u) for u in members)
        rows += f"<tr><td>group</td><td>{_e(ids)}</td><td>{r:g}</td></tr>"
    if pairs or groups:
        listing = (
            "<table><tr><th>Kind</th><th>Activities (UID)</th><th>&rho;</th></tr>"
            f"{rows}</table>"
            '<form action="/sra/correlation-matrix" method=post style="display:inline">'
            "<input type=hidden name=action value=clear>"
            "<button type=submit>Clear all correlations</button></form>"
        )
    else:
        listing = (
            "<p class=muted>No correlation matrix entered &mdash; the blanket scalar correlation "
            "above drives the run.</p>"
        )
    n_pairs, n_groups = len(pairs), len(groups)
    corr_head = _panel_head("Correlation matrix (advanced)", tools=tools, prov=prov)
    driver = (
        "this matrix overrides the blanket scalar"
        if (pairs or groups)
        else f"the blanket scalar &rho;&nbsp;=&nbsp;{st.sra_correlation:g} drives the run"
    )
    corr_take = (
        f"<p class=sf-take data-no-i18n>{n_pairs} pairwise correlation"
        f"{'' if n_pairs == 1 else 's'} and {n_groups} shared-driver group"
        f"{'' if n_groups == 1 else 's'} entered &mdash; {driver}.</p>"
    )
    return f"""
<div class=panel{export_attr}>{corr_head}{corr_take}
<p class=muted>Beyond the single blanket correlation above, enter <b>pairwise</b> correlations
between specific activities, or <b>shared-driver groups</b> (activities with a common cause &mdash;
one crew, one vendor, one test rig &mdash; that move together, the Hulett risk-driver idea). A
non-empty matrix <b>OVERRIDES</b> the blanket scalar for the run and drives a multivariate Gaussian
copula over the uncertain (spread-bearing) activities. Pairwise &rho; may be <b>negative</b> (unlike
the 0&ndash;1 blanket); strong mutual negatives can be jointly infeasible, in which case the run
repairs to the nearest valid correlation matrix and says so below (never silently). Not bit-exact
vs commercial tools (ADR-0005/0106).</p>
{listing}
<h3>Add a pairwise correlation</h3>
<form action="/sra/correlation-matrix" method=post class=viz-controls>
<input type=hidden name=action value=add-pair>
<label>UID A <input type=number name=uid_a min=1 step=1></label>
<label>UID B <input type=number name=uid_b min=1 step=1></label>
<label>&rho; (&minus;1&hellip;1) <input type=number name=rho min=-1 max=1 step=any></label>
<button type=submit>Add pair</button></form>
<h3>Add a shared-driver group</h3>
<form action="/sra/correlation-matrix" method=post class=viz-controls>
<input type=hidden name=action value=add-group>
<label>UIDs <input type=text name=uids placeholder="101, 102, 205"></label>
<label>&rho; (&minus;1&hellip;1) <input type=number name=group_rho min=-1 max=1 step=any></label>
<button type=submit>Add group</button></form>
<div id=corrBadge></div></div>"""


def _jcl_panel(st: SessionState, *, prov: str = "") -> str:
    """The Joint Cost-&-Schedule Confidence (JCL / FICSM) panel (ADR-0269), gated on a
    cost-loaded file (the same non-summary Σ budgeted_cost > 0 rule as the cost EVM
    indices). A duration-only file renders the honest requirement note — never a number.

    Panel contract (ADR-0339). This is the ONE panel that builds its own tool strip instead of
    taking the page's: the JCL sheets ride ``/export/xlsx/sra`` only once the file is cost-loaded,
    so on a duration-only file ⤓ EXCEL would point at a workbook that carries no JCL data. The
    rank-3 law is "never a dead OR LYING link", so the ⤓ is gated on the same ``loaded`` flag the
    panel's own body is — head, ⛶ and chip stay either way. The take likewise refuses to imply a
    number the gate forbids: unloaded, it states the SCL/JCL distinction rather than a confidence.
    """
    chosen = _sra_selected(st)
    scoped = chosen[1] if chosen is not None else None
    loaded = scoped is not None and cost_loaded_total(scoped) > 0.0
    tools = _shell_tools(export_title=_SRA_XLSX_TITLE if loaded else "")
    if loaded:
        take = (
            f"<p class=sf-take data-no-i18n>Cost-loaded &mdash; the joint run is available, and "
            f"its frontier is drawn at your {st.jcl_confidence * 100:g}% confidence target.</p>"
        )
    elif scoped is None:
        take = (
            "<p class=sf-take data-no-i18n>No analyzable version selected &mdash; the joint run "
            "needs a schedule whose CPM solves.</p>"
        )
    else:
        take = (
            "<p class=sf-take data-no-i18n>No budgeted cost on this file &mdash; a run here "
            "would be a schedule-only confidence level (SCL), never a JCL.</p>"
        )
    head = (
        f"<div class=panel{_SRA_EXPORT if loaded else ''}>"
        + _panel_head("Joint Cost-&amp;-Schedule Confidence (JCL / FICSM)", tools=tools, prov=prov)
        + take
        + "<p class=muted>The probability of finishing <b>at or below a target cost AND on or "
        "before a target date</b>, from one joint Monte-Carlo (NASA NPR&nbsp;7120.5F / CEH "
        "App.&nbsp;J; the policy anchor is ~70%). The cost dimension rides the <i>same</i> "
        "sampled durations as the SSI run above — time-dependent cost burns at each "
        "activity's budget rate over its <i>sampled</i> remaining duration (the "
        "NASA/Hulett integrated method, ADR-0269) — so the football chart's schedule axis "
        "is exactly the SSI S-curve. It uses the SSI panel's focus event, factors, risk "
        "register, correlation, distribution, and probabilistic &amp; conditional branches "
        "(ADR-0408 — a branch's rework fragnet carries no budget, so it moves the finish "
        "axis only, never the cost axis); only the cost settings below are its own.</p>"
    )
    if not loaded:
        return (
            head + '<div class="notice warn" role=note><b>Needs a cost-loaded schedule.</b> '
            "This file carries no budgeted cost, so a run here would be a <b>schedule-only</b> "
            "confidence level (SCL) and must not be labeled JCL (NASA CEH App.&nbsp;J; "
            "ADR-0106). Load a schedule with task budgets — the same gate as the cost-based "
            "EVM indices — and this panel runs the full joint simulation.</div></div>"
        )
    tgt_date = _e(st.jcl_target_date or "")
    tgt_cost = "" if st.jcl_target_cost is None else f"{st.jcl_target_cost:g}"
    td_pct = f"{st.jcl_td_share * 100:g}"
    cl_pct = f"{st.jcl_cost_low * 100:g}"
    cm_pct = f"{st.jcl_cost_ml * 100:g}"
    ch_pct = f"{st.jcl_cost_high * 100:g}"
    conf_pct = f"{st.jcl_confidence * 100:g}"
    unc_off = st.jcl_cost_low == 1.0 and st.jcl_cost_ml == 1.0 and st.jcl_cost_high == 1.0
    screening = (
        '<div class="notice warn" role=note><b>Screening setup.</b> Cost uncertainty is '
        "duration-driven only (multipliers 100/100/100 = off) with a 100%-time-dependent "
        "default (&tau;); a defensible decision-point JCL needs elicited cost ranges "
        "(GAO). Blank targets use the run's deterministic finish / EAC.</div>"
        if unc_off and st.jcl_td_share == 1.0
        else '<div class="notice ok" role=note>Using your cost settings. Blank targets use '
        "the run's deterministic finish / EAC.</div>"
    )
    iters = "".join(
        f'<option value="{n}"{" selected" if n == 1000 else ""}>{n}</option>'
        for n in (500, 1000, 2000, 5000)
    )
    return f"""{head}
{screening}
<form action="/sra/jcl-config" method=post class=viz-controls>
<label>Target date <input type=date name=target_date value="{tgt_date}"></label>
<label>Target cost <input type=number name=target_cost min=0 step=any value="{tgt_cost}"
 placeholder="deterministic EAC"></label>
<label title="The share of every remaining budget that burns with time (labor); the rest is time-independent (materials / fixed price). 100% is the labor-dominant screening default.">TD share %
 <input type=number name=td_share min=0 max=100 step=1 value="{td_pct}" style="width:60px"></label>
<label title="FICSM cost-estimating uncertainty: a triangular multiplier on each incomplete activity's remaining cost. 100/100/100 = off (duration-driven cost only); supply elicited values for a real range.">Cost low/ml/high %
 <input type=number name=cost_low min=10 max=150 step=1 value="{cl_pct}" style="width:56px">
 <input type=number name=cost_ml min=50 max=150 step=1 value="{cm_pct}" style="width:56px">
 <input type=number name=cost_high min=100 max=300 step=1 value="{ch_pct}" style="width:56px"></label>
<label title="The joint confidence the frontier line is drawn at (NASA policy anchor 70%).">Confidence %
 <input type=number name=confidence min=10 max=95 step=1 value="{conf_pct}" style="width:56px"></label>
<button type=submit>Save JCL settings</button>
<button type=submit name=reset value=1>Reset defaults</button></form>
<div class=viz-controls>
<label>Iterations <select id=jclIters>{iters}</select></label>
<button id=jclRun type=button>Run JCL</button></div>
<p id=jclStatus class=muted aria-live=polite></p>
<div id=jclSummary></div>
<div id=jclCharts class=ssi-charts></div>
<p class=muted style="font-size:11px">The JCL sheets (headline, frontier, joint sample) ride the
SRA Excel export above once the file is cost-loaded. Each chart has the shared toolbar (full
screen, zoom) and hover call-outs.</p>
<script src="/static/sra_jcl.js"></script></div>"""


def _sra_explainers(*, prov: str = "") -> str:
    """Detailed, example-rich "which model, and when" guidance for the SRA page: the two Monte-Carlo
    models the tool offers (SSI additive vs legacy multiplicative) and JCL — what each does, its
    pros/cons, and when to reach for it. Collapsible so it never crowds the working controls.

    Panel contract (ADR-0339), with NO ⤓ EXCEL: this panel is guidance prose — it holds no figure
    the SRA workbook could carry, so offering an export would be a lying link (rank-3). It builds
    its own ⛶-only strip rather than taking the page's ⤓-bearing one.
    """
    head = _panel_head(
        "Which risk model should I use? (pros, cons &amp; examples)",
        tools=_shell_tools(),
        prov=prov,
    )
    return f"""
<div class=panel>{head}
<p class=sf-take data-no-i18n>Three models compared below &mdash; SSI additive-days, the legacy
multiplicative risk-driver Monte-Carlo, and joint cost+schedule (JCL).</p>
<p class=muted>This page offers two schedule risk models. They answer the same question &mdash; "how
confident am I in the finish?" &mdash; with different math. Open each below. JCL is explained too, so
it is clear why a cost+schedule confidence is a separate thing.</p>
<details class=explainer><summary><b>SSI Schedule Risk &amp; Opportunity</b> &mdash; additive days, focus event (the top model)</summary>
<p><b>What it does.</b> Each task gets a <b>Best / Worst Case</b> duration &mdash; either from a 1&ndash;5
<b>Risk Ranking Factor</b> (e.g. factor&nbsp;3 = Best&nbsp;&minus;30% / Worst&nbsp;+30% of the remaining
duration) or from Best/Worst days you type. A Monte-Carlo samples each task between those bounds and
reports the <b>finish-date confidence of a chosen focus event</b> (e.g. "Ready to Ship"). Discrete
<b>risks add a fixed number of days</b> to the tasks they hit when they fire.</p>
<p><b>Pros.</b> Mirrors SSI Tools' SRA workflow (factor table, focus event, additive risks); intuitive
for SMEs who think "this task could run X&ndash;Y days"; the focus-event curve answers "how likely is
<i>this milestone</i> by date&nbsp;D?"; the deterministic facts (all-most-likely finish, one-at-a-time
sensitivity) validate against SSI to a fraction of a day.</p>
<p><b>Cons.</b> An additive day impact is a fixed count, not scaled to task size; the stochastic
distribution is statistically close to SSI but <i>not bit-identical</i> (different RNG, ADR-0005); you
must supply factors / Best-Worst durations and day-based risks.</p>
<p><b>When to use.</b> You want the SSI-style milestone confidence and risk register, and your SMEs give
you factors or best/worst durations and discrete risks measured <b>in days</b>.</p>
<p class=muted><b>Example.</b> Focus = "Ready to Ship". Set factor&nbsp;3 on the integration tasks, add a
risk "Late castings" 40% likely / <b>+20 days</b> on UIDs&nbsp;101,&nbsp;102. Run &rarr; P50/P80 finish
for the milestone and a tornado of which tasks drive the date.</p></details>
<details class=explainer><summary><b>Legacy Monte-Carlo</b> &mdash; multiplicative risk drivers (GAO/AACE/Hulett)</summary>
<p><b>What it does.</b> Samples each activity's duration from a triangular/PERT distribution (a global
"Min&nbsp;90% / ML&nbsp;100% / Max&nbsp;110%" default, or your per-activity 3-point), optionally fires
discrete <b>risks that MULTIPLY</b> the duration of the tasks they hit (e.g. 1.0&nbsp;/&nbsp;1.2&nbsp;/
&nbsp;1.5), and recomputes the whole project finish each iteration.</p>
<p><b>Pros.</b> The canonical <b>risk-driver</b> method (GAO Schedule Assessment Guide / AACE / Hulett);
percentage impacts <b>scale with task size</b> (a 20% slip is 20% on a 10-day or a 100-day task); one
risk mapped to several tasks <b>correlates</b> them automatically (the shared-driver correlation, no
coefficient needed); a clean project-finish confidence curve.</p>
<p><b>Cons.</b> Oriented to the <b>project</b> finish rather than a chosen milestone; multiplicative
thinking is less intuitive than "add N days"; the auto 90&ndash;100&ndash;110 default is a
<b>screening default, not SME-validated</b> (supply elicited ranges for a real run).</p>
<p><b>When to use.</b> You want the classic risk-driver Monte-Carlo for the overall project finish, with
<b>percentage</b> impacts and automatic shared-driver correlation.</p>
<p class=muted><b>Example.</b> Keep the global 90&ndash;100&ndash;110, add a risk "Permit delay" 40% likely /
100&ndash;120&ndash;150% on the permit tasks &rarr; the S-curve shows project-finish confidence and the
risk-driver tornado ranks each risk by the mean slip it causes.</p></details>
<details class=explainer><summary><b>JCL (Joint Confidence Level)</b> &mdash; why cost+schedule is a separate thing</summary>
<p><b>What it is.</b> A <b>joint cost-AND-schedule</b> confidence: the probability of finishing at or
below a given <b>cost</b> <i>and</i> on or before a given <b>date</b>, from a cost-loaded, risk-loaded
schedule (NASA NPR&nbsp;7120.5 / CEH Appendix&nbsp;J; the policy target is typically <b>~70%</b>).</p>
<p><b>Requirement.</b> A <b>cost-loaded</b> schedule (a budget and actuals on the tasks). Without cost, a
duration-only run is a <b>Schedule</b> Confidence Level (SCL) only &mdash; it must <u>not</u> be called a
JCL.</p>
<p><b>Pros.</b> The integrated cost+schedule risk picture agencies require at major milestones; ties
reserve (cost contingency + schedule margin) to a confidence target; captures cost/schedule
correlation that a schedule-only run cannot.</p>
<p><b>Cons.</b> Needs trustworthy cost loading and cost-risk inputs; more data and effort than a
schedule-only SRA.</p>
<p><b>When to use.</b> A formal cost+schedule confidence at a decision point (e.g. a NASA KDP) where a
cost-loaded, risk-adjusted IMS exists.</p>
<p class=muted><b>Status here.</b> The two models above are <b>schedule</b> SRA (an SCL). The
<b>Joint Cost-&amp;-Schedule Confidence panel below</b> runs the full joint Monte-Carlo (ADR-0269)
whenever the loaded file is <b>cost-loaded</b> (task budgets present &mdash; the same gate as the
<a href="/evm">EVM</a> cost indices). Without cost it stays honestly gated: a duration-only run
remains an SCL and is never labeled JCL.</p></details>
</div>"""


def _sra_body(st: SessionState) -> str:
    """The Schedule Risk Analysis (SRA) results page: risk-input panel + (empty) chart hosts.

    The simulation is intentionally NOT run here — ``sra.js`` fetches ``/api/sra`` (which now reads
    the session's manual risk inputs) and renders the confidence S-curve, finish-date histogram,
    and the sensitivity tornado. Running 1000x CPM during the page render would hang on a large
    schedule, so the page opens instantly and the run happens off the page-load path.

    Panel contract (ADR-0339). Two consequences of that deferred run shape the conversion:

    * the provenance chip is the SINGLE-file :func:`_prov_chip` of the SRA-selected version, not a
      series or pair chip. Every model on this page resolves its schedule through
      :func:`_sra_selected` — the top panel exists to say so — and a first→last series chip would
      name versions no figure on the page came from. (The mirror image of ADR-0338's decision on
      ``/risks``, where the findings genuinely came from a pair.)
    * four of these panels are EMPTY chart hosts until the operator runs the simulation, so their
      takes state what the panel will draw and from what, rather than a figure the server does not
      have. Law 2: a take that quoted a P50 before any run would be fabricating one.
    """
    iter_opts = "".join(
        f'<option value="{n}"{" selected" if n == 1000 else ""}>{n}</option>'
        for n in (500, 1000, 2000, 5000)
    )
    sch = _sra_selected(st)
    scoped = sch[1] if sch is not None else None
    selected_key = sch[0] if sch is not None else None
    file_opts = "".join(
        f'<option value="{_e(key)}"{" selected" if key == selected_key else ""}>{_e(key)}</option>'
        for key, _raw in st.ordered_versions()
    )
    file_selector = (
        '<form method=get action="/sra" class=viz-controls style="margin-bottom:8px">'
        "<label>Run SRA against file "
        f"<select name=file>{file_opts}</select></label>"
        "<button type=submit>Run on this file</button></form>"
        if len(st.schedules) > 1
        else ""
    )
    # The file pick governs EVERY model on the page (SSI, OAT, and the legacy Monte-Carlo all
    # resolve their schedule through _sra_selected), so it lives in one panel at the very top.
    active_note = (
        f"<p class=muted>Active file: <b>{_e(selected_key) if selected_key else '—'}</b> "
        f"{'(latest solvable version)' if st.sra_file is None else ''}</p>"
    )
    # The page's shared contract furniture. When NOTHING solves there is no selected file, so
    # `/export/xlsx/sra` answers 400 — the ⤓ would be a dead link, which rank 3 forbids. The whole
    # strip degrades together with the chip: head + ⛶ only, and no panel-level data-export.
    solvable = scoped is not None
    prov = _prov_chip(scoped) if scoped is not None else ""
    tools = _shell_tools(export_title=_SRA_XLSX_TITLE if solvable else "")
    export_attr = _SRA_EXPORT if solvable else ""
    # the SELECTOR's population (active project, exclusions dropped), not every loaded file —
    # `len(st.schedules)` spans other projects and would not match the dropdown beside it
    n_loaded = len(st.ordered_versions())
    top_file_panel = (
        f"<div class=panel{export_attr}>"
        + _panel_head("Schedule file for the SRA", tools=tools, prov=prov)
        + f"<p class=sf-take data-no-i18n>{n_loaded} version"
        f"{'' if n_loaded == 1 else 's'} in this project; every SRA model on this page runs "
        f"against {_e(selected_key) if selected_key else '—'}.</p>"
        "<p class=muted>Choose which loaded version <b>every</b> SRA model on this page runs "
        "against &mdash; the SSI Schedule Risk &amp; Opportunity model, the one-at-a-time "
        "sensitivity, and the legacy Monte-Carlo all use this same file.</p>"
        f"{_user_tip('Set your Risk Ranking Factors, Best/Worst-Case durations and risks once: they are shared by both the SSI model and the legacy Monte-Carlo, so you never re-enter them per model.')}"
        f"{file_selector}{active_note}</div>"
    )
    # one-shot Excel round-trip import feedback (ADR-0211): shown once, then cleared
    import_banner = ""
    if st.sra_import_msg:
        # ADR-0313: a failure must not render in the success style. `role=alert` is announced
        # immediately by a screen reader; `role=status` is polite and can be missed entirely —
        # which is the wrong politeness for "your risk was not added".
        cls, role = ("notice warn", "alert") if st.sra_import_is_error else ("notice ok", "status")
        # ADR-0359: the ADR-0356 CHECK-INPUTS vintage warning carries its own remedy — the
        # root-caused deltas were BOTH stale-setup replays, and a warning the operator must
        # leave the banner to act on is a warning that gets run past. One click seeds the grid
        # verbatim from the active schedule's stored SRA fields.
        fix_btn = (
            '<form action="/sra/load-from-schedule" method=post style="display:inline;margin-left:8px">'
            "<button type=submit>Use the file's own values</button></form>"
            if "CHECK INPUTS" in st.sra_import_msg
            else ""
        )
        import_banner = f'<div class="{cls}" role={role}>{_e(st.sra_import_msg)}{fix_btn}</div>'
        st.sra_import_msg = None
        st.sra_import_is_error = False
    low_pct = f"{st.sra_low * 100:g}"
    ml_pct = f"{st.sra_ml * 100:g}"
    high_pct = f"{st.sra_high * 100:g}"
    on_defaults = (
        st.sra_low == 0.9 and st.sra_ml == 1.0 and st.sra_high == 1.10 and not st.sra_overrides
    )
    if on_defaults:
        disclaimer = (
            '<div class="notice warn" role=note><b>Auto defaults &mdash; screening placeholder, '
            "not SME-validated.</b> With no analyst-supplied risk ranges this run applies an "
            "industry-default <b>triangular</b> distribution to each activity's <i>remaining</i> "
            "duration (Min&nbsp;90% / Most-Likely&nbsp;100% / Max&nbsp;110% &mdash; an industry "
            '"Realistic" default). It is a <b>screening placeholder, not SME-validated</b> (GAO/NASA/AACE '
            "prefer elicited ranges) and is overridable per-activity. A duration-only run is a "
            "<i>schedule</i> confidence level &mdash; a cost-loaded file unlocks the joint "
            "cost+schedule (JCL) panel above (ADR-0269).</div>"
        )
    else:
        disclaimer = (
            '<div class="notice ok" role=note>Using your analyst-supplied uncertainty (global '
            f"low/ml/high = {low_pct}/{ml_pct}/{high_pct}%, {len(st.sra_overrides)} per-activity "
            "overrides). A duration-only run is a <i>schedule</i> confidence level &mdash; a "
            "cost-loaded file unlocks the joint cost+schedule (JCL) panel above (ADR-0269).</div>"
        )
    n_risks = len(st.sra_risks)
    n_over = len(st.sra_overrides)
    # The four deferred-run panels + the two that describe pending inputs. Each head/take pair is
    # built here so the (long) template below stays readable.
    h_legacy = _panel_head(
        "Legacy SRA &mdash; Monte-Carlo (multiplicative risk drivers)", tools=tools, prov=prov
    )
    h_means = _panel_head("What the results mean", tools=tools, prov=prov)
    h_inputs = _panel_head("Risk inputs", tools=tools, prov=prov)
    h_drivers = _panel_head("Risk drivers (tornado)", tools=tools, prov=prov)
    h_cdf = _panel_head("Finish-date confidence (S-curve)", tools=tools, prov=prov)
    h_hist = _panel_head("Finish-date distribution", tools=tools, prov=prov)
    h_sens = _panel_head("Duration sensitivity (tornado)", tools=tools, prov=prov)
    t_inputs = (
        f"<p class=sf-take data-no-i18n>Global triangular {low_pct}/{ml_pct}/{high_pct}% of each "
        f"remaining duration, with {n_over} per-activity override"
        f"{'' if n_over == 1 else 's'}.</p>"
    )
    t_drivers = (
        f"<p class=sf-take data-no-i18n>{n_risks} risk{'' if n_risks == 1 else 's'} registered "
        "&mdash; ranked here by the mean finish slip each contributes once the simulation runs.</p>"
    )
    # B608 is bandit's SQL heuristic tripping on HTML ("<select ..." + "drawn from the latest
    # run" in one f-string) — this is a server-rendered page template, no SQL anywhere.
    return f"""
{import_banner}
{top_file_panel}
{_sra_explainers(prov=prov)}
{_TS_CAPTION_MARK}{_ssi_panel(st, prov=prov, tools=tools, export_attr=export_attr)}
{_correlation_matrix_panel(st, prov=prov, tools=tools, export_attr=export_attr)}
{_jcl_panel(st, prov=prov)}
<div class=panel{export_attr}>{h_legacy}
<p class=sf-take data-no-i18n>Runs on demand &mdash; 1000 iterations of the trusted CPM solver by
default, sampling a triangular distribution.</p>
<p class=muted>A seeded Monte-Carlo simulation samples each activity's duration from its
distribution and recomputes the network finish through the trusted CPM solver, building a
finish-date confidence curve. The deterministic CPM finish is marked against the distribution
so you can read how much contingency it implies (the deterministic date typically sits well
below P50). Per-activity criticality and duration sensitivity drive the tornado.</p>
{disclaimer}
<div class=viz-controls>
<label>Iterations <select id=sraIters>{iter_opts}</select></label>
<label>Distribution <select id=sraDistribution data-no-i18n>
<option value=triangular selected>Triangular</option>
<option value=pert>Beta-PERT</option>
</select></label>
<button id=sraRun type=button>Run simulation</button>
</div>
<p id=sraStatus class=muted aria-live=polite></p></div>
<div class=panel{export_attr}>{h_means}
<p class=sf-take data-no-i18n>Template sentences filled with the run's own figures &mdash; nothing
here is AI-generated, and nothing appears until you run the simulation above.</p>
<p class=muted>Plain-language conclusions drawn from the latest run &mdash; each card names the
evidence figures behind it (nothing here is AI-generated; the sentences are templates filled with
the run's own numbers). Refreshed on every run and included first in the Excel export.</p>
<div id=sraConclusions class=sra-conclusions data-no-i18n></div></div>
<div class=panel{export_attr}>{h_inputs}{t_inputs}
<p class=muted>These uncertainty ranges feed the next simulation run. The <b>global</b> triangular
applies to every activity's <i>remaining</i> duration (the standard "Quick Risk" screening
approach); completed work is fixed at its actuals (no uncertainty). Per-activity 3-point overrides
take precedence over the global for the activities you elicit.</p>
<form action="/sra/risk" method=post class=viz-controls>
<label>Low % <input type=number id=sraLow name=low min=5 max=100 step=any value="{low_pct}"></label>
<label>Most-likely % <input type=number id=sraMl name=ml min=50 max=150 step=any value="{ml_pct}"></label>
<label>High % <input type=number id=sraHigh name=high min=100 max=300 step=any value="{high_pct}"></label>
<button type=submit>Save global risk</button>
</form>
<h3>Per-activity override (3-point, days)</h3>
<form action="/sra/risk" method=post class=viz-controls>
<label>UID <input type=number name=uid min=1 step=1></label>
<label>Optimistic (d) <input type=number name=opt_days min=0 step=any></label>
<label>Most-likely (d) <input type=number name=ml_days min=0 step=any></label>
<label>Pessimistic (d) <input type=number name=pess_days min=0 step=any></label>
<button type=submit>Add override</button>
</form>
{_sra_overrides_table(st, scoped)}</div>
<div class=panel{export_attr}>{h_drivers}{t_drivers}
<p class=muted>Register risks <b>once</b> in the <b>Risk / Opportunity register</b> above (the Schedule
Risk &amp; Opportunity Analysis panel) &mdash; each carries both a days-impact (SSI &mdash; the impact
replaces the affected task's remaining duration while it fires, ADR-0359) and a
multiplicative-% (legacy) magnitude and feeds this Monte-Carlo. This tornado ranks each registered
risk by the mean project-finish slip it contributes: the difference between the mean finish over the
iterations the risk fired and the iterations it did not (working days), with its observed occurrence
rate. Empty until a risk is registered.</p>
<div id=sraRisk class=chart-host></div></div>
<div class=panel{export_attr}>{h_cdf}
<p class=sf-take data-no-i18n>Drawn from the run above &mdash; cumulative confidence by date, with
the deterministic CPM finish marked at the percentile it lands on.</p>
<p class=muted>Cumulative probability of finishing on or before each date, with P10/P50/P80/P90
markers and the deterministic CPM finish annotated with the percentile it sits at.</p>
<div id=sraCdf class=chart-host></div></div>
<div class=panel{export_attr}>{h_hist}
<p class=sf-take data-no-i18n>The same run's finish dates as a histogram &mdash; how many of the
iterations landed in each date bin.</p>
<div id=sraHist class=chart-host></div></div>
<div class=panel{export_attr}>{h_sens}
<p class=sf-take data-no-i18n>Ranks the activities whose duration most drives the finish, by
Spearman rank correlation over the run's iterations.</p>
<p class=muted>The activities whose duration most drives the project finish (Spearman rank
correlation), with each activity's Criticality Index and Schedule Sensitivity Index.</p>
<div id=sraSens class=chart-host></div></div>
<script src="/static/sra.js"></script>
<script src="/static/panelkit.js"></script>"""  # nosec B608 (HTML, not SQL)


def _sra_data(
    st: SessionState, sch: Schedule, cpm: CPMResult, result: SRAResult
) -> dict[str, object]:
    """The SRA results payload for ``sra.js`` — offsets resolved to ISO dates on the calendar.

    Every offset→date conversion here applies the run's stored-date-axis realignment
    (``sra.stored_finish_correction`` — the ADR-0256 pattern, adopted by the legacy model in
    ADR-0353), so the S-curve, histogram, mean and deterministic marker land on the identical
    date axis as the result's own ``*_date`` fields (pinned by test).
    """
    cal = sch.calendar
    ps = sch.project_start
    correction = stored_finish_correction(sch, None, result.deterministic_finish)

    def _iso(offset: int) -> str:
        return (offset_to_datetime(ps, max(offset, 0), cal) + correction).isoformat()

    names = sch.tasks_by_id
    # tornado: the most influential activities by |duration sensitivity| (top 20)
    top = sorted(result.activities, key=lambda a: abs(a.duration_sensitivity), reverse=True)[:20]
    sensitivity = [
        {
            "uid": a.unique_id,
            "name": names[a.unique_id].name if a.unique_id in names else "",
            "ci": round(a.criticality_index, 4),
            "sens": round(a.duration_sensitivity, 4),
            "ssi": round(a.ssi, 4),
        }
        for a in top
    ]
    return {
        "iterations": result.iterations,
        "auto_used": result.auto_used,
        "manual": {
            "low": st.sra_low,
            "ml": st.sra_ml,
            "high": st.sra_high,
            "overrides": len(st.sra_overrides),
        },
        "deterministic": {
            "date": _iso(result.deterministic_finish),
            "percentile": round(result.deterministic_percentile * 100, 1),
        },
        "percentiles": [
            {"label": "P10", "date": result.p10_date},
            {"label": "P50", "date": result.p50_date},
            {"label": "P80", "date": result.p80_date},
            {"label": "P90", "date": result.p90_date},
        ],
        "mean": _iso(round(result.mean)),
        "cdf": [[_iso(offset), prob] for offset, prob in result.cdf],
        "histogram": [[_iso(lo), _iso(hi), count] for lo, hi, count in result.histogram],
        "sensitivity": sensitivity,
        "constraints_flagged": len(result.constraints_flagged),
        "risk_drivers": [
            {
                "id": d.id,
                "name": d.name,
                "probability": round(d.probability, 4),
                "hits": d.hits,
                "iterations": result.iterations,
                "delta_days": d.mean_delta_days,
            }
            for d in result.risk_drivers
        ],
        # plain-language "what the results mean" cards (ADR-0201) — deterministic templates
        # filled with the run's own figures; sra.js renders them under the run controls
        "conclusions": conclusions_as_dicts(conclusions_from_sra(sch, cpm, result)),
    }


def _what_could_go_wrong_header(st: SessionState) -> str:
    """Chapter 11 "What could go wrong" (ADR-0209): the data-driven takeaway + a risk-exposure
    KPI strip + the float-exposure and risk-flag bars. The Monte-Carlo runs client-side on
    demand, so the header reports the DETERMINISTic structural risk of the SRA-selected file
    (float exposure + constraint/negative-float/registered-risk flags) — no simulation, no new
    math; every figure comes from the cached analysis + the risk register."""
    chosen = _sra_selected(st)
    if chosen is None:
        return ""
    key, sch, cpm = chosen
    try:
        audit = st.analysis_for(key, st.schedules[key]).audit
    except (CPMError, KeyError):
        return ""
    mpd = sch.calendar.working_minutes_per_day or 480
    crit = near = comfy = incomplete = neg = 0
    # per-segment UID sets so the two status bars drill (ADR-0360): a click on a segment lists
    # exactly the activities it counts, through the shared sf-drill grid (+ columns + Excel).
    crit_uids: list[int] = []
    near_uids: list[int] = []
    comfy_uids: list[int] = []
    neg_uids: list[int] = []
    for task in non_summary(sch):
        if task.is_complete:
            continue
        incomplete += 1
        timing = cpm.timings.get(task.unique_id)
        if timing is None:
            continue
        tf_days = effective_total_float(task, timing.total_float) / mpd
        if tf_days < 0:
            neg += 1
            neg_uids.append(task.unique_id)
        if tf_days <= 0:
            crit += 1
            crit_uids.append(task.unique_id)
        elif tf_days <= 5:
            near += 1
            near_uids.append(task.unique_id)
        else:
            comfy += 1
            comfy_uids.append(task.unique_id)

    def _count(metric_id: str) -> int:
        return next((c.count for c in audit.checks if c.metric_id == metric_id), 0)

    hard = _count("DCMA05")
    hard_uids = tuple(
        c.unique_id
        for chk in audit.checks
        if chk.metric_id == "DCMA05"
        for c in chk.citations
        if c.unique_id
    )
    risks = len(st.sra_risks)
    risk_uids = tuple(dict.fromkeys(u for r in st.sra_risks for u in r.affected))

    def _acts(n: int) -> str:
        return "activity" if n == 1 else "activities"

    if incomplete == 0:
        takeaway = (
            "Every activity is complete — there is no remaining work for the risk simulation to "
            "put at risk."
        )
    else:
        risk_clause = f", with {risks} risk{'s' if risks != 1 else ''} registered" if risks else ""
        takeaway = (
            f"{crit} {_acts(crit)} drive the finish and {near} more are near-critical "
            f"(within 5 days of float){risk_clause} — run the Monte-Carlo below to quantify the "
            "finish-date confidence."
        )

    kpi = _stat_cards(
        [
            ("Critical activities", str(crit)),
            ("Near-critical (≤5d)", str(near)),
            ("Negative float", str(neg)),
            ("Hard constraints", str(hard)),
            ("Registered risks", str(risks)),
            ("Incomplete activities", str(incomplete)),
        ]
    )
    exposure_bar = _status_stack(
        "Float exposure",
        "Incomplete activities by how much total float protects them from driving the finish. "
        "Hover a segment for its count; click it to list the activities underneath "
        "(add any field, export to Excel).",
        [
            ("Critical", crit, "--bad"),
            ("Near-critical", near, "--warn"),
            ("Comfortable", comfy, "--ok"),
        ],
        f"{incomplete} incomplete {_acts(incomplete)}",
        drill=[
            (tuple(crit_uids), key),
            (tuple(near_uids), key),
            (tuple(comfy_uids), key),
        ],
    )
    flags_bar = _status_stack(
        "Risk flags",
        "The structural risk sources the simulation and register draw on. "
        "Hover a segment for its count; click it to list the activities underneath "
        "(add any field, export to Excel).",
        [
            ("Negative float", neg, "--bad"),
            ("Hard constraints", hard, "--warn"),
            ("Registered risks", risks, "--accent"),
        ],
        "deterministic flags on the selected file",
        drill=[
            (tuple(neg_uids), key),
            (hard_uids, key),
            (risk_uids, key),
        ],
    )
    # ADR-0339: the h1 was always here; the DoD's *context line* was not (measured `page-lede` 0 on
    # the pristine tree). Routing both through `_utility_takeaway` renders the same h1 byte-for-byte
    # and adds the missing lede, so /sra stops being the one Act III page with half the rule.
    return (
        _utility_takeaway(
            _e(takeaway),
            "Deterministic structural risk on the selected file first &mdash; float exposure, "
            "constraints and the registered risks &mdash; then the Monte-Carlo models below turn "
            "it into a finish-date confidence.",
        )
        + f'<div class="ws-kpi">{kpi}</div>'
        + f'<div class="ws-bars">{exposure_bar}{flags_bar}</div>'
    )
