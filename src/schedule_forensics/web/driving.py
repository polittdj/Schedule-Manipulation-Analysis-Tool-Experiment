"""The driving-path page family — /driving-path and its data/panel helpers.

Monolith split, phase 3 slice 2 (ADR-0351), extracted VERBATIM from ``web/app.py``: every
function, constant, docstring and comment moves byte-for-byte, only the module boundary changes.

The seam is the AST transitive closure of the family's entry points, and with the shared kernel
already out (ADR-0350) that closure is finally the page's own: five entry points plus
``_task_iso_dates`` and ``_corridor_chips``, neither referenced from anywhere else.

Layering: ``app`` → ``driving`` → ``components`` → ``chrome`` → ``state`` → engine/model.
Nothing here imports ``web.app``. That constraint is what moved ``_task_name_across`` and
``_EVO_TIER_LABEL`` DOWN into ``components`` in the same commit — this module needs both, and
reaching back up into ``app.py`` for them would have made the cut circular.
"""

from __future__ import annotations

import json
from typing import cast
from urllib.parse import quote

from schedule_forensics.engine import compute_driving_slack
from schedule_forensics.engine.cpm import CPMResult, offset_to_datetime, span_start_datetime
from schedule_forensics.engine.driving_path import (
    DrivingPathEvolution,
    DrivingPathSnapshot,
    compute_driving_path_evolution,
)
from schedule_forensics.engine.driving_slack import (
    DEFAULT_SECONDARY_MAX_DAYS,
    DEFAULT_TERTIARY_MAX_DAYS,
    PathDirection,
    date_basis,
)
from schedule_forensics.engine.path_trace import topo_order
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.components import (
    _EVO_TIER_LABEL,
    _mdY,
    _panel_head,
    _prov_chip,
    _series_prov_chip,
    _shell_tools,
    _task_name_across,
)
from schedule_forensics.web.state import _iso_date


