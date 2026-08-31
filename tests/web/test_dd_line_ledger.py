"""The data-date line is required on every TIME-AXIS chart — and that population is a ledger.

``DESIGN-SYSTEM.md`` §chart-contract: "Data date: always a red vertical line labeled ``DD`` /
``DATA DATE``, on every time-axis chart, no exceptions." The DoD checklist repeats it. Nothing
enforced it, so this module is the census — the DD-line counterpart to ``test_axis_titles.py``.

**The population is re-derived, never hand-listed.** Every chart already DECLARES its own axes,
in the ``SFChartFrame.axisTitles`` call ADR-0298 made universal. So the buckets below are keyed
by ``(module, line)`` and every one is re-read from disk and CHECKED against the labels that
justify it. A hand-typed list of "the time-axis charts" would be a second source of truth that
drifts the first time a chart is added; this cannot, because a new call site fails the partition
test and a re-labelled axis fails its bucket's predicate.

**"Time axis" is narrower than "ordered by time", and narrower again than "denominated in
dates".** The brief named three exclusions. There are twenty-one, in three families:

* the **version axis** (``margin``, ``margin_dashboard``'s burn-down, ``trend``'s five and three
  of ``volatility``'s): ordered by time, but CATEGORICAL, one tick per loaded file. A DD line has
  no position on such an axis because *every version has its own data date*.
* the **outcome axis** (ADR-0342 — ``sra`` x2, ``sra_jcl`` L136, ``sra_ssi`` x2): a distribution
  over a SIMULATED FINISH, which is denominated in dates but is not a timeline. See below; this
  family was measured, not assumed.
* plain **non-time** axes (float bands, WBS branches, a metric, ``sra_jcl``'s EAC).

Note the collision the version family creates, and why the order of the checks below matters:
``margin.js``'s xLabel is **"Schedule version (data date)"** — it contains the words "data date"
while being the clearest case of an axis that must NOT carry a DD line. The version check
therefore runs BEFORE the date check, exactly as ``ai/qa.py``'s identifier check runs before its
derivation check.

**Two reclassifications this round, both from measurement (ADR-0342).**

``margin_dashboard``'s burn-down was in TIME_AXIS with xLabel "Status date". Rendered in chromium
with deliberately irregular status dates — 1 week, 1 week, then 15 weeks apart — it spaced all
four versions EVENLY: its ``x(i) = L + (R-L)*i/(n-1)`` is one slot per loaded version, so the
15-week jump got the same pixel width as the 1-week gaps and two ticks both read "2026-03". It is
``margin.js``'s axis wearing a date's name. Its caption now names the version and it sits in
VERSION_AXIS. Its SIBLING, the erosion chart, is the opposite case and stayed: ``x(t)`` is linear
in milliseconds and ``tmax`` is EXTENDED to the projected zero-margin date, so the latest status
date is exactly the boundary between measured history and projection — the same render bunched
the first three versions at the left and put the fourth far right. One module, two charts, two
different answers, which is why this ledger is keyed by CALL SITE.

The five SRA sites all declared "Finish date" and were all recorded as pending. They are a
distribution over a simulated OUTCOME, and the data date is not on that axis at all — measured on
the ``project2_5`` golden: schedule status date **2026-08-27**, ``/api/sra`` CDF domain
**2028-01-21 → 2028-01-28**. The data date sits ~17 months to the LEFT of a 7-day, index-spaced
window. That is structural rather than fixture-specific — a Monte Carlo of the project finish
samples an outcome that is necessarily at or after the data date — so clamping a marker to the
left edge would assert the data date IS the earliest simulated finish, a figure the engine never
produced (Law 2). The internal-consistency check agrees: ``sra_jcl.js`` L136 is the joint
(finish, EAC) scatter whose SIBLING cost axis at L189 was already excluded, and ``histogram.js`` /
``scatter.js`` — distributions over an outcome variable — were already excluded too. The only
thing that made these five look different is that their outcome is denominated in dates.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "src" / "schedule_forensics" / "web" / "static"

#: Charts whose X axis is a real calendar/period axis — the DD line's population.
TIME_AXIS = {
    ("cei.js", 226),
    ("curves.js", 386),
    ("drift.js", 136),
    ("margin_dashboard.js", 323),
    ("resources.js", 243),
    ("scurve.js", 168),
}

#: X is a quantity, a category or a metric — not time. The DD line does not apply.
#: ``sra_jcl.js`` L189 is the COST axis the brief called out: the SAME module carries a
#: finish-date chart at L136, which is why this ledger is keyed by CALL SITE and not by module.
NOT_TIME_AXIS = {
    ("histogram.js", 243),
    ("scatter.js", 111),
    ("sra_jcl.js", 189),
    ("trend_drill.js", 110),
    ("volatility.js", 367),
    ("wbs.js", 133),
}

#: Ordered by time, but categorical — one tick per loaded version. See the module docstring.
VERSION_AXIS = {
    ("margin.js", 224),
    ("margin_dashboard.js", 240),
    ("trend.js", 483),
    ("trend.js", 587),
    ("trend.js", 712),
    ("trend.js", 830),
    ("trend.js", 920),
    ("volatility.js", 167),
    ("volatility.js", 208),
    ("volatility.js", 251),
}

#: Denominated in dates, but a DISTRIBUTION over a simulated outcome rather than a timeline
#: (ADR-0342). Kept as its own family — not folded into NOT_TIME_AXIS — precisely because the
#: label IS a date, so the exclusion is a judgment that has to be stated and checked, not one
#: the "is it a date?" predicate can make on its own.
OUTCOME_AXIS = {
    ("sra.js", 158),
    ("sra.js", 230),
    ("sra_jcl.js", 136),
    ("sra_ssi.js", 240),
    ("sra_ssi.js", 273),
}

#: ``performance.js`` passes its caption options through as a VARIABLE (``opts``), built by the
#: quad-chart caller, so its xLabel is the one of the 28 that cannot be read statically. It is
#: recorded here rather than guessed into a bucket — the honest state, and the assertion below
#: pins the REASON (a variable, not a literal) so this entry cannot quietly outlive it.
OPTS_NOT_LITERAL = {
    ("performance.js", 472),
}

#: Time-axis charts that draw NO data-date marker today. **EMPTY since ADR-0342** — every
#: time-axis chart draws the marker through the one shared helper. It is DERIVED below, so this
#: cannot silently overstate or understate: delete ``resources.js``'s call and the test fails.
DD_PENDING: set[tuple[str, int]] = set()

CALL = "SFChartFrame.axisTitles("
X_LABEL = re.compile(r'xLabel:\s*"([^"]*)"')
Y_LABEL = re.compile(r'yLabel:\s*"([^"]*)"')

#: A version axis names the VERSION, whatever else it also mentions. Checked FIRST — margin.js's
#: "Schedule version (data date)" would otherwise read as a date axis.
VERSION_RE = re.compile(r"\bversion", re.I)
#: A time axis names a date, a month, or a period. Deliberately anchored to whole words: "EAC" and
#: "Total float band (working days)" must not match, and "days" alone must never imply a calendar.
TIME_RE = re.compile(r"\bdate\b|\bmonth\b|^Period \(", re.I)
#: What makes an outcome axis an outcome axis: the Y is a probability, a simulated count or a
#: cost — the chart is a DISTRIBUTION, not a timeline. This is the half of the judgment that can
#: be checked mechanically, so it is.
OUTCOME_Y_RE = re.compile(r"probability|simulated|^EAC$", re.I)


def _call_sites() -> list[tuple[str, int, str | None, str | None]]:
    """Re-derive every axis-caption call site and its declared labels from disk."""
    out: list[tuple[str, int, str | None, str | None]] = []
    for js in sorted(STATIC.glob("*.js")):
        lines = js.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if CALL not in line:
                continue
            chunk = [line]
            if not line.rstrip().endswith(");"):
                for follow in lines[i + 1 :]:
                    chunk.append(follow)
                    if follow.strip().startswith("});"):
                        break
            blob = "\n".join(chunk)
            mx, my = X_LABEL.search(blob), Y_LABEL.search(blob)
            out.append((js.name, i + 1, mx.group(1) if mx else None, my.group(1) if my else None))
    return out


def _labels() -> dict[tuple[str, int], str | None]:
    return {(n, ln): x for n, ln, x, _y in _call_sites()}


def _y_labels() -> dict[tuple[str, int], str | None]:
    return {(n, ln): y for n, ln, _x, y in _call_sites()}


def test_every_chart_is_bucketed_exactly_once() -> None:
    """The anti-regression property: a NEW chart cannot slip past the DD-line rule unnoticed,
    and a chart that MOVES cannot silently keep a stale classification."""
    sites = {(n, ln) for n, ln, _x, _y in _call_sites()}
    families = (TIME_AXIS, NOT_TIME_AXIS, VERSION_AXIS, OUTCOME_AXIS, OPTS_NOT_LITERAL)
    buckets = set().union(*families)

    stale = buckets - sites
    assert not stale, (
        "the ledger names call sites that no longer exist (a chart moved or was removed) — "
        f"re-derive rather than deleting the rule: {sorted(stale)}"
    )
    unbucketed = sites - buckets
    assert not unbucketed, (
        "these charts are in no DD-line bucket — put each in TIME_AXIS (a calendar/period axis, "
        "so it MUST carry a data-date line), NOT_TIME_AXIS, VERSION_AXIS or OUTCOME_AXIS: "
        f"{sorted(unbucketed)}"
    )
    names = ("TIME_AXIS", "NOT_TIME_AXIS", "VERSION_AXIS", "OUTCOME_AXIS", "OPTS_NOT_LITERAL")
    for i, a in enumerate(families):
        for j in range(i + 1, len(families)):
            assert not a & families[j], (
                f"{names[i]} and {names[j]} overlap: {sorted(a & families[j])}"
            )


@pytest.mark.parametrize("site", sorted(TIME_AXIS))
def test_time_axis_entries_really_declare_a_calendar_axis(site: tuple[str, int]) -> None:
    """Each bucket is checked against the chart's OWN declared axis, so the ledger cannot drift
    from the code: parking a float-band chart in TIME_AXIS to excuse a missing DD line fails."""
    label = _labels()[site]
    assert label is not None, f"{site}: xLabel is not a literal — it belongs in OPTS_NOT_LITERAL"
    assert not VERSION_RE.search(label), (
        f"{site}: xLabel {label!r} names a VERSION — categorical, so it belongs in VERSION_AXIS"
    )
    assert TIME_RE.search(label), (
        f"{site}: xLabel {label!r} is not a date/month/period axis — the DD-line rule does not "
        "reach it, so it belongs in NOT_TIME_AXIS"
    )


@pytest.mark.parametrize("site", sorted(NOT_TIME_AXIS))
def test_not_time_axis_entries_really_declare_a_non_calendar_axis(site: tuple[str, int]) -> None:
    """The mirror check, and the one that keeps the EXCLUSIONS honest: a chart cannot be excused
    from the DD-line rule by being listed here unless its own axis caption says it is not time."""
    label = _labels()[site]
    assert label is not None, f"{site}: xLabel is not a literal — it belongs in OPTS_NOT_LITERAL"
    assert not TIME_RE.search(label), (
        f"{site}: xLabel {label!r} IS a date/month/period axis — it must carry a data-date line, "
        "not sit in the exclusion list"
    )


@pytest.mark.parametrize("site", sorted(VERSION_AXIS))
def test_version_axis_entries_really_declare_a_version_axis(site: tuple[str, int]) -> None:
    """The collision this ledger exists to get right: margin.js's axis is
    "Schedule version (data date)" — it says "data date" and is still the clearest case of an
    axis that must NOT carry a DD line. Version wins, and it is asserted, not assumed."""
    label = _labels()[site]
    assert label is not None, f"{site}: xLabel is not a literal — it belongs in OPTS_NOT_LITERAL"
    assert VERSION_RE.search(label), (
        f"{site}: xLabel {label!r} does not name a version — re-bucket it"
    )


@pytest.mark.parametrize("site", sorted(OUTCOME_AXIS))
def test_outcome_axis_entries_are_distributions_not_timelines(site: tuple[str, int]) -> None:
    """The exclusion that needs BOTH halves stated, because the X label alone argues the other
    way (ADR-0342). X really is denominated in dates — that is why these five were mistaken for
    the DD line's population — and Y really is a distribution quantity (a probability, a
    simulated count, a cost). Re-label an SRA chart's Y to something that is not a distribution
    and it stops qualifying for this exemption and has to be re-argued.
    """
    x, y = _labels()[site], _y_labels()[site]
    assert x is not None and y is not None, f"{site}: labels are not literals"
    assert TIME_RE.search(x), (
        f"{site}: xLabel {x!r} is not date-denominated — this family is specifically for axes "
        "that LOOK like time; a plain non-time axis belongs in NOT_TIME_AXIS"
    )
    assert OUTCOME_Y_RE.search(y), (
        f"{site}: yLabel {y!r} is not a distribution quantity, so the 'it plots an outcome, not "
        "a timeline' exemption does not apply — re-argue this entry or move it to TIME_AXIS"
    )


@pytest.mark.parametrize("site", sorted(OPTS_NOT_LITERAL))
def test_the_unreadable_entry_really_is_unreadable(site: tuple[str, int]) -> None:
    """The escape hatch cannot rot (the INCIDENTAL_SVG lesson): an entry parked here must really
    pass a non-literal xLabel. The moment performance.js inlines a literal, this fails and the
    chart must be bucketed for real."""
    assert _labels()[site] is None, (
        f"{site}: xLabel IS a literal now — classify it into a real bucket and drop it from here"
    )


#: Detecting a marker is itself a lesson, twice over. The FIRST detector matched the literal
#: bytes of ``cei.js``'s implementation and reported two modules, agreeing with a
#: ``grep -ci "data.date"`` census that was ALSO wrong — in the opposite direction (the grep
#: counted mentions and over-reported; the byte-match required one module's exact style and
#: under-reported, missing ``drift``'s unlabelled line and ``scurve``'s suffixed label). The
#: anchor then became the code comment naming the block, deliberately NOT a style match, because
#: the styles were the finding.
#:
#: Now that there is ONE implementation the honest anchor is the CALL itself — and it is counted
#: PER MODULE against that module's time-axis chart count, not merely "does this module mention
#: it anywhere". ``margin_dashboard.js`` is exactly why: it draws two charts and only ONE of them
#: takes a marker, so a module-level "has a marker" flag would have called it covered whichever
#: chart drew. Call sites, all the way down.
MARKER_CALL = "SFGantt.dataDateLine("


def _marker_calls_by_module() -> dict[str, int]:
    return {
        js.name: js.read_text(encoding="utf-8").count(MARKER_CALL)
        for js in sorted(STATIC.glob("*.js"))
        if js.name != "gantt.js"  # the helper's own definition + export, not a call site
    }


def test_the_pending_ledger_matches_what_the_code_actually_draws() -> None:
    """``DD_PENDING`` is DERIVED, not declared — the property ``DOM_PENDING`` earned the hard way.

    A hand-maintained list of "charts still missing a DD line" can overstate the work (an entry
    that was fixed and never removed) or understate it (a chart that lost its marker). Both are
    silent. Re-deriving means the ledger cannot disagree with the tree: delete ``resources.js``'s
    call and this fails until its entry is put back.
    """
    calls = _marker_calls_by_module()
    wanted: dict[str, int] = {}
    for name, _ln in TIME_AXIS:
        wanted[name] = wanted.get(name, 0) + 1
    derived = {site for site in TIME_AXIS if calls.get(site[0], 0) < wanted.get(site[0], 0)}
    assert derived == DD_PENDING, (
        "DD_PENDING no longer matches the tree. If a chart GAINED a data-date marker, delete its "
        f"entry; if one LOST its marker, that is a regression. derived={sorted(derived)} "
        f"recorded={sorted(DD_PENDING)}"
    )
    assert DD_PENDING <= TIME_AXIS, "only a time-axis chart can be pending a data-date line"
    # the excluded families must never appear as "pending" — that is the whole point of excluding
    assert not DD_PENDING & (NOT_TIME_AXIS | VERSION_AXIS | OUTCOME_AXIS)


def test_every_time_axis_chart_draws_the_marker_and_nothing_else_does() -> None:
    """The population is closed in BOTH directions (ADR-0342).

    Forwards: every module carrying a time-axis chart calls the helper once per such chart.
    Backwards: no module OUTSIDE that population calls it — an SRA chart quietly gaining a DD
    line would put a marker on an axis the data date is not on, which is the thing the outcome-
    axis measurement ruled out.
    """
    calls = _marker_calls_by_module()
    wanted: dict[str, int] = {}
    for name, _ln in TIME_AXIS:
        wanted[name] = wanted.get(name, 0) + 1
    # NB: no `wanted == {<literal>}` assertion here. That would be a relation between two module
    # constants wearing an `assert` — no change to the app can move it, so it reads as coverage
    # and is worse than a comment. Every assertion below compares the ledger to the TREE.
    for name, want in sorted(wanted.items()):
        assert calls.get(name, 0) == want, (
            f"{name}: {calls.get(name, 0)} marker call(s) for {want} time-axis chart(s)"
        )
    strays = {n: c for n, c in calls.items() if c and n not in wanted}
    assert not strays, (
        "a module with no time-axis chart is drawing a data-date marker — for the SRA family "
        f"that would place it off its own axis (see the module docstring): {strays}"
    )


def test_the_marker_has_exactly_one_implementation() -> None:
    """The finding this round closed: there were FOUR hand-rolled copies that disagreed with each
    other — ``cei``/``curves`` drew ``var(--accent)`` dashed ``6 5``, ``drift``/``scurve`` drew
    ``var(--muted)`` dotted ``2 3``, ``drift`` put no label on its line at all and ``scurve``
    appended the date to its label. Two colours, two dash patterns, three labelling schemes for
    the same contract element, and not one of them red.

    Now there is one. This pins that: the helper is defined once, in the head-loaded module, and
    no chart re-implements it. A FIFTH copy appearing is the regression to catch.
    """
    gantt = (STATIC / "gantt.js").read_text(encoding="utf-8")
    assert gantt.count("function dataDateLine(") == 1
    assert "dataDateLine: dataDateLine" in gantt, "the helper is not exported"
    # the old label form, which every hand-rolled copy wrote, is gone from every chart module
    for js in sorted(STATIC.glob("*.js")):
        src = js.read_text(encoding="utf-8")
        assert 'textContent = "data date"' not in src, f"{js.name}: a hand-rolled marker label"
        assert '"data date " +' not in src, f"{js.name}: a hand-rolled marker label"


def test_the_helper_lives_where_the_load_order_requires() -> None:
    """ADR-0340's lesson, applied: WHERE a shared drawing helper lives is a load-order question,
    not a filing one. ``_LAYOUT`` emits ``chartframe.js`` AFTER ``</main>``, so a parse-time body
    script — which is what cei/curves/drift/scurve are — would find a ``window.SFChartFrame``
    helper undefined at the moment it draws, and the marker would silently never appear.
    ``gantt.js`` is head-loaded, so it is defined for the deferred family too.
    """
    # `_LAYOUT` moved to `web/chrome.py` (ADR-0349, monolith split phase 2). This guard reads the
    # layout's INTERNAL script order, which is only meaningful inside the module that defines it.
    layout = (ROOT / "src" / "schedule_forensics" / "web" / "chrome.py").read_text(encoding="utf-8")
    head = layout.index('<script src="/static/gantt.js"></script>')
    main = layout.index("<main>{{ banner }}{{ body }}</main>")
    frame = layout.index('<script src="/static/chartframe.js"></script>')
    assert head < main < frame, (
        "the layout's script order changed — re-derive the helper's home before trusting it"
    )
    assert "dataDateLine" not in (STATIC / "chartframe.js").read_text(encoding="utf-8")


def test_the_marker_now_matches_the_design_system() -> None:
    """The deviations this ledger recorded are CLOSED (ADR-0342).

    ``DESIGN-SYSTEM.md`` §chart-contract asks for "a **red** vertical line labeled ``DD`` /
    ``DATA DATE``". Previously NOT ONE of the four implementations did that: two drew the accent
    colour, two the muted colour, none was red, every label was lowercase "data date" or absent,
    and each hard-coded ``"font-size": 10`` — the numeric-type-in-JS fork ADR-0298 removed from
    axis captions and ADR-0195 forbids generally.

    Colour and type now come from the theme, so this asserts against ``base.css`` rather than a
    JS block: ``--bad`` is the red token (there is no ``--danger``), and the type size reads the
    SAME ``--sf-fs-axis-title`` token as ``.ch-at`` so the queued crispness change still moves
    one value.
    """
    spec = (ROOT / "docs" / "DESIGN-SYSTEM.md").read_text(encoding="utf-8")
    assert "red vertical line labeled `DD` / `DATA DATE`" in spec, (
        "the design system's DD-line wording changed — re-derive this ledger against the new rule"
    )
    css = (STATIC / "base.css").read_text(encoding="utf-8")
    rule = css[css.index(".ch-dd line") : css.index(".ch-dd line") + 420]
    assert "stroke:var(--bad)" in rule, "the marker is no longer drawn in the red token"
    assert "fill:var(--bad)" in rule, "the marker's label is no longer red"
    assert "font-size:var(--sf-fs-axis-title)" in rule, "the label hard-codes a type size again"
    assert "text-transform:uppercase" in rule, "the DD label is no longer uppercase"
    # and the label the helper writes is the spec's compact form
    gantt = (STATIC / "gantt.js").read_text(encoding="utf-8")
    assert 'label.textContent = "DD";' in gantt
    assert '"DATA DATE "' in gantt, "the full spec label no longer reaches the hover call-out"
    assert '"font-size": 10' not in gantt
