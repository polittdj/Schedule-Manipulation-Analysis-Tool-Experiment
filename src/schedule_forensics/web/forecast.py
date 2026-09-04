"""The /forecast page family: where the schedule lands, and how each method knows.

Monolith split, phase 3 slice 10 (ADR-0374), extracted VERBATIM from ``web/app.py``: every
function, docstring and comment moves byte-for-byte, only the module boundary changes.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour
(the ``/forecast``, ``/api/forecast``, ``/export/{fmt}/forecast`` and
``/export/{fmt}/field-forecast`` routes): NINE names / one contiguous block - the
"Where it lands" chapter header, the Carnac KPI cards, the method lane colours + ruler +
methodology explainer, the per-field execution panel and its group rollup (ADR-0179/0188),
the page body and the ``/api/forecast`` drift payload. Every external referrer is a
``create_app`` route, which imports downward and stays put; that includes ``evm_view`` -
``_field_forecast_panel`` is served on /evm too (operator 2026-07-10), and the route reaches
it through ``web.app``'s re-export exactly as ``forecast_view`` does. The export routes
contribute NO movers: they build their tables from the engine (``carnac_table`` /
``forecast_tables`` / ``compute_field_forecast``) and the shared export machinery
(``_bad_format`` / ``_solvable_versions`` / ``_export_response``), all multi-family stays.
No descents: the family's externals live in ``web/components.py`` / ``web/chrome.py``,
the engine and the model.

Layering: ``app`` -> ``forecast`` -> ``components`` -> ``chrome`` -> ``state`` ->
engine/model. Nothing here imports ``web.app``.
"""

from __future__ import annotations

import datetime as dt
from urllib.parse import quote

from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.forecast import (
    CarnacSummary,
    ForecastSet,
    compute_carnac_summary,
    compute_group_rollup,
)
from schedule_forensics.engine.grouping import available_fields_union
from schedule_forensics.engine.metrics.field_forecast import compute_field_forecast
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _EXPLAINERS, _e
from schedule_forensics.web.components import (
    _mdY,
    _panel_head,
    _prov_chip,
    _series_prov_chip,
    _shell_tools,
    _stat_cards,
    _status_stack,
    _user_tip,
)


def _carnac_cards(summary: CarnacSummary) -> str:
    """The deck's Carnac KPI card row (PBIX page 13) over the latest version."""

    def d(value: dt.date | None) -> str:
        return _mdY(value)

    def n(value: float | None, *, suffix: str = "") -> str:
        return f"{value:g}{suffix}" if value is not None else "—"

    return _stat_cards(
        [
            ("Earliest start", d(summary.earliest_start)),
            ("Latest finish (CPM)", d(summary.latest_finish)),
            ("Project duration (wd)", n(summary.project_duration_days)),
            ("Forecasted end (rate)", d(summary.forecasted_end)),
            ("Estimated end (ES, to-go)", d(summary.estimated_end_es)),
            ("Avg tasks / month", n(summary.avg_tasks_per_month)),
            ("Remaining duration (wd)", n(summary.remaining_duration_days)),
            ("SPI(t)", n(summary.spi_t)),
            ("Earned schedule (wd)", n(summary.earned_schedule_days)),
            ("Tasks to complete", str(summary.to_go_count)),
        ]
    )


#: lane color per forecast method (matches static/drift.js so the ruler and the animation
#: read consistently): logic = accent, stored = muted, throughput = ok, performance = bad.
#: ``as_scheduled`` was missing (ADR-0310, audit H6) and silently fell through to ``var(--ink)``,
#: so the one method that reports the SOURCE TOOL's own progress-aware date was the one lane with
#: no identity of its own.
_FORECAST_METHOD_COLORS = {
    "cpm": "var(--accent)",
    "as_scheduled": "var(--muted)",
    "rate": "var(--ok)",
    "earned_schedule": "var(--bad)",
}