def _driving_data(
    sch: Schedule,
    cpm: CPMResult,
    target: int,
    secondary: int,
    tertiary: int,
    *,
    direction: str = "predecessors",
    range_mode: str = "all",
    range_days: int = 0,
    ignore_constraints: bool = False,
    ignore_leveling: bool = False,
    with_drag: bool = False,
) -> dict[str, object]:
    """Driving-slack rows for the Gantt — tier + CPM ordinal positions for each traced UID.

    SSI Directional Path Tool options (operator 2026-07-08): ``direction`` traces
    predecessors / successors / both; ``range_mode`` "slack" keeps only rows with driving
    slack <= ``range_days`` (SSI "Get dependencies with Driving Slack <= x"), "all" keeps the
    full trace; ``ignore_constraints`` / ``ignore_leveling`` mirror SSI's same-named options —
    stored dates still govern dated tasks (a fully-dated file traces identically; the flags
    reach only the CPM fallback for undated tasks and the calendar basis — ADR-0251);
    ``with_drag`` adds Devaux DRAG (SSI-validated, test_ssi_drag_exact) per path activity.
    The payload always carries ``parallel_paths`` — the on-path set decomposed into its
    parallel branches — so the client can render the SSI "Separate parallel paths" output.
    Defaults reproduce the original behavior byte-for-byte."""
    by_id = sch.tasks_by_id
    # per-task governing calendar name for per-row non-working shading (ADR-0243)
    _cal_name_by_uid = {c.uid: c.name for c in sch.calendars}
    _proj_cal_name = sch.calendar.name
    if target not in by_id:
        return {
            "target_uid": target,
            "target_name": None,
            "rows": [],
            "note": f"UID {target} is not in this schedule.",
        }
    if by_id[target].is_summary:
        # summary rollups are not in the logic network — tracing one raised before
        return {
            "target_uid": target,
            "target_name": by_id[target].name,
            "rows": [],
            "note": f"UID {target} is a summary rollup — pick one of its activities instead.",
        }
    try:
        dir_enum = PathDirection(direction)
    except ValueError:
        dir_enum = PathDirection.PREDECESSORS
    results = compute_driving_slack(
        sch,
        target_uid=target,
        secondary_max_days=secondary,
        tertiary_max_days=tertiary,
        cpm_result=cpm,
        direction=dir_enum,
        ignore_constraints=ignore_constraints,
        ignore_leveling_delay=ignore_leveling,
    )
    if range_mode == "slack":
        keep = {
            uid
            for uid, r in results.items()
            if uid == target or int(r.driving_slack_days) <= max(0, range_days)
        }
        results = {uid: r for uid, r in results.items() if uid in keep}
    drag_by_uid: dict[int, object] = {}
    if with_drag:
        from schedule_forensics.engine.drag import compute_drag

        drag_by_uid = {uid: float(d.drag_days) for uid, d in compute_drag(sch, results).items()}
    cal = sch.calendar
    per_day = cal.working_minutes_per_day
    # display the AS-SCHEDULED stored-date axis the slack math runs on — pure CPM
    # timings pack real files' completed work at the project start (wrong bars/dates)
    basis_start, basis_finish = date_basis(sch, cpm)
    date_driven = set(cpm.date_driven)

    def day(ordinal: int | None) -> str | None:
        if ordinal is None:
            return None
        return offset_to_datetime(sch.project_start, max(ordinal, 0), cal).date().isoformat()

    def day_start(ordinal: int | None, finish_ordinal: int | None) -> str | None:
        """Start-role sibling of :func:`day` (ADR-0348 day-boundary spelling)."""
        if ordinal is None:
            return None
        return (
            span_start_datetime(sch.project_start, max(ordinal, 0), finish_ordinal or 0, cal)
            .date()
            .isoformat()
        )

    # Driving links: each traced activity's immediate logic successors that are themselves on the
    # trace to the target — the "what is this linked to on the way to the target" detail (e.g.
    # UID 8022 → UID 152). on_path marks the successor that keeps the chain on the 0-slack path.
    trace_ids = set(results)
    drives: dict[int, list[dict[str, object]]] = {uid: [] for uid in trace_ids}
    for rel in sch.relationships:
        if rel.predecessor_id in trace_ids and rel.successor_id in trace_ids:
            drives[rel.predecessor_id].append(
                {
                    "uid": rel.successor_id,
                    "type": rel.type.value,
                    "lag_days": round(rel.lag_minutes / per_day, 1) if per_day else 0.0,
                    "on_path": results[rel.successor_id].on_driving_path,
                }
            )

    rows = []
    for uid in sorted(results):
        timing = cpm.timings.get(uid)
        task = by_id[uid]
        start_ord = basis_start.get(uid, timing.early_start if timing else None)
        finish_ord = basis_finish.get(uid, timing.early_finish if timing else None)
        if task.start is not None and task.finish is not None:
            # the same stored-or-CPM split date_basis() makes; stored dates render
            # verbatim (an actual start may legally predate the project start)
            start_iso: str | None = task.start.date().isoformat()
            finish_iso: str | None = task.finish.date().isoformat()
        else:
            start_iso, finish_iso = day_start(start_ord, finish_ord), day(finish_ord)
        rows.append(
            {
                "unique_id": uid,
                "name": task.name,
                "wbs": task.wbs or "",
                "tier": str(results[uid].tier),
                "driving_slack_days": int(results[uid].driving_slack_days),
                "on_driving_path": results[uid].on_driving_path,
                "calendar": (
                    _cal_name_by_uid.get(task.calendar_uid, _proj_cal_name)
                    if task.calendar_uid is not None
                    else _proj_cal_name
                ),
                "start_ord": start_ord,
                "finish_ord": finish_ord,
                "start": start_iso,
                "finish": finish_iso,
                "baseline_finish": _iso_date(task.baseline_finish),
                "duration_days": round(
                    task.duration_minutes / (1440 if task.duration_is_elapsed else per_day), 1
                )
                if per_day
                else 0.0,
                "total_float_days": (
                    float(round(timing.total_float / per_day, 1)) if timing else None
                ),
                "percent_complete": task.percent_complete,
                # robust "complete" for the hide-completed toggles: a real .mpp/.xer may
                # report a done activity at 99.x% while carrying an actual finish — treat
                # an actual finish (or >=100%) as complete so the toggle never misses it.
                "complete": task.is_complete or task.actual_finish is not None,
                "is_milestone": task.is_milestone,
                "date_driven": uid in date_driven,
                "drag_days": drag_by_uid.get(uid),
                "resource_names": ", ".join(task.resource_names),
                # immediate logic successors within this trace (uid, type, lag, on_path) — the
                # "linked to UID X" detail surfaced by the Drives → column
                "drives": drives[uid],
                # mapped custom fields populated on this task (label → value); the grid offers
                # each as an optional column (ADR-0088 mapping → ADR-0093 display)
                "custom": dict(task.custom_field_map),
            }
        )
    # waterfall order: earliest finish first, so the chain cascades to the target's finish
    rows.sort(key=lambda r: (r["finish_ord"] is None, r["finish_ord"], r["start_ord"]))
    # the trace is logic-only by definition: say how much of the schedule it covers, so
    # absent (e.g. unlinked completed) work reads as explained, not missing
    activities = sum(1 for t in sch.tasks if not t.is_summary)
    coverage = (
        f"{len(rows)} of the schedule's {activities} activities have a logic path to this target"
    )
    driven_in_trace = sum(1 for r in rows if r["date_driven"])
    if driven_in_trace:
        coverage += f"; {driven_in_trace} traced date(s) are not supported by logic (see report)"
    # SSI "Separate parallel paths": decompose the on-path set into serial branches — a new
    # branch starts wherever a path task is not the single continuation of the previous one
    path_set = {uid for uid, r in results.items() if r.on_driving_path}
    succ_in_path: dict[int, list[int]] = {u: [] for u in path_set}
    pred_in_path: dict[int, list[int]] = {u: [] for u in path_set}
    for rel2 in sch.relationships:
        if rel2.predecessor_id in path_set and rel2.successor_id in path_set:
            succ_in_path[rel2.predecessor_id].append(rel2.successor_id)
            pred_in_path[rel2.successor_id].append(rel2.predecessor_id)
    ordered_path = [u for u in topo_order(sch, path_set)]
    visited: set[int] = set()
    branches: list[list[int]] = []
    for u in ordered_path:
        if u in visited:
            continue
        chain = [u]
        visited.add(u)
        cur = u
        while True:
            nxt = [x for x in succ_in_path.get(cur, ()) if x not in visited]
            if len(nxt) == 1 and len(pred_in_path.get(nxt[0], ())) <= 1:
                cur = nxt[0]
                chain.append(cur)
                visited.add(cur)
            else:
                break
        branches.append(chain)
    parallel_paths = [
        {"label": f"Path 01 ({i})", "uids": chain} for i, chain in enumerate(branches, 1)
    ]

    return {
        "target_uid": target,
        "target_name": by_id[target].name,
        "data_date": sch.status_date.date().isoformat() if sch.status_date else None,
        "coverage": coverage,
        # the schedule's mapped custom fields (declared order) → optional grid columns
        "custom_field_labels": list(sch.custom_field_labels),
        "rows": rows,
        "parallel_paths": parallel_paths,
    }


