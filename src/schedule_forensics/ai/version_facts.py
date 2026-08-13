"""Cross-version population facts for Ask-the-AI — tell the model the whole workbook exists.

**The defect this closes (ADR-0392).** The workbook fact sheet is assembled from the Diagnostic
Executive Briefing, whose subject is the NEWEST version and whose only comparison is the latest
consecutive PAIR. Measured on a synthetic 31-version workbook: 23 facts, of which exactly one
named more than one version — and that one was the "How to Verify" boilerplate, which lists the
file names inside a verification *procedure*, not as data. Every substantive fact named either the
newest version or the newest two. Asked to read the S-curve across 31 loaded files, a local model
correctly reported that its evidence covered *two* file versions and carried no cumulative-progress
series at all. It was not hallucinating; it was describing what it had been given.

So the fix is not in the model and not in the loader — the files were loaded. It is here: the
population itself has to be a **fact**, and the per-version series has to be *in* the evidence.

Four facts, all engine-computed by :mod:`schedule_forensics.engine.version_series`, all
:attr:`~schedule_forensics.ai.citations.CitedStatement.pinned` so relevance ranking and the
48-fact model cap can never drop the frame:

1. **the population** — how many versions are loaded and each one's data date;
2. **the S-curve series** — every version's cumulative actual-vs-planned point at its own data
   date, in one compact series;
3. **the trend verdict** — the mechanical first-to-last movement of that gap plus the step counts;
4. **the finish series** — every version's schedule-logic finish (CPM) and its net movement.

Facts 2-4 are emitted only when they carry a measurement: a workbook whose versions have no data
dates gets fact 1 and an explicit statement that the S-curve series is unreadable — never a series
of fabricated zeroes (Law 2: "—" never 0).
"""

from __future__ import annotations

from schedule_forensics.ai.citations import CitedStatement
from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.dcma_audit import Citation
from schedule_forensics.engine.version_series import VersionSeries, compute_version_series
from schedule_forensics.model.schedule import Schedule

#: Versions rendered in full inside one series fact before the middle is elided. A model reads a
#: 31-entry series comfortably; a 400-version portfolio would drown the rest of the evidence, so
#: past this the oldest and newest ``_SERIES_EDGE`` are shown and the elision is STATED (never
#: silent — a truncation the reader cannot see is the defect this whole module exists to fix).
_SERIES_FULL_MAX = 60
_SERIES_EDGE = 20


def _anchor(schedules: list[Schedule]) -> tuple[Citation, ...]:
    """One citation per version — the population itself is what these facts are about, so every
    loaded file is cited (UID 0 = the file, the same anchor the briefing's verify section uses)."""
    return tuple(Citation(s.source_file, 0, s.source_file or s.name) for s in schedules)


def _elide(entries: list[str]) -> tuple[str, str]:
    """``(rendered series, elision note)`` — the whole series, or both edges plus a stated gap."""
    if len(entries) <= _SERIES_FULL_MAX:
        return "; ".join(entries), ""
    hidden = len(entries) - 2 * _SERIES_EDGE
    kept = entries[:_SERIES_EDGE] + entries[-_SERIES_EDGE:]
    return (
        "; ".join(kept),
        f" (the {hidden} versions between the oldest {_SERIES_EDGE} and the newest "
        f"{_SERIES_EDGE} are omitted from this line for length; they are loaded and analyzed)",
    )


def _population_fact(series: VersionSeries, cite: tuple[Citation, ...]) -> CitedStatement:
    entries = [
        f"{p.label} (data date {p.status_date.isoformat() if p.status_date else 'none'})"
        for p in series.points
    ]
    rendered, note = _elide(entries)
    n = len(series.points)
    return CitedStatement(
        f"WORKBOOK POPULATION: {n} schedule version(s) are loaded and analyzed together as one "
        f"series, ordered oldest to newest by data date: {rendered}{note}. Every other fact that "
        f"names a single file describes ONE member of this series — most describe the newest "
        f"version, and the change/counterfactual facts compare the newest two. The version-series "
        f"facts below are the ones that span all {n}.",
        cite,
        pinned=True,
    )


