"""The /trend page family - the "How it moved" multi-version trend view.

Monolith split, phase 3 slice 6 (ADR-0364), extracted VERBATIM from ``web/app.py``: every
function, docstring and comment moves byte-for-byte, only the module boundary changes.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour (the
``/trend`` and ``/api/trend`` routes' builders): 3 names / 424 lines whose only external
referrer is ``create_app``, a route, which imports downward and stays put. The
``_focus_rows``/``_focus_panel`` pair descended into ``web/components.py`` instead of moving
here: the /compare route still in ``app.py`` calls ``_focus_panel`` too, and a symbol an
extracted module needs must live at or below that module's layer (the ADR-0351 rule - the
FIRST slice of a pair forces the descent). ``export_trend`` stays whole in ``app.py``: it
builds its workbook from ``compute_quality_trend`` directly and references nothing moved.

Layering: ``app`` -> ``trend`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

import json

from schedule_forensics.engine.cpm import CPMResult, offset_to_datetime
from schedule_forensics.engine.manipulation import detect_manipulation, trend_across_versions
from schedule_forensics.engine.metrics import (
    compute_activity_makeup,
    compute_bri,
    compute_fei,
    compute_float_sums,
    compute_net_finish_impact,
)
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.engine.metrics.evm import compute_schedule_variance
from schedule_forensics.engine.trend import (
    compute_cei_trend,
    compute_float_ratio_trend,
    compute_hmi_trend,
    compute_quality_trend,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _EXPLAINERS, _e
from schedule_forensics.web.components import (
    _focus_panel,
    _mdY,
    _metric_help_cell,
    _panel_head,
    _series_prov_chip,
    _shell_tools,
    _stat_cards,
    _status_stack,
    _user_tip,
)
from schedule_forensics.web.state import _Analysis


def _how_it_moved_header(schedules: list[Schedule], cpms: list[CPMResult]) -> str:
    """Chapter 05 "How it moved" (ADR-0202): the data-driven takeaway + a slippage KPI strip
    + the update-behaviour and work-status bars, from the per-version trend the page already
    tabulates (trend_across_versions) and the latest version's activity makeup (no new math)."""
    points = trend_across_versions(schedules, cpms)
    n_ver = len(points)
    updates = n_ver - 1
    moves = [
        (points[i].project_finish.date() - points[i - 1].project_finish.date()).days
        for i in range(1, n_ver)
    ]
    net = (points[-1].project_finish.date() - points[0].project_finish.date()).days
    slipped = sum(1 for m in moves if m > 0)
    improved = sum(1 for m in moves if m < 0)
    held = updates - slipped - improved
    biggest = max(moves, key=abs) if moves else 0
    latest = points[-1]
    makeup = compute_activity_makeup(schedules[-1])

    def _cal(n: int) -> str:
        return f"{abs(n)} calendar day" + ("" if abs(n) == 1 else "s")

    if net > 0:
        moved = f"slipped {_cal(net)}"
    elif net < 0:
        moved = f"pulled in {_cal(net)}"
    else:
        moved = "held steady"
    upd = f"update{'s' if updates != 1 else ''}"
    takeaway = (
        f"Across {n_ver} versions the finish {moved} — {slipped} of {updates} {upd} slipped it "
        f"— and the schedule-logic (CPM) finish is {_mdY(latest.project_finish)}."
    )

    kpi = _stat_cards(
        [
            ("Versions compared", str(n_ver)),
            ("Schedule-logic finish", _mdY(latest.project_finish)),
            ("Net finish move", f"{net:+d} d" if net else "0 d"),
            ("Updates that slipped", f"{slipped} / {updates}"),
            ("Biggest single move", f"{biggest:+d} d" if biggest else "0 d"),
            ("Critical now", str(latest.critical)),
        ]
    )
    behaviour = _status_stack(
        "Update behaviour",
        "How each update moved the schedule-logic (CPM) finish vs the version before it.",
        [("Slipped", slipped, "--bad"), ("Held", held, "--muted"), ("Improved", improved, "--ok")],
        f"over {updates} {upd}",
        # (no drill — these segments count version-to-version updates, not activities)
    )
    # the "Where the work stands" segments DO map to activity sets — partition the latest version's
    # non-summary tasks by percent-complete, exactly as compute_activity_makeup counts them.
    latest_sch = schedules[-1]
    ns = non_summary(latest_sch)
    fkey = latest_sch.source_file or latest_sch.name
    complete_uids = tuple(sorted(t.unique_id for t in ns if t.percent_complete >= 100.0))
    inprog_uids = tuple(sorted(t.unique_id for t in ns if 0.0 < t.percent_complete < 100.0))
    planned_uids = tuple(sorted(t.unique_id for t in ns if t.percent_complete <= 0.0))
    work = _status_stack(
        "Where the work stands",
        f"Activity status in the newest version — {latest.source_file or 'latest'}.",
        [
            ("Complete", makeup.complete, "--ok"),
            ("In progress", makeup.in_progress, "--accent"),
            ("Not started", makeup.planned, "--muted"),
        ],
        f"{makeup.total} activities in scope",
        drill=[(complete_uids, fkey), (inprog_uids, fkey), (planned_uids, fkey)],
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{behaviour}{work}</div>'
        "<div id=sfDrillMount></div>"  # drilldown.js loaded globally in _LAYOUT
    )