def _corridor_chips(snap: DrivingPathSnapshot) -> str:
    """The corridor as an ordered chain of UID — name chips; entered chips flag the new ones."""
    if not snap.between.path:
        return f"<span class=muted>{_e(snap.status)}</span>"
    entered = set(snap.entered)
    chips: list[str] = []
    for uid, name in zip(snap.between.path, snap.names, strict=True):
        cls = "ev-entered" if uid in entered else "ev-stayed"
        chips.append(f'<span class="dp-chip {cls}">{uid} &mdash; {_e(name)}</span>')
    return " <span class=dp-arrow>&rarr;</span> ".join(chips)


def _task_iso_dates(
    sch: Schedule,
    basis_start: dict[int, int],
    basis_finish: dict[int, int],
    uid: int,
) -> tuple[str | None, str | None]:
    """A task's (start, finish) as ISO dates — the same stored-or-CPM basis the Path page uses
    (stored dates render verbatim; otherwise the date_basis offsets convert on the calendar)."""
    task = sch.tasks_by_id.get(uid)
    if task is None:
        return None, None
    if task.start is not None and task.finish is not None:
        return task.start.date().isoformat(), task.finish.date().isoformat()
    cal = sch.calendar
    s, f = basis_start.get(uid), basis_finish.get(uid)
    si = (
        span_start_datetime(sch.project_start, max(s, 0), f or 0, cal).date().isoformat()
        if s is not None
        else None
    )
    fi = (
        offset_to_datetime(sch.project_start, max(f, 0), cal).date().isoformat()
        if f is not None
        else None
    )
    return si, fi


def _driving_path_gantt(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    evo: DrivingPathEvolution,
    a_name: str,
    b_name: str,
) -> dict[str, object]:
    """Per-version corridor activities with dates — the payload the animated Gantt steps through.

    Each version carries the corridor's activities (ordered, with start/finish + an ``entered``
    flag vs the prior version) so the JS can draw the bars on a date axis held fixed across every
    version, the corridor visibly shifting as the schedule slips."""
    version_data: list[dict[str, object]] = []
    # Union of every calendar across all versions (name -> shading def), so the page can register
    # them once with SFTimescale.setCalendars and resolve each row's per-task calendar name (#382
    # shipped the JS read `a.calendar` but the server never emitted the field or the registry, so
    # the corridor fell back to a flat project-calendar shade — audit ADR-0247 completes the wiring).
    calendars: dict[str, dict[str, object]] = {}
    for sch, cpm, snap in zip(schedules, cpms, evo.snapshots, strict=True):
        basis_start, basis_finish = date_basis(sch, cpm)
        by_id = sch.tasks_by_id
        entered = set(snap.entered)
        # each task's GOVERNING calendar name (ADR-0243), matching the /analysis grid's resolution:
        # the task's own calendar_uid -> its registered name, else the project calendar (MSP inherit).
        cal_name_by_uid = {c.uid: c.name for c in sch.calendars}
        proj_cal_name = sch.calendar.name
        for cal in (sch.calendar, *sch.calendars):
            if cal is not None and cal.name:
                calendars.setdefault(
                    cal.name,
                    {
                        "name": cal.name,
                        "work_weekdays": list(cal.work_weekdays),
                        "holidays": [d.isoformat() for d in cal.holidays],
                    },
                )
        acts: list[dict[str, object]] = []
        for uid, name in zip(snap.between.path, snap.names, strict=True):
            start, finish = _task_iso_dates(sch, basis_start, basis_finish, uid)
            task = by_id.get(uid)
            cal_name: str | None = None
            if task is not None:
                cuid = task.calendar_uid
                cal_name = (
                    cal_name_by_uid.get(cuid, proj_cal_name) if cuid is not None else proj_cal_name
                )
            acts.append(
                {
                    "uid": uid,
                    "name": name,
                    "start": start,
                    "finish": finish,
                    "is_milestone": task.is_milestone if task is not None else False,
                    "entered": uid in entered,
                    "calendar": cal_name,
                }
            )
        version_data.append(
            {
                "label": snap.label,
                "data_date": snap.status_date,
                "status": snap.status,
                "change_note": snap.change_note,
                "drives": snap.between.drives,
                "activities": acts,
            }
        )
    return {
        "source_uid": evo.source_uid,
        "target_uid": evo.target_uid,
        "source_name": a_name,
        "target_name": b_name,
        "versions": version_data,
        "calendars": list(calendars.values()),
    }


