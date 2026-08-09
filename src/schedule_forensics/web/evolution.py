"""The critical-path evolution page family — /evolution and its panels, data and trace options.

Monolith split, phase 3 slice 3 (ADR-0352), extracted VERBATIM from ``web/app.py``: every
function, constant, docstring and comment moves byte-for-byte, only the module boundary changes.

The seam is the AST transitive closure of the family's entry points, seeded by the ``_evolution_*``
prefix AND by ``_trace_options_form`` / ``_optioned_versions``. That widening was measured, not
assumed: the prefix alone left ``_trace_option_names`` and ``_keep_hidden`` being pulled by helpers
that would have stayed in ``app.py``. With the trace-options pair seeded, every external referrer
of the closure is ``create_app`` — a route, which imports downward and stays put.

Layering: ``app`` -> ``evolution`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from urllib.parse import urlencode

from schedule_forensics.engine import compute_driving_slack
from schedule_forensics.engine.cpm import (
    CPMError,
    CPMResult,
    compute_cpm,
    offset_to_datetime,
    span_start_datetime,
)
from schedule_forensics.engine.driving_slack import (
    DEFAULT_SECONDARY_MAX_DAYS,
    DEFAULT_TERTIARY_MAX_DAYS,
    PathTier,
)
from schedule_forensics.engine.path_counterfactual import (
    PathCounterfactual,
    compute_path_counterfactual,
)
from schedule_forensics.engine.path_evolution import PathEvolution, compute_path_evolution
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.components import (
    _EVO_TIER_LABEL,
    _mdY,
    _pair_prov_chip,
    _panel_head,
    _series_prov_chip,
    _shell_tools,
    _stat_cards,
    _status_stack,
    _user_tip,
)
from schedule_forensics.web.state import _iso_date


def _keep_hidden(keep: dict[str, str]) -> str:
    """Hidden inputs that carry a page's OTHER GET state through a form submit (the
    drop-nothing rule, ADR-0320): only non-empty values are emitted, so default state stays
    out of the resulting URL and a stateless page renders byte-identically."""
    return "".join(
        f'<input type=hidden name="{_e(k)}" value="{_e(v)}">' for k, v in keep.items() if v
    )


def _evolution_state_qs(
    *,
    target: str | None,
    tier: str,
    ignore_constraints: bool,
    ignore_leveling: bool,
    keep_blank_target: bool = False,
) -> str:
    """The /evolution GET state as a query string (ADR-0320) — only non-default values are
    emitted, so a stateless render yields "" and every existing default URL stays
    byte-identical. ``keep_blank_target`` emits an EMPTY ``target=`` pair even with no focus
    (the clear-focus link: an explicit "no focus" that must override a session-wide target,
    which an absent parameter would not)."""
    pairs = [
        (k, v)
        for k, v in (
            ("target", target or ""),
            ("tier", tier if tier != "off" else ""),
            ("ignore_constraints", "1" if ignore_constraints else ""),
            ("ignore_leveling", "1" if ignore_leveling else ""),
        )
        if v
    ]
    if keep_blank_target and not (target or ""):
        pairs.insert(0, ("target", ""))
    return urlencode(pairs)


def _trace_option_names(ignore_constraints: bool, ignore_leveling: bool) -> list[str]:
    """ONE source for the active trace-option names: the options banner and the export
    scope headings read this same list (ADR-0320), so the vocabulary can never drift
    between the page and the workbook."""
    return [
        name
        for on, name in (
            (ignore_constraints, "constraints ignored"),
            (ignore_leveling, "leveling delay ignored (pure-logic dates)"),
        )
        if on
    ]


def _evolution_export_scope(
    uid: int | None, tier: str, *, ignore_constraints: bool, ignore_leveling: bool
) -> tuple[list[str], list[str]]:
    """What the /evolution export actually applied (ADR-0320). Returns ``(applied, notes)``:
    ``applied`` are transforms baked into the exported rows — the focused UID's driving-path
    basis (URL or session, same fallback as the page) and the counterfactual trace options;
    ``notes`` are truthful clarifications for page state that does NOT reach these tables
    (the on-screen tier stepper). Headings must never claim a scope the rows don't carry —
    in a testimony context a wrong scope line is worse than none."""
    applied: list[str] = []
    if uid is not None:
        applied.append(f"driving path to UID {uid}")
    applied.extend(_trace_option_names(ignore_constraints, ignore_leveling))
    notes: list[str] = []
    if tier in _EVO_TIER_SELECT:
        notes.append(
            f"the on-screen tier view ({tier}) is not applied - these tables keep the path basis"
        )
    return applied, notes


def _trace_options_form(
    action: str, *, ignore_constraints: bool, ignore_leveling: bool, keep: dict[str, str]
) -> str:
    """The trace-option toggles for the server-rendered path pages (operator 2026-07-08):
    Ignore constraints / Ignore leveling delay re-solve every version's network un-pinned —
    a genuine counterfactual re-solve via ``_optioned_versions``, unlike the Path-Analysis
    options of the same name, which keep SSI's stored-date parity (ADR-0251).
    Direction and dependency range live on Path Analysis, whose trace is target-relative;
    this corridor/evolution pair is directional by construction (A→B / to the finish)."""
    hidden = _keep_hidden(keep)
    ic = " checked" if ignore_constraints else ""
    il = " checked" if ignore_leveling else ""
    return f"""<form method=get action="{action}" class="viz-controls trace-options">{hidden}
