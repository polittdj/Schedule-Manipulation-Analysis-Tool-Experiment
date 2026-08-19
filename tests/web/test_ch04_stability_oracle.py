"""Chapter 04 — an INDEPENDENT oracle for every figure the stability band reports.

Why this module exists. ``test_evolution_stability_band.py`` guards the page's *structure*:
the panels mount, the scope words are present, both pages embed the same dataset. Every one of
those assertions passes even if the arithmetic underneath is wrong — they compare the tool to
itself. This module compares the tool to answers worked out **by hand**, on schedules whose
critical path is fixed by construction, so it is capable of disagreeing with the implementation.

The construction. ``effective_critical_set`` prefers the source file's **stored** Critical flag
over recomputed float (``_common.is_effective_critical`` — that is how real MS Project files are
read), so setting ``stored_is_critical`` per version pins the membership exactly. The CPM still
runs, the real code path is exercised, and the expected numbers below were derived from set
algebra on paper, not from running the tool.

PASS cases assert the tool reproduces the hand-computed figures. FAIL cases are schedules that
are known to be BAD — a path that is rebuilt every update, a path with nothing carried over — and
assert the tool *reports* them as bad. A stability metric that cannot say "erratic" is worthless
in a testimony product, and a green structural test would never notice.
"""

from __future__ import annotations

import datetime as dt
from itertools import pairwise

import pytest

from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.components import _volatility_data

START = dt.datetime(2026, 1, 5, 8, 0)
DAY = 480
#: Five activities in one FS chain. Which of them is *critical* is dictated per version by
#: ``stored_is_critical``; the chain only has to be solvable so every task gets a CPM timing.
UIDS = (1, 2, 3, 4, 5)


def _version(name: str, critical: set[int], *, complete: set[int] = frozenset()) -> Schedule:
    """One loaded file whose critical membership is exactly ``critical``."""
    tasks = tuple(
        Task(
            unique_id=u,
            name=f"Activity {u}",
            duration_minutes=5 * DAY,
            percent_complete=100.0 if u in complete else 0.0,
            stored_is_critical=u in critical,
        )
        for u in UIDS
    )
    rels = tuple(
        Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS, lag_minutes=0)
        for p, s in pairwise(UIDS)
    )
    return Schedule(
        name=name,
        source_file=name,
        project_start=START,
        status_date=START + dt.timedelta(days=30 * UIDS.index(1)),
        tasks=tasks,
        relationships=rels,
    )


def _solve(schedules: list[Schedule]) -> list[CPMResult]:
    return [compute_cpm(s) for s in schedules]


def _data(schedules: list[Schedule]) -> dict[str, object]:
    return _volatility_data(schedules, _solve(schedules))


# ══ PASS — the hand-computed case ═════════════════════════════════════════════════════════════
#
# Four versions, critical membership fixed by construction:
#
#   v1 {1,2,3}   v2 {1,2,3}   v3 {1,2,4}   v4 {1,2,3}
#
# Worked out on paper (Jaccard = size of the intersection / size of the union):
#
#   v1→v2  intersection {1,2,3} union {1,2,3}    stayed 3  entered 0  left 0   J = 3/3 = 1.0
#   v2→v3  intersection {1,2}   union {1,2,3,4}  stayed 2  entered 1  left 1   J = 2/4 = 0.5
#   v3→v4  intersection {1,2}   union {1,2,3,4}  stayed 2  entered 1  left 1   J = 2/4 = 0.5
#
#   mean J = (1.0 + 0.5 + 0.5) / 3 = 0.666… → 0.667 → the page prints 67%
#
#   per activity:  1 → [1,1,1,1] tenure 4 streak 4 flips 0
#                  2 → [1,1,1,1] tenure 4 streak 4 flips 0
#                  3 → [1,1,0,1] tenure 3 streak 2 flips 2
#                  4 → [0,0,1,0] tenure 1 streak 1 flips 2
#                  5 → never critical, so it must NOT appear at all
KNOWN = [
    _version("v1", {1, 2, 3}),
    _version("v2", {1, 2, 3}),
    _version("v3", {1, 2, 4}),
    _version("v4", {1, 2, 3}),
]


