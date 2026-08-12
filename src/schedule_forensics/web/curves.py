"""The /curves page family: chapter 05's three monthly delivery curves.

Monolith split, phase 4 slice 24 (ADR-0389), extracted VERBATIM from ``web/app.py``: every
definition moves byte-for-byte -- docstrings, comments and HTML f-strings unchanged -- and only
the module boundary is new.

The seam is the AST transitive closure of the family's entry points, seeded on the EXACT route
list ``/curves`` + ``/api/curves`` + ``/export/{fmt}/curves``. Three names, ZERO descents.

Layering: ``app`` -> ``curves`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

from schedule_forensics.engine.month_curves import MonthCurves
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.components import _panel_head


def _curves_header(curves: MonthCurves) -> str:
    """Chapter 05's story header for /curves (Mission Ops rank 9): the takeaway h1 + muted lede.

    The chapter kicker is injected by the spine (:func:`_chapter_kicker`), so only the headline
    and lede are built here. Every figure is one the page already renders — the loaded version
    count, their labels/data dates, and the shared month axis the three charts are drawn on.
    No engine call, no new arithmetic, and no adjective the engine did not assert."""
    versions = curves.versions
    if not versions:
        return ""
    n = len(versions)
    months = curves.month_labels
    latest = versions[-1]
    dd = f" (data date {latest.status_date})" if latest.status_date else ""
    span = f"{months[0]} → {months[-1]}" if months else "—"
    files = f"{n} version" + ("" if n == 1 else "s")
    takeaway = (
        f"{files} of finish and start months on one shared {len(months)}-month axis "
        f"({span}); the newest is {latest.label}{dd}."
    )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        '<p class="page-lede">Where finishes were promised against where they actually land, '
        "month by month. Step or play through the loaded files to watch the finish and start "
        "curves slide along a month axis held fixed across every frame.</p>"
    )


def _curves_body(curves: MonthCurves, *, prov: str = "") -> str:
    """The Finish & Slippage page (PBIX pages 6, 7, 12): three monthly-curve charts.

    Finishes (actual vs baseline, latest version), DATA Date Finishes (per-version
    actual-finish curves overlaid — the bow wave's line sibling), and Slippage (the
    per-version start and finish curves). All client-side SVG over /api/curves.

    Panel contract (Mission Ops rank 9): each chart panel carries the headline strip +
    provenance chip + an ``.sf-take`` line, and the panel-level ``data-export`` points at the
    EXISTING ``/export/xlsx/curves`` endpoint that serves exactly these curves. The three-glyph
    tool strip is NOT duplicated in the head here: curves.js already builds this page's action
    strip next to each chart (⛶ ENLARGE → the viewport overlay, ▦ DATA → that chart's data
    table) and that strip is normalized to the contract vocabulary in place — relabel, never
    rebuild — with ⤓ EXCEL added there so panelkit.js follows the panel's data-export."""
    n_versions = len(curves.versions)
    latest = curves.versions[-1].label if curves.versions else ""
    latest_dd = curves.versions[-1].status_date if curves.versions else None
    oldest = curves.versions[0].label if curves.versions else ""
    months = curves.month_labels
    n_months = len(months)
    # a literal em dash, never the em-dash ENTITY as a value: test_presentation_fixes pins that
    # sentinel because an entity string here would double-escape the next time it meets _e()
    span = f"{_e(months[0])} &rarr; {_e(months[-1])}" if months else "—"
    files = f"{n_versions} file" + ("" if n_versions == 1 else "s")
    dd_txt = f" (data date {_e(latest_dd)})" if latest_dd else ""

    def take(text: str) -> str:
        return f"<p class=sf-take data-no-i18n>{text}</p>"

    # every figure below is one the page ALREADY renders: the version labels and data dates the
    # frame captions name, and the shared month axis the charts are drawn on. No new arithmetic.
    finishes_take = take(
        f"Latest version <b>{_e(latest)}</b>{dd_txt}: baselined finish months against actual "
        f"or scheduled finish months, on the shared {n_months}-month axis ({span})."
    )
    datadate_take = take(
        f"{files} on one fixed {n_months}-month axis ({span}), oldest first by data date "
        f"&mdash; <b>{_e(oldest)}</b> through <b>{_e(latest)}</b>, one file per frame."
    )
    slippage_take = take(
        f"Start and finish curves for {files} on the same {n_months}-month axis ({span}); "
        f"the frame label names the file shown, newest being <b>{_e(latest)}</b>."
    )
    multi = (
        ""
        if n_versions >= 2
        else "<p class=muted>Load more than one version (monthly snapshots, by data date) to "
        "see the per-version curve overlays — with a single version the curves show that "
        "version alone.</p>"
    )
    return f"""
<div class=viz-controls><label><input type=checkbox id=curvesHideDone> hide 100% complete</label>
<span class=muted>&mdash; show only the remaining / forecast work on every curve below.</span>
<label style="margin-left:1em">Time scale <select id=curvesGran data-no-i18n>
<option value=month selected>Months (year / quarter / month)</option>
<option value=quarter>Quarters (year / quarter)</option>
<option value=year>Years</option>
</select></label></div>
<div class=panel data-export="/export/xlsx/curves">{
        _panel_head("Finishes &mdash; actual vs baseline by month", prov=prov)
    }
{finishes_take}
<p class=muted>For the latest version (<b>{_e(latest)}</b>): activities counted by the month
they were <b>baselined</b> to finish (gold) against the month they <b>actually</b> finished
or are now scheduled to (blue). Where the blue curve sits to the right of the gold is slipped
finish work, read month by month.</p>
<div id=finishesChart class=chart-host></div></div>
<div class=panel data-export="/export/xlsx/curves">{
        _panel_head("DATA Date Finishes &mdash; actual-finish curve per version", prov=prov)
    }
{datadate_take}
<p class=muted>One file per frame on a month axis held fixed across every file (ADR-0150):
step or play through the loaded versions (oldest first by data date) and watch the finish
curve slide right &mdash; the bow wave of slipped finishes. The frame label names the file
you are looking at.</p>{multi}
<div id=dataDateChart class=chart-host></div></div>
<div class=panel data-export="/export/xlsx/curves">{
        _panel_head("Slippage &mdash; start &amp; finish curves per version", prov=prov)
    }
{slippage_take}
<p class=muted>One file per frame (fixed month axis, ADR-0150): activities counted by their
<b>start</b> month (solid) and <b>finish</b> month (dashed). Step or play through the versions
&mdash; the whole profile sliding right is the slippage signature. The frame label names the
file shown.</p>
<div id=slippageChart class=chart-host></div></div>
<script src="/static/timeaxis.js"></script>
<script src="/static/curves.js"></script>
<script src="/static/panelkit.js"></script>"""


def _curves_data(curves: MonthCurves) -> dict[str, object]:
    """JSON for the finish/slippage curves: shared month axis + per-version count series."""
    return {
        "months": list(curves.month_labels),
        "versions": [
            {
                "label": v.label,
                "status_date": v.status_date,
                "status_index": v.status_index,
                "baseline_finishes": list(v.baseline_finishes),
                "actual_finishes": list(v.actual_finishes),
                "baseline_starts": list(v.baseline_starts),
                "actual_starts": list(v.actual_starts),
            }
            for v in curves.versions
        ],
    }
