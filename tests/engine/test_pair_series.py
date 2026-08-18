"""The consecutive-pair comparison series (ADR-0424) — every update compared, not just the last.

The defect these pin, measured on a 4-version workbook whose manipulation sat in the FIRST two
updates: the Ask-the-AI workbook fact sheet held ZERO manipulation facts, neither shortened
activity appeared anywhere in the evidence, and the only statement on the subject was an
affirmative negative scoped to the newest pair. Manipulation is a DIFF signal, so a workbook of N
versions offers N-1 comparisons; the tool made exactly one of them.

So the assertions are about COVERAGE and ORDER: is every consecutive pair compared, is "earliest
forward" the data-date order rather than the load order, does a signal in an early pair survive,
and is a pair we could not compare reported as unmeasured rather than as signal-free (Law 2).
"""

from __future__ import annotations

import datetime as dt
import random
import re
from pathlib import Path

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.pair_series import (
    _longest_run,
    compute_pairwise_series,
)
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

_GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
_D0 = dt.datetime(2026, 4, 15)


@pytest.fixture(scope="module")
def base() -> Schedule:
    return parse_mspdi_text(
        (_GOLDEN / "Project5.mspdi.xml").read_text(encoding="utf-8"), source_file="base.mpp"
    )


def _victims(sch: Schedule) -> list[int]:
    return [
        t.unique_id
        for t in sch.tasks
        if not t.is_summary and t.percent_complete < 100.0 and t.duration_minutes >= 4800
    ]