@pytest.fixture
def known() -> dict[str, object]:
    return _data(KNOWN)


def test_per_pair_similarity_matches_the_hand_computed_jaccard(known: dict[str, object]) -> None:
    pairs = known["pairs"]
    assert isinstance(pairs, list)
    assert [p["jaccard"] for p in pairs] == [1.0, 0.5, 0.5]


def test_per_pair_stayed_entered_left_match_the_hand_computed_sets(
    known: dict[str, object],
) -> None:
    pairs = known["pairs"]
    assert isinstance(pairs, list)
    assert [(p["stayed"], p["entered"], p["left"]) for p in pairs] == [
        (3, 0, 0),
        (2, 1, 1),
        (2, 1, 1),
    ]
    # and the drill-down IDs must be the actual activities, not just counts
    assert pairs[1]["entered_uids"] == [4] and pairs[1]["left_uids"] == [3]
    assert pairs[2]["entered_uids"] == [3] and pairs[2]["left_uids"] == [4]


def test_entered_and_left_are_not_interchangeable() -> None:
    """The KNOWN fixture above is SYMMETRIC — every pair has entered == left — so swapping the
    two labels changes none of its numbers. Mutation M5 proved exactly that: the swap survived.
    This case is deliberately lopsided (two join, none leave) so the labels cannot be exchanged
    without the test noticing. A fixture that cannot distinguish two quantities does not test
    either of them."""
    asym = [_version("a1", {1, 2}), _version("a2", {1, 2, 3, 4})]
    pairs = _data(asym)["pairs"]
    assert isinstance(pairs, list)
    p0 = pairs[0]
    assert (p0["stayed"], p0["entered"], p0["left"]) == (2, 2, 0)
    assert p0["entered_uids"] == [3, 4] and p0["left_uids"] == []
    # J = |{1,2}| / |{1,2,3,4}| = 0.5
    assert p0["jaccard"] == 0.5


def test_the_headline_mean_carry_over_is_the_mean_of_those_pairs(known: dict[str, object]) -> None:
    """The single biggest number on the page. 0.667 → 67%."""
    assert known["stability"] == 0.667
    assert round(0.667 * 100) == 67


def test_tenure_streak_and_flips_match_the_hand_computed_membership(
    known: dict[str, object],
) -> None:
    tasks = known["tasks"]
    assert isinstance(tasks, list)
    by_uid = {t["uid"]: t for t in tasks}
    assert by_uid[1]["member"] == [1, 1, 1, 1] and by_uid[1]["tenure"] == 4
    assert by_uid[1]["streak"] == 4 and by_uid[1]["flips"] == 0
    assert by_uid[3]["member"] == [1, 1, 0, 1] and by_uid[3]["tenure"] == 3
    assert by_uid[3]["streak"] == 2, "longest UNBROKEN run, not the total"
    assert by_uid[3]["flips"] == 2, "off once and back on once"
    assert by_uid[4]["member"] == [0, 0, 1, 0] and by_uid[4]["tenure"] == 1
    assert by_uid[4]["flips"] == 2


def test_an_activity_never_on_the_path_is_absent_not_listed_with_zero(
    known: dict[str, object],
) -> None:
    """UID 5 is never critical in any version. The matrix is "ever on the path", so a
    never-critical activity must not appear — listing it with tenure 0 would inflate every
    denominator on the page."""
    tasks = known["tasks"]
    assert isinstance(tasks, list)
    assert 5 not in {t["uid"] for t in tasks}
    assert {t["uid"] for t in tasks} == {1, 2, 3, 4}


def test_per_version_critical_counts_match_the_construction(known: dict[str, object]) -> None:
    versions = known["versions"]
    assert isinstance(versions, list)
    assert [v["critical"] for v in versions] == [3, 3, 3, 3]
    assert [v["label"] for v in versions] == ["v1", "v2", "v3", "v4"]


def test_the_rows_are_ordered_most_stable_first(known: dict[str, object]) -> None:
    """The matrix's reading order is a claim: the backbone at the top, the jumpers at the
    bottom. Sorted by (-tenure, flips, uid)."""
    tasks = known["tasks"]
    assert isinstance(tasks, list)
    assert [t["uid"] for t in tasks] == [1, 2, 3, 4]