<label><input type=checkbox name=ignore_constraints value=1{ic}
title="Counterfactual re-solve: every version recomputed with all date constraints removed (pure logic). Diverges from the stored schedule — and from SSI's same-named option, which keeps reporting on stored dates (ADR-0251)"> Ignore constraints</label>
<label><input type=checkbox name=ignore_leveling value=1{il}
title="Counterfactual re-solve: incomplete tasks' stored dates are cleared and the CPM recomputed (a 0-day leveling delay). Diverges from the stored schedule — and from SSI's same-named option, which keeps reporting on stored dates (ADR-0251)"> Ignore leveling delay</label>
<button type=submit>Apply</button></form>"""


def _optioned_versions(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    *,
    ignore_constraints: bool,
    ignore_leveling: bool,
) -> tuple[list[Schedule], list[CPMResult], str]:
    """Apply the trace options to every loaded version (operator 2026-07-08).

    ``ignore_constraints`` re-solves each version on a constraint-stripped copy;
    ``ignore_leveling`` additionally clears incomplete tasks' stored dates so the
    corridor/evolution engines (which honor stored dates) run on the pure-logic CPM
    ("0-day leveling delay"). This is a genuine re-solve — a **counterfactual** view,
    stronger than SSI's same-named Directional Path options, which keep reporting against
    the stored (leveled/progressed) dates: SSI's own options-ON export is reproduced by
    the stored-date trace, NOT by this transform (ADR-0251) — so paths here diverge from
    SSI/MS Project output by design, and the banner says so. Returns the
    possibly-substituted lists plus that banner — defaults return the originals
    untouched."""
    if not ignore_constraints and not ignore_leveling:
        return schedules, cpms, ""
    from schedule_forensics.engine.driving_slack import strip_constraints

    out_s: list[Schedule] = []
    out_c: list[CPMResult] = []
    for sch in schedules:
        s2 = strip_constraints(sch) if ignore_constraints else sch
        if ignore_leveling:
            tasks = tuple(
                t.model_copy(update={"start": None, "finish": None}) if not t.is_complete else t
                for t in s2.tasks
            )
            s2 = s2.model_copy(update={"tasks": tasks})
        out_s.append(s2)
        out_c.append(compute_cpm(s2))
    opts = _trace_option_names(ignore_constraints, ignore_leveling)
    banner = (
        '<div class="notice">Trace options active: ' + ", ".join(opts) + " — every date and "
        "path on this page (including the animated stepper and the Excel exports) comes from "
        "the re-solved pure-logic network, not the stored schedule (ADR-0265: one basis per "
        "page). This is a counterfactual view: SSI / MS Project report against the stored "
        "dates even with their same-named options on, so these paths will not match those "
        "tools' output (ADR-0251). Stored-schedule date/float drill columns are hidden while "
        "the options are active.</div>"
    )
    return out_s, out_c, banner


def _evolution_body(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    target: int | None = None,
    tier: str = "off",
    *,
    cf_a: int = -1,
    cf_b: int = -1,
    ignore_constraints: bool = False,
    ignore_leveling: bool = False,
) -> str:
    """The Critical-Path Evolution view (M18 item 7): a Bow-Wave-style stepper over the
    versions, showing the critical path and how it enters/leaves between versions. ``target``
    focuses a UniqueID (highlighted across every frame); zoom/pan controls scope the axis. ``tier``
    scopes the stepper to a driving-slack tier (secondary/tertiary/all) instead of the float
    critical path — the activities driving the focused UID (or the project finish)."""
    # ONE source for the tier vocabulary: the <select> options AND the panel's takeaway read the
    # same list, so a label can never drift between the control and the sentence describing it.
    tier_choices = [
        ("off", "Critical path"),
        ("secondary", f"Secondary tier (≤{DEFAULT_SECONDARY_MAX_DAYS}d slack)"),
        ("tertiary", f"Tertiary tier (≤{DEFAULT_TERTIARY_MAX_DAYS}d slack)"),
        ("all", "All tiers (colour-coded)"),
    ]
    tier_opts = "".join(
        f'<option value="{v}"{" selected" if tier == v else ""}>{lbl}</option>'
        for v, lbl in tier_choices
    )
    # ADR-0320 (drop-nothing rule): submitting Focus / the tier select used to DROP the
    # active trace options, silently flipping the page back to the stored basis; the clear-
    # focus link did the same. Both now carry the rest of the page's state (defaults emit
    # nothing, so a stateless page renders byte-identically).
    keep_opts = _keep_hidden(
        {
            "ignore_constraints": "1" if ignore_constraints else "",
            "ignore_leveling": "1" if ignore_leveling else "",
        }
    )
    clear_qs = _evolution_state_qs(
        target=None,
        tier=tier,
        ignore_constraints=ignore_constraints,
        ignore_leveling=ignore_leveling,
        keep_blank_target=True,
    )
    focus_form = f"""
<div class=panel><form method=get action=/evolution class=viz-controls>{keep_opts}
Focus a specific activity across every version &mdash; UniqueID:
<input name=target type=number min=1 value="{target if target is not None else ""}"
placeholder="UID"> <button type=submit>Focus</button>
{f'<a class=btn-link href="/evolution?{clear_qs}">clear focus</a>' if target is not None else ""}
<label style="margin-left:1em">Path tier:
<select name=tier data-no-i18n data-sf-autosubmit>{tier_opts}</select></label>
<span class=muted>critical / secondary / tertiary by driving slack to the focused UID (or the
project finish).</span>
</form></div>"""
    # ── Panel contract (Mission Ops rank 11). ONE evolution pass feeds both the stepper's take
    # and the "Completed on the path" panel below (it used to compute its own) — same call, same
    # arguments as the page header's `_how_stable_header`, so the take can never disagree with
    # the churn KPI strip above it. Engine untouched: this is the figure the page already prints.
    ev = compute_path_evolution(schedules, cpms, target_uid=target)
    snaps = ev.snapshots
    n_ver = len(snaps)
    updates = max(n_ver - 1, 1)
    entered = sum(len(s.entered) for s in snaps[1:])
    left = sum(len(s.left) for s in snaps[1:])
    moves = [s.finish_delta_days for s in snaps[1:] if s.finish_delta_days is not None]
    net = sum(moves) if moves else None
    if net is None:
        fin = "and no version-over-version finish move is recorded"
    elif net > 0:
        fin = f"and the finish slipped {net} calendar day{'s' if net != 1 else ''}"
    elif net < 0:
        fin = f"and the finish pulled in {abs(net)} calendar day{'s' if net != -1 else ''}"
    else:
        fin = "while the finish held"
    if tier == "off":
        evo_take = (
            f"{n_ver} frames step the critical path oldest-first on a date axis held fixed, so a "
            f"bar reaching further right is the finish moving, not the axis rescaling: "
            f"{entered} activit{'y' if entered == 1 else 'ies'} entered the path and {left} left "
            f"over {updates} update{'s' if updates != 1 else ''}, {fin}."
        )
    else:
        tier_label = dict(tier_choices).get(tier, tier)
        evo_take = (
            f"{n_ver} frames step the <b>{_e(tier_label)}</b> basis &mdash; driving slack to the "
            "focused UID (or the project finish) &mdash; not the float critical path the churn "
            "figures above are counted on."
        )
    return (
        focus_form
        + f"""
