"""The driving path to a focus UID, computed for EVERY loaded version (OR-11a).

The operator asked, of a 32-version workbook: *"calculate the driving path for UID 152 for each
version."* Measured on the pre-fix tree, the workbook ask handed the model exactly ONE
driving-path fact, citing ONE file — the newest (``driving_path_facts(schedules[-1], cpms[-1],
text)``). Thirty-one versions were invisible to the question, so no model, however good, could
answer it: the evidence did not exist.

The engine has always been able to compute it. ``compute_driving_slack`` reproduces the operator's
SSI Directional Path export for UID 152 on the real 2,126-task master IMS EXACTLY — 76 of 76
members, verified against ``golden/ssi_uid152/case.json`` — and one call costs 0.039 s there, so a
32-version series is ~1.2 s on top of the 32 CPM solves the ask already pays for. What was missing
was the per-version LOOP and a fact to carry it.

These fixtures are hand-authored so the path genuinely MOVES between versions: v1 is driven
through A→B, v2 is re-wired so C drives instead while the focus's own finish does not move (the
forensic pattern the operator is hunting), and v3 deletes the focus entirely.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.ai.driving_facts import (
    driving_path_series,
    driving_path_series_facts,
)
from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

_START = dt.datetime(2025, 1, 6, 8, 0)
_DAY = 480
FOCUS = 90


def _fs(pred: int, succ: int) -> Relationship:
    return Relationship(predecessor_id=pred, successor_id=succ, type=RelationshipType.FS)


def _v1() -> Schedule:
    """A(10d) -> B(10d) -> FOCUS, and C(1d) -> FOCUS. The A-B chain drives; C has slack."""
    return Schedule(
        name="prog",
        source_file="v1.mpp",
        project_start=_START,
        status_date=dt.datetime(2025, 1, 6, 8, 0),
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=10 * _DAY),
            Task(unique_id=2, name="B", duration_minutes=10 * _DAY),
            Task(unique_id=3, name="C", duration_minutes=1 * _DAY),
            Task(unique_id=FOCUS, name="Ready to Ship", duration_minutes=5 * _DAY),
        ),
        relationships=(_fs(1, 2), _fs(2, FOCUS), _fs(3, FOCUS)),
    )


def _v2() -> Schedule:
    """RE-WIRED: C is grown to 20 d and takes over as the driver; A->B is cut to 5+5 d so it
    falls off the path. The focus's own early finish is UNCHANGED (20 d of predecessor either
    way), so the date holds while the path underneath it is different."""
    return Schedule(
        name="prog",
        source_file="v2.mpp",
        project_start=_START,
        status_date=dt.datetime(2025, 2, 3, 8, 0),
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=5 * _DAY),
            Task(unique_id=2, name="B", duration_minutes=5 * _DAY),
            Task(unique_id=3, name="C", duration_minutes=20 * _DAY),
            Task(unique_id=FOCUS, name="Ready to Ship", duration_minutes=5 * _DAY),
        ),
        relationships=(_fs(1, 2), _fs(2, FOCUS), _fs(3, FOCUS)),
    )


def _v1_later() -> Schedule:
    """v1's logic EXACTLY, one month on — the no-change control for the movement census."""
    return _v1().model_copy(
        update={"source_file": "v1b.mpp", "status_date": dt.datetime(2025, 2, 3, 8, 0)}
    )


def _v3() -> Schedule:
    """The focus activity is DELETED — a version that cannot carry a driving path to it."""
    return Schedule(
        name="prog",
        source_file="v3.mpp",
        project_start=_START,
        status_date=dt.datetime(2025, 3, 3, 8, 0),
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=5 * _DAY),
            Task(unique_id=2, name="B", duration_minutes=5 * _DAY),
        ),
        relationships=(_fs(1, 2),),
    )


def _workbook(*builders: object) -> tuple[list[Schedule], list[CPMResult]]:
    scheds = [b() for b in builders]  # type: ignore[operator]
    return scheds, [compute_cpm(s) for s in scheds]


def _text(facts: tuple[object, ...]) -> str:
    return " ".join(f.text for f in facts)  # type: ignore[attr-defined]


# --- the regression -----------------------------------------------------------------------


def test_the_series_names_every_loaded_version() -> None:
    """THE defect. Before OR-11a exactly one version reached the model."""
    scheds, cpms = _workbook(_v1, _v2, _v3)
    blob = _text(driving_path_series(scheds, cpms, FOCUS))
    for label in ("v1.mpp", "v2.mpp", "v3.mpp"):
        assert label in blob, f"{label} missing from the driving-path series"


def test_each_version_carries_its_own_driver_count_not_the_newest_ones() -> None:
    """v1 is driven through A->B (2 drivers), v2 through C (1). A series that recomputed
    nothing — or applied one version's path to all — cannot show both."""
    scheds, cpms = _workbook(_v1, _v2)
    blob = _text(driving_path_series(scheds, cpms, FOCUS))
    assert "2 activities" in blob and "1 activity" in blob, blob


