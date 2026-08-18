"""Page chrome — the shell every rendered page is poured into (monolith split, phase 2).

Extracted VERBATIM from ``web/app.py`` (ADR-0349, following ADR-0297's phase-1 method): the
``_LAYOUT`` skeleton, the story-spine navigation, the always-on banners (classification,
filter, endpoint, provenance), the per-page explainers, and ``_page`` itself — the single
chokepoint every route returns through. No behaviour changed; only the module boundary did.

``app.py`` re-exports every name here with the explicit ``X as X`` idiom, so existing import
paths (and the tests that use them) keep working unchanged. Nothing in this module imports
``web.app``: the dependency runs one way — ``chrome`` → ``state`` → engine/ai/model.
"""

from __future__ import annotations

import html
import importlib.metadata
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import quote

from fastapi.responses import HTMLResponse
from jinja2 import Template

from schedule_forensics.ai import Banner, Classification, banner_for, banner_for_backend
from schedule_forensics.model.saved_view import Criterion as SavedCriterion
from schedule_forensics.model.saved_view import Operand as SavedOperand
from schedule_forensics.web import i18n
from schedule_forensics.web.state import _ROLE_BY_ID, _ROLES, SessionState, _Flash

try:  # the installed package version, used to cache-bust static asset URLs on upgrade
    _ASSET_VERSION = importlib.metadata.version("schedule-forensics")
except importlib.metadata.PackageNotFoundError:  # running from a raw source tree
    _ASSET_VERSION = "dev"
#: /static/<asset> not already carrying a query — rewritten to /static/<asset>?v=<version> at the
#: page-render boundary. Deployed installs serve a FIXED port, so the browser cache origin
#: persists across upgrades; without a versioned URL a browser may serve a heuristically-cached
#: stale JS/CSS (StaticFiles sends no Cache-Control) and an upgraded tool keeps OLD behavior.
_STATIC_REF = re.compile(r"(/static/[A-Za-z0-9_.\-]+)(?![A-Za-z0-9_.\-?])")


def _bust_static(html_text: str) -> str:
    """Append ``?v=<package version>`` to every static asset URL in a rendered page."""
    return _STATIC_REF.sub(rf"\1?v={_ASSET_VERSION}", html_text)


_LAYOUT = Template(
    """<!doctype html><html lang="{{ lang }}"><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<meta name=sf-launch content="{{ launch_token }}">
<title>{{ title }} — POLARIS</title>
<link rel=icon href="/static/favicon.ico">
<script id=sfI18nBoot type="application/json">{{ i18n_boot_json }}</script>
<script src="/static/theme.js"></script>
<script src="/static/chrome.js"></script>
<script src="/static/checklist.js"></script>
<script src="/static/gantt.js"></script>
<script src="/static/timescale.js"></script>
<script src="/static/colresize.js"></script>
<script src="/static/taskinfo.js"></script>
<script src="/static/persist.js"></script>
<script src="/static/a11y.js"></script>
<script src="/static/translate.js"></script>
<script src="/static/drilldown.js"></script>
<script src="/static/tooltips.js"></script>
<link rel=stylesheet href="/static/base.css"><link rel=stylesheet href="/static/app.css"><link rel=stylesheet href="/static/hud.css"><link rel=stylesheet href="/static/sf-themes.css">
<style>
/* Density + containment overrides (operator request, ADR-0150): tighter spacing everywhere,
   and grid/table containment so wide tables scroll inside their card instead of overlapping
   the neighbouring column (the Executive Briefing 3-column blowout). */
.panel{padding:10px 14px;margin:10px 0}
.panel h2{margin:.15em 0 .35em}
.panel h3{margin:.5em 0 .25em}
td,th{padding:3px 8px}
p{margin:.4em 0}
p.muted{margin:.3em 0}
.brief-card,.brief-cards .panel,.dash-card,.stat-card{min-width:0}
.brief-card{overflow-x:auto}
.brief-card table{width:100%}
/* Never let table auto-layout crush columns into vertical one-character text: headers stay on
   one line, data cells wrap at word boundaries only, and a too-wide table scrolls inside its
   card (overflow-x above) instead of squeezing its columns. */
.brief-card th{white-space:nowrap}
.brief-card td{overflow-wrap:break-word;word-break:normal}
.cite{overflow-wrap:break-word}
</style></head><body>
<div class="cui-banner {{ cui_class }}" data-no-i18n>{{ cui_text }}</div>
{{ drawer }}
<header><h1 class=brand data-no-i18n
aria-label="POLARIS — Program Oversight &amp; Logic Analysis for Risk &amp; Integrity of Schedules"
title="POLARIS — Program Oversight &amp; Logic Analysis for Risk &amp; Integrity of Schedules">
<!-- POLARIS wordmark (ADR-0175): hand-set NASA-worm-style letterforms drawn as SVG strokes —
     no webfont, fully inline, so the air-gap CSP stays intact and it renders identically
     on every machine. Uniform stroke, rounded joins, crossbar-less A, trailing north star. -->
<svg class=brand-mark viewBox="0 0 344 72" aria-hidden=true focusable=false>
<g class=brand-strokes fill=none stroke-width=13 stroke-linecap=round stroke-linejoin=round>
<path d="M6 62 V10 H20 A13 13 0 0 1 20 36 H6"/>
<rect x="54" y="10" width="28" height="52" rx="14"/>
<path d="M102 10 V62 H128"/>
<path d="M150 62 V28 A14 14 0 0 1 178 28 V62"/>
<path d="M198 62 V10 H212 A13 13 0 0 1 212 36 H198 M212 36 L226 62"/>
<path d="M248 10 V62"/>
<path d="M299 12 H285 A12 12 0 0 0 285 36 H287 A12 12 0 0 1 287 60 H273"/>
</g>
<path class=brand-star d="M328 6 Q329.5 16.5 340 18 Q329.5 19.5 328 30 Q326.5 19.5 316 18 Q326.5 16.5 328 6 Z"/>
</svg>
<span class=brand-sub>Program Oversight &amp; Logic Analysis for Risk &amp; Integrity of Schedules</span>
</h1>
<input type=checkbox id=navToggle class=nav-toggle aria-label="Toggle navigation menu">
<label for=navToggle class=nav-burger title="Menu" data-no-i18n><span aria-hidden=true>&#9776;</span></label>
{{ nav }}
<span class="nasa-globe" data-no-i18n title="Local AI status: the globe spins up while the model is generating"><canvas width="96" height="96" aria-hidden="true"></canvas></span>
</header>
<main>{{ banner }}{{ body }}</main><script src="/static/heartbeat.js"></script>
<script src="/static/chartframe.js"></script>
<script src="/static/legend_toggle.js"></script>
<script src="/static/target.js"></script>
<script src="/static/globe.js"></script>
<script src="/static/sysmon.js"></script>
<script src="/static/hints.js"></script>
<script src="/static/vizhints.js"></script>
<script src="/static/story.js"></script>
<div class="cui-banner {{ cui_class }} bottom" data-no-i18n>{{ cui_text }}</div>
</body></html>"""
)


def _explain(what: str, read: str, decide: str) -> str:
    """A collapsed "What am I looking at?" explainer rendered above a chart/section: WHAT the
    visual shows, HOW to read it, and the DECISIONS it should inform. Server-rendered plain text
    (escaped) so the i18n pass translates it like any other prose."""
    return (
        "<details class=explain><summary>What am I looking at &mdash; and how do I use it?"
        "</summary><div class=explain-body>"
        f"<h4>What this shows</h4><p>{_e(what)}</p>"
        f"<h4>How to read it</h4><p>{_e(read)}</p>"
        f"<h4>Decisions it informs</h4><p class=explain-decide>{_e(decide)}</p>"
        "</div></details>"
    )


def _guide(tip_id: str, text: str) -> str:
    """A dismissable first-visit guide tip (hints.js persists the dismissal per tip id)."""
    return (
        f'<div class=guide-tip data-tip-id="{_e(tip_id)}"><button type=button '
        'class=guide-dismiss title="Dismiss this tip" data-no-i18n>&times;</button>'
        f"<b>Tip:</b> {_e(text)}</div>"
    )


