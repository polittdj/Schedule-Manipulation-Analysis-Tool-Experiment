"""Mission Control - the wall body: the tile mosaic, the verdict band and the ctl KPI tiles.

Monolith split, phase 3 slice 8 (ADR-0372), extracted VERBATIM from ``web/app.py``: every
function, docstring and comment moves byte-for-byte, only the module boundary changes.

The seam is the AST transitive closure of the family's entry points, seeded by behaviour
(the ``/mission`` and ``/export/{fmt}/mission`` routes): ONE name / 304 lines whose sole
external referrer is a ``create_app`` route, which imports downward and stays put. The
export route contributes NO movers - it builds its tables from the trend/evolution
engine functions and the shared export machinery (``_bad_format`` / ``_solvable_versions``
/ ``_pair_versions`` / ``_export_response``), all multi-family stays. No descents: the
body's only externals are ``_e`` (already in ``web/chrome.py``), ``Schedule`` (model) and
``ExecutiveBriefing`` (ai) - the smallest closure of any slice so far.

Layering: ``app`` -> ``mission`` -> ``chrome`` -> ``state`` -> engine/ai/model. Nothing
here imports ``web.app``.
"""

from __future__ import annotations

from schedule_forensics.ai.briefing import ExecutiveBriefing
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.chrome import _e


