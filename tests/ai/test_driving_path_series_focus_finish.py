"""The focus's finish in the DRIVING-PATH SERIES is the file's own stored Finish (OR-20).

The operator asked a 32-version workbook for the driving path to UID 152 in every version and the
answer tabled a "driving-path finish" for one version 656 days later than the Finish MS Project
shows for it. The series' drivers were always measured on the file's **stored, progress-aware**
dates — the axis SSI's Directional Path runs on and the only one that reproduced its export
(``engine/driving_slack.py``, ADR-0011) — but the finish printed beside them was the engine's
logic-only CPM early finish, unlabelled. On the operator's own IMS the two disagree by more than a
day on 50 of 1,723 scheduled activities (up to 106 days); wherever the focus is one of them the
line carried a date the reference tools never show, and nothing said which date it was.

The fixture is the class measured on that IMS: v1 stores B and the focus 60 working days after
the point logic alone reaches (a gap the file's logic does not carry), v2 stores every date where
logic puts it. The oracle for every expected date is the stored ``finish`` the fixture itself
writes — independent of the engine that must reproduce it.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.ai.driving_facts import driving_path_series
from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

_START = dt.datetime(2025, 1, 6, 8, 0)  # a Monday
_DAY = 480
FOCUS = 90

#: The focus's stored Finish in each version — written here, reproduced by the engine (never the
#: other way round). v1's is 60 working days past the logic-only finish; v2's coincides with it.
V1_STORED_FINISH = dt.datetime(2025, 5, 2, 17, 0)
V2_STORED_FINISH = dt.datetime(2025, 2, 7, 17, 0)
#: The logic-only early finish of the focus in BOTH versions: A(10 d) -> B(10 d) -> focus(5 d)
#: from the project start = working day 25 = Friday 2025-02-07 17:00.
LOGIC_FINISH = dt.date(2025, 2, 7)


def _fs(pred: int, succ: int) -> Relationship:
    return Relationship(predecessor_id=pred, successor_id=succ, type=RelationshipType.FS)


def _task(uid: int, name: str, days: int, start: dt.datetime, finish: dt.datetime) -> Task:
    return Task(unique_id=uid, name=name, duration_minutes=days * _DAY, start=start, finish=finish)


def _d(m: int, d: int, h: int = 8) -> dt.datetime:
    return dt.datetime(2025, m, d, h, 0)


def _v1_pushed() -> Schedule:
    """A where logic puts it; B stored 60 working days after A ends; the focus right after B.

    Logic alone reaches the focus's finish on 02-07; the file says 05-02. On the stored axis only
    B drives (the A -> B link carries the 60-day gap as free float)."""
    return Schedule(
        name="prog",
        source_file="v1.mpp",
        project_start=_START,
        status_date=_START,
        tasks=(
            _task(1, "A", 10, _d(1, 6), _d(1, 17, 17)),
            _task(2, "B", 10, _d(4, 14), _d(4, 25, 17)),
            _task(3, "C", 1, _d(1, 6), _d(1, 6, 17)),
            _task(FOCUS, "Ready to Ship", 5, _d(4, 28), V1_STORED_FINISH),
        ),
        relationships=(_fs(1, 2), _fs(2, FOCUS), _fs(3, FOCUS)),
    )


def _v2_logic() -> Schedule:
    """Every stored date exactly where logic puts it — A and B both drive, no disagreement."""
    return Schedule(
        name="prog",
        source_file="v2.mpp",
        project_start=_START,
        status_date=dt.datetime(2025, 2, 3, 8, 0),
        tasks=(
            _task(1, "A", 10, _d(1, 6), _d(1, 17, 17)),
            _task(2, "B", 10, _d(1, 20), _d(1, 31, 17)),
            _task(3, "C", 1, _d(1, 6), _d(1, 6, 17)),
            _task(FOCUS, "Ready to Ship", 5, _d(2, 3), V2_STORED_FINISH),
        ),
        relationships=(_fs(1, 2), _fs(2, FOCUS), _fs(3, FOCUS)),
    )


def _workbook() -> tuple[list[Schedule], list[CPMResult]]:
    scheds = [_v1_pushed(), _v2_logic()]
    return scheds, [compute_cpm(s) for s in scheds]


def _series_text() -> str:
    facts = driving_path_series(*_workbook(), FOCUS)
    return next(f.text for f in facts if f.text.startswith("DRIVING-PATH SERIES"))


def _movement_text() -> str:
    facts = driving_path_series(*_workbook(), FOCUS)
    return next(f.text for f in facts if f.text.startswith("DRIVING-PATH MOVEMENT"))


def _segment(text: str, label: str, next_label: str | None) -> str:
    start = text.index(label)
    return text[start : text.index(next_label)] if next_label else text[start:]


def test_the_fixture_is_the_measured_class() -> None:
    """Precondition, not the claim: the engine's logic-only finish for the focus really is 02-07
    in both versions, so v1 is a genuine stored-vs-logic disagreement and v2 a genuine agreement.
    If this fails the fixture is wrong, not the fact builder."""
    _scheds, cpms = _workbook()
    for cpm in cpms:
        assert cpm.timings[FOCUS].early_finish == 25 * _DAY


def test_the_focus_finish_is_the_files_stored_finish_not_the_logic_only_one() -> None:
    """THE defect. v1's line must carry 2025-05-02 — the Finish MS Project shows and SSI exports —
    as the focus's finish. The pre-fix builder printed the logic-only 2025-02-07 there."""
    text = _series_text()
    v1 = _segment(text, "v1.mpp", "v2.mpp")
    assert f"UID {FOCUS} finishes {V1_STORED_FINISH.date().isoformat()}" in v1, v1
    assert "1 activity driving" in v1, v1  # the drivers are on the same (stored) axis