def _observed_banner(state: SessionState) -> Banner:
    """The session's sovereignty banner, OBSERVED from every reachable evidence (DoD 001b).

    Two observations, either of which vetoes the local-only assurance:

    * :func:`banner_for` constructs the backends this config would route schedule content
      through (primary + cross-check second, ``ai.factory``) and derives from what those
      objects themselves declare — so a non-local *configuration* warns even before any
      generation runs, and a cloud intent warns while routing falls closed (§0.2).
    * The session's actually-routed backend (``state.backend_cache``, the product of
      ``_active_backend`` — however it was injected) is re-derived through
      :func:`banner_for_backend` — so a non-local object that reached the routing cache by
      any path at all can never sit behind a local-only banner.

    The assurance renders only when BOTH observations agree everything is local.
    """
    banner = banner_for(state.ai_config)
    if not banner.cloud_active:
        cached = state.backend_cache
        if cached is not None and cached[0] == state.ai_config:
            derived = banner_for_backend(cached[2], state.ai_config)
            if derived.cloud_active:
                return derived
    return banner


def _banner_html(state: SessionState) -> str:
    # the persistent banner is OBSERVED (DoD 001b): see _observed_banner. Generation still
    # fails closed via route_backend, whose returned Banner is the same derivation over the
    # backend it actually chose.
    banner = _observed_banner(state)
    css = "cloud" if banner.cloud_active else "local"
    return f'<div class="banner {css}">{html.escape(banner.text)}</div>'


def _filter_banner(state: SessionState) -> str:
    """A page-top notice, shown on EVERY page while a session-wide filter/group is active, so the
    operator always knows how the numbers are scoped — with one-click manage/clear (ADR-0104).
    Branches on the active source (saved MS Project filter vs field rows) and states the MODE
    honestly: reduce scopes every metric; highlight only marks (metrics stay whole-schedule)."""
    lines: list[str] = []
    if state.active_saved_filter is not None:
        saved = state.active_saved_filter
        tree = _e(_criteria_text(saved.criteria))
        if state.filter_mode == "highlight":
            reach = (
                "matching tasks are <b>highlighted</b> on the grids &mdash; metrics are "
                "<b>not</b> scoped (full schedules)"
            )
        else:
            reach = "every metric on every page (all files) is <b>scoped</b> to its matches"
        lines.append(
            f"<b>Saved filter “{_e(saved.display_name)}”</b> &mdash; {reach}: "
            f'<span class="dp-chip">{tree}</span>. <a href="/groups">manage</a> &middot; '
            '<a href="/groups?clear=1">clear</a>'
        )
    elif state.active_filter:
        parts = []
        for fld, value in state.active_filter:
            vals = _criterion_value_list(value)
            shown = (
                "(populated)"
                if not vals
                else _expandable_more(_e(", ".join(vals[:3])), [_e(v) for v in vals[3:]])
            )
            parts.append(f"{_e(fld)} = {shown}")
        chips = " &middot; ".join(parts)
        mode_note = (
            " (highlight mode &mdash; matches marked, metrics NOT scoped)"
            if state.filter_mode == "highlight"
            else ""
        )
        lines.append(
            f"<b>Filter active</b>{mode_note} &mdash; every metric on every page (all files) is "
            f'scoped to: {chips}. <a href="/groups">manage</a> &middot; '
            '<a href="/groups?clear=1">clear filter</a>'
        )
    if state.active_saved_group is not None:
        lines.append(
            f"<b>Grouped by “{_e(state.active_saved_group.display_name)}”</b> &mdash; ordering/"
            'banding only, metric populations unchanged. <a href="/groups">manage</a> &middot; '
            '<a href="/groups?saved_group=">clear group</a>'
        )
    if not lines:
        return ""
    body = "<br>".join(lines)
    return (
        f'<div class="panel filter-active" style="border-left:4px solid var(--accent)">{body}</div>'
    )


def _endpoint_clear_form(label: str) -> str:
    """An inline form that clears the Target-UID endpoint, returning to the current page (the
    shared ``targetform`` class lets target.js rewrite next_url to the current location)."""
    return (
        '<form action="/target" method=post class="targetform endpoint-clear">'
        '<input type=hidden name=uid value=""><input type=hidden name=next_url value="/">'
        f"<button type=submit class=linkbtn>{_e(label)}</button></form>"
    )


def _endpoint_banner(state: SessionState) -> str:
    """A page-top notice, shown on EVERY page while a Target UID endpoint is active, so the operator
    always knows every metric/visual is limited to that activity and the work that drives it — with
    the count of omitted activities and a one-click clear (forensic transparency)."""
    uid = state.target_uid
    if uid is None:
        return ""
    found = False
    kept = total = 0
    # Scope to the ACTIVE project's versions (ADR-0284 / Fix E), not every loaded version across
    # every project: ordered_versions() applies the ADR-0258 active-project narrowing, so the
    # omitted-count reflects the population actually being analysed (a UID that lives only in
    # another project neither counts toward `total` nor marks the endpoint as found here).
    for _key, s in state.ordered_versions():
        if any(t.unique_id == uid and not t.is_summary for t in s.tasks):
            found = True
        scoped = state.scope(s)
        total += sum(1 for t in s.tasks if not t.is_summary)
        kept += sum(1 for t in scoped.tasks if not t.is_summary)
    if not found:
        return (
            '<div class="panel endpoint-active" style="border-left:4px solid var(--bad)">'
            f"<b>Endpoint UID {uid} not found</b> &mdash; no loaded version contains that activity, "
            f"so nothing is being truncated. Check the UID. {_endpoint_clear_form('clear endpoint')}"
            "</div>"
        )
    omitted = total - kept
    return (
        '<div class="panel endpoint-active" style="border-left:4px solid var(--warn)">'
        f"<b>Analysis endpoint: UID {uid}</b> &mdash; every metric and visual on every page is "
        f"limited to UID {uid} and the activities that drive it "
        f"({kept} of {total} activities shown; {omitted} omitted). "
        f"{_endpoint_clear_form('clear endpoint')}</div>"
    )


def _flash_html(flash: _Flash | None) -> str:
    """Render one-shot import feedback (loaded N / per-file errors / notices), or nothing.

    Notices render even with nothing accepted and no errors — an upload where EVERY file was a
    collapsed byte-identical duplicate (ADR-0259) or unreadable must still say so, never land
    silently on an unchanged dashboard."""
    if flash is None or (not flash.accepted and not flash.errors and not flash.notices):
        return ""
    parts: list[str] = []
    if flash.accepted:
        names = ", ".join(_e(a) for a in flash.accepted)
        parts.append(f'<div class="notice ok">Loaded {len(flash.accepted)}: {names}</div>')
    for err in flash.errors:
        parts.append(f'<div class="notice err">Could not import {_e(err)}</div>')
    for note in flash.notices:
        parts.append(f'<div class="notice info">{_e(note)}</div>')
    return "".join(parts)


