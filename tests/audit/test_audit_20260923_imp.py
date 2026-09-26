"""Executable reproducers for the AUDIT-2026-09-23 findings in the IMP lane (A0923-IMP-001..005).

Campaign: AUDIT-2026-09-23, a read-only audit of base 8c71c639 (v1.0.289). AUDIT + PLAN ONLY:
the audit changed nothing under ``src/``; these tests are the evidence a fixing PR inherits.

Every test asserts the CORRECT behaviour and is marked ``xfail(strict=True, raises=...)`` with the
exception observed red-first on the audited tree, so the suite stays green while the defect exists:

  * XFAIL  -- the defect is still present (the expected state until it is fixed).
  * XPASS  -- the defect is gone. Under ``strict=True`` an XPASS FAILS the run and names the test:
    that is the signal. The fixing PR removes that test's marker in the same commit, and the test
    stays behind as the permanent regression pin.
  * FAILED with an exception other than the marker's ``raises`` -- a precondition moved (every
    precondition is a ``pytest.fail``, never an ``assert``, so a broken setup can never pass for
    the expected xfail) or the defect changed shape. Investigate; do not re-mark.

Every input is built inline — MSPDI and XER text, and .xlsx packages written with ``zipfile`` — so
no fixture file is added and nothing is CUI. No Java: the .mpp path is never exercised. An autouse
fixture refuses every non-loopback connect and name lookup. Drop-in path: ``tests/audit/``.
Run: ``pytest tests/audit/test_audit_20260923_imp.py -rxX``.
"""

from __future__ import annotations

import datetime as dt
import io
import logging
import re
import socket
import zipfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.cpm import (
    CPMError,
    compute_cpm,
    offset_to_datetime,
    offset_to_start_datetime,
    working_minutes_between,
)
from schedule_forensics.importers._common import ImporterError
from schedule_forensics.importers.mspdi import parse_mspdi, parse_mspdi_text
from schedule_forensics.importers.xer import parse_xer_text
from schedule_forensics.model import ConstraintType
from schedule_forensics.web.app import SessionState, create_app

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})


@pytest.fixture(autouse=True)
def _air_gapped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-test state dirs, and no way off the machine: a non-loopback connect or any name lookup
    other than a loopback literal raises before a packet is sent."""
    for var in ("SF_SETTINGS_DIR", "SF_AI_LOG_DIR", "SF_CACHE_DIR"):
        monkeypatch.setenv(var, str(tmp_path / var))
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect

    def getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
        name = host.decode() if isinstance(host, bytes) else host
        if name is not None and str(name) not in _LOOPBACK:
            raise OSError(f"air-gapped test: name lookup of {name!r} refused")
        return real_getaddrinfo(host, *args, **kwargs)

    def connect(self: socket.socket, address: Any) -> None:
        if isinstance(address, tuple) and str(address[0]) not in _LOOPBACK:
            raise OSError(f"air-gapped test: connect to {address!r} refused")
        real_connect(self, address)

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", connect)


_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _col(index: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA."""
    out, index = "", index + 1
    while index:
        index, rem = divmod(index - 1, 26)
        out = chr(65 + rem) + out
    return out


def _xlsx(sheet_name: str, rows_xml: str) -> bytes:
    """A minimal one-sheet .xlsx package (inline strings) around ``rows_xml``."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/></Types>',
        )
        z.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{_NS}" xmlns:r="{_REL}"><sheets>'
            f'<sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{_REL}/worksheet" Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="{_NS}"><sheetData>{rows_xml}</sheetData></worksheet>',
        )
    return buf.getvalue()


# --------------------------------------------------------------------------------------------
# A0923-IMP-001 (T2): a mixed-r workbook silently empties the SRA risk register
# --------------------------------------------------------------------------------------------
_RR_HEADERS = (
    "Risk ID",
    "Risk name",
    "Probability %",
    "Impact (working days)",
    "Consequence (1-5)",
    "Affected UIDs (; separated)",
)
_RR_ROWS = (
    _RR_HEADERS,
    ("R1", "Vendor slip", "40", "12", "4", "1"),
    ("R2", "Weather", "25", "6", "2", "2"),
)
_TWO_TASK_MSPDI = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Project xmlns="http://schemas.microsoft.com/project"><Name>rr</Name>
<StartDate>2026-03-02T08:00:00</StartDate>
<Tasks>
 <Task><UID>1</UID><ID>1</ID><Name>Design</Name><Duration>PT40H0M0S</Duration></Task>
 <Task><UID>2</UID><ID>2</ID><Name>Build</Name><Duration>PT80H0M0S</Duration>
  <PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink></Task>
</Tasks></Project>"""