<div class=panel>{_panel_head("Critical-Path Evolution", tools=_shell_tools(), prov=_series_prov_chip(schedules))}
<p class=sf-take data-no-i18n>{evo_take}</p>
{_user_tip("The date axis is held fixed across versions, so the critical path visibly extends as the finish slips. Use <b>View entire project</b> to fit the whole timeline, and set a <b>target UID</b> to highlight one activity across every frame.")}
<p class=muted><b>Path basis (ADR-0150):</b> with a <b>focused UID</b> the path shown is the
<b>0-driving-slack chain to that UID</b> (the same set as the /path driving-slack view); with no
focus it is the <b>progress-aware critical set</b> &mdash; the source tool&rsquo;s stored Critical
flag (what MS Project shows), falling back to recomputed CPM float only when the file carries no
flag. Completed work leaves the path and is recorded below under
<b>Completed on the path</b>.</p>
<p class=muted>Step through the versions (oldest first by data date) to watch the critical
path change, drawn as a <b>Gantt</b> on a date axis held fixed across every version (so the
path visibly extends as the finish slips). Bars are colored
<b class=ev-entered>green</b> for activities that <b>entered</b> the path since the prior
version, <b class=ev-stayed>grey</b> for those that <b>stayed</b>, with a &#9650; marking a
duration change; activities that <b class=ev-left>left</b> the path appear below as dashed
ghost bars at their prior position. Every entered/left activity carries a <b>reason chip</b>
explaining <b>why</b> it moved &mdash; a new task, a duration change, a logic change, a
constraint, a completion, or a slip elsewhere consuming its float (hover the chip for the
detail). The callout reports the finish movement and the schedule-optics signals, so a path
shedding work while the finish holds steady (a slip being absorbed rather than recovered) is
visible.</p>
<div class=viz-controls>
<button id=prevEvo type=button>&#9664; Prev</button>
<span id=evoLabel class=muted></span>
<button id=nextEvo type=button>Next &#9654;</button>
<button id=evoPlay type=button>&#9654; Auto-play</button>
<label class=muted style="margin-left:1em"><input type=checkbox id=evoHideDone> hide completed</label>
<label class=muted title="Show the start/finish dates at the ends of the Gantt bars (MS Project bar text)"><input type=checkbox id=evoBarDates> dates on bars</label>
</div>
<div class=viz-controls>
<span class=muted>Zoom the date axis:</span>
<button id=evoZoomOut type=button title="zoom out">&minus;</button>
<button id=evoZoomIn type=button title="zoom in">&plus;</button>
<button id=evoPanL type=button title="pan earlier">&#9664;</button>
<button id=evoPanR type=button title="pan later">&#9654;</button>
<button id=evoZoomReset type=button title="Auto-scale to show the whole project">View entire project</button>
<button id=timescaleBtn type=button title="Modify the timescale: tiers, units (years to hours), labels, count, alignment, fiscal year, tick lines, size and non-working-time shading (like Microsoft Project)">Timescale&hellip;</button>
</div>
<div class=viz-controls>
<label>Filter the path:
<select id=evoFilterMode>
<option value=none selected>none &mdash; whole critical path</option>
<option value=driving>driving path to the focused UID</option>
<option value=version>track one version's path</option>
<option value=movement>entered / left / stayed</option>
<option value=search>name / UID search</option>
</select></label>
<select id=evoFilterVersion style="display:none"></select>
<span id=evoFilterMovement style="display:none">
<label><input type=checkbox class=evoMove value=entered checked> entered</label>
<label><input type=checkbox class=evoMove value=stayed checked> stayed</label>
<label><input type=checkbox class=evoMove value=left checked> left</label>
</span>
<input id=evoFilterText type=search placeholder="name or UID" style="display:none">
<span id=evoFilterNote class=muted></span>
</div>
<p class=muted style="margin:.2em 0">Each row carries its grid columns &mdash; <b>%&nbsp;complete</b>,
<b>duration</b> (working days), <b>start</b> and <b>finish</b> &mdash; beside the bar.
Use <b>Focus</b> above to highlight one activity across every version.</p>
<div id=evoChart data-target="{target if target is not None else ""}"
data-tier="{tier}" data-ignore-constraints="{int(ignore_constraints)}"
data-ignore-leveling="{int(ignore_leveling)}"></div></div>
<script src="/static/path_evolution.js"></script>"""
        + _completed_on_path_panel(schedules, cpms, target, ev=ev)
        + _counterfactual_panel(
            schedules,
            cpms,
            target,
            baseline_idx=cf_a,
            comparison_idx=cf_b,
            tier=tier,
            ignore_constraints=ignore_constraints,
            ignore_leveling=ignore_leveling,
        )
        # ⛶ wiring for the two panels above that carry `data-sf-big`. Appended to the ONE string
        # this builder returns, so the include lands exactly once no matter which branches fired.
        + '\n<script src="/static/panelkit.js"></script>'
    )


def _completed_on_path_panel(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    target: int | None,
    *,
    ev: PathEvolution | None = None,
) -> str:
    """Version-to-version record of path activities that COMPLETED — the operator's "what got
    done on the path month to month". Server-rendered from the page's evolution snapshots
    (ADR-0150) — the OPTIONED versions when the counterfactual trace options are active, the
    SAME basis the client-fetched stepper now reads (`/api/evolution` forwards the options,
    ADR-0265): for each version pair, the prior version's path activities that are complete
    in the newer version, with their actual finishes.

    ``ev`` lets the caller hand in the evolution it already computed (rank 11: the page builder
    computes one pass and shares it) — keyword-with-default so any direct caller still works."""
    if ev is None:
        ev = compute_path_evolution(schedules, cpms, target_uid=target)
    basis = f"driving path to UID {target}" if target is not None else "effective critical path"
    sections: list[str] = []
    for i in range(1, len(ev.snapshots)):
        snap = ev.snapshots[i]
        prior_label = _e(ev.snapshots[i - 1].label)
        label = _e(snap.label)
        period = f"{prior_label} &rarr; {label}"
        if not snap.completed_on_path:
            sections.append(
                f"<h3>{period}</h3><p class=muted>No path activities completed this period.</p>"
            )
            continue
        by_id = schedules[i].tasks_by_id
        rows = "".join(
            f"<tr><td>{uid}</td><td>{_e(t.name if t else f'UID {uid}')}</td>"
            f"<td>{_mdY(t.actual_finish) if t is not None else '—'}</td>"
            f"<td>{round(t.percent_complete) if t is not None else 0}%</td></tr>"
            for uid in snap.completed_on_path
            for t in (by_id.get(uid),)
        )
        sections.append(
            f"<h3>{period} &mdash; {len(snap.completed_on_path)} completed on the path</h3>"
            "<table><tr><th scope=col>UID</th><th scope=col>Activity</th>"
            f"<th scope=col>Actual finish</th><th scope=col>%</th></tr>{rows}</table>"
        )
    src_names = ", ".join(_e(s.source_file or s.name) for s in schedules)
    # The take counts the SAME `snap.completed_on_path` tuples the sections above are built from —
    # one pass, so the headline can never disagree with the tables underneath it.
    periods = max(len(ev.snapshots) - 1, 0)
    done = sum(len(s.completed_on_path) for s in ev.snapshots[1:])
    active = sum(1 for s in ev.snapshots[1:] if s.completed_on_path)
    if done == 0:
        take = (
            f"No path activity completed in any of the {periods} update "
            f"period{'s' if periods != 1 else ''} &mdash; nothing burned off the {basis} between "
            "versions."
        )
    else:
        idle = periods - active
        tail = f"; the other {idle} recorded none" if idle else ""
        take = (
            f"{done} path activit{'y' if done == 1 else 'ies'} completed across {periods} update "
            f"period{'s' if periods != 1 else ''}, in {active} of them{tail}."
        )
    return (
        "<div class=panel>"
        + _panel_head(
            "Completed on the path &mdash; version to version",
            tools=_shell_tools(),
            prov=_series_prov_chip(schedules),
        )
        + f"<p class=sf-take data-no-i18n>{take}</p>"
        f"<p class=muted>Basis: <b>{basis}</b>. Sources ({len(schedules)} files): {src_names}. "
        "Activities that were ON the path in one version and show complete in the next &mdash; "
        "the work that actually burned down the driving chain each period.</p>"
        + "".join(sections)
        + "</div>"
    )


def _counterfactual_panel(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    target: int | None,
    *,
    baseline_idx: int = -1,
    comparison_idx: int = -1,
    tier: str = "off",
    ignore_constraints: bool = False,
    ignore_leveling: bool = False,
) -> str:
    """The 'what-if' panel for a CHOSEN version pair: revert the duration/logic/constraint changes
    that took non-completed activities off the critical path, and report what the finish (and the
    target UID) would have been — isolating slip removed by changes vs progress.

    Operator 2026-07-08: the panel previously always used the LATEST two versions, so on a long
    history it only showed the tiny most-recent update (looking like "no change") and hid the
    cumulative manipulation. It now runs on ANY two files the operator picks (Baseline A vs
    Comparison B), defaulting to the two most recent, so first-vs-last reveals the real change.
    ADR-0320: ``tier`` / ``ignore_*`` ride the picker (with ``target``) as hidden inputs so
    "Run what-if" keeps the rest of the page's state; defaults emit nothing."""
    if len(schedules) < 2:
        return ""
    n = len(schedules)
    labels = [s.source_file or s.name for s in schedules]
    # resolve the chosen pair safely (same rule as Integrity): default the two most recent, order
    # prior -> current chronologically, never collapse to one file or a negative index.
    cur = comparison_idx if 0 <= comparison_idx < n else n - 1
    base = baseline_idx if 0 <= baseline_idx < n else cur - 1
    if base == cur or not (0 <= base < n):
        base = cur - 1 if cur > 0 else cur + 1
    prior_idx, cur_idx = (base, cur) if base < cur else (cur, base)

    picker = ""
    if n > 2:

        def _opts(selected: int) -> str:
            return "".join(
                f'<option value="{i}"{" selected" if i == selected else ""}>{_e(lb)}</option>'
                for i, lb in enumerate(labels)
            )

        # ADR-0320 (drop-nothing rule): "Run what-if" used to reload /evolution with ONLY
        # cf_a/cf_b, dropping the focus, tier and trace options the operator had set.
        keep_state = _keep_hidden(
            {
                "target": str(target) if target is not None else "",
                "tier": tier if tier != "off" else "",
                "ignore_constraints": "1" if ignore_constraints else "",
                "ignore_leveling": "1" if ignore_leveling else "",
            }
        )
        picker = f"""
<form method=get action=/evolution class=viz-controls style="margin:.4em 0">{keep_state}
<span class=muted>Compare any two of the {n} loaded versions:</span>
<label>Baseline (A) <select name=cf_a>{_opts(prior_idx)}</select></label>
<label>Comparison (B) <select name=cf_b>{_opts(cur_idx)}</select></label>
<button type=submit>Run what-if</button></form>"""

    pc = compute_path_counterfactual(
        schedules[prior_idx], schedules[cur_idx], cpms[prior_idx], cpms[cur_idx], target_uid=target
    )
    # enrich each reverted activity with its current-version fields (duration / % complete / start /
    # finish / WBS / custom) so the client table can add columns and FILTER by any of them.
    current = schedules[cur_idx]
    by_id = current.tasks_by_id
    per_day = current.calendar.working_minutes_per_day or 480
    enriched: list[dict[str, object]] = []
    if pc is not None:
        for r in pc.reverted:
            t = by_id.get(r.uid)
            row: dict[str, object] = {
                "unique_id": r.uid,
                "name": r.name,
                "why_left": r.reason,
                "change_reverted": "; ".join(r.changes),
            }
            if t is not None:
                row.update(
                    {
                        "duration_days": round(
                            t.duration_minutes / (1440 if t.duration_is_elapsed else per_day), 1
                        ),
                        "percent_complete": t.percent_complete,
                        "start": _iso_date(t.start),
                        "finish": _iso_date(t.finish),
                        "wbs": t.wbs or "",
                        "resource_names": ", ".join(t.resource_names),
                        "custom": dict(t.custom_field_map),
                    }
                )
            enriched.append(row)
    custom_labels = sorted(current.custom_field_labels)
    added_rows = _whatif_added_rows(
        schedules[prior_idx], current, cpms[prior_idx], cpms[cur_idx], target
    )
    return _render_counterfactual(
        pc,
        picker=picker,
        pair=(labels[prior_idx], labels[cur_idx]),
        enriched_rows=enriched,
        custom_labels=custom_labels,
        added_rows=added_rows,
        # The two what-if panels are a version PAIR, so they take the pair chip the compare views
        # already speak (never a third provenance vocabulary) — the same pair the picker selected.
        prov=_pair_prov_chip(schedules[prior_idx], schedules[cur_idx], prior_idx + 1, cur_idx + 1),
    )