def _forecast_ruler(fc: ForecastSet) -> str:
    """A static single-version SVG 'ruler' (M18 item 8): the data date, the baseline finish,
    and each method's forecast on one timeline so the spread between them is visible at a
    glance. Inline SVG (no JS, no external fetch); the multi-version movement is the animated
    drift stepper below. Methods with missing inputs render '— (inputs missing)'."""
    lanes = [(f.name, f.method_id, f.finish) for f in fc.forecasts]
    method_dates = [d for _, _, d in lanes if d is not None]
    axis_dates = list(method_dates)
    if fc.as_of is not None:
        axis_dates.append(fc.as_of)
    if fc.planned_finish is not None:
        axis_dates.append(fc.planned_finish)
    if not axis_dates:
        return ""
    lo, hi = min(axis_dates), max(axis_dates)
    if lo == hi:
        lo, hi = lo - dt.timedelta(days=15), hi + dt.timedelta(days=15)
    span = (hi - lo).days or 1

    w, pad_l, pad_r, pad_t, row_h = 940, 150, 130, 46, 40
    height = pad_t + row_h * len(lanes) + 24
    plot_w = w - pad_l - pad_r
    bottom = pad_t + row_h * len(lanes)

    def x(d: dt.date) -> float:
        return pad_l + ((d - lo).days / span) * plot_w

    parts = [
        f'<svg viewBox="0 0 {w} {height}" width="100%" role="img" '
        f'aria-label="Forecast finish dates on a shared timeline">'
    ]
    if fc.as_of is not None:
        ax = x(fc.as_of)
        parts.append(
            f'<line x1="{ax:.1f}" y1="{pad_t - 12}" x2="{ax:.1f}" y2="{bottom}" '
            'style="stroke:var(--muted)" stroke-width="1.5" stroke-dasharray="2 3"/>'
            f'<text x="{ax:.1f}" y="{pad_t - 16}" text-anchor="middle" '
            f'style="fill:var(--muted)" font-size="11">data date {_mdY(fc.as_of)}</text>'
        )
    if fc.planned_finish is not None:
        px = x(fc.planned_finish)
        parts.append(
            f'<line x1="{px:.1f}" y1="{pad_t - 12}" x2="{px:.1f}" y2="{bottom}" '
            'style="stroke:var(--warn)" stroke-width="2" stroke-dasharray="5 4"/>'
            f'<text x="{px:.1f}" y="{pad_t - 30}" text-anchor="middle" '
            f'style="fill:var(--warn)" font-size="11">baseline {_mdY(fc.planned_finish)}</text>'
        )
    for i, (name, mid, d) in enumerate(lanes):
        cy = pad_t + row_h * i + row_h / 2
        color = _FORECAST_METHOD_COLORS.get(mid, "var(--ink)")
        parts.append(
            f'<line x1="{pad_l}" y1="{cy:.1f}" x2="{w - pad_r}" y2="{cy:.1f}" '
            'style="stroke:var(--line)" stroke-width="1"/>'
            f'<text x="{pad_l - 10}" y="{cy + 4:.1f}" text-anchor="end" '
            f'style="fill:var(--muted)" font-size="12">{_e(name)}</text>'
        )
        if d is not None:
            cx = x(d)
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" style="fill:{color}"/>'
                f'<text x="{cx:.1f}" y="{cy - 11:.1f}" text-anchor="middle" '
                f'style="fill:var(--ink)" font-size="11">{_mdY(d)}</text>'
            )
        else:
            parts.append(
                f'<text x="{pad_l + 10}" y="{cy + 4:.1f}" '
                'style="fill:var(--muted)" font-size="11">&#8212; (inputs missing)</text>'
            )
    parts.append("</svg>")
    legend_items = "".join(
        f"<span class=chart-legend-item><span class=chart-swatch "
        f'style="background:{_FORECAST_METHOD_COLORS.get(mid, "var(--ink)")}"></span>'
        f"{_e(name)}</span>"
        for name, mid, _ in lanes
    )
    legend_items += (
        '<span class=chart-legend-item style="color:var(--muted)">'
        "&mdash; gold dashed = baseline finish &middot; grey dotted = data date</span>"
    )
    legend = f"<div class=chart-legend>{legend_items}</div>"
    spread = ""
    if len(method_dates) >= 2:
        lo_m, hi_m = min(method_dates), max(method_dates)
        spread = (
            f"<p class=muted>The methods span <b>{(hi_m - lo_m).days} days</b> "
            f"({_mdY(lo_m)} &rarr; {_mdY(hi_m)}). A wide fan means the plan, the "
            "throughput, and the earned-schedule performance disagree about the finish.</p>"
        )
    return f"<div id=forecastRuler>{''.join(parts)}{legend}</div>{spread}"


def _forecast_explainer(fc: ForecastSet, *, prov: str = "") -> str:
    """Plain-English methodology for the finish forecasts (M18 item 8): one card per
    method (what it measures, the formula in words + symbols, when it is available, and this
    version's value), plus the static ruler. Every value reuses the forecast set — nothing
    is recomputed.

    Panel contract: head + ``.sf-take`` + the caller's provenance chip, and deliberately NO
    ⤓ EXCEL — the ruler also plots the data date and the baseline finish, which no column of
    ``/export/xlsx/forecast`` carries, so a ⤓ here would hand back less than the panel draws
    (:func:`_shell_tools` drops the button when no export title is given: never a dead or
    lying link). ``#forecastRuler`` is untouched — :func:`_forecast_ruler` keeps its exact
    signature and its byte-exact empty-path return."""
    by = {f.method_id: f for f in fc.forecasts}

    def fin(mid: str) -> str:
        f = by.get(mid)
        return _mdY(f.finish) if (f is not None and f.finish is not None) else "&#8212;"

    rate_txt = f"{fc.rate_per_month:g} / month" if fc.rate_per_month is not None else "n/a"
    spi_txt = f"{fc.spi_t:g}" if fc.spi_t is not None else "n/a"
    cards = [
        (
            "Schedule logic (CPM)",
            "The date the plan claims",
            "Runs the network's own forward and backward pass over every activity, its links, "
            "durations and calendar, and reports the finish the logic computes. It reflects "
            "what the schedule says &mdash; not how the work has actually been going.",
            "Method: the critical-path method (the longest logic-driven chain to the end).",
            "Always available once the network schedules &mdash; it never reads &#8212;.",
            fin("cpm"),
        ),
        (
            "As-scheduled (stored dates)",
            "The date the source tool itself reports",
            "Reads the finish MS&nbsp;Project / P6 <i>stored in the file</i> rather than recomputing "
            "it. The source tool is progress-aware &mdash; where it has rescheduled an in-progress "
            "activity's remaining work it records that decision &mdash; so on a progressed schedule "
            "this can sit LATER than the CPM date above. That gap is the point of showing "
            "both: CPM says what the network implies, this says what the file asserts.",
            "Method: the latest stored finish among the schedule's activities &mdash; no "
            "recalculation, so it carries whatever constraints, levelling or out-of-sequence "
            "progress the author left in.",
            "Needs stored finish dates in the source file, else &#8212;.",
            fin("as_scheduled"),
        ),
        (
            "Completion-rate extrapolation",
            "The throughput answer",
            "Counts the activities that have actually finished, divides by the months elapsed "
            "since the project started to get a completion pace, then asks how long the "
            "remaining activities take at that same pace.",
            "Formula: rate = completed &divide; elapsed&nbsp;months, then "
            "finish = data&nbsp;date + (to-go &divide; rate) months "
            f"(here {fc.completed_count} done at {rate_txt}, {fc.remaining_count} to go).",
            "Needs a status (data) date and at least one completed activity, else &#8212;.",
            fin("rate"),
        ),
        (
            "Earned-schedule IEAC(t)",
            "The performance answer",
            "Earned Schedule (ES) is how much planned <i>time</i> the completed work was worth "
            "on the baseline; AT is the actual time elapsed; their ratio SPI(t) = ES &divide; AT "
            "is the schedule efficiency. The estimate projects the remaining planned duration "
            "at that observed efficiency.",
            f"Formula: IEAC(t) = AT + (PD &minus; ES) &divide; SPI(t) (here SPI(t) = {spi_txt}).",
            "Needs baselines, completed work, and SPI(t) &gt; 0, else &#8212;.",
            fin("earned_schedule"),
        ),
    ]
    card_html = "".join(
        f"<div class=forecast-method><h3>{_e(title)}</h3>"
        f"<p class=method-tag>{_e(tag)}</p>"
        f"<p>{what}</p><p class=muted>{how}</p>"
        f"<p class=muted><b>Availability:</b> {needs}</p>"
        f"<p class=method-finish>This version: <b>{value}</b></p></div>"
        for title, tag, what, how, needs, value in cards
    )
    # Every figure the take quotes is ALREADY rendered verbatim by the cards below, from the
    # same locals the card text is built from: `fc.completed_count`, `rate_txt` and
    # `fc.remaining_count` (the completion-rate card's formula line) and `spi_txt` (the
    # earned-schedule card's formula line). Nothing is recomputed.
    take = (
        f"{fc.completed_count} activities are done at {rate_txt} with {fc.remaining_count} to "
        f"go, and SPI(t) reads {spi_txt} &mdash; the inputs each method below turns into a date."
    )
    return f"""
<div class=panel>{_panel_head("How the forecasts are computed", tools=_shell_tools(), prov=prov)}
<p class=sf-take data-no-i18n>{take}</p>
<p class=muted>Each method answers "when will it really end?" from a different angle &mdash;
the plan's own logic, the observed throughput, and the earned-schedule performance. When they
agree you can trust the date; when they fan apart, the disagreement is itself a finding. Every
figure here reuses the forecast above &mdash; nothing is recomputed.</p>
<div class=card-cols>{card_html}</div>
<h3>Forecast spread &mdash; latest version</h3>
<p class=muted>The data date, the baseline finish, and each method's forecast on one
timeline. The multi-version movement is animated in the stepper below when two or more
versions are loaded.</p>
{_forecast_ruler(fc)}</div>"""


