"""The /wbs page family: the optional-number cell, the two WBS pivots, and the chart JSON.

Monolith split, phase 4 slice 21 (ADR-0386), extracted VERBATIM from ``web/app.py``: every
function moves byte-for-byte — docstrings, comments and HTML f-strings unchanged — and only the
module boundary is new.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour over
all THREE routes — ``/wbs/{name}``, ``/api/wbs/{name}`` and ``/export/{fmt}/wbs/{name}``.
THREE names in ONE contiguous block (app.py 7294-7407).

**The prefix misses a member.** A ``wbs`` prefix census finds 2 names / 107 ast lines; the
referrer walk finds **3 names / 110** — ``_num`` carries no ``wbs`` prefix at all. It is a
three-line formatter, and it is a member: its only referrers are inside ``_wbs_body``, which a
bare-NAME sweep confirms independently of the walk. The prefix is a finder; the walk is the
definition (ADR-0378).

**The export route contributes NO movers, measured.** ``export_wbs``'s app-level callee set is
empty — it re-derives its own pivots through ``reports/tables.py::wbs_breakdown_tables`` rather
than calling ``_wbs_body`` or ``_wbs_data``. That is what licenses a page-only probe anchor here;
ADR-0378's trap (a page-only anchor understates an export-feeding member) is checked off by
measurement, not waved past.

**Zero descent, zero shared names, zero owned constants.** Every other name the three members
touch resolves to an *import*: ``_e``, ``_utility_takeaway`` (chrome); ``_panel_head``,
``_shell_tools`` (components); ``WBSGroup`` (engine.metrics); ``quote`` (stdlib). The free-name
pass finds no module-level assignment owned by the block.

Layering: ``app`` -> ``wbs`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

from urllib.parse import quote

from schedule_forensics.engine.metrics import WBSGroup
from schedule_forensics.web.chrome import _e, _utility_takeaway
from schedule_forensics.web.components import _panel_head, _shell_tools


def _num(value: float | None, *, suffix: str = "") -> str:
    """Render an optional number for a table cell — em-dash when absent (never a fake 0)."""
    return f"{value:g}{suffix}" if value is not None else "—"


def _wbs_body(key: str, groups: tuple[WBSGroup, ...], *, prov: str = "") -> str:
    """The deck's *Completion Metrics* (PBIX 8) + *SPI and Earned Schedule* (PBIX 9) pages.

    Two WBS pivots over one version: a completion-by-WBS table (counts, %, ahead/on/behind,
    duration ratio) and the SPI(t)/Earned-Schedule-by-WBS combo chart + table. Grouped by
    the top-level WBS segment; every figure verifiable on the full report.

    Panel contract (rank 12 toolbar sweep, ADR-0327): both panels wear the head strip + tools
    + this file's provenance chip (``prov``), with ⤓ EXCEL on both pointing at the EXISTING
    WBS workbook (/export/xlsx/wbs/{key}) — its two sheets are EXACTLY these two pivots
    (reports/tables.py::wbs_breakdown_tables). No ▦ DATA: the completion pivot IS a table,
    and the combo chart's numbers are the ES table rendered directly beneath it in the same
    panel (the home-shell precedent). The no-groups branch renders a bare notice with NO
    controls — the ROUTE appends the panelkit include, gated on a control actually being in
    the assembled body (a focus panel above this body carries controls of its own)."""
    if not groups:
        return (
            "<div class=panel><h2>WBS breakdown</h2><p class=muted>This schedule has no "
            "schedulable activities to break down by WBS.</p></div>"
        )
    _tot = sum(g.total for g in groups)
    _done = sum(g.completed for g in groups)
    _behind = sum(g.completed_behind for g in groups)
    _pct = (100.0 * _done / _tot) if _tot else 0.0
    # pair the value out so the None-narrowing survives into the key (mypy cannot narrow a lambda)
    _scored_spi = [(g.wbs, g.spi_t) for g in groups if g.spi_t is not None]
    _worst = min(_scored_spi, key=lambda pair: pair[1], default=None)
    _head = (
        f"{_behind} completed activities finished behind baseline across {len(groups)} WBS groups."
        if _behind
        else f"No completed activity finished behind baseline across {len(groups)} WBS groups."
    )
    takeaway = _utility_takeaway(
        _head,
        f"{_done} of {_tot} activities complete ({_pct:.0f}%). Weakest group by SPI(t): "
        + (
            f"<b>{_e(_worst[0])}</b> at {_worst[1]:g}."
            if _worst is not None
            else "&mdash; (no group has a computable SPI(t))."
        ),
    )
    completion_rows = "".join(
        f"<tr><th scope=col>{_e(g.wbs)}</th><td>{g.total}</td><td>{g.completed}</td>"
        f"<td>{g.not_completed}</td><td>{g.percent_complete:g}%</td>"
        f"<td>{g.completed_ahead}</td><td>{g.completed_on_schedule}</td><td>{g.completed_behind}</td>"
        f"<td>{_num(g.avg_days_ahead)}</td><td>{_num(g.avg_days_late)}</td>"
        f"<td>{_num(g.avg_completion_variance)}</td>"
        f"<td>{g.longer_than_planned}</td><td>{g.shorter_than_planned}</td>"
        f"<td>{_num(g.duration_ratio_min)}</td><td>{_num(g.duration_ratio_avg)}</td>"
        f"<td>{_num(g.duration_ratio_max)}</td></tr>"
        for g in groups
    )
    es_rows = "".join(
        f"<tr><th scope=col>{_e(g.wbs)}</th><td>{_num(g.spi_t)}</td>"
        f"<td>{_num(g.earned_schedule_days)}</td><td>{_num(g.actual_time_days)}</td>"
        f"<td>{g.completed}/{g.total}</td></tr>"
        for g in groups
    )
    wbs_export = f"/export/xlsx/wbs/{quote(key, safe='')}"
    wbs_tools = _shell_tools(
        export_title=(
            "Export the WBS breakdown workbook (completion + SPI(t)/Earned-Schedule sheets) — "
            "opens in Excel"
        )
    )
    completion_head = _panel_head(
        f"Completion metrics by WBS &mdash; {len(groups)} groups", tools=wbs_tools, prov=prov
    )
    es_head = _panel_head("SPI(t) &amp; Earned Schedule by WBS", tools=wbs_tools, prov=prov)
    return f"""{takeaway}
