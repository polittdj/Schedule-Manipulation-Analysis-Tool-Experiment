"""Axis captions come from ONE shared helper, and the remaining work is an explicit ledger.

ADR-0298 promotes the single axis-caption implementation into ``chartframe.js``
(``SFChartFrame.axisTitles``) and retires the two conflicting ones that existed in the tree
(``performance.js``'s local pair, ``scatter.js``'s centred-X + rotated-Y pair).

The regression this guards is **not** "a chart forgot a caption" — it is "someone drew a caption
a second way". That is what re-fragments the convention, and it is asserted below globally.

**Why a ledger instead of a tick-detecting regex.** The spec's heuristic (match modules that draw
SVG tick text) under-detected by half: it missed ``path.js`` and ``resources.js``, which do draw
SVG axes, and it silently said nothing about the dozen modules whose visuals are **HTML/DOM, not
SVG** — including ``gantt.js``, which is explicitly "shared Microsoft-Project-style **HTML** Gantt
timeline primitives". An SVG ``<text>`` helper cannot caption an HTML Gantt, so those modules are
recorded as a separate, named category rather than quietly skipped. Every non-exempt module must
appear in exactly one bucket; a NEW file that fits none of them fails this test, which is the
anti-regression property the heuristic could not give.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "src" / "schedule_forensics" / "web" / "static"

#: Chrome, frames, rulers and utilities — they render no data visual of their own.
#: ``timeaxis`` / ``timescale`` are the shared rulers consumed by charts that carry their own
#: captions; ``chartframe`` is the frame (and now the caption helper's home).
#:
#: ``sra_risk.js`` moved here from ``NO_SVG_AXES`` in ADR-0340. It was parked as a DOM visual
#: awaiting a caption, but it renders NO visual at all and never could: it constructs no DOM
#: whatsoever (no ``createElement``, no ``appendChild``, no ``innerHTML``) — it is the risk
#: form's days<->% derivation, and its entire output is writing ``.value`` back into inputs the
#: SERVER rendered and toggling ``aria-invalid``. A caption needs something to caption, so its
#: place in the remaining-work ledger overstated that work by one for four ADRs. Re-triaged, not
#: captioned: the honest close, and the reason the DOM ledger is a named list rather than a count.
EXEMPT = {
    "a11y.js",
    "ai_polish.js",
    "app.js",
    "ask.js",
    "chartframe.js",
    "checklist.js",
    "chrome.js",
    "colresize.js",
    "dashboard.js",
    "globe.js",
    "groups.js",
    "heartbeat.js",
    # ADR-0426: the boot screen's particle lightshow. A canvas of decorative motion, not a
    # data visual — it plots nothing, so it has no axis to caption.
    "launch.js",
    "hints.js",
    "home.js",
    "launch_audio.js",
    "legend_toggle.js",
    "mission.js",
    "panelkit.js",
    "persist.js",
    "settings.js",
    "sra_risk.js",
    "story.js",
    "sysmon.js",
    "target.js",
    "taskinfo.js",
    "theme.js",
    "timeaxis.js",
    "timescale.js",
    "tooltips.js",
    "translate.js",
    "vizhints.js",
}

#: Visuals rendered as HTML/DOM rather than SVG — tables, chip rows, DOM bars, and the HTML
#: Gantt family. ``SFChartFrame.axisTitles`` appends an SVG ``<text>``, so it does not apply to
#: them: captioning a DOM visual needs a DOM label element, which is a separate design decision
#: (deferred deliberately, ADR-0298 §Consequences — not an omission).
NO_SVG_AXES = {
    "drilldown.js",
    "driving_path.js",
    "driving_tiers.js",
    "findings_drill.js",
    "gantt.js",
    "path.js",
    "path_evolution.js",
    "ribbon_drill.js",
    "scorecards.js",
    "sra_grid.js",
    "whatif.js",
    "workbench.js",
}

#: Entries of ``NO_SVG_AXES`` that DO emit some SVG, but not an axis — so the bucket is right and
#: the "renders no SVG at all" shortcut below would wrongly reject them. Each needs a reason.
#:
#: ``path.js`` was parked in ``PENDING`` until ADR-0301 batch 2, on ADR-0298's claim that it
#: "does draw SVG axes". It does not. Its timeline is a DOM table (``tbody``, ``.path-track``
#: divs, ``rowIndex`` arithmetic); its ONLY SVG is a 2-element absolutely-positioned overlay
#: (``.pv-link``: one ``<svg>``, one ``<path>``) that draws a dependency connector between two
#: table rows. There is no chart root, no plot rect, no tick text — nothing
#: ``SFChartFrame.axisTitles`` can attach to.
#:
#: ``gantt.js`` joined for the same reason under ADR-0342. It is still the HTML-Gantt primitive
#: module — it draws no chart and owns no axis — but it is now also the home of
#: ``SFGantt.dataDateLine``, the ONE data-date marker helper, which emits a 3-node SVG group
#: (``line`` + ``text`` + ``title``) into a chart the CALLER owns. It lives here for the same
#: load-order reason ``tableCaption`` does (ADR-0340): the layout emits ``gantt.js`` in the head
#: and ``chartframe.js`` after ``</main>``, so a marker helper filed with the axis captions would
#: be undefined when the parse-time chart modules draw. An annotation is not an axis, so
#: ``NO_SVG_AXES`` remains the right bucket — but the shortcut assertion below has to be told.
#:
#: Keeping this list separate and explicit is the point: a real chart cannot land in
#: ``NO_SVG_AXES`` quietly, because parking it there ALSO requires naming it here, with a reason.
INCIDENTAL_SVG = {
    "gantt.js",
    "path.js",
}

#: DOM visuals captioned via decision B1's TABLE mechanism (ADR-0326): a native
#: ``<table><caption class="ch-atd">`` built with the table — announced by screen readers,
#: in-flow for print. Subset of ``NO_SVG_AXES``: the bucket records the MEDIUM, this records
#: the caption state within it.
#:
#: ADR-0340 completed the bucket and, in doing so, promoted the mechanism to ONE implementation:
#: ``SFGantt.tableCaption``. Before, the convention was an inline ``el("caption", …)`` — which
#: these seven modules cannot spell the same way, because their local ``el()`` helpers take three
#: different signatures (``(tag, attrs, text)``, ``(tag, {text})``, ``(tag, text, cls)``). A
#: detector that accepted all three would have been looser than the rule it claims to enforce.
#: One helper, one call shape, one tight detector — the same move ADR-0298 made for SVG.
DOM_TABLE_CAPTIONED = {
    "drilldown.js",
    "driving_tiers.js",
    "findings_drill.js",
    "ribbon_drill.js",
    "scorecards.js",
    "whatif.js",
    "workbench.js",
}

#: DOM Gantt-family modules whose time axis is named by decision B1's OTHER mechanism: the ONE
#: caption slot ``gantt.js``'s shared ``buildTierScale`` renders above the tiers whenever the
#: served page carries a ``data-ts-caption`` marker (``app.py``'s ``_TS_CAPTION_MARK``). One
#: shared edit labels all four consumers at a stroke; ``gantt.js`` itself is the primitive that
#: RENDERS the slot, not a consumer, so it stays outside both captioned buckets.
TIMESCALE_CAPTIONED = {
    "driving_path.js",
    "path.js",
    "path_evolution.js",
    "sra_grid.js",
}

#: NO_SVG_AXES entries still awaiting a caption under the B1 mechanisms — the DOM medium's
#: remaining-work ledger, mirroring ``PENDING`` for SVG. It is now EMPTY (ADR-0340), which with
#: ``PENDING`` already empty (ADR-0330) closes ADR-0298's deferral for good: every data visual in
#: the tree, in BOTH media, names its own dimensions.
#:
#: How it emptied, in one batch, because the answer was one shared helper rather than seven:
#: six modules gained a ``SFGantt.tableCaption`` call on the table they already built
#: (``drilldown`` the drill modal's grid, ``driving_tiers`` the tier table, ``findings_drill`` the
#: cited-activity list, ``ribbon_drill`` the metric drill, ``scorecards`` the reserve table — the
#: one whose row unit is a PERCENTILE, not an activity — and ``whatif`` BOTH of its grids, which
#: share a column header set and so are distinguishable only by caption). The seventh,
#: ``sra_risk.js``, was never captionable and moved to ``EXEMPT``; see the note there.
#:
#: It stays as the triage bucket for any NEW DOM visual: a module may not be parked here once it
#: calls the helper (asserted by the partition test + the detector below).
DOM_PENDING: set[str] = set()

#: SVG axis charts not yet captioned. This list SHRANK one batch at a time, and it is now
#: EMPTY — the completion signal for AXIS-TITLES (reached in ADR-0330, batch 3c-ii). It stays
#: as the triage bucket for any NEW SVG chart module: a module may not be parked here once it
#: calls the helper, and may not be listed here unless it really renders SVG — both asserted.
#:
#: How it emptied (the graduation record, kept because each entry carries a re-usable lesson):
#:
#: ``drift.js`` graduated in ADR-0303 batch 3a after being attempted and reverted once. The
#: placement answer its revert note demanded turned out to be ADR-0303's law — the caption
#: stays fixed, the DATA yields: the method rows sit 12px lower (``padT + 26``, H grown to
#: match) clearing the Y caption's 136x6px hit on the first row name, and the last row's
#: forecast date label clamps to ``H - padB - 15`` clearing the X caption's 75x3px hit at
#: 90% scale. Both collisions are MEASURED closed by ``test_axis_titles_visual.py``, which
#: walks ``/forecast`` in every theme at every scale.
#:
#: ``margin_dashboard.js`` graduated in ADR-0325 (batch 3b-i, decision A1): both charts
#: captioned, the two local "status date" quasi-captions retired into the helper, the
#: legends yielding the top-left corner to the Y caption, and ``/margin`` joining the
#: measured visual pass with its own margin-carrying serve.
#:
#: ``sra.js`` + ``volatility.js`` graduated in ADR-0329 (batch 3c-i): the six axis charts
#: between them captioned (CDF + histogram; churn + flow + area + dwell), two hand-rolled
#: quasi-captions retired into the helper, rotated ticks + the dwell count labels yielding
#: per ADR-0303, and ``/sra`` + ``/volatility`` joining the measured visual pass. The
#: tornado pair, gauge, heatmap, leaderboards, strips and ribbon are recorded
#: NOT-axis-charts (decision A1) in the ADR — no call, deliberately.
#:
#: ``sra_jcl.js`` + ``sra_ssi.js`` graduated in ADR-0330 (batch 3c-ii, the finale): the four
#: on-demand charts captioned (JCL football + cost S-curve; SSI S-curve + histogram), the
#: football's two corner quadrant %-labels clamped out of the caption bands (the ADR-0303
#: yield, the dwell-precedent static mechanism), and the measured pass taught to CLICK — a
#: dedicated cost-loaded serve (``served_sra``) because the golden pair gates the JCL panel
#: closed (no budgeted cost) and degenerates the SSI S-curve to one point (no spread). The
#: FICSM strip is a labeled bar strip and the 5x5 matrices are natively-labeled HTML tables —
#: recorded not-axis-charts (decision A1 / ADR-0326's other medium), no call, deliberately.
PENDING: set[str] = set()

CALLS_HELPER = re.compile(r"SFChartFrame\.axisTitles\s*\(")
#: Caption-drawing done any way other than the shared helper — the fragmentation this guards.
SECOND_CONVENTION = re.compile(
    r"""(rotate\(-90|axisTitle\s*=|\bxt\.textContent|\byt\.textContent)"""
)
RENDERS_SVG = re.compile(r"w3\.org/2000/svg")


def modules() -> list[Path]:
    return sorted(STATIC.glob("*.js"))


def _src(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_every_module_is_classified_exactly_once() -> None:
    """A new chart module must be triaged deliberately — it cannot slip through unnoticed."""
    names = {p.name for p in modules()}
    stale = (EXEMPT | NO_SVG_AXES | PENDING) - names
    assert not stale, f"ledger names files that no longer exist: {sorted(stale)}"

    captioned = {p.name for p in modules() if CALLS_HELPER.search(_src(p))}
    unclassified = names - EXEMPT - NO_SVG_AXES - PENDING - captioned
    assert not unclassified, (
        "these modules are in no bucket — add each to EXEMPT (no data visual), NO_SVG_AXES "
        f"(HTML/DOM visual), or PENDING (an SVG chart awaiting captions): {sorted(unclassified)}"
    )
    overlap = captioned & PENDING
    assert not overlap, f"already captioned but still parked in PENDING: {sorted(overlap)}"


@pytest.mark.parametrize("name", sorted(PENDING))
def test_pending_entries_are_really_svg_charts(name: str) -> None:
    """Keeps the remaining-work ledger honest: a DOM visual belongs in NO_SVG_AXES, not here,
    or the count of 'charts still to caption' silently overstates the work."""
    assert RENDERS_SVG.search(_src(STATIC / name)), (
        f"{name} renders no SVG — it belongs in NO_SVG_AXES, not PENDING"
    )


@pytest.mark.parametrize("name", sorted(NO_SVG_AXES))
def test_no_svg_axes_entries_really_render_no_svg(name: str) -> None:
    """The mirror check: a module parked as 'DOM visual' must not actually draw SVG axes.

    "Renders no SVG at all" is a shortcut for the real property, and ADR-0301 batch 2 found where
    it breaks: ``path.js`` renders a DOM table plus ONE two-element SVG overlay for a dependency
    connector. The bucket ("no SVG *axes*") was right for it; this assertion was not. Rather than
    swap in a cleverer regex — a chart-root/plot-rect detector was tried and mis-classified five
    modules, because every module names its geometry differently — the exception is explicit and
    must be justified in ``INCIDENTAL_SVG``.
    """
    if name in INCIDENTAL_SVG:
        pytest.skip(f"{name}: SVG present but not an axis — see INCIDENTAL_SVG")
    assert not RENDERS_SVG.search(_src(STATIC / name)), (
        f"{name} does render SVG — move it to PENDING (or caption it) rather than exempting it"
    )


def test_dom_caption_buckets_partition_no_svg_axes() -> None:
    """The B1 ledger stays honest the same way the SVG one does: every DOM visual is in exactly
    one caption state — table-captioned, timescale-captioned, still pending, or the one named
    primitive — and nothing outside NO_SVG_AXES can claim a DOM caption state."""
    assert DOM_TABLE_CAPTIONED <= NO_SVG_AXES
    assert TIMESCALE_CAPTIONED <= NO_SVG_AXES
    assert DOM_PENDING <= NO_SVG_AXES
    assert not DOM_TABLE_CAPTIONED & TIMESCALE_CAPTIONED
    assert not (DOM_TABLE_CAPTIONED | TIMESCALE_CAPTIONED) & DOM_PENDING
    leftover = NO_SVG_AXES - DOM_TABLE_CAPTIONED - TIMESCALE_CAPTIONED - DOM_PENDING
    assert leftover == {"gantt.js"}, (
        "every NO_SVG_AXES module must be table-captioned, timescale-captioned, in DOM_PENDING, "
        f"or the slot-rendering primitive itself — unclassified: {sorted(leftover)}"
    )


DOM_CAPTION_CALL = re.compile(r"SFGantt\.tableCaption\s*\(")
#: The DOM medium's caption class. Only the module that IMPLEMENTS the two B1 mechanisms may
#: name it; a caller naming it directly is a second convention (see the test below).
DOM_CAPTION_CLASS = "ch-atd"
#: The one module allowed to name it — it implements BOTH B1 mechanisms.
DOM_CAPTION_OWNER = "gantt.js"


@pytest.mark.parametrize("name", sorted(DOM_TABLE_CAPTIONED))
def test_dom_table_captioned_modules_really_build_a_caption(name: str) -> None:
    """The executable detector for B1's table mechanism: the module must caption its table
    through the shared helper (workbench and whatif each caption two tables)."""
    assert DOM_CAPTION_CALL.search(_src(STATIC / name)), (
        f"{name} is listed DOM_TABLE_CAPTIONED but never calls SFGantt.tableCaption"
    )


def test_no_module_reimplements_the_dom_caption() -> None:
    """The DOM medium's copy of THE regression this file exists for.

    ``test_no_module_reimplements_the_caption_helper`` closes this for SVG; before ADR-0340 the
    DOM side had no equivalent, and it was drifting in exactly the predicted way — ``workbench.js``
    hand-rolled the caption element inline, so a second caller would have hand-rolled its own,
    in its own ``el()`` dialect. Now the class is named in ONE module, which is also the only
    module that renders either B1 mechanism (the table caption and the timescale slot).
    """
    offenders = [
        p.name for p in modules() if p.name != DOM_CAPTION_OWNER and DOM_CAPTION_CLASS in _src(p)
    ]
    assert not offenders, (
        f"DOM captions must be built only by SFGantt.tableCaption / buildTierScale's slot in "
        f"{DOM_CAPTION_OWNER} — these name .{DOM_CAPTION_CLASS} themselves: " + ", ".join(offenders)
    )


def test_the_dom_caption_helper_is_reachable_before_every_caller_runs() -> None:
    """Placement, not merely existence — the load-order trap ADR-0340 was written around.

    Every table-captioning module is a script inside ``<main>``; the layout emits
    ``chartframe.js`` (the SVG helper's home) AFTER ``<main>``, and ``whatif.js`` renders
    SYNCHRONOUSLY at parse time. Had the DOM helper been added to ``SFChartFrame``, whatif's
    caption would silently never render while every source-level assertion above still passed.
    ``gantt.js`` is emitted in the head, before ``<main>`` — that ordering IS the fix, so it is
    pinned here rather than left as a comment.
    """
    # ADR-0349 (monolith split, phase 2): `_LAYOUT` — and therefore every script-order fact this
    # test asserts — now lives in `web/chrome.py`. The subject is the LAYOUT, so the guard follows
    # it; reading `app.py` here would silently pass on a file that no longer contains the layout.
    app = (ROOT / "src" / "schedule_forensics" / "web" / "chrome.py").read_text(encoding="utf-8")
    # Anchor to the LAYOUT, not to whichever occurrence comes first in the file: gantt.js is also
    # re-included by an individual page, and "<main>" also appears in a comment.
    head = app[app.index("_LAYOUT = Template(") : app.index("<main>{{ banner }}")]
    assert '<script src="/static/gantt.js"></script>' in head, (
        "gantt.js must be emitted in the layout HEAD, before <main> — every table-captioning "
        "module is a body script, and whatif.js captions at parse time"
    )
    assert app.index("</main>") < app.index('<script src="/static/chartframe.js"></script>'), (
        "this test's premise moved: chartframe.js is no longer emitted after </main>, so the "
        "reason the DOM helper lives in gantt.js needs re-deriving (do not just delete this)"
    )


@pytest.mark.parametrize("name", sorted(TIMESCALE_CAPTIONED))
def test_timescale_captioned_modules_really_consume_the_slotted_header(name: str) -> None:
    """The executable detector for B1's timescale mechanism, half one: every listed module must
    actually draw its header through the shared builder that renders the slot."""
    assert "SFGantt.buildTierScale(" in _src(STATIC / name), (
        f"{name} is listed TIMESCALE_CAPTIONED but never calls SFGantt.buildTierScale"
    )


def test_the_timescale_slot_exists_and_every_consumer_page_serves_the_marker() -> None:
    """The executable detector, half two: the slot must exist in the shared builder, and the
    caption text must actually be SERVED on the four hosting pages (/path, /evolution,
    /driving-path, /sra). A module cannot count as captioned by a slot no page feeds.

    Repointed with the split (the ADR-0349 trap): ``_TS_CAPTION_MARK`` is DEFINED in
    ``components.py`` since ADR-0373 descended it (the /sra body moved to ``sra.py`` while
    three routes still serve the marker from ``app.py``), so the counter reads each file
    for what it actually holds — three route insertions in ``app.py``, the /sra body's one
    in ``sra.py``, the definition in ``components.py``."""
    gantt = _src(STATIC / "gantt.js")
    assert 'querySelector("[data-ts-caption]")' in gantt
    assert "g-tscap ch-atd" in gantt, "the slot row must carry the DOM caption class"
    web = ROOT / "src" / "schedule_forensics" / "web"
    app = (web / "app.py").read_text(encoding="utf-8")
    sra = (web / "sra.py").read_text(encoding="utf-8")
    components = (web / "components.py").read_text(encoding="utf-8")
    assert "_TS_CAPTION_MARK = " in components, "the marker's definition left components.py"
    # the re-export line carries the name twice (`X as X`); the three route insertions are extra
    assert app.count("_TS_CAPTION_MARK") >= 5, (
        "the /path, /evolution and /driving-path routes must serve the data-ts-caption marker"
    )
    assert sra.count("_TS_CAPTION_MARK") >= 1, "the /sra body must serve the data-ts-caption marker"
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    for rule in (".g-tscap", ".g-scale-capped"):
        assert rule in css, f"{rule} missing — the slot would render unstyled"


def test_the_dom_caption_class_reads_the_token_not_a_literal() -> None:
    """`.ch-atd` is `.ch-at`'s DOM sibling: same token, same case rule — only `color` may
    differ from the SVG class's `fill` (ADR-0326's one-convention-per-medium)."""
    css = (STATIC / "base.css").read_text(encoding="utf-8")
    assert "font-size:var(--sf-fs-axis-title)" in css.split(".ch-atd{", 1)[1].split("}", 1)[0]
    assert "color:var(--muted)" in css.split(".ch-atd{", 1)[1].split("}", 1)[0]


def test_the_incidental_svg_exception_cannot_rot() -> None:
    """The escape hatch above is only safe while it stays small, justified, and TRUE.

    Three ways it could quietly become a dumping ground, each closed here: an entry that is not
    actually parked as a DOM visual; an entry that renders no SVG at all (so the exception was
    never needed and now hides nothing but itself); and an entry that has since gained real
    captions.
    """
    assert INCIDENTAL_SVG <= NO_SVG_AXES, (
        "INCIDENTAL_SVG may only excuse NO_SVG_AXES entries: "
        f"{sorted(INCIDENTAL_SVG - NO_SVG_AXES)}"
    )
    for name in sorted(INCIDENTAL_SVG):
        src = _src(STATIC / name)
        assert RENDERS_SVG.search(src), (
            f"{name} renders no SVG at all — it needs no exception; drop it from INCIDENTAL_SVG"
        )
        assert not CALLS_HELPER.search(src), (
            f"{name} calls axisTitles — it is a captioned chart, not a DOM visual"
        )


def test_captioned_modules_pass_both_labels() -> None:
    """One-axis captions are not acceptable: a captioned module must supply both labels."""
    for p in modules():
        if not CALLS_HELPER.search(_src(p)):
            continue
        src = _src(p)
        assert "xLabel" in src and "yLabel" in src, (
            f"{p.name} calls axisTitles but never supplies both xLabel and yLabel"
        )


def test_no_module_reimplements_the_caption_helper() -> None:
    """THE regression this file exists for: captions drawn a second way (ADR-0195, one
    convention). Only chartframe.js may contain caption-drawing code."""
    offenders = [
        p.name for p in modules() if p.name != "chartframe.js" and SECOND_CONVENTION.search(_src(p))
    ]
    assert not offenders, (
        "axis captions must be drawn only by SFChartFrame.axisTitles — these draw their own: "
        + ", ".join(offenders)
    )


def test_the_helper_takes_its_size_from_the_token_not_a_literal() -> None:
    """A numeric size in JS would fork the type ramp back into 30 modules."""
    frame = _src(STATIC / "chartframe.js")
    # the WHOLE caption block, not just axisTitles(): the node-building helper sits above it, and
    # a numeric size planted there escaped an earlier, narrower slice of this assertion.
    block = frame[frame.index("shared axis captions") : frame.index("window.SFChartFrame =")]
    assert "font-size" not in block, "the caption block must not set a font-size in JS"
    assert "fill" not in block, "the caption block must not set a fill in JS (.ch-at owns colour)"
    assert '"ch-at"' in block, "axisTitles must apply the .ch-at class"

    css = (STATIC / "base.css").read_text(encoding="utf-8")
    assert "--sf-fs-axis-title:" in css, "the axis-caption size token must be defined"
    assert "font-size:var(--sf-fs-axis-title)" in css, ".ch-at must read the token"


def test_the_helper_is_available_on_every_page() -> None:
    """chartframe.js is layout-global, so no chart has to import anything to caption its axes."""
    # the layout moved to `web/chrome.py` (ADR-0349) — "layout-global" is a claim about the layout
    app = (ROOT / "src" / "schedule_forensics" / "web" / "chrome.py").read_text(encoding="utf-8")
    assert '<script src="/static/chartframe.js"></script>' in app


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH (local-gate tool)")
def test_the_dom_caption_helper_behaves_under_node() -> None:
    """The DOM helper's behaviour, for the same reason the SVG one has a harness (ADR-0289): the
    ledger above proves a module CALLS ``SFGantt.tableCaption``, never that the call produces a
    caption. The harness boots gantt.js against a DOM stub and drives it — including the
    assertion that only execution can make: the caption lands as the table's FIRST child even
    when rows already exist (an ``appendChild`` implementation passes every source pin in this
    file and fails there)."""
    node = shutil.which("node")
    assert node is not None
    harness = Path(__file__).parent / "js" / "dom_caption_harness.mjs"
    proc = subprocess.run(  # fixed argv, repo-local harness
        [node, str(harness)], cwd=ROOT, capture_output=True, text=True, timeout=120
    )
    assert proc.returncode == 0, f"harness failed:\n{proc.stdout}\n{proc.stderr}"
    assert proc.stdout.rstrip().endswith("OK dom captions"), proc.stdout


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH (local-gate tool)")
def test_the_helper_behaves_under_node() -> None:
    """Placement, the .ch-at hook, and the no-numeric-type law are BEHAVIOUR, and a source pin
    cannot catch a behaviour (ADR-0289). The harness boots chartframe.js against a DOM stub and
    drives axisTitles for real; it also pins that the Y caption is never rotated, which is the
    convention this ADR exists to retire."""
    node = shutil.which("node")
    assert node is not None
    harness = Path(__file__).parent / "js" / "axis_titles_harness.mjs"
    proc = subprocess.run(  # fixed argv, repo-local harness
        [node, str(harness)], cwd=ROOT, capture_output=True, text=True, timeout=120
    )
    assert proc.returncode == 0, f"harness failed:\n{proc.stdout}\n{proc.stderr}"
    assert proc.stdout.rstrip().endswith("OK axis titles"), proc.stdout