def _field_forecast_panel(
    schedules: list[Schedule], group_field: str, action: str = "/forecast"
) -> str:
    """Per-field group execution metrics on /forecast (operator 2026-07-09, ADR-0179): pick
    any standard or custom field (e.g. a CAM code) and every version's tasks are grouped by
    its values (plus NA for unassigned), each group scored with the SAME engine functions the
    schedule-wide figures use — BEI / HMI / CEI / both SPI(t)s — plus the start-basis leading
    index for groups that have not completed work yet.

    Panel contract (ADR-0298, shared with /evm — both routes load panelkit.js): head + tools +
    a series provenance chip + one ``.sf-take``. Two deliberate decisions:

    * **ONE CONVENTION for Excel.** This panel already carried an ``<a class=btn-link>⇩ Excel</a>``
      INSIDE its ``<form>``. Rather than ship a second Excel control beside it, that anchor is
      REWIRED into the head strip's ⤓ EXCEL following the panel's ``data-export`` — the same
      ``/export/xlsx/field-forecast?field=…`` endpoint, one affordance. It stays CONDITIONAL
      exactly as the anchor was: the endpoint REQUIRES a field (no field → 422, empty → 404),
      so an ungrouped panel carries no ``data-export`` and :func:`_shell_tools` emits no ⤓.
    * **a take that quotes NO figure.** This panel renders no aggregate anywhere — no row count,
      no group count, no column total — so any number in a takeaway would be new arithmetic.
      It gets a figure-free sentence instead of an invented one.

    The ``<form>`` itself (method, action, ``name=group_field``, the option list and its
    ``selected`` marker, and the Compute button) is otherwise byte-for-byte unchanged."""
    fields = available_fields_union(schedules)
    if group_field and group_field not in fields:
        group_field = ""
    opts = '<option value="">— pick a field —</option>' + "".join(
        f'<option value="{_e(f)}"{" selected" if f == group_field else ""}>{_e(f)}</option>'
        for f in fields
    )
    export_attr = (
        f' data-export="/export/xlsx/field-forecast?field={quote(group_field, safe="")}"'
        if group_field
        else ""
    )
    head = _panel_head(
        "Execution metrics by field group",
        tools=_shell_tools(
            export_title=(
                "Export this field's per-group execution metrics for every loaded version "
                "— opens in Excel"
            )
            if group_field
            else ""
        ),
        prov=_series_prov_chip(schedules),
    )
    take = (
        "Every loaded version's activities scored group by group on this field with the same "
        "engine metrics the schedule-wide figures use; a group with no completed work reads "
        "N/A on the finish-anchored indices and carries the start index (SEI) instead."
        if group_field
        else "Pick a field to score every loaded version's activities group by group with the "
        "same engine metrics the schedule-wide figures use."
    )
    form = f"""
<div class=panel{export_attr}>{head}
<p class=sf-take data-no-i18n>{take}</p>
<p class=muted>Group every loaded version's activities by any <b>standard or custom field</b>
(for example a CAM code) and score each group with the same engine metrics the schedule-wide
figures use — <b>BEI</b>, <b>HMI</b>, <b>CEI (Finish / Start)</b>, and both <b>SPI(t)</b>
methods — computed over <b>only that group's tasks</b>. Activities carrying no value for the
field are grouped as <b>NA</b>.</p>
<form method=get action={action} class=viz-controls>
<label>Group by <select name=group_field data-no-i18n>{opts}</select></label>
<button type=submit>Compute</button>
</form>"""
    if not group_field:
        return form + "</div>"
    rows_data = compute_field_forecast(schedules, group_field)

    def cell(v: float | None, *, na_hint: str = "") -> str:
        if v is None:
            return (
                f'<td class=muted title="{_e(na_hint)}">N/A</td>'
                if na_hint
                else ("<td class=muted>N/A</td>")
            )
        cls = "fail" if v < 0.95 else "pass"
        return f'<td class="num {cls}">{v:g}</td>'

    body_rows = ""
    last_group = None
    for g in rows_data:
        group_cell = (
            f"<th scope=row rowspan=1 data-no-i18n>{_e(g.group)}</th>"
            if g.group != last_group
            else "<th scope=row></th>"
        )
        last_group = g.group
        note = ""
        if g.activities and g.no_completed_work:
            note = (
                '<span class=exc-note title="No completed work in this group yet — the '
                "finish-anchored indices are undefined (never imputed). Read the start "
                'index (SEI) as the leading execution signal.">start-basis</span>'
            )
        sei_hint = (
            "Start execution index — started ÷ baselined-to-start-by-the-data-date: the "
            "leading indicator used when a group has no completions yet"
        )
        body_rows += (
            f"<tr>{group_cell}<td data-no-i18n>{_e(g.version)}</td>"
            f"<td class=num>{g.activities}</td><td class=num>{g.completed}</td>"
            f"<td class=num>{g.started}</td><td class=num>{g.to_go}</td>"
            f"{cell(g.bei)}{cell(g.hmi)}{cell(g.cei_finish)}{cell(g.cei_start)}"
            f"{cell(g.spi_t)}{cell(g.spi_t_acumen)}"
            f"{cell(g.sei, na_hint=sei_hint)}"
            f"<td>{note}</td></tr>"
        )
    analysis = """
<details class=explainer><summary><b>Groups without completed work — how these figures are
derived (best-practice analysis)</b></summary>
<div style="padding:8px 12px">
<p><b>The problem.</b> BEI, HMI, CEI (Finish) and both SPI(t) methods are <i>finish-anchored</i>:
they compare completed work against what was baselined or forecast to complete. A group (a CAM,
a resource, a WBS leg) whose work has not completed anything yet gives these indices no
qualifying data — the denominator or the earned set is empty.</p>
<p><b>What published practice says.</b> The NDIA Planning &amp; Scheduling Excellence Guide's
treatment of BEI-family indices and the DCMA construct are explicit that an index without
qualifying data reads <b>N/A</b> — imputing a 0 (reads as catastrophic failure) or a 1 (reads
as perfect execution) poisons any forecast built on it. The accepted practice is to switch to
<b>leading, start-anchored indicators</b>: work must start before it can finish, so start
execution predicts finish execution one period ahead (Acumen's own library carries the
start-anchored twin as "BEI - Value Task Starts").</p>
<p><b>What this table does.</b> (1) Finish-anchored indices are <b>never fabricated</b> — an
undefined cell reads N/A. (2) Every group additionally carries the <b>start execution index
(SEI)</b> = activities started &divide; activities baselined to start by the data date — defined
as soon as anything is due to start, so a no-completions group still gets a real execution read.
(3) The <b>Started / To-go</b> counts give the group's workoff burden. A group flagged
<b>start-basis</b> with SEI &lt; 0.95 is already executing late even though no finish-based
metric can say so yet — that is the earlier, more accurate forecast signal the grouping is for.
(4) As soon as the group completes its first activity, the finish-anchored indices activate
automatically on the same engine formulas as the schedule-wide figures.</p>
</div></details>"""
    table = f"""
<div class=hist-drill-scroll style="max-height:560px">
<table class=hist-drill-table>
<tr><th scope=col data-no-i18n>{_e(group_field)}</th><th scope=col>Version</th>
<th scope=col>Activities</th><th scope=col>Done</th><th scope=col>Started</th>
<th scope=col>To go</th><th scope=col>BEI</th><th scope=col>HMI</th>
<th scope=col>CEI (F)</th><th scope=col>CEI (S)</th><th scope=col>SPI(t) ES</th>
<th scope=col>SPI(t) Acumen</th><th scope=col>SEI (start)</th><th scope=col></th></tr>
{body_rows}</table></div>"""
    return form + analysis + table + "</div>"


