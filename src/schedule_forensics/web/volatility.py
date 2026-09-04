"""The /volatility page family: critical-path membership churn across versions.

Monolith split, phase 4 slice 24 (ADR-0389), extracted VERBATIM from ``web/app.py``: both
definitions move byte-for-byte -- docstrings, comments and HTML f-strings unchanged -- and only
the module boundary is new.

The seam is the AST transitive closure of the family's entry points, seeded on the EXACT route
list ``/volatility`` + ``/export/{fmt}/volatility``. Two names, ZERO descents.

Layering: ``app`` -> ``volatility`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

import json
from typing import Any, cast

from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.model.schedule import Schedule

# ADR-0427 moved `_volatility_data` DOWN into `components.py`: `evolution.py` needs it for the
# Chapter-04 stability band, and evolution sits BELOW volatility in the view layer's order, so
# importing it from here would have been an upward (circular) import. ADR-0351's rule: a name a
# second extracted module needs descends to the shared kernel.
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.components import (
    _panel_head,
    _series_prov_chip,
    _volatility_data,
)


def _volatility_body(schedules: list[Schedule], cpms: list[CPMResult]) -> str:
    """The CP Volatility page shell: intro framed to GAO/DCMA best practice, the master
    stepper, ten chart mounts, the scoreboard, and the embedded dataset volatility.js reads.

    Panel contract (Mission Ops rank 11, ADR-0298 vocabulary): the masthead and the scoreboard
    wear :func:`_panel_head` + a :func:`_series_prov_chip` chip + one ``.sf-take``; each of the
    ten ``.tile.panel`` mosaic tiles wears the mission-wall tile shape ``_performance_body``
    established — tools strip inside the existing ``.tile-head``, ``.tile-prov`` chip, one
    ``.sf-take`` under the chart. Four deliberate omissions, each of which would otherwise ship
    an inert or dishonest control:

    * **no ▦ DATA on any tile** — these tiles carry no ``.sf-drawer`` and no ``.sr-only`` table
      (measured: 0 of each on this route), so the glyph would reveal nothing;
    * **no tools on the masthead** — it holds ZERO visuals and ZERO tables (it is a masthead,
      not a panel of data), and it ALREADY owns this page's Excel control (the
      ``⇩ Excel (scoreboard)`` anchor pointing at the very URL ⤓ would follow — ADR-0298's
      one-convention law);
    * **no tools on the scoreboard** — same anchor, same URL, one table;
    * **no per-version figure in any tile take** — the master stepper (volatility.js ``cursor``)
      re-draws the churn/composition/heatmap/ribbon visuals at a DIFFERENT version on every
      tick, so a server-rendered per-version number would become false on the first ▶. The tile
      takes are structural; the two figure-bearing takes (masthead, scoreboard) quote only
      whole-series values the visuals below them already print verbatim, and the provenance is
      :func:`_series_prov_chip` (a first→last RANGE that holds at every frame).

    The ten ``<h3 class=viz-hint>`` explainers are deliberately NOT routed through
    :func:`_panel_head`: that helper emits an ``<h2>`` and would drop the ``data-sf-hint``
    explainer this page's tiles are built around."""
    data = _volatility_data(schedules, cpms)
    blob = json.dumps(data).replace("<", "\\u003c")
    # ── The panel contract for this page. Every figure a take quotes is read off the SAME
    # `data` dict the embedded #volData blob carries (no second engine call), so the takes and
    # the visuals drawn from that blob can never disagree.
    versions = cast(list[dict[str, object]], data["versions"])
    tasks = cast(list[dict[str, Any]], data["tasks"])
    stability = cast("float | None", data["stability"])
    # The gauge prints `Math.round(s * 100) + "%"` (volatility.js) — half-UP. Python's round()
    # is half-to-even, so it is spelled out here rather than borrowed; otherwise a stability of
    # x.xx5 would let the take and the dial it describes read differently.
    stab_txt = "—" if stability is None else f"{int(stability * 100 + 0.5)}%"
    full_tenure = sum(1 for t in tasks if t["tenure"] == len(versions))
    prov = _series_prov_chip(schedules)
    head = _panel_head(
        "Critical-Path Volatility &mdash; membership churn across versions", prov=prov
    )
    intro_take = (
        f"<p class=sf-take data-no-i18n>{len(tasks)} activities were ever on the critical path "
        f"across the {len(versions)} loaded versions; mean similarity between consecutive paths "
        f"is {stab_txt}.</p>"
    )
    board_head = _panel_head("Volatility scoreboard", prov=prov)
    board_take = (
        f"<p class=sf-take data-no-i18n>Every one of the {len(tasks)} activities that ever "
        f"reached the critical path is listed here; {full_tenure} held it in all "
        f"{len(versions)} loaded versions.</p>"
    )
    # One ⤓ destination for all ten tiles: the workbook is the membership matrix the visuals are
    # drawn from, NOT a per-visual series — the hover text says exactly that and no more.
    tile_export = ' data-export="/export/xlsx/volatility"'
    tile_prov = f"<div class=tile-prov>{prov}</div>"
    tile_tools = (
        '<span class="tile-actions sf-tools" data-noprint=1>'
        "<button type=button data-sf-excel "
        'title="Export the critical-path membership matrix these visuals are drawn from '
        '&mdash; opens in Excel" '
        'aria-label="Export this visual&#39;s data to Excel">⤓ EXCEL</button>'
        "<button type=button data-sf-big aria-pressed=false "
        'title="Enlarge / shrink this visual" '
        'aria-label="Enlarge this visual">⛶ ENLARGE</button></span>'
    )
    # ── Claude Design layout (operator 2026-09-02: "convert this page to that design but don't
    # modify any of the functionality"): the prototype's five numbered panels — ① Stability
    # signal · ② Flow of the path · ③ Membership matrix · ④ Transition ribbons · ⑤ the scoreboard
    # as the ▦ DATA drawer — under a masthead and ONE master cursor strip (Prev / Play / Next /
    # a chip per version / the "Vn · DD" pill). Every one of the ten visuals keeps its tile,
    # ids, hint, toolbar and take VERBATIM inside the panel it belongs to (the census counts ten
    # chart frames here and the JS finds every host by id); the stepper ids are unchanged and the
    # chips drive the same stepTo(). The prototype's ⑤ is the evolution what-if ledger — that
    # lives on /evolution; here ⑤ is the scoreboard the design folds under ▦ DATA.
    headline = (
        "Awaiting a second version &mdash; path stability needs two to compare."
        if stability is None
        else f"Only {stab_txt} of the critical path survives each update."
        if stability < 0.7
        else f"{stab_txt} of the critical path carries over each update &mdash; a settled chain."
    )
    band_cls, band_txt = _stability_band(stability)
    chips = "".join(
        f'<button type=button class="cd-chip{" on" if i == len(versions) - 1 else ""}" '
        f'data-idx="{i}" data-no-i18n title="{_e(str(v.get("label", "")))}">v{i}</button>'
        for i, v in enumerate(versions)
    )
    kpi = (
        f"<div class=vol-kpi id=volKpi data-no-i18n><div class=vol-kpi-value>{stab_txt}</div>"
        f"<div class=vol-kpi-label>MEAN CARRY-OVER &middot; ALL VERSIONS</div>"
        f'<div class="vol-band {band_cls}">{band_txt}</div></div>'
    )
    ph = _vol_panel_open
    ph1 = ph(
        1,
        "&#9312; Stability signal",
        "Mean carry-over between consecutive paths, and the per-pair churn timeline. Bands are display guidance, not a published threshold &mdash; the caveat ships on the chart face.",
    )
    ph2 = ph(
        2,
        "&#9313; Flow of the path",
        "Joined &uarr; and left &darr; per update, and each version&rsquo;s composition &mdash; the share carried over against the share newly joined.",
    )
    ph3 = ph(
        3,
        "&#9314; Membership matrix",
        "Who was on the path, version by version &mdash; the matrix, then tenure, the jumpers, the dwell distribution and the on-path strips that read it from four angles. Click any row for its Task Information.",
    )
    ph4 = ph(
        4,
        "&#9315; Transition ribbons",
        "The stepper&rsquo;s current pair as proportional ribbons: what stayed against what joined and what left. A thin carried band means the path is being rebuilt each update, not held.",
    )
    ph5 = ph(
        5,
        "&#9316; The scoreboard &mdash; every activity that ever held the path",
        'The data behind every panel: versions on path, longest unbroken streak and on/off flips per activity (click a column header to sort). The what-if ledger of edits that moved the chain is <a href="/evolution">Chapter 04&rsquo;s Evolution view</a>.',
        wide=True,
    )
    return f"""
<div class="panel vol-masthead">{head}
<h1 class=vol-headline data-no-i18n>{headline}</h1>
{intro_take}
<p class=muted>The critical path should be <b>stable</b>: GAO's Schedule Assessment Guide (Best
Practice 6 — maintain a valid critical path) and the DCMA 14-point construct (the critical-path
test and CPLI) both treat an erratic controlling chain as a schedule-health failure. A path that
churns member activities version over version means the network's logic is being rewired between
updates — either real replanning that deserves a change log, or edits that quietly move the
controlling chain away from slipping work. The ten visuals below answer two questions from the
loaded files: <b>which activities stayed on the critical path longest</b>, and <b>which jumped
off and on over time</b> (every figure derives from the same effective-critical sets the other
pages use; nothing is fabricated).</p>
<div class="viz-controls cd-cursor" id=volCursor>
<button id=volPrev type=button>&#9664; Prev</button>
<button id=volPlay type=button class=cd-play>&#9654; Play</button>
<button id=volNext type=button>Next &#9654;</button>
<span class=cd-chips>{chips}</span>
<span id=volLabel class="muted cd-pill" data-no-i18n></span>
</div></div>
<div id=volGrid class=vol-layout>
<div class="vol-row vol-row-1">
{ph1}<div class=vol-signal>{kpi}<div class="mosaic vol-tiles">
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the overall stability index — the average Jaccard similarity of consecutive critical paths (100% = the same path every update).\n\nHOW TO READ: GAO/DCMA expect a largely stable controlling chain; below ~70% the network is being rewired between updates.\n\nDECIDE: whether to ask for the change log before accepting the latest update.">Stability gauge</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=volGauge></div><p class=sf-take data-no-i18n>The mean similarity between consecutive critical paths on a dial whose bands are operator-set display guidance, not a published threshold.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: path similarity between each consecutive pair of versions (Jaccard %).\n\nHOW TO READ: dips are the updates where the controlling chain was rewired — cross-reference those updates with the Schedule Integrity findings.\n\nDECIDE: which update to interrogate for logic/duration edits.">Churn timeline (Jaccard %)</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=volChurn></div><p class=sf-take data-no-i18n>Path similarity for each consecutive pair of versions, so the updates where the controlling chain was rewired read as dips.</p></section>
</div></div></section>
{ph2}<div class="mosaic vol-tiles">
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: per update — how many activities stayed on, joined, and left the critical path.\n\nHOW TO READ: joined bars up, left bars down; a healthy schedule shows small bars (progress-driven turnover), not tall ones.\n\nDECIDE: which update churned the most members.">Entry / exit waterfall</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=volFlow></div><p class=sf-take data-no-i18n>Per update, how many activities joined the critical path (above the axis) against how many left it (below).</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the composition of each version's path — the share carried over vs newly joined.\n\nHOW TO READ: a mostly-'stayed' area is a settled plan; a growing 'entered' share is instability.\n\nDECIDE: whether the path is converging or churning over time.">Path composition (stayed vs entered)</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=volArea></div><p class=sf-take data-no-i18n>Each version's critical-path size split into the members carried over from the prior version and those newly joined.</p></section>
</div></section>
</div>
<div class="vol-row vol-row-2">
{ph3}<div class="mosaic vol-tiles vol-matrix">
<section class="tile panel tile-wide"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the presence matrix — one row per activity ever on the critical path, one column per version; a filled cell = on the path that version. The stepper highlights the animated version.\n\nHOW TO READ: long unbroken rows are the stable backbone; gap-toothed rows are the jumpers.\n\nDECIDE: which rows deserve a 'why did this change?' interrogation.">Membership heatmap</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=volHeatmap></div><p class=sf-take data-no-i18n>Membership as a matrix &mdash; activities down the side, most-volatile first; versions across the top; a filled cell marks a version the activity was on the critical path.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the activities that spent the most versions on the critical path.\n\nHOW TO READ: these carry the schedule — the true backbone of the finish date.\n\nDECIDE: where sustained management attention belongs.">Tenure leaderboard</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=volTenure></div><p class=sf-take data-no-i18n>The activities that held the critical path the longest, ranked by how many versions they spent on it.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the biggest jumpers — activities ranked by on/off flips.\n\nHOW TO READ: an activity that repeatedly leaves and rejoins the controlling chain usually marks logic being toggled around it.\n\nDECIDE: exactly which activities' predecessors/durations to audit across updates.">Jumper leaderboard (on/off flips)</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=volJumpers></div><p class=sf-take data-no-i18n>Activities ranked by how often they left the critical path and rejoined it; when nothing changed more than once, the panel says so in words instead of drawing a bar.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: how long activities typically stay on the path (distribution of versions-on-path).\n\nHOW TO READ: a healthy path skews long (stable membership); a spike at 1 version means most members blink on and off.\n\nDECIDE: whether churn is a few bad actors or systemic.">Dwell histogram</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=volDwell></div><p class=sf-take data-no-i18n>How many activities spent one version on the critical path, how many spent two, and so on across the loaded versions.</p></section>
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: on-path intervals for the top jumpers as timeline strips (filled = on the path).\n\nHOW TO READ: aligned breaks across many strips point at ONE update that rewired the chain; scattered breaks are activity-level toggling.\n\nDECIDE: whether to investigate an update or an activity.">Jumper timelines</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=volStrips></div><p class=sf-take data-no-i18n>On-path intervals as one strip per activity &mdash; the top jumpers, or the longest-tenured members when nothing has jumped &mdash; so breaks that line up across strips point at a single update.</p></section>
</div></section>
{ph4}<div class="mosaic vol-tiles">
<section class="tile panel"{tile_export}><div class=tile-head><h3 class=viz-hint data-sf-hint="WHAT: the animated stayed/entered/left transition between the stepper's current pair of versions, as proportional ribbons.\n\nHOW TO READ: a thick 'stayed' ribbon is continuity; thick 'entered'/'left' ribbons mark a rewired update.\n\nDECIDE: step through the pairs to find the update that moved the chain.">Transition flow (animated)</h3>{tile_tools}</div>{tile_prov}<div class=chart-host id=volRibbon></div><p class=sf-take data-no-i18n>The stepper's current pair of versions as proportional ribbons: what stayed on the critical path against what joined and what left.</p></section>
</div></section>
</div>
{ph5}<div class=panel>{board_head}{board_take}
<details class=vol-data open><summary class=vol-data-toggle>&#9638; DATA &middot; scoreboard <a class=btn-link href="/export/xlsx/volatility">&#11015; Excel</a></summary>
<p class=muted>Every activity that was ever on the critical path — versions on path, longest
unbroken streak, and on/off flips (click a column header to sort; the Excel export carries the
full membership vector).</p>
<div id=volTable></div></details></div></section>
</div>
<script type="application/json" id=volData>{blob}</script>
<script defer src="/static/volatility.js"></script>
<script src="/static/panelkit.js"></script>"""


def _vol_panel_open(num: int, title: str, caption: str, *, wide: bool = False) -> str:
    """The opening of one numbered design panel (closed by the template with ``</section>``)."""
    cls = "vol-block vol-wide" if wide else "vol-block"
    return (
        f'<section class="{cls}" data-vol-panel="{num}"><div class=vol-panel-head><h2>{title}</h2>'
        f"</div><p class=vol-caption>{caption}</p>"
    )


def _stability_band(stability: float | None) -> tuple[str, str]:
    """The design's band pill: STABLE >=70 % · WATCH 50-70 % · CHURN <50 % · awaiting.
    Display guidance (the page says so), never a published threshold."""
    if stability is None:
        return "vol-band-na", "AWAITING 2+ VERSIONS"
    if stability >= 0.7:
        return "vol-band-ok", "STABLE BAND &ge;70%"
    if stability >= 0.5:
        return "vol-band-warn", "WATCH BAND 50&ndash;70%"
    return "vol-band-bad", "CHURN BAND &lt;50%"