def test_a_logic_only_finish_that_disagrees_is_disclosed_beside_the_stored_one() -> None:
    """Law 2: a date the file's logic alone does not reproduce is stated, never silently replaced.
    v1 discloses the engine's own 2025-02-07 and the size of the gap in working days."""
    text = _series_text()
    v1 = _segment(text, "v1.mpp", "v2.mpp")
    assert "logic-only finish for it is" in v1, v1
    assert LOGIC_FINISH.isoformat() in v1, v1
    assert "60 working days earlier" in v1, v1


def test_no_disclosure_where_logic_and_the_file_agree() -> None:
    """The negative control that gives the one above teeth: v2's stored Finish IS the logic-only
    finish, so its line carries one date and no disclosure — a builder that always discloses, or
    that discloses on a sub-day difference, fails here."""
    text = _series_text()
    v2 = _segment(text, "v2.mpp", None)
    assert f"UID {FOCUS} finishes {V2_STORED_FINISH.date().isoformat()}" in v2, v2
    assert "logic-only finish for it is" not in v2, v2
    assert "2 activities driving" in v2, v2


def test_the_series_states_whose_date_the_finish_is() -> None:
    """The two per-version date lists in one fact sheet (this one and the SCHEDULE-LOGIC FINISH
    SERIES) must be tellable apart by a reader who sees only the text: the header names the
    stored Finish as the source and says the network finish is NOT what this line carries."""
    text = _series_text()
    assert "stored Finish" in text, text
    assert "NOT the project's network finish" in text, text


def test_the_movement_is_measured_on_the_stored_finish() -> None:
    """05-02 -> 02-07 is -84 calendar days on the stored axis; the logic-only finish did not move
    at all between the versions. The pre-fix census reported 0."""
    text = _movement_text()
    assert "moved -84 calendar day(s)" in text, text
    assert f"from {V1_STORED_FINISH.date().isoformat()} in v1.mpp" in text, text
    assert f"to {V2_STORED_FINISH.date().isoformat()} in v2.mpp" in text, text


def test_the_movement_counts_the_versions_where_logic_disagrees_with_the_file() -> None:
    """One of the two versions carries a focus whose logic-only finish disagrees with its stored
    Finish by a working day or more — the census says so, so a series where the engine and the
    reference tool part company is visible as a count, not discoverable only by reading 32 lines."""
    text = _movement_text()
    assert "in 1 of the 2 measured version(s)" in text, text
    assert "disagrees with the stored Finish" in text, text


def test_a_focus_without_stored_dates_still_reports_the_computed_finish() -> None:
    """Hand-authored schedules carry no stored dates; the CPM early finish is then the only finish
    there is, and the line says it is computed rather than pretending the file stored it."""
    bare = [
        Schedule(
            name="prog",
            source_file=label,
            project_start=_START,
            status_date=sd,
            tasks=(
                Task(unique_id=1, name="A", duration_minutes=10 * _DAY),
                Task(unique_id=FOCUS, name="Ready to Ship", duration_minutes=5 * _DAY),
            ),
            relationships=(_fs(1, FOCUS),),
        )
        for label, sd in (("b1.mpp", _START), ("b2.mpp", dt.datetime(2025, 2, 3, 8, 0)))
    ]
    facts = driving_path_series(bare, [compute_cpm(s) for s in bare], FOCUS)
    text = next(f.text for f in facts if f.text.startswith("DRIVING-PATH SERIES"))
    # working day 15 from a Monday start = Friday 2025-01-24
    lines = text[text.index("b1.mpp") :]
    assert f"UID {FOCUS} finishes 2025-01-24 (computed by CPM" in lines, lines
    assert "logic-only finish for it is" not in lines, lines


def test_a_next_morning_milestone_is_the_same_instant_not_a_disagreement() -> None:
    """MS Project stores the milestone that follows a Friday 17:00 finish at Monday 08:00; the
    engine's logic-only finish for it is the Friday 17:00 instant — the SAME working-minute offset
    on the project axis. A wall-clock ruler calls the two a day apart (measured: 480 minutes on the
    default calendar), so a threshold read on that ruler would disclose a disagreement that is a
    representation. The line must carry the stored Monday and nothing else."""
    monday = dt.datetime(2025, 2, 3, 8, 0)

    def _version(label: str, sd: dt.datetime) -> Schedule:
        return Schedule(
            name="prog",
            source_file=label,
            project_start=_START,
            status_date=sd,
            tasks=(
                _task(1, "A", 10, _d(1, 6), _d(1, 17, 17)),
                _task(2, "B", 10, _d(1, 20), _d(1, 31, 17)),
                Task(
                    unique_id=FOCUS,
                    name="Ready to Ship",
                    duration_minutes=0,
                    is_milestone=True,
                    start=monday,
                    finish=monday,
                ),
            ),
            relationships=(_fs(1, 2), _fs(2, FOCUS)),
        )

    scheds = [_version("m1.mpp", _START), _version("m2.mpp", monday)]
    cpms = [compute_cpm(s) for s in scheds]
    assert all(c.timings[FOCUS].early_finish == 20 * _DAY for c in cpms)  # Friday 17:00's offset
    facts = driving_path_series(scheds, cpms, FOCUS)
    text = next(f.text for f in facts if f.text.startswith("DRIVING-PATH SERIES"))
    lines = text[text.index("m1.mpp") :]
    assert f"UID {FOCUS} finishes 2025-02-03" in lines, lines
    assert "logic-only finish for it is" not in lines, lines