def _ask_panel_html(state: SessionState, page_schedule: str | None = None) -> str:
    """The Ask-the-AI panel every page carries once schedules are loaded (M18 item 4).

    Scope select: the whole workbook (multi-version cited facts) or any single loaded
    schedule; a page with a natural schedule context pre-selects it. The disclaimer is
    standing and permanent — answers may be model-interpreted (settings: AI answer mode)
    but are always grounded by, and shown with, the engine's cited facts.
    """
    if not state.schedules:
        return ""
    keys = [k for k, _ in state.ordered_versions()]
    options: list[str] = []
    if len(keys) > 1:
        sel = " selected" if page_schedule is None else ""
        options.append(f'<option value=""{sel}>Workbook — all {len(keys)} versions</option>')
    for k in keys:
        sel = " selected" if k == page_schedule or len(keys) == 1 else ""
        options.append(f'<option value="{_e(k)}"{sel}>{_e(k)}</option>')
    return f"""
<div class=panel id=askPanel><h2>Ask the AI</h2>
<p class=muted><b>AI can err &mdash; verify against citations.</b> Ask anything about the loaded
data: with a local model active (Ollama) you get a full written analysis grounded in the
engine's computed, cited facts &mdash; the matching facts are always shown alongside. With no
local model active you get the cited facts themselves; <a href="/settings">enable Ollama in AI
Settings</a> for interpretation. Questions have <b>no length limit</b> &mdash; paste as much
context as you need. Once an answer is on screen, <b>&#10515; EXCEL</b> saves the question, the
answer and every cited fact as a workbook.</p>
<p class=muted><b>Figure check is role-aware.</b> In <i>strict</i> and <i>annotate</i> modes a number
the model writes is matched against the figures in the cited facts, and a digit that appears only in
an activity <i>name</i> or <i>ID</i> (e.g. "Milestone 2099", UID&nbsp;6077) &mdash; never as an engine
value &mdash; is treated as an identifier the model has re-used in another role (a finish year, a
count): <i>strict</i> discards that answer and <i>annotate</i> flags it &mdash; and the identifier
check runs <i>before</i> the derived-figure check, so a re-used ID can never pass as a coincidental
derivation. Writing an ID <i>as</i> an ID ("UID&nbsp;143", a quoted activity name) is fine; dates
count as whole dates, not digit fragments; a derived whole number must reconstruct exactly; and a
figure re-written with a <i>different explicit unit</i> than the engine stated (a "5%" re-used as
"5&nbsp;days") is likewise discarded/flagged. A digit
that is also a genuine value is untouched (collision-safe). <i>Interpretive</i> mode is not
figure-gated at all. Read any figure against the cited facts &mdash; the meaning, not just the
number.</p>
<div class=viz-controls>
<label>About <select id=askScope>{"".join(options)}</select></label>
<button id=askBtn type=button>Ask</button>
<span id=askExports class=ask-exports hidden><a class=linkbtn id=askExport href="/export/xlsx/ask" download
 title="Export this question, the answer and every cited fact to Excel">&#10515; EXCEL</a>
<a class=linkbtn id=askExportDocx href="/export/docx/ask" download
 title="Export this question, the answer and every cited fact to Word">&#10515; WORD</a></span></div>
<textarea id=askInput class=ask-input rows=3
 placeholder="e.g. Why is the finish slipping? How many critical activities? Ask as long a question as you like &#8212; there is no length limit. Enter sends; Shift+Enter starts a new line."></textarea>
<div class=viz-controls><span class=muted>Driving path (exact, no AI):</span>
<label>to UID <input id=drivePathUid type=number min=1 step=1 style="width:7em"
 placeholder="UID"></label>
<button id=drivePathBtn type=button>Show driving path</button></div>
<div id=askOut></div></div>
<script src="/static/ask.js"></script>"""