# ══ FAIL — schedules that are KNOWN BAD, which the tool must report as bad ════════════════════


def test_an_identical_path_every_update_reports_perfect_carry_over() -> None:
    """The ceiling. Nothing changed, so carry-over is 100% and nobody ever flips."""
    same = [_version(f"s{i}", {1, 2, 3}) for i in range(4)]
    d = _data(same)
    assert d["stability"] == 1.0
    pairs = d["pairs"]
    tasks = d["tasks"]
    assert isinstance(pairs, list) and isinstance(tasks, list)
    assert all(p["jaccard"] == 1.0 for p in pairs)
    assert all(p["entered"] == 0 and p["left"] == 0 for p in pairs)
    assert all(t["flips"] == 0 for t in tasks)


def test_a_path_rebuilt_from_scratch_every_update_reports_zero_carry_over() -> None:
    """The floor, and the case that matters most. Consecutive paths share NO activity, so the
    controlling chain is being rebuilt every update — GAO BP-6's failure. Mean carry-over must
    be 0%, not a comfortable-looking number."""
    churn = [
        _version("c1", {1, 2}),
        _version("c2", {3, 4}),
        _version("c3", {1, 2}),
        _version("c4", {3, 4}),
    ]
    d = _data(churn)
    pairs = d["pairs"]
    assert isinstance(pairs, list)
    assert [p["jaccard"] for p in pairs] == [0.0, 0.0, 0.0]
    assert d["stability"] == 0.0, "a fully-rebuilt path must report 0% carry-over"
    tasks = d["tasks"]
    assert isinstance(tasks, list)
    # every activity flips off and on three times across four versions
    assert {t["flips"] for t in tasks} == {3}


def test_a_completed_activity_leaves_the_path() -> None:
    """``effective_critical_set``'s documented rule: finished work drives nothing, so it is NOT
    on the path even when the file still flags it Critical. If this regressed, a schedule would
    look stable purely because completed activities never move."""
    before = _version("b1", {1, 2, 3})
    after = _version("b2", {1, 2, 3}, complete={3})
    d = _data([before, after])
    pairs = d["pairs"]
    versions = d["versions"]
    assert isinstance(pairs, list) and isinstance(versions, list)
    assert [v["critical"] for v in versions] == [3, 2], "the completed activity still counted"
    assert pairs[0]["left_uids"] == [3]
    assert pairs[0]["jaccard"] == round(2 / 3, 3)


def test_a_single_version_reports_no_similarity_rather_than_a_number() -> None:
    """One file has no consecutive pair. Stability is UNKNOWN, and unknown must be None so the
    page renders an em dash — never 0, which would read as 'completely unstable'."""
    d = _data([_version("only", {1, 2, 3})])
    assert d["stability"] is None
    assert d["pairs"] == []


def test_a_version_with_no_critical_activity_at_all_is_not_a_crash() -> None:
    """A fully-complete or fully-non-critical file yields an empty set. The union is then empty
    for that pair and the similarity is genuinely undefined — it must be None, not a divide."""
    d = _data([_version("e1", set()), _version("e2", set())])
    pairs = d["pairs"]
    assert isinstance(pairs, list)
    assert pairs[0]["jaccard"] is None, "0/0 must be undefined, not 0.0 or a crash"
    assert d["stability"] is None
    assert d["tasks"] == []


# ══ the page must SHOW what the dataset says ══════════════════════════════════════════════════


def test_the_rendered_headline_equals_the_oracles_own_number() -> None:
    """Closes the last gap: the dataset can be right while the page prints something else.
    Renders ``_stability_panels`` on the hand-computed fixture and reads the figure back."""
    from schedule_forensics.web.evolution import _stability_panels

    html = _stability_panels(KNOWN, _solve(KNOWN))
    assert ">67%<" in html, "the page did not print the hand-computed 67%"
    assert "STABLE" not in html or "67" in html
    # the matrix's own count, also hand-computed: four activities ever on the path
    assert "4 activities reached the critical path" in html
