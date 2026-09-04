"""/integrity's Counterfactual panel: working days, and the project finish NAMED (ADR-0462).

The operator (2026-09-04) read this on the page:

    "…the project finish would have been 2029-10-29 instead of the reported 2029-09-28 —
    31 working day(s) of apparent recovery … Target UID 152 (Ready to Ship): would have
    finished 2027-12-30 instead of 2027-10-04."

and asked why one CPM to one target yields two different dates. Two defects, one panel:

1. **The unit was wrong.** ``finish_delta_days`` was a calendar-``date`` subtraction, printed
   under a "working day(s)" label: 2029-09-28 → 2029-10-29 IS 31 calendar days (about 21
   working days on a five-day week). The engine now reports the CPM's own working-minute move
   over the calendar's day — the unit every other delta on the page already used.
2. **The two dates were never explained.** They are two DIFFERENT activities — the network's
   last finish (2029) and the target milestone (2027) — and the panel said only "the project
   finish". It now names that activity, gives the target its own working-day move, and says
   in one line that the two finishes are different activities.

Fixture: A(3d, was 10d) → C(2d); B(5d) → C. Cutting A handed the path to B; restoring A moves
C (the finish activity, UID 3) from Tue 2026-01-13 to Tue 2026-01-20 — 7 calendar days,
**5 working days** — while B (the chosen target, UID 2) does not move at all. Pre-fix the page
printed "7 working day(s)" and no target move.
"""

from __future__ import annotations

import datetime as dt
import re

from fastapi.testclient import TestClient

from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

START = dt.datetime(2026, 1, 5, 8, 0)  # a Monday
DAY = 480


def _version(name: str, a_minutes: int, status: dt.datetime) -> Schedule:
    return Schedule(
        name=name,
        source_file=f"{name}.xml",
        project_start=START,
        status_date=status,
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=a_minutes),
            Task(unique_id=2, name="B", duration_minutes=5 * DAY),
            Task(unique_id=3, name="C", duration_minutes=2 * DAY),
        ),
        relationships=(
            Relationship(predecessor_id=1, successor_id=3),
            Relationship(predecessor_id=2, successor_id=3),
        ),
    )


def _page(target_uid: int | None) -> str:
    c = TestClient(create_app(SessionState()), raise_server_exceptions=True)
    st = c.app.state.session  # type: ignore[attr-defined]
    prior = _version("v1", 10 * DAY, dt.datetime(2026, 1, 5))
    current = _version("v2", 3 * DAY, dt.datetime(2026, 2, 2))
    st.schedules[prior.source_file] = prior
    st.schedules[current.source_file] = current
    st.target_uid = target_uid
    r = c.get("/integrity")
    assert r.status_code == 200, r.status_code
    return r.text


def _counterfactual_panel(page: str) -> str:
    m = re.search(r'<div class="panel counterfactual">(.*?)</div>\s*(?:<div|$)', page, re.S)
    assert m, "the counterfactual panel did not render"
    return m.group(1)


def test_the_delta_is_working_days_and_the_finish_activity_is_named() -> None:
    panel = _counterfactual_panel(_page(target_uid=2))
    # 2026-01-13 → 2026-01-20 is 7 calendar days and 5 working days: the panel says 5
    assert "<b>2026-01-20</b> instead of the reported\n<b>2026-01-13</b>" in panel, panel
    assert "<b class=fail>5 working day(s)</b> of apparent recovery" in panel, panel
    assert "7 working day(s)" not in panel
    # "the project finish" names WHICH activity it is
    assert "the project\nfinish (the network's last activity, UID 3 &ldquo;C&rdquo;)" in panel


def test_the_target_line_carries_its_own_move_and_the_two_are_told_apart() -> None:
    panel = _counterfactual_panel(_page(target_uid=2))
    # B is the target; restoring A does not move it — and the panel SAYS so instead of leaving
    # two bare dates beside a different activity's delta
    assert (
        "Target UID 2 (B): would have finished <b>2026-01-09</b> instead of <b>2026-01-09</b>"
        " — <b>no change</b> on the target." in panel
    ), panel
    assert "The project finish and the target are different activities" in panel


def test_a_target_that_is_the_finish_activity_moves_by_the_same_working_days() -> None:
    panel = _counterfactual_panel(_page(target_uid=3))
    assert "<b class=fail>5 working day(s)</b> of apparent recovery came from the changes" in panel
    assert (
        "Target UID 3 (C): would have finished <b>2026-01-20</b> instead of <b>2026-01-13</b>"
        " — <b class=fail>5 working day(s)</b> of apparent recovery on the target" in panel
    ), panel
    # same activity on both lines: no "different activities" note
    assert "different activities" not in panel