def _scurve_fact(series: VersionSeries, cite: tuple[Citation, ...]) -> CitedStatement:
    readable = series.readable
    if not readable:
        return CitedStatement(
            f"S-CURVE SERIES: none of the {len(series.points)} loaded version(s) carries a data "
            "date, so no version has a readable cumulative plan-vs-actual point and no S-curve "
            "trend across versions can be computed. This is missing input, not zero progress.",
            cite,
            pinned=True,
        )
    entries = []
    for p in series.points:
        if p.gap_pct is None:
            # unreadable for one of two DIFFERENT reasons, and the model must not conflate them:
            # no status date to read the curve at, or no activities in scope to measure
            why = "no data date" if p.status_date is None else "no activities in scope"
            entries.append(f"{p.label} {why} — unreadable")
            continue
        entries.append(
            f"{p.label} ({p.status_date.isoformat() if p.status_date else 'none'}) "
            f"actual {p.actual_pct}% vs planned {p.planned_pct}% (gap {p.gap_pct:+} points)"
        )
    rendered, note = _elide(entries)
    return CitedStatement(
        f"S-CURVE SERIES across all {len(series.points)} loaded version(s) — each version's "
        f"cumulative S-curve read AT ITS OWN DATA DATE, as the percentage of that version's "
        f"non-summary activities finished (actual/forecast) versus planned by baseline finish. A "
        f"negative gap means less work was complete than the plan called for at that data date: "
        f"{rendered}{note}.",
        cite,
        pinned=True,
    )


def _trend_fact(series: VersionSeries, cite: tuple[Citation, ...]) -> CitedStatement | None:
    delta = series.gap_delta
    if delta is None:
        return None
    readable = series.readable
    first, last = readable[0], readable[-1]
    narrowed, widened, flat = series.steps
    meaning = {
        "narrowed": (
            "execution moved TOWARD the plan across the series — later versions are closer to "
            "their own plan than earlier ones were to theirs"
        ),
        "widened": (
            "execution moved AWAY from the plan across the series — later versions are further "
            "behind their own plan than earlier ones were to theirs"
        ),
        "unchanged": (
            "the plan-vs-actual gap ends where it started; the plan and the execution moved "
            "together across the series"
        ),
    }[series.direction]
    return CitedStatement(
        f"S-CURVE TREND across the {len(readable)} readable version(s): the plan-vs-actual gap "
        f"went from {first.gap_pct:+} points in {first.label} to {last.gap_pct:+} points in "
        f"{last.label} — it {series.direction} by {abs(delta)} points. Version to version, "
        f"{narrowed} step(s) narrowed the gap, {widened} widened it and {flat} left it unchanged. "
        f"Read literally: {meaning}. This is arithmetic on the first and last readable S-curve "
        "points; each version is measured against ITS OWN baseline, so a re-baseline between "
        "versions can narrow the gap without any work being completed — check the change and "
        "counterfactual facts before reading a narrowing gap as progress.",
        cite,
        pinned=True,
    )


def _finish_fact(series: VersionSeries, cite: tuple[Citation, ...]) -> CitedStatement | None:
    moved = series.finish_movement_days
    if moved is None:  # fewer than two versions carry a computed finish — no series to state
        return None
    dated = [p for p in series.points if p.finish is not None]
    entries = [f"{p.label} {p.finish.isoformat()}" for p in series.points if p.finish is not None]
    rendered, note = _elide(entries)
    verdict = (
        "later (the computed finish slipped across the series)"
        if moved > 0
        else "earlier (the computed finish pulled in across the series)"
        if moved < 0
        else "not at all (the computed finish is identical in the first and last version)"
    )
    return CitedStatement(
        f"SCHEDULE-LOGIC FINISH SERIES across {len(dated)} version(s) — each version's own CPM "
        f"finish (the network's computed finish, NOT a progress-aware forecast): {rendered}"
        f"{note}. From {dated[0].label} to {dated[-1].label} that date moved {moved:+d} calendar "
        f"day(s), i.e. {verdict}.",
        cite,
        pinned=True,
    )


def version_series_facts(
    schedules: list[Schedule], cpms: list[CPMResult] | None = None
) -> tuple[CitedStatement, ...]:
    """The pinned population + cross-version series facts for a multi-version workbook.

    Returns ``()`` for a single version (there is no series to state, and the existing
    single-version facts already say which file they are about).
    """
    if len(schedules) < 2:
        return ()
    series = compute_version_series(schedules, cpms)
    cite = _anchor(schedules)
    facts: list[CitedStatement] = [
        _population_fact(series, cite),
        _scurve_fact(series, cite),
    ]
    for maybe in (_trend_fact(series, cite), _finish_fact(series, cite)):
        if maybe is not None:
            facts.append(maybe)
    return tuple(facts)
