"""The /performance page family: the Performance Analysis Summary workbook, live.

Monolith split, phase 3 slice 14 (ADR-0378), extracted VERBATIM from ``web/app.py``: every
function, docstring and comment moves byte-for-byte, only the module boundary changes.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour (the
``/performance`` and ``/export/{fmt}/performance`` routes): FOUR names in one contiguous block —
the memoised per-version G1-G5 block, the dataset builder both the page and the export read, the
chapter-07 "How we execute" header, and the page body with its fourteen chart mounts. The
closure is **census-exact** for the first time in phase 3 (the prefix census said 326 ast lines;
the referrer walk says the same four names, 326) — and it needs no descent: the only shared name
the walk surfaced, ``_sources_line``, is called by the ROUTE, not by any mover, so it stays in
``app.py`` with the other multi-family provenance helpers.

Unlike the previous five slices, the export route DOES share a mover: ``export_performance``
builds its five tables from ``_performance_data``, so both export formats are part of this
family's render-proven surface (9 of the 498 oracle labels move for ``_performance_data`` and
for ``_perf_version_block``, page AND xlsx AND docx, in all three session states).

Layering: ``app`` -> ``performance`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

import json
from typing import cast

from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.metrics import compute_activity_makeup, compute_bei
from schedule_forensics.engine.metrics._common import CheckStatus
from schedule_forensics.engine.metrics.evm import compute_evm_indices
from schedule_forensics.engine.metrics.hmi import compute_hmi
from schedule_forensics.engine.metrics.performance_summary import (
    activity_flow,
    duration_ratio,
    to_go_snapshot,
    work_to_go_census,
    workoff_burden,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e, _explain
from schedule_forensics.web.components import (
    _panel_head,
    _series_prov_chip,
    _stat_cards,
    _status_stack,
)
from schedule_forensics.web.state import SessionState


def _perf_version_block(
    st: SessionState, s: Schedule, c: CPMResult
) -> tuple[frozenset[int], dict[str, object], bool]:
    """One version's G1-G5 Performance block — ``(critical set, serialized block, truncated)`` —
    memoised per scoped-schedule identity (ADR-0261 P3). The census/flow/burden/DRM passes are
    pure functions of the scoped version, so a /performance render (or its master stepper /
    export) no longer recomputes every loaded version every time. The memo lives and dies with
    the scope epoch (cleared by the scope setters and wipe), so identity can never go stale."""
    from dataclasses import asdict

    from schedule_forensics.engine.path_evolution import effective_critical_set

    with st._lock:
        hit = st._perf_memo.get(id(s))
        if hit is not None and hit[0] is s:
            return hit[1], hit[2], hit[3]
        gen = (st._scope_gen, st.wipe_gen)
    critical = frozenset(effective_critical_set(s, c))
    cen_v = work_to_go_census(s, critical)
    flow_v = activity_flow(s)
    bur_v = workoff_burden(s)
    drm_v = duration_ratio(s)
    block: dict[str, object] = {
        "label": s.source_file or s.name,
        "status_date": s.status_date.date().isoformat() if s.status_date else None,
        "status_month": flow_v.status_month,
        "census": [asdict(m) for m in cen_v.months],
        "flow": [asdict(m) for m in flow_v.months],
        "burden": [asdict(m) for m in bur_v.months],
        "drm": {
            "points": [asdict(pt) for pt in drm_v.points],
            "bins": [asdict(b) for b in drm_v.bins],
            "min": drm_v.drm_min,
            "avg": drm_v.drm_avg,
            "max": drm_v.drm_max,
            "n": drm_v.n,
            "excluded": drm_v.n_excluded,
        },
    }
    truncated = cen_v.truncated or flow_v.truncated or bur_v.truncated
    with st._lock:
        # ADR-0263: the memo is identity-keyed, so it must die with its scope epoch — a store
        # whose compute started under an older epoch (or before a wipe) is skipped; the result
        # is still returned to ITS requester, but never memoised into the new epoch.
        if (st._scope_gen, st.wipe_gen) == gen:
            st._perf_memo[id(s)] = (s, critical, block, truncated)
    return critical, block, truncated


def _performance_data(
    st: SessionState, schedules: list[Schedule], cpms: list[CPMResult], file: str
) -> dict[str, object]:
    """The Performance-Summary dataset (operator 2026-07-10): the per-version G1-G5 series for
    the SELECTED file (default: the newest version) plus the G6/G7 portfolio quad points for
    EVERY loaded version. Every figure comes from the engine's performance_summary /
    bei / hmi / evm functions — the same single sources of truth the rest of the tool cites.
    ADR-0261 P3: the per-version G1-G5 blocks are memoised per scope epoch
    (:func:`_perf_version_block`); the quads recompute each render (cheap linear passes whose
    HMI leg depends on the PRIOR version's status date, which memoising would have to track)."""
    labels = [s.source_file or s.name for s in schedules]
    sel = labels.index(file) if file in labels else len(schedules) - 1

    # per-version G1-G5 series for the master stepper (operator 2026-07-10: "automate" the
    # Performance visuals like the Mission wall) — each animation step redraws every chart
    # from THIS version's series and captions its file name (provenance per iteration).
    criticals: list[frozenset[int]] = []
    per_version: list[dict[str, object]] = []
    truncateds: list[bool] = []
    for s_i, c_i in zip(schedules, cpms, strict=True):
        crit_v, block, trunc = _perf_version_block(st, s_i, c_i)
        criticals.append(crit_v)
        per_version.append(block)
        truncateds.append(trunc)

    quads: list[dict[str, object]] = []
    for i, (s, _c) in enumerate(zip(schedules, cpms, strict=True)):
        crit_i = criticals[i]
        snap = to_go_snapshot(s, crit_i)
        prior_status = schedules[i - 1].status_date if i > 0 else None
        # HMI is informational (its status is ALWAYS NOT_APPLICABLE by design) — the genuine
        # "no qualifying period/population" case is population == 0, so gate on that instead.
        hmi = compute_hmi(s, prior_status)["hmi_tasks"]
        evm = compute_evm_indices(s)
        cei = evm["cei_finish"]
        bei = compute_bei(s)
        quads.append(
            {
                "label": labels[i],
                "hmi": None if hmi.population == 0 else hmi.value,
                # cei_finish is a PERCENT (0-100); the quad plots 0-1 like HMI, so rescale
                "cei": (
                    None
                    if cei.status is CheckStatus.NOT_APPLICABLE or cei.value is None
                    else round(cei.value / 100.0, 3)
                ),
                "bei": None if bei.status is CheckStatus.NOT_APPLICABLE else bei.value,
                "start_ratio": snap.start_ratio,
                "finish_ratio": snap.finish_ratio,
                "cp_share": snap.critical_share,
                "tm_to_go": snap.tm_to_go,
                "critical_to_go": snap.critical_to_go,
                "baselined_to_start_remaining": snap.baselined_to_start_remaining,
                "scheduled_to_start_to_go": snap.scheduled_to_start_to_go,
                "baselined_to_finish_remaining": snap.baselined_to_finish_remaining,
                "scheduled_to_finish_to_go": snap.scheduled_to_finish_to_go,
            }
        )

    # the selected version's top-level series ARE its per_version block (identical values —
    # previously the same dataclasses were serialized twice)
    sel_block = per_version[sel]
    return {
        "version": labels[sel],
        "versions": labels,
        "cursor": sel,
        "per_version": per_version,
        "status_month": sel_block["status_month"],
        "truncated": truncateds[sel],
        "census": sel_block["census"],
        "flow": sel_block["flow"],
        "burden": sel_block["burden"],
        "drm": sel_block["drm"],
        "quads": quads,
    }


def _how_we_execute_header(sch: Schedule) -> str:
    """Chapter 07 "How we execute" (ADR-0205): the data-driven takeaway + an execution-quality
    KPI strip + the baseline-pace and duration-performance bars, from the same throughput and
    duration-ratio functions the page charts (compute_bei / duration_ratio / activity makeup —
    no new math). Anchored on the latest loaded version."""
    makeup = compute_activity_makeup(sch)
    total = makeup.total or 1
    complete_pct = 100.0 * makeup.complete / total
    bei = compute_bei(sch)
    kept = bei.count  # completed among the baselined-due
    missed = max(bei.population - bei.count, 0)  # due but not finished on the baseline
    drm = duration_ratio(sch)

    lead = (
        f"The project has finished {makeup.complete} of {makeup.total} activities "
        f"({complete_pct:.0f}%)"
    )
    if bei.population == 0:
        takeaway = f"{lead}; no work is yet baselined-due to measure the execution pace."
    else:
        if bei.value >= 1.0:
            pace = f"baselined-due work is finishing at BEI {bei.value:.2f} — on or ahead of the baseline pace"
        elif bei.value >= 0.95:
            pace = f"baselined-due work is finishing at BEI {bei.value:.2f} — just behind the baseline pace"
        else:
            pace = (
                f"baselined-due work is finishing at BEI {bei.value:.2f} — behind the baseline pace"
            )
        if drm.drm_avg is None:
            dur = ""
        elif drm.drm_avg > 1.05:
            dur = f", and completed work ran {drm.drm_avg:.2f}x its planned duration"
        elif drm.drm_avg < 0.95:
            dur = f", and completed work beat its plan at {drm.drm_avg:.2f}x planned duration"
        else:
            dur = f", and completed work ran close to plan ({drm.drm_avg:.2f}x planned duration)"
        takeaway = f"{lead}; {pace}{dur}."

    kpi = _stat_cards(
        [
            ("Activities complete", f"{makeup.complete} / {makeup.total}"),
            ("Complete", f"{complete_pct:.0f}%"),
            ("BEI (throughput)", f"{bei.value:.2f}" if bei.population else "—"),
            (
                "Duration ratio (avg)",
                f"{drm.drm_avg:.2f}x" if drm.drm_avg is not None else "—",
            ),
            ("Missed the baseline", str(missed) if bei.population else "—"),
            ("Still to go", str(makeup.total - makeup.complete)),
        ]
    )
    pace_bar = _status_stack(
        "Baseline pace (BEI)",
        "Activities baselined to finish by the data date — kept pace vs missed the baseline.",
        [("Kept pace", kept, "--ok"), ("Missed", missed, "--bad")],
        f"BEI {bei.value:.2f} over {bei.population} baselined-due"
        if bei.population
        else "no baselined-due activities yet",
    )
    # completed-task duration bands: under (<0.95x) / on-target (0.95-1.05x) / over (>1.05x)
    under = sum(1 for p in drm.points if p.drm < 0.95)
    ontgt = sum(1 for p in drm.points if 0.95 <= p.drm <= 1.05)
    over = sum(1 for p in drm.points if p.drm > 1.05)
    dur_bar = _status_stack(
        "Duration performance",
        "Completed activities by how their actual duration compared to their baseline.",
        [
            ("Under plan", under, "--ok"),
            ("On target", ontgt, "--muted"),
            ("Over plan", over, "--bad"),
        ],
        f"{drm.n} completed with a baseline"
        + (f"; {drm.n_excluded} lack one" if drm.n_excluded else ""),
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        '<p class="page-lede">How the work is actually being executed against the baseline: '
        "where starts and finishes are landing month by month, whether throughput is keeping "
        "the baseline pace, how much past-due baseline work is still being carried, and how "
        "completed durations compared with what was planned.</p>"
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{pace_bar}{dur_bar}</div>'
    )


def _performance_body(
    st: SessionState, schedules: list[Schedule], cpms: list[CPMResult], file: str
) -> str:
    """The Performance-Summary page shell: version picker, the FOURTEEN chart mounts (G1-G7 of
    the operator's reference workbook), the DRM stat chips, and the embedded dataset
    performance.js reads. Every chart carries a hover explainer (viz-hint) like the rest of
    the tool.

    Panel contract (Mission Ops rank 10, ADR-0298): each ``.tile.panel`` wears the mission-wall
    tile shape — tools strip in the ``.tile-head``, ``.tile-prov`` chip, one ``.sf-take``. Three
    deliberate omissions, each of which would otherwise ship an inert glyph:

    * **no ▦ DATA** on any tile — these tiles carry no ``.sf-drawer`` and no ``.sr-only`` table,
      and ``mission.js`` (which drives ``.tile-data``) is not on this route (the
      :func:`_shell_tools` / ``_scurve_body`` precedent of omitting the glyph);
    * **no ⤓ EXCEL or ⛶ ENLARGE on the intro panel** — it ALREADY owns this page's Excel control
      (the ``⬇ Excel (all datasets)`` anchor, pointing at the very URL ⤓ would follow; ADR-0298's
      one-convention law), and it is not a grid item, so ``.is-big``'s ``grid-column:1/-1`` is
      inert on it;
    * **no per-file figure in any tile take** — the master stepper (performance.js ``setVersion``)
      re-binds G1-G5 to a DIFFERENT loaded file on every tick, so a server-rendered number would
      become false on the first ▶. The takes are structural, and the provenance chip is
      :func:`_series_prov_chip` (a first→last RANGE that holds at every frame), never
      :func:`_prov_chip` of one file. The one figure the intro take quotes, ``sel``, is already
      rendered verbatim by the selected ``<option>`` and the export href below it, and is framed
      as the opening state ("open on") that the stepper is described as moving."""
    data = _performance_data(st, schedules, cpms, file)
    blob = json.dumps(data).replace("<", "\\u003c")
    versions = cast(list[str], data["versions"])
    sel = cast(str, data["version"])
    opts = "".join(
        f'<option value="{_e(v)}"{" selected" if v == sel else ""}>{_e(v)}</option>'
        for v in versions
    )
    trunc_note = (
        "<p class=muted>&#9888; The month axis hit the 30-year safety cap; the earliest months "
        "are shown and the remainder truncated (check the file for corrupt far-future dates).</p>"
        if data["truncated"]
        else ""
    )
    intro = _explain(
        "The seven graph families of the Performance Analysis Summary workbook, recreated "
        "live from the loaded schedule(s): a monthly census of where the remaining work sits "
        "(G1), the bow-wave of activity starts and finishes against the baseline (G2), the "
        "BEI/HMI execution-index curves (G3), the workoff burden of past-due baseline work "
        "(G4), the duration-ratio S-curve and histogram (G5), and three portfolio quad charts "
        "with one dot per loaded version (G6/G7).",
        "Time-series charts share a month axis; the vertical dashed line is the data date. "
        "Counts left of the line are history (actuals); everything right of it is forecast. "
        "Index curves stop at the data date — no index is fabricated for future months. N/A "
        "means the qualifying population is empty, never zero-filled.",
        "Where the remaining work is piling up (bow wave), whether execution is keeping pace "
        "with the baseline (BEI/HMI), how much past-due baseline work is being carried "
        "(workoff burden), how realistic remaining durations are (DRM), and which loaded "
        "version sits in the danger quadrant of each portfolio quad.",
    )
    # ── The panel contract for this page. The provenance chip is the SERIES chip on every
    # visual (the stepper walks G1-G5 through the whole loaded list, so a single-file chip
    # would be falsified on the first tick); the tools strip is panel-scoped because each
    # .tile.panel holds EXACTLY ONE chart, so one ⛶ can never desync a sibling's label.
    prov = _series_prov_chip(schedules)
    head = _panel_head("Performance Analysis Summary", prov=prov)
    # the ONLY figure any take on this page quotes: `sel`, already rendered verbatim by the
    # selected <option> and the export href in the form directly below this line
    intro_take = (
        f"<p class=sf-take data-no-i18n>G1&ndash;G5 open on {_e(sel)}; the stepper below walks "
        "them through every loaded file, while the G6/G7 quads always plot them all.</p>"
    )
    tile_export = f' data-export="/export/xlsx/performance?file={_e(sel)}"'
    tile_prov = f"<div class=tile-prov>{prov}</div>"
    tile_tools = (
        '<span class="tile-actions sf-tools" data-noprint=1>'
        "<button type=button data-sf-excel "
        'title="Export every Performance-Summary dataset (this visual&#39;s series is one of '
        'its sheets) &mdash; opens in Excel" '
        'aria-label="Export this visual&#39;s data to Excel">⤓ EXCEL</button>'
        "<button type=button data-sf-big aria-pressed=false "
        'title="Enlarge / shrink this visual" '
        'aria-label="Enlarge this visual">⛶ ENLARGE</button></span>'
    )
    # bandit B608 false positive: this is server-rendered HTML (a <select> control + prose
    # containing the words select/from), not SQL construction.
    return f"""
<div class=panel>{head}{intro_take}
<p class=muted>Recreates the operator's <b>PerformanceAnalysisSummary</b> reference workbook
(G1&ndash;G7) from the loaded files &mdash; no manual pasting: every series below is computed
from the schedule's own dates, baseline, progress and logic, and matches the engine figures
cited on the other pages.</p>{intro}{trunc_note}
<form method=get action=/performance class=viz-controls>
<label>Project graphs (G1&ndash;G5) use:&nbsp;<select name=file data-sf-autosubmit>
{opts}</select></label>
<noscript><button type=submit>Apply</button></noscript>
<a class=btn-link href="/export/xlsx/performance?file={_e(sel)}">&#11015; Excel (all datasets)</a>
</form>
<div class=viz-controls>
<button id=perfPrev type=button>&#9664; Prev</button>
<span id=perfStep class=muted data-no-i18n></span>
<button id=perfNext type=button>Next &#9654;</button>
<button id=perfPlay type=button>&#9654; Play</button>
<span class=muted>animates G1&ndash;G5 through every loaded file (the caption names the file
shown at each step); the quads ring the current file's dot</span>
</div></div>
<div class=mosaic id=perfGrid>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: per calendar month, the tasks &amp; milestones ACTIVE in that month (span overlaps it) — total, completed, and still to-go — plus how many sit on the longest path.\n\nHOW TO READ: the to-go area right of the data date is the remaining-work profile; a hump far right of the baseline plan is the bow wave. The longest-path line shows how much of each month's work controls the finish.\n\nDECIDE: which months are overloaded with remaining work and deserve resource/logic scrutiny.">G1 &mdash; Completed vs Work-to-Go (Tasks &amp; Milestones)</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=g1Census></div><p class=sf-take data-no-i18n>Every task and milestone active in each month, split completed vs still to go, with the longest-path share drawn over it.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the same census restricted to NORMAL tasks (no milestones): active, to-go, and longest-path counts per month.\n\nHOW TO READ: normal tasks carry the real work; a widening gap between the active line and the to-go line left of the data date is completed work, and the to-go line right of it is the workload still ahead.\n\nDECIDE: whether the remaining normal-task load is spread or spiking.">G1 &mdash; Work-to-Go (Normal Tasks)</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=g1Normal></div><p class=sf-take data-no-i18n>The same monthly census with milestones removed, so the line is the remaining normal-task workload on its own.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: activity STARTS per month — baselined vs scheduled/forecast vs actual (lines), with stacked bars for starts that happened late vs baseline (&le;30 / 31&ndash;60 / &gt;60 days).\n\nHOW TO READ: actuals tracking under the baseline line = starts falling behind; tall late-bars show how late. Right of the data date the scheduled line is the forecast start plan.\n\nDECIDE: whether work is being initiated on pace (a start bow-wave precedes a finish bow-wave).">G2 &mdash; Activity Starts (baselined / scheduled / actual + late buckets)</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=g2Starts></div><p class=sf-take data-no-i18n>Monthly activity starts on three bases &mdash; baselined, scheduled and actual &mdash; with the late-start buckets stacked beneath them.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: activity FINISHES per month — baselined vs scheduled/forecast vs actual (lines) with late-finish buckets (&le;30 / 31&ndash;60 / &gt;60 days vs baseline).\n\nHOW TO READ: if starts are on pace but finishes lag, in-progress work is piling up (the classic bow wave); the late buckets show the severity distribution.\n\nDECIDE: whether completion (not initiation) is the constraint, and how much forecast finish work is stacked after the data date.">G2 &mdash; Activity Finishes (baselined / scheduled / actual + late buckets)</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=g2Finishes></div><p class=sf-take data-no-i18n>Monthly activity finishes on the same three bases, with the late-finish buckets stacked beneath them.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: cumulative S-curves — baselined, scheduled and actual starts and finishes accumulated over time.\n\nHOW TO READ: the horizontal gap between the baseline curve and the actual curve is schedule slip in time units; a scheduled curve bending right of baseline is the re-planned (slipped) plan.\n\nDECIDE: how far behind the baseline the schedule is running and whether the recovery slope is credible.">G2 &mdash; Cumulative S-curves (starts &amp; finishes)</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=g2Cum></div><p class=sf-take data-no-i18n>The same starts and finishes accumulated, so the horizontal gap between the baseline and actual curves reads as elapsed slip.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: execution-index curves for STARTS — BEI-Starts (cumulative actual &divide; cumulative baselined) and the monthly HMI-Starts hit rate with its 3-month rolling average. Curves stop at the data date; nothing is projected.\n\nHOW TO READ: BEI &lt; 0.95 (DCMA practice band) = execution behind plan; HMI is the sharper month-by-month pulse.\n\nDECIDE: whether start execution is recovering or deteriorating.">G3 &mdash; Start execution indices (BEI / HMI)</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=g3Starts></div><p class=sf-take data-no-i18n>Cumulative BEI-Starts against the monthly HMI-Starts pulse and its rolling average, both stopping at the data date.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the same indices for FINISHES — BEI-Finishes and monthly HMI-Finishes (+ 3-mo rolling average).\n\nHOW TO READ: finish indices below the start indices mean work is started but not being closed out — the in-progress pileup signature.\n\nDECIDE: whether completion discipline (not just starts) is holding.">G3 &mdash; Finish execution indices (BEI / HMI)</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=g3Finishes></div><p class=sf-take data-no-i18n>The same two indices for finishes, so start discipline and closeout discipline can be read apart.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: workoff burden for STARTS. Above the axis, each month's starts categorized: on-plan (baselined that month), early, workoff of a PAST-DUE baseline, past-due backlog now forecast here, and slipped future baseline. BELOW the axis, the same un-started work mirrored at the month its baseline promised it.\n\nHOW TO READ: below-axis bars are broken promises at their original month; the matching above-axis bars show where that work has been pushed — the further right, the bigger the bow wave.\n\nDECIDE: how much past-due work the forecast is carrying and where it has been re-stacked.">G4 &mdash; Workoff burden (starts)</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=g4Starts></div><p class=sf-take data-no-i18n>Un-started baseline work mirrored below the axis at the month it was promised, and above it at the month it is now forecast.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the same workoff-burden categorization for FINISHES — where past-due baseline finishes went, and the un-finished backlog mirrored below the axis at its baselined month.\n\nHOW TO READ: a tall past-due (workoff) stack just right of the data date = a recovery plan betting on immediate catch-up; spread far right = acknowledged slip.\n\nDECIDE: whether the finish workoff plan is credible or front-loaded hope.">G4 &mdash; Workoff burden (finishes)</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=g4Finishes></div><p class=sf-take data-no-i18n>The same workoff view for finishes &mdash; promised below the axis, re-planned above it.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the Duration Ratio S-curve — every COMPLETED task's actual duration &divide; baseline duration (DRM), sorted ascending against cumulative probability.\n\nHOW TO READ: DRM 1.0 = took exactly as long as baselined. The curve's crossing of 1.0 tells you what share of completed work beat its baseline; a long right tail = chronic under-estimation.\n\nDECIDE: what growth factor history supports when judging the remaining durations (and any SRA).">G5 &mdash; Duration Ratio S-curve</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=g5Scurve></div><p class=sf-take data-no-i18n>Every completed activity's actual-to-baseline duration ratio, sorted against cumulative probability.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: histogram of the MIDDLE 70% of completed-task duration ratios (the workbook's convention — the tails are excluded from the bars but included in the min/avg/max chips).\n\nHOW TO READ: a mode below 1.0 = durations typically beaten; mass above 1.0 = systematic overrun. The chips carry the full-population min / average / max and the excluded-count disclosure.\n\nDECIDE: the realistic duration growth factor for forecasts.">G5 &mdash; Duration Ratio histogram (middle 70%)</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=g5Hist></div><div id=g5Stats class=stat-row></div><p class=sf-take data-no-i18n>The middle 70% of those duration ratios as a histogram; the chips beneath carry the full-population min, average and max.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: portfolio quad — HMI (tasks, latest period) vs CEI (finish) for EVERY loaded version; dashed guides at the 0.95 practice band used across this tool's index metrics.\n\nHOW TO READ: top-right = hitting current commitments AND closing out to plan; bottom-left = missing both. A version drifting left over time is losing period discipline.\n\nDECIDE: which version/update deserves the deep-dive first.">G3 quad &mdash; HMI vs CEI (per loaded version)</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=quadHmiCei></div><p class=sf-take data-no-i18n>One dot per loaded version, plotting period hit rate against closeout performance inside the practice-band guides.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: portfolio quad — to-go starts ratio vs to-go finishes ratio (remaining scheduled work &divide; work the baseline said should remain). Guides at 1.0 = carrying exactly what the baseline planned.\n\nHOW TO READ: above/right of 1.0 = more to-go work than planned (the bow wave, quantified); far above the diagonal = finishes lagging starts.\n\nDECIDE: which version is quietly accumulating un-done work.">G6 quad &mdash; To-Go Starts vs To-Go Finishes</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=quadRatio></div><p class=sf-take data-no-i18n>One dot per loaded version, plotting remaining scheduled starts against remaining scheduled finishes, each against what the baseline left.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: portfolio quad — BEI (baseline execution) vs the share of the to-go work sitting on the critical path. Vertical guide at BEI 0.95 (DCMA practice); horizontal guide at the portfolio median critical share (labeled — no industry threshold exists for this axis).\n\nHOW TO READ: bottom-right (high BEI, low critical share) is healthy; top-left (poor execution AND a critical-heavy backlog) is the danger quadrant.\n\nDECIDE: which version pairs poor execution with a critical-path-loaded backlog.">G7 quad &mdash; BEI vs % critical of to-go work</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=quadBeiCp></div><p class=sf-take data-no-i18n>One dot per loaded version, plotting baseline execution against how much of the remaining work sits on the critical path.</p></section>
</div>
<script type="application/json" id=perfData>{blob}</script>
<script defer src="/static/performance.js"></script>
<script src="/static/panelkit.js"></script>"""  # nosec B608 (HTML, not SQL)