def _group_rollup_panel(latest: Schedule, latest_set: ForecastSet, field: str) -> str:
    """The project forecast RECALCULATED from the group-weighted data points (ADR-0188/0189).

    Rendered under the per-group table when a group field is chosen: the groups' exact
    SPI(t)s weighted by their to-go work re-run IEAC(t) (direct-only AND full-coverage,
    where no-history groups contribute credibility-weighted estimates), and each group's
    throughput extrapolates its own backlog with the LATEST group finish as the project's
    bottleneck answer. Estimates are quantified and labeled (ADR-0189) — never silent."""
    rollup = compute_group_rollup(latest, field)
    if rollup is None:
        return ""
    top = {f.method_id: f.finish for f in latest_set.forecasts}

    def d(v: dt.date | None) -> str:
        return _mdY(v) if v else "—"

    spi_cell = f"{rollup.weighted_spi_t:g}" if rollup.weighted_spi_t is not None else "—"
    spi_all = f"{rollup.weighted_spi_t_all:g}" if rollup.weighted_spi_t_all is not None else "—"
    top_spi = f"{latest_set.spi_t:g}" if latest_set.spi_t is not None else "—"
    coverage = (
        f"{rollup.groups_used} of {rollup.groups_total} groups with to-go work carry a DIRECT "
        f"SPI(t), covering {rollup.covered_to_go} of {rollup.total_to_go} to-go activities; "
        "the full-coverage figure adds the estimated groups below (credibility-weighted)"
    )
    est_block = ""
    if rollup.estimated:
        rows = "".join(
            f"<tr><th scope=row data-no-i18n>{_e(e.group)}</th><td class=num>{e.to_go}</td>"
            f"<td class=num>{e.sei if e.sei is not None else '—'}</td>"
            f"<td class=num>{e.pooled_rate_per_month:g}/mo</td>"
            f"<td class=num>&times;{e.adjustment:g}</td>"
            f"<td><b>{d(e.finish)}</b></td>"
            f"<td class=muted>{d(e.finish_early)} &rarr; {d(e.finish_late)}</td>"
            f'<td class=muted title="{_e(e.basis)}">hover for the full basis</td></tr>'
            for e in rollup.estimated
        )
        est_block = f"""
<h3>Estimated groups &mdash; no completion history yet (credibility-weighted)</h3>
<p class=muted>These groups carry to-go work but have completed nothing, so a finish-anchored
measure has no qualifying data. Instead of flagging them unforecastable, each gets a
<b>quantified estimate</b> built on standard statistical practice: <b>partial pooling /
credibility weighting</b> (B&uuml;hlmann; with zero group observations the credibility weight
on the group's own history is Z&nbsp;=&nbsp;0, so the estimate borrows the <b>pooled
per-activity throughput</b> of the whole project), <b>discounted by the group's own start
execution index</b> (the NDIA PASEG-style start-anchored leading indicator &mdash; work must
start before it can finish, so demonstrated late starting slows the borrowed rate; the
discount only ever penalizes and is floored at &times;0.25), and <b>ranged by
reference-class forecasting</b> (the P75&rarr;P25 per-activity rates the groups WITH history
demonstrated &mdash; Flyvbjerg's outside view). Estimates are labeled everywhere they are
used and are replaced by direct measures the moment the group completes its first
activity.</p>
<table><tr><th scope=col>Group</th><th scope=col>To go</th><th scope=col>SEI</th>
<th scope=col>Borrowed rate</th><th scope=col>Discount</th><th scope=col>Estimated finish</th>
<th scope=col>Early &rarr; late (reference class)</th><th scope=col>Basis</th></tr>
{rows}</table>"""
    unforecastable = ""
    if rollup.unforecastable:
        names = ", ".join(_e(g) for g in rollup.unforecastable[:8])
        more = (
            f" (+{len(rollup.unforecastable) - 8} more)" if len(rollup.unforecastable) > 8 else ""
        )
        unforecastable = (
            f"<p class=muted><b>Unforecastable:</b> {names}{more} &mdash; no data date or no "
            "completions anywhere in the file, so there is nothing to borrow from; estimating "
            "here would be fabrication, not statistics.</p>"
        )
    limiting = (
        f" &mdash; limited by <b data-no-i18n>{_e(rollup.rate_limiting_group)}</b>"
        + (" <span class=exc-note>ESTIMATED</span>" if rollup.rate_finish_is_estimated else "")
        + " (the project finishes when its slowest group finishes)"
        if rollup.rate_limiting_group
        else ""
    )
    # Panel contract: head + chip + take, and NO ⤓ EXCEL — there is no export endpoint for
    # compute_group_rollup anywhere in the app, and _shell_tools omits the button when no
    # export title is given (never a dead link). The take quotes the two SPI(t) cells the
    # table below renders VERBATIM (`spi_all` and `top_spi`, the same strings, same {:g}).
    head = _panel_head(
        "Project rollup &mdash; recalculated from the group-weighted data points",
        tools=_shell_tools(),
        prov=_prov_chip(latest),
    )
    take = f"Rolled up from the groups, SPI(t) reads {spi_all} against the top-down {top_spi}."
    return f"""
<div class=panel>{head}
<p class=sf-take data-no-i18n>{take}</p>
<p class=muted>The per-group figures above, rolled BACK UP into a project-level forecast:
each group's <b>exact SPI(t)</b> is weighted by its <b>to-go activity count</b> (the groups
still carrying the remaining work dominate the index), and each group's own completion
throughput extrapolates its own backlog with the <b>latest</b> group finish as the project's
bottleneck answer. Groups without completion history contribute <b>credibility-weighted
estimates</b> (detailed below) so the rollup covers ALL the remaining work. Compare against
the top-down forecast &mdash; a gap means the remaining work sits in groups performing
differently than the project-wide average suggests.</p>
<table>
<tr><th scope=col>Figure</th><th scope=col>Rollup (direct only)</th>
<th scope=col>Rollup (full coverage)</th>
<th scope=col>Top-down (whole project)</th><th scope=col>Basis</th></tr>
<tr><th scope=row>SPI(t)</th><td class=num>{spi_cell}</td><td class=num><b>{spi_all}</b></td>
<td class=num>{top_spi}</td>
<td class=muted>{_e(rollup.weight_basis)}; {coverage}</td></tr>
<tr><th scope=row>Earned-schedule IEAC(t) finish</th><td>{d(rollup.ieac_finish)}</td>
<td><b>{d(rollup.ieac_finish_all)}</b></td>
<td>{d(top.get("earned_schedule"))}</td>
<td class=muted>IEAC(t) = AT + (PD &minus; ES) / <b>weighted</b> SPI(t)</td></tr>
<tr><th scope=row>Completion-rate finish</th><td colspan=2><b>{d(rollup.rate_finish)}</b></td>
<td>{d(top.get("rate"))}</td>
<td class=muted>each group's own throughput extrapolates its own to-go count; estimated
groups use their credibility-weighted rate{limiting}</td></tr>
</table>
{est_block}
{unforecastable}
<p class=cite>Weighted over {rollup.groups_total} group(s) of &ldquo;{_e(field)}&rdquo; with
to-go work &mdash; {_e(latest.source_file or latest.name)}</p></div>"""


