"""R-65 — the engine's honoured leveling gaps meet MS Project's recorded window to the minute
(ADR-0508; the residual ADR-0501 registered).

The row: the engine's honoured gaps (ADR-0491) landed 1-28 minutes short of the window MS Project
recorded for the same split booking, systematic and one-directional, on "~100" bookings of the
29-file ``.mpp`` corpus. Measured on fresh conversions of all 29 files before anything changed:
239 split WORK bookings, 173 differing from their window; **102 of those differ by the minute
truncation alone** — at seconds resolution the recorded window equals the duration plus the
uncovered gaps EXACTLY on every one (24 distinct bookings once the four saves of the Large Test
File2 schedule are counted once; 1 to 62 minutes short, never long, on 1 to 69 gaps) — and the
70 whose window is SHORTER than the occupancy are not this class: 49 completed records (ADR-0476)
and 21 bookings carrying ADR-0502's absorbed delay or ending before their task.

The mechanism: MS Project stores every split boundary in tenths of a minute (all 3,742 boundaries
in the corpus are multiples of six seconds) and the engine measured each gap with both ends
truncated to the whole minute — 0.0 to 0.9 minutes short per gap, never long. The gaps are now
measured in working seconds and rounded CUMULATIVELY to the nearest minute at every boundary, so
the whole is the nearest minute of the true whole; the recorded-span ruler reads the nearest
minute too.

The oracle is the file's own recorded ``Assignment/Start`` / ``Finish`` window on the leg's
calendar — MS Project's placement, independent of the engine judged. Every pin here failed by
name on the pristine engine (UID 5342: 2,757 against 2,758; 5316: 9,329 against 9,333; 5273:
4,687 against 4,688; the leveled golden's 5306: 8 against MS Project's 10:24 of gaps).
"""

from __future__ import annotations

import gzip
from functools import cache
from pathlib import Path

import pytest

from schedule_forensics.engine import cpm as C
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.assignment import Assignment
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.resource import ResourceType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task, TaskType

pytestmark = pytest.mark.parity

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

LTF = "fuse_ltf/Large_Test_File.mspdi.xml.gz"
LTF2 = "fuse_ltf/Large_Test_File2.mspdi.xml.gz"
LEVELED = "ssi_uid152_leveled/Large_Test_File_Leveled.mspdi.xml.gz"

#: The R-65 population per golden — every split WORK booking of an active, unfinished,
#: undelayed task whose recorded window equals its duration plus its uncovered gaps at SECONDS
#: resolution (derived below from the file; the tuple pins it so a moved fixture or importer is
#: noticed). The Large Test File golden is the 'Large Test File.mpp' save, File2 its sibling,
#: Leveled the leveled save; the same UIDs carry different figures in each.
POPULATION = {
    LTF: (
        (5265, 76),
        (5269, 77),
        (5278, 70),
        (5280, 81),
        (5316, 77),
        (5317, 75),
        (5317, 82),
        (5317, 86),
        (5317, 88),
        (5324, 75),
        (5324, 82),
        (5324, 86),
        (5324, 88),
    ),
    LTF2: (
        (5243, 77),
        (5265, 76),
        (5268, 77),
        (5269, 77),
        (5273, 77),
        (5278, 70),
        (5280, 81),
        (5282, 81),
        (5284, 76),
        (5286, 76),
        (5308, 76),
        (5316, 77),
        (5317, 75),
        (5317, 82),
        (5317, 86),
        (5317, 88),
        (5320, 77),
        (5324, 75),
        (5324, 82),
        (5324, 86),
        (5324, 88),
        (5341, 71),
        (5342, 71),
    ),
    LEVELED: (
        (5265, 76),
        (5269, 77),
        (5278, 70),
        (5280, 81),
        (5284, 76),
        (5306, 75),
        (5306, 76),
        (5306, 77),
        (5306, 78),
        (5306, 82),
        (5316, 77),
        (5317, 75),
        (5317, 82),
        (5317, 86),
        (5317, 88),
        (5320, 77),
        (5324, 75),
        (5324, 82),
        (5324, 86),
        (5324, 88),
        (5341, 71),
    ),
}


@cache
def _load(rel: str) -> Schedule:
    path = GOLDEN / rel
    raw = path.read_bytes()
    text = gzip.decompress(raw).decode("utf-8") if path.suffix == ".gz" else raw.decode("utf-8")
    return parse_mspdi_text(text)


