"""The /margin page family - the Executive Margin Dashboard.

Monolith split, phase 3 slice 5 (ADR-0363), extracted VERBATIM from ``web/app.py``: every
function, docstring and comment moves byte-for-byte, only the module boundary changes.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour (the
``/margin`` and ``/api/margin/dashboard`` routes' builders): 10 names / 417 lines whose only
external referrer is ``create_app``, a route, which imports downward and stays put. The
margin-terminology glossary (``_margin_terminology`` + its two handbook-citation constants)
descended into ``web/components.py`` instead of moving here: the /analysis margin panel still
in ``app.py`` needs it too, and a symbol an extracted module needs must live at or below that
module's layer (the ADR-0351 rule - the FIRST slice of a pair forces the descent). The
SRA-side margin machinery (``_margin_risk_data`` and the names only it reaches) stays with
``create_app``: it is route-scoped, and this family's closure never reaches it.

Layering: ``app`` -> ``margin`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

import datetime as dt
import json

from schedule_forensics.engine.cpm import CPMError, CPMResult
from schedule_forensics.engine.margin_dashboard import (
    GOLD_RULE_DAYS_PER_YEAR,
    MarginDashboard,
    MarginMonth,
    compute_margin_dashboard,
)
from schedule_forensics.engine.margin_guideline import (
    FIG_5_30_ROWS,
    MONTH_WORK_DAYS,
    BandPoint,
    GuidelineBandConfig,
    band_position,
    expected_margin_band,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.components import (
    _export_bar,
    _margin_terminology,
    _mdY,
    _panel_head,
    _series_prov_chip,
    _shell_tools,
    _stat_cards,
)
from schedule_forensics.web.state import SessionState

# ── Executive Margin Dashboard (NASA Margin/Contingency Burn-Down + Margin Erosion Trend) ──────


def _solvable_scoped_versions(st: SessionState) -> list[tuple[str, Schedule, CPMResult]]:
    """Loaded versions oldest→newest whose network solves, each as (label, scoped schedule,
    cpm) — the ONE population rule the margin dashboard computes from AND the provenance chip
    describes (codex-review round, ADR-0327 addendum: a chip built from the raw loaded list
    could name an unschedulable version that contributes no row or chart point)."""
    versions: list[tuple[str, Schedule, CPMResult]] = []
    for key, raw in st.ordered_versions():
        try:
            a = st.analysis_for(key, raw)
        except CPMError:
            continue
        versions.append((raw.source_file or raw.name, a.scoped, a.cpm))
    return versions


def _margin_dashboard_for(st: SessionState) -> MarginDashboard:
    """Build the margin/contingency dashboard from the loaded versions (oldest -> newest), scoped to
    the active group/filter, measured to the session target milestone (else the project finish)."""
    return compute_margin_dashboard(
        _solvable_scoped_versions(st),
        target_uid=st.target_uid,
        gold_rule_per_year=st.margin_rate,
        margin_uids=st.confirmed_margin_union(),
    )


def _margin_dashboard_data(d: MarginDashboard) -> dict[str, object]:
    return {
        "have_margin_tasks": d.have_margin_tasks,
        "erosion_wd_per_month": d.erosion_wd_per_month,
        "zero_margin_date": d.zero_margin_date,
        "erosion_r2": d.erosion_r2,
        "erosion_basis_wmpd": d.erosion_basis_wmpd,
        "erosion_mixed_basis": list(d.erosion_mixed_basis),
        "gold_rule_per_year": d.gold_rule_per_year,
        "months": [
            {
                "label": m.label,
                "status_date": m.status_date,
                "target_name": m.target_name,
                "target_finish": m.target_finish,
                "zero_margin_finish": m.zero_margin_finish,
                "effective_margin_wd": m.effective_margin_wd,
                "total_margin_wd": m.total_margin_wd,
                "planned_margin_wd": m.planned_margin_wd,
                "consumed_wd": m.consumed_wd,
                "consumed_pct": m.consumed_pct,
                "corrective_action": m.corrective_action,
                "margin_cd": m.margin_cd,
                "contingency_wd": m.contingency_wd,
                "total_available": m.total_available,
                "days_to_go": m.days_to_go,
                "nasa_rqmt_wd": m.nasa_rqmt_wd,
                "pct_available": m.pct_available,
                "pct_effective": m.pct_effective,
                "below_requirement": m.below_requirement,
            }
            for m in d.months
        ],
    }


def _wmpd_label(wmpd: int) -> str:
    """Human label for a working-minutes-per-day basis (480 -> '8h/day', 1440 -> '24h/day')."""
    if wmpd % 60 == 0:
        return f"{wmpd // 60}h/day"
    return f"{wmpd}-min/day"


def _margin_dashboard_header(d: MarginDashboard) -> str:
    """The data-driven takeaway + KPI strip: latest effective margin vs the NASA requirement, the
    trigger state, and the erosion projection. Every figure comes from the engine (no new math)."""
    dated = [m for m in d.months if m.status_date is not None]
    latest = dated[-1] if dated else None
    if latest is None:
        takeaway = (
            "Load monthly schedule versions (each carrying a status date) to track how schedule "
            "margin is being consumed against the plan."
        )
        return f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'

    target = latest.target_name or "the project finish"
    if not d.have_margin_tasks:
        takeaway = (
            f'No schedule-margin activity (an activity named "margin") was found in the loaded '
            f"versions, so effective margin to {target} reads 0. Name the buffer activities "
            '"…margin…" so the burn-down can measure the reserve protecting the date.'
        )
    elif latest.below_requirement:
        takeaway = (
            f"Effective margin to {target} is {latest.effective_margin_wd:g} work days as of "
            f"{_mdY(latest.status_date)} — BELOW the NASA Gold-Rule requirement of "
            f"{latest.nasa_rqmt_wd:g} — a trigger to enact contingency or buy back schedule."
        )
    else:
        takeaway = (
            f"Effective margin to {target} is {latest.effective_margin_wd:g} work days as of "
            f"{_mdY(latest.status_date)} — at or above the {latest.nasa_rqmt_wd:g}-day NASA "
            "Gold-Rule requirement."
        )
    if d.erosion_mixed_basis:
        bases = " vs ".join(_wmpd_label(w) for w in d.erosion_mixed_basis)
        takeaway += (
            f" The margin-erosion trend is not shown: the loaded versions express margin in "
            f"different work-day bases ({bases}) because the schedule calendar changed, so a "
            "single erosion rate would conflate the two — compare margin within one calendar basis."
        )
    elif d.zero_margin_date is not None and d.erosion_wd_per_month:
        takeaway += (
            f" At the current erosion of {d.erosion_wd_per_month:g} work days per month, margin "
            f"reaches zero around {_mdY(d.zero_margin_date)}."
        )
    # 50%-consumed corrective-action trigger, quoted from the handbook: "The corrective action
    # threshold is set where the margin is 50% consumed" — §7.3.3.2.3 Sufficiency of Margin
    # (printed p.324), where it is the handbook's EXAMPLE-case threshold choice (citation
    # corrected from ADR-0230's §7.3.3.1.6, ADR-0254; the flag's behavior is unchanged).
    if latest.corrective_action and latest.consumed_pct is not None:
        takeaway += (
            f" {round(100 * latest.consumed_pct)}% of the planned margin was consumed this period — "
            "at or past the 50%-consumed corrective-action threshold (the Schedule Management "
            "Handbook's example threshold, §7.3.3.2.3); enact a corrective action (watch / "
            "re-plan / re-baseline)."
        )

    trigger = "TRIGGERED" if (latest.below_requirement or latest.corrective_action) else "OK"
    consumed_txt = (
        f"{round(100 * latest.consumed_pct)}%" if latest.consumed_pct is not None else "—"
    )
    kpi = _stat_cards(
        [
            ("Effective margin (wd)", f"{latest.effective_margin_wd:g}"),
            ("Total margin (wd)", f"{latest.total_margin_wd:g}"),
            ("NASA requirement (wd)", f"{latest.nasa_rqmt_wd:g}"),
            ("Contingency (days)", str(latest.contingency_wd)),
            ("Consumed this period", consumed_txt),
            (
                "Erosion (wd/month)",
                f"{d.erosion_wd_per_month:g}" if d.erosion_wd_per_month else "—",
            ),
            ("Zero-margin date", _mdY(d.zero_margin_date) if d.zero_margin_date else "—"),
            ("Trigger for action", trigger),
        ]
    )
    lede = (
        f"Measured to <b>{_e(target)}</b> across {len(dated)} dated version"
        f"{'' if len(dated) == 1 else 's'}, against the NASA Gold-Rule requirement of "
        f"{d.gold_rule_per_year:g} work days per program year. Effective margin is the "
        "buffer that actually protects the date; the erosion rate and zero-margin date are "
        "projections from the versions loaded, not forecasts of intent."
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        f'<p class="page-lede">{lede}</p><div class="ws-kpi">{kpi}</div>'
    )


def _margin_rate_control(rate: float) -> str:
    """F3c operator control: the NASA Gold-Rule margin-requirement rate (work-days per program year)
    the dashboard measures effective margin against. 30/yr is the Schedule Management Handbook
    default, but the handbook states margin as a program-managed guideline, so the rate is
    operator-parameterized here — a GET form persists it on the session (fail-soft on a bad value),
    and the requirement line, the per-version ``NASA rqmt`` column, the trigger, and the export all
    follow it. The verbatim 50%-consumed corrective threshold stays fixed (it is not a guideline)."""
    reset = (
        ""
        if rate == GOLD_RULE_DAYS_PER_YEAR
        else f' <a class="btn-link" href="/margin?rate={GOLD_RULE_DAYS_PER_YEAR:g}" '
        f"data-no-i18n>Reset to {GOLD_RULE_DAYS_PER_YEAR:g}</a>"
    )
    return (
        '<div class="panel"><form method="get" action="/margin" class="viz-controls">'
        "<label data-no-i18n>NASA Gold-Rule margin requirement: "
        f'<input name="rate" type="number" min="1" max="365" step="0.5" value="{rate:g}" '
        'title="Work-days of margin per program year the requirement expects '
        '(days-to-go x rate / 365)"> work-days / program year</label> '
        '<button type="submit">Apply</button>'
        f"{reset}"
        '<p class="muted" data-no-i18n style="margin:.4em 0 0;font-size:12px">The NASA requirement '
        "line is <b>days-to-go &times; rate &divide; 365</b>. <b>30</b>/yr is the Schedule Management "
        "Handbook &ldquo;Gold Rule&rdquo; default; a program may set a different guideline, so the "
        "rate is parameterized here &mdash; the burn-down requirement line, the per-version "
        "<i>NASA&nbsp;rqmt</i> column, the trigger flag, and the Excel/Word export all follow it.</p>"
        "</form></div>"
    )


def _band_payload(st: SessionState, d: MarginDashboard) -> dict[str, object] | None:
    """The Fig 5-30 guideline-band overlay for the burn-down chart + table (ADR-0254), or ``None``
    when the operator has not entered the phase dates (the band is simply absent — never derived).

    Evaluates the stepped band at every dated version's status date plus the phase boundaries;
    classifies each dated month via :func:`band_position`. Month verdicts are SUPPRESSED (None)
    when the versions mix work-day bases — comparing one band against two different "work day"
    units would conflate them, the same refusal the erosion fit makes (disclosed, not fabricated).
    """
    if st.margin_band_dates is None:
        return None
    try:
        cfg = GuidelineBandConfig(
            phase_dates=(
                dt.date.fromisoformat(st.margin_band_dates[0]),
                dt.date.fromisoformat(st.margin_band_dates[1]),
                dt.date.fromisoformat(st.margin_band_dates[2]),
                dt.date.fromisoformat(st.margin_band_dates[3]),
            ),
            rates=st.margin_band_rates,
        )
    except ValueError:
        return None  # fail-soft: a corrupted stored config renders no band, never a wrong one
    dated = [(m.status_date, m.effective_margin_wd) for m in d.months if m.status_date]
    points = expected_margin_band(cfg, tuple(dt.date.fromisoformat(s) for s, _ in dated))
    by_date: dict[str, BandPoint] = {p.date.isoformat(): p for p in points}
    mixed = bool(d.erosion_mixed_basis)
    months = []
    for iso, eff in dated:
        p = by_date[iso]
        months.append(
            {
                "date": iso,
                "low_wd": p.low_wd,
                "high_wd": p.high_wd,
                "position": None if mixed else band_position(eff, p.low_wd, p.high_wd),
            }
        )
    return {
        "points": [
            {"date": p.date.isoformat(), "low_wd": p.low_wd, "high_wd": p.high_wd} for p in points
        ],
        "months": months,
        "mixed_basis": mixed,
        "dates": list(st.margin_band_dates),
        "rates": [list(r) for r in st.margin_band_rates],
        "month_work_days": MONTH_WORK_DAYS,
    }


def _margin_band_control(st: SessionState) -> str:
    """The Fig 5-30 guideline-band operator control (F3c-fuller, ADR-0254): the three verbatim
    handbook rows beside editable (low, high) wd/yr rates, the four phase-boundary date inputs
    (program facts — never auto-filled), and the §7.3.3.2.3 Watch / Corrective-Action percentile
    thresholds. Every default is cited; the conversion convention is stated on the panel."""
    dts = st.margin_band_dates or ("", "", "", "")
    date_labels = (
        "Confirmation Review",
        "Start of Integration &amp; Test",
        "Delivery to Launch Site",
        "Launch",
    )
    date_inputs = " ".join(
        f'<label data-no-i18n>{lbl} <input type=date name=phase{i} value="{_e(dts[i])}"></label>'
        for i, lbl in enumerate(date_labels)
    )
    rate_rows = "".join(
        f"<tr><td class=muted data-no-i18n>{_e(frm)} &rarr; {_e(to)}</td>"
        f"<td class=muted data-no-i18n>&ldquo;{_e(amount)}&rdquo;</td>"
        f'<td><input type=number name=low{i} min=1 max=365 step=0.5 value="{st.margin_band_rates[i][0]:g}" style="width:5em">'
        f' &ndash; <input type=number name=high{i} min=1 max=365 step=0.5 value="{st.margin_band_rates[i][1]:g}" style="width:5em"> wd/yr</td></tr>'
        for i, (frm, to, amount) in enumerate(FIG_5_30_ROWS)
    )
    watch, ca = st.margin_risk_pcts
    return f"""