def _where_it_lands_header(sch: Schedule, fset: ForecastSet) -> str:
    """Chapter 09 "Where it lands" (ADR-0207): the data-driven takeaway + a forecast KPI strip +
    the progress-to-finish and method-agreement bars, from the finish-forecast set the page
    already computes (compute_finish_forecasts — no new math). Anchored on the latest version."""
    dated = [f for f in fset.forecasts if f.finish is not None]
    n_methods = len(fset.forecasts)
    cpm_f = next((f for f in fset.forecasts if f.method_id == "cpm"), None)
    cpm_date = cpm_f.finish if cpm_f is not None else None
    dates: list[dt.date] = [f.finish for f in dated if f.finish is not None]
    earliest = min(dates, default=None)
    latest = max(dates, default=None)
    spread = (latest - earliest).days if earliest is not None and latest is not None else None
    var = (
        (cpm_date - fset.planned_finish).days
        if cpm_date is not None and fset.planned_finish is not None
        else None
    )

    def _vs(days: int) -> str:
        if days > 0:
            return f"{days} day{'s' if days != 1 else ''} behind the baseline"
        if days < 0:
            n = -days
            return f"{n} day{'s' if n != 1 else ''} ahead of the baseline"
        return "on the baseline"

    if not dated:
        takeaway = (
            "No forecasting method could place the finish — the loaded files carry neither a "
            "computable network finish nor the progress history the rate methods need."
        )
    else:
        window = (
            f"between {_mdY(earliest)} and {_mdY(latest)}"
            if spread and spread > 0
            else f"at {_mdY(earliest)}"
        )
        cpm_clause = ""
        if cpm_date is not None:
            cpm_clause = f"; CPM logic lands on {_mdY(cpm_date)}"
            if var is not None:
                cpm_clause += f", {_vs(var)}"
        takeaway = f"{len(dated)} of {n_methods} forecasting methods place the finish {window}{cpm_clause}."

    kpi = _stat_cards(
        [
            ("Methods with a date", f"{len(dated)} / {n_methods}"),
            ("CPM finish", _mdY(cpm_date) if cpm_date is not None else "—"),
            ("Earliest", _mdY(earliest) if earliest is not None else "—"),
            ("Latest", _mdY(latest) if latest is not None else "—"),
            ("Spread (days)", str(spread) if spread is not None else "—"),
            ("vs Baseline", f"{var:+d} d" if var is not None else "—"),
        ]
    )
    progress_bar = _status_stack(
        "Progress to the finish",
        f"Activities complete vs still to go as of {_mdY(fset.as_of) if fset.as_of else 'the data date'}.",
        [
            ("Complete", fset.completed_count, "--ok"),
            ("Still to go", fset.remaining_count, "--muted"),
        ],
        f"{fset.completed_count + fset.remaining_count} activities",
    )
    agree_bar = _status_stack(
        "Method agreement",
        "How many independent forecasting methods could place a finish date.",
        [
            ("Placed a date", len(dated), "--ok"),
            ("Inputs missing", n_methods - len(dated), "--muted"),
        ],
        f"{spread}-day spread across the methods" if spread else "methods converge",
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{progress_bar}{agree_bar}</div>'
    )