def _register(rows: tuple[tuple[str, ...], ...], shape: str) -> bytes:
    """A 'Risk Register' sheet written in one of three legal ``r=`` encodings:
    ``all`` (every cell carries r=, what Excel writes); ``first-from-B`` (the table starts at
    column B, each row's FIRST cell carries r= and the rest omit it — the Acumen Fuse writer's
    shape); ``header-only`` (the header row carries r= on every cell, data rows on none)."""
    xml = []
    for ri, row in enumerate(rows, start=1):
        cells = []
        for ci, value in enumerate(row):
            if shape == "all":
                ref = f' r="{_col(ci)}{ri}"'
            elif shape == "first-from-B":
                ref = f' r="{_col(ci + 1)}{ri}"' if ci == 0 else ""
            else:  # header-only
                ref = f' r="{_col(ci)}{ri}"' if ri == 1 else ""
            cells.append(f'<c{ref} t="inlineStr"><is><t>{value}</t></is></c>')
        xml.append("<row>" + "".join(cells) + "</row>")
    return _xlsx("Risk Register", "".join(xml))


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-IMP-001: read_xlsx puts every r-less cell in column A, so a legal mixed-r risk "
    "register (first-cell-only r=, the Acumen Fuse shape; or header r= / data r-less) replaces the "
    "session register with an EMPTY one under a non-error 'Imported 0 risk(s)' banner",
)
def test_a0923_imp_001_a_mixed_r_risk_register_imports_whole() -> None:
    """Claim: at 8c71c639 a complete two-risk register whose rows start at column B with r= on
    each row's first <c> only (and, likewise, one whose header carries r= and data rows none)
    posted to POST /sra/import/risk-register empties the session register, switches the register
    off and reports 'Imported 0 risk(s); skipped N incomplete row(s) ...' with
    sra_import_is_error False; an all-r-less workbook is refused loudly (not asserted).

    Authority: [MS-OI29500] Part 1 Section 18.3.1.4, c (Cell),
    https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oi29500/2fd4e47f-0965-4c60-95bd-cff980b6c325
    (retrieved 2026-09-23): "If this attribute is not specified, the cell shall be located in the
    column with the index that is 1 greater than that of the previous cell in the parent row
    collection." and src/schedule_forensics/web/app.py:7385-7386 "A bad workbook (or no schedule
    loaded) is reported, never silently lost."

    Tier: T2 (not LAW-1; T1 exposure if the SRA is run without the silently dropped register).
    ADR-0526:57 left read_xlsx's column-A handling unchanged for the SRA path without measuring
    this consequence.
    """
    state = SessionState()
    client = TestClient(create_app(state))
    upload = client.post("/upload", files={"files": ("rr.xml", _TWO_TASK_MSPDI, "text/xml")})
    if upload.status_code != 200 or len(state.schedules) != 1:
        pytest.fail("precondition: the two-task MSPDI loads")

    def post(blob: bytes) -> None:
        client.post(
            "/sra/import/risk-register",
            files={"file": ("register.xlsx", blob, _XLSX)},
            follow_redirects=False,
        )

    expected = ["Vendor slip", "Weather"]
    post(_register(_RR_ROWS, "all"))
    if [r.name for r in state.sra_risks] != expected:
        pytest.fail(f"precondition: the all-r= register imports: {state.sra_import_msg!r}")
    problems: list[str] = []
    for shape in ("first-from-B", "header-only"):
        post(_register((_RR_HEADERS, ("R0", "Old risk", "10", "2", "1", "1")), "all"))
        if [r.name for r in state.sra_risks] != ["Old risk"]:
            pytest.fail("precondition: the prior one-risk register is in place")
        post(_register(_RR_ROWS, shape))
        got = [r.name for r in state.sra_risks]
        if got != expected or state.sra_import_is_error or not state.sra_use_risk_register:
            problems.append(
                f"{shape}: register {got}, use_register={state.sra_use_risk_register}, "
                f"is_error={state.sra_import_is_error}, banner {state.sra_import_msg!r}"
            )
    assert problems == [], "\n".join(problems)


# --------------------------------------------------------------------------------------------
# A0923-IMP-002 (T1): a single-block MSPDI working day is measured from midnight
# --------------------------------------------------------------------------------------------
_WORKING_TIME = (
    "<WorkingTimes><WorkingTime><FromTime>07:00:00</FromTime><ToTime>15:00:00</ToTime>"
    "</WorkingTime></WorkingTimes>"
)
_WEEK = "".join(
    f"<WeekDay><DayType>{d}</DayType><DayWorking>{1 if 2 <= d <= 6 else 0}</DayWorking>"
    + (_WORKING_TIME if 2 <= d <= 6 else "")
    + "</WeekDay>"
    for d in range(1, 8)
)
_SINGLE_BLOCK_MSPDI = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Project xmlns="http://schemas.microsoft.com/project"><Name>h2</Name>
<StartDate>2026-03-02T07:00:00</StartDate><CalendarUID>1</CalendarUID>
<Calendars><Calendar><UID>1</UID><Name>Day shift</Name><IsBaseCalendar>1</IsBaseCalendar>
 <BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{_WEEK}</WeekDays></Calendar></Calendars>
<Tasks>
 <Task><UID>1</UID><ID>1</ID><Name>Pour</Name><Duration>PT8H0M0S</Duration></Task>
 <Task><UID>2</UID><ID>2</ID><Name>Cure</Name><Duration>PT8H0M0S</Duration>
  <PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink></Task>
</Tasks>
<Resources><Resource><UID>1</UID><ID>1</ID><Name>Concrete</Name><Type>0</Type></Resource></Resources>
<Assignments><Assignment><UID>1</UID><TaskUID>1</TaskUID><ResourceUID>1</ResourceUID>
 <Start>2026-03-02T07:00:00</Start><Finish>2026-03-03T11:00:00</Finish></Assignment></Assignments>