#: Per-page "What am I looking at?" explainers (title → what / how to read / decisions). Rendered
#: collapsed at the top of every matching page by _page(); plain text (escaped + translated by the
#: normal i18n pass). Written for a project analyst, decision-first.
_EXPLAINERS: dict[str, tuple[str, str, str]] = {
    "Dashboard": (
        "Every schedule version loaded in this session, with its headline health: activity "
        "counts, data date, computed finish, and the DCMA 14-point pass rate.",
        "Each row is one schedule file. Green PASS rates and a stable computed finish are "
        "healthy; a falling pass rate or a finish that moves right between versions is the "
        "first warning. Click a file name for its full forensic report.",
        "Decide which version needs attention first, whether the latest update degraded "
        "schedule quality, and whether the finish date is drifting before anyone reports it.",
    ),
    "Mission Control": (
        "A single wall-view of the whole session: every loaded version's key indicators side "
        "by side, built for a stand-up or a war room screen.",
        "Scan for red: failing checks, negative float, slipped finishes. Everything here is "
        "computed by the engine from the files — nothing is typed in.",
        "Use it to open a status meeting: pick the reddest column and drill into that "
        "version's report before discussing anything else.",
    ),
    "Schedule Quality Ribbon": (
        "The Acumen-Fuse-style quality ribbon: one chip per structural metric (missing logic, "
        "leads, lags, constraints, high float, negative float, logic density and more) for the "
        "selected version.",
        "Each chip is a metric with its count and pass/fail color. Hover a chip for its "
        "definition; click through to the Metric Dictionary for the formula, thresholds and a "
        "worked example.",
        "A failing chip tells you exactly which structural repair to schedule next — fix "
        "missing logic before trusting any critical-path or float number downstream.",
    ),
    "Assessment Scorecards": (
        "Three named assessment frameworks beside DCMA-14: the NASA STAT construction checks, the "
        "GAO Schedule Assessment Guide's ten best practices, and an SRA-readiness gate — plus a "
        "reserve-sizing card that says how much buffer protects a committed date at P70/P80.",
        "Each line is a chip (green pass / red fail / grey info) whose figure is drawn straight "
        "from the tool's already-validated metrics — the gate-locked DCMA-14 audit, the "
        "logic-integrity checks, and deterministic model scans; nothing is re-scored here. Pick a "
        "version to assess, and enter a committed date to size the schedule reserve.",
        "Use it to answer 'is this schedule fit for a defensible risk analysis, and does it meet "
        "the GAO/NASA construction bar?' in one view — and to justify the contingency you carry "
        "against the committed finish, at a confidence you can defend in testimony.",
    ),
    "Path Analysis": (
        "The activity network laid out on a time axis: the critical path plus every driving "
        "and near-driving chain, with float per activity.",
        "Bars are activities; the highlighted chain is the path controlling the finish. Tight "
        "float (colored) means little room before a slip hits the end date. Use the filter to "
        "isolate a subsystem, and the export bar to take the picture into a report.",
        "Identify WHERE to add resources or resequence: only work on the driving chain moves "
        "the finish; float elsewhere is schedule margin you can spend deliberately.",
    ),
    "Driving Path": (
        "The exact chain of activities that drives a chosen target activity (or the project "
        "finish), with each link's driving slack — the SSI driving-path view.",
        "Read top-down: each row is the next activity in the chain, and the slack column shows "
        "how much that link can give before it stops driving. Zero-slack links are the "
        "controlling logic.",
        "This is the repair map for a late milestone: accelerate or de-couple the zero-slack "
        "links; anything off this chain will not move the target date.",
    ),
    "Critical-Path Evolution": (
        "How the critical path CHANGED across the loaded versions: which activities joined, "
        "left, and stayed on the controlling path over time.",
        "Each column is a version; each row an activity. Long unbroken rows are a stable "
        "controlling chain; churn (rows appearing/disappearing) means the network's logic is "
        "being rewired between updates.",
        "Stable paths justify targeted recovery plans. Heavy churn is a red flag — either the "
        "plan is being re-baselined quietly or logic is being edited to mask slips; ask for "
        "the change log before accepting the update.",
    ),
    "CP Volatility": (
        "How STABLE the critical path's membership is across the loaded versions: which "
        "activities stayed on the controlling chain longest, and which jumped off and on.",
        "Ten linked visuals over the same per-version critical sets — a stability gauge and "
        "churn timeline (Jaccard similarity), entry/exit flows, a membership heatmap, tenure "
        "and jumper leaderboards, dwell distribution, animated transition ribbons, and a "
        "sortable per-activity scoreboard.",
        "GAO/DCMA best practice expects a stable controlling chain. Heavy churn means the "
        "network is being rewired between updates — cross-reference the worst update with "
        "the Schedule Integrity findings and ask for the change log.",
    ),
    "Trend": (
        "Every metric family tracked ACROSS versions: quality counts, float, completion "
        "performance, forecast movement — the direction of the schedule over time.",
        "Each mini-chart is one metric plotted per version, oldest to newest. Flat or "
        "improving lines are health; worsening lines show exactly when a problem entered. "
        "Click a point to drill into that version.",
        "Trends turn one bad number into a story: use the inflection version to ask what "
        "changed in THAT update — a re-baseline, a calendar edit, a logic rewrite.",
    ),
    "Bow Wave / CEI": (
        "The bow-wave chart: work planned vs work actually finished per period, plus the "
        "Current Execution Index (CEI) — how much of what was planned near-term actually got "
        "done.",
        "Bars pushing right of the data date are the bow wave — work sliding ahead of itself. "
        "CEI below about 0.8 means the near-term plan is not being executed as written.",
        "A growing bow wave predicts a finish slip BEFORE the finish moves: force-rank the "
        "pushed work, fix the choke (resources, predecessors), and re-check next period.",
    ),
    "Finish & Slippage": (
        "Two curves per version pair: where finishes were promised and how far they slipped — "
        "the schedule's promise-keeping record.",
        "Each point compares an activity's finish across versions. Points off the diagonal "
        "slipped; the spread shows whether slippage is isolated or systemic.",
        "Systemic slippage means the baseline is unrealistic — re-plan capacity. Isolated "
        "slippage names the specific work packages to manage this period.",
    ),
    "S-Curve": (
        "Cumulative planned vs actual progress over time — the classic S-curve for the "
        "selected version(s).",
        "The gap between the planned and actual curves is the schedule's true position; a "
        "flattening actual curve means momentum is being lost even if percent-complete "
        "numbers still look busy.",
        "Use the gap and its growth rate to justify (or refute) a recovery plan: a widening "
        "gap with a flat actual curve will not be closed by optimism.",
    ),
    "Forecast": (
        "Multiple engine-computed finish forecasts side by side: schedule-logic CPM (with started "
        "work anchored to its recorded actual start), the stored as-scheduled finish, and "
        "performance-adjusted projections.",
        "Each method row shows its date and its basis. When methods disagree, the spread IS "
        "the uncertainty; the as-scheduled row shows what the source tool itself stored.",
        "Never brief a single date without the spread: use the range to set commitment dates "
        "with margin, and investigate when the methods diverge sharply.",
    ),
    "EVM": (
        "Earned-value indices computed from the schedule's cost loading: BCWS/BCWP/ACWP, "
        "SPI, CPI and companions, validated against Acumen Fuse where reference data exists.",
        "SPI/CPI near 1.0 is on-plan; below ~0.9 is trouble. NOT APPLICABLE rows mean the "
        "loaded file carries no cost data — that is a fact about the file, not a failure.",
        "Falling SPI with steady CPI means schedule pressure without overspend — a staffing or "
        "sequencing fix. Falling both means the plan itself is broken: re-baseline.",
    ),
    "Resources": (
        "Resource loading over time: who/what is booked, where bookings exceed capacity, and "
        "which activities drive the peaks.",
        "Bars above the capacity line are over-allocations. Expand a peak to see the exact "
        "activities stacking on that resource in that window.",
        "Level BEFORE committing dates: an over-allocated critical resource makes the whole "
        "plan fiction. Move, split, or re-staff the peak drivers first.",
    ),
    "Risks & Opportunities": (
        "The engine's cited findings ranked in a 5x5 risk matrix: every schedule-quality and "
        "manipulation signal, with severity, likelihood and the exact activities cited.",
        "Each finding carries its evidence (file + UID + activity). The matrix position comes "
        "from computed exposure — the days of float actually at stake — not opinion.",
        "Work the top-right cells first; every finding lists its recommended course of action "
        "and the activities to open. Treat manipulation signals as questions to ASK, not "
        "verdicts.",
    ),
    "Schedule Integrity": (
        "Version-over-version change forensics: every manipulation-pattern signal the engine "
        "detects between consecutive files (deleted tasks or logic, shortened in-progress "
        "durations, added hard constraints, loosened calendars, baseline-date changes, edited "
        "or erased actuals), each cited to file + UniqueID + task — plus a counterfactual that "
        "reverts the path-shedding changes and re-runs CPM to show what the finish would have "
        "been without them.",
        "Read each version-pair section top to bottom: the severity column ranks the signals; "
        "the citations name the exact activities; the counterfactual panel quantifies how much "
        "apparent recovery came from the changes rather than performed work. Select an "
        "exception field (for example a BCR number) to badge or hide changes that were "
        "authorized.",
        "Whether the schedule's reported recovery is real; which specific changes to interrogate "
        "in a schedule review; which findings are already covered by an approved change request "
        "and which have no paper trail.",
    ),
    "Risk Analysis (SRA)": (
        "A Monte-Carlo schedule risk analysis: activity durations varied per your 3-point "
        "settings and risk register, run through the real CPM engine to a finish-date "
        "distribution.",
        "The histogram shows possible finish dates and their likelihood; P50/P80 markers are "
        "the dates with 50%/80% confidence. The tornado ranks which activities drive the "
        "spread.",
        "Commit to P80-class dates, not the deterministic finish. Attack the top tornado "
        "drivers — tightening their uncertainty moves the whole distribution left.",
    ),
    "Diagnostic Brief": (
        "A printable, fully-cited diagnostic of the selected version: every failing check, "
        "finding and key figure with its evidence trail.",
        "Read it like an audit report: each statement cites the file, activity ID and name it "
        "rests on. Nothing here is AI-generated — it is the engine's own computation.",
        "Hand this to the schedule owner as the work list; every line is defensible because "
        "every line is cited.",
    ),
    "Executive Briefing": (
        "The whole session condensed for leadership: bottom line up front, cross-version "
        "trend, per-version verdicts, risks and recommended actions — every statement cited.",
        "Start at the one-sentence bottom line. Optional local-AI polish only rewords "
        "sentences — every figure is verified against the engine before display.",
        "Use it as the meeting document: decisions land faster when every claim carries its "
        "citation inline.",
    ),
    "Metric Dictionary": (
        "The authoritative definition of every metric this tool computes: formula, source, "
        "thresholds, and a worked example for each.",
        "Each entry states what the metric measures, the exact formula, why it matters, what "
        "a failure indicates, and PASS/FAIL examples. Metrics link here from every page.",
        "When two stakeholders argue about a number, this page ends the argument: same "
        "formula, same thresholds, same source for everyone.",
    ),
    "Groups & Filters": (
        "A session-wide lens: filter every page and every loaded version to the activities "
        "matching your criteria (WBS, name, custom fields...).",
        "Set criteria and Apply — the filter banner then shows on every page until cleared. "
        "All metrics recompute over the filtered population only.",
        "Isolate one subsystem or contractor and read its health in minutes instead of "
        "exporting subsets by hand. Clear the filter before quoting whole-project numbers.",
    ),
    "AI Settings": (
        "Controls for the OPTIONAL local AI: backend, model, answer mode, second-model "
        "cross-check, and the project's classification posture.",
        "Everything runs on 127.0.0.1 — a cloud backend is refused while the project is "
        "CLASSIFIED. Answer modes trade breadth for strictness: strict never shows an "
        "unverified number; annotate flags derived ones; interpretive is unfiltered analysis.",
        "Pick strict for testimony work, annotate for daily analysis. If a figure ever "
        "surprises you, check its citation before repeating it.",
    ),
    "Compare": (
        "Two versions side by side: every tracked field change per activity — dates, "
        "durations, logic, constraints, status.",
        "Each row is one activity's deltas between the versions. Sort by the change that "
        "matters (finish slip, duration growth, constraint added).",
        "This is where quiet edits surface: baseline changes, added constraints and "
        "deactivated work show up here even when the summary numbers look stable.",
    ),
}


def _page_explainer(title: str) -> str:
    entry = _EXPLAINERS.get(title)
    if entry is None or not entry[0]:
        return ""
    return _explain(*entry)