def _forecast_body(
    schedules: list[Schedule], cpms: list[CPMResult], sets: list[ForecastSet]
) -> str:
    """The multi-method finish-forecast page (M15/ADR-0030): logic vs throughput vs
    performance, the deck's Carnac KPI cards (PBIX p13, ADR-0042), plus per-version drift.

    Panel contract (Mission Ops rank 10, ADR-0298): each content panel wears the headline strip
    + tools + provenance chip + one ``.sf-take``. The deliberate decisions:

    * **⤓ EXCEL points at /export/xlsx/forecast on the cards / methods / drift panels** — that
      workbook is ``TableSet("Finish forecasts", (carnac_table(carnac), *forecast_tables(...)))``,
      i.e. the Carnac card row IS its first sheet and the per-version method grid IS the rest.
      The methodology panel deliberately ships WITHOUT ⤓ EXCEL: its ruler also plots the data
      date and the baseline finish, which no forecast export column carries, so pointing there
      would hand back less than the panel draws.
    * **no ▦ DATA anywhere** — no panel carries a ``.sf-drawer``; the cards, the two method
      tables and the drift table ARE their panels' data (the :func:`_shell_tools` home-shell
      precedent), and inventing a drawer would mean emitting figures this page does not render.
    * **panel-scoped ⛶** — the only chart on this page is the drift stepper's single
      ``#driftChart``, alone in its panel, so one ⛶ can never desync a sibling label. The
      stepper's Prev/Next/Auto-play strip and chartframe.js's own ``⤢`` zoom bar do a
      different job and are left exactly as they are (never a parallel vocabulary).
    * **every take figure is already on the page** — the cards take quotes only the "Tasks to
      complete" and "Latest finish (CPM)" cards; the methods take quotes only the Inputs table's
      own cells; the drift take quotes only cells the drift table itself renders (the version
      labels and the CPM column), selected out of the rendered rows rather than re-derived. No
      delta, no total, no new arithmetic anywhere."""
    latest_sch, latest = schedules[-1], sets[-1]
    carnac = compute_carnac_summary(latest_sch, cpms[-1], latest)
    by_id = latest_sch.tasks_by_id
    method_rows = "".join(
        f"<tr><th scope=col>{_e(f.name)}</th>"
        f"<td><b>{_mdY(f.finish) if f.finish else '—'}</b></td>"
        f"<td class=muted>{_e(f.basis)}</td></tr>"
        for f in latest.forecasts
    )
    inputs = "".join(
        f"<tr><th scope=col>{_e(label)}</th><td>{_e(value)}</td></tr>"
        for label, value in (
            ("Data date", _mdY(latest.as_of) if latest.as_of else "none recorded"),
            ("Completed activities", latest.completed_count),
            ("To-go activities", latest.remaining_count),
            (
                "Historical completion rate",
                # `is not None`: a rate rounding to 0.0 must not display as absent (#67 class)
                f"{latest.rate_per_month:g} / month"
                if latest.rate_per_month is not None
                else "n/a",
            ),
            ("SPI(t)", f"{latest.spi_t:g}" if latest.spi_t is not None else "n/a"),
            (
                "Baseline (planned) finish",
                _mdY(latest.planned_finish) if latest.planned_finish else "n/a",
            ),
        )
    )
    cite = "; ".join(
        f"{by_id[uid].name} (UID {uid})" for uid in latest.citation_uids[:3] if uid in by_id
    )
    # ── The panel contract for this page (see the docstring for the four decisions).
    fc_export = "/export/xlsx/forecast"
    prov = _prov_chip(latest_sch)
    cards_head = _panel_head(
        f"Forecast cards &mdash; {_e(latest_sch.name)}",
        tools=_shell_tools(
            export_title=(
                "Export the finish-forecast workbook (these Carnac cards are its first "
                "sheet) — opens in Excel"
            )
        ),
        prov=prov,
    )
    methods_head = _panel_head(
        f"Finish forecast &mdash; {_e(latest_sch.name)}",
        tools=_shell_tools(
            export_title=("Export the finish forecasts for every loaded version — opens in Excel")
        ),
        prov=prov,
    )
    # Both figures below are ALREADY rendered verbatim by _carnac_cards, read from the same
    # `carnac` object and through the same formatters its cards use: `str(summary.to_go_count)`
    # ("Tasks to complete") and `_mdY(summary.latest_finish)` ("Latest finish (CPM)").
    cards_take = (
        f"{carnac.to_go_count} activities remain to complete, and the schedule logic places "
        f"the latest finish on {_mdY(carnac.latest_finish)}."
    )
    # Already rendered verbatim by the Inputs table below: "Completed activities",
    # "To-go activities" and "Baseline (planned) finish" (same expressions, same guard).
    methods_take = (
        f"{latest.completed_count} activities are complete and {latest.remaining_count} are "
        "still to go against a baseline finish of "
        f"{_mdY(latest.planned_finish) if latest.planned_finish else 'n/a'}."
    )
    drift = cursor = drift_script = ""
    if len(sets) >= 2:
        drift_rows = "".join(
            f"<tr><td>{_e(sch.source_file or sch.name)}</td>"
            f"<td>{_mdY(fs.as_of) if fs.as_of else '-'}</td>"
            + "".join(f"<td>{_mdY(f.finish) if f.finish else '—'}</td>" for f in fs.forecasts)
            + "</tr>"
            for sch, fs in zip(schedules, sets, strict=True)
        )
        drift_head = _panel_head(
            "Forecast drift across versions",
            tools=_shell_tools(
                export_title="Export every version's finish forecasts — opens in Excel"
            ),
            prov=_series_prov_chip(schedules),
        )

        # The take names only cells the drift table itself renders: the first and last row's
        # version label (`_e(sch.source_file or sch.name)`) and their CPM column value — the
        # SAME Forecast object the row's own <td> prints, SELECTED out of the rendered set.
        # Dates only: the table prints no delta, so a "moved N days" figure would be new math.
        def _cpm_cell(fs: ForecastSet) -> str:
            f = next((x for x in fs.forecasts if x.method_id == "cpm"), None)
            return _mdY(f.finish) if (f is not None and f.finish) else "—"

        drift_take = (
            f"Across {_e(schedules[0].source_file or schedules[0].name)} to "
            f"{_e(schedules[-1].source_file or schedules[-1].name)} the schedule-logic finish "
            f"reads {_cpm_cell(sets[0])} then {_cpm_cell(sets[-1])}."
        )
        drift = f"""
<div class=panel data-export="{fc_export}">{drift_head}
<p class=sf-take data-no-i18n>{drift_take}</p>
<p class=muted>The forecasts re-run per loaded version (oldest first). Forecasts that
keep sliding right are the bow-wave signature; methods that diverge from the CPM date tell
you the logic and the observed performance disagree.</p>
<div class=viz-controls>
<button id=prevDrift type=button>&#9664; Prev</button>
<span id=driftLabel class=muted></span>
<button id=nextDrift type=button>Next &#9654;</button>
<button id=driftPlay type=button>&#9654; Auto-play</button>
</div>
<p class=muted>Each forecast marker sits on a <b>locked date axis</b> (held fixed across every
version); step or play to watch the forecasts drift toward later dates as the project
progresses. Faint markers are the prior version's forecasts.</p>
<div id=driftChart class=chart-host></div>
<table><tr><th scope=col>Version</th><th scope=col>Data date</th><th scope=col>CPM</th><th scope=col>As-scheduled</th><th scope=col>Completion rate</th>
<th scope=col>Earned schedule</th></tr>{drift_rows}</table></div>"""
        # ── Claude Design cursor strip (ADR-0464): the drift stepper's own ◀ Prev / label / Next ▶
        # / ▶ Auto-play are RE-HOMED by drift.js into #forecastMaster (same nodes, ids, handlers),
        # ONE chip per version (drift opens on the OLDEST version, so the FIRST chip is on), and a
        # frame pill. The chips carry no id and no census family word (DESIGN-SYSTEM §9).
        chips = "".join(
            f'<button type=button class="cd-chip{" on" if i == 0 else ""}" data-idx="{i}" '
            f'title="{_e(s.source_file or s.name)}" data-no-i18n>v{i + 1}</button>'
            for i, s in enumerate(schedules)
        )
        cursor = f"""
<div class="viz-controls cd-cursor" id=forecastCursor>
<span id=forecastMaster class=cd-master></span>
<span class=cd-chips>{chips}</span>
<span id=forecastFrame class="muted cd-pill" data-no-i18n></span>
<span class="muted cd-note">One cursor &mdash; &#9664; Prev / Next &#9654; / &#9654; Auto-play step the forecast drift through the loaded files, oldest first; a chip jumps to that version.</span>
</div>"""
        drift_script = '<script src="/static/drift.js"></script>'
    cards_panel = f"""<div class=panel data-export="{fc_export}">{cards_head}
<p class=sf-take data-no-i18n>{cards_take}</p>
<p class=muted>The reference deck's <i>Carnac</i> forecast KPIs (PBIX page 13): the project
window, the forecast end dates, the completion rate, remaining and project duration,
SPI(t), Earned Schedule, and the to-go activity count. A card with missing inputs shows
"—" &mdash; never a fabricated value. Every figure reuses the forecast below.</p>
{_user_tip("Independent methods (logic, the source schedule, throughput and performance) forecast the finish; where they disagree, the logic and the observed performance are telling different stories. A method whose inputs are missing shows a dash &mdash; never a fabricated date.")}
{_carnac_cards(carnac)}</div>"""
    methods_panel = f"""<div class=panel data-export="{fc_export}">{methods_head}
<p class=sf-take data-no-i18n>{methods_take}</p>
<p class=muted>Independent answers to "when will it really end": the schedule's own
logic (CPM), the observed completion throughput, and earned-schedule performance
(IEAC(t) = AT + (PD &minus; ES) / SPI(t)). Methods that disagree are themselves a finding.
A method whose inputs are missing shows "—" &mdash; never a fabricated date.</p>
<table><tr><th scope=col>Method</th><th scope=col>Forecast finish</th><th scope=col>Basis</th></tr>{method_rows}</table>
<h3>Inputs</h3><table>{inputs}</table>
<p class=cite>Finish-controlling: {_e(cite)}</p></div>"""
    # ── Claude Design layout (ADR-0464): artboard "09 Where it lands" ─────────────────────────
    # The page is RE-ARRANGED into the design, functionality unchanged (ADR-0451/0456/0460's
    # method): the cursor strip (when two or more versions are loaded), then the design's order —
    # the methodology panel with its ruler full width (the mock's WHERE THE FINISH LANDS), the
    # finish-forecast methods + inputs beside the Carnac cards (the mock's method-card row), the
    # drift stepper + table beside a "How to read this" block whose three beats are this page's
    # own explainer (the mock's FORECAST DRIFT, BY VERSION beside WHICH TO BELIEVE), and the
    # field-forecast panel the route appends after. Every panel is byte-for-byte what it was; the
    # mock's S-curve & finish walk is /scurve's chart and is NOT ported (named in the ADR).
    what, how, decide = _EXPLAINERS["Forecast"]
    beats = "".join(
        f'<div class="cd-beat {cls}"><b>{lead}</b> {_e(text)}</div>'
        for cls, lead, text in (
            ("cd-beat-accent", "What it shows.", what),
            ("cd-beat-warn", "How to read it.", how),
            ("cd-beat-bad", "Why it matters.", decide),
        )
    )
    reading = f'<section class="cd-block cd-read"><h2>How to read this</h2>{beats}</section>'
    row_methods = f'<div class="cd-grid cd-grid-2">{methods_panel}{cards_panel}</div>'
    rows = (
        f'{row_methods}<div class="cd-grid cd-grid-12">{drift}{reading}</div>'
        if drift
        else f"{row_methods}{reading}"
    )
    return f"""{cursor}
{_forecast_explainer(latest, prov=prov)}{rows}{drift_script}
<script src="/static/panelkit.js"></script>"""