class _Booking:
    """One split WORK booking's leg arithmetic, from the ENGINE's own helpers (the leg calendar,
    the type rule, the gaps) beside the file's own window."""

    def __init__(self, sch: Schedule, t: Task, a: Assignment, by_uid: dict[int, Calendar]):
        self.uid, self.res = t.unique_id, a.resource_id
        self.cal = C.booking_calendar(sch, t, a, by_uid)
        others = [
            w
            for x in t.resource_assignments
            if x is not a
            and (r := sch.resources_by_id.get(x.resource_id)) is not None
            and r.type is ResourceType.WORK
            and x.work_minutes > 0
            for w in C._worked_windows(x)
        ]
        ratio = (
            min(1.0, (a.work_minutes / a.units) / t.duration_minutes)
            if t.task_type is TaskType.FIXED_UNITS
            else 1.0
        )
        self.span = round(ratio * t.duration_minutes)
        self.gaps = C._split_gaps(a, self.cal, others)
        span = self.span
        used = [(round(sh * span), g) for sh, g in self.gaps if 0 < round(sh * span) < span]
        self.gap_minutes = sum(g for _, g in used)
        self.occupancy = self.span + self.gap_minutes
        assert a.start is not None and a.finish is not None
        self.window = C._recorded_span(self.cal, a.start, a.finish)
        self.window_seconds = C._recorded_seconds(self.cal, a.start, a.finish)
        # the true gap in working seconds, the same task-split rule (ADR-0491)
        total = sum(p.work_minutes for p in a.work_pieces)
        worked = 0
        self.gap_seconds = 0
        for prev, nxt in zip(a.work_pieces, a.work_pieces[1:], strict=False):
            worked += prev.work_minutes
            g = C._recorded_seconds(self.cal, prev.finish, nxt.start) - C._covered_seconds(
                self.cal, prev.finish, nxt.start, others
            )
            if g > 0 and 0 < worked < total:
                self.gap_seconds += g
        self.seconds_exact = self.window_seconds == t.duration_minutes * 60 + self.gap_seconds
        self.in_class = (
            t.percent_complete < 100.0
            and a.leveling_delay_minutes == 0
            and bool(used)
            and abs(self.window_seconds - (t.duration_minutes * 60 + self.gap_seconds)) < 60
        )


def _bookings(rel: str) -> list[_Booking]:
    sch = _load(rel)
    by_uid = {c.uid: c for c in sch.calendars}
    out: list[_Booking] = []
    for t in sch.tasks:
        if t.is_summary or not t.is_active or t.duration_is_elapsed:
            continue
        if not t.resource_assignments or t.ignore_resource_calendar or t.duration_minutes <= 0:
            continue
        for a in t.resource_assignments:
            r = sch.resources_by_id.get(a.resource_id)
            if r is None or r.type is not ResourceType.WORK:
                continue
            if a.work_minutes <= 0 or a.units <= 0 or len(a.work_pieces) < 2:
                continue
            if a.start is None or a.finish is None:
                continue
            out.append(_Booking(sch, t, a, by_uid))
    return out


def _booking(rel: str, uid: int, res: int) -> _Booking:
    return next(b for b in _bookings(rel) if (b.uid, b.res) == (uid, res))


# --- the population, and the invariant on every member of it --------------------------------


@pytest.mark.parametrize("rel", [LTF, LTF2, LEVELED])
def test_every_r65_booking_occupies_exactly_the_window_ms_project_recorded(rel: str) -> None:
    """The class, derived from the file: every split booking of an unfinished, undelayed task
    whose window IS its duration plus its uncovered gaps to the second (to the duration's own
    import rounding, under a minute). On every one the leg's occupancy — the duration plus the
    gaps the engine honours, in whole minutes — equals the recorded window read to the nearest
    minute. The pristine engine was short on 10 / 19 / 16 of them (Large Test File / File2 /
    Leveled), by 1 to 62 minutes, never long."""
    members = [b for b in _bookings(rel) if b.in_class]
    assert tuple(sorted((b.uid, b.res) for b in members)) == POPULATION[rel]
    off = [(b.uid, b.res, b.window - b.occupancy) for b in members if b.window != b.occupancy]
    # File2's UID 5268 is the one member the duration's own import rounding leaves a minute
    # long (its own pin below); every other member occupies its window exactly
    assert off == ([(5268, 77, -1)] if rel == LTF2 else [])