def _driving_tiers_panel(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    target: int,
    *,
    ignore_constraints: bool = False,
    ignore_leveling: bool = False,
) -> str:
    """Three columns of the activities driving ``target`` in the LATEST version, bucketed by
    driving-slack tier (ADR-0011): critical/driving (0 working days — the driving path), secondary
    (<= 10 days), tertiary (<= 20 days). Fewer days = more control over the target.

    ``ignore_constraints`` / ``ignore_leveling`` are the active page trace options (the caller has
    already re-solved the schedules with them); they are embedded so the tiers Excel export runs on
    the SAME network the panel shows (ADR-0174)."""
    sch, cpm = schedules[-1], cpms[-1]
    if target not in sch.tasks_by_id:
        return ""  # the corridor branch already reports a target absent from every version
    try:
        results = compute_driving_slack(sch, target, cpm_result=cpm)
    except (KeyError, ValueError):
        return ""
    by_id = sch.tasks_by_id
    buckets: dict[str, list[tuple[int, str, float]]] = {
        "driving": [],
        "secondary": [],
        "tertiary": [],
    }
    for uid, r in results.items():
        if uid == target:
            continue
        label = _EVO_TIER_LABEL.get(r.tier)
        if label in buckets:
            t = by_id.get(uid)
            buckets[label].append(
                (uid, t.name if t is not None else f"UID {uid}", float(r.driving_slack_days))
            )
    for items in buckets.values():
        items.sort(key=lambda a: (a[2], a[0]))
    cols = [
        ("driving", "Critical / driving", "0 days"),
        ("secondary", "Secondary", f"&le; {DEFAULT_SECONDARY_MAX_DAYS} days"),
        ("tertiary", "Tertiary", f"&le; {DEFAULT_TERTIARY_MAX_DAYS} days"),
    ]
    blocks: list[str] = []
    for key, title, sub in cols:
        items = buckets[key]
        if items:
            rows = "".join(
                f"<tr><td class=num>{u}</td><td>{_e(n)}</td><td class=num>{d:.1f}</td></tr>"
                for u, n, d in items
            )
            body = (
                "<table class=card-table><tr><th scope=col>UID</th>"
                "<th scope=col>Activity</th><th scope=col>Slack (d)</th></tr>"
                f"{rows}</table>"
            )
        else:
            body = "<p class=muted>none</p>"
        blocks.append(
            f'<div style="flex:1;min-width:15em"><h3>{title} '
            f"<span class=muted>({len(items)} &middot; {sub})</span></h3>{body}</div>"
        )
    focus = by_id.get(target)
    fname = _e(focus.name) if focus is not None else f"UID {target}"
    # The file whose driving path this is (operator 2026-07-08: a bold banner naming the traced
    # file, because the driving path can differ between files). Its display label doubles as the
    # /api/analysis + export token, resolved by _find_schedule.
    file_label = sch.source_file or sch.name
    banner = f'<p class="dp-file-banner">Driving path computed on <b>{_e(file_label)}</b></p>'
    # ── Panel contract (Mission Ops rank 11). The tier counts the takes quote are the SAME
    # `buckets` the three columns below are rendered from — one pass, so a take can never
    # disagree with the table beside it.
    n_drv, n_sec, n_ter = (len(buckets[k]) for k in ("driving", "secondary", "tertiary"))
    prov = _prov_chip(sch)
    # ⤓ EXCEL for the TIERS panel only. The URL carries the very target + trace options this
    # panel was solved with (ADR-0174 keeps the export on the same network), and every one of
    # those three values comes from the single `<form method=get action=/driving-path>` above —
    # there is no client-side control that can move them without a full navigation, so the
    # server-rendered attribute cannot go stale while the operator looks at it.
    tiers_export = (
        f"/export/xlsx/driving-tiers/{quote(file_label, safe='')}?target={target}"
        f"&ignore_constraints={int(ignore_constraints)}&ignore_leveling={int(ignore_leveling)}"
    )
    tiers_head = _panel_head(
        f"Driving tiers to {target} &mdash; {fname}",
        tools=_shell_tools(
            export_title=(
                "Export every activity driving this target, by tier, on this page's active "
                "trace basis — opens in Excel"
            )
        ),
        prov=prov,
    )
    tiers_take = (
        f"<p class=sf-take data-no-i18n>{n_drv} activities sit at 0 days of driving slack to "
        f"{fname} &mdash; the driving path itself; {n_sec} more are within "
        f"{DEFAULT_SECONDARY_MAX_DAYS} working days and {n_ter} within "
        f"{DEFAULT_TERTIARY_MAX_DAYS}.</p>"
    )
    # Interactive "all driving-tier activities" chart (operator #72): one table across the three
    # tiers with a Tier + Slack(d) column, a Columns dropdown (any standard/custom field, set
    # once), a Filter box, and an Excel export of the selection — the same drill pattern as the
    # ribbon / finding-citation tables. Tier + slack are embedded here (from the same driving-slack
    # pass the buckets use); the field columns come from same-origin /api/analysis.
    tier_rows = [
        {"uid": u, "tier": key, "slack": round(d, 1)}
        for key, _title, _sub in cols
        for u, _n, d in buckets[key]
    ]
    drill = ""
    if tier_rows:
        blob = json.dumps(
            {
                "file": file_label,
                "target": target,
                "rows": tier_rows,
                "ignore_constraints": 1 if ignore_constraints else 0,
                "ignore_leveling": 1 if ignore_leveling else 0,
            }
        ).replace("<", "\\u003c")
        # DELIBERATELY ⛶ ONLY, NO ⤓ / NO `data-export` on this panel. driving_tiers.js:167-172
        # rebuilds `&cols=<live selection>` on every render and persist.js remembers the
        # selection across visits, so a server-pinned data-export would hand the operator the
        # DEFAULT columns while they are looking at theirs — the round-10 /performance defect.
        # The panel's own column-aware Excel control (rendered by driving_tiers.js) is the one
        # export here, and the take points at it.
        drill = (
            "<div class=panel>"
            + _panel_head("All driving-tier activities", tools=_shell_tools(), prov=prov)
            + f"<p class=sf-take data-no-i18n>The same {n_drv} driving, {n_sec} secondary and "
            f"{n_ter} tertiary activities as the tiers above, in one table &mdash; the Excel "
            "button beside the Columns picker exports exactly the columns you select.</p>"
            "<p class=muted>Every activity driving this target, across all three tiers, in one "
            "chart. Add any standard or custom field (set once), filter by any shown column, and "
            "export exactly your columns to Excel."
            + (
                " <b>Trace options active:</b> every column shown (and exported) shares the "
                "re-solved counterfactual basis — stored-schedule date/float columns are "
                "hidden until the options are off (ADR-0265)."
                if (ignore_constraints or ignore_leveling)
                else ""
            )
            + "</p>"
            "<div id=drivingTiers></div>"
            f'<script type="application/json" id=drivingTiersData>{blob}</script>'
            '<script src="/static/driving_tiers.js"></script></div>'
        )
    return (
        f'<div class=panel data-export="{tiers_export}">{tiers_head}{tiers_take}'
        f"{banner}"
        "<p class=muted>Activities driving this target in the latest version, by their driving "
        "slack: <b>critical</b> (0 working days &mdash; the driving path), <b>secondary</b>, and "
        "<b>tertiary</b>. Fewer days = more control over the target (ADR-0011).</p>"
        '<div style="display:flex;gap:1em;align-items:flex-start;flex-wrap:wrap">'
        f"{''.join(blocks)}</div></div>"
        f"{drill}"
    )


