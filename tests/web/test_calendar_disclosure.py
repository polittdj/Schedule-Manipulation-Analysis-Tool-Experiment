"""The Working-calendar panel names EVERY calendar the base pass runs anything on (R-59, ADR-0504).

Until ADR-0504 the panel disclosed a "single-calendar approximation" that ADR-0322 / ADR-0474 /
ADR-0503 had made false: the base pass honours a task's own calendar (its float axis), schedules
a WORK booking on the calendar its task and crew share, and the crews' calendars — the ones
``off_project_calendars`` never sees — were undisclosed, so the analyst read "single calendar"
under a multi-calendar result. The panel now names each calendar with the activities it touches,
from the engine's own execution plans, and the stale claim is gone. Single-calendar files stay
silent (no cry-wolf), and an importer note still reaches the page (ADR-0312).

Red first (2026-09-17, pristine ADR-0503 tree): ``plan_calendars`` does not exist, so the module
cannot import. Probed with the import bypassed, the pristine panel is SILENT on the crewed
schedule below (no notice at all: nothing about the task says "16 Hour Work Days") and on the
task-calendar variant it carries the "single-calendar approximation" sentence, cites ADR-0028 and
names neither the crew's calendar nor the intersection.
"""

from __future__ import annotations

import datetime as dt
import gzip
from pathlib import Path

from fastapi.testclient import TestClient

from schedule_forensics.engine.cpm import plan_calendars
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.assignment import Assignment
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.resource import Resource
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, _calendar_panel, create_app

_DAY = 480
GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
HARD_FILE = GOLDEN / "fuse_hardfile" / "Hard_File.mspdi.xml.gz"

STALE = ("single-calendar approximation", "models the single project calendar")

CAL_16 = Calendar(
    uid=11,
    name="16 Hour Work Days",
    working_minutes_per_day=960,
    day_segments=((360, 720), (780, 1380)),
)
SAT_CAL = Calendar(
    uid=12,
    name="Standard+Sat.",
    working_minutes_per_day=930,
    work_weekdays=(0, 1, 2, 3, 4, 5),
    day_segments=((420, 720), (750, 1140), (1170, 1410)),
)
CREW_16 = Resource(unique_id=2, name="Customer Service Team", calendar_uid=11)


def _crewed(cal: Calendar | None = None) -> Schedule:
    """A project-calendar task and a task booked on the 16-hour crew — with a task calendar of
    its own when ``cal`` is given (the derived-intersection case)."""
    tasks = (
        Task(unique_id=1, name="Mon-Fri task", duration_minutes=_DAY),
        Task(
            unique_id=2,
            name="Crewed task",
            duration_minutes=_DAY,
            calendar_uid=None if cal is None else cal.uid,
            resource_assignments=(Assignment(resource_id=2, work_minutes=_DAY, units=1.0),),
        ),
    )
    return Schedule(
        name="crewed",
        project_start=dt.datetime(2025, 1, 6, 8, 0),
        calendar=Calendar(name="Standard", day_segments=((480, 720), (780, 1020))),
        calendars=(CAL_16, SAT_CAL),
        resources=(CREW_16,),
        tasks=tasks,
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )


def _single() -> Schedule:
    tasks = (
        Task(unique_id=1, name="A", duration_minutes=_DAY),
        Task(unique_id=2, name="B", duration_minutes=_DAY),
    )
    return Schedule(
        name="plain",
        project_start=dt.datetime(2025, 1, 6, 8, 0),
        calendar=Calendar(name="Standard"),
        tasks=tasks,
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )


def test_a_crew_calendar_the_task_does_not_carry_is_named_on_the_panel() -> None:
    """The R-59 hole: nothing about the task says "16 Hour Work Days" — only its booking does —
    and the page must name it with the one activity it touches."""
    html = _calendar_panel(_crewed())
    assert "Working calendar" in html  # still the same panel
    assert 'class="notice info"' in html  # the disclosure is present
    assert "<b>16 Hour Work Days</b> (1)" in html
    assert "Not every activity runs on Standard." in html
    assert "ADR-0474" in html and "ADR-0503" in html and "ADR-0118" in html
    # the takeaway carries the split: one of two activities is off the project pattern
    assert "is the time basis for 1 of 2 activities; the other 1 run wholly or partly on" in html
    assert "on 1 other calendar, named below." in html