def _mission_body(
    target_uid: int | None,
    *,
    n_loaded: int,
    n_solvable: int,
    latest: Schedule | None = None,
    briefing: ExecutiveBriefing | None = None,
    other_files: int = 0,
) -> str:
    """Mission Control — every visual on one wall at small scale: expand any tile (⛶), reveal its
    underlying data table (▦ DATA), export it (⤓ EXCEL), and Play-all to step every animated chart
    in lockstep. Each tile hosts the SAME chart scripts/endpoints the dedicated pages use, so the
    session-wide Target UID and Groups & Filters scope every tile automatically.

    ADR-0262: ``n_loaded`` / ``n_solvable`` are the ACTIVE population's loaded and analyzable
    version counts. A cross-version tile below its threshold renders a degrade note INSTEAD of
    its chart host, so its script early-returns and never fetches an API that would 400 — the
    threshold mirrors each tile's own API: Bow Wave/CEI is a stored-date view (two LOADED
    versions), Evolution and the two Quality tiles need two ANALYZABLE (CPM-solvable) versions.

    Mission Ops rank 2 (prototype screen 'ctl'): the tiles carry the panel contract — the exact
    three-glyph strip (▦ DATA / ⤓ EXCEL / ⛶ ENLARGE, ⤓ wired to the EXISTING /export endpoints),
    an "Open NN →" chapter link, a per-tile provenance chip, and a one-line takeaway fed only
    from already-computed figures (the version manifest + the Executive Briefing's own banner) —
    plus the ctl KPI tiles and the verdict band, both quoting ``briefing`` verbatim."""
    target = target_uid if target_uid is not None else ""
    need2_loaded = (
        "Needs at least two loaded versions of the active project &mdash; "
        "load another schedule update to activate this visual."
    )
    need2_solvable = (
        "Needs at least two analyzable versions of the active project &mdash; "
        "load another schedule update to activate this visual."
    )
    # operator 2026-08-20: when OTHER loaded files formed separate Projects (per-update P6
    # exports carry per-copy Project IDs; a renamed project name shatters the version series),
    # "load another schedule update" alone reads as a silent mystery — updates ARE loaded. Name
    # where they went and the two remedies (combine in Portfolio, or switch the active Project).
    # A separate <span> so the base sentence stays one exact-match text node for the i18n
    # catalog; filenames/counts are session data, so the tail is data-no-i18n.
    others_tail = ""
    if other_files == 1:
        others_tail = (
            " <span data-no-i18n>1 other loaded file is grouped into a different Project and "
            "stays off this wall &mdash; if it is an update of the same project, combine the "
            'Projects in <a href="/portfolio">Portfolio</a>, or switch the active Project in '
            "the banner.</span>"
        )
    elif other_files > 1:
        others_tail = (
            f" <span data-no-i18n>{other_files} other loaded files are grouped into a "
            "different Project (or Projects) and stay off this wall &mdash; if they are "
            'updates of the same project, combine the Projects in <a href="/portfolio">'
            "Portfolio</a>, or switch the active Project in the banner.</span>"
        )
    cei_note = (need2_loaded + others_tail) if n_loaded < 2 else ""
    solvable_note = (need2_solvable + others_tail) if n_solvable < 2 else ""

    # ── provenance (SOURCE: file · DD date) — same chip format as the home shell ──────────────
    latest_file = (latest.source_file or latest.name) if latest is not None else ""
    latest_dd = (
        latest.status_date.date().isoformat()
        if latest is not None and latest.status_date is not None
        else "—"
    )
    prov_text = f"SOURCE: {latest_file} · DD {latest_dd}" if latest is not None else ""
    prov = (
        f"<div class=tile-prov><span class=prov-chip data-no-i18n>{_e(prov_text)}</span></div>"
        if prov_text
        else ""
    )

    # ── per-tile takeaway sentences — figures the session/briefing ALREADY computed ───────────
    banner = dict(briefing.banner) if briefing is not None else {}
    forecast = banner.get("Schedule-logic finish (CPM)") or ""
    slip = banner.get("Slip") or ""
    vnoun = "version" if n_loaded == 1 else "versions"
    fc_tail = (
        f" &mdash; the briefing's schedule-logic (CPM) finish is {_e(forecast)}" if forecast else ""
    )
    slip_tail = f" &mdash; the slip vs baseline reads {_e(slip)}" if slip else ""
    verdict_tail = (
        f" &mdash; the briefing verdict is {_e(briefing.verdict)}" if briefing is not None else ""
    )
    target_phrase = f"UID {target_uid}" if target_uid is not None else "the project finish"
    takes = {
        "scurve": f"Cumulative planned vs actual finishes across {n_loaded} loaded "
        f"{vnoun}{fc_tail}.",
        "cei": f"Where unfinished work sits against each data date across {n_loaded} loaded "
        f"{vnoun} &mdash; CEI 1.00 means executed to plan.",
        "drift": f"Three independent forecast methods tracked across {n_loaded} loaded "
        f"{vnoun}{fc_tail}.",
        "finishes": "The distribution of activity finishes, baseline vs current, across "
        f"{n_loaded} loaded {vnoun}{slip_tail}.",
        "datadate": f"Finishes relative to each version's own data date &mdash; {n_loaded} "
        f"loaded {vnoun} through DD {latest_dd}.",
        "slippage": f"Finish slip vs baseline across {n_loaded} loaded {vnoun}{slip_tail}.",
        "evolution": f"The driving path to {target_phrase}, version by version, across "
        f"{n_solvable} analyzable versions.",
        "offenders": "The specific offending activities per quality metric across "
        f"{n_solvable} analyzable versions.",
        "qtrend": f"The DCMA-14 / schedule-quality scores across {n_solvable} analyzable "
        f"versions{verdict_tail}.",
    }

    def tile(
        title: str,
        full_url: str,
        inner: str,
        *,
        controls: str = "",
        wide: bool = False,
        hint: str = "",
        note: str = "",
        num: str = "",
        take: str = "",
        export: str = "",
    ) -> str:
        cls = "tile panel" + (" tile-wide" if wide else "")
        # operator 2026-07-08: every visual explains itself on hover over its NAME — what it
        # shows, an example, how to read it, and what to decide from it (sf-hint-wide callout)
        hint_attr = f' class=viz-hint data-sf-hint="{_e(hint)}"' if hint else ""
        # "Open NN →": the tile's chapter link (prototype ctl tiles) — NN is the chapter number
        open_link = f'<a href="{full_url}" class=btn-link>Open{f" {num}" if num else ""} &rarr;</a>'
        if note:
            # degraded tile (ADR-0262): title + why + the Open link only — no chart host ids
            # (the chart script early-returns), no steppers, no DATA/EXCEL/ENLARGE for a plain
            # note. chart-note (NOT chart-host) so chartframe.js never adds a dead zoom toolbar.
            return f"""<section class="{cls}">
<div class=tile-head><h3{hint_attr}>{title}</h3>
<span class="tile-actions sf-tools" data-noprint=1>{open_link}</span></div>
{prov}
<div class=chart-note><p class=muted>{note}</p></div></section>"""
        # the exact three-glyph strip (panel contract): ▦ DATA / ⤓ EXCEL / ⛶ ENLARGE. DATA and
        # ENLARGE keep their existing mission.js wiring (tile-data / tile-expand); ⤓ EXCEL is
        # panelkit.js's [data-sf-excel] following the tile's data-export (an EXISTING endpoint).
        excel_btn = (
            "<button type=button data-sf-excel "
            'title="Export this visual&#39;s data — opens in Excel" '
            'aria-label="Export this visual&#39;s data to Excel">⤓ EXCEL</button>'
            if export
            else ""
        )
        export_attr = f' data-export="{export}"' if export else ""
        take_html = f"<p class=sf-take data-no-i18n>{take}</p>" if take else ""
        return f"""<section class="{cls}"{export_attr}>
<div class=tile-head><h3{hint_attr}>{title}</h3>
<span class="tile-actions sf-tools" data-noprint=1>\
<button type=button class=tile-data aria-pressed=false \
title="Show / hide the underlying data table" \
aria-label="Show the underlying data table">▦ DATA</button>\
{excel_btn}\
<button type=button class=tile-expand aria-pressed=false \
title="Enlarge / shrink this tile" aria-label="Enlarge this tile">⛶ ENLARGE</button>
{open_link}</span></div>
{prov}
{controls}
<div class=chart-host>{inner}</div>{take_html}</section>"""

    def steps(prev: str, play: str, nxt: str) -> str:
        return (
            f"<div class=mini-steps><button type=button id={prev}>&#8249;</button>"
            f"<button type=button id={play}>&#9654;</button>"
            f"<button type=button id={nxt}>&#8250;</button></div>"
        )

    perf_tiles = "".join(
        [
            tile(
                "S-Curve",
                "/scurve",
                "<div id=scurveLabel class=muted></div><div id=scurveChart></div>",
                hint="WHAT: cumulative % of activities finished over time — the planned curve (baseline dates) vs the actual/current curve.\n\nEXAMPLE: plan says 38% done by the data date but the actual curve reads 22% — the project is running ~16 points behind plan.\n\nHOW TO READ: actual below planned = behind; the horizontal gap between the curves at today's height = roughly how far behind in time; a flattening actual curve = throughput stalling.\n\nDECIDE: whether claimed % complete matches reality, and whether the remaining rate must accelerate to hit the finish.",
                controls=steps("prevScurve", "scurvePlay", "nextScurve"),
                num="09",
                take=takes["scurve"],
                export="/export/xlsx/scurve",
            ),
            tile(
                "Bow Wave / CEI",
                "/cei",
                "<div id=snapLabel class=muted></div><div id=ceiChart></div>",
                hint="WHAT: where unfinished work piles up relative to each version's data date, stepped snapshot by snapshot, with the Current Execution Index (how much of the planned window's work was actually executed).\n\nEXAMPLE: each new version shows a taller hump of tasks packed just after the data date — work is being pushed ahead in a 'bow wave' instead of being finished.\n\nHOW TO READ: a stable, spread-out profile is healthy; a growing near-term hump that rolls forward version after version means replanning is deferring, not solving; CEI well below 1.0 means the team executes far less than each plan promises.\n\nDECIDE: whether the schedule is managed by slipping work windows (a classic health/manipulation red flag) and whether near-term commitments are credible.",
                controls=steps("prevSnap", "autoPlay", "nextSnap"),
                note=cei_note,
                num="06",
                take=takes["cei"],
                export="/export/xlsx/cei",
            ),
            tile(
                "Forecast Drift",
                "/forecast",
                "<div id=driftLabel class=muted></div><div id=driftChart></div>",
                hint="WHAT: the forecast finish date from three independent methods (CPM network logic, historical throughput rate, earned schedule), tracked across every loaded version.\n\nEXAMPLE: over five updates the logic forecast holds March while the rate and earned-schedule forecasts drift to August — the network promises what the demonstrated pace can't deliver.\n\nHOW TO READ: lines drifting right = slipping; methods that AGREE make the forecast credible; a logic forecast far ahead of the performance-based ones usually means optimistic remaining durations or loosened logic.\n\nDECIDE: which finish date to plan around, and whether to challenge an optimistic official forecast.",
                controls=steps("prevDrift", "driftPlay", "nextDrift"),
                num="09",
                take=takes["drift"],
                export="/export/xlsx/forecast",
            ),
            tile(
                "Finishes",
                "/curves",
                "<div id=finishesChart></div>",
                hint="WHAT: the distribution of activity FINISH dates — baseline vs current — as overlaid curves.\n\nEXAMPLE: the current curve's bulk sits two quarters right of the baseline curve — most finishes have moved later, not just a few outliers.\n\nHOW TO READ: a rightward shift of the whole curve = broad slip; a matching shape but offset = uniform delay; a stretched tail = a few activities carrying extreme slips.\n\nDECIDE: whether delay is systemic (replan) or concentrated (recover the few outliers).",
                num="05",
                take=takes["finishes"],
                export="/export/xlsx/curves",
            ),
            tile(
                "Data-date Finishes",
                "/curves",
                "<div id=dataDateChart></div>",
                hint="WHAT: finish dates relative to each version's own data date — how much work each update claims it will finish, and how soon.\n\nEXAMPLE: every version promises a surge of finishes in the 60 days after its data date, and every next version shows the surge didn't happen.\n\nHOW TO READ: compare the promised near-term finishes against what the next snapshot actually closed; repeated over-promising shows up as the same near-term bulge rolling forward.\n\nDECIDE: how much of the near-term plan to believe, and whether commitments need de-risking.",
                num="05",
                take=takes["datadate"],
                export="/export/xlsx/curves",
            ),
            tile(
                "Slippage",
                "/curves",
                "<div id=slippageChart></div>",
                hint="WHAT: how far activity finishes have slipped against baseline (working days, positive = late), across the loaded versions.\n\nEXAMPLE: median slip grows +10 wd per update for three updates straight — the schedule is losing ground at a steady, predictable rate.\n\nHOW TO READ: a rising slip trend that never recovers is erosion; sudden drops without matching scope/logic changes can mean the baseline was quietly moved.\n\nDECIDE: the realistic slip rate to project forward, and whether baseline integrity needs a forensic look.",
                num="05",
                take=takes["slippage"],
                export="/export/xlsx/curves",
            ),
            tile(
                "Critical-Path Evolution",
                "/evolution",
                f'<div id=evoLabel class=muted></div><div id=evoChart data-target="{target}"></div>',
                hint="WHAT: the driving path to the project finish (or your Target UID), version by version — which activities carry the schedule and how membership changes.\n\nEXAMPLE: the path ran through fabrication for four versions, then suddenly runs through software integration — either real progress or a logic change moved the drive.\n\nHOW TO READ: stable membership = a settled plan; churn every version = an unstable network; watch for activities that leave the path exactly when they start slipping (a manipulation signature).\n\nDECIDE: where management attention belongs now, and which path changes deserve a 'why did this change?' interrogation.",
                controls=steps("prevEvo", "evoPlay", "nextEvo"),
                note=solvable_note,
                num="04",
                take=takes["evolution"],
                export="/export/xlsx/evolution",
            ),
            # operator 2026-07-09: the Quality visuals sit NEXT TO Critical-Path Evolution in the
            # same grid (the separate Quality Control section left a mostly-empty row of dead
            # space). The Quality Trend tile is a HOST: on the wall, trend.js lifts each of its
            # charts into its OWN tile (one graph per visual) right after this position.
            tile(
                "Quality Offenders",
                "/trend",
                "<div id=qualLabel class=muted></div>"
                "<div class=qual-drill-grid><div id=qualBars></div><div id=qualDrill></div></div>"
                "<label class=muted>Metric <select id=qualMetric></select></label>",
                hint="WHAT: for the selected quality metric (missing logic, hard constraints, high float…), which specific activities offend, ranked, with a drill-down — across versions.\n\nEXAMPLE: 'Hard constraints' shows 12 offenders and the drill list is dominated by one subproject — that team is pinning dates instead of using logic.\n\nHOW TO READ: click a bar to list the offending activities (UIDs); recurring offenders across versions are structural, not accidental.\n\nDECIDE: exactly which activities to send back to the planner, and where quality problems concentrate.",
                controls=steps("qualPrev", "qualPlay", "qualNext"),
                note=solvable_note,
                num="05",
                take=takes["offenders"],
                export="/export/xlsx/trend",
            ),
            tile(
                "Quality Trend",
                "/trend",
                f'<div id=trendCharts data-target="{target}" data-prov="{_e(prov_text)}"></div>',
                hint="WHAT: the DCMA-14 / schedule-quality metric scores tracked across every loaded version — on this wall each metric renders as its own tile below.\n\nEXAMPLE: missing-logic count falls from 40 to 5 in one update with no matching activity changes — links were bulk-added to pass the audit; verify they are real logic.\n\nHOW TO READ: gradual improvement is normal cleanup; step changes right before reviews are audit-chasing; deteriorating trends flag eroding schedule discipline.\n\nDECIDE: whether schedule quality is genuinely improving and which metric family to audit in depth.",
                note=solvable_note,
                num="05",
                take=takes["qtrend"],
                export="/export/xlsx/trend",
            ),
        ]
    )
    # ── the verdict band + ctl KPI tiles (prototype 'ctl'): the EXISTING Executive Briefing's
    # verdict and banner figures, quoted verbatim — no figure is computed on this page. ─────────
    band = ""
    kpis = ""
    if briefing is not None:
        slug = briefing.verdict.lower().replace(" ", "-").replace("/", "")
        target_chip = f"UID {target_uid}" if target_uid is not None else "PROJECT FINISH"
        band = (
            f'<div class="panel verdict-band vb-{_e(slug)}">'
            "<div><div class=vb-kicker>Mission verdict</div>"
            f"<div class=vb-verdict data-no-i18n>{_e(briefing.verdict)}</div></div>"
            f"<div class=vb-chips><span class=vb-chip data-no-i18n>MEASURED TO {_e(target_chip)}"
            "</span></div>"
            '<a class=btn-link href="/briefing">Open the briefing &rarr;</a></div>'
        )
        kcls = {"ON TRACK": " k-ok", "WATCH": " k-warn", "AT RISK": " k-bad"}.get(
            briefing.verdict, ""
        )
        subs = {
            "Status": "the executive briefing's verdict",
            "SPI (duration-based)": "1.00 = executing to plan",
            "Schedule-logic finish (CPM)": "pure network logic — not a progress-aware forecast",
            "Baseline finish": "the promised finish",
            "Slip": "working days vs the baseline finish",
        }
        cards = "".join(
            f'<div class="ctl-kpi{kcls if label == "Status" else ""}">'
            f"<div class=k-label>{_e(label)}</div>"
            f"<div class=k-value data-no-i18n>{_e(value)}</div>"
            f"<div class=k-sub>{_e(subs.get(label, ''))}</div></div>"
            for label, value in briefing.banner
        )
        kpis = f"<div class=ctl-kpis>{cards}</div>"
    return f"""
<div class=panel><h2>Mission Control &mdash; every visual on one wall</h2>
<p class=muted>Every visual on one wall, each the same size. <b>⛶ ENLARGE</b> any tile to the
full width (and back), reveal the underlying numbers with <b>▦ DATA</b>, take any tile's
data to Excel with <b>⤓ EXCEL</b>, and use
<b>Play all</b> to step every animated chart &mdash; S-Curve, Bow Wave, Forecast Drift, Quality
Offenders, and Critical-Path Evolution &mdash; in lockstep. The session <b>Target UID</b> and
<b>Groups &amp; Filters</b> apply to every tile.</p>
<div class=viz-controls>
<button id=missionPlay type=button>&#9654; Play all</button>
<button id=missionStep type=button>&#9197; Step all</button>
</div></div>
{band}
{kpis}
<div id=missionGrid class=mosaic>
{perf_tiles}
</div>
<script src="/static/timeaxis.js"></script>
<script src="/static/scurve.js"></script>
<script src="/static/cei.js"></script>
<script src="/static/drift.js"></script>
<script src="/static/trend_drill.js"></script>
<script src="/static/curves.js"></script>
<script src="/static/trend.js"></script>
<script src="/static/path_evolution.js"></script>
<script src="/static/mission.js"></script>
<script src="/static/panelkit.js"></script>"""