</Project>"""


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-IMP-002: a single-block 07:00-15:00 MSPDI day imports with day_segments=(), the "
    "recorded-window ruler anchors it at midnight (540/0/60/480 working minutes for windows worth "
    "720/120/480/240), and the material-booked task finishes Tue 08:00 instead of Tue 11:00",
)
def test_a0923_imp_002_a_single_block_day_is_measured_where_the_file_puts_it() -> None:
    """Claim: at 8c71c639 an MSPDI whose working day is ONE block 07:00-15:00 (Mon-Fri) imports
    with day_segments=(), after which working_minutes_between reads Mon 07:00->Tue 11:00 as 540,
    Mon 09:00->11:00 as 0, Mon 07:00->15:00 as 60 and Mon 13:00->Tue 09:00 as 480 (the declared
    working time gives 720 / 120 / 480 / 240 — hand arithmetic, MPXJ 16.2.0 and the engine's own
    two-touching-blocks rewrite agree), and compute_cpm finishes the task whose MATERIAL booking
    records Mon 07:00->Tue 11:00 at Tue 08:00 instead of Tue 11:00.

    Authority: Microsoft Project XML schema, 'WorkingTimes Element (Calendar)',
    https://learn.microsoft.com/en-us/office-project/xml-data-interchange/workingtimes-element-calendar?view=project-client-2016
    (retrieved 2026-09-23): "The collection of working times that defines the time for work on a
    working day or a calendar exception." and src/schedule_forensics/engine/cpm.py:1654
    "Working minutes of ``cal`` inside the recorded window ``[start, finish]``". The deferral this
    falsifies (its premise), docs/adr/0497-the-driving-path-series-reports-the-focuss-own-stored-
    finish-and-discloses-the-logic-only-finish-where-they-disagree.md:150-151: "Every MSPDI calendar
    carries segments, so no shipped number is known to be affected".

    Tier: T1 (not LAW-1; data-gated: 0 committed files carry a single non-24h block).
    """
    sch = parse_mspdi_text(_SINGLE_BLOCK_MSPDI, source_file="h2.xml")
    cal = sch.calendar
    if cal.working_minutes_per_day != 480 or cal.work_weekdays != (0, 1, 2, 3, 4):
        pytest.fail(f"precondition: the calendar imports as 480 min, Mon-Fri: {cal!r}")
    mon, tue = dt.date(2026, 3, 2), dt.date(2026, 3, 3)

    def at(day: dt.date, hour: int) -> dt.datetime:
        return dt.datetime.combine(day, dt.time(hour))

    windows = {
        "Mon 07:00 -> Tue 11:00": (at(mon, 7), at(tue, 11), 720),
        "Mon 09:00 -> Mon 11:00": (at(mon, 9), at(mon, 11), 120),
        "Mon 07:00 -> Mon 15:00": (at(mon, 7), at(mon, 15), 480),
        "Mon 13:00 -> Tue 09:00": (at(mon, 13), at(tue, 9), 240),
    }
    problems = [
        f"working_minutes_between {label} = {got}, declared working time gives {want}"
        for label, (start, finish, want) in windows.items()
        if (got := working_minutes_between(cal, start, finish)) != want
    ]
    finish = compute_cpm(sch).timings[1].early_finish_wall
    if finish != at(tue, 11):
        problems.append(
            f"material-booked task finishes {finish}, the recorded window ends Tue 11:00"
        )
    assert problems == [], "\n".join(problems)


# --------------------------------------------------------------------------------------------
# A0923-IMP-003 (T1): XER TASK.clndr_id is ignored
# --------------------------------------------------------------------------------------------
def _clndr_data(working_days: set[int]) -> str:
    """P6 packed clndr_data; day numbers 1=Sun .. 7=Sat; one span 08:00-16:00 per working day."""
    days = "".join(
        f"(0||{n}()(" + ("(0||0(s|08:00|f|16:00)())" if n in working_days else "") + "))"
        for n in range(1, 8)
    )
    return f"(0||CalendarData()((0||DaysOfWeek()({days}))(0||Exceptions()())))"


_XER = "\r\n".join(
    [
        "ERMHDR\t19.12\t2026-03-01\tProject\tadmin\tAdmin\tdb\tProject Management\tUSD",
        "%T\tPROJECT",
        "%F\tproj_id\tproj_short_name\tplan_start_date\tplan_end_date\tlast_recalc_date\tclndr_id",
        "%R\t10\tH4\t2026-03-06 08:00\t2026-03-09 16:00\t2026-03-06 08:00\t1",
        "%T\tCALENDAR",
        "%F\tclndr_id\tdefault_flag\tclndr_name\tproj_id\tbase_clndr_id\tclndr_type\tday_hr_cnt\t"
        "clndr_data",
        f"%R\t1\tY\t5-Day\t\t\tCA_Base\t8\t{_clndr_data({2, 3, 4, 5, 6})}",
        f"%R\t2\tN\t7-Day\t\t\tCA_Base\t8\t{_clndr_data({1, 2, 3, 4, 5, 6, 7})}",
        "%T\tPROJWBS",
        "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name",
        "%R\t50\t10\t\tH4\tH4 project",
        "%T\tTASK",
        "%F\ttask_id\tproj_id\twbs_id\tclndr_id\ttask_code\ttask_name\ttask_type\t"
        "complete_pct_type\tphys_complete_pct\ttarget_drtn_hr_cnt\tremain_drtn_hr_cnt\t"
        "early_start_date\tearly_end_date",
        "%R\t1001\t10\t50\t2\tA1000\tPour (7-day crew)\tTT_Task\tCP_Drtn\t0\t24\t24\t"
        "2026-03-06 08:00\t2026-03-08 16:00",
        "%R\t1002\t10\t50\t1\tA1010\tInspect\tTT_Task\tCP_Drtn\t0\t8\t8\t"
        "2026-03-09 08:00\t2026-03-09 16:00",
        "%T\tTASKPRED",
        "%F\ttask_pred_id\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt",
        "%R\t9001\t1002\t1001\tPR_FS\t0",
        "%E",
        "",
    ]
)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-IMP-003: the XER importer never reads TASK.clndr_id (no import note), so an "
    "activity on a 7-day P6 calendar is scheduled on the 5-day project calendar: A1000 finishes "
    "Tue 03-10 and A1010 Wed 03-11 instead of the file's own Sun 03-08 / Mon 03-09",
)
def test_a0923_imp_003_an_xer_activity_runs_on_its_own_p6_calendar() -> None:
    """Claim: at 8c71c639 a P6 XER whose activity A1000 carries TASK.clndr_id=2 (7-day,
    08:00-16:00) while PROJECT.clndr_id=1 is 5-day imports with calendar_uid=None,
    Schedule.calendars=() and no import note, and compute_cpm finishes A1000 Tue 2026-03-10 16:00
    and its successor Wed 2026-03-11 16:00, where the file's own early_end_date (= MPXJ = the
    engine's MSPDI twin) is Sun 2026-03-08 16:00 / Mon 2026-03-09 16:00.

    Authority: Oracle Primavera P6 EPPM Help, 'General Columns of the Activity Table',
    https://docs.oracle.com/cd/F74773_01/p6help/en/47225.htm (retrieved 2026-09-23): "Task
    Dependent : Activities are scheduled using the activity's calendar rather than the calendars of
    the assigned resources." The deferral whose premise ADR-0322 falsified,
    src/schedule_forensics/importers/xer.py:29-30: "Deferred (ADR-0008): per-task calendars (the
    engine models one schedule-level calendar)."

    Tier: T1 (not LAW-1; data-gated: the only committed XER has no CALENDAR table) with a T2
    disclosure ('/analysis' states every date rides the project calendar).
    """
    sch = parse_xer_text(_XER, source_file="h4.xer")
    by_name = {t.name: t for t in sch.tasks}
    if set(by_name) != {"Pour (7-day crew)", "Inspect"} or sch.calendar.name != "5-Day":
        pytest.fail(f"precondition: unexpected import {sorted(by_name)} / {sch.calendar.name!r}")
    cpm = compute_cpm(sch)
    problems = []
    for name, want in (
        ("Pour (7-day crew)", dt.datetime(2026, 3, 8, 16, 0)),
        ("Inspect", dt.datetime(2026, 3, 9, 16, 0)),
    ):
        timing = cpm.timings[by_name[name].unique_id]
        finish = timing.early_finish_wall or offset_to_datetime(
            sch.project_start, timing.early_finish, sch.calendar
        )
        if finish != want:
            problems.append(f"{name} finishes {finish}; P6 (the file's early_end_date) {want}")
    assert problems == [], "\n".join(problems) + f"\nimport_notes={sch.import_notes}"


# --------------------------------------------------------------------------------------------
# A0923-IMP-004 (T2): a windows-1252 MSPDI is decoded as UTF-8 with errors='replace'
# --------------------------------------------------------------------------------------------
_NAME = "Café façade \u2013 Müller\u2019s pour"
_CP1252_MSPDI = f"""<?xml version="1.0" encoding="windows-1252" standalone="yes"?>
<Project xmlns="http://schemas.microsoft.com/project"><Name>h5</Name>
<StartDate>2026-03-02T08:00:00</StartDate>
<Tasks><Task><UID>1</UID><ID>1</ID><Name>{_NAME}</Name><Duration>PT8H0M0S</Duration></Task></Tasks>
</Project>""".encode("cp1252")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-IMP-004: parse_mspdi and POST /upload decode an MSPDI declared and encoded as "
    "windows-1252 as UTF-8 with errors='replace', so task names load with U+FFFD and no import "
    "note ('loaded 1 schedule(s); 0 rejected')",
)
def test_a0923_imp_004_a_windows_1252_mspdi_keeps_its_names_or_is_refused(
    tmp_path: Path,
) -> None:
    """Claim: at 8c71c639 an MSPDI whose XML declaration reads encoding="windows-1252" and whose
    bytes are in that encoding loads through parse_mspdi (importers/mspdi.py:135) and POST /upload
    (web/app.py:8166) with 'Café façade \u2013 Müller\u2019s pour' mangled to five U+FFFD, no
    import note and an upload that reports 1 loaded, 0 rejected. (UTF-16 is refused loudly — not
    asserted.)

    Authority: W3C XML 1.0 (Fifth Edition) §4.3.3, https://www.w3.org/TR/xml/ (retrieved
    2026-09-23): "It is a fatal error when an XML processor encounters an entity with an encoding
    that it is unable to process." — a reader decodes the declared encoding or refuses the file;
    it never substitutes in silence. README.md:69-70 "the dashboard tells you exactly what loaded
    and what failed (no silent failures)."

    Tier: T2 (not LAW-1; T3 component: the load summary says nothing was lost). Correct = the
    exact name, or a loud refusal, on BOTH entry points.
    """
    path = tmp_path / "h5.xml"
    path.write_bytes(_CP1252_MSPDI)
    problems = []
    try:
        name = parse_mspdi(path).tasks[0].name
    except ImporterError:
        name = None  # a named refusal is also correct
    if name is not None and name != _NAME:
        problems.append(f"parse_mspdi loaded {name!r}")
    state = SessionState()
    client = TestClient(create_app(state))
    # no redirect-follow: the dashboard GET would consume the one-shot flash that names a refusal
    client.post(
        "/upload", files={"files": ("h5.xml", _CP1252_MSPDI, "text/xml")}, follow_redirects=False
    )
    loaded = [s.tasks[0].name for s in state.schedules.values()]
    refused = state.flash is not None and any("h5.xml" in e for e in state.flash.errors)
    if loaded and loaded != [_NAME]:
        problems.append(f"POST /upload loaded {loaded}")
    elif not loaded and not refused:
        pytest.fail("precondition: the upload either loads the file or reports its refusal")
    assert problems == [], "\n".join(problems)


# --------------------------------------------------------------------------------------------
# A0923-IMP-005 (T4): an isdigit()-gated int() 500s both One-Pager upload routes
# --------------------------------------------------------------------------------------------
def _onepager_workbook(row_number: str) -> bytes:
    """A header row plus one One-Pager data row whose ``<row r=...>`` is ``row_number``."""
    header = "".join(
        f'<c r="{c}1" t="inlineStr"><is><t>{v}</t></is></c>'
        for c, v in zip("ABC", ("Swimlane", "Item", "Date"), strict=True)
    )
    data = "".join(
        f'<c t="inlineStr"><is><t>{v}</t></is></c>' for v in ("Design", "PDR", "05/15/2026")
    )
    return _xlsx("One Pager", f'<row r="1">{header}</row><row r="{row_number}">{data}</row>')


@pytest.mark.xfail(
    strict=True,
    raises=ValueError,
    reason="A0923-IMP-005: xlsx_read._row_number gates int() with str.isdigit(); a row "
    "numbered '\u00b2' or '\u2460' raises a bare ValueError the One-Pager routes (which catch "
    "XlsxError) do not handle -> HTTP 500 with no message",
)
def test_a0923_imp_005_a_superscript_row_number_is_refused_by_name() -> None:
    """Claim: at 8c71c639 an .xlsx whose worksheet row carries r="²" (or r="①") uploaded to
    POST /onepager/upload or POST /onepager-compare/upload answers HTTP 500, because
    reports/xlsx_read.py:229 gates int() with str.isdigit() and the bare ValueError is not the
    XlsxError the routes catch; r="x" is refused by name (303).

    Authority: docs/adr/0423-isdigit-gated-int-500d-twelve-routes-and-isdecimal-is-the-exact-
    predicate.md:10-13
    "`str.isdigit()` is **True** for superscripts (`²`), circled forms (`①`) and many other Unicode
    numeric characters that `int()` rejects with `ValueError`. An `isdigit()`-gated conversion is
    therefore not a guard at all: it admits the value and then raises." and
    src/schedule_forensics/reports/xlsx_read.py:119-120 "Raises :class:`XlsxError` as
    :func:`read_xlsx` does, and also for a row or cell reference that cannot be read".

    Tier: T4 (not LAW-1). The ADR-0423 route fuzz posts form fields only, so it cannot reach a
    file-borne value (T5 note).
    """
    client = TestClient(create_app(SessionState()))
    problems = []
    for route in ("/onepager/upload", "/onepager-compare/upload"):
        named = client.post(
            route,
            files={"file": ("list.xlsx", _onepager_workbook("x"), _XLSX)},
            follow_redirects=False,
        )
        if named.status_code != 303:
            pytest.fail(f"precondition: {route} refuses r='x' by name ({named.status_code})")
        for row in ("\u00b2", "\u2460"):
            resp = client.post(
                route,
                files={"file": ("list.xlsx", _onepager_workbook(row), _XLSX)},
                follow_redirects=False,
            )
            if resp.status_code != 303:
                problems.append(f"{route} r={row!r} -> {resp.status_code}")
    assert problems == [], "\n".join(problems)


# --- A0923-IMP-006 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_imp.py, and on nothing else:
#   imports    datetime as dt, pytest,
#              compute_cpm, offset_to_datetime (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi)
#   fixture    the module-level autouse _air_gapped
# Inputs: inline MSPDI text only. No fixture file, no Java, no network.

#: Mon-Fri 08:00-12:00 / 13:00-17:00 (MS Project's Standard calendar); Sat/Sun non-working.
_A0923_IMP_006_DAY = (
    "<WorkingTimes><WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime>"
    "</WorkingTime><WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime>"
    "</WorkingTime></WorkingTimes>"
)
_A0923_IMP_006_WEEK = "".join(
    f"<WeekDay><DayType>{d}</DayType><DayWorking>{1 if 2 <= d <= 6 else 0}</DayWorking>"
    + (_A0923_IMP_006_DAY if 2 <= d <= 6 else "")
    + "</WeekDay>"
    for d in range(1, 8)
)


def _a0923_imp_006_mspdi(link_lag: int, lag_format: int) -> str:
    """Z (5 d) -FS0-> A (5 d) -FS+lag-> B (2 d), start Mon 2026-06-01 08:00, the A -> B lag
    written exactly as MS Project / MPXJ write it: ``<LinkLag>`` in tenths of a minute and
    ``<LagFormat>`` naming the unit."""

    def task(uid: int, name: str, hours: int, pred: int | None, lag: int, fmt: int) -> str:
        link = (
            ""
            if pred is None
            else f"<PredecessorLink><PredecessorUID>{pred}</PredecessorUID><Type>1</Type>"
            f"<LinkLag>{lag}</LinkLag><LagFormat>{fmt}</LagFormat></PredecessorLink>"
        )
        return (
            f"<Task><UID>{uid}</UID><ID>{uid}</ID><Name>{name}</Name>"
            f"<Duration>PT{hours}H0M0S</Duration><DurationFormat>7</DurationFormat>{link}</Task>"
        )

    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Project xmlns="http://schemas.microsoft.com/project"><Name>imp006</Name>
<ScheduleFromStart>1</ScheduleFromStart><StartDate>2026-06-01T08:00:00</StartDate>
<CalendarUID>1</CalendarUID><MinutesPerDay>480</MinutesPerDay><MinutesPerWeek>2400</MinutesPerWeek>
<Calendars><Calendar><UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>
 <BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{_A0923_IMP_006_WEEK}</WeekDays></Calendar>
</Calendars>
<Tasks>{task(1, "Z", 40, None, 0, 7)}{task(2, "A", 40, 1, 0, 7)}
{task(3, "B", 16, 2, link_lag, lag_format)}</Tasks></Project>"""


