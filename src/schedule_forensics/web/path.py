"""The /path page family: the SSI-style path-analysis workspace and its chapter-03 header.

Monolith split, phase 3 slice 17 (ADR-0381), extracted VERBATIM from ``web/app.py``: both
functions move byte-for-byte — every docstring, comment and HTML f-string unchanged — and only
the module boundary is new.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour (the
``/path`` page route and the ``/export/{fmt}/path/{name}`` trace export): TWO names in ONE
contiguous block (app.py 6972-7167) — the "What drives the date" story header and the
path-analysis workspace body.

**The closure equals the census here — measured, not assumed.** The ``/path`` prefix finds 2
names / 194 ast lines; the referrer walk over both routes finds the same 2 / 194 (1.00x). Every
other name the two members touch resolves to an *import* — ``components``, ``chrome``, ``state``
or the engine — so there is nothing to descend into and no shared name to adjudicate. The prefix
remains a finder and the walk remains the definition (ADR-0378); this slice is simply a family
whose author kept it whole.

**The export route contributes NO movers.** ``export_path`` serves the /driving-path trace, not
this page: it builds from ``_driving_data`` (``web.driving``), ``_optioned_versions``
(``web.evolution``) and ``driving_table`` (``reports.tables``), all of them already extracted.
The page's own grid is client-side over ``/api/driving``, which belongs to the driving family.

Layering: ``app`` -> ``path`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

from schedule_forensics.engine.cpm import offset_to_datetime
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.components import (
    _mdY,
    _panel_head,
    _shell_tools,
    _stat_cards,
    _status_stack,
    _user_tip,
)
from schedule_forensics.web.state import _Analysis


def _what_drives_header(sch: Schedule, analysis: _Analysis) -> str:
    """Chapter 03 "What drives the date" (ADR-0199): the data-driven takeaway + a drivers KPI strip
    + the Critical-exposure and Path-composition bars, for the latest version. The critical path
    (``cpm.critical_path``) is already scoped to any global Analysis Target, so this respects it
    automatically. Every figure is read from what the report already computed (no engine math)."""
    cpm = analysis.cpm
    chain = cpm.critical_path  # unique_ids with total_float <= 0, topo order
    n = len(chain)
    total = sum(1 for _ in non_summary(sch)) or 1

    path_float_min = min((cpm.timings[u].total_float for u in chain if u in cpm.timings), default=0)
    path_float_days = path_float_min / 480.0
    longest_uid: int | None = None
    longest_min = -1
    for u in chain:
        t = sch.tasks_by_id.get(u)
        if t is not None and t.duration_minutes > longest_min:
            longest_min, longest_uid = t.duration_minutes, u
    longest_days = longest_min / 480.0 if longest_min >= 0 else 0.0
    longest_name = sch.tasks_by_id[longest_uid].name if longest_uid is not None else "—"
    cpm_finish = _mdY(offset_to_datetime(sch.project_start, cpm.project_finish, sch.calendar))

    if path_float_days < 0:
        float_phrase = f"{abs(path_float_days):g} days of negative float (already behind)"
    elif path_float_days == 0:
        float_phrase = "0 days of total float"
    else:
        float_phrase = f"{path_float_days:g} days of total float"
    acts = "activity" if n == 1 else "activities"
    if n:
        takeaway = (
            f"The finish rides on a critical path of {n} {acts} carrying {float_phrase} — "
            f"its longest single activity is {_e(longest_name)} at {longest_days:g} working days."
        )
    else:
        takeaway = "No critical path resolves for this version."

    floats: list[float] = []
    for r in analysis.activity_rows:
        tf = r.get("total_float_days")
        pc = r.get("percent_complete")
        if isinstance(tf, int | float) and isinstance(pc, int | float) and pc < 100.0:
            floats.append(float(tf))
    b0 = sum(1 for f in floats if f <= 0)
    b1 = sum(1 for f in floats if 0 < f <= 4)
    b2 = sum(1 for f in floats if 4 < f <= 9)
    b3 = sum(1 for f in floats if f > 9)

    kpi = _stat_cards(
        [
            ("Critical-path activities", str(n)),
            ("Path total float", f"{path_float_days:g} d"),
            ("Longest driver", f"{longest_days:g} d"),
            ("On the critical path", f"{100.0 * n / total:.0f}%"),
            ("Computed finish", cpm_finish),
            ("Near-critical (≤ 4d)", str(b0 + b1)),
        ]
    )
    exposure = _status_stack(
        "Critical exposure",
        "Incomplete activities by total-float band — how many sit at or near the edge.",
        [
            ("0 days", b0, "--bad"),
            ("1-4 days", b1, "--warn"),
            ("5-9 days", b2, "--accent"),
            ("10+ days", b3, "--muted"),
        ],
        f"{len(floats)} incomplete activities",
    )
    composition = _status_stack(
        "Path composition",
        "Activities that drive the finish (critical path) vs those carrying slack.",
        [("Critical path", n, "--bad"), ("Has slack", max(total - n, 0), "--ok")],
        f"{total} activities",
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{takeaway}</h1>'
        f'<div class="ws-kpi">{kpi}</div>'
        f'<div class="ws-bars">{exposure}{composition}</div>'
    )


def _path_body(keys: list[str], target_uid: int | None) -> str:
    """The SSI-style path-analysis workspace: controls, data grid left, scalable Gantt right.

    All interaction is client-side (`static/path.js`) over `/api/driving` — field
    add/remove, filters (incl. hide-completed), tier day-bands, zoom, the data-date
    line. The grounded ask-the-AI panel is the page-shell one (`_ask_panel_html`)."""
    # default the grid to the LATEST version (keys[-1]) — the same version the "What drives the
    # date" header above is anchored on (ADR-0199). Without this the browser defaults to the first
    # <option> (the OLDEST version), so the header described one file while the grid traced another
    # — the operator's "critical path is mixing up information from the various files" report.
    latest = keys[-1] if keys else None
    options = "".join(
        f'<option value="{_e(k)}"{" selected" if k == latest else ""}>{_e(k)}</option>'
        for k in keys
    )
    # Panel-contract head (Mission Ops rank 11): ⛶ ENLARGE ONLY.
    #  * NO ⤓ EXCEL. `/export/xlsx/path/{name}` declares `target: int = Query(...)` — REQUIRED —
    #    so with no session target the URL answers 422 application/json, and `st.target_uid` is
    #    legitimately None on this page. A server-rendered `data-export` would therefore ship a
    #    dead link in a real session state. path.js:204-213 (`updateExportLinks`) already owns a
    #    LIVE, column-aware export bar (#pathXlsx / #pathDocx) that rebuilds on every trace —
    #    reuse the page's existing mechanism instead of shadowing it with a stale pinned URL.
    #  * NO `prov=`. The version this panel traces is chosen CLIENT-side by #pathSchedule, so a
    #    server-rendered file/data-date chip would be wrong the moment the operator switches
    #    version; #pathStatus already prints target + name + data date + coverage from the live
    #    /api/driving payload.
    head = _panel_head(
        "Path analysis &mdash; driving / secondary / tertiary to a target",
        tools=_shell_tools(),
    )
    # The takeaway states ONLY what the server knows at render time — the session target that the
    # workspace opens on (path.js traces immediately when #pathTarget carries a value) and how many
    # versions are selectable. No engine figure is invented here: the traced counts come from
    # /api/driving and are printed live by #pathStatus.
    if not keys:
        take = ""
    elif target_uid is not None:
        where = (
            "the only loaded version"
            if len(keys) == 1
            else f"the latest of {len(keys)} loaded versions"
        )
        take = (
            f"<p class=sf-take data-no-i18n>Opens on the session target UID {target_uid} &mdash; traced in "
            f"{where}; pick another version or a different UniqueID above to re-trace.</p>"
        )
    else:
        avail = "1 loaded version is" if len(keys) == 1 else f"{len(keys)} loaded versions are"
        take = (
            "<p class=sf-take data-no-i18n>No session target is set &mdash; enter a target "
            f"UniqueID above and press Trace; {avail} available to trace.</p>"
        )
    return f"""