def _whatif_added_rows(
    prior: Schedule,
    current: Schedule,
    prior_cpm: CPMResult,
    current_cpm: CPMResult,
    target: int | None,
) -> list[dict[str, object]]:
    """Activities ADDED to the critical path between the chosen pair (operator 2026-07-09),
    with the engine's per-activity reason attribution (path_evolution's classifier — new task,
    own duration/logic/constraint change, or float consumed by a NAMED slip elsewhere) plus the
    current-version fields so the client table can add columns / filter / export."""
    try:
        ev = compute_path_evolution([prior, current], [prior_cpm, current_cpm], target_uid=target)
    except (CPMError, ValueError, KeyError) as exc:
        logging.getLogger("schedule_forensics").warning("what-if added-path failed: %s", exc)
        return []
    snap = ev.snapshots[-1]
    by_id = current.tasks_by_id
    per_day = current.calendar.working_minutes_per_day or 480
    rows: list[dict[str, object]] = []
    for ch in snap.entered_changes:
        row: dict[str, object] = {
            "unique_id": ch.uid,
            "name": ch.name,
            "why_entered": ch.reason,
            "detail": ch.detail,
        }
        t = by_id.get(ch.uid)
        if t is not None:
            row.update(
                {
                    "duration_days": round(
                        t.duration_minutes / (1440 if t.duration_is_elapsed else per_day), 1
                    ),
                    "percent_complete": t.percent_complete,
                    "start": _iso_date(t.start),
                    "finish": _iso_date(t.finish),
                    "wbs": t.wbs or "",
                    "resource_names": ", ".join(t.resource_names),
                    "custom": dict(t.custom_field_map),
                }
            )
        rows.append(row)
    return rows