def _a0923_imp_006_finishes(link_lag: int, lag_format: int) -> tuple[dt.datetime, dt.datetime]:
    """(A's finish, B's finish) as the product renders a project-calendar task."""
    sch = parse_mspdi_text(_a0923_imp_006_mspdi(link_lag, lag_format), source_file="imp006.xml")
    if sorted(t.unique_id for t in sch.tasks) != [1, 2, 3] or len(sch.relationships) != 2:
        pytest.fail(f"precondition: the three-task, two-link probe imports whole: {sch.tasks!r}")
    cpm = compute_cpm(sch)

    def finish(uid: int) -> dt.datetime:
        timing = cpm.timings[uid]
        return timing.early_finish_wall or offset_to_datetime(
            sch.project_start, timing.early_finish, sch.calendar
        )

    return finish(2), finish(3)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-IMP-006: the MSPDI importer ignores LagFormat, so an ELAPSED link lag (ed / eh / "
    "ew) is scheduled as the same number of WORKING minutes: FS+2ed (LinkLag 28800, LagFormat 8) "
    "finishes B Wed 06-24 17:00 exactly as FS+6d does, where 48 clock hours after Fri 17:00 put B "
    "at Tue 06-16 17:00; 12eh and 12h import to the identical Relationship",
)
def test_a0923_imp_006_an_elapsed_link_lag_counts_non_working_time() -> None:
    """A0923-IMP-006 · IMP · T1 (latent)

    Claim: at 19173728 a hand-built MSPDI (Standard 08-12/13-17 Mon-Fri calendar, start Mon
    2026-06-01 08:00; Z 5d -FS0-> A 5d -FS+lag-> B 2d) through parse_mspdi_text + compute_cpm
    finishes B at Wed 2026-06-24 17:00 for FS+2ed
    (<LinkLag>28800</LinkLag><LagFormat>8</LagFormat>): the model holds lag_minutes=2880
    WORKING minutes (6 working days), byte-identical to FS+6d (28800 / LagFormat 7). FS+12eh
    (7200 / 6) and FS+12h (7200 / 5) import to the identical Relationship (it has no elapsed
    field) and both finish B Thu 06-18 12:00; FS+1ew (100800 / 10) finishes B Wed 07-15 17:00.
    A finishes Fri 2026-06-12 17:00 in every variant.

    Correct (hand walk from Microsoft's definitions): 2ed = 48 clock hours -> Sun 06-14 17:00 ->
    the next working instant Mon 06-15 08:00 -> B (16 working h) finishes Tue 2026-06-16 17:00;
    12eh -> Sat 06-13 05:00 -> Mon 08:00 -> Tue 06-16 17:00; 1ew = 168 h -> Fri 06-19 17:00 ->
    Mon 06-22 08:00 -> Tue 06-23 17:00. The working-unit controls (6d -> Wed 06-24 17:00,
    12h -> Thu 06-18 12:00) are preconditions: the engine is right on them today and a fix must
    keep them.

    Authority: Microsoft Learn, 'DurationFormat Element' (the enumeration LagFormat uses),
    https://learn.microsoft.com/office-project/xml-data-interchange/durationformat-element?view=project-client-2016
    (retrieved 2026-09-25): "Elapsed time counts all time, including non-working time specified
    in the project, resource, or task calendar. For example, if the calendar specifies Saturday
    and Sunday as non-working days, a duration of 7d is seven working days such as Monday \u2013
    Friday and the following Monday and Tuesday. A duration of 7ed is seven elapsed days, such as
    Monday \u2013 Sunday." and its value table "6 | eh (elapsed hours)", "8 | ed (elapsed days)",
    "10 | ew (elapsed weeks)"; 'LinkLag Element',
    https://learn.microsoft.com/office-project/xml-data-interchange/linklag-element?view=project-client-2016
    (retrieved 2026-09-25): "The amount of lag in tenths of a minute." / "LinkLag requires a
    LagFormat to be specified." The repo premise this falsifies, src/schedule_forensics/importers/
    mspdi.py:115-116: "MSPDI ``LinkLag`` is stored in tenths of a minute for time-unit
    ``LagFormat``s, so ``LinkLag / 10`` is working minutes directly." -- an assumption
    docs/adr/0008-m3-mspdi-xer-importers.md:48-50 filed under "Source-pending" ("``LagFormat``
    governs display only ... unconfirmed against a real file") and never closed for the elapsed
    formats (ADR-0026 Decision 3 closed only the percent formats 19/20).

    Why the oracle is independent: Microsoft's published schema pages plus calendar arithmetic
    written out above; the engine supplies only the observed value. MPXJ 16.2.0's reader, its
    MSPDI writer (the product's own .mpp -> MSPDI path writes 2.0ed as 28800/8) and its
    MicrosoftScheduler agree with the hand walk on all three elapsed formats, and agree with the
    engine on the working-unit controls (verifier record A0923-IMP-006). MS Project's own stored
    dates for this probe are UNVERIFIED; the claim does not depend on them -- under ANY fixed
    reading of LinkLag, 12eh and 12h cannot both be right while they import identically.

    Tier: T1 (not LAW-1; latent: 0 elapsed LagFormats among 34,678 links in 72 MSPDI documents).
    """
    a_finish = dt.datetime(2026, 6, 12, 17, 0)
    controls = {  # working units: the engine agrees with MPXJ's MicrosoftScheduler today
        "FS+6d (28800 / LagFormat 7)": (28800, 7, dt.datetime(2026, 6, 24, 17, 0)),
        "FS+12h (7200 / LagFormat 5)": (7200, 5, dt.datetime(2026, 6, 18, 12, 0)),
        "FS0 (0 / LagFormat 7)": (0, 7, dt.datetime(2026, 6, 16, 17, 0)),
    }
    for label, (lag, fmt, want) in controls.items():
        got_a, got_b = _a0923_imp_006_finishes(lag, fmt)
        if (got_a, got_b) != (a_finish, want):
            pytest.fail(f"precondition: {label} finishes A {got_a} / B {got_b}; want {want}")
    elapsed = {
        "FS+2ed (28800 / LagFormat 8)": (28800, 8, dt.datetime(2026, 6, 16, 17, 0)),
        "FS+12eh (7200 / LagFormat 6)": (7200, 6, dt.datetime(2026, 6, 16, 17, 0)),
        "FS+1ew (100800 / LagFormat 10)": (100800, 10, dt.datetime(2026, 6, 23, 17, 0)),
    }
    problems = []
    for label, (lag, fmt, want) in elapsed.items():
        got_a, got_b = _a0923_imp_006_finishes(lag, fmt)
        if got_a != a_finish:
            pytest.fail(f"precondition: {label} moved A's finish to {got_a}")
        if got_b != want:
            problems.append(
                f"{label}: B finishes {got_b:%a %Y-%m-%d %H:%M}; elapsed time gives "
                f"{want:%a %Y-%m-%d %H:%M}"
            )
    assert problems == [], "\n".join(problems)


