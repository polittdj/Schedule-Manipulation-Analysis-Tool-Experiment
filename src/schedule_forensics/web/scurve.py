"""The /scurve page family: cumulative planned vs actual progress, month by month.

Monolith split, phase 3 slice 16 (ADR-0380), extracted VERBATIM from ``web/app.py``: every
function, docstring and comment moves byte-for-byte, only the module boundary changes.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour (the
``/scurve`` page route, the ``/api/scurve`` chart API and the ``/export/{fmt}/scurve`` export):
SEVEN names in TWO contiguous blocks — the per-chart filter's field/value machinery, the shared
status point, the AI-interpretation panel, the chapter-09 header, the animated page body, and
the chart's JSON payload builder.

**The closure is NOT the census.** The ``_scurve`` prefix finds 6 names / 212 ast lines; the
referrer walk assigns 7 names / 222. The extra name is ``_pair_criteria`` — the cf/cv validator
reachable only from ``/api/scurve``, which no ``_scurve`` prefix sweep can see. The prefix is a
finder; the walk is the definition (ADR-0378).

**No descent.** The walk surfaced six shared names — ``_parse_uid``, ``_parse_uid_list``,
``_parse_track_uids``, ``_MAX_TRACK_UIDS``, ``_CF_QUERY`` and ``_CV_QUERY`` — and every one of
them is pinned to ``app.py``: the first three by routes of OTHER families (/cei, /sra,
/evolution, /trend, /margin, /driving) and by two non-route importers, and the last two because
they are FastAPI ``Query`` singletons that exist only as defaults in a route signature. No
route-signature default has ever lived in an extracted module (zero precedent across 220
extracted names), and a route-only referrer never forces a descent (ADR-0378): routes live in
``create_app``, which imports downward and stays.

**The export route contributes NO movers** — ``export_scurve`` builds its table straight from
``compute_s_curve``, so this family's proven surface is the page plus the chart API.

Layering: ``app`` -> ``scurve`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

import json
from urllib.parse import quote

from schedule_forensics.engine.grouping import (
    MAX_FIELDS,
    Criterion,
    available_fields_union,
    distinct_values,
)
from schedule_forensics.engine.s_curve import SCurve
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.components import _panel_head, _shell_tools


def _scurve_filter_fields(versions: list[Schedule]) -> dict[str, list[str]]:
    """The parent file(s)' filterable fields → their distinct values, for the S-curve's own
    up-to-5-field filter. Capped so the embedded payload stays small on large schedules."""
    out: dict[str, list[str]] = {}
    for fld in available_fields_union(versions):
        values = distinct_values(versions, fld)
        if 0 < len(values) <= 1000:
            out[fld] = values[:300]
    return out


def _pair_criteria(cf: list[str], cv: list[str], versions: list[Schedule]) -> list[Criterion]:
    """Zip the cf/cv query lists into validated (field, value) criteria (<= MAX_FIELDS)."""
    fields = set(available_fields_union(versions))
    out: list[Criterion] = []
    for fld, value in zip(cf, cv, strict=False):
        if fld in fields and value:
            out.append((fld, value))
        if len(out) >= MAX_FIELDS:
            break
    return out


def _scurve_status_point(sc: SCurve) -> tuple[float, float] | None:
    """The latest version's ``(actual %, planned %)`` AT ITS DATA DATE — exactly the pair
    :func:`_scurve_interpretation` already renders in prose. ``None`` when that version carries
    no data date on the axis (a figure is never imputed). ONE source, so the panel takeaway and
    the interpretation below it can never quote different numbers. Reads the computed curves;
    it computes nothing itself."""
    if not sc.versions:
        return None
    latest = sc.versions[-1]
    si = latest.status_index
    if si is None or si >= len(latest.planned):
        return None
    return latest.actual[si], latest.planned[si]


def _scurve_interpretation(sc: SCurve, *, prov: str = "") -> str:
    """A grounded, always-present plain-English read of the S-curve: plan-vs-actual at the data
    date and how that gap is trending across versions — what the trend says about execution."""
    versions = sc.versions
    if not versions:
        return ""
    point = _scurve_status_point(sc)
    if point is None:
        read = (
            "This version has no data date, so plan-vs-actual can't be read at a status point; "
            "the curves show how the planned and scheduled finishes are distributed over time."
        )
    else:
        actual, planned = point
        gap = planned - actual
        if gap > 2:
            verdict = f"running <b>{gap:.0f} points behind plan</b> at the data date"
            health = (
                "Execution is lagging the baseline — less work has completed than was promised "
                "by now, so the forecast finish is at risk unless the team recovers."
            )
        elif gap < -2:
            verdict = f"running <b>{-gap:.0f} points ahead of plan</b> at the data date"
            health = "Execution is ahead of the baseline — work is completing faster than planned."
        else:
            verdict = "tracking <b>on plan</b> at the data date"
            health = "Execution is essentially on the baseline at the status date."
        read = (
            f"As of the latest data date, <b>{actual:.0f}%</b> of the work has finished versus "
            f"<b>{planned:.0f}%</b> planned — {verdict}. {health}"
        )
    gaps = [
        v.planned[v.status_index] - v.actual[v.status_index]
        for v in versions
        if v.status_index is not None and v.status_index < len(v.planned)
    ]
    trend = ""
    if len(gaps) >= 2:
        delta = gaps[-1] - gaps[0]
        if delta > 1:
            trend = (
                f" Across the loaded versions the gap has <b>widened by {delta:.0f} points</b> — "
                "the schedule is falling further behind."
            )
        elif delta < -1:
            trend = (
                f" Across the loaded versions the gap has <b>narrowed by {-delta:.0f} points</b> — "
                "the team is recovering."
            )
        else:
            trend = " The plan-vs-actual gap has held roughly steady across the loaded versions."
    return (
        "<div class=panel>"
        + _panel_head("AI interpretation", tools=_shell_tools(), prov=prov)
        + f"<p>{read}{trend}</p>"
        + "<p class=muted><b>Auto-generated</b> from the S-curve's computed values &mdash; verify "
        'against the chart. Enable a local model in <a href="/settings">AI Settings</a> for a '
        "fuller, model-written read.</p></div>"
    )


def _scurve_header(sc: SCurve) -> str:
    """Chapter 09's story header for /scurve (Mission Ops rank 9): takeaway h1 + muted lede.

    The chapter kicker rides the spine. Both figures quoted here are ones the page already
    renders — the plan-vs-actual pair at the data date (the same
    :func:`_scurve_status_point` the AI-interpretation panel prints) and the version count."""
    if not sc.versions:
        return ""
    latest = sc.versions[-1]
    point = _scurve_status_point(sc)
    n = len(sc.versions)
    files = f"{n} version" + ("" if n == 1 else "s")
    if point is None:
        takeaway = (
            f"{files} of cumulative progress on one fixed 0-100% scale; "
            f"{latest.label} records no data date, so no status point is read."
        )
    else:
        actual, planned = point
        takeaway = (
            f"At {latest.label}'s data date {actual:.0f}% of the work has finished against "
            f"{planned:.0f}% planned, over {files}."
        )
    return (
        f'<h1 class="page-takeaway" data-no-i18n>{_e(takeaway)}</h1>'
        '<p class="page-lede">How much of the work has actually completed against how much the '
        "baseline promised, month by month. Step or play through the loaded files to watch the "
        "actual curve climb — and lag — against the plan.</p>"
    )


def _scurve_body(
    sc: SCurve,
    fields: dict[str, list[str]],
    track_uids: list[int] | None = None,
    *,
    prov: str = "",
) -> str:
    """The animated S-curve view: cumulative planned vs actual/forecast progress per version,
    with a per-chart up-to-5-field filter over the parent file's fields.

    Panel contract (Mission Ops rank 9): headline strip + ⤓ EXCEL (the EXISTING
    ``/export/xlsx/scurve`` endpoint, which exports exactly this curve set) + ⛶ ENLARGE +
    provenance chip + an ``.sf-take``. No ▦ DATA — this visual ships no drawer table (the
    /evm precedent), and unlike /curves and /trend this chart owns no pre-existing
    ⛶ / ▦ strip, so the tools sit in the head where the merged contract puts them."""
    # escape "<" so a field value can never break out of the inline <script> embed
    fields_json = json.dumps(fields).replace("<", "\\u003c")
    track_txt = ", ".join(str(u) for u in (track_uids or []))
    export_url = "/export/xlsx/scurve" + (f"?uids={quote(track_txt)}" if track_txt else "")
    head = _panel_head(
        "S-Curve &mdash; cumulative progress",
        tools=_shell_tools(
            export_title="Export the cumulative planned vs actual curves — opens in Excel"
        ),
        prov=prov,
    )
    point = _scurve_status_point(sc)
    latest = sc.versions[-1] if sc.versions else None
    if latest is None:
        take = "No version carries progress to plot."
    elif point is None:
        take = (
            f"{latest.label} records no data date, so plan-vs-actual is not read at a status "
            f"point; the curves cover {latest.activities} activities."
        )
    else:
        take = (
            f"{latest.label}: {point[0]:.0f}% finished against {point[1]:.0f}% planned at its "
            f"data date, over {latest.activities} activities."
        )
    return f"""