def _delta_words(days: int) -> str:
    """The counterfactual finish move in words, sign preserved. ONE wording shared by the panel
    body's emphasised line and its takeaway line, so the two can never quote different digits."""
    if days > 0:
        return f"+{days} day(s) later"
    if days < 0:
        return f"{days} day(s) earlier"
    return "no change"


def _render_counterfactual(
    pc: PathCounterfactual | None,
    *,
    picker: str = "",
    pair: tuple[str, str] | None = None,
    enriched_rows: list[dict[str, object]] | None = None,
    custom_labels: list[str] | None = None,
    added_rows: list[dict[str, object]] | None = None,
    prov: str = "",
) -> str:
    """Render the counterfactual panel from a computed result (split out for direct testing).

    ``prov`` is the panel-contract provenance chip for the chosen version pair (rank 11) —
    keyword-with-default because this renderer is called POSITIONALLY by the coverage tests."""
    pair_txt = (
        f"between <b data-no-i18n>{_e(pair[0])}</b> and <b data-no-i18n>{_e(pair[1])}</b>"
        if pair
        else "between the two chosen versions"
    )
    # Work ADDED to the critical path (operator 2026-07-09) — the mirror of the reverted list:
    # every activity that ENTERED the path between the pair, with the engine's reason attribution.
    added_html = ""
    if added_rows is not None:
        a_attr = _e(pair[0]) if pair else ""
        b_attr = _e(pair[1]) if pair else ""
        added_blob = json.dumps({"rows": added_rows, "customLabels": custom_labels or []}).replace(
            "<", "\\u003c"
        )
        added_body = (
            f'<div id=whatifAddedTable data-a="{a_attr}" data-b="{b_attr}"></div>'
            f'<script type="application/json" id=whatifAddedData>{added_blob}</script>'
            if added_rows
            else f"<p class=muted>No activity entered the critical path {pair_txt}.</p>"
        )
        # The take splits the SAME `added_rows` the table below renders, on the engine's own
        # `why_entered` attribution — "slack_consumed" is the classifier's code for "nothing about
        # this activity changed; a slip elsewhere ate its float" (engine/path_evolution.py).
        n_add = len(added_rows)
        unchanged = sum(1 for r in added_rows if r.get("why_entered") == "slack_consumed")
        if n_add == 0:
            added_take = "No activity entered the critical path between the chosen pair."
        else:
            added_take = (
                f"{n_add} activit{'y' if n_add == 1 else 'ies'} entered the critical path between "
                f"the chosen pair &mdash; {n_add - unchanged} through a change to the activity "
                f"itself and {unchanged} because a slip elsewhere consumed its float."
            )
        added_html = f"""
<div class=panel>{_panel_head("What-if: work added to the critical path", prov=prov)}
<p class=sf-take data-no-i18n>{added_take}</p>
<p class=muted>The mirror of the list above: activities that <b>entered</b> the critical (driving)
path {pair_txt}. Each carries the engine's reason — a <b>new</b> activity, its <b>own</b> duration
/ logic / constraint change, or <b>float consumed</b> by a named slip elsewhere. Work joining the
path is where the schedule's risk is moving: a path that churns member activities version over
version is unstable even when the finish date holds.</p>
{added_body}</div>"""
    # The removed-work take reads the SAME `pc` fields the body prints verbatim below (the
    # reverted count, the two finishes and the signed delta) — nothing is recomputed, and an
    # uncomputable network reports the missing finish as an em dash, never a fabricated date.
    if pc is None:
        removed_take = (
            "Nothing to revert between the chosen pair &mdash; no non-completed activity left "
            "the critical path, so no schedule time here was removed by change rather than by "
            "progress."
        )
    elif not pc.reverted:
        n_gf = len(pc.gained_float)
        removed_take = (
            f"Nothing to revert between the chosen pair &mdash; {n_gf} "
            f"activit{'y' if n_gf == 1 else 'ies'} left the path by gaining float, not by any "
            "change to itself."
            if n_gf
            else "Nothing to revert between the chosen pair."
        )
    elif pc.uncomputable:
        removed_take = (
            f"{len(pc.reverted)} change(s) on non-completed activities took work off the path; "
            "reverting them produces an unsolvable network (a logic cycle), so the counterfactual "
            "finish is &mdash;."
        )
    else:
        removed_take = (
            f"{len(pc.reverted)} change(s) on non-completed activities took work off the path; "
            f"reverting them moves the computed finish from {_e(pc.actual_finish)} to "
            f"{_e(pc.counterfactual_finish)} ({_delta_words(pc.finish_delta_days)})."
        )
    intro = f"""
<div class=panel>{_panel_head("What-if: work removed from the critical path", prov=prov)}
<p class=sf-take data-no-i18n>{removed_take}</p>
<p class=muted>This runs on the <b>one pair you pick</b> {pair_txt} — not lumped across the whole
history. Some activities leave the critical (driving) path between these two versions. A
<b>completed</b> activity leaving is real progress (excluded here). An unchanged activity leaving
<b>gained float</b> &mdash; a slip elsewhere made another chain longer, so this one is no longer on
the longest path (nothing about it changed). But an activity that leaves because <b>its own
remaining duration was cut, a logic link was removed, or a constraint was dropped</b> can make a
slipping finish look recovered. Below, those specific changes (on non-completed activities) are
reverted to their prior values and the schedule re-run &mdash; the gap is schedule time the
<b>changes</b>, not progress, removed from the path.</p>{picker}"""
    if pc is None:
        return (
            intro + f"<p class=muted>No non-completed activity left the critical path {pair_txt} "
            "&mdash; nothing to revert. Pick a wider pair (e.g. the first vs the latest version) "
            "to see cumulative change.</p></div>"
            + added_html
            + '<script src="/static/whatif.js"></script>'
        )

    def _delta(days: int) -> str:
        """The emphasised delta the body prints — the SAME words :func:`_delta_words` gives the
        takeaway line, wrapped in the pass/fail emphasis (one wording, not two)."""
        if days > 0:
            return f"<b class=fail>{_delta_words(days)}</b>"
        if days < 0:
            return f"<b class=pass>{_delta_words(days)}</b>"
        return f"<b>{_delta_words(days)}</b>"

    # interactive reverted-changes table: filter by any field + add standard/custom columns + Excel
    # export (operator 2026-07-08). Rows carry each activity's current fields (embedded server-side).
    # Fall back to the base columns from pc.reverted when no enriched rows were supplied (direct
    # callers / tests) so the table always lists the reverted activities.
    rows_data = (
        enriched_rows
        if enriched_rows is not None
        else [
            {
                "unique_id": r.uid,
                "name": r.name,
                "why_left": r.reason,
                "change_reverted": "; ".join(r.changes),
            }
            for r in pc.reverted
        ]
    )
    whatif_blob = json.dumps({"rows": rows_data, "customLabels": custom_labels or []}).replace(
        "<", "\\u003c"
    )
    a_attr = _e(pair[0]) if pair else ""
    b_attr = _e(pair[1]) if pair else ""
    table_html = (
        f'<div id=whatifTable data-a="{a_attr}" data-b="{b_attr}"></div>'
        f'<script type="application/json" id=whatifData>{whatif_blob}</script>'
    )
    body = [intro]
    if pc.reverted:
        finish_line = (
            f"Computed finish is <b>{_e(pc.actual_finish)}</b>; had these "
            f"{len(pc.reverted)} change(s) not been made it would be "
            f"<b>{_e(pc.counterfactual_finish)}</b> ({_delta(pc.finish_delta_days)})."
        )
        if pc.uncomputable:
            finish_line = (
                "Reverting these changes produced an unsolvable network (a logic cycle), so the "
                "counterfactual finish cannot be computed; the changed activities are named below."
            )
        body.append(f"<p>{finish_line}</p>")
        if pc.target_uid is not None and pc.target_delta_days is not None:
            body.append(
                f"<p>Target activity <b>UID {pc.target_uid}: {_e(pc.target_name or '')}</b> "
                f"finishes <b>{_e(pc.target_actual_finish or '')}</b> now; without the changes "
                f"it would finish <b>{_e(pc.target_counterfactual_finish or '')}</b> "
                f"({_delta(pc.target_delta_days)}).</p>"
            )
        elif pc.target_uid is not None:
            body.append(
                f"<p class=muted>Target UID {pc.target_uid} is not in both the current and "
                "counterfactual networks, so its individual impact is not shown.</p>"
            )
        body.append(table_html)
    if pc.gained_float:
        names = "; ".join(f"{g.name} (UID {g.uid})" for g in pc.gained_float)
        body.append(
            f"<p class=muted><b>Gained float (no change to revert):</b> {_e(names)} left the path "
            "because a slip elsewhere lengthened another chain, freeing this one's float &mdash; "
            "not because the activity itself was altered.</p>"
        )
    body.append("</div>")
    body.append(added_html)
    body.append('<script src="/static/whatif.js"></script>')
    return "".join(body)