# --- A0923-IMP-007 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_imp.py:
#   imports    datetime as dt, pytest,
#              compute_cpm, offset_to_datetime (schedule_forensics.engine.cpm),
#              ImporterError (schedule_forensics.importers._common),
#              parse_mspdi_text (schedule_forensics.importers.mspdi)
#   fixture    the module-level autouse _air_gapped; pytest's built-in caplog
# and on FIVE names the header does not carry today -- merge them into its import block:
#   import logging
#   import re
#   from schedule_forensics.engine.cpm import CPMError, offset_to_start_datetime
#   from schedule_forensics.model import ConstraintType
# Inputs: inline MSPDI text only. No fixture file, no Java, no network.

#: Mon-Fri 08:00-12:00 / 13:00-17:00 (MS Project's Standard calendar); Sat/Sun non-working.
_A0923_IMP_007_WEEK = "".join(
    f"<WeekDay><DayType>{d}</DayType><DayWorking>{1 if 2 <= d <= 6 else 0}</DayWorking>"
    + (
        "<WorkingTimes><WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime>"
        "</WorkingTime><WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime>"
        "</WorkingTime></WorkingTimes>"
        if 2 <= d <= 6
        else ""
    )
    + "</WeekDay>"
    for d in range(1, 8)
)
#: a disclosure names what was changed: ALAP, or a constraint collapsed to ASAP
_A0923_IMP_007_NAMES_ALAP = re.compile(r"\bALAP\b|as[\s-]+late[\s-]+as[\s-]+possible", re.I)
_A0923_IMP_007_NAMES_COLLAPSE = re.compile(r"constraint.*\b(ASAP|as[\s-]+soon)", re.I | re.S)


