"""The /resources page family: who is booked beyond their availability, and when.

Monolith split, phase 3 slice 15 (ADR-0379), extracted VERBATIM from ``web/app.py``: every
function, docstring and comment moves byte-for-byte, only the module boundary changes.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour (the
``/resources`` page route and the two export routes, ``/export/{fmt}/resources`` and
``/export/{fmt}/resource-drill``): FOUR names in one contiguous block — the CSP-safe JSON
payload resources.js drills into, the how-to-read explainer, the chapter-08 "Who is overloaded"
header, and the page body with its histogram and roster panels. The closure is census-EXACT
(the prefix census said 306 ast lines; the referrer walk says the same four names, 306) — the
second consecutive exact closure, and again only because the queue had already absorbed the
prior ruling by hand.

**No descent.** The walk surfaced exactly one shared name, ``_cell`` (2 lines) — pulled in by
the ``export_resource_drill`` ROUTE, never by a mover, and referred to by eight other routes and
two importers besides. A route-only referrer never forces a descent (ADR-0378): routes live in
``create_app``, which imports downward and stays.

**The export routes contribute NO movers** — the streak that ended at five in ADR-0378 resumes
here: ``export_resources`` and ``export_resource_drill`` build their own tables straight from
``compute_resource_loading``, so this family's proven surface is the page alone.

Layering: ``app`` -> ``resources`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

import json

from schedule_forensics.engine.resources import (
    ResourceLoading,
    bucket_key,
    compute_resource_loading,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.components import (
    _latest_solvable,
    _panel_head,
    _prov_chip,
    _shell_tools,
    _stat_cards,
    _status_stack,
    _user_tip,
)
from schedule_forensics.web.state import SessionState


def _resource_loading_json(rl: ResourceLoading, sch: Schedule) -> str:
    """The resource-loading payload for resources.js (load/capacity in working DAYS for display).

    Each period carries its per-task ``contributors`` (uid, name, days) so clicking a bar opens the
    over-allocation drill entirely client-side (the work behind that bar), same-origin only."""
    mpd = rl.working_minutes_per_day or 480
    by_id = sch.tasks_by_id
    payload = {
        "granularity": rl.granularity,
        # provenance + drill wiring (operator 2026-07-10): the drill fetches field data from
        # /api/analysis/<source_file> and builds its Excel link against the same file
        "source_file": sch.source_file or sch.name,
        # The data-date line (ADR-0342). The BUCKET KEY is computed HERE, with the engine's own
        # bucket_key, rather than re-derived in JS: the three granularities include ISO week
        # numbering (YYYY-Www, Monday-start), and a second implementation of that in the browser
        # is exactly the kind of drift this round is closing. None when the schedule carries no
        # status date — the chart then draws no marker rather than one at an assumed position.
        "status_date": sch.status_date.date().isoformat() if sch.status_date else None,
        "status_period": (
            bucket_key(sch.status_date.date(), rl.granularity) if sch.status_date else None
        ),
        "resources": [
            {
                "id": r.resource_id,
                "name": r.name,
                "type": r.type,
                "max_units": r.max_units,
                "total_days": round(r.total_work_minutes / mpd, 1),
                "over": list(r.over_allocated_periods),
                "series": [
                    {
                        "period": p.period,
                        "load": round(p.load_minutes / mpd, 2),
                        "cap": round(p.capacity_minutes / mpd, 2),
                        "over": p.over_allocated,
                        "tasks": [
                            {
                                "uid": uid,
                                "name": (by_id[uid].name if uid in by_id else f"UID {uid}"),
                                "days": round(mins / mpd, 2),
                            }
                            for uid, mins in p.contributors
                        ],
                    }
                    for p in r.series
                ],
            }
            for r in rl.resources
        ],
    }
    return json.dumps(payload).replace("<", "\\u003c")  # match the scurve/rem embeds (QC INFO)


def _resources_explainer() -> str:
    return """