def test_the_stale_single_calendar_claim_is_gone() -> None:
    """The sentence the page carried until ADR-0504 was false since ADR-0322 / ADR-0474: a
    disclosure that over-claims an approximation the engine no longer makes is worse than none."""
    html = _calendar_panel(_crewed())
    for stale in STALE:
        assert stale not in html, stale
    assert "ADR-0028" not in html


def test_a_derived_intersection_is_named_with_both_names() -> None:
    """A task calendar meeting a crew calendar (ADR-0503) runs on a calendar no file carries; the
    page names it as the intersection, cites the activity, and says what it is."""
    html = _calendar_panel(_crewed(SAT_CAL))
    assert "<b>Standard+Sat. ∩ 16 Hour Work Days</b> (1 — UID 2; a derived calendar" in html
    assert "<b>Standard+Sat.</b> (1)" in html  # the task calendar, as the float axis
    assert "<b>16 Hour Work Days</b>" not in html  # the crew's calendar is NOT what the leg runs on


def test_single_calendar_panel_is_silent() -> None:
    html = _calendar_panel(_single())
    assert "Working calendar" in html  # the panel still renders
    assert 'class="notice info"' not in html  # ...but NO disclosure (nothing to disclose)
    assert (
        "Every computed date and float rides Standard: 8 h/day, a 5-day work week, 0 holiday(s)."
        in html
    )
    for stale in STALE:
        assert stale not in html


def _upload_hard_file(client: TestClient) -> str:
    data = gzip.decompress(HARD_FILE.read_bytes())
    resp = client.post("/upload", files={"files": ("Hard_File.mspdi.xml", data, "text/xml")})
    assert resp.status_code == 200
    return data.decode("utf-8-sig")


def test_hard_file_page_names_every_calendar_the_plan_runs_on() -> None:
    """The oracle the row names: the sentence on the /analysis page for Hard_File. Its figures are
    derived from the engine's listing on the same bytes (the listing's own pins against the XML
    live in ``tests/engine/test_plan_calendars.py``); the derived calendar is named with both
    names; the API's registry is untouched (a derived calendar is never registered, ADR-0503)."""
    client = TestClient(create_app(SessionState()))
    text = _upload_hard_file(client)
    plans = plan_calendars(parse_mspdi_text(text))
    page = client.get("/analysis/Hard_File").text
    assert "Working calendar" in page and 'class="notice info"' in page
    assert "Not every activity runs on Standard." in page
    for use in (*plans.axes, *plans.legs):
        n = len(use.task_uids)
        if use.derived:
            assert f"<b>{use.calendar.name}</b> ({n} — UID {use.task_uids[0]}" in page
        else:
            assert f"<b>{use.calendar.name}</b> ({n})" in page, use.calendar.name
    assert "<b>Standard+Sat. ∩ Customer Service Team</b> (1 — UID 94; a derived calendar" in page
    for name in ("Customer Service Team", "Content Developer", "Logistics"):
        assert f"<b>{name}</b> (" in page  # the crews the old page never named
    assert "1 activity has an elapsed duration and runs round the clock." in page
    plain = plans.population - len(plans.touched)
    assert (
        f"is the time basis for {plain} of {plans.population} activities; the other "
        f"{len(plans.touched)} run wholly or partly on 6 other calendars, named below." in page
    )
    for stale in STALE:
        assert stale not in page
    registry = [c["name"] for c in client.get("/api/analysis/Hard_File").json()["calendars"]]
    assert "Customer Service Team" in registry and not any("∩" in n for n in registry)


def _normalised() -> Schedule:
    """A schedule whose importer had to move the anchor (ADR-0312) — the note the panel owes."""
    return _single().model_copy(
        update={
            "import_notes": (
                "Project start time normalised from 08:00 to 00:00 on 2026-01-05: calendar "
                "'24 Hours' works 1440 minutes per day, so a working day beginning at 08:00 "
                "runs past midnight.",
            )
        }
    )


def test_an_import_note_reaches_the_panel_rather_than_only_the_log() -> None:
    """ADR-0310 §5 rejected "merely warned about". The anchor normalisation moves the reference
    every computed date is laid out from, so it has to be on the page — a console line the
    analyst never opens is not disclosure in a testimony tool."""
    html = _calendar_panel(_normalised())
    assert 'class="notice warn"' in html
    assert "On import:" in html
    assert "normalised from 08:00 to 00:00" in html


def test_a_file_taken_verbatim_shows_no_import_note() -> None:
    """No cry-wolf: the empty case is every schedule in the committed corpus."""
    html = _calendar_panel(_single())
    assert "On import:" not in html
    assert 'class="notice warn"' not in html