def _global_sources_banner(state: SessionState, focus_key: str | None = None) -> str:
    """The ALWAYS-ON provenance banner every page carries (operator 2026-07-10: "NO MATTER
    WHAT ... I want them to see clearly what file it is being pulled from"): the loaded
    file(s), oldest first, under the page header. Single-file pages and per-visual captions
    still name their specific file; animated visuals caption the file per step on top of this.

    With more than one Project loaded, a PROJECT strip leads (ADR-0258): analysis pages show
    exactly ONE Project — the strip names it, offers the switch, links Portfolio (the only
    cross-project page), and flags pending duplicate-review decisions (ADR-0259)."""
    try:
        schedules = [s for _k, s in state.ordered_versions()]
        with state._lock:
            pops = state.populations()
        pending = sum(1 for p in state.projects() if p.pending_review)
    except Exception:
        return ""
    strip = ""
    if len(pops) > 1:
        active = state.active_population()
        if active is not None:
            opts = "".join(
                f'<option value="{_e(pid)}"{" selected" if pid == active[0] else ""}>'
                f"{_e(title)} ({len(keys)})</option>"
                for pid, title, keys in pops
            )
            review = (
                f" &middot; <span class=rib-fail>{pending} pending review</span>" if pending else ""
            )
            strip = (
                "<div class=src-banner data-no-i18n>&#128193; Project: "
                f"<b>{_e(active[1])}</b> &mdash; switch: "
                f'<form method=post action="/project/select" style="display:inline">'
                '<input type=hidden name=next_url value="/">'
                # the app sends Referrer-Policy: no-referrer, so the CURRENT page rides an
                # explicit next_url (validated server-side like /target's) — the switch returns
                # to the page the operator was reading, not the dashboard
                f"<select name=pid data-sf-nexturl-submit>{opts}</select></form>"
                f" &middot; {len(pops)} Projects loaded &middot; "
                f'<a class=btn-link href="/portfolio">Portfolio</a>{review}</div>'
            )
    if not schedules:
        return strip
    names = [_e(s.source_file or s.name) for s in schedules]
    # a per-file page (e.g. /analysis — "Where We Stand") names ITS file and offers a switcher
    # instead of implying the numbers mix all loaded files (operator 2026-07-16)
    if focus_key is not None:
        pairs = state.ordered_versions()
        cur = dict(pairs).get(focus_key)
        cur_name = _e((cur.source_file or cur.name) if cur is not None else focus_key)
        if len(pairs) <= 1:
            inner = f"All data on this page is computed from: <b>{cur_name}</b>"
        else:
            opts = "".join(
                f'<option value="/analysis/{quote(k, safe="")}"'
                f"{' selected' if k == focus_key else ''}>{_e(s.source_file or s.name)}</option>"
                for k, s in pairs
            )
            inner = (
                f"This page shows ONE file: <b>{cur_name}</b> &mdash; switch file: "
                f"<select data-sf-navselect data-no-i18n>{opts}</select> "
                "(versions are compared on the Trend / Compare / Evolution pages, never mixed here)"
            )
        return strip + f"<div class=src-banner data-no-i18n>&#128196; {inner}</div>"
    if len(names) == 1:
        inner = f"All data on this page is computed from: <b>{names[0]}</b>"
    else:
        inner = (
            f"Data on this page is computed from the {len(names)} loaded files "
            "(oldest first): <b>" + "</b> &rarr; <b>".join(names) + "</b> — each visual/table "
            "names its own file scope, and animated visuals caption the file shown at each step."
        )
    return strip + f"<div class=src-banner data-no-i18n>&#128196; {inner}</div>"


# ── Mission Ops story spine (ADR-0196) ─────────────────────────────────────────────────────
@dataclass(frozen=True)
class _Chapter:
    """One entry in the three-act / twelve-chapter story spine (the Mission Ops redesign).

    ``route`` is where the nav link points; ``@analysis`` / ``@wbs`` resolve to the first loaded
    schedule's report. ``beats`` are secondary pages folded under the chapter — kept in the nav so
    nothing is orphaned. ``titles`` are the ``_page(...)`` title strings that resolve to this
    chapter (drives the kicker / Continue footer / progress "you are here"); ``takeaway`` seeds the
    Continue segue.
    """

    num: str
    label: str
    route: str
    beats: tuple[tuple[str, str], ...] = ()
    titles: tuple[str, ...] = ()
    takeaway: str = ""


_SPINE: tuple[tuple[str, tuple[_Chapter, ...]], ...] = (
    (
        "LOAD",
        (
            _Chapter(
                "00",
                "Import",
                "/",
                (),
                ("Dashboard",),
                "Load the mission — drop schedule files to begin.",
            ),
        ),
    ),
    (
        "OVERVIEW",
        (
            _Chapter(
                "",
                "Portfolio",
                "/portfolio",
                (),
                ("Portfolio",),
                "Every project across the portfolio, at a glance.",
            ),
            _Chapter(
                "",
                "Mission Control",
                "/mission",
                (),
                ("Mission Control",),
                "The whole session on one wall.",
            ),
        ),
    ),
    (
        "ACT I · SITUATION",
        (
            _Chapter(
                "01",
                "Where we stand",
                "@analysis",
                (),  # the Card drill now heads the LIBRARY rail (nav placement only)
                (),
                "Where the project stands at the data date.",
            ),
            _Chapter(
                "02",
                "Can we trust the plan?",
                "/ribbon",
                (),  # Integrity → FORENSICS, Scorecards → CONTROL; both stay ch-02 by title
                ("Schedule Quality Ribbon", "Schedule Integrity", "Assessment Scorecards"),
                "Whether the schedule is built soundly enough to trust its numbers.",
            ),
        ),
    ),
    (
        "ACT II · DIAGNOSIS",
        (
            _Chapter(
                "03",
                "What drives the date",
                "/path",
                (("Driving Path", "/driving-path"),),
                ("Path Analysis", "Driving Path"),
                "The chain of work that controls the finish.",
            ),
            _Chapter(
                "04",
                "How stable is the path",
                "/evolution",
                (("CP Volatility", "/volatility"),),
                ("Critical-Path Evolution", "CP Volatility"),
                "Whether the critical path holds or thrashes between updates.",
            ),
            _Chapter(
                "05",
                "How it moved",
                "/trend",
                (("Finish & Slippage", "/curves"),),
                ("Trend", "Finish & Slippage"),
                "How the finish has moved, update over update.",
            ),
            _Chapter(
                "06",
                "Work piling up",
                "/cei",
                (),
                ("Bow Wave / CEI",),
                "Whether work is bow-waving into the future.",
            ),
            _Chapter(
                "07",
                "How we execute",
                "/performance",
                (),  # EVM + WBS now sit on the LIBRARY rail; both stay ch-07 pages
                ("Performance Summary", "EVM"),
                "How execution is actually tracking to plan.",
            ),
            _Chapter(
                "08",
                "Who is overloaded",
                "/resources",
                (),
                ("Resources",),
                "Where resource pressure concentrates.",
            ),
        ),
    ),
    (
        "ACT III · OUTLOOK",
        (
            _Chapter(
                "09",
                "Where it lands",
                "/forecast",
                (("S-Curve", "/scurve"),),
                ("Forecast", "S-Curve"),
                "Where the finish is most likely to land.",
            ),
            _Chapter(
                "10",
                "What changed",
                "/compare",
                (),
                ("Compare",),
                "What actually changed between two versions.",
            ),
            _Chapter(
                "11",
                "What could go wrong",
                "/sra",
                (("Risks & Opportunities", "/risks"),),
                ("Risk Analysis (SRA)", "Risks & Opportunities"),
                "What could still bite the finish.",
            ),
            _Chapter(
                "12",
                "The briefing",
                "/briefing",
                (("Diagnostic Brief", "/brief"),),
                ("Executive Briefing", "Diagnostic Brief"),
                "The one-page verdict for leadership.",
            ),
        ),
    ),
    # ── Off-spine rails (ADR-0425) ─────────────────────────────────────────────────────────
    # The prototype groups the non-story pages into FORENSICS / LIBRARY / CONTROL / SETUP rather
    # than one mixed SETUP rail. Nav PLACEMENT only: chapter membership still comes from `titles`
    # / `_page(..., chapter=…)`, so /integrity and /scorecards remain Chapter 02 pages and /evm,
    # /wbs, /card remain Chapter 07/01 drills — their kickers and Continue segues are unchanged.
    (
        "FORENSICS",
        (
            _Chapter(
                "",
                "Schedule Integrity",
                "/integrity",
                (),
                (),  # "Schedule Integrity" stays a Chapter-02 title — see integrity.py
                "Which record edits moved dates, and how much slip those edits absorb.",
            ),
        ),
    ),
    (
        "LIBRARY",
        (
            _Chapter(
                "",
                "Metric Workbench",
                "/workbench",
                (),
                ("Metric Workbench",),
                "Build and compare any metric against the population you choose.",
            ),
            _Chapter(
                "",
                "WBS Rollup",
                "@wbs",
                (),
                (),
                "Planned versus earned progress for every branch of the breakdown.",
            ),
            _Chapter(
                "",
                "Schedule ID Card",
                "@card",
                (),
                (),
                "What one file is: population, calendars, constraints and open ends.",
            ),
            _Chapter(
                "",
                "EVM",  # the deck's LIBRARY label for this screen, verbatim
                "/evm",
                (),
                (),  # "EVM" stays a Chapter-07 title
                "The full earned-value set, arranged for an analyst rather than a story.",
            ),
        ),
    ),
    (
        "CONTROL",
        (
            _Chapter(
                "",
                "Margin Dashboard",
                "/margin",
                (),
                ("Margin Dashboard",),
                "How much schedule margin is left, and whether it is enough.",
            ),
            _Chapter(
                "",
                "Standards & Execution",
                "/standards",
                (),
                ("Standards & Execution Indices",),
                "How the schedule scores against the governing standards.",
            ),
            _Chapter(
                "",
                "Assessment Scorecards",
                "/scorecards",
                (),
                (),  # "Assessment Scorecards" stays a Chapter-02 title — see scorecards.py
                "How the schedule scores against NASA STAT, GAO-10 and SRA readiness.",
            ),
        ),
    ),
    (
        "SETUP",
        (
            _Chapter(
                "",
                "Groups & Filters",
                "/groups",
                (),
                ("Groups & Filters",),
                "Scope every page to the activities you care about.",
            ),
            _Chapter(
                "",
                "AI Settings",
                "/settings",
                (),
                ("AI Settings",),
                "Choose the local model and the figure-citation mode.",
            ),
            _Chapter(
                "",
                "Metric Dictionary",
                "/help",
                (),
                ("Metric Dictionary",),
                "Every metric, its formula, and where the formula comes from.",
            ),
        ),
    ),
)