def _evolution_data(
    schedules: list[Schedule], cpms: list[CPMResult], target: int | None = None
) -> dict[str, object]:
    """JSON for the critical-path evolution Gantt stepper: per-version snapshots with each
    critical activity's bar geometry (start/finish), the entered/left attribution (the reason
    WHY each entered or left the path), and a date axis LOCKED across every version so bars
    stay comparable frame to frame. ``target`` (if set) is echoed so the view can highlight
    that UniqueID's row in every frame."""
    # With a focused UID the path IS the 0-driving-slack chain to it (the /path basis);
    # untargeted, the progress-aware effective critical set (stored Critical flag).
    evolution = compute_path_evolution(schedules, cpms, target_uid=target)
    by_id = [s.tasks_by_id for s in schedules]
    axis_dates: list[dt.date] = []

    def bar(idx: int, uid: int) -> tuple[str | None, str | None]:
        timing = cpms[idx].timings.get(uid)
        if timing is None:
            return None, None
        sch = schedules[idx]
        start = span_start_datetime(
            sch.project_start, timing.early_start, timing.early_finish, sch.calendar
        ).date()
        finish = offset_to_datetime(sch.project_start, timing.early_finish, sch.calendar).date()
        axis_dates.extend((start, finish))
        return start.isoformat(), finish.isoformat()

    def is_complete_in(idx: int, uid: int) -> bool:
        """Robust complete flag (ADR-0051: ≥100% OR an actual finish) for ``uid`` in version
        ``idx`` — False when the activity is absent from that version."""
        task = by_id[idx][uid] if 0 <= idx < len(by_id) and uid in by_id[idx] else None
        return task is not None and (task.is_complete or task.actual_finish is not None)

    def stats(idx: int, uid: int) -> dict[str, object]:
        """Per-activity grid columns for the row: %complete, duration (working days), and the
        robust complete flag. Empty when the activity is absent from version ``idx`` (e.g. a
        removed activity shown at its prior position)."""
        task = by_id[idx][uid] if 0 <= idx < len(by_id) and uid in by_id[idx] else None
        if task is None:
            return {"percent_complete": None, "duration": None, "complete": False}
        per_day = schedules[idx].calendar.working_minutes_per_day or 1
        return {
            "percent_complete": round(task.percent_complete),
            "duration": f"{task.duration_minutes / per_day:g}wd",
            "complete": is_complete_in(idx, uid),
        }

    def path_to_target(idx: int) -> list[int]:
        """When a UID is focused, the activities that DRIVE it in version ``idx`` — the target
        plus its transitive predecessors — so the "driving path to focus" filter can scope the
        Gantt to just the chain feeding the focused activity. Empty when no target is set or it
        is absent from this version."""
        if target is None or not (0 <= idx < len(schedules)) or target not in by_id[idx]:
            return []
        preds_of: dict[int, list[int]] = {}
        for r in schedules[idx].relationships:
            preds_of.setdefault(r.successor_id, []).append(r.predecessor_id)
        seen, stack = {target}, [target]
        while stack:
            for p in preds_of.get(stack.pop(), ()):
                if p not in seen:
                    seen.add(p)
                    stack.append(p)
        return sorted(seen)

    snapshots: list[dict[str, object]] = []
    for i, s in enumerate(evolution.snapshots):
        names = {str(uid): by_id[i][uid].name for uid in s.critical if uid in by_id[i]}
        if i > 0:
            for uid in s.left:
                if uid in by_id[i - 1]:
                    names[str(uid)] = by_id[i - 1][uid].name
        entered_reason = {c.uid: c for c in s.entered_changes}
        dur_changed = set(s.duration_changed)
        critical_rows: list[dict[str, object]] = []
        for uid in s.critical:
            start, finish = bar(i, uid)
            change = entered_reason.get(uid)
            critical_rows.append(
                {
                    "uid": uid,
                    "name": names.get(str(uid), f"UID {uid}"),
                    "start": start,
                    "finish": finish,
                    "entered": uid in entered_reason,
                    "duration_changed": uid in dur_changed,
                    "reason": change.reason if change is not None else None,
                    "detail": change.detail if change is not None else None,
                    **stats(i, uid),
                }
            )
        critical_rows.sort(key=lambda r: (r["start"] is None, str(r["start"])))
        left_rows: list[dict[str, object]] = []
        for c in s.left_changes:
            start, finish = bar(i - 1, c.uid) if i > 0 else (None, None)
            # left activities are drawn at their PRIOR-version position, so %complete/duration
            # read from that version (i - 1); the complete flag is the CURRENT status, so an
            # activity that left *because it completed* hides under the hide-completed toggle.
            grid = stats(i - 1, c.uid)
            grid["complete"] = is_complete_in(i, c.uid)
            left_rows.append(
                {
                    "uid": c.uid,
                    "name": c.name,
                    "start": start,
                    "finish": finish,
                    "reason": c.reason,
                    "detail": c.detail,
                    **grid,
                }
            )
        snapshots.append(
            {
                "label": s.label,
                "status_date": s.status_date,
                "project_finish": s.project_finish,
                "finish_delta_days": s.finish_delta_days,
                "critical": list(s.critical),
                "entered": list(s.entered),
                "left": list(s.left),
                "duration_changed": list(s.duration_changed),
                "shortened_on_path": list(s.shortened_on_path),
                "removed_logic_count": s.removed_logic_count,
                "names": names,
                "critical_rows": critical_rows,
                "left_rows": left_rows,
                "path_to_target": path_to_target(i),
            }
        )
    axis = {
        "min": min(axis_dates).isoformat() if axis_dates else None,
        "max": max(axis_dates).isoformat() if axis_dates else None,
    }
    return {"axis": axis, "snapshots": snapshots, "target": target}