def _a0923_imp_007_mspdi(b_constraint_code: int, *, external_link: bool = False) -> str:
    """Z (5 d) -> A (5 d) -> C (1 d) and Z -> B (2 d) -> C, all FS0, start Mon 2026-06-01
    08:00; B carries ``<ConstraintType>`` ``b_constraint_code`` (1 = As Late As Possible).
    ``external_link`` adds a link from a UID outside the file on C (the capture control)."""

    def task(uid: int, name: str, hours: int, preds: tuple[int, ...], extra: str = "") -> str:
        links = "".join(
            f"<PredecessorLink><PredecessorUID>{p}</PredecessorUID><Type>1</Type>"
            "<LinkLag>0</LinkLag><LagFormat>7</LagFormat></PredecessorLink>"
            for p in preds
        )
        return (
            f"<Task><UID>{uid}</UID><ID>{uid}</ID><Name>{name}</Name>"
            f"<Duration>PT{hours}H0M0S</Duration><DurationFormat>7</DurationFormat>"
            f"{extra}{links}</Task>"
        )

    b_ct = f"<ConstraintType>{b_constraint_code}</ConstraintType>"
    c_preds = (2, 3, 999) if external_link else (2, 3)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Project xmlns="http://schemas.microsoft.com/project"><Name>imp007</Name>