# The rails that sit OFF the narrative spine: they carry no chapter number, take no part in the
# Continue segue / progress dashes, and render with the muted `setup` treatment. Membership is
# declared here rather than inferred from the label so adding a rail can never silently inject a
# utility page into the story order.
_OFF_SPINE: frozenset[str] = frozenset({"FORENSICS", "LIBRARY", "CONTROL", "SETUP"})


def _role_strip(state: SessionState) -> str:
    """The front-page "Who's analyzing today?" picker + the active role's Start-here strip
    (v4 F4, ADR-0255). Emphasis only: everything stays reachable under every role, and the
    "Show everything" pill (no role) reproduces the pre-F4 page exactly. Cards whose spine
    route cannot resolve yet (``@analysis`` with nothing loaded) are skipped, not broken."""
    active = _ROLE_BY_ID.get(state.role) if state.role else None

    def _pill(rid: str, label: str, blurb: str, is_active: bool) -> str:
        cls = "role-card active" if is_active else "role-card"
        return (
            f'<form method=post action="/role" class=roleform>'
            f'<input type=hidden name=role value="{_e(rid)}">'
            f'<button type=submit class="{cls}" aria-pressed={"true" if is_active else "false"} '
            f'title="{_e(blurb)}">{_e(label)}</button></form>'
        )

    pills = "".join(_pill(r.id, r.label, r.blurb, active is r) for r in _ROLES)
    pills += _pill("", "Show everything", "No role — the full console, unfiltered.", active is None)
    strip = (
        "<div class=panel><h2>Who&rsquo;s analyzing today?</h2>"
        "<p class=muted>Pick a role to get a tailored <b>Start here</b> strip, highlighted "
        "chapters in the nav, and a role-matched landing page after an import. Nothing is hidden "
        "and no number changes &mdash; every page stays reachable under every role.</p>"
        f"<div class=role-strip>{pills}</div>"
    )
    if active is None:
        return strip + "</div>"
    cards = ""
    for title, route, why in active.cards:
        href = _resolve_route(state, route)
        if not href or (route == "@analysis" and not state.schedules):
            continue  # unresolvable until a schedule is loaded — skipped, never a dead link
        cards += (
            f'<a class=start-card href="{href}"><b>{_e(title)}</b>'
            f"<span class=muted>{_e(why)}</span></a>"
        )
    return (
        strip
        + f"<h3>Start here &mdash; {_e(active.label)}</h3>"
        + f"<p class=muted>{_e(active.blurb)}</p>"
        + f"<div class=start-strip>{cards}</div></div>"
    )


# Narrative order for the Continue footer + progress (Import → Mission Control → 01…12; the
# Forensics / Library / Control / Setup rails are off-spine).
_STORY_ORDER: tuple[_Chapter, ...] = tuple(
    ch for label, chapters in _SPINE for ch in chapters if label not in _OFF_SPINE
)
# Numbered chapters only, for the progress dashes.
_STORY_CHAPTERS: tuple[_Chapter, ...] = tuple(c for c in _STORY_ORDER if c.num)


def _build_title_map() -> dict[str, _Chapter]:
    m: dict[str, _Chapter] = {}
    for _label, chapters in _SPINE:
        for ch in chapters:
            for t in ch.titles:
                m.setdefault(t, ch)
    return m


# Chapters whose page carries a dynamic title (e.g. /analysis renders the schedule name) can't be
# resolved from the title, so a route may name its chapter explicitly via _page(..., chapter=…).
_CHAPTER_BY_NUM: dict[str, _Chapter] = {
    ch.num: ch for _label, chapters in _SPINE for ch in chapters if ch.num
}


_TITLE_TO_CHAPTER: dict[str, _Chapter] = _build_title_map()


def _resolve_route(state: SessionState, route: str) -> str:
    """Resolve a spine ``route`` to a real URL. ``@analysis`` / ``@wbs`` / ``@card`` point at the
    first loaded schedule's report (the dropzone when nothing is loaded)."""
    _PER_FILE = {"@analysis": "/analysis/", "@wbs": "/wbs/", "@card": "/card/"}
    base = _PER_FILE.get(route)
    if base is not None:
        first_key = next(iter(state.schedules), None)
        if first_key is None:
            return "/" if route == "@analysis" else ""
        return base + quote(first_key)
    return route


def _render_target_control(state: SessionState) -> str:
    """The global Analysis-Target selector: pick the activity every metric, path, forecast and the
    briefing verdict is measured to (Project finish = the whole schedule). The dropdown lists the
    **milestones** across the ACTIVE project's loaded versions (ADR-0284 / Fix E — a milestone
    deleted in a later version is still selectable, but another project's milestone never leaks in,
    which also stops a shared UniqueID from showing a foreign project's label); the **UID box**
    measures to ANY activity by UniqueID — a non-milestone, or a UID that exists only in an older
    version. Both post to ``/target`` (which drives the endpoint scope and the SRA/SSI focus). A
    non-milestone target still shows as a selected custom dropdown option."""
    seen: dict[int, str] = {}
    for _key, s in state.ordered_versions():
        for t in s.tasks:
            if t.is_milestone and not t.is_summary and t.unique_id not in seen:
                seen[t.unique_id] = t.name or f"UID {t.unique_id}"
    cur = state.target_uid
    opts = ['<option value="">Project finish (whole schedule)</option>']
    for uid, name in seen.items():
        sel = " selected" if uid == cur else ""
        opts.append(f'<option value="{uid}"{sel}>{_e(f"{name} · UID {uid}")}</option>')
    if cur is not None and cur not in seen:
        opts.append(f'<option value="{cur}" selected>UID {cur} (custom)</option>')
    options = "".join(opts)
    return (
        '<form action="/target" method=post class="navform targetform" '
        'title="Measure every view to one milestone (Project finish = the whole schedule)" '
        'data-sf-hint="Pick a milestone every metric, path, forecast and the briefing verdict is '
        "measured to (Project finish uses the whole schedule), or enter any activity's UID at right.\">"
        '<input type=hidden name=next_url value="/">'
        "<label>Measure to "
        f"<select name=uid data-no-i18n data-sf-autosubmit>{options}</select></label>"
        "</form>"
        '<form action="/target" method=post class="navform targetform sf-uid-form" '
        'data-sf-hint="Measure to ANY activity by UniqueID — including a non-milestone or a milestone '
        "that was deleted in a later version. The UID is matched across every loaded version; a blank "
        'or unknown UID clears back to Project finish.">'
        '<input type=hidden name=next_url value="/">'
        "<label class=sf-uid-ctl>or UID "
        '<input type=number name=uid min=1 step=1 inputmode=numeric placeholder="any UID…" '
        'data-no-i18n aria-label="Measure to any activity by UniqueID"></label>'
        "<button type=submit class=linkbtn data-no-i18n>Set</button>"
        "</form>"
    )