<div class=panel><h2 data-no-i18n>Expected margin &mdash; Figure 5-30 guideline band</h2>
<p class=muted data-no-i18n>The NASA SMH's "Established standards for margin allocation" (Figure 5-30,
&sect;5.5.11.2) give per-phase margin <b>rate ranges</b> &mdash; each explicitly "Varies" (program-defined).
Enter the program's phase-boundary dates to draw the stepped expected-margin band on the burn-down
(&sect;7.3.3.1.6, Fig 7-32: "stepped burndowns that mimic the margin guidelines over time"). Rates are
editable; the prefills convert the handbook ranges at the tool's disclosed convention
<b>1 month = {MONTH_WORK_DAYS:g} work days</b> (the ADR-0230/0253 Gold-Rule reading; row 3 lists three
alternatives &mdash; the prefill spans their extremes). A month below the band is flagged as a
<b>guideline deviation</b> (&sect;7.3.3.1.6 Thresholds: deviations "trigger a requirement for either an
explanation&hellip; or&hellip; activities to mitigate the trend" &mdash; thresholds themselves are program-set
in the SMP).</p>
<form method=post action="/margin/band" class=viz-controls>
<table class=card-table><tr><th scope=col>Phase (Fig 5-30)</th><th scope=col>Handbook amount (verbatim)</th><th scope=col>Rate (wd / program year)</th></tr>
{rate_rows}</table>
<p style="margin:.5em 0 0">{date_inputs}</p>
<p style="margin:.5em 0 0" data-no-i18n><label>Watch percentile <input type=number name=watch_pct min=1 max=99 step=1 value="{watch:g}" style="width:4em">%</label>
<label>Corrective-Action percentile <input type=number name=ca_pct min=1 max=99 step=1 value="{ca:g}" style="width:4em">%</label>
<span class=muted>(the handbook's <i>example</i> thresholds &mdash; Fig 7-45 prose / &sect;7.3.3.2.1; program-set per the SMP)</span></p>
<p style="margin:.5em 0 0"><button type=submit name=action value=apply>Apply band</button>
<button type=submit name=action value=clear>Clear</button></p>
</form></div>"""


def _margin_risk_panel(st: SessionState) -> str:
    """The §7.3.3.2.3 risk-based margin-sufficiency panel shell (F3c tier-b, ADR-0254). The SRA
    run is OFF the page-load path — clicking the button fetches ``/api/margin/risk`` (the repo's
    SRA doctrine); the shell only carries the cited explanation and the result container.

    Rank 12 (ADR-0327): the panel wears the head strip with ⛶ ENLARGE only. ⤓ EXCEL is
    deliberately refused — the Zero-margin toggle switches which curve the result shows while
    ``panelkit.js`` follows a STATIC ``data-export``, so a pinned URL would export the default
    curve while the operator looks at the Fig 7-43 one (the round-10 live-state defect class);
    the page's export bar carries the parameterized export instead. No provenance chip either:
    the fetched result echoes its own run parameters in-panel, and a static chip could
    contradict them."""
    watch, ca = st.margin_risk_pcts
    return f"""
<div class=panel>{_panel_head("Risk-based margin sufficiency (SRA)", tools=_shell_tools(), h2_attrs=" data-no-i18n")}
<p class=muted data-no-i18n>&sect;7.3.3.2.3 (Sufficiency of Margin): "using a stochastic tracking curve
takes the results from a routine SRA and plots the results against organizational margin
requirements." Runs the seeded SSI SRA (same engine and inputs as the Risk Analysis page), then reads
the finish distribution against the deterministic margin window &mdash; the all-ML finish <b>D</b> and
the same solve with the margin activities zeroed <b>E</b>. The <b>covered percentile</b> is the fraction
of simulated finishes the margin absorbs; it is classified against the operator thresholds
(Watch {watch:g}% / Corrective {ca:g}% &mdash; the handbook's <i>example</i> values, editable above).
By default the simulation carries the margin activities in-network at their plan durations;
<b>Zero-margin curve</b> (ADR-0266) instead runs them at zero duration in every iteration &mdash;
the handbook's Fig 7-43 basis, "Current Plan, Zero Margin, With Risks" &mdash; read against the
same [E, D] window. Duration uncertainty and risks come from the Risk Analysis page inputs.</p>
<p><button type=button id=marginRiskRun>Run margin-sufficiency SRA</button>
<label class=muted><input type=checkbox id=marginRiskZero value=1
title="Run the handbook-faithful Fig 7-43 curve: every margin activity at zero duration in every iteration (ADR-0266). The margin window [E, D] and thresholds are unchanged — only the curve&#39;s basis moves, and the result names it."> Zero-margin curve (Fig 7-43)</label>
<span id=marginRiskStatus class=muted aria-live=polite></span></p>
<div id=marginRisk></div></div>"""


def _margin_dashboard_body(st: SessionState) -> str:
    """The Margin Dashboard page: the takeaway + KPI header, the operator rate control (F3c), the
    Fig 5-30 band control + risk-sufficiency panel (F3c-fuller, ADR-0254), the two reference charts
    (burn-down + erosion trend), the per-version table, and the embedded dataset
    margin_dashboard.js reads.

    Panel contract (rank 12 toolbar sweep, ADR-0327): the two charts and the per-version table
    wear the headline strip + tools + the whole-series provenance chip, with ⤓ EXCEL on all
    three pointing at the ONE existing margin workbook (/export/xlsx/margin — the per-version
    figures ARE its first sheet and the erosion summary its second). The deliberate refusals:

    * **no ⤓ on the risk-sufficiency panel** — its Zero-margin toggle changes which curve the
      panel shows while ``panelkit.js`` reads a STATIC ``data-export``; a pinned URL would hand
      the operator the default curve while they are looking at the Fig 7-43 one (the round-10
      /performance live-state defect class). The export bar at the top of the page is the
      export path for that read.
    * **no ▦ DATA anywhere** — the per-version table IS the two charts' data, rendered on the
      same page (the home-shell precedent); a drawer would duplicate it.
    * the rate and band panels are OPERATOR CONTROLS (forms), not data visuals — no toolbar."""
    d = _margin_dashboard_for(st)
    data = _margin_dashboard_data(d)
    data["band"] = _band_payload(st, d)
    blob = json.dumps(data).replace("<", "\\u003c")
    # the chip describes the SAME population the dashboard computed from — the solvable
    # subset — never the raw loaded list (codex-review round; analyses are cached, so this
    # re-walk costs nothing beyond what _margin_dashboard_for already paid)
    prov = _series_prov_chip([s for _lbl, s, _c in _solvable_scoped_versions(st)])
    margin_tools = _shell_tools(
        export_title=(
            "Export the margin dashboard workbook (per-version figures + erosion summary) — "
            "opens in Excel"
        )
    )

    def _row(m: MarginMonth) -> str:
        pct = f"{100 * m.pct_available:.1f}%" if m.pct_available is not None else "—"
        sd = _mdY(m.status_date) if m.status_date else "—"
        planned = f"{m.planned_margin_wd:g}" if m.planned_margin_wd is not None else "—"
        consumed = f"{m.consumed_wd:g}" if m.consumed_wd is not None else "—"
        trig = "&#9888; trigger" if m.below_requirement else "ok"
        corr = "&#9888; 50%+" if m.corrective_action else "—"
        return (
            f"<tr{' class=below' if m.below_requirement else ''}><td>{_e(sd)}</td>"
            f"<td class=num>{planned}</td>"
            f"<td class=num>{m.effective_margin_wd:g}</td>"
            f"<td class=num>{m.total_margin_wd:g}</td>"
            f"<td class=num>{consumed}</td>"
            f"<td class=num>{m.contingency_wd}</td>"
            f"<td class=num>{m.total_available:g}</td>"
            f"<td class=num>{m.nasa_rqmt_wd:g}</td>"
            f"<td class=num>{m.days_to_go}</td>"
            f"<td class=num>{pct}</td><td>{corr}</td><td>{trig}</td></tr>"
        )

    rows = "".join(_row(m) for m in d.months)
    r2 = d.erosion_r2
    fit = f" (R&sup2; {r2:.2f})" if r2 is not None else ""
    return (
        _margin_dashboard_header(d)
        + _export_bar("margin")
        + _margin_rate_control(st.margin_rate)
        + _margin_band_control(st)
        + '<div class="panel" data-export="/export/xlsx/margin">'
        + _panel_head(
            "Margin &amp; Contingency Burn-Down",
            tools=margin_tools,
            prov=prov,
            h2_attrs=" data-no-i18n",
        )
        + _margin_terminology()
        + '<p class="muted" data-no-i18n>Per status date: effective schedule <b>margin</b> (work days) '
        "stacked with <b>contingency</b> (weekends + holidays to the target), against the NASA "
        "Gold-Rule requirement line. A red bar is a month where margin has fallen below the "
        "requirement &mdash; the trigger for action. The dashed <b>planned</b> line traces the "
        "period-start margin carried forward; a &#9650; marker flags a month where half or more of "
        "the planned margin was consumed (the 50%-consumed corrective-action threshold &mdash; the "
        "Schedule Management Handbook's <i>example</i> threshold, &sect;7.3.3.2.3; thresholds are "
        "program-set in the SMP). <b>Total margin</b> (sum of the "
        "margin activities&rsquo; durations) and <b>effective margin</b> (the buffer on the driving "
        "chain) can differ &mdash; both are reported.</p>"
        '<div class="chart-host" id="marginBurndownChart"></div></div>'
        '<div class="panel" data-export="/export/xlsx/margin">'
        + _panel_head(
            "Margin Erosion Trend (MET)",
            tools=margin_tools,
            prov=prov,
            h2_attrs=" data-no-i18n",
        )
        + f'<p class="muted" data-no-i18n>Effective margin (work days) over the status dates with a '
        f"least-squares erosion line extrapolated to zero{fit}. The projected zero-margin date is "
        "the honest linear read of the current trend, not a commitment.</p>"
        '<div class="chart-host" id="marginErosionChart"></div></div>'
        + _margin_risk_panel(st)
        + '<div class="panel" data-export="/export/xlsx/margin">'
        + _panel_head(
            "Per-version figures",
            tools=margin_tools,
            prov=prov,
            h2_attrs=" data-no-i18n",
        )
        + '<p class="muted" data-no-i18n>One row per loaded status date — the exact figures the '
        "two charts above draw: planned / effective / total margin, the consumed slice, the "
        "calendar contingency, the NASA requirement at that date, and the corrective-action and "
        "trigger flags. <b>⤓ EXCEL</b> exports these rows (plus the erosion summary) as one "
        "workbook.</p>"
        "<table><tr><th scope=col>Status date</th><th scope=col>Planned (wd)</th>"
        "<th scope=col>Effective (wd)</th><th scope=col>Total (wd)</th><th scope=col>Consumed</th>"
        "<th scope=col>Contingency</th><th scope=col>Total avail.</th>"
        "<th scope=col>NASA rqmt (wd)</th><th scope=col>Days-to-go</th>"
        "<th scope=col>% available</th><th scope=col>Corrective</th><th scope=col>Trigger</th></tr>"
        f"{rows or '<tr><td colspan=12 class=muted>No dated versions loaded.</td></tr>'}</table></div>"
        f'<script type="application/json" id=marginDashData>{blob}</script>'
        # defer: the layout emits chartframe.js AFTER <main>, and margin_dashboard.js now calls
        # SFChartFrame.axisTitles at render time (ADR-0325) — same load-order defect and same fix
        # as resources.js / performance.js (ADR-0316, the blob-driven-module defer family)
        '<script defer src="/static/margin_dashboard.js"></script>'
        '<script src="/static/panelkit.js"></script>'
    )
