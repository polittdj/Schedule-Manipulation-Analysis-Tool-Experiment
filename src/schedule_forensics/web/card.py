"""The /card page family: the schedule's ID card and its count/percent pivot table.

Monolith split, phase 4 slice 22 (ADR-0387), extracted VERBATIM from ``web/app.py``: every
function and constant moves byte-for-byte -- docstrings, comments and HTML f-strings
unchanged -- and only the module boundary is new.

The seam is the AST transitive closure of ``GET /card/{name}``.  TWO names in ONE
contiguous block (app.py 7156-7297), and the prefix finds only one of them:
``_count_bar_table`` carries no ``card`` token in its name and is a member -- its only
referrer is ``_card_body``.  The prefix is a finder; the walk is the definition
(ADR-0378).

``_unschedulable_panel`` is NOT a member: the ``/card`` route calls it, but so does
``/analysis``.  A route-only referrer never blocks a move (ADR-0378) but it does not
make the name this family's to carry, so it stays in ``app.py``.

Layering: ``app`` -> ``card`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

from urllib.parse import quote

from schedule_forensics.engine.cpm import offset_to_datetime
from schedule_forensics.engine.metrics import (
    compute_activity_makeup,
    compute_constraint_distribution,
)
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e, _utility_takeaway
from schedule_forensics.web.components import (
    _mdY,
    _panel_head,
    _prov_chip,
    _shell_tools,
    _stat_cards,
)
from schedule_forensics.web.state import _Analysis


def _count_bar_table(headers: tuple[str, str], rows: list[tuple[str, int, float]]) -> str:
    """A count + percent table with an inline percent bar (deck pie/pivot, as a table)."""
    body = "".join(
        f"<tr><td>{_e(label)}</td><td>{count}</td>"
        f'<td class=pct-cell><span class=pct-bar style="width:{min(pct, 100):.0f}%"></span>'
        f"<span class=pct-num>{pct:.1f}%</span></td></tr>"
        for label, count, pct in rows
    )
    return (
        f"<table class=card-table><tr><th scope=col>{_e(headers[0])}</th><th scope=col>Count</th>"
        f"<th scope=col>{_e(headers[1])}</th></tr>{body}</table>"
    )


def _card_body(
    key: str, sch: Schedule, analysis: _Analysis, *, margin_days: float | None = None
) -> str:
    """The deck's *Metrics* page (PBIX page 1) — the schedule's ID card.

    Reproduces the landing-page aggregates: activity makeup, status split, completion
    performance, the primary-constraint distribution, and the KPI cards — all from the
    engine outputs already computed for this schedule (no recomputation of the CPM).
    ``margin_days`` (OR-01, ADR-0321) is the effective schedule margin from the caller's
    cached summary tier — rendered "—" when ``None`` (unsolvable or n/a), never 0.

    Panel contract (rank 12 toolbar sweep, ADR-0327): both panels wear the head strip +
    ⛶ ENLARGE + this file's provenance chip. **Neither carries ⤓ EXCEL** — no existing export
    covers what they draw: the ID-card KPI set is not a sheet of any workbook (the analysis
    workbook's summary sheet is a different item list), and the pivots panel mixes ONE covered
    table (completion performance IS an analysis-workbook sheet) with three uncovered ones
    (makeup / status / constraint appear in no export), so a panel-level ⤓ would hand back
    less than the panel draws (the /forecast methodology precedent). No ▦ DATA: the pivots
    ARE tables and the KPI cards' figures all render on the card itself."""
    makeup = compute_activity_makeup(sch)
    constraints = compute_constraint_distribution(sch)
    cpm, comp = analysis.cpm, analysis.completion
    cal = sch.calendar

    # makeup pie -> count/percent table
    total = makeup.total or 1
    makeup_tbl = _count_bar_table(
        ("Task makeup", "% of activities"),
        [
            ("Normal", makeup.normal, 100.0 * makeup.normal / total),
            ("Milestones", makeup.milestones, 100.0 * makeup.milestones / total),
            ("Summaries", makeup.summaries, 100.0 * makeup.summaries / (total + makeup.summaries)),
        ],
    )
    status_tbl = _count_bar_table(
        ("Activity status", "% of activities"),
        [
            ("Complete", makeup.complete, 100.0 * makeup.complete / total),
            ("In progress", makeup.in_progress, 100.0 * makeup.in_progress / total),
            ("Planned", makeup.planned, 100.0 * makeup.planned / total),
        ],
    )
    # completion-performance split (deck "Completion Performance" pie)
    split = [
        ("Completed ahead", comp["completed_ahead"]),
        ("Completed on schedule", comp["completed_on_schedule"]),
        ("Completed behind", comp["completed_behind"]),
    ]
    perf_tbl = _count_bar_table(
        ("Completion performance", "% of measured completions"),
        [(label, r.count, r.value) for label, r in split],
    )
    constraint_tbl = _count_bar_table(
        ("Primary constraint", "% of activities"),
        [(r.constraint_type, r.count, r.percent) for r in constraints],
    )

    # KPI cards (reuse the engine outputs the report already computed)
    starts = [t.start for t in non_summary(sch) if t.start is not None]
    earliest = _mdY(min(starts)) if starts else "—"
    latest_finish = _mdY(offset_to_datetime(sch.project_start, cpm.project_finish, cal))
    critical = sum(
        1
        for t in non_summary(sch)
        if t.percent_complete < 100.0
        and (tm := cpm.timings.get(t.unique_id)) is not None
        and tm.total_float <= 0
    )
    togo_normal = sum(
        1 for t in non_summary(sch) if t.percent_complete < 100.0 and not t.is_milestone
    )
    togo_ms = sum(1 for t in non_summary(sch) if t.percent_complete < 100.0 and t.is_milestone)
    ahead, late = comp["avg_days_ahead"], comp["avg_days_late"]
    stale = comp["elapsed_since_last_finish"]
    cards = _stat_cards(
        [
            ("Earliest start", earliest),
            ("Computed finish", latest_finish),
            ("Data date", _mdY(sch.status_date) if sch.status_date else "—"),
            # OR-01 (ADR-0321): the two ID-card fields the deck page was missing. Values are
            # escaped by _stat_cards itself — no pre-escape here.
            ("Site / Company", sch.company if sch.company else "—"),
            ("Effective margin", f"{margin_days:g} d" if margin_days is not None else "—"),
            ("Activities complete", f"{100.0 * makeup.complete / total:.1f}%"),
            ("Critical (incomplete)", str(critical)),
            ("To-go activities", str(togo_normal)),
            ("To-go milestones", str(togo_ms)),
            ("Avg days ahead", f"{ahead.value:g}" if ahead.population else "—"),
            ("Avg days late", f"{late.value:g}" if late.population else "—"),
            ("% elapsed since last finish", f"{stale.value:g}%" if stale.population else "—"),
        ]
    )
    _pct_done = 100.0 * makeup.complete / total
    _head = (
        f"{critical} incomplete activities sit on the critical path, with {_pct_done:.0f}% of the "
        f"schedule complete."
        if critical
        else f"Nothing incomplete is critical, with {_pct_done:.0f}% of the schedule complete."
    )
    takeaway = _utility_takeaway(
        _head,
        f"{togo_normal} activities and {togo_ms} milestones still to go on "
        f"<b>{_e(sch.name)}</b>; computed finish {latest_finish}. Every figure below is the one the "
        f'<a href="/analysis/{quote(key, safe="")}">full report</a> computes.',
    )
    prov = _prov_chip(sch)
    card_head = _panel_head(
        f"Schedule card &mdash; {_e(sch.name)}", tools=_shell_tools(), prov=prov
    )
    pivots_head = _panel_head(
        "Makeup, status &amp; performance pivots", tools=_shell_tools(), prov=prov
    )
    return f"""{takeaway}
<div class=panel>{card_head}
<p class=muted>The schedule's ID card (the reference deck's <i>Metrics</i> page): activity
makeup, status, completion performance, the primary-constraint distribution, and the
headline KPI cards — every figure computed from this file and verifiable on the
<a href="/analysis/{quote(key, safe="")}">full report</a>.</p>
{cards}</div>
<div class="panel">{pivots_head}
<p class=muted>Four pivots of the same activity population: task makeup, current status,
how completed work landed against baseline, and the primary-constraint distribution &mdash;
each as a count with its share of the population as an inline bar.</p>
<div class=card-cols>
<div>{makeup_tbl}</div><div>{status_tbl}</div>
<div>{perf_tbl}</div><div>{constraint_tbl}</div>
</div></div>
<script src="/static/panelkit.js"></script>"""