_EVO_TIER_SELECT: dict[str, set[PathTier]] = {
    "critical": {PathTier.DRIVING},
    "secondary": {PathTier.SECONDARY},
    "tertiary": {PathTier.TERTIARY},
    "all": {PathTier.DRIVING, PathTier.SECONDARY, PathTier.TERTIARY},
}


def _project_finish_uid(sch: Schedule, cpm: CPMResult) -> int | None:
    """The non-summary activity that finishes last (drives the project finish) — the default focus
    for the tiered driving-path view when no target UID is pinned."""
    best_uid: int | None = None
    best: int | None = None
    for t in sch.tasks:
        if t.is_summary:
            continue
        tm = cpm.timings.get(t.unique_id)
        if tm is None:
            continue
        if best is None or tm.early_finish > best:
            best, best_uid = tm.early_finish, t.unique_id
    return best_uid


def _evolution_tier_data(
    schedules: list[Schedule], cpms: list[CPMResult], target: int | None, tier: str
) -> dict[str, object]:
    """Critical-Path Evolution scoped to a DRIVING-SLACK tier (ADR-0011) instead of the float
    critical path: per version, classify the activities driving the focus (the pinned ``target``,
    else that version's project-finish activity) into driving (0 days) / secondary (<=10 days) /
    tertiary (<=20 days), and show ONLY the chosen tier (``all`` shows all three, the client colours
    them by tier). Same payload shape as :func:`_evolution_data` so the Gantt stepper renders it
    unchanged; ``entered`` / ``left`` are by set difference of the tier membership across versions,
    and the version framing (label / data date / project finish) is reused from the evolution."""
    selected = _EVO_TIER_SELECT.get(tier, _EVO_TIER_SELECT["critical"])
    evolution = compute_path_evolution(schedules, cpms)
    by_id = [s.tasks_by_id for s in schedules]
    axis_dates: list[dt.date] = []

    def bar(idx: int, uid: int) -> tuple[str | None, str | None]:
        timing = cpms[idx].timings.get(uid)
        if timing is None:
            return None, None
        sch = schedules[idx]
        start = span_start_datetime(
            sch.project_start, timing.early_start, timing.early_finish, sch.calendar
        ).date()
        finish = offset_to_datetime(sch.project_start, timing.early_finish, sch.calendar).date()
        axis_dates.extend((start, finish))
        return start.isoformat(), finish.isoformat()

    def grid(idx: int, uid: int) -> dict[str, object]:
        task = by_id[idx].get(uid) if 0 <= idx < len(by_id) else None
        if task is None:
            return {"percent_complete": None, "duration": None, "complete": False}
        per_day = schedules[idx].calendar.working_minutes_per_day or 1
        return {
            "percent_complete": round(task.percent_complete),
            "duration": f"{task.duration_minutes / per_day:g}wd",
            "complete": task.is_complete or task.actual_finish is not None,
        }

    # per-version tier membership: uid -> tier label, for the selected tiers only
    members: list[dict[int, str]] = []
    for i, sch in enumerate(schedules):
        focus = (
            target
            if (target is not None and target in by_id[i])
            else _project_finish_uid(sch, cpms[i])
        )
        m: dict[int, str] = {}
        if focus is not None:
            try:
                results = compute_driving_slack(sch, focus, cpm_result=cpms[i])
            except (KeyError, ValueError):
                results = {}
            for uid, r in results.items():
                if r.tier in selected:
                    m[uid] = _EVO_TIER_LABEL[r.tier]
        members.append(m)

    snapshots: list[dict[str, object]] = []
    prior: set[int] = set()
    for i, snap in enumerate(evolution.snapshots):
        cur = set(members[i])
        entered = (cur - prior) if i > 0 else set()
        left = (prior - cur) if i > 0 else set()
        rows: list[dict[str, object]] = []
        for uid in cur:
            start, finish = bar(i, uid)
            task = by_id[i].get(uid)
            rows.append(
                {
                    "uid": uid,
                    "name": task.name if task is not None else f"UID {uid}",
                    "start": start,
                    "finish": finish,
                    "entered": uid in entered,
                    "duration_changed": False,
                    "reason": None,
                    "detail": None,
                    "tier": members[i][uid],
                    **grid(i, uid),
                }
            )
        rows.sort(key=lambda r: (r["start"] is None, str(r["start"])))
        left_rows: list[dict[str, object]] = []
        for uid in sorted(left):
            start, finish = bar(i - 1, uid) if i > 0 else (None, None)
            g = grid(i - 1, uid)
            now = by_id[i].get(uid)
            g["complete"] = bool(now and (now.is_complete or now.actual_finish is not None))
            name = by_id[i - 1][uid].name if (i > 0 and uid in by_id[i - 1]) else f"UID {uid}"
            left_rows.append(
                {
                    "uid": uid,
                    "name": name,
                    "start": start,
                    "finish": finish,
                    "reason": None,
                    "detail": None,
                    "tier": members[i - 1].get(uid) if i > 0 else None,
                    **g,
                }
            )
        prior = cur
        snapshots.append(
            {
                "label": snap.label,
                "status_date": snap.status_date,
                "project_finish": snap.project_finish,
                "finish_delta_days": snap.finish_delta_days,
                "critical": sorted(cur),
                "entered": sorted(entered),
                "left": sorted(left),
                "duration_changed": [],
                "shortened_on_path": [],
                "removed_logic_count": 0,
                "names": {str(u): (by_id[i][u].name if u in by_id[i] else f"UID {u}") for u in cur},
                "critical_rows": rows,
                "left_rows": left_rows,
                "path_to_target": [],
            }
        )
    axis = {
        "min": min(axis_dates).isoformat() if axis_dates else None,
        "max": max(axis_dates).isoformat() if axis_dates else None,
    }
    return {"axis": axis, "snapshots": snapshots, "target": target, "tier": tier}