def _shorten(sch: Schedule, uid: int) -> Schedule:
    return sch.model_copy(
        update={
            "tasks": tuple(
                t.model_copy(update={"duration_minutes": t.duration_minutes // 2})
                if t.unique_id == uid
                else t
                for t in sch.tasks
            )
        }
    )


def _stamp(sch: Schedule, i: int) -> Schedule:
    label = f"v{i + 1:02d}.mpp"
    return sch.model_copy(
        update={
            "name": label,
            "source_file": label,
            "status_date": _D0 + dt.timedelta(days=30 * i),
        }
    )


def _workbook(base: Schedule, n: int, cut_at: set[int]) -> list[Schedule]:
    """``n`` versions; a duration is halved going INTO each step index in ``cut_at`` (1-based)."""
    victims = _victims(base)
    out: list[Schedule] = [_stamp(base, 0)]
    cur = base
    for i in range(1, n):
        if i in cut_at:
            cur = _shorten(cur, victims[i % len(victims)])
        out.append(_stamp(cur, i))
    return out


def _series(versions: list[Schedule]):
    return compute_pairwise_series(versions, [compute_cpm(v) for v in versions])


# --- coverage: every consecutive pair, not just the newest -------------------------------------


def test_a_workbook_of_n_versions_produces_n_minus_one_comparisons(base: Schedule) -> None:
    versions = _workbook(base, 8, cut_at=set())
    series = _series(versions)
    assert len(series.steps) == 7
    assert [s.label for s in series.steps] == [
        f"v{i:02d}.mpp → v{i + 1:02d}.mpp" for i in range(1, 8)
    ]
    assert [s.index for s in series.steps] == list(range(1, 8))


def test_a_signal_in_the_earliest_pair_is_found(base: Schedule) -> None:
    """THE regression: the manipulation is in step 1 of 3 and the newest pair is clean."""
    versions = _workbook(base, 4, cut_at={1})
    series = _series(versions)
    assert series.total_signals >= 1
    firing = [s.index for s in series.steps if s.findings]
    assert firing == [1], f"only the earliest step should fire, got {firing}"
    assert "MANIP_SHORTENED_DURATION" in series.steps[0].signal_ids
    assert not series.steps[-1].findings  # the pair the old code looked at is clean


def test_signals_in_several_early_pairs_all_survive(base: Schedule) -> None:
    versions = _workbook(base, 6, cut_at={1, 2, 4})
    series = _series(versions)
    assert [s.index for s in series.steps if s.findings] == [1, 2, 4]


# --- order: "earliest forward" is by DATA DATE, never by load order ----------------------------


def test_ordering_is_by_data_date_not_load_order(base: Schedule) -> None:
    versions = _workbook(base, 6, cut_at={1, 3})
    expected = [s.label for s in _series(versions).steps]
    shuffled = versions[:]
    random.Random(1234).shuffle(shuffled)
    assert shuffled != versions, "the shuffle must actually reorder, or this proves nothing"
    assert [s.label for s in _series(shuffled).steps] == expected


# --- recurrence: the arithmetic behind "is this a pattern?" ------------------------------------


def test_recurrence_counts_steps_totals_and_the_span(base: Schedule) -> None:
    versions = _workbook(base, 6, cut_at={1, 2, 4})
    (rec,) = _series(versions).recurrence
    assert rec.metric_id == "MANIP_SHORTENED_DURATION"
    assert rec.steps_present == 3
    assert rec.total_findings == 3
    assert (rec.first_step, rec.last_step) == (1, 4)
    assert rec.longest_run == 2  # steps 1-2 are unbroken; step 4 stands alone


@pytest.mark.parametrize(
    ("indices", "expected"),
    [([], 0), ([3], 1), ([1, 2, 3], 3), ([1, 3, 5], 1), ([1, 2, 5, 6, 7], 3), ([2, 3, 7, 8], 2)],
)
def test_longest_run_is_the_longest_unbroken_run(indices: list[int], expected: int) -> None:
    assert _longest_run(indices) == expected


def test_a_clean_workbook_reports_zero_recurrence_not_an_empty_series(base: Schedule) -> None:
    series = _series(_workbook(base, 5, cut_at=set()))
    assert len(series.steps) == 4, "every pair is still COMPARED when nothing fires"
    assert series.recurrence == ()
    assert series.total_signals == 0
    assert series.steps_with_signals == 0


# --- Law 2: "could not look" is never reported as "looked and found nothing" -------------------


def test_an_unsolvable_version_is_named_uncomparable_not_counted_as_signal_free(
    base: Schedule,
) -> None:
    from schedule_forensics.engine import pair_series as mod

    versions = _workbook(base, 4, cut_at=set())
    # CONTROL: with every network solvable all three pairs are steps and nothing is uncomparable
    control = compute_pairwise_series(versions, [compute_cpm(v) for v in versions])
    assert len(control.steps) == 3
    assert control.uncomparable == ()

    real, bad = mod.compute_cpm, versions[2]

    def fake(sch: Schedule, *a: object, **k: object) -> object:
        if sch is bad:
            raise mod.CPMError("synthetic: this network does not solve")
        return real(sch, *a, **k)  # type: ignore[arg-type]

    mod.compute_cpm = fake  # type: ignore[assignment]
    try:  # no cpms passed -> the engine solves them itself and meets the failure
        series = compute_pairwise_series(versions)
    finally:
        mod.compute_cpm = real  # type: ignore[assignment]
    assert len(series.steps) == 1, "the two pairs touching the unsolvable version are not steps"
    assert series.uncomparable == ("v02.mpp → v03.mpp", "v03.mpp → v04.mpp")
    assert series.steps[0].label == "v01.mpp → v02.mpp"
    # the decisive half of Law 2: those pairs are UNMEASURED, never counted as signal-free
    assert series.steps_with_signals == 0
    assert len(series.steps) + len(series.uncomparable) == 3


def test_fewer_than_two_versions_has_nothing_to_compare(base: Schedule) -> None:
    assert compute_pairwise_series([_stamp(base, 0)]).steps == ()
    assert compute_pairwise_series([]).steps == ()


# --- the label table is a COMPUTED census of another module's constants ------------------------


def test_every_emitted_manipulation_metric_id_has_a_compact_label() -> None:
    """A hand-maintained mirror of another module's constants goes stale silently, so the
    expected set is READ OUT of ``manipulation.py`` rather than written down here."""
    from schedule_forensics.ai.pair_facts import _SIGNAL_LABELS

    source = (
        Path(__file__).resolve().parents[2] / "src/schedule_forensics/engine/manipulation.py"
    ).read_text(encoding="utf-8")
    emitted = set(re.findall(r'metric_id="(MANIP_[A-Z_]+)"', source))
    assert emitted, "the census found no metric ids — the regex, not the code, is what broke"
    missing = emitted - set(_SIGNAL_LABELS)
    assert not missing, f"manipulation signals with no compact label: {sorted(missing)}"
    stale = set(_SIGNAL_LABELS) - emitted
    assert not stale, f"labels for signals manipulation.py no longer emits: {sorted(stale)}"
