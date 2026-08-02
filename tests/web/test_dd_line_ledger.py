"""The data-date line is required on every TIME-AXIS chart — and that population is a ledger.

``DESIGN-SYSTEM.md`` §chart-contract: "Data date: always a red vertical line labeled ``DD`` /
``DATA DATE``, on every time-axis chart, no exceptions." The DoD checklist repeats it. Nothing
enforced it, so this module is the census — the DD-line counterpart to ``test_axis_titles.py``.

**The population is re-derived, never hand-listed.** Every chart already DECLARES its own X axis,
in the ``SFChartFrame.axisTitles`` call ADR-0298 made universal. So the buckets below are keyed by
``(module, line)`` and every one is re-read from disk and CHECKED against the xLabel that justifies
it. A hand-typed list of "the time-axis charts" would be a second source of truth that drifts the
first time a chart is added; this cannot, because a new call site fails the partition test and a
re-labelled axis fails its bucket's predicate.

**"Time axis" is narrower than "ordered by time" — the finding this census produced.** The brief
named three exclusions (``histogram``, ``scatter``, and ``sra_jcl``'s COST axis). There are twelve.
The extra family is the **version axis**: ``margin``, ``trend``'s five charts and three of
``volatility``'s plot against "Schedule version" — ordered by time, but CATEGORICAL, one tick per
loaded file. A DD line has no position on such an axis, because *every version has its own data
date*; drawing one would have to pick a version and would assert something the engine never says.
That exclusion is a judgment, so it is stated here rather than assumed.

Note the collision it creates, and why the order of the checks below matters: ``margin.js``'s
xLabel is **"Schedule version (data date)"** — it contains the words "data date" while being the
clearest case of an axis that must NOT carry a DD line. The version check therefore runs BEFORE the
date check, exactly as ``ai/qa.py``'s identifier check runs before its derivation check.
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
    ("curves.js", 385),
    ("drift.js", 133),
    ("margin_dashboard.js", 233),
    ("margin_dashboard.js", 309),
    ("resources.js", 243),
    ("scurve.js", 168),
    ("sra.js", 158),
    ("sra.js", 230),
    ("sra_jcl.js", 136),
    ("sra_ssi.js", 240),
    ("sra_ssi.js", 273),
}

#: X is a quantity, a category or a metric — not time. The DD line does not apply.
#: ``sra_jcl.js`` L189 is the COST axis (EAC) the brief called out: the SAME module carries a
#: time-axis chart at L136, which is why this ledger is keyed by CALL SITE and not by module.
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
    ("trend.js", 479),
    ("trend.js", 583),
    ("trend.js", 708),
    ("trend.js", 826),
    ("trend.js", 916),
    ("volatility.js", 167),
    ("volatility.js", 208),
    ("volatility.js", 251),
}

#: ``performance.js`` passes its caption options through as a VARIABLE (``opts``), built by the
#: quad-chart caller, so its xLabel is the one of the 28 that cannot be read statically. It is
#: recorded here rather than guessed into a bucket — the honest state, and the assertion below
#: pins the REASON (a variable, not a literal) so this entry cannot quietly outlive it.
OPTS_NOT_LITERAL = {
    ("performance.js", 472),
}

#: Time-axis charts that draw NO data-date marker today — the remaining-work ledger, mirroring
#: ``DOM_PENDING``. It is re-derived below, so fixing one chart FAILS this test until the entry is
#: removed; it can never silently overstate or understate the work.
DD_PENDING = {
    ("margin_dashboard.js", 233),
    ("margin_dashboard.js", 309),
    ("resources.js", 243),
    ("sra.js", 158),
    ("sra.js", 230),
    ("sra_jcl.js", 136),
    ("sra_ssi.js", 240),
    ("sra_ssi.js", 273),
}

CALL = "SFChartFrame.axisTitles("
X_LABEL = re.compile(r'xLabel:\s*"([^"]*)"')

#: A version axis names the VERSION, whatever else it also mentions. Checked FIRST — margin.js's
#: "Schedule version (data date)" would otherwise read as a date axis.
VERSION_RE = re.compile(r"\bversion", re.I)
#: A time axis names a date, a month, or a period. Deliberately anchored to whole words: "EAC" and
#: "Total float band (working days)" must not match, and "days" alone must never imply a calendar.
TIME_RE = re.compile(r"\bdate\b|\bmonth\b|^Period \(", re.I)


def _call_sites() -> list[tuple[str, int, str | None]]:
    """Re-derive every axis-caption call site and its declared xLabel from disk."""
    out: list[tuple[str, int, str | None]] = []
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
            m = X_LABEL.search("\n".join(chunk))
            out.append((js.name, i + 1, m.group(1) if m else None))
    return out


def _labels() -> dict[tuple[str, int], str | None]:
    return {(n, ln): x for n, ln, x in _call_sites()}


def test_every_chart_is_bucketed_exactly_once() -> None:
    """The anti-regression property: a NEW chart cannot slip past the DD-line rule unnoticed,
    and a chart that MOVES cannot silently keep a stale classification."""
    sites = {(n, ln) for n, ln, _x in _call_sites()}
    buckets = TIME_AXIS | NOT_TIME_AXIS | VERSION_AXIS | OPTS_NOT_LITERAL

    stale = buckets - sites
    assert not stale, (
        "the ledger names call sites that no longer exist (a chart moved or was removed) — "
        f"re-derive rather than deleting the rule: {sorted(stale)}"
    )
    unbucketed = sites - buckets
    assert not unbucketed, (
        "these charts are in no DD-line bucket — put each in TIME_AXIS (a calendar/period axis, "
        "so it MUST carry a data-date line), NOT_TIME_AXIS, or VERSION_AXIS: "
        f"{sorted(unbucketed)}"
    )
    for a, b, an, bn in (
        (TIME_AXIS, NOT_TIME_AXIS, "TIME_AXIS", "NOT_TIME_AXIS"),
        (TIME_AXIS, VERSION_AXIS, "TIME_AXIS", "VERSION_AXIS"),
        (NOT_TIME_AXIS, VERSION_AXIS, "NOT_TIME_AXIS", "VERSION_AXIS"),
    ):
        assert not a & b, f"{an} and {bn} overlap: {sorted(a & b)}"


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


@pytest.mark.parametrize("site", sorted(OPTS_NOT_LITERAL))
def test_the_unreadable_entry_really_is_unreadable(site: tuple[str, int]) -> None:
    """The escape hatch cannot rot (the INCIDENTAL_SVG lesson): an entry parked here must really
    pass a non-literal xLabel. The moment performance.js inlines a literal, this fails and the
    chart must be bucketed for real."""
    assert _labels()[site] is None, (
        f"{site}: xLabel IS a literal now — classify it into a real bucket and drop it from here"
    )


#: Detecting a marker is itself a lesson. The first detector here matched the literal bytes of
#: ``cei.js``'s implementation (``"stroke-dasharray": "6 5"`` plus ``textContent = "data date"``)
#: and reported exactly two modules — agreeing with a `grep -ci "data.date"` census and with the
#: handoff note written from it. Both were WRONG, in opposite directions: the grep counted
#: MENTIONS (comments, ``statusDate`` variables) and over-reported; the byte-match required
#: ``cei.js``'s exact style and under-reported. ``drift.js`` and ``scurve.js`` both draw a real
#: marker and neither matched — drift labels its line only in a legend note, and scurve appends the
#: date to the label (``"data date " + v.status_date``).
#:
#: So the anchor is the thing all four implementations share and that a reader must write
#: deliberately: the code comment naming the block. It is deliberately NOT a style match, because
#: the styles disagree — which is the finding recorded below.
MARKER_BLOCK = re.compile(r"//\s*(?:dashed )?data-date marker")


def _modules_with_a_marker() -> set[str]:
    return {
        js.name
        for js in sorted(STATIC.glob("*.js"))
        if MARKER_BLOCK.search(js.read_text(encoding="utf-8"))
    }


def test_the_pending_ledger_matches_what_the_code_actually_draws() -> None:
    """``DD_PENDING`` is DERIVED, not declared — the property ``DOM_PENDING`` earned the hard way.

    A hand-maintained list of "charts still missing a DD line" can overstate the work (an entry
    that was fixed and never removed) or understate it (a chart that lost its marker). Both are
    silent. Re-deriving means the ledger cannot disagree with the tree: give ``resources.js`` a
    marker and this test fails until its entry is removed.
    """
    drawn = _modules_with_a_marker()
    derived = {site for site in TIME_AXIS if site[0] not in drawn}
    assert derived == DD_PENDING, (
        "DD_PENDING no longer matches the tree. If a chart GAINED a data-date marker, delete its "
        f"entry; if one LOST its marker, that is a regression. derived={sorted(derived)} "
        f"recorded={sorted(DD_PENDING)}"
    )
    assert DD_PENDING <= TIME_AXIS, "only a time-axis chart can be pending a data-date line"
    # the excluded families must never appear as "pending" — that is the whole point of excluding
    assert not DD_PENDING & (NOT_TIME_AXIS | VERSION_AXIS)


#: The four hand-rolled implementations, and the fact that matters: THEY DISAGREE. Recorded as
#: (module, stroke colour, dasharray, label form) read from each marker block.
#: ``stroke`` is recorded as (expression AS WRITTEN in the block, token it resolves to) — cei and
#: curves reference a module-scope alias (``BLUE``), drift and scurve inline the token. Resolving
#: the alias is the difference between checking what the code SAYS and what it RENDERS.
MARKER_STYLES = {
    "cei.js": (("BLUE", "var(--accent)"), "6 5", 'textContent = "data date"'),
    "curves.js": (("BLUE", "var(--accent)"), "6 5", 'textContent = "data date"'),
    "drift.js": (('"var(--muted)"', "var(--muted)"), "2 3", None),  # no label on the line at all
    "scurve.js": (
        ('"var(--muted)"', "var(--muted)"),
        "2 3",
        'textContent = v.status_date ? "data date "',
    ),
}


def _marker_block(name: str) -> str:
    """The marker's CODE block — anchored past the module docstring.

    Two slicing bugs were found by RUNNING this, not by reading it. ``cei.js`` says "dashed
    data-date marker" in its header comment as well as at the code, so slicing from the first
    occurrence read the DOCSTRING — hence anchoring on the ``//`` comment form. Then a fixed
    700-character window over-ran into the NEXT block, which matters only for ``drift.js``: its
    marker carries no label, so the spill supplied a ``textContent`` and a ``font-size`` from
    unrelated code and made two assertions read the wrong bytes. The block therefore ends at the
    blank line that actually terminates it in all four files.
    """
    src = (STATIC / name).read_text(encoding="utf-8")
    m = MARKER_BLOCK.search(src)
    assert m is not None, f"{name}: no data-date marker block"
    end = src.find("\n\n", m.start())
    return src[m.start() : end if end != -1 else m.start() + 700]


def test_the_marker_has_four_implementations_that_disagree_with_each_other() -> None:
    """The finding that decides HOW the pending work gets done — and it is worse than "a copy".

    ``cei``/``curves`` draw ``var(--accent)`` dashed ``6 5``; ``drift``/``scurve`` draw
    ``var(--muted)`` dotted ``2 3``; and ``drift`` puts no label on its line at all, naming the
    marker only in a legend note. So the same contract element renders in two different colours,
    two different dash patterns and three different labelling schemes depending on which page the
    analyst is looking at. That is precisely the pre-ADR-0298 caption situation, and with eight
    charts still pending the answer is ONE helper rather than four more copies — remembering
    ADR-0340's lesson that WHERE it lives is a load-order question, not a filing one.
    """
    drawn = _modules_with_a_marker()
    assert drawn == set(MARKER_STYLES), (
        "the set of modules hand-drawing a data-date marker changed — if a FIFTH copy appeared, "
        f"stop and promote this into a shared helper instead: {sorted(drawn)}"
    )
    for name, ((expr, token), dash, label) in sorted(MARKER_STYLES.items()):
        block = _marker_block(name)
        src = (STATIC / name).read_text(encoding="utf-8")
        assert f"stroke: {expr}" in block, f"{name}: marker stroke is no longer {expr} — re-derive"
        # resolve a bare IDENTIFIER to the token it renders; a quoted literal already is one
        if not expr.startswith('"'):
            assert f'{expr} = "{token}"' in src, (
                f"{name}: {expr} no longer resolves to {token} — the marker's RENDERED colour "
                "changed even though the block did not"
            )
        assert f'"stroke-dasharray": "{dash}"' in block, f"{name}: dash pattern moved"
        if label is None:
            assert "textContent" not in block, (
                f"{name} gained a label on its marker line — good, but the ledger must record it"
            )
        else:
            assert label in block, f"{name}: marker label moved — re-derive the record"
    # exactly the divergence, stated as a number so closing it is visible
    assert len({(c, d) for c, d, _l in MARKER_STYLES.values()}) == 2, (
        "the two rendering styles converged (or a third appeared) — update the ADR and this test"
    )


def test_the_marker_contradicts_the_design_system_in_recorded_ways() -> None:
    """``DESIGN-SYSTEM.md`` §chart-contract asks for "a **red** vertical line labeled ``DD`` /
    ``DATA DATE``". NOT ONE of the four implementations does that: two draw the accent colour, two
    the muted colour, none is red, and every label is lowercase "data date" or absent.

    Both hard-code ``"font-size": 10`` where they label at all — the numeric-type-in-JS fork
    ADR-0298 removed from axis captions and ADR-0195 forbids generally.

    This pins the CURRENT state deliberately, the way a PENDING entry does: closing any part of the
    gap FAILS this test and forces the ledger to be updated in the same commit. It records the
    deviation; it does not bless it.
    """
    spec = (ROOT / "docs" / "DESIGN-SYSTEM.md").read_text(encoding="utf-8")
    assert "red vertical line labeled `DD` / `DATA DATE`" in spec, (
        "the design system's DD-line wording changed — re-derive this ledger against the new rule"
    )
    for name in sorted(MARKER_STYLES):
        block = _marker_block(name)
        assert "var(--danger)" not in block and "var(--bad)" not in block, (
            f"{name}: the marker is RED now — the colour deviation is CLOSED, update this test"
        )
        assert "DATA DATE" not in block, (
            f"{name}: the marker label is uppercase now — that deviation is CLOSED, update this"
        )
        if "textContent" in block:
            assert '"font-size": 10' in block, (
                f"{name}: the hard-coded marker type size is gone — if it reads a token now, that "
                "deviation is CLOSED; update this test"
            )