<div class=panel data-export="{wbs_export}">{completion_head}
<p class=muted>The reference deck's <i>Completion Metrics</i> pivot (PBIX page 8), grouped by
the top-level WBS segment: counts and completion, the ahead / on-schedule / behind split with
average calendar days, and the actual-vs-baseline duration ratio. Every figure is verifiable
on the <a href="/analysis/{quote(key, safe="")}">full report</a>.</p>
<div style="overflow-x:auto"><table class=wbs-table>
<tr><th scope=col>WBS</th><th scope=col>Total</th><th scope=col>Done</th><th scope=col>To go</th><th scope=col>% comp</th>
<th scope=col>Ahead</th><th scope=col>On sched</th><th scope=col>Behind</th>
<th scope=col>Avg ahead</th><th scope=col>Avg late</th><th scope=col>Avg var</th>
<th scope=col>Longer</th><th scope=col>Shorter</th><th scope=col>Dur min</th><th scope=col>Dur avg</th><th scope=col>Dur max</th></tr>
{completion_rows}</table></div></div>
<div class=panel data-export="{wbs_export}">{es_head}
<p class=muted>The deck's <i>SPI and Earned Schedule</i> pivot + combo (PBIX page 9). Per WBS
group: the count-based <b>SPI(t)</b> (Earned Schedule &divide; Actual Time; &lt; 1 = behind),
the <b>Earned Schedule</b> and <b>Actual Time</b> in working days. A group with no completions
or no baseline finishes reads &mdash; (never a fabricated value).</p>
<div id=wbsChart class=chart-host></div>
<table class=wbs-table><tr><th scope=col>WBS</th><th scope=col>SPI(t)</th><th scope=col>Earned schedule (wd)</th>
<th scope=col>Actual time (wd)</th><th scope=col>Completed</th></tr>{es_rows}</table></div>
<script src="/static/wbs.js"></script>"""


def _wbs_data(groups: tuple[WBSGroup, ...]) -> dict[str, object]:
    """JSON for the SPI/Earned-Schedule combo chart: per-WBS SPI(t) + ES/AT days."""
    return {
        "groups": [
            {
                "wbs": g.wbs,
                "total": g.total,
                "completed": g.completed,
                "percent_complete": g.percent_complete,
                "spi_t": g.spi_t,
                "earned_schedule_days": g.earned_schedule_days,
                "actual_time_days": g.actual_time_days,
                "uids": list(g.uids),  # the group's activities, for the SPI-bar drill
            }
            for g in groups
        ],
    }