def _trend_body(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    target: int | None = None,
    *,
    pair_schedules: list[Schedule] | None = None,
    pair_cpms: list[CPMResult] | None = None,
) -> str:
    """The multi-version trend view: table, quality-trend sentences, pairwise signals, charts.

    ``pair_schedules``/``pair_cpms`` (ADR-0371) are the PAIR-scope populations the pairwise
    manipulation signals diff — the Target UID never truncates them (a truncated pair
    fabricated deleted-task findings from cone membership and missed real cuts outside the
    cone). The series, header and focus panels stay on the focused ``schedules`` (the page's
    ``?target=`` feature, ADR-0268). ``None`` falls back to ``schedules``/``cpms`` — the
    correct basis whenever the caller's populations are already unscoped (no target set)."""
    points = trend_across_versions(schedules, cpms)
    trend_rows = "".join(
        f"<tr><td>{_e(p.source_file or p.version_index)}</td>"
        f"<td>{_e(p.status_date.date()) if p.status_date else '-'}</td>"
        f"<td>{_e(p.project_finish.date())}</td>"
        f"<td>{p.completed}</td><td>{p.in_progress}</td><td>{p.critical}</td></tr>"
        for p in points
    )
    qtrends = list(compute_quality_trend(schedules, cpms))
    quality_items = "".join(f"<li>{_e(t.sentence())}</li>" for t in qtrends)
    impact = compute_net_finish_impact(
        schedules[-1], schedules[0], current_cpm=cpms[-1], prior_cpm=cpms[0]
    )
    days = int(impact.value)
    cls, word = ("fail", "later") if days < 0 else ("pass", "earlier or unchanged")
    signal_rows: list[str] = []
    # each signal's cited activities, embedded so the operator can drill into the tasks behind a
    # finding (UID/name/duration/%/start/finish + add columns + Excel) — reuses findings_drill.js
    # with a PER-FINDING file (a signal cites its own version: deletions cite the prior, most
    # others cite the current).
    signal_findings: list[dict[str, object]] = []
    sig_schedules = pair_schedules if pair_schedules is not None else schedules
    sig_cpms = pair_cpms if pair_cpms is not None else cpms
    for i in range(len(sig_schedules) - 1):
        prior, current = sig_schedules[i], sig_schedules[i + 1]
        p_label = prior.source_file or prior.name
        c_label = current.source_file or current.name
        step = f"{_e(p_label)} &rarr; {_e(c_label)}"
        for f in detect_manipulation(
            current, prior, current_cpm=sig_cpms[i + 1], prior_cpm=sig_cpms[i]
        ):
            task_cites = [c for c in f.citations if c.unique_id > 0]
            cite_file = next((c.source_file for c in task_cites if c.source_file), None)
            signal_cell = _e(f.title)
            if task_cites and cite_file:
                fi = len(signal_findings)
                signal_findings.append(
                    {
                        "title": f"{f.title} — {p_label} → {c_label}",
                        "file": cite_file,
                        "uids": [c.unique_id for c in task_cites],
                    }
                )
                n = len(task_cites)
                signal_cell = (
                    f"{_e(f.title)} "
                    f'<a class=cite-more data-finding="{fi}">'
                    f"(view {n} task{'s' if n != 1 else ''})</a>"
                )
            signal_rows.append(
                f'<tr><td>{step}</td><td class="sev-{_e(f.severity)}">{_e(f.severity)}</td>'
                f"<td>{signal_cell}</td><td class=muted>{_e(f.course_of_action)}</td></tr>"
            )
    signals_blob = json.dumps({"findings": signal_findings}).replace("<", "\\u003c")

    # ── panel contract (Mission Ops rank 9) ───────────────────────────────────────────────
    # Headline strip + first→last provenance chip + one .sf-take per panel. Every take QUOTES a
    # figure this page already renders (the Net Finish Impact sentence below the trend table, the
    # loaded version labels/count, the engine's own quality-trend sentences, the signal rows) —
    # never a new computation and never an adjective the engine did not assert.
    # ⤓ EXCEL is added ONLY where an EXISTING endpoint serves that panel's data: /export/xlsx/trend
    # exports the schedule-quality trend, so the trend table, the trend charts, the quality
    # drill-down and the quality-trend sentences carry it; the manipulation-signal table has no
    # endpoint of its own (a dead ⤓ is never shipped) and the margin burndown rides
    # /export/xlsx/margin. The chart panels whose action strip trend.js/margin.js already build
    # (⛶ ENLARGE / ▦ DATA next to the chart) do NOT get a second ⛶ in the head — that strip IS the
    # panel's tool strip and is normalized in place (relabel, never rebuild).
    prov = _series_prov_chip(schedules)
    trend_xlsx = "Export the schedule-quality trend for every loaded version — opens in Excel"
    n_ver = len(schedules)
    steps = n_ver - 1
    step_txt = f"{steps} consecutive-version step" + ("" if steps == 1 else "s")
    oldest_label = schedules[0].source_file or schedules[0].name
    latest_label = schedules[-1].source_file or schedules[-1].name

    def take(text: str) -> str:
        return f"<p class=sf-take data-no-i18n>{text}</p>"

    trend_take = take(
        f"Across {n_ver} versions the Net Finish Impact is <b class={cls}>{days:+d} calendar "
        f"days</b> &mdash; the project finish moved {word} between "
        f"<b>{_e(oldest_label)}</b> and <b>{_e(latest_label)}</b>."
    )
    charts_take = take(
        f"Every chart plots the same {n_ver} versions on a locked axis, oldest first by data "
        f"date &mdash; <b>{_e(oldest_label)}</b> through <b>{_e(latest_label)}</b>."
    )
    qual_take = take(
        f"{len(qtrends)} schedule-quality metrics stepped across {n_ver} versions on a locked "
        "bar axis; pick one to list the offending activities behind its number."
    )
    qtrend_take = take(
        f"{len(qtrends)} schedule-quality metrics tracked across {n_ver} versions &mdash; each "
        "sentence below is the engine's own trend statement, quoted verbatim."
    )
    n_sig = len(signal_rows)
    signals_take = take(
        f"{n_sig} manipulation-trend signal{'' if n_sig == 1 else 's'} across {step_txt}."
        if n_sig
        else f"No manipulation signals across {step_txt}."
    )
    margin_take = take(
        f"Total against effective margin across {n_ver} submissions, from "
        f"<b>{_e(oldest_label)}</b> to <b>{_e(latest_label)}</b>."
    )
    focus_panel = _focus_panel(schedules, cpms, target) if target is not None else ""
    focus_form = f"""
<div class=panel><form method=get action=/trend class=viz-controls>
Focus the trend on a specific activity &mdash; UniqueID:
<input name=target type=number min=1 value="{target if target is not None else ""}"
placeholder="UID"> <button type=submit>Focus</button>
{'<a class=btn-link href="/trend?target=">clear focus</a>' if target is not None else ""}
</form></div>"""
    # ── Claude Design layout (ADR-0460): artboard "05 How it moved" ──────────────────────────
    # The page is RE-ARRANGED into the design, functionality unchanged (ADR-0451/0456's method):
    # a masthead cursor strip — the page's own ▶ Play all / ⏭ Step all master mounts into
    # #trendMaster (trend.js), ONE chip per version, the frame pill — the Focus form as the
    # options row, then the design's rows: the version table beside the manipulation signals (the
    # mock's "computed finish, by version" beside "net finish impact, per update"), the trend
    # charts full width (the mock's slope and float-erosion visuals live there), the quality
    # drill-down beside a stack of the schedule-quality sentences and a "How to read this" block
    # whose three beats are this page's own explainer (no new prose enters the loaded-terms audit
    # surface), the margin burndown full width. Every panel below is byte-for-byte what it was;
    # the .cd-* family is the page-neutral vocabulary (DESIGN-SYSTEM §9). A chip is the page's own
    # steppers: trend.js clicks the Next buttons that already exist until every chart shows that
    # version — the charts open fully revealed, so the LAST chip is on.
    chips = "".join(
        f'<button type=button class="cd-chip{" on" if i == n_ver - 1 else ""}" data-idx="{i}" '
        f'title="{_e(s.source_file or s.name)}" data-no-i18n>v{i + 1}</button>'
        for i, s in enumerate(schedules)
    )
    what, how, decide = _EXPLAINERS["Trend"]
    beats = "".join(
        f'<div class="cd-beat {cls}"><b>{lead}</b> {_e(text)}</div>'
        for cls, lead, text in (
            ("cd-beat-accent", "What it shows.", what),
            ("cd-beat-warn", "How to read it.", how),
            ("cd-beat-bad", "Why it matters.", decide),
        )
    )
    cursor = f"""
<div class="viz-controls cd-cursor" id=trendCursor>
<span id=trendMaster class=cd-master></span>
<span class=cd-chips>{chips}</span>
<span id=trendFrame class="muted cd-pill" data-no-i18n></span>
<span class="muted cd-note">One cursor &mdash; &#9654; Play all / &#9197; Step all beat every chart on this page through the loaded files in lockstep; a chip jumps every chart to that version.</span>
</div>"""
    return f"""{cursor}
<div class=cd-options>{focus_form}</div>{focus_panel}
<div class="cd-grid cd-grid-12">
<div class=panel data-export="/export/xlsx/trend">{
        _panel_head(
            f"Version trend &mdash; {len(schedules)} versions, oldest first (by data date)",
            tools=_shell_tools(export_title=trend_xlsx),
            prov=prov,
        )
    }
{trend_take}
{
        _user_tip(
            "Load two or more versions (oldest first by data date) to see how the finish, criticality and schedule quality move over time &mdash; a finish that keeps sliding right is the classic bow-wave signature."
        )
    }
<table><tr><th scope=col>Version</th><th scope=col>Data date</th><th scope=col>Project finish</th>
<th scope=col class=metric-th>{_metric_help_cell("Completed", "completed")}</th>
<th scope=col class=metric-th>{_metric_help_cell("In progress", "in_progress")}</th>
<th scope=col class=metric-th>{_metric_help_cell("Critical", "critical")}</th></tr>{
        trend_rows
    }</table>
<p>Net Finish Impact across the series: <b class={cls}>{days:+d} calendar days</b>
&mdash; the project finish moved {word} between the first and last version.</p></div>
<div class=panel>{
        _panel_head(
            "Manipulation-trend signals (consecutive versions)", tools=_shell_tools(), prov=prov
        )
    }
{signals_take}
<p class=muted>Each signal with cited activities is a <b>view N tasks</b> link &mdash; click it to
list the exact activities behind that finding (UID / name / duration / % complete / start /
finish), add any standard or custom field, filter, and export to Excel.</p>
<table><tr><th scope=col>Step</th><th scope=col>Severity</th><th scope=col>Signal</th><th scope=col>Course of action</th></tr>
{
        "".join(signal_rows)
        or "<tr><td colspan=4 class=muted>No manipulation signals detected across the series (honest progress).</td></tr>"
    }</table>
<div id=findingsDrill class=findings-drill></div>
<script type="application/json" id=findingsData>{signals_blob}</script>
<script src="/static/findings_drill.js"></script></div>
</div>
<div class=panel data-export="/export/xlsx/trend">{_panel_head("Trend charts", prov=prov)}
{charts_take}
<div id=trendCharts class="charts chart-host"
data-target="{target if target is not None else ""}"></div></div>
<div class="cd-grid cd-grid-2">
<div class=panel id=qualDrillPanel data-export="/export/xlsx/trend">{
        _panel_head(
            "Quality drill-down &amp; animation",
            tools=_shell_tools(export_title=trend_xlsx),
            prov=prov,
        )
    }
{qual_take}
<p class=muted>Step through the versions (oldest first) and watch the count of <b>offending
activities</b> for each schedule-quality metric move on a <b>locked axis</b> &mdash; bar
heights stay comparable frame to frame, so a metric that worsens stands out. Pick a metric to
list the exact activities behind its number in the current version (the drill-down).</p>
<div class=viz-controls>
<label>Metric <select id=qualMetric></select></label>
<button id=qualPrev type=button>&#9664; Prev</button>
<span id=qualLabel class=muted></span>
<button id=qualNext type=button>Next &#9654;</button>
<button id=qualPlay type=button>&#9654; Auto-play</button>
</div>
<div class=qual-drill-grid>
<div id=qualBars class=qual-bars></div>
<div id=qualDrill class=qual-offenders></div>
</div></div>
<div class=cd-stack>
<div class=panel data-export="/export/xlsx/trend">{
        _panel_head(
            "Schedule-quality trends", tools=_shell_tools(export_title=trend_xlsx), prov=prov
        )
    }
{qtrend_take}
<p class=muted>How each schedule-quality metric moves across the versions.</p>
<ul>{quality_items}</ul></div>
<section class="cd-block cd-read"><h2>How to read this</h2>{beats}</section>
</div>
</div>
<div class=panel data-export="/export/xlsx/margin">{
        _panel_head("Schedule margin burndown", prov=prov)
    }
{margin_take}
<p class=muted>Tracks <b>total</b> vs <b>effective</b> margin &mdash; the buffer protecting the project
finish &mdash; across submissions, so margin erosion (a buffer being spent or quietly removed) is
visible at a glance.</p>
<div class="chart-host" id=marginBurndown></div></div>
<script src="/static/trend.js"></script>
<script src="/static/trend_drill.js"></script>
<script src="/static/margin.js"></script>
<script src="/static/panelkit.js"></script>"""