def _how_stable_header(ev: PathEvolution) -> str:
    """Chapter 04 "How stable is the path" (ADR-0200): the data-driven takeaway + a churn KPI strip
    + the Latest-critical-path and Total-churn bars, from the per-version critical-path snapshots.
    Every figure is read from the evolution the page already computed (no engine math)."""
    snaps = ev.snapshots
    n_ver = len(snaps)
    updates = max(n_ver - 1, 1)
    entered = sum(len(s.entered) for s in snaps[1:])
    left = sum(len(s.left) for s in snaps[1:])
    latest = snaps[-1]
    crit_now = len(latest.critical)
    moves = [s.finish_delta_days for s in snaps[1:] if s.finish_delta_days is not None]
    net = sum(moves) if moves else None
    churn = entered + left

    def _acts(x: int) -> str:
        return "activity" if x == 1 else "activities"

    if churn == 0:
        stability = "held completely steady"
    elif churn <= updates:
        stability = "stayed largely stable"
    else:
        stability = "churned"
    if net is None:
        fin = ""
    elif net > 0:
        fin = f", and the finish slipped {net} calendar day{'s' if net != 1 else ''}"
    elif net < 0:
        fin = f", and the finish pulled in {abs(net)} calendar day{'s' if net != -1 else ''}"
    else:
        fin = ", while the finish held"
    takeaway = (
        f"Across {n_ver} versions the critical path {stability} — {entered} {_acts(entered)} "
        f"entered it and {left} left{fin}."
    )

    kpi = _stat_cards(
        [
            ("Versions compared", str(n_ver)),
            ("Critical now", str(crit_now)),
            ("Entered (all updates)", str(entered)),
            ("Left (all updates)", str(left)),
            ("Net finish move", f"{net:+d} d" if net is not None else "—"),
            ("Churn per update", f"{churn / updates:.1f}"),
        ]
    )
    # the latest file resolves the segment activities (entered/left UIDs are matched against it)
    fkey = latest.label
    churn_entered_uids = tuple(sorted({u for s in snaps[1:] for u in s.entered}))
    churn_left_uids = tuple(sorted({u for s in snaps[1:] for u in s.left}))
    latest_bar = _status_stack(
        "Latest critical path",
        f"How the newest version's path formed — {latest.label}.",
        [("Entered", len(latest.entered), "--ok"), ("Stayed", len(latest.stayed), "--muted")],
        f"{crit_now} on the path now; {len(latest.left)} left since the prior version",
        drill=[(tuple(latest.entered), fkey), (tuple(latest.stayed), fkey)],
    )
    churn_bar = _status_stack(
        "Total churn",
        "Activities that entered vs left the critical path across every update.",
        [("Entered", entered, "--ok"), ("Left", left, "--bad")],
        f"over {updates} update{'s' if updates != 1 else ''}",
        drill=[(churn_entered_uids, fkey), (churn_left_uids, fkey)],
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{takeaway}</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{latest_bar}{churn_bar}</div>'
        "<div id=sfDrillMount></div>"  # drilldown.js loaded globally in _LAYOUT
    )