<div class=panel><h2>How to read the resource loading</h2>
<details class=explainer><summary><b>What this shows &amp; how it's computed</b></summary>
<p>Each task's assigned <b>work</b> (hours, from the schedule's resource assignments) is spread evenly
across the <b>working days</b> of the task's span (its CPM early start &rarr; early finish) and totalled
into the chosen <b>bucket</b> (day / week / month), per resource. A resource's per-bucket <b>capacity</b>
is <code>max&nbsp;units &times; working&nbsp;hours/day &times; working&nbsp;days&nbsp;in&nbsp;the&nbsp;bucket</code>,
so over-allocation is consistent at every granularity.</p>
<p>A bucket where booked work <b>exceeds capacity</b> is <b class=res-over>over-allocated</b> (shown red)
&mdash; the resource is asked to do more than its availability allows there, a signal to re-level,
re-sequence, or add capacity. <b>Click any bar</b> to see the exact activities driving that bucket's
load. A schedule that records resource <i>names</i> but no <i>work</i> hours shows assignment counts
only (no load bars).</p></details>
<details class=explainer><summary><b>Pros &amp; cons of the even-spread method</b></summary>
<p><b>Pro:</b> works on any schedule that carries assignment work, with no extra inputs, and gives a
faithful monthly histogram. <b>Con:</b> it assumes work is spread evenly across the task (no front/back
loading) when the source file doesn't carry a time-phased contour &mdash; the totals are exact, the
within-task shape is an approximation.</p></details>
</div>"""


def _who_is_overloaded_header(st: SessionState, granularity: str = "month") -> str:
    """Chapter 08 "Who is overloaded" (ADR-0206): the data-driven takeaway + an allocation KPI
    strip + the resource-allocation and overload-concentration bars, from the same resource
    loading the page charts (compute_resource_loading — no new math). Empty when the schedule
    carries no resources (the body renders its own notice)."""
    chosen = _latest_solvable(st)
    if chosen is None:
        return ""
    _key, sch, cpm = chosen
    granularity = granularity if granularity in ("day", "week", "month") else "month"
    rl = compute_resource_loading(sch, cpm, granularity)
    if not rl.resources:
        return ""
    mpd = rl.working_minutes_per_day or 480
    n_res = len(rl.resources)
    over = [r for r in rl.resources if r.over_allocated_periods]
    over_count = len(over)
    within = n_res - over_count
    total_days = round(sum(r.total_work_minutes for r in rl.resources) / mpd, 1)
    unit = {"day": "day", "week": "week", "month": "month"}[granularity]
    # the single worst resource by number of over-allocated periods
    worst = max(rl.resources, key=lambda r: len(r.over_allocated_periods), default=None)
    worst_over = len(worst.over_allocated_periods) if worst else 0

    def _res(n: int) -> str:
        return "resource" if n == 1 else "resources"

    if over_count == 0:
        takeaway = (
            f"All {n_res} loaded {_res(n_res)} stay within capacity across the {len(rl.periods)} "
            f"{unit}{'s' if len(rl.periods) != 1 else ''} covered — no over-allocation."
        )
    elif worst is not None and worst_over > 0:
        takeaway = (
            f"{over_count} of {n_res} {_res(n_res)} are over-allocated in at least one {unit} — "
            f"the worst is {worst.name}, over capacity in {worst_over} {unit}"
            f"{'s' if worst_over != 1 else ''}."
        )
    else:
        takeaway = (
            f"{over_count} of {n_res} {_res(n_res)} are over-allocated in at least one {unit}."
        )

    kpi = _stat_cards(
        [
            ("Resources loaded", str(n_res)),
            ("Over-allocated", str(over_count)),
            ("Within capacity", str(within)),
            ("Total work (days)", f"{total_days:g}"),
            ("Busiest resource", worst.name if worst else "—"),
            (f"{unit.title()}s covered", str(len(rl.periods))),
        ]
    )
    alloc_bar = _status_stack(
        "Resource allocation",
        f"Loaded resources within vs over their capacity, bucketed by {unit}.",
        [("Within capacity", within, "--ok"), ("Over-allocated", over_count, "--bad")],
        f"{n_res} {_res(n_res)} loaded",
    )
    if worst is not None and len(rl.periods) > 0:
        w_over = len(worst.over_allocated_periods)
        w_clear = max(len(rl.periods) - w_over, 0)
        conc_bar = _status_stack(
            "Overload concentration",
            f"The busiest resource's timeline — {worst.name} — over vs within capacity per {unit}.",
            [("Over capacity", w_over, "--bad"), ("Within", w_clear, "--muted")],
            f"{w_over} of {len(rl.periods)} {unit}{'s' if len(rl.periods) != 1 else ''} over capacity",
        )
    else:
        conc_bar = ""
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        '<p class="page-lede">Who is booked beyond their availability, and when. Each resource\'s '
        "assigned work is spread across its activities' spans and totalled per bucket, then "
        "compared with that resource's own capacity for the same bucket.</p>"
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{alloc_bar}{conc_bar}</div>'
    )


def _resources_body(st: SessionState, granularity: str = "month") -> str:
    """Resources page: per-resource loading histogram + over-allocation, and a roster table.

    Panel contract (Mission Ops rank 10, ADR-0298): the three content panels wear the headline
    strip + tools + provenance chip + one ``.sf-take``. Four deliberate decisions, each of which
    would otherwise ship an inert or lying control:

    * **⤓ EXCEL carries the RENDERED bucket** — ``/export/xlsx/resources?bucket={granularity}``,
      never a bare URL. Capacity scales with the working days in a bucket, so an operator reading
      the week histogram must not silently receive the month workbook (a presentation lie about
      engine numbers). The same endpoint the page-level export bar already points at — one
      convention, two affordances.
    * **no ▦ DATA anywhere** — no panel carries a ``.sf-drawer``, and the two data panels' own
      tables ARE their data (the :func:`_shell_tools` home-shell precedent). Inventing a drawer
      here would mean emitting per-period load/capacity numbers the page does not render today.
    * **panel-scoped ⛶** — each converted panel holds AT MOST ONE chart (the histogram panel has
      exactly one ``.chart-host``; the other two have none), so one ⛶ can never desync a sibling.
    * **every take figure is already on the page** — the summary take quotes only the four
      ``{cards}`` values; the histogram and roster takes quote only roster ROW 1, which is
      ``rl.resources[0]`` — the same object the first ``<option>`` selects and the chart therefore
      opens on. No figure is re-derived (the header's ``worst`` max() lives in
      :func:`_who_is_overloaded_header` and is deliberately NOT recomputed here)."""
    chosen = _latest_solvable(st)
    if chosen is None:
        return (
            "<div class=panel>Load a resource-loaded schedule to see resource loading and "
            "over-allocation.</div>"
        )
    _key, sch, cpm = chosen
    granularity = granularity if granularity in ("day", "week", "month") else "month"
    rl = compute_resource_loading(sch, cpm, granularity)
    if not rl.resources:
        return (
            "<div class=panel><h2>Resources</h2><p class=muted>This schedule has no resource "
            "assignments to load. Load an MS Project / Primavera file with assigned resources.</p>"
            "</div>"
        )
    mpd = rl.working_minutes_per_day or 480
    over_count = sum(1 for r in rl.resources if r.over_allocated_periods)
    total_days = round(sum(r.total_work_minutes for r in rl.resources) / mpd, 1)
    gran_label = {"day": "Days", "week": "Weeks", "month": "Months"}[granularity]
    cards = _stat_cards(
        [
            ("Resources loaded", str(len(rl.resources))),
            ("Total work (days)", f"{total_days:g}"),
            ("Over-allocated resources", str(over_count)),
            (f"{gran_label} covered", str(len(rl.periods))),
        ]
    )
    rows = "".join(
        f"<tr><td>{_e(r.name)}</td><td>{_e(r.type.title())}</td>"
        # a max units the FILE stated renders as its own figure; the engine's assumed 1.0
        # default renders as an em dash — "missing shows —, never a fabricated figure"
        f"<td class=num>{f'{r.max_units:g}' if r.max_units_declared else '—'}</td>"
        f"<td class=num>{round(r.total_work_minutes / mpd, 1):g}</td>"
        f"<td class=num>{r.task_count}</td><td>{_e(r.peak_period or '')}</td>"
        f"<td class={'res-over' if r.over_allocated_periods else 'num'}>"
        f"{len(r.over_allocated_periods) or ''}</td></tr>"
        for r in rl.resources
    )
    unit = gran_label[:-1].lower()  # "day" / "week" / "month"
    roster = (
        "<table class=card-table><tr><th scope=col>Resource</th><th scope=col>Type</th>"
        "<th scope=col>Max units</th><th scope=col>Work (days)</th><th scope=col>Tasks</th>"
        f"<th scope=col>Peak {unit}</th><th scope=col>Over-alloc {unit}s</th></tr>"
        f"{rows}</table>"
    )
    res_opts = "".join(
        f'<option value="{r.resource_id}">{_e(r.name)}'
        f"{' ⚠' if r.over_allocated_periods else ''}</option>"
        for r in rl.resources
    )
    blob = _resource_loading_json(rl, sch)
    # day/week/month bucket selector (operator #74) — a plain GET so the server recomputes capacity
    # at the chosen granularity (capacity scales with the working days in each bucket).
    bucket_opts = "".join(
        f'<option value="{g}"{" selected" if g == granularity else ""}>{g.title()}</option>'
        for g in ("day", "week", "month")
    )
    bucket_form = (
        '<form method=get action=/resources class=viz-controls style="display:inline-flex">'
        f"<label>Bucket <select name=bucket data-no-i18n data-sf-autosubmit "
        f'title="Time-bucket the histogram by day, week or month">{bucket_opts}</select></label>'
        "</form>"
    )
    tip = _user_tip(
        "Pick a resource to see its <b>work vs capacity</b> histogram at the chosen bucket "
        "(day&nbsp;/&nbsp;week&nbsp;/&nbsp;month). Bars above the capacity line (red) are "
        "<b>over-allocated</b> &mdash; where that resource is booked beyond its availability. "
        "<b>Click any bar</b> to list the activities driving that bucket's load."
    )
    # ── The panel contract for this page (see the docstring for the four decisions). The
    # data-export URL carries the RENDERED bucket so ⤓ EXCEL can never hand back a workbook
    # computed at a different granularity than the one on screen.
    prov = _prov_chip(sch)
    export_url = f"/export/xlsx/resources?bucket={granularity}"
    tools = _shell_tools(
        export_title=(
            f"Export the resource-loading series and roster at the {unit} bucket — opens in Excel"
        )
    )
    sum_head = _panel_head(
        f"Resource loading &amp; over-allocation &mdash; {_e(sch.source_file or sch.name)}",
        tools=tools,
        prov=prov,
    )
    hist_head = _panel_head("Loading histogram", tools=tools, prov=prov)
    util_head = _panel_head("Utilization by resource", tools=tools, prov=prov)
    roster_head = _panel_head("Resource roster", tools=tools, prov=prov)
    # every figure below is ALREADY rendered verbatim on this page, read from the same variable
    # the visible markup reads: the four {cards} values, and roster ROW 1 (rl.resources[0]) —
    # which is also the first <option>, i.e. the resource the histogram opens on.
    n_periods = len(rl.periods)
    unit_s = f"{unit}{'s' if n_periods != 1 else ''}"
    first = rl.resources[0]
    first_days = f"{round(first.total_work_minutes / mpd, 1):g}"  # the roster row-1 Work cell
    over_clause = (
        f"{over_count} of them are over-allocated in at least one {unit}"
        if over_count
        else f"none is over-allocated in any {unit}"
    )
    sum_take = (
        f"{len(rl.resources)} loaded resources carry {total_days:g} work-days across "
        f"{n_periods} {unit_s}; {over_clause}."
    )
    peak_clause = f", peaking in {_e(first.peak_period)}" if first.peak_period else ""
    hist_take = (
        f"The histogram opens on {_e(first.name)} &mdash; {first_days} work-days across "
        f"{first.task_count} activities{peak_clause}; bars above the dashed capacity line are "
        f"that resource's over-allocated {unit}s."
    )
    roster_take = (
        f"All {len(rl.resources)} of the schedule's resources are listed — assigned or not — "
        f"largest first: {_e(first.name)} at {first_days} work-days across "
        f"{first.task_count} activities; {over_clause}."
    )

    util_take = (
        "Every resource's peak utilization against its OWN max units, on one chart, worst "
        "first — the whole roster at a glance instead of one resource at a time."
    )

    def take(text: str) -> str:
        return f"<p class=sf-take data-no-i18n>{text}</p>"

    return f"""