def test_the_class_beside_the_row_is_not_this_class() -> None:
    """The bookings whose window is SHORTER than the occupancy are records or absorbed delays,
    not gap granularity: on the File2 golden, UIDs 5231 (four crews) and 5249 (three) are
    recorded-complete — a completed activity's window is its actual, and it adjudicates no
    scheduling rule (ADR-0476, ADR-0501) — and 5270 / 5274 carry ADR-0502's booking delay,
    absorbed inside the span they share with the task, so their windows begin after the task's.
    None of them is in the class, and none of them is exact at seconds resolution either."""
    sch = _load(LTF2)
    shorter = [b for b in _bookings(LTF2) if b.window < b.occupancy]
    assert sorted({b.uid for b in shorter}) == [5231, 5249, 5268, 5270, 5274]
    for b in shorter:
        t = sch.task_by_id(b.uid)
        a = next(x for x in t.resource_assignments if x.resource_id == b.res)
        if b.uid in (5231, 5249):
            assert C.is_recorded_complete(t) and not b.seconds_exact
        elif b.uid in (5270, 5274):
            assert a.leveling_delay_minutes > 0 and not b.seconds_exact
        assert not b.in_class or b.uid == 5268


def test_uid_5268_is_the_one_booking_the_durations_own_rounding_leaves_a_minute_long() -> None:
    """The residual this unit leaves, pinned so it cannot drift silently: File2's UID 5268 is
    8,157.8 minutes of duration (read 8,158 at import — the model's integer minutes) plus
    2,554.5 minutes of gap (read 2,555, half up) against a window of 10,712.3 (read 10,712):
    two halves rounded up, one whole rounded down — occupancy one minute LONG, the only such
    booking in the 29-file corpus. It was exact before by the coincidence of two truncations.
    Closing it needs the duration's seconds to survive import; deliberately not done."""
    b = _booking(LTF2, 5268, 77)
    assert (b.span, b.gap_minutes, b.occupancy, b.window) == (8158, 2555, 10713, 10712)
    assert b.gap_seconds == 153270 and b.window_seconds == 642738
    assert b.seconds_exact is False and b.window_seconds == 8157 * 60 + 48 + b.gap_seconds


# --- the witnesses, by name --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("uid", "res", "span", "gap_seconds", "gap_minutes", "window"),
    [
        # the row's three witnesses (ADR-0501): occupancy 2,757 / 9,329 / 4,687 read against the
        # windows 2,758 / 9,333 / 4,688 on the pristine engine
        (5342, 71, 2625, 7968, 133, 2758),  # four gaps, 132.8 minutes
        (5316, 77, 4256, 304608, 5077, 9333),  # nineteen gaps, 5,076.8 minutes
        (5273, 77, 4575, 6750, 113, 4688),  # one gap, 112.5 minutes — half up
        (5317, 88, 4989, 187104, 3118, 8107),  # sixteen gaps, 3,118.4 minutes; read 3,103
    ],
)
def test_the_witnesses_occupy_their_recorded_windows_to_the_minute(
    uid: int, res: int, span: int, gap_seconds: int, gap_minutes: int, window: int
) -> None:
    b = _booking(LTF2, uid, res)
    assert (b.span, b.gap_seconds, b.gap_minutes, b.window) == (
        span,
        gap_seconds,
        gap_minutes,
        window,
    )
    assert b.occupancy == b.window
    assert b.in_class


def test_leveled_5306s_four_gaps_of_two_minutes_thirty_six_seconds_read_ten_minutes() -> None:
    """ADR-0491 recorded this residual: MS Project's stored finish is the start plus the 39 h
    47 m duration plus four 2:36 daily gaps (10:24), and the integer-minute engine read
    2 x 4 = 8. Rounded cumulatively the boundaries read 3, 2, 3, 2 — ten, the nearest minute of
    10.4 — and the booking occupies its recorded 2,397 minutes exactly. The chain behind it
    (6873, 5307, 6521) still sits a day late because 5306's START is a day late for a reason
    that is not a split; the leg is now 0.4 minutes from MS Project's occupancy."""
    b = _booking(LEVELED, 5306, 78)
    assert b.gaps == ((0.08, 3), (0.28, 2), (0.48, 3), (0.68, 2))
    assert (b.gap_seconds, b.gap_minutes, b.span, b.occupancy, b.window) == (
        624,
        10,
        2387,
        2397,
        2397,
    )