def _render_nav(state: SessionState) -> str:
    """The story-spine navigation: three acts / twelve chapters (with folded beat links) plus the
    off-spine Load / Overview / Setup rails, followed by the session controls. Rendered server-side
    so the milestone target selector and the chapter-01 link can read the loaded session."""
    lang = i18n.normalize(state.language)
    lang_options = "".join(
        f'<option value="{code}"{" selected" if code == lang else ""}>{_e(name)}</option>'
        for code, name in i18n.LANGUAGES.items()
    )

    # v4 F4 (ADR-0255): the active role's card routes get a nav HIGHLIGHT — emphasis only,
    # every chapter stays rendered and reachable regardless of role.
    role = _ROLE_BY_ID.get(state.role) if state.role else None
    role_routes: frozenset[str] = (
        frozenset(route for _t, route, _w in role.cards) if role else frozenset()
    )

    def _chapter_link(ch: _Chapter) -> str:
        href = _resolve_route(state, ch.route) or "/"
        num = f"<span class=ch-num>{ch.num}</span>" if ch.num else ""
        beats = ""
        beat_links = []
        for lbl, route in ch.beats:
            r = _resolve_route(state, route)
            if r:
                beat_links.append(f'<a href="{r}">{_e(lbl)}</a>')
        if beat_links:
            beats = "<span class=nav-beats>" + "".join(beat_links) + "</span>"
        hl = (
            " role-hl"
            if ch.route in role_routes or any(rt in role_routes for _lbl, rt in ch.beats)
            else ""
        )
        # ADR-0311: the DoD asks for a "nav entry with takeaway". A numbered chapter surfaces its
        # takeaway through the Continue segue, but an OFF-SPINE Setup page has no segue by design —
        # so its takeaway had nowhere to go and the four Setup entries carried "". They now carry
        # real text, surfaced here as the link's tooltip so the takeaway reaches the reader on the
        # one nav entry that cannot show it any other way.
        tip = f' title="{_e(ch.takeaway)}"' if ch.takeaway else ""
        return (
            f'<a class="nav-chapter{hl}" href="{href}"{tip}>{num}'
            f"<span class=ch-label>{_e(ch.label)}</span></a>{beats}"
        )

    sections = ""
    for sect_label, chapters in _SPINE:
        # A per-file rail entry (@wbs / @card) has no URL until a schedule is loaded. Drop it
        # rather than render it pointing at "/" — the same "skipped, not broken" rule the folded
        # beats and the role Start-here cards already follow (ADR-0255).
        shown = [c for c in chapters if _resolve_route(state, c.route)]
        if not shown:
            continue
        links = "".join(_chapter_link(c) for c in shown)
        cls = "nav-sect setup" if sect_label in _OFF_SPINE else "nav-sect"
        sections += (
            f'<div class="{cls}"><span class=nav-sect-label>{_e(sect_label)}</span>{links}</div>'
        )

    controls = (
        "<div class=nav-controls>"
        '<form action="/session/wipe" method=post class=navform '
        'data-sf-confirm="Wipe all loaded schedules?">'
        "<button type=submit class=linkbtn>Wipe Session</button></form>"
        '<a href="#" id=sfQuitLink title="Stop the local server and exit">Quit</a>'
        '<button id=sfResetView type=button class="linkbtn sf-reset-view" data-no-i18n '
        'title="Clear every selection you made on THIS page (inputs, filters, toggles, remembered '
        'view) and return to its default view">&#10226; Reset view</button>'
        + _render_target_control(state)
        # nosec B608 — this is HTML markup (a <select> control), not a SQL query; the B608
        # heuristic false-matches the "select"/option keywords in the concatenated view picker.
        + '<label class=ui-scale-ctl title="Choose the console view — four complete themes '  # nosec B608
        '(ADR-0195)">View'
        "<select id=themeSelect data-no-i18n>"
        "<option value=console>CONSOLE — mission control</option>"
        "<option value=daylight>DAYLIGHT — clean light</option>"
        "<option value=apollo>APOLLO — retro CRT</option>"
        "<option value=jarvis>JARVIS — HUD</option>"
        "</select></label>"
        "<button id=themeToggle type=button class=linkbtn data-no-i18n "
        'title="Toggle daylight vs your last dark view" '
        'data-sf-hint="Flips between DAYLIGHT and the last dark view you used (Console, Apollo or '
        'JARVIS). Pick any of the four views from the View menu.">Theme</button>'
        '<label class=ui-scale-ctl title="Rescale the whole page — text and layout together">Size'
        "<select id=uiScale data-no-i18n>"
        '<option value="0.9">90%</option><option value="1">100%</option>'
        '<option value="1.1">110%</option>'
        '<option value="1.25">125%</option><option value="1.5">150%</option>'
        '<option value="1.75">175%</option>'
        "</select></label>"
        '<form action="/language" method=post class="navform langform" '
        'title="Display language for the UI and AI results">'
        "<label>Language: <select name=lang data-no-i18n "
        f"data-sf-autosubmit>{lang_options}</select></label>"
        "</form>"
        "</div>"
    )
    return f"<nav><div class=nav-spine>{sections}</div>{controls}</nav>"


def _utility_takeaway(headline: str, lede: str) -> str:
    """The takeaway h1 + context line the DoD requires of any page (ADR-0311, rank 12).

    Rank 12's pages are Setup utilities and per-file drills, not spine chapters, so they take the
    kicker/no-segue treatment ADR-0311 settled — but the DoD's *takeaway h1 + context line* applies
    to every page regardless of where it sits in the story. `DESIGN-SYSTEM.md` §5: a headline states
    a FINDING, not a topic. Every figure passed in here must already be rendered further down the
    same page, so the number the reader sees first is one they can verify below it, and a missing
    value must arrive as an em dash rather than a fabricated zero.
    """
    return f'<h1 class="page-takeaway" data-no-i18n>{headline}</h1><p class="page-lede">{lede}</p>'


def _chapter_kicker(title: str, chapter: _Chapter | None = None) -> str:
    """The slim chapter kicker above a page's content: ``CHAPTER NN · NAME`` (story position).
    ``chapter`` overrides title-based resolution for dynamic-title pages (e.g. /analysis)."""
    ch = chapter if chapter is not None else _TITLE_TO_CHAPTER.get(title)
    if ch is None:
        return ""
    prefix = f"CHAPTER {ch.num} · " if ch.num else ""
    return f"<div class=chapter-kicker data-no-i18n>{prefix}{_e(ch.label.upper())}</div>"


def _story_footer(state: SessionState, title: str, chapter: _Chapter | None = None) -> str:
    """The Continue → next-chapter footer + the STORY-SO-FAR progress dashes, on every spine page.
    ``chapter`` overrides title-based resolution for dynamic-title pages (e.g. /analysis)."""
    ch = chapter if chapter is not None else _TITLE_TO_CHAPTER.get(title)
    if ch is None:
        return ""
    try:
        idx = _STORY_ORDER.index(ch)
    except ValueError:
        return ""
    dashes = ""
    for c in _STORY_CHAPTERS:
        state_cls = " cur" if c is ch else ""
        dashes += (
            f'<span class="story-dash{state_cls}" data-route="{_resolve_route(state, c.route)}" '
            f'title="{_e(c.num + " " + c.label)}"></span>'
        )
    progress = (
        "<div class=story-progress data-no-i18n>"
        "<span class=story-so-far>STORY SO FAR</span>"
        f"<span class=story-dashes>{dashes}</span></div>"
    )
    cont = ""
    if idx + 1 < len(_STORY_ORDER):
        nxt = _STORY_ORDER[idx + 1]
        href = _resolve_route(state, nxt.route)
        if href:
            label = f"Chapter {nxt.num} → {nxt.label}" if nxt.num else f"{nxt.label} →"
            seg = _e(nxt.takeaway) if nxt.takeaway else ""
            cont = (
                "<div class=continue-foot data-no-i18n>"
                f"<span class=continue-seg>{seg}</span>"
                f'<a class="btn continue-btn" href="{href}">{_e(label)}</a></div>'
            )
    return f"<div class=story-foot>{progress}{cont}</div>"