def test_a_version_without_the_focus_says_so_and_never_reports_zero() -> None:
    """Law 2: missing shows as missing, never as a fabricated 0. A deleted focus is also a
    forensic signal in its own right, so it must be stated rather than skipped."""
    scheds, cpms = _workbook(_v1, _v3)
    blob = _text(driving_path_series(scheds, cpms, FOCUS))
    assert "v3.mpp" in blob
    low = blob.lower()
    assert "not in this version" in low or "not present" in low or "absent" in low, blob
    assert "v3.mpp — 0 " not in blob and "v3.mpp 0 activities" not in blob


def test_the_series_is_ordered_oldest_first_whatever_order_it_is_given() -> None:
    """The operator's question is explicitly "starting at the earliest data date". List order
    is not data-date order — the caller hands these over in whatever order the session held."""
    scheds, cpms = _workbook(_v2, _v1)  # newest FIRST on the way in
    blob = _text(driving_path_series(scheds, cpms, FOCUS))
    assert blob.index("v1.mpp") < blob.index("v2.mpp"), blob


def test_each_version_is_measured_with_its_own_cpm() -> None:
    """The pairing trap: ordering the schedules without re-pairing their CPMs measures one
    version's network against another's timings — a silently wrong number, the worst kind."""
    scheds, cpms = _workbook(_v2, _v1)
    blob = _text(driving_path_series(scheds, cpms, FOCUS))
    v1_seg = blob[blob.index("v1.mpp") : blob.index("v2.mpp")]
    v2_seg = blob[blob.index("v2.mpp") :]
    assert "2 activities" in v1_seg, v1_seg  # v1 is the A->B chain
    assert "1 activity" in v2_seg, v2_seg  # v2 is driven by C alone


def _movement(scheds: list[Schedule], cpms: list[CPMResult]) -> str:
    facts = driving_path_series(scheds, cpms, FOCUS)
    return next(f.text for f in facts if "DRIVING-PATH MOVEMENT" in f.text)


def test_the_movement_fact_counts_a_rewire_that_did_not_move_the_finish() -> None:
    """The forensic verdict, stated as a MEASUREMENT and never as an accusation.

    v1 -> v2 is exactly one step, it IS a re-wire ({1,2} -> {3}, no overlap), and the focus's
    early finish is identical either way (12,000 working minutes, verified against the engine).
    So the census is 1 and 1 — asserted as VALUES, because a mutation that never counts a
    re-wire still produces every word of this sentence (measured: it survived an earlier version
    of this test that checked the wording)."""
    scheds, cpms = _workbook(_v1, _v2)
    text = _movement(scheds, cpms)
    assert "1 changed WHICH activities drive it" in text, text
    assert "1 of those changed the membership" in text, text
    for loaded in ("fraud", "deliberate", "concealed", "manipulated", "intentional"):
        assert loaded not in text.lower(), f"the engine must not assert intent: {loaded!r}"


def test_the_movement_fact_counts_ZERO_when_nothing_was_rewired() -> None:
    """The negative control that gives the one above teeth: identical logic in both versions
    (only the data date differs) must count 0 re-wires. A census hard-wired to any constant
    fails one of this pair."""
    scheds, cpms = _workbook(_v1, _v1_later)
    text = _movement(scheds, cpms)
    assert "0 changed WHICH activities drive it" in text, text
    assert "0 of those changed the membership" in text, text


def test_every_series_fact_is_pinned() -> None:
    """The 48-fact model cap and the 12-fact shown cap both rank by question overlap; the
    population frame must survive both (ADR-0392's rule, applied here)."""
    scheds, cpms = _workbook(_v1, _v2, _v3)
    facts = driving_path_series(scheds, cpms, FOCUS)
    assert facts and all(f.pinned for f in facts)  # type: ignore[attr-defined]


def test_one_version_is_not_a_series() -> None:
    scheds, cpms = _workbook(_v1)
    assert driving_path_series(scheds, cpms, FOCUS) == ()


def test_a_focus_absent_from_every_version_yields_no_series() -> None:
    scheds, cpms = _workbook(_v3, _v3)
    assert driving_path_series(scheds, cpms, 4242) == ()


# --- the question gate --------------------------------------------------------------------


def test_the_series_fires_only_on_a_driving_question_naming_a_uid() -> None:
    scheds, cpms = _workbook(_v1, _v2)
    assert driving_path_series_facts(scheds, cpms, "how is the schedule doing?") == ()
    assert driving_path_series_facts(scheds, cpms, f"is UID {FOCUS} healthy?") == ()
    hit = driving_path_series_facts(scheds, cpms, f"driving path to UID {FOCUS} per version?")
    assert hit and "v1.mpp" in _text(hit)