<div class=panel data-export="{export_url}">{sum_head}
{take(sum_take)}
<p class=muted>Time-phased work per resource per {unit}, against each resource's capacity. Over-allocated
{unit}s are flagged.</p>
{tip}
{cards}</div>
<div class=panel data-export="{export_url}">{hist_head}
{take(hist_take)}
<div class=viz-controls><label>Resource <select id=resPick>{res_opts}</select></label>
{bucket_form}<span id=resStatus class=muted></span></div>
<div id=resChart class=chart-host></div>
<div id=resDrill></div>
<script type="application/json" id=resData>{blob}</script>
<script defer src="/static/resources.js"></script></div>
<div class=panel data-export="{export_url}">{roster_head}
{take(roster_take)}
<p class=muted>Every resource in the schedule — assigned or not — sorted by total work; unassigned
resources show zero work. Max units is the file's own figure (&mdash; when the file does not state
one; capacity then assumes 1 full unit, see the explainer). Over-allocated {unit}s are the count of
{unit}s booked beyond capacity.</p>
{roster}</div>
<div class=panel data-export="{export_url}">{util_head}
{take(util_take)}
<p class=muted>Peak booked load as a share of each resource's OWN capacity (its max units) in its
busiest {unit} — every resource on one chart, worst first. The amber line is 100% of capacity;
bars past it are over-allocated. A resource with booked work but zero capacity reads "over (no
capacity)".</p>
<div id=resUtilChart></div></div>
{_resources_explainer()}
<script src="/static/panelkit.js"></script>"""