#: The compliance drawer's prose, with ONE substitution slot for the locality sentence. Lifted
#: out of ``_LAYOUT`` by ADR-0426 so the boot screen — which renders no ``_LAYOUT`` — carries the
#: byte-identical notice instead of a second, drift-prone copy. Design system §6 says the drawer
#: sits under the top bar on EVERY page; two copies of a regulatory notice is how one of them
#: quietly stops matching the other.
_DRAWER_HTML = """<details class=compliance-drawer id=complianceDrawer>
<summary>Handling &amp; export-control notice — click to review (CUI / ITAR / EAR)</summary>
<div class=compliance-body>
<h3>Controlled Unclassified Information (CUI)</h3>
<p>Treat every loaded schedule and every derived metric on these pages as CUI unless the project
is explicitly marked UNCLASSIFIED in AI Settings. Handle per 32 CFR Part 2002 and your
organization's CUI program: store on approved systems only, share only with a lawful government
purpose, and destroy per records schedules. {locality}</p>
<h3>Export control (ITAR / EAR)</h3>
<p>WARNING — Schedules for defense or space programs may contain technical data subject to the
International Traffic in Arms Regulations (ITAR, 22 CFR 120&ndash;130) or the Export
Administration Regulations (EAR, 15 CFR 730&ndash;774). Do not export, release, or disclose such
data to foreign persons, in the U.S. or abroad, without proper authorization. Violations carry
severe criminal and civil penalties.</p>
<h3>Your responsibility</h3>
<p>The markings above reflect the session's declared classification &mdash; not a review of your
data. You remain responsible for confirming the actual sensitivity, markings, and distribution
statements of every file you load and every report you export.</p>
</div>
</details>"""


def _compliance_drawer(state: SessionState) -> str:
    """The compliance drawer, locality sentence resolved for this session.

    The locality sentence is conditioned on the SAME observed derivation as the persistent banner
    (DoD 001b): the absolute assurance may only print while every constructible AI candidate — and
    the actually-routed backend — is provably local. The non-local branch is unreachable with this
    repo's loopback-validated constructors; it exists so a wired gateway (001c) or a patched
    install can never render the absolute claim.
    """
    ai_banner = _observed_banner(state)
    locality = (
        "This tool enforces the technical side — it binds 127.0.0.1 only and no schedule "
        "content ever leaves this machine."
        if not ai_banner.cloud_active
        else "This tool binds 127.0.0.1 for its own pages, but the session's AI is configured "
        f"for a non-local endpoint ({_e(ai_banner.endpoint or '')}) — schedule content sent to "
        "the AI leaves this machine. The engine's computations remain local."
    )
    return _DRAWER_HTML.format(locality=locality)


def _cui_marking(state: SessionState) -> tuple[str, str]:
    """The CUI banner's ``(css class, text)`` — the ONE derivation of the page marking.

    Extracted from :func:`_page` by ADR-0426 so the boot screen, which does not render through
    the story chrome, cannot drift from the marking every other page shows. Default CLASSIFIED
    marks CUI; only the operator-asserted UNCLASSIFIED mode drops the controls marking. Kept out
    of the i18n pass by its ``data-no-i18n`` call sites so the wording stays standard.
    """
    classified = state.ai_config.classification is Classification.CLASSIFIED
    return (
        "cui" if classified else "unclassified",
        "Controlled Unclassified Information • CUI"
        if classified
        else "Unclassified • no CUI controls asserted",
    )


def _page(
    state: SessionState,
    title: str,
    body: str,
    *,
    status_code: int = 200,
    ask_schedule: str | None = None,
    chapter: _Chapter | None = None,
    focus_file: str | None = None,
) -> HTMLResponse:
    lang = i18n.normalize(state.language)
    # NASA CUI page-marking (top + bottom banner on every page). Default CLASSIFIED → mark CUI;
    # only the operator-asserted UNCLASSIFIED mode drops the CUI controls marking. Kept out of the
    # i18n pass (data-no-i18n) so the control marking stays in its required standard wording.
    cui_class, cui_text = _cui_marking(state)
    # _bust_static: version-bust every /static URL so an upgraded install can never keep
    # executing a stale browser-cached JS/CSS (the fixed-port deployment reuses the same
    # cache origin across restarts, and StaticFiles alone sends no Cache-Control).
    return HTMLResponse(
        _bust_static(
            _LAYOUT.render(
                # _LAYOUT is a bare jinja2.Template (autoescape=False) because `body`/`banner` are
                # already-built raw HTML; `title` is the one untrusted plain-text value (derived from the
                # uploaded filename via _clean_key), so escape it here at the boundary to close the latent
                # reflected-XSS in <title> (audit F-06 / ADR-0130). The CSP allows 'unsafe-inline', so
                # escaping — not CSP — is the barrier; do NOT pass raw schedule-derived text as `title`.
                title=_e(title),
                nav=_render_nav(state),
                banner=_banner_html(state),
                body=(
                    _filter_banner(state)
                    + _endpoint_banner(state)
                    + _global_sources_banner(state, focus_file)
                    + _chapter_kicker(title, chapter)
                    + _page_explainer(title)
                    + body
                    + _ask_panel_html(state, ask_schedule)
                    + _story_footer(state, title, chapter)
                ),
                lang=lang,
                # ADR-0268: a non-executable JSON boot block (translate.js parses it) — the
                # strict script-src CSP forbids the old inline `window.SF_*=` script. The
                # catalog is only shipped when not English (no payload for en); "<" escaped
                # so imported text can never close the block.
                i18n_boot_json=json.dumps(
                    {"lang": lang, "catalog": i18n.catalog_for(lang)}
                ).replace("<", "\\u003c"),
                cui_class=cui_class,
                cui_text=cui_text,
                drawer=_compliance_drawer(state),
                # OR-06: scopes the browser's ADR-0186 page-selection memory to this
                # launch + wipe generation (persist.js clears its layers on a change)
                launch_token=state.launch_token,
            )
        ),
        status_code=status_code,
    )


def _e(text: object) -> str:
    return html.escape(str(text))


def _expandable_more(shown_html: str, hidden_items: list[str]) -> str:
    """``shown … <details>+N more</details>`` — every truncated list is expandable in place.

    ``shown_html`` is already-escaped/authored HTML for the visible prefix; ``hidden_items``
    are the already-escaped overflow entries. The operator asked that "(+N more)" never be a
    dead end — the full list opens inline (native ``<details>``, no JS, air-gap safe)."""
    if not hidden_items:
        return shown_html
    return (
        f'{shown_html} <details class=more-inline style="display:inline-block">'
        f'<summary style="display:inline;cursor:pointer" class=btn-link>+{len(hidden_items)}'
        " more</summary> "
        f"<span>{', '.join(hidden_items)}</span></details>"
    )


def _criterion_value_list(value: str | Sequence[str]) -> list[str]:
    """A criterion's selected values as a list ([] = no value restriction / field populated)."""
    if isinstance(value, str):
        return [value] if value else []
    return [v for v in value if v]


_OP_TEXT = {
    "EQUALS": "=",
    "DOES_NOT_EQUAL": "≠",
    "IS_GREATER_THAN": ">",
    "IS_LESS_THAN": "<",
    "IS_GREATER_THAN_OR_EQUAL_TO": "≥",
    "IS_LESS_THAN_OR_EQUAL_TO": "≤",
    "CONTAINS": "contains",
    "DOES_NOT_CONTAIN": "does not contain",
    "CONTAINS_EXACTLY": "contains exactly",
    "IS_WITHIN": "is within",
    "IS_NOT_WITHIN": "is not within",
    "IS_ANY_VALUE": "is any value",
}


def _criteria_text(node: SavedCriterion | None) -> str:
    """A compact, human-readable rendering of a saved filter's criteria tree (for chips/banner)."""
    if node is None:
        return "all tasks"
    if node.is_branch:
        parts = [_criteria_text(c) for c in node.children]
        joiner = " AND " if node.operator == "AND" else " OR "
        return "(" + joiner.join(parts) + ")" if len(parts) > 1 else (parts[0] if parts else "all")

    def operand_text(op: SavedOperand) -> str:
        if op.kind == "null":
            return "(none)"
        if op.kind == "prompt":
            return f"?[{op.text or 'prompt'}]"
        if op.kind == "field":
            return f"[{op.text}]"
        return op.text or ""

    ops = ", ".join(operand_text(o) for o in node.operands)
    verb = _OP_TEXT.get(node.operator, node.operator)
    return f"{node.field or '?'} {verb} {ops}".rstrip()