def _trend_data(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    analyses: list[_Analysis],
    target: int | None = None,
) -> dict[str, object]:
    """JSON for the trend charts: per-version headline numbers + quality-metric series.

    The ``analyses`` are pre-computed (cached) _Analysis objects parallel to schedules/cpms.
    Extended in ADR-0039 to carry per-version cross-file comparison and float-analysis data
    for the PBIX page 4+5 charts rendered by trend.js.
    """
    points = trend_across_versions(schedules, cpms)
    focus: dict[str, object] | None = None
    if target is not None:
        finishes: list[str | None] = []
        percents: list[float | None] = []
        for sch, cpm in zip(schedules, cpms, strict=True):
            timing = cpm.timings.get(target)
            task = sch.tasks_by_id.get(target)
            if timing is None or task is None:
                finishes.append(None)
                percents.append(None)
            else:
                fin = offset_to_datetime(sch.project_start, timing.early_finish, sch.calendar)
                finishes.append(fin.date().isoformat())
                percents.append(task.percent_complete)
        names = [s.tasks_by_id[target].name for s in schedules if target in s.tasks_by_id]
        focus = {
            "uid": target,
            "name": names[0] if names else None,
            "finishes": finishes,
            "percents": percents,
        }

    # HMI and CEI are period-over-period (each version scored against the previous version's data
    # date), so they are computed once across the ordered series and indexed per version (first =
    # None). HMI is baseline-anchored; CEI is forecast-anchored (prior forecast vs current actuals).
    hmi_series = compute_hmi_trend(schedules)
    cei_series = compute_cei_trend(schedules)
    # Float Ratio is single-snapshot; the trend scores each version and carries the period-over-period
    # delta (this minus prior) so the chart reads as a period-to-period series (ADR-0103).
    float_ratio_series = compute_float_ratio_trend(schedules, cpms)
    version_rows: list[dict[str, object]] = []
    for i, (p, sch, cpm, an) in enumerate(zip(points, schedules, cpms, analyses, strict=True)):
        makeup = compute_activity_makeup(sch)
        cp = an.completion
        fb = an.float_bands
        fs = compute_float_sums(sch, cpm)
        # BEI lives in the DCMA14 check (metric_id="DCMA14")
        bei_chk = next((c for c in an.audit.checks if c.metric_id == "DCMA14"), None)
        bei: float | None = bei_chk.value if (bei_chk and bei_chk.population) else None
        mei_r = cp["mei"]
        epi_r = cp["epi"]
        sfr_r = cp["start_finish_ratio"]
        # FEI (to-go forecast execution) + BRI (baseline realism) — single-snapshot (ADR-0100)
        fei = compute_fei(sch)
        bri_r = compute_bri(sch)
        # SVt (Earned-Schedule time variance, working days) per version — the SV/SVt trend (D4)
        svt = compute_schedule_variance(sch, non_summary(sch)).svt_days
        # The activity ids behind each stacked-bar segment are NOT shipped here (ADR-0288): these
        # three groups partition the whole schedule, so their UID arrays were ~21.8 KiB per version
        # (46% of this payload) for data only read when the operator clicks a bar. The bars now carry
        # a segment NAME and `_drill_uid_set` rebuilds the set on demand from the same predicates.
        version_rows.append(
            {
                "label": p.source_file or f"v{p.version_index + 1}",
                # a resolvable schedule key for the bar drill (the label may be a synthetic "v3")
                "file": sch.source_file or sch.name,
                "status_date": p.status_date.date().isoformat() if p.status_date else None,
                "finish": p.project_finish.date().isoformat(),
                "completed": p.completed,
                "in_progress": p.in_progress,
                "critical": p.critical,
                # SVt (Earned-Schedule time variance, working days; None when undefined) — SV/SVt trend
                "svt_days": svt,
                # PBIX p4 — Cross File Comparison
                "makeup": {
                    "milestones": makeup.milestones,
                    "normal": makeup.normal,
                    "summaries": makeup.summaries,
                },
                "status_split": {
                    "complete": makeup.complete,
                    "in_progress": makeup.in_progress,
                    "planned": makeup.planned,
                },
                "completion_perf": {
                    "ahead": cp["completed_ahead"].count,
                    "on_schedule": cp["completed_on_schedule"].count,
                    "behind": cp["completed_behind"].count,
                },
                "indices": {
                    "mei": mei_r.value if mei_r.population else None,
                    "bei": bei,
                    "epi": epi_r.value if epi_r.population else None,
                    "sfr": sfr_r.value if sfr_r.population else None,
                    # HMI / CEI (period-over-period): None on the first version (no predecessor)
                    "hmi_tasks": hmi_series.task_values[i],
                    "hmi_milestones": hmi_series.milestone_values[i],
                    "cei_tasks": cei_series.task_values[i],
                    "cei_milestones": cei_series.milestone_values[i],
                    "cei_starts": cei_series.start_values[i],
                    "cei_critical": cei_series.critical_values[i],
                    "cei_adjusted": cei_series.adjusted_values[i],
                    # FEI / BRI (single-snapshot, baseline-anchored)
                    "fei_starts": fei["fei_starts"].value if fei["fei_starts"].population else None,
                    "fei_finish": fei["fei_finish"].value if fei["fei_finish"].population else None,
                    "bri": bri_r.value if bri_r.population else None,
                    # Float Ratio (single-snapshot; the delta is period-over-period)
                    "float_ratio": float_ratio_series.values[i],
                    "float_ratio_aggregate": float_ratio_series.aggregate_values[i],
                    "float_ratio_delta": float_ratio_series.deltas[i],
                },
                # PBIX p5 — Float Analysis
                "float_sums": {
                    "total_days": fs.total_days,
                    "free_days": fs.free_days,
                },
                "float_bands": {
                    k: {"count": v.count, "pct": round(v.value, 1), "uids": list(v.offender_uids)}
                    for k, v in fb.items()
                },
            }
        )

    # Per-metric drill-down (M18 item 8): every §A quality metric carries, per version,
    # the offending activities (UID + name) behind the trended number — the data the
    # drill-down/animation panel steps through. Names resolve against each version's own
    # task map (an activity can change name between versions). No cap (Law 1, local).
    by_id_per_version = [s.tasks_by_id for s in schedules]
    quality: dict[str, object] = {}
    for t in compute_quality_trend(schedules, cpms):
        offenders_per_version = [
            [
                {"uid": uid, "name": by_id_per_version[vi][uid].name}
                for uid in offs
                if uid in by_id_per_version[vi]
            ]
            for vi, offs in enumerate(t.offenders_by_version)
        ]
        quality[t.metric_id] = {
            "name": t.name,
            "values": list(t.values),
            "lower_is_better": t.lower_is_better,
            "worst_index": t.worst_index,
            "counts": [len(offs) for offs in t.offenders_by_version],
            "offenders": offenders_per_version,
        }
    return {"target": focus, "versions": version_rows, "quality": quality}