<div class=panel>{head}{take}
<p class=muted>Pick a schedule and a target UniqueID: the driving path (slack &le; 0) and the
secondary/tertiary tiers within your day-bands trace back from it — data on the
left, a scalable timeline on the right with the gold data-date line. Add/remove columns,
filter rows, and hide completed work. <b>Click a row</b> to highlight that task's fields and its
bar; click another task to move the highlight, or click off to clear it. <b>Double-click</b> a row
for the full Task Information.</p>
{_user_tip("Pick a tier such as <b>DRIVING</b> to fit the timeline to just that path so its bars fill the page; the data columns stay locked on the left as the timeline scrolls, and <b>View entire project</b> zooms back out to the whole trace.")}
<details class=path-explainer><summary>Why an activity can show 0&#8209;day driving slack here but not on another view</summary>
<p class=muted>This trace is <b>relative to the target UniqueID</b> you choose. An activity has
<b>0 days of driving slack</b> when a slip in it would push <i>this target's</i> finish, so it sits
on the driving path <b>to that target</b>. The same activity may legitimately not appear on a view
scoped to a <b>different</b> target, on the project&#8209;finish critical path (the DCMA
&ldquo;Critical Path Test&rdquo;), or when completed work is hidden &mdash; driving slack to a
target and the project's critical path answer different questions. Turn on the <b>Drives &#8594;</b>
column to see each activity's logic successors inside this trace (e.g. UID 8022 &#8594; UID 152);
a <b>*</b> marks the successor that keeps the chain on the driving path.</p></details>
<div class="viz-controls sf-freeze-bar" id=pathControls>
<label>Schedule <select id=pathSchedule>{options}</select></label>
<label>Target UID <input id=pathTarget type=number min=1 value="{target_uid if target_uid is not None else ""}" placeholder="UID"></label>
<label>Secondary &le; <input id=pathSec type=number min=1 value=10 title="days of driving slack"> d</label>
<label>Tertiary &le; <input id=pathTer type=number min=1 value=20 title="days of driving slack"> d</label>
<button id=pathRun type=button>Trace</button>
<button id=pathDrag type=button title="SSI-validated Devaux DRAG: how many working days each driving-path activity personally adds — capped by its remaining duration and by parallel branches">Run Drag Analysis</button>
<label><input id=pathHideDone type=checkbox> hide 100% complete</label>
<label>Tier <span id=pathTier class=tier-filter></span></label>
<label>Filter <input id=pathFilter type=text placeholder="name / UID contains"></label>
<label>Find <input id=pathFind type=text placeholder="UID or name…" title="Jump to a UniqueID, or mark every traced task whose row contains this text"></label>
<span id=pathFindStatus class=muted aria-live=polite></span>
<label title="Show the start/finish dates at the ends of the Gantt bars (MS Project bar text)"><input id=pathBarDates type=checkbox> dates on bars</label>
<label>Zoom <input id=pathZoom type=range min=2 max=40 value=8 title="pixels per day"></label>
<button id=timescaleBtn type=button title="Modify the timescale: tiers, units (years to hours), labels, count, alignment, fiscal year, tick lines, size and non-working-time shading (like Microsoft Project)">Timescale&hellip;</button>
<button id=pathFit type=button class=linkbtn title="Auto-scale the timeline so the whole project fits">View entire project</button>
</div>
<details class=path-options open><summary>Path options (SSI Directional Path Tool)</summary>
<div class=viz-controls id=pathOptions>
<span class=opt-group><b>Path Direction</b>
<label><input type=radio name=pathDir value=predecessors checked> &#8592; Predecessors</label>
<label><input type=radio name=pathDir value=successors> &#8594; Successors</label>
<label><input type=radio name=pathDir value=both> &#8596; Both</label></span>
<span class=opt-group><b>Dependency Range</b>
<label><input type=radio name=pathRange value=slack> Driving Slack &le;
<input id=pathRangeDays type=number min=0 value=0 style="width:52px"> d</label>
<label><input type=radio name=pathRange value=all checked> Get all dependencies</label></span>
<span class=opt-group>
<label><input id=pathIgnoreConstraints type=checkbox title="SSI-parity option: strips constraint pins out of the CPM fallback that dates otherwise-undated tasks. Tasks with stored dates keep them — on a fully-dated file the trace is unchanged, matching SSI's own output with this option on (ADR-0251)"> Ignore constraints</label>
<label><input id=pathIgnoreLeveling type=checkbox title="SSI-parity option: measures link gaps on the project-calendar date basis (stored dates first; CPM only for undated tasks). Stored leveled dates still govern — on a fully-dated file the trace is unchanged, matching SSI's own output with this option on (ADR-0251)"> Ignore leveling delay</label></span>
<span class=opt-group><b>Output</b>
<label><input type=radio name=pathOutput value=waterfall checked> &#8615; Waterfall</label>
<label><input type=radio name=pathOutput value=summaries> With Summaries</label>
<label><input type=radio name=pathOutput value=parallel> Separate parallel paths</label></span>
<span class=opt-group><b>Group by</b>
<select id=pathGroupBy title="Group the traced activities by any field — standard or custom (e.g. a CA-WBS code); overrides the Output grouping"><option value="">(none)</option></select></span>
<span class=opt-group><label><input id=pathShowLinks type=checkbox title="Draw the logic links between traced activities on the timeline (MS-Project Layout style)"> Show links</label></span>
</div></details>
<div id=pathFields class=muted></div>
<div class="export-bar" id=pathExport style="display:none"><a id=pathXlsx href="#">&#11015; Excel</a><a id=pathDocx href="#">&#11015; Word</a></div>
<div id=pathStatus class=muted></div>
<div id=pathView class=path-view></div></div>
<script src="/static/path.js"></script>
<script src="/static/panelkit.js"></script>"""