def _driving_tier_trend(schedules: list[Schedule], cpms: list[CPMResult], target: int) -> str:
    """Per-version trend of how the driving path to ``target`` degrades: the count of activities at
    each driving-slack tier — driving (0 days) / secondary (<=10) / tertiary (<=20) — over the
    loaded versions, oldest first. A GROWING driving count means slack is eroding into the path
    (more activities now control the target's date); the delta column flags that movement."""
    if len(schedules) < 2:
        return ""
    rows: list[tuple[str, str, int | None, int | None, int | None, int | None]] = []
    prior_driving: int | None = None
    any_present = False
    for sch, cpm in zip(schedules, cpms, strict=True):
        label = sch.source_file or sch.name
        dd = _mdY(sch.status_date) if sch.status_date else "—"
        if target not in sch.tasks_by_id:
            rows.append((label, dd, None, None, None, None))
            continue
        any_present = True
        counts = {"driving": 0, "secondary": 0, "tertiary": 0}
        try:
            for uid, r in compute_driving_slack(sch, target, cpm_result=cpm).items():
                if uid == target:
                    continue
                lab = _EVO_TIER_LABEL.get(r.tier)
                if lab in counts:
                    counts[lab] += 1
        except (KeyError, ValueError):
            pass
        delta = None if prior_driving is None else counts["driving"] - prior_driving
        prior_driving = counts["driving"]
        rows.append((label, dd, counts["driving"], counts["secondary"], counts["tertiary"], delta))
    if not any_present:
        return ""

    def num(v: int | None) -> str:
        return "—" if v is None else str(v)

    body = ""
    for label, dd, drv, sec, ter, delta in rows:
        if delta is None or delta == 0:
            dtxt = "" if delta is None else "0"
        elif delta > 0:  # the driving path GREW — slack eroded (degradation)
            dtxt = f'<span style="color:var(--bad)">&#9650;+{delta}</span>'
        else:
            dtxt = f'<span style="color:var(--ok)">&#9660;{delta}</span>'
        body += (
            f"<tr><td>{_e(label)}</td><td>{dd}</td><td class=num>{num(drv)}</td>"
            f"<td class=num>{num(sec)}</td><td class=num>{num(ter)}</td>"
            f"<td class=num>{dtxt}</td></tr>"
        )
    # ── Panel contract (Mission Ops rank 11). ⛶ ONLY — deliberately NO ⤓: no export endpoint
    # serves PER-VERSION driving-slack tier counts. /export/{fmt}/driving-tiers is single-file /
    # per-activity and /export/{fmt}/evolution is compute_path_evolution (CRITICAL-path
    # evolution, a different analysis), so any ⤓ here would be a live-but-wrong link.
    # The take reads the FIRST and LAST rows that actually carry counts — the same `rows` list
    # the table below is rendered from, so the two can never disagree.
    present = [(lbl, drv) for lbl, _dd, drv, _s, _t, _d in rows if drv is not None]
    first_lbl, first_drv = present[0]
    last_lbl, last_drv = present[-1]
    if len(present) > 1 and first_lbl != last_lbl:
        trend_take = (
            f"<p class=sf-take data-no-i18n>The driving (0d) tier holds {last_drv} activities in "
            f"{_e(last_lbl)}, against {first_drv} in {_e(first_lbl)} &mdash; the first loaded "
            "version that carries this target.</p>"
        )
    else:
        trend_take = (
            f"<p class=sf-take data-no-i18n>Only {_e(first_lbl)} carries this target, so there "
            f"is no version-to-version movement to read: {first_drv} activities at 0 days.</p>"
        )
    return (
        "<div class=panel>"
        + _panel_head(
            "Driving-slack degradation trend",
            tools=_shell_tools(),
            prov=_series_prov_chip(schedules),
        )
        + trend_take
        + "<p class=muted>How the driving path to this target changes across the loaded versions "
        "(oldest first): the count of activities at each driving-slack tier. A rising "
        "<b>driving (0d)</b> count means slack is eroding into the path &mdash; more work now "
        "controls the target's finish (ADR-0011).</p>"
        "<table class=card-table><tr><th scope=col>Version</th><th scope=col>Data date</th>"
        "<th scope=col>Driving (0d)</th><th scope=col>Secondary</th><th scope=col>Tertiary</th>"
        f"<th scope=col>&Delta; driving</th></tr>{body}</table></div>"
    )