<ScheduleFromStart>1</ScheduleFromStart><StartDate>2026-06-01T08:00:00</StartDate>
<CalendarUID>1</CalendarUID><MinutesPerDay>480</MinutesPerDay><MinutesPerWeek>2400</MinutesPerWeek>
<HonorConstraints>1</HonorConstraints>
<Calendars><Calendar><UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>
 <BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{_A0923_IMP_007_WEEK}</WeekDays></Calendar>
</Calendars>
<Tasks>{task(1, "Z", 40, ())}{task(2, "A", 40, (1,))}{task(3, "B", 16, (1,), b_ct)}
{task(4, "C", 8, c_preds)}</Tasks></Project>"""


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-IMP-007: the MSPDI importer rewrites an As-Late-As-Possible task to ASAP "
    "(mspdi.py:730-734) with no log record and no import note, so it is scheduled at its EARLY "
    "dates (Mon 06-08..Tue 06-09, TF 1440) where MS Project's ALAP puts it (Thu 06-11..Fri 06-12) "
    "-- the docstring's 'logged by count, never silently' contract is false",
)
def test_a0923_imp_007_an_alap_constraint_is_honored_or_its_collapse_is_disclosed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A0923-IMP-007 · IMP · T1 (latent; T2/T3 if the value change is ruled HELD by ADR-0026 D2)

    Claim (verifier's narrowed claim): at 19173728 an MSPDI ALAP task (ConstraintType 1) is
    rewritten to ASAP by src/schedule_forensics/importers/mspdi.py:730-734 and scheduled at its
    EARLY dates (B Mon 2026-06-08 08:00..Tue 06-09 17:00, TF 1440, FF 1440) with no log record,
    no Schedule.import_notes entry and no mention on /analysis or /api/analysis -- falsifying the
    importer's own disclosure contract, while Microsoft's ALAP definition places B at Thu 06-11
    08:00..Fri 06-12 17:00. The ALAP -> ASAP normalization itself is a documented deliberate
    decision (ADR-0026 Decision 2; pinned by tests/importers/test_mspdi.py::
    test_alap_constraint_is_normalized_to_asap), so the finding stands on that decision's
    falsified premise (silent + value-changing), not on the choice to normalize.

    Correct = ONE of: (a) ALAP survives import and the engine honors it (B at Thu 06-11 08:00 ..
    Fri 06-12 17:00) or refuses it by name (CPMError, src/schedule_forensics/engine/cpm.py:143-146
    -- loud, the documented Law-2 outcome -- or an ImporterError at import); or (b) the collapse
    is disclosed -- a log record (INFO or above, from the package's loggers) or an import note
    that names it.

    Authority: src/schedule_forensics/importers/mspdi.py:19-25 "**ALAP** constraints (out of scope
    for the early-date CPM), and date-requiring constraints with the date cleared. These are
    *valid* schedule states, not corruption, so they are normalized on import (links dropped,
    those constraints collapsed to ASAP) and logged by count — never silently changing a
    parity-relevant value of a well-formed file." Microsoft Learn, 'Definition of Microsoft
    Project constraints',
    https://learn.microsoft.com/en-us/previous-versions/troubleshoot/microsoft-365/microsoft-365-apps/project/definition-of-project-constraints
    (retrieved 2026-09-25): "As Late As Possible: Schedules the task as late as it can without
    delaying subsequent tasks. Use no constraint date. ES=(Calculated)LS". Hand walk: C starts
    Mon 06-15 08:00 (A ends Fri 06-12 17:00), so B's latest finish is Fri 06-12 17:00 and its
    latest start Thu 06-11 08:00.

    Why the oracle is independent: the disclosure half needs no external oracle -- it is the
    repo's own written contract against an executed log / import-note capture (with a positive
    control proving the capture sees the importer's logger). The date half is Microsoft's
    published definition plus the backward walk written above; MPXJ 16.2.0's MicrosoftScheduler
    places B at 06-11..06-12 too (verifier record). MS Project's stored Total Slack for the ALAP
    task is UNVERIFIED and not asserted.

    Tier: T1 (not LAW-1; latent: ALAP = 0 of 28,188 tasks in 72 MSPDI documents and 0 CS_ALAP in
    the committed XER); T2 / T3 if the lead rules the value change HELD by ADR-0026 D2.
    """
    caplog.set_level(logging.DEBUG)
    parse_mspdi_text(_a0923_imp_007_mspdi(0, external_link=True), source_file="control.xml")
    if not any(
        r.name == "schedule_forensics.importers.mspdi" and r.levelno >= logging.INFO
        for r in caplog.records
    ):
        pytest.fail("precondition: the capture sees the importer's own INFO record (dropped link)")
    asap = parse_mspdi_text(_a0923_imp_007_mspdi(0), source_file="asap.xml")
    asap_cpm = compute_cpm(asap)
    c_finish = offset_to_datetime(
        asap.project_start, asap_cpm.timings[4].early_finish, asap.calendar
    )
    if c_finish != dt.datetime(2026, 6, 15, 17, 0):
        pytest.fail(f"precondition: the ASAP twin's C finishes Mon 06-15 17:00, not {c_finish}")
    caplog.clear()

    try:
        sch = parse_mspdi_text(_a0923_imp_007_mspdi(1), source_file="alap.xml")
    except ImporterError:
        return  # a refusal by name at import is loud -- never a silently moved value
    said = [
        text
        for text in (
            *(
                r.getMessage()
                for r in caplog.records
                if r.name.startswith("schedule_forensics") and r.levelno >= logging.INFO
            ),
            *sch.import_notes,
        )
        if _A0923_IMP_007_NAMES_ALAP.search(text) or _A0923_IMP_007_NAMES_COLLAPSE.search(text)
    ]
    b = sch.tasks_by_id[3]
    alap = (dt.datetime(2026, 6, 11, 8, 0), dt.datetime(2026, 6, 12, 17, 0))
    problems = []
    try:
        cpm = compute_cpm(sch)
    except CPMError:
        cpm = None  # a refusal by name is loud -- never a silently moved value
    if cpm is not None:
        t = cpm.timings[3]
        placed = (
            t.early_start_wall
            or offset_to_start_datetime(sch.project_start, t.early_start, sch.calendar),
            t.early_finish_wall
            or offset_to_datetime(sch.project_start, t.early_finish, sch.calendar),
        )
        if b.constraint_type is ConstraintType.ALAP and placed != alap:
            problems.append(
                f"ALAP kept but B placed {placed[0]:%a %m-%d %H:%M}..{placed[1]:%a %m-%d %H:%M}; "
                f"Microsoft's ALAP places it {alap[0]:%a %m-%d %H:%M}..{alap[1]:%a %m-%d %H:%M}"
            )
        elif b.constraint_type is not ConstraintType.ALAP and not said and placed != alap:
            problems.append(
                f"ALAP on UID 3 silently became {b.constraint_type}: B placed "
                f"{placed[0]:%a %m-%d %H:%M}..{placed[1]:%a %m-%d %H:%M} TF {t.total_float} "
                f"(ALAP: {alap[0]:%a %m-%d %H:%M}..{alap[1]:%a %m-%d %H:%M}); no log record or "
                f"import note names it (import_notes={sch.import_notes!r})"
            )
    assert problems == [], "\n".join(problems)
