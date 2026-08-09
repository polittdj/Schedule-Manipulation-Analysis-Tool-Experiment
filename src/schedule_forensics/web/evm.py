"""The /evm page family: how the work is executing against the baseline — earned value.

Monolith split, phase 3 slice 13 (ADR-0377), extracted VERBATIM from ``web/app.py``: every
function, docstring and comment moves byte-for-byte, only the module boundary changes.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour
(the ``/evm`` and ``/export/{fmt}/evm`` routes): SIX names / one contiguous block — the
"How we execute" chapter-07 header, the EVM page body, the index/days stat-card formatters,
the "what these EVM numbers mean" explainer, and the PASS/FAIL/N-A threshold legend (its
sole referrer is the body — the closure found it, the prefix census never did).
``_metric_scorecard_table`` DESCENDS to ``web/components.py`` in the same commit (ADR-0351's
rule: needed by a mover AND by ``_groups_body``, which stays with the queued /groups page).
Every external referrer of the movers is a ``create_app`` route, which imports downward and
stays put; ``evm_view`` reaches the family through ``web.app``'s re-export, and
``_field_forecast_panel`` (served on /evm too) is already below in ``web/forecast.py``
(ADR-0374). The export route contributes NO movers: it builds its tables from the engine
(``compute_evm_indices`` / ``compute_schedule_variance``) and the shared export machinery,
all multi-family stays — the mission shape, fifth consecutive slice.

Layering: ``app`` -> ``evm`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

from schedule_forensics.engine.metrics import compute_baseline_compliance, compute_bei
from schedule_forensics.engine.metrics._common import CheckStatus, MetricResult, non_summary
from schedule_forensics.engine.metrics.evm import compute_evm_indices, compute_schedule_variance
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.components import (
    _ANALYSIS_XLSX_TITLE,
    _analysis_export_attr,
    _latest_solvable,
    _metric_scorecard_table,
    _panel_head,
    _prov_chip,
    _shell_tools,
    _stat_cards,
    _task_name_across,
    _user_tip,
)
from schedule_forensics.web.state import SessionState


def _threshold_legend() -> str:
    """Explain, on-page, why some measures read PASS/FAIL and others N/A, and how the on-time
    thresholds were derived (operator 2026-07-08: "define for the user what those are and how you
    calculated them")."""
    return (
        "<details class=threshold-legend><summary>How these PASS / FAIL / N&#47;A results are "
        "scored</summary><div class=threshold-legend-body>"
        "<p><b>On-time execution indices</b> (Baseline Finish/Start Compliance, Completed/Started "
        "On&nbsp;Time, CEI Finish/Start) score <b>PASS at &ge; 95%</b>. That bar is the DCMA "
        "14-Point Assessment's Baseline-Execution-Index / CPLI standard (0.95), reinforced by the "
        "GAO Schedule Assessment Guide (GAO-16-89G, Best Practice&nbsp;9); these indices are the "
        "same on-time-delivery family, so they inherit the same threshold (ADR-0161).</p>"
        "<p><b>Late mirrors</b> (Completed&nbsp;Late, Started&nbsp;Late) score <b>PASS at &le; 5%</b> "
        "&mdash; the complement of the 95% on-time bar.</p>"
        "<p><b>Informational counts</b> (Forecast to be Finished/Started, Not Started, Not "
        "Completed) carry <b>no pass/fail</b> &mdash; they are denominators / status counts, not "
        "quality gates, so they read <b>N&#47;A</b> by design.</p>"
        "<p><b>Cost indices</b> (SPI, CPI, TCPI) read <b>N&#47;A</b> only when the schedule is not "
        "cost-loaded &mdash; a <i>data limitation of the file</i>, not a missing threshold. On a "
        "cost-loaded schedule they score against 1.0. A fabricated number is never shown in place "
        "of a genuinely undefined one.</p>"
        "<p class=muted>Every threshold and its derivation is in the "
        '<a href="/help">Metric Dictionary</a>; hover any measure name for its own tooltip.</p>'
        "</div></details>"
    )


def _evm_idx_str(m: MetricResult | None) -> str:
    """A rounded index value for an EVM stat card; em dash when the metric is NOT_APPLICABLE."""
    if m is None or str(m.status) == "NA":
        return "—"
    return f"{round(m.value, 2)}"


def _evm_days_str(v: float | None) -> str:
    return "—" if v is None else f"{v:g}"


def _evm_explainer() -> str:
    """Collapsible "what these EVM numbers mean" guidance, including how EVM relates to a JCL."""
    return """
<div class=panel><h2>What these EVM numbers mean</h2>
<details class=explainer><summary><b>Schedule-based EVM</b> (always available)</summary>
<p><b>Earned Schedule SPI(t)</b> = Earned Schedule &divide; Actual Time. Unlike the cost-based SPI
(which mathematically returns to 1.0 as a late project finishes), SPI(t) stays meaningful to the end.
<b>SVt</b> = ES &minus; AT in working days (negative = behind the baseline plan).</p>
<p><b>CEI (Finish / Start)</b> &mdash; the Current Execution Index: of the activities the baseline said
should have finished (started) by now, how many actually did, on time. <b>Baseline compliance</b>
(BFC / BSC) measures the same idea against the baseline finish/start dates.</p></details>
<details class=explainer><summary><b>Cost-based EVM</b> (needs a cost-loaded schedule)</summary>
<p><b>SPI</b> = BCWP &divide; BCWS (value earned vs planned). <b>CPI</b> = BCWP &divide; ACWP (value earned
per dollar spent). <b>TCPI</b> = (BAC &minus; BCWP) &divide; (BAC &minus; ACWP) &mdash; the cost efficiency
the remaining work must hit to land on budget. These read <b>N/A</b> until the schedule carries task
budgets and actual costs; the tool never fabricates a cost figure (Law&nbsp;2).</p></details>
<details class=explainer><summary><b>How EVM relates to a JCL</b></summary>
<p>A <b>JCL</b> (Joint Confidence Level) is a Monte-Carlo over a <b>cost-loaded, risk-loaded</b> schedule
&mdash; the joint probability of finishing at or below a cost AND on or before a date. EVM here gives
you the deterministic cost+schedule performance to date; once a schedule is cost-loaded, those cost
indices populate and the <a href="/sra">Risk Analysis</a> page's <b>JCL panel</b> runs the full joint
cost+schedule Monte-Carlo (ADR-0269). Without cost it stays a schedule-only confidence level (SCL).
See the JCL explainer on the Risk Analysis page.</p></details>
</div>"""


def _how_we_execute_evm_header(st: SessionState) -> str:
    """Chapter 07 "How we execute" story header for the EVM beat (Mission Ops rank 4,
    prototype screens 'px'/'ev'): the data-driven takeaway h1 + muted lede + the ws-kpi
    strip. Every figure is QUOTED from the same MetricResult values the page's scorecard
    tables already show (compute_evm_indices / compute_schedule_variance / compute_bei —
    presentation only; the EVM numbers are parity-locked). A comparative clause appears
    ONLY when the engine's own threshold/status asserts it — never an invented trend
    word. Empty when nothing analyzable is loaded (the body shows the load prompt); the
    chapter kicker itself comes from _page's spine resolution ("EVM" -> Chapter 07)."""
    chosen = _latest_solvable(st)
    if chosen is None:
        return ""
    _key, sch, cpm = chosen
    indices = compute_evm_indices(sch, cpm)
    sv = compute_schedule_variance(sch, non_summary(sch))
    bei = compute_bei(sch)
    spi_t = indices.get("spi_t")
    cpi = indices.get("cpi")

    parts: list[str] = []
    if bei.population:
        clause = f"baselined-due work is finishing at BEI {bei.value:.2f}"
        if bei.threshold is not None and bei.status is CheckStatus.FAIL:
            clause += f" — below the {bei.threshold:g} execution bar"
        elif bei.threshold is not None and bei.status is CheckStatus.PASS:
            clause += f" — meeting the {bei.threshold:g} execution bar"
        parts.append(clause)
    if spi_t is not None and spi_t.status is not CheckStatus.NOT_APPLICABLE:
        parts.append(f"Earned-Schedule SPI(t) reads {round(spi_t.value, 2)}")
    if sv.svt_days is not None:
        parts.append(f"SVt {sv.svt_days:+g} working days")
    if cpi is not None and cpi.status is not CheckStatus.NOT_APPLICABLE:
        parts.append(f"CPI {round(cpi.value, 2)}")
    if parts:
        sent = "; ".join(parts) + "."
        takeaway = sent[0].upper() + sent[1:]
    else:
        takeaway = (
            "No earned-value figure is defined for this file yet — it carries no "
            "baselined-due work and no cost loading to measure (a value is never imputed)."
        )

    kpi = _stat_cards(
        [
            ("SPI(t) — Earned Schedule", _evm_idx_str(indices.get("spi_t"))),
            ("SPI(t) — Acumen", _evm_idx_str(indices.get("spi_t_acumen"))),
            ("BEI (throughput)", f"{bei.value:.2f}" if bei.population else "—"),
            ("SVt (working days)", _evm_days_str(sv.svt_days)),
            ("CPI (cost)", _evm_idx_str(cpi)),
            ("TCPI (cost to-go)", _evm_idx_str(indices.get("tcpi"))),
        ]
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        '<p class="page-lede">How the work is actually executing against the baseline plan '
        "&mdash; the earned-value view. The schedule-based Earned-Schedule metrics always "
        "compute; the cost indices (SPI / CPI / TCPI) join in when the file is cost-loaded. "
        "Every figure below is read verbatim from the loaded file&rsquo;s computed metrics.</p>"
        f'<div class="ws-kpi">{kpi}</div>'
    )


def _evm_body(st: SessionState) -> str:
    """Earned Value Management page: schedule-based EVM always, plus cost EVM when the schedule is
    cost-loaded (else gracefully N/A), baseline compliance, and the worst finish variances."""
    chosen = _latest_solvable(st)
    if chosen is None:
        return (
            "<div class=panel>Load an analyzable schedule to see its earned-value metrics "
            "&mdash; SPI(t), schedule variance, baseline compliance, and (if the schedule is "
            "cost-loaded) SPI / CPI / TCPI.</div>"
        )
    key, sch, cpm = chosen
    indices = compute_evm_indices(sch, cpm)
    sv = compute_schedule_variance(sch, non_summary(sch))
    compliance = compute_baseline_compliance(sch, cpm)
    cost_loaded = any((t.budgeted_cost or 0.0) > 0 for t in non_summary(sch))

    # explicit str keys: newer mypy infers the comprehension key type as a Literal union,
    # which does not unify with _metric_scorecard_table's dict[str, MetricResult]
    sched_idx: dict[str, MetricResult] = {
        k: indices[k] for k in ("spi_t", "spi_t_acumen", "cei_finish", "cei_start") if k in indices
    }
    cost_idx: dict[str, MetricResult] = {
        k: indices[k] for k in ("spi", "cpi", "tcpi") if k in indices
    }

    cards = _stat_cards(
        [
            ("SPI(t) — Earned Schedule", _evm_idx_str(indices.get("spi_t"))),
            ("SPI(t) — Acumen", _evm_idx_str(indices.get("spi_t_acumen"))),
            ("SVt (working days)", _evm_days_str(sv.svt_days)),
            ("Earned Schedule (wd)", _evm_days_str(sv.es_days)),
            ("Actual Time (wd)", _evm_days_str(sv.at_days)),
        ]
    )

    if sv.worst:
        worst_rows = "".join(
            f"<tr><td class=num>{w.unique_id}</td>"
            f"<td>{_e(_task_name_across([sch], w.unique_id) or '')}</td>"
            f"<td class=num>{w.variance_days:+g}</td></tr>"
            for w in sv.worst
        )
        worst_tbl = (
            "<table class=card-table><tr><th scope=col>UID</th><th scope=col>Activity</th>"
            f"<th scope=col>Finish variance (wd)</th></tr>{worst_rows}</table>"
        )
    else:
        worst_tbl = (
            "<p class=muted>No completed activities carry both an actual and a baseline "
            "finish yet.</p>"
        )

    cost_note = (
        ""
        if cost_loaded
        else _user_tip(
            "This schedule is <b>not cost-loaded</b>, so the cost indices (SPI / CPI / TCPI) read "
            "<b>N/A</b> &mdash; the tool never fabricates a cost number. Load a schedule with task "
            "budgets and actual costs to compute them; the schedule-based metrics need no cost."
        )
    )

    tip = _user_tip(
        "SPI(t) and SVt come from <b>Earned Schedule</b> (time-based), so they stay meaningful late "
        "in a project where the classic cost-based SPI saturates at 1.0. A negative SVt (in working "
        "days) means the project is running behind the baseline plan."
    )
    # Operator 2026-07-09: BOTH SPI(t) methods are reported, each explained with pros/cons and a
    # worked example — they measure different things and can legitimately disagree in direction.
    dual_spi = _user_tip(
        "<b>Two SPI(t) methods are shown &mdash; they answer different questions and can "
        "legitimately disagree.</b><br><br>"
        "<b>SPI(t) &mdash; Earned Schedule</b> = ES &divide; AT: how far along the <i>baseline "
        "finish curve</i> the completed work reaches (ES), divided by the working time actually "
        "elapsed (AT). <i>Example:</i> 27 activities are complete; the baseline expected the "
        "27th finish at working day 80, but 115 working days have elapsed &mdash; SPI(t) = "
        "80 &divide; 115 = <b>0.70</b> (behind). "
        "<i>Pros:</i> a true schedule-position index &mdash; it sees work that <u>has not "
        "happened</u> (stalled work drags AT while ES freezes), follows the standard "
        "Earned-Schedule literature, and feeds the IEAC(t) finish forecast. "
        "<i>Cons:</i> count-based (a tiny task and a 6-month task each move ES one step) and it "
        "needs a meaningful baseline finish sequence.<br><br>"
        "<b>SPI(t) &mdash; Acumen</b> (the Fuse metric library formula) = the <i>average "
        "duration-efficiency of started activities</i>: for each completed activity, baselined "
        "span &divide; actual span; an in-progress activity contributes 0 until it finishes. "
        "<i>Example:</i> two completed tasks ran exactly to baseline (1.0 each) and one task "
        "baselined at 10 days took 20 (0.5) &mdash; average = <b>0.83</b>: completed work ran "
        "17% slower than baselined. "
        "<i>Pros:</i> per-activity and intuitive (&gt;1 = tasks finishing faster than their "
        "baselined spans), matches Acumen Fuse exactly, unaffected by the plan's task "
        "granularity ordering. "
        "<i>Cons:</i> only sees <u>started</u> work &mdash; a schedule that is executing its "
        "few started tasks efficiently but starting far too little scores well; each in-progress "
        "activity dilutes the average toward 0 by design (the Fuse formula's blank-ActualFinish "
        "term); and equal weight per activity lets many small on-pace tasks mask one huge "
        "overrun. "
        "<i>Read them together:</i> Earned-Schedule SPI(t) low + Acumen SPI(t) high means the "
        "work being touched runs efficiently but the project is not progressing through the "
        "baselined sequence &mdash; a classic under-resourced or logic-blocked pattern."
    )

    # ── panel-contract shells (Mission Ops rank 4, ADR-0298): headline strip + prov chip +
    # sf-take on each metric table. The tables ARE their own data drawer, so the toolbar is
    # ⤓ EXCEL (only where an EXISTING export endpoint serves that data) + ⛶ ENLARGE — no
    # ▦ DATA. Every take QUOTES the MetricResult values already rendered in the table below
    # it (parity-locked figures, read verbatim; never a new computation).
    evm_xlsx_title = "Export the EVM indices for every loaded version — opens in Excel"
    prov = _prov_chip(sch)

    sched_head = _panel_head(
        "Schedule performance", tools=_shell_tools(export_title=evm_xlsx_title), prov=prov
    )
    cei_f = sched_idx.get("cei_finish")
    cei_clause = (
        f"; CEI Finish has {cei_f.count} of {cei_f.population} due activities on time "
        f"({cei_f.value:g}%)"
        if cei_f is not None and cei_f.population
        else ""
    )
    sched_take = (
        f"SPI(t) reads {_evm_idx_str(sched_idx.get('spi_t'))} on the Earned-Schedule method "
        f"and {_evm_idx_str(sched_idx.get('spi_t_acumen'))} on the Acumen per-activity "
        f"method{cei_clause}."
    )

    cost_head = _panel_head(
        "Cost performance", tools=_shell_tools(export_title=evm_xlsx_title), prov=prov
    )
    if cost_loaded:
        cost_take = (
            f"SPI {_evm_idx_str(cost_idx.get('spi'))} · CPI {_evm_idx_str(cost_idx.get('cpi'))} "
            f"· TCPI {_evm_idx_str(cost_idx.get('tcpi'))} — scored against the 1.0 bar."
        )
    else:
        cost_take = (
            "This schedule carries no cost, so SPI / CPI / TCPI read N/A — "
            "a cost figure is never fabricated."
        )

    comp_head = _panel_head(
        "Baseline compliance",
        tools=_shell_tools(export_title=_ANALYSIS_XLSX_TITLE if key else ""),
        prov=prov,
    )
    bfc = compliance.get("baseline_finish_compliance")
    bsc = compliance.get("baseline_start_compliance")
    comp_parts: list[str] = []
    if bfc is not None and bfc.population and bfc.status is not CheckStatus.NOT_APPLICABLE:
        comp_parts.append(
            f"Baseline Finish Compliance {bfc.value:g}% ({bfc.count} of {bfc.population} on time)"
        )
    if bsc is not None and bsc.population and bsc.status is not CheckStatus.NOT_APPLICABLE:
        comp_parts.append(
            f"Baseline Start Compliance {bsc.value:g}% ({bsc.count} of {bsc.population})"
        )
    comp_take = (
        "; ".join(comp_parts) + "."
        if comp_parts
        else "The compliance ratios read N/A — the file lacks a data date or baselined-due "
        "work (a value is never imputed)."
    )

    worst_head = _panel_head("Worst finish variances", tools=_shell_tools(), prov=prov)
    if sv.worst:
        w0 = sv.worst[0]
        worst_take = (
            f"The latest finisher ran {w0.variance_days:+g} working days against its baseline "
            f"(UID {w0.unique_id}); the {len(sv.worst)} worst variances are listed."
        )
    else:
        worst_take = "No completed activities carry both an actual and a baseline finish yet."

    def take(text: str) -> str:
        return f"<p class=sf-take data-no-i18n>{_e(text)}</p>"

    return f"""
<div class=panel><h2>Earned Value Management (EVM) &mdash; {_e(sch.source_file or sch.name)}</h2>
<p class=muted>Performance against the baseline. The <b>schedule-based</b> metrics (Earned Schedule,
baseline compliance) always compute; the <b>cost</b> indices (SPI / CPI / TCPI) need a cost-loaded
schedule and otherwise read N/A.</p>
{tip}
{cards}</div>
<div class=panel data-export="/export/xlsx/evm">{sched_head}
{take(sched_take)}
<p class=muted>Both SPI(t) methods (Earned-Schedule and Acumen per-activity) and the
baseline-anchored Current Execution Index (finish / start).</p>
{dual_spi}
{_threshold_legend()}
{_metric_scorecard_table(sched_idx)}</div>
<div class=panel data-export="/export/xlsx/evm">{cost_head}
{take(cost_take)}
<p class=muted>Cost-based EVM indices &mdash; applicable only when the schedule carries task budgets
and actual costs.</p>
{cost_note}
{_metric_scorecard_table(cost_idx)}</div>
<div class=panel{_analysis_export_attr(key)}>{comp_head}
{take(comp_take)}
<p class=muted>How the executed work lines up with the baseline dates (BFC / BSC and the on-time
counts).</p>
{_threshold_legend()}
{_metric_scorecard_table(compliance)}</div>
<div class=panel>{worst_head}
{take(worst_take)}
<p class=muted>Completed activities that finished latest relative to their baseline (working days;
positive = late).</p>
{worst_tbl}</div>
{_evm_explainer()}
<script src="/static/panelkit.js"></script>"""