def _driving_path_body(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    source: int | None,
    target: int | None,
    *,
    ignore_constraints: bool = False,
    ignore_leveling: bool = False,
    file_options: list[str] | None = None,
    selected_file: str = "",
    export_key: str | None = None,
) -> str:
    """Server-rendered Driving Path view: the controlling logic corridor between two chosen
    UniqueIDs, and how it changes across every loaded version (oldest first by data date) — or
    within ONE chosen file (operator 2026-07-08: the path can differ between files, so the File
    selector scopes the whole page, tiers and Gantt included, to that version).
    The counterfactual trace options (ignore constraints / leveling — a genuine
    ``_optioned_versions`` re-solve, ADR-0251) persist through the form; the page
    is directional by construction (A→B), so Path Direction lives on Path Analysis."""
    ic = " checked" if ignore_constraints else ""
    il = " checked" if ignore_leveling else ""
    file_select = ""
    if file_options and len(file_options) > 1:
        opts = '<option value="">All files (chronological)</option>' + "".join(
            f'<option value="{_e(n)}"{" selected" if n == selected_file else ""}>{_e(n)}</option>'
            for n in file_options
        )
        file_select = (
            f"<label>File <select name=file data-no-i18n "
            f'title="Trace the driving path in one chosen file — it can differ between files">'
            f"{opts}</select></label> "
        )
    export_link = ""
    if target is not None and schedules and export_key:
        # the export route looks the schedule up by SESSION KEY (filename-derived), never the
        # internal project name — the old link used last.name and 404'd (fixed 2026-07-09)
        opts = (
            f"&ignore_constraints={int(ignore_constraints)}"
            f"&ignore_leveling={int(ignore_leveling)}&drag=1&basis=resolve"
        )
        # ADR-0265: the export carries basis=resolve, so with the counterfactual options
        # active it runs on the SAME re-solved network as the tiers above (one basis per
        # page); with no options active basis=resolve is a no-op and the download is the
        # byte-identical stored-date trace. The /path page's export stays family A (stored).
        export_link = (
            f'<a class=btn-link href="/export/xlsx/path/{_e(export_key)}?target={target}{opts}" '
            'title="Exports the full trace on THIS page&#39;s basis: with trace options active '
            "it mirrors the re-solved tiers above (counterfactual network, ADR-0265); with no "
            'options it is the stored-date Path Analysis trace">'
            "&#11015; Excel (full trace to target, latest version, incl. Drag)</a>"
        )
    form = f"""
<div class=panel><form method=get action=/driving-path class=viz-controls>
{file_select}<label>From (source UniqueID): <input name=source type=number min=1
value="{source if source is not None else ""}" placeholder="UID A"></label>
<label>To (target UniqueID): <input name=target type=number min=1
value="{target if target is not None else ""}" placeholder="UID B"></label>
<label><input type=checkbox name=ignore_constraints value=1{ic}
title="Counterfactual re-solve: every version recomputed with all date constraints removed (pure logic). Diverges from the stored schedule — and from SSI's same-named option, which keeps reporting on stored dates (ADR-0251)"> Ignore constraints</label>
<label><input type=checkbox name=ignore_leveling value=1{il}
title="Counterfactual re-solve: incomplete tasks' stored dates are cleared and the CPM recomputed (a 0-day leveling delay). Diverges from the stored schedule — and from SSI's same-named option, which keeps reporting on stored dates (ADR-0251)"> Ignore leveling delay</label>
<button type=submit>Trace</button> {export_link}</form>
<p class=muted style="margin:.4em 0 0">The <b>driving path</b> from A to B is the chain of
activities controlling B's date that lie on a logic route from A &mdash; the work that, if it
slips, moves B. If A reaches B only through activities with float, the two are <b>connected</b>
but A does not <b>drive</b> B (the slack is reported instead). Trace it across every loaded
version to see the corridor shift.</p></div>"""

    tiers_html = (
        _driving_tiers_panel(
            schedules,
            cpms,
            target,
            ignore_constraints=ignore_constraints,
            ignore_leveling=ignore_leveling,
        )
        + _driving_tier_trend(schedules, cpms, target)
        if target is not None
        else ""
    )
    if tiers_html:
        # panelkit.js wires the ⛶ / ⤓ controls the three tier panels carry. Conditioned on the
        # RENDERED HTML, not on `target is not None`: with a target that no loaded version
        # contains, both sub-builders return "" and this page must not ship a script whose
        # controls do not exist. One statement covers all three return branches below.
        tiers_html += '\n<script src="/static/panelkit.js"></script>'

    if source is None or target is None:
        hint = (
            "Enter a source and a target UniqueID above to trace the driving path between them"
            + (
                " &mdash; or enter just a target to see its driving tiers above."
                if target is None
                else "."
            )
        )
        return form + tiers_html + f"<div class=panel><p class=muted>{hint}</p></div>"

    a_name = _task_name_across(schedules, source)
    b_name = _task_name_across(schedules, target)
    if a_name is None or b_name is None:
        missing = source if a_name is None else target
        return (
            form
            + tiers_html
            + (
                f'<div class="notice err">UniqueID {missing} is not present in any loaded '
                f"version.</div>"
            )
        )

    evo = compute_driving_path_evolution(schedules, cpms, source, target)
    # ── Panel contract (Mission Ops rank 11). NO `tools=` on this panel: it holds ZERO tables
    # and ZERO charts (measured: 0 tables / 0 chart-hosts / 0 svg), so ⛶ would enlarge two
    # lines of text and ⤓ would have nothing of its own to export. It is a caption panel for
    # the per-version records below it, and it wears a head + a series chip + one take only.
    # Both take figures come from `evo.snapshots` — the same object the records are rendered
    # from — and the snapshot's own `status` phrase is quoted verbatim, never paraphrased.
    n_drives = sum(1 for s in evo.snapshots if s.between.drives)
    last_snap = evo.snapshots[-1]
    if n_drives == len(evo.snapshots):
        path_take = (
            f"<p class=sf-take data-no-i18n>{source} drives {target} in every one of the "
            f"{len(evo.snapshots)} loaded versions; in the newest, {_e(last_snap.label)}, the "
            f"corridor is a {_e(last_snap.status)}.</p>"
        )
    else:
        path_take = (
            f"<p class=sf-take data-no-i18n>{source} drives {target} in {n_drives} of the "
            f"{len(evo.snapshots)} loaded versions; in the newest, {_e(last_snap.label)}, the "
            f"state is: {_e(last_snap.status)}.</p>"
        )
    header = (
        "<div class=panel>"
        + _panel_head(
            f"Driving path: {source} &mdash; {_e(a_name)} &rarr; {target} &mdash; {_e(b_name)}",
            prov=_series_prov_chip(schedules),
        )
        + path_take
        + f"<p class=muted>{len(evo.snapshots)} version(s), oldest first.</p></div>"
    )

    # animated date-axis Gantt of the corridor over the versions (ADR-0096); only when at least
    # one version actually has a corridor to draw (and there's more than one version to step).
    gantt = _driving_path_gantt(schedules, cpms, evo, a_name, b_name)
    versions = cast("list[dict[str, object]]", gantt["versions"])
    has_corridor = any(v["activities"] for v in versions)
    gantt_html = ""
    if has_corridor and len(schedules) > 1:
        blob = json.dumps(gantt).replace("<", "\\u003c")  # match the scurve/rem embeds (QC INFO)
        # ── Panel contract (Mission Ops rank 11). NO `tools=` — so no ⛶ and no ⤓, both
        # deliberately. ⛶: this panel already owns Zoom &minus;/&plus;, "View entire project"
        # (#dpFit) and Timescale…, and driving_path.js sets `forcedPx` ONLY from #dpFit and
        # never re-fits on a resize — measured, after a Fit the mount grows 1118 → 1386px while
        # the corridor table stays 1102px, so ⛶ would be right before a Fit and wrong after it.
        # ⤓: the corridor's per-version geometry has no export endpoint (driving-tiers is
        # per-activity, evolution is the CRITICAL-path analysis). Head + series chip + take.
        n_with = sum(1 for v in versions if v["activities"])
        corridor_head = _panel_head("Corridor over time", prov=_series_prov_chip(schedules))
        corridor_take = (
            f"<p class=sf-take data-no-i18n>{n_with} of the {len(versions)} loaded versions have "
            "a corridor to draw, and the date axis is held fixed across all of them &mdash; so "
            "the shift between updates reads as movement on the page, not as a re-scaled "
            "chart.</p>"
        )
        gantt_html = f"""
<div class=panel>{corridor_head}{corridor_take}
<p class=muted>The driving corridor drawn on a date axis held fixed across every version, so it
visibly shifts as the schedule slips. Step or play through the versions; activities that
<b class=ev-entered>entered</b> the corridor since the prior version are outlined.</p>
<div class=viz-controls>
<button id=dpPrev type=button>&#9664; Prev</button>
<span id=dpLabel class=muted></span>
<button id=dpNext type=button>Next &#9654;</button>
<button id=dpPlay type=button>&#9654; Auto-play</button>
<span class=muted style="margin-left:1em">Zoom:</span>
<button id=dpZoomOut type=button title="zoom out">&minus;</button>
<button id=dpZoomIn type=button title="zoom in">&plus;</button>
<button id=dpFit type=button class=linkbtn title="Auto-scale the timeline so the whole project fits">View entire project</button>
<label>Find <input id=dpFind type=text placeholder="UID or name…" title="Jump to a UniqueID, or mark every corridor task whose row contains this text"></label>
<span id=dpFindStatus class=muted aria-live=polite></span>
<label title="Show the start/finish dates at the ends of the Gantt bars (MS Project bar text)"><input id=dpBarDates type=checkbox> dates on bars</label>
<button id=timescaleBtn type=button title="Modify the timescale: tiers, units (years to hours), labels, count, alignment, fiscal year, tick lines, size and non-working-time shading (like Microsoft Project)">Timescale&hellip;</button>
</div>
<div id=dpChart class=path-view></div></div>
<script type="application/json" id=dpData>{blob}</script>
<script src="/static/driving_path.js"></script>"""

    rows: list[str] = []
    for snap in evo.snapshots:
        when = f" &middot; data date {snap.status_date}" if snap.status_date else ""
        note = f' <span class="dp-note">{_e(snap.change_note)}</span>' if snap.change_note else ""
        delta = ""
        if snap.length_delta:
            sign = "+" if snap.length_delta > 0 else ""
            delta = f" <span class=muted>(corridor length {sign}{snap.length_delta})</span>"
        left = ""
        if snap.left:
            names = ", ".join(
                f"{uid} {_e(_task_name_across(schedules, uid) or '')}".strip() for uid in snap.left
            )
            left = f"<div class=muted>Left the corridor: <span class=ev-left>{names}</span></div>"
        rows.append(
            f"<div class=panel><h3>{_e(snap.label)}{when}</h3>"
            f"<p>{_corridor_chips(snap)}</p>"
            f"<p class=muted>{_e(snap.status)}{note}{delta}</p>"
            f"{left}</div>"
        )

    return form + tiers_html + header + gantt_html + "".join(rows)