def _forecast_data(schedules: list[Schedule], sets: list[ForecastSet]) -> dict[str, object]:
    # LOCKED date axis (item 5) for the drift animation: span every version's
    # forecasts + data dates + baseline finishes, so the time scale is held fixed through
    # the stepper and the forecasts visibly drift right rather than the axis rescaling.
    axis_dates: list[dt.date] = []
    for fs in sets:
        if fs.as_of is not None:
            axis_dates.append(fs.as_of)
        if fs.planned_finish is not None:
            axis_dates.append(fs.planned_finish)
        axis_dates.extend(f.finish for f in fs.forecasts if f.finish is not None)
    axis = {
        "min": min(axis_dates).isoformat() if axis_dates else None,
        "max": max(axis_dates).isoformat() if axis_dates else None,
    }
    # the method order/labels the animation plots (stable, deterministic). ``basis`` rides along
    # (ADR-0310, audit H6): it is mandatory on FinishForecast and exported to Excel, but the payload
    # used to ship only id+name, so the drift chart and its table could not say what basis a date
    # came from even in principle.
    methods = [
        {"id": f.method_id, "name": f.name, "basis": f.basis}
        for f in (sets[-1].forecasts if sets else [])
    ]
    return {
        "axis": axis,
        "methods": methods,
        "versions": [
            {
                "label": sch.source_file or sch.name,
                "as_of": fs.as_of.isoformat() if fs.as_of else None,
                "completed": fs.completed_count,
                "remaining": fs.remaining_count,
                "rate_per_month": fs.rate_per_month,
                "spi_t": fs.spi_t,
                "planned_finish": fs.planned_finish.isoformat() if fs.planned_finish else None,
                "forecasts": {
                    f.method_id: f.finish.isoformat() if f.finish else None for f in fs.forecasts
                },
            }
            for sch, fs in zip(schedules, sets, strict=True)
        ],
    }
