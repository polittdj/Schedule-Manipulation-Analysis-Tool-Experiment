"""Targeted importer coverage — friendly-JSON fallbacks, MSPDI/XER edge field paths,
and the Java/JRE discovery helpers (no real .mpp / JVM required).

These exercise narrow, real-world-tolerant branches that the broader importer suites do
not reach: malformed-but-recoverable JSON, calendar/exception edge cases, model-validation
error wrapping, and the cross-platform Java discovery order.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from schedule_forensics.importers import (
    ImporterError,
    mpp_mpxj,
    parse_json_text,
    parse_mspdi_text,
    parse_xer_text,
)
from schedule_forensics.importers import mspdi as mspdi_mod
from schedule_forensics.importers import xer as xer_mod
from schedule_forensics.model.relationship import Relationship


def _clndr_data(days: dict[int, list[tuple[str, str]]], exceptions: list[tuple[int, str]]) -> str:
    """Build a P6 ``clndr_data`` blob: days = {1..7: [(from, to), ...]},
    exceptions = [(excel_serial, "" | "HH:MM-HH:MM"), ...] ("" = full day off). Inlined here (not
    imported from another test module) so it resolves without the ``tests`` package on sys.path."""
    day_nodes = []
    for day in range(1, 8):
        spans = days.get(day, [])
        inner = "".join(f"(0||{i}(s|{s}|f|{f})())" for i, (s, f) in enumerate(spans))
        day_nodes.append(f"(0||{day}()({inner}))" if inner else f"(0||{day}())")
    exc_nodes = []
    for i, (serial, hours) in enumerate(exceptions):
        if hours:
            start, finish = hours.split("-")
            exc_nodes.append(f"(0||{i}(d|{serial})((0||0(s|{start}|f|{finish})())))")
        else:
            exc_nodes.append(f"(0||{i}(d|{serial})())")
    return (
        "(0||CalendarData()("
        f"(0||DaysOfWeek()({''.join(day_nodes)}))"
        f"(0||Exceptions()({''.join(exc_nodes)}))"
        "))"
    )


# --- JSON importer: friendly-parse fallback to strict pydantic + the loud failure --------

_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _force_self_loop(*, predecessor_id: int, successor_id: int, **kwargs: object) -> Relationship:
    """A Relationship factory that forces a self-loop, so the real model validator raises a
    ValidationError the importer must wrap — used to reach the link-validation error paths."""
    return Relationship(
        predecessor_id=predecessor_id,
        successor_id=predecessor_id,
        **kwargs,  # type: ignore[arg-type]
    )


def test_dt_passes_through_an_existing_datetime_object() -> None:
    # json.loads never yields a datetime, but the strict-serialization fallback (which
    # model_validate handles) and the _dt helper must accept an already-parsed datetime.
    import datetime as dt

    from schedule_forensics.importers.json_schedule import _dt

    moment = dt.datetime(2025, 1, 6, 8, 0)
    assert _dt(moment) is moment  # returned unchanged (line 41), never re-parsed
    assert _dt(None) is None  # empty/None -> None (line 39), never an error
    assert _dt("") is None


def test_friendly_parse_failure_falls_back_to_strict_serialization() -> None:
    # A document whose 'tasks' is shaped like the STRICT pydantic serialization (objects the
    # friendly parser chokes on) must round-trip through Schedule.model_validate, not error.
    from schedule_forensics.model.calendar import Calendar
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task

    strict = Schedule(
        name="Strict",
        project_start=__import__("datetime").datetime(2025, 1, 6, 8, 0),
        calendar=Calendar(),
        tasks=(Task(unique_id=1, name="A", duration_minutes=480),),
    )
    # the strict dump carries fields the friendly _task() does not understand (e.g. it lacks
    # the friendly shape), so _from_friendly raises and the model_validate fallback wins.
    data = json.loads(strict.model_dump_json())
    reparsed = parse_json_text(json.dumps(data))
    assert reparsed.name == "Strict"
    assert reparsed.tasks_by_id[1].name == "A"


def test_friendly_parse_failure_that_strict_also_rejects_surfaces_friendly_cause() -> None:
    # tasks present (so the 'tasks' guard passes) but each task is malformed in a way that
    # breaks BOTH the friendly parser (TypeError on int(None)) and strict validation — the
    # error must name the friendly cause, not pydantic's strict-schema text.
    bad = json.dumps({"name": "x", "tasks": [{"unique_id": None, "name": "A"}]})
    with pytest.raises(ImporterError, match="could not read JSON schedule"):
        parse_json_text(bad)


# --- MSPDI: exception-range, extended-attribute, and validation-error field paths --------


def _doc(body: str, *, start: str = "<StartDate>2025-01-06T08:00:00</StartDate>") -> str:
    return f"<Project {_NS}>{start}{body}</Project>"


def test_mspdi_calendar_exception_with_no_timeperiod_yields_no_holiday() -> None:
    # an Exception node with no <TimePeriod> child -> _exception_range(None) -> empty set
    # (line 376), so the day pattern stays intact and no holiday is fabricated.
    body = (
        "<CalendarUID>1</CalendarUID>"
        "<Calendars><Calendar><UID>1</UID><Name>Std</Name>"
        "<WeekDays>"
        + "".join(
            f"<WeekDay><DayType>{d}</DayType><DayWorking>1</DayWorking>"
            "<WorkingTimes><WorkingTime><FromTime>08:00:00</FromTime>"
            "<ToTime>16:00:00</ToTime></WorkingTime></WorkingTimes></WeekDay>"
            for d in range(2, 7)  # Mon-Fri
        )
        + "</WeekDays>"
        "<Exceptions><Exception><DayWorking>0</DayWorking></Exception></Exceptions>"
        "</Calendar></Calendars>"
        "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert sch.calendar.work_weekdays == (0, 1, 2, 3, 4)
    assert sch.calendar.holidays == ()  # the period-less exception contributed nothing


def test_mspdi_calendar_exception_with_inverted_range_is_ignored() -> None:
    # FromDate after ToDate is a nonsense range -> _exception_range returns empty (line 380).
    body = (
        "<CalendarUID>1</CalendarUID>"
        "<Calendars><Calendar><UID>1</UID><Name>Std</Name>"
        "<WeekDays>"
        + "".join(
            f"<WeekDay><DayType>{d}</DayType><DayWorking>1</DayWorking>"
            "<WorkingTimes><WorkingTime><FromTime>08:00:00</FromTime>"
            "<ToTime>16:00:00</ToTime></WorkingTime></WorkingTimes></WeekDay>"
            for d in range(2, 7)
        )
        + "</WeekDays>"
        "<Exceptions><Exception><DayWorking>0</DayWorking><TimePeriod>"
        "<FromDate>2025-07-10T00:00:00</FromDate><ToDate>2025-07-01T00:00:00</ToDate>"
        "</TimePeriod></Exception></Exceptions>"
        "</Calendar></Calendars>"
        "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert sch.calendar.holidays == ()  # the inverted range produced no holiday


def test_mspdi_calendar_element_without_uid_is_skipped() -> None:
    # a <Calendar> with no <UID> is skipped when indexing the calendars-by-uid map (the
    # 285->283 loop-back), and the project resolves its real, UID-carrying calendar.
    body = (
        "<CalendarUID>1</CalendarUID>"
        "<Calendars>"
        "<Calendar><Name>Ghost</Name></Calendar>"  # no UID -> skipped
        "<Calendar><UID>1</UID><Name>Real</Name>"
        "<WeekDays>"
        + "".join(
            f"<WeekDay><DayType>{d}</DayType><DayWorking>1</DayWorking>"
            "<WorkingTimes><WorkingTime><FromTime>08:00:00</FromTime>"
            "<ToTime>16:00:00</ToTime></WorkingTime></WorkingTimes></WeekDay>"
            for d in range(2, 7)
        )
        + "</WeekDays></Calendar></Calendars>"
        "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert sch.calendar.name == "Real"
    assert sch.calendar.work_weekdays == (0, 1, 2, 3, 4)


def test_mspdi_extended_attribute_without_field_id_is_ignored() -> None:
    # a project-level ExtendedAttribute with no <FieldID> cannot be labelled -> skipped
    # (line 408); a task ExtendedAttribute with no FieldID/Value is likewise skipped (425).
    body = (
        "<ExtendedAttributes>"
        "<ExtendedAttribute><Alias>NoId</Alias></ExtendedAttribute>"  # no FieldID -> line 408
        "<ExtendedAttribute><FieldID>188743731</FieldID><Alias>CA-WBS</Alias>"
        "<FieldName>Text1</FieldName></ExtendedAttribute>"
        "</ExtendedAttributes>"
        "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration>"
        "<ExtendedAttribute><Value>orphan</Value></ExtendedAttribute>"  # no FieldID -> line 425
        "<ExtendedAttribute><FieldID>188743731</FieldID></ExtendedAttribute>"  # no Value -> 425
        "<ExtendedAttribute><FieldID>188743731</FieldID><Value>CA-7</Value></ExtendedAttribute>"
        "</Task></Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert sch.tasks_by_id[1].custom_fields == (("CA-WBS", "CA-7"),)
    assert sch.custom_field_labels == ("CA-WBS",)


def test_mspdi_task_model_validation_error_is_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    # A value that survives parsing but fails the Task model (here a negative duration the ISO
    # grammar cannot itself produce) must surface as an ImporterError naming the UID (line 497).
    monkeypatch.setattr(mspdi_mod, "iso_duration_to_minutes", lambda _raw: -1)
    body = "<Tasks><Task><UID>7</UID><Name>Bad</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"
    with pytest.raises(ImporterError, match="task UID 7 is invalid"):
        parse_mspdi_text(_doc(body))


def test_mspdi_relationship_model_validation_error_is_wrapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A PredecessorLink that constructs a model-invalid Relationship must surface as an
    # ImporterError naming the edge (lines 583-584). Forcing a self-loop at construction
    # (which the pre-filter would normally drop) makes the real model validator raise.
    monkeypatch.setattr(mspdi_mod, "Relationship", _force_self_loop)
    body = (
        "<Tasks>"
        "<Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task>"
        "<Task><UID>2</UID><Name>B</Name><Duration>PT8H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task></Tasks>"
    )
    with pytest.raises(ImporterError, match="invalid logic link 1->2"):
        parse_mspdi_text(_doc(body))


# --- XER: progress, relationship, calendar, and cost edge paths --------------------------


def _xer(tables: list[tuple[str, list[str], list[list[str]]]]) -> str:
    lines = ["ERMHDR\t19.12\t2025-02-01"]
    for name, fields, rows in tables:
        lines.append("%T\t" + name)
        lines.append("%F\t" + "\t".join(fields))
        lines.extend("%R\t" + "\t".join(row) for row in rows)
    lines.append("%E")
    return "\n".join(lines)


_MIN_PROJECT = (
    "PROJECT",
    ["proj_id", "proj_short_name", "plan_start_date"],
    [["1", "P1", "2025-01-06 08:00"]],
)


def test_xer_in_progress_task_with_no_target_duration_uses_physical_percent() -> None:
    # started-but-unfinished + CP_Drtn but target_drtn_hr_cnt == 0 -> the duration share
    # cannot be computed, so the physical % is the fallback (line 393).
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                [
                    "task_id",
                    "proj_id",
                    "task_name",
                    "task_type",
                    "complete_pct_type",
                    "phys_complete_pct",
                    "target_drtn_hr_cnt",
                    "remain_drtn_hr_cnt",
                    "act_start_date",
                ],
                [["1", "1", "A", "TT_Task", "CP_Drtn", "33", "0", "0", "2025-01-06 08:00"]],
            ),
        ]
    )
    assert parse_xer_text(text).tasks_by_id[1].percent_complete == 33.0


def test_xer_relationship_model_validation_error_is_wrapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A TASKPRED row whose Relationship fails the model must surface as an ImporterError
    # naming the edge (lines 439-440). Forcing a self-loop at construction trips the validator
    # AFTER the importer's own self-reference pre-filter (the two endpoints differ in the row).
    monkeypatch.setattr(xer_mod, "Relationship", _force_self_loop)
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["1", "1", "A", "TT_Task", "8"], ["2", "1", "B", "TT_Task", "8"]],
            ),
            (
                "TASKPRED",
                ["task_id", "pred_task_id", "pred_type", "lag_hr_cnt"],
                [["2", "1", "PR_FS", "0"]],
            ),
        ]
    )
    with pytest.raises(ImporterError, match="invalid logic link 1->2"):
        parse_xer_text(text)


def test_xer_negative_target_duration_task_is_wrapped() -> None:
    # a negative target_drtn_hr_cnt yields a negative duration the Task model rejects -> the
    # importer wraps it as a task ImporterError (lines 365-366), naming the task_id.
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["9", "1", "Bad", "TT_Task", "-8"]],
            ),
        ]
    )
    with pytest.raises(ImporterError, match="task task_id 9 is invalid"):
        parse_xer_text(text)


def test_xer_calendar_table_with_no_matching_row_keeps_the_default() -> None:
    # a CALENDAR table exists but the project's clndr_id matches nothing AND no default_flag=Y
    # row exists -> row stays None and the standard default calendar is used (line 489).
    text = _xer(
        [
            (
                "PROJECT",
                ["proj_id", "proj_short_name", "plan_start_date", "clndr_id"],
                [["1", "P1", "2025-01-06 08:00", "999"]],  # no such calendar
            ),
            (
                "CALENDAR",
                ["clndr_id", "default_flag", "clndr_name", "day_hr_cnt"],
                [["100", "N", "Field", "10"]],  # default_flag != Y -> no fallback match
            ),
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["1", "1", "A", "TT_Task", "8"]],
            ),
        ]
    )
    cal = parse_xer_text(text).calendar
    assert cal.working_minutes_per_day == 480
    assert cal.work_weekdays == (0, 1, 2, 3, 4)


def test_xer_calendar_with_weekdays_but_no_dominant_minutes_degrades_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Defensive guard (line 516): if a parseable weekday grid exists but the dominant per-day
    # minute total comes back None, the calendar keeps its name and falls to the safe default
    # rather than crashing. The condition is documented unreachable on real data, so the
    # dominant-minutes helper is forced to None to exercise the guard.
    five_eights = {d: [("08:00", "12:00"), ("13:00", "17:00")] for d in (2, 3, 4, 5, 6)}
    monkeypatch.setattr(xer_mod, "dominant_day_minutes", lambda _totals: None)
    text = _xer(
        [
            (
                "PROJECT",
                ["proj_id", "proj_short_name", "plan_start_date", "clndr_id"],
                [["1", "P1", "2025-01-06 08:00", "100"]],
            ),
            (
                "CALENDAR",
                ["clndr_id", "default_flag", "clndr_name", "clndr_data"],
                [["100", "Y", "Weird", _clndr_data(five_eights, [])]],
            ),
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["1", "1", "A", "TT_Task", "8"]],
            ),
        ]
    )
    cal = parse_xer_text(text).calendar
    assert cal.name == "Weird"  # the name survives even on the defensive fallback
    assert cal.working_minutes_per_day == 480  # the safe default per-day total


def test_xer_calendar_exception_with_invalid_excel_serial_yields_no_holiday() -> None:
    # an Exceptions node carrying a serial that excel_serial_to_date() cannot resolve adds no
    # holiday (the 562->555 loop-back where `day is None`), while the day grid still parses.
    five_eights = {d: [("08:00", "12:00"), ("13:00", "17:00")] for d in (2, 3, 4, 5, 6)}
    # serial 0 is before P6's 1900 epoch floor -> excel_serial_to_date returns None
    data = _clndr_data(five_eights, [(0, "")])
    text = _xer(
        [
            (
                "PROJECT",
                ["proj_id", "proj_short_name", "plan_start_date", "clndr_id"],
                [["1", "P1", "2025-01-06 08:00", "100"]],
            ),
            (
                "CALENDAR",
                ["clndr_id", "default_flag", "clndr_name", "day_hr_cnt", "clndr_data"],
                [["100", "Y", "Std", "8", data]],
            ),
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["1", "1", "A", "TT_Task", "8"]],
            ),
        ]
    )
    cal = parse_xer_text(text).calendar
    assert cal.work_weekdays == (0, 1, 2, 3, 4)
    assert cal.holidays == ()  # the unresolvable serial added no day off


def test_xer_projcost_row_without_task_id_and_target_only_expense() -> None:
    # PROJCOST exercises two narrow paths: a row with no task_id is skipped (line 637), and a
    # target-only expense row (no remain_cost) does NOT mark the task as having remaining cost
    # (branch 639->641), so a budget-only task keeps cost == None.
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["1", "1", "A", "TT_Task", "8"]],
            ),
            (
                "PROJCOST",
                ["cost_item_id", "task_id", "act_cost", "remain_cost", "target_cost"],
                [
                    ["10", "", "5", "5", "5"],  # no task_id -> skipped (line 637)
                    ["11", "1", "", "", "500"],  # target only -> no remaining flagged (639->641)
                ],
            ),
        ]
    )
    one = parse_xer_text(text).tasks_by_id[1]
    assert one.budgeted_cost == 500.0
    assert one.cost is None  # no actual, no remaining -> the at-completion total stays absent
    assert one.actual_cost is None


# --- mpp_mpxj: Java/JRE discovery helpers (no real .mpp / JVM) ----------------------------


def _blind_discovery(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SF_JAVA", raising=False)
    monkeypatch.delenv("JAVA_HOME", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(mpp_mpxj.shutil, "which", lambda _name: None)
    monkeypatch.setattr(mpp_mpxj, "_WINDOWS_JAVA_ROOTS", ())
    monkeypatch.setattr(mpp_mpxj, "_POSIX_JAVA_GLOBS", ())
    monkeypatch.setattr(mpp_mpxj, "_portable_jre_dir", lambda: tmp_path / "no-jre-here")


def test_portable_jre_dir_points_at_repo_tools_jre() -> None:
    # the un-monkeypatched helper resolves to <repo>/tools/jre (line 65).
    portable = mpp_mpxj._portable_jre_dir()
    assert portable.name == "jre"
    assert portable.parent.name == "tools"


def test_find_java_returns_path_executable_when_on_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # with SF_JAVA / JAVA_HOME unset, a java on PATH is returned directly (line 88).
    _blind_discovery(monkeypatch, tmp_path)
    monkeypatch.setattr(
        mpp_mpxj.shutil, "which", lambda name: "/usr/bin/java" if name == "java" else None
    )
    assert mpp_mpxj._find_java() == "/usr/bin/java"


def test_find_java_with_java_home_lacking_a_bin_java_falls_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # JAVA_HOME set but neither bin/java nor bin/java.exe exists -> the loop exhausts without
    # returning (branch 82->86) and discovery continues to PATH, finding nothing here.
    _blind_discovery(monkeypatch, tmp_path)
    empty_home = tmp_path / "empty-jdk"
    (empty_home / "bin").mkdir(parents=True)  # bin exists but holds no java executable
    monkeypatch.setenv("JAVA_HOME", str(empty_home))
    assert mpp_mpxj._find_java() is None  # JAVA_HOME bin had no java -> nothing else found


def test_find_java_skips_non_directory_windows_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # a configured Windows root that is not a directory is skipped (branch 111->110); a real
    # root holding a versioned java.exe is then scanned and returned.
    _blind_discovery(monkeypatch, tmp_path)
    missing_root = tmp_path / "does-not-exist"
    real_root = tmp_path / "Adoptium"
    exe = real_root / "jdk-21.0.4+7" / "bin" / "java.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    monkeypatch.setattr(mpp_mpxj, "_WINDOWS_JAVA_ROOTS", (missing_root, real_root))
    found = mpp_mpxj._find_java()
    assert found is not None and "jdk-21.0.4+7" in found


def test_find_java_scans_posix_globs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # the POSIX glob scan (line 114) finds a JVM under a /usr/lib/jvm-style layout. The scan
    # roots at Path("/"); we point an absolute glob at the temp tree so the real filesystem is
    # never touched and the temp java executable is the discovered candidate.
    _blind_discovery(monkeypatch, tmp_path)
    java = tmp_path / "usr" / "lib" / "jvm" / "temurin-21" / "bin" / "java"
    java.parent.mkdir(parents=True)
    java.write_text("")
    # an absolute pattern makes Path("/").glob(pattern) walk our temp tree, not the host's /usr.
    jvm_dir = java.parent.parent.parent  # .../jvm  (temurin-21/bin/java -> jvm)
    abs_pattern = str(jvm_dir / "*" / "bin" / "java").lstrip("/")
    monkeypatch.setattr(mpp_mpxj, "_POSIX_JAVA_GLOBS", (abs_pattern,))
    found = mpp_mpxj._find_java()
    assert found == str(java)
