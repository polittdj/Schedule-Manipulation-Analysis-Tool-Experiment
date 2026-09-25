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
import socket
import zipfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.cpm import compute_cpm, offset_to_datetime, working_minutes_between
from schedule_forensics.importers._common import ImporterError
from schedule_forensics.importers.mspdi import parse_mspdi, parse_mspdi_text
from schedule_forensics.importers.xer import parse_xer_text
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