<div class=panel data-export="{_e(export_url)}">{head}
<p class=sf-take data-no-i18n>{_e(take)}</p>
<p class=muted>Each version's cumulative progress on a fixed 0&ndash;100% scale: <b>gold</b> =
planned (share of activities the baseline had finishing by each month), <b>blue</b> =
actual / forecast (share whose actual or scheduled finish lands by each month). The dashed
line is that version's data date &mdash; actuals to its left, forecast to its right; the blue
curve sitting below the gold at the data date is work behind plan. Step through the versions
or press Auto-play to watch the actual curve climb (and lag) over time. <b>Track UIDs</b>
(up to 20) marks those activities' finish months on every animated frame.</p>
<div class=viz-controls id=scurveFilterBar><span class=muted>Filter this chart by up to
{MAX_FIELDS} field(s) of the parent file:</span> <span id=scurveFilter></span>
<form method=get action=/scurve style="display:inline">
<label>Track UIDs <input id=scurveTrack name=uids data-no-i18n value="{_e(track_txt)}"
placeholder="e.g. 155, 187, 411" size=28
title="Up to 20 UniqueIDs (comma/space separated) marked on every frame of the animation"></label>
<button type=submit>Track</button></form></div>
<div class=viz-controls>
<label id=scurveVersionWrap style="display:none">File <select id=scurveVersion data-no-i18n>
<option value=all>All files (chronological)</option>
</select></label>
<button id=prevScurve type=button>&#9664; Prev</button>
<span id=scurveLabel class=muted></span>
<button id=nextScurve type=button>Next &#9654;</button>
<button id=scurvePlay type=button>&#9654; Auto-play</button>
<label>Time scale <select id=scurveGran data-no-i18n>
<option value=month selected>Months (year / quarter / month)</option>
<option value=quarter>Quarters (year / quarter)</option>
<option value=year>Years</option>
</select></label>
</div>
<div id=scurveChart class=chart-host></div></div>
{_scurve_interpretation(sc, prov=prov)}
<script id=sfScurveFields type="application/json">{fields_json}</script>
<script src="/static/timeaxis.js"></script>
<script src="/static/scurve.js"></script>
<script src="/static/panelkit.js"></script>"""


def _scurve_data(sc: SCurve) -> dict[str, object]:
    return {
        "months": list(sc.month_labels),
        "versions": [
            {
                "label": v.label,
                "status_index": v.status_index,
                "status_date": v.status_date,
                "activities": v.activities,
                "planned": list(v.planned),
                "actual": list(v.actual),
                "tracked": [
                    {
                        "uid": t.uid,
                        "name": t.name,
                        "finish_index": t.finish_index,
                        "baseline_index": t.baseline_index,
                        "pct": t.percent_complete,
                    }
                    for t in v.tracked
                ],
            }
            for v in sc.versions
        ],
    }
