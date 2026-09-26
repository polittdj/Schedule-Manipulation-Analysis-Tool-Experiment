"""Executable reproducers for the AUDIT-2026-09-23 findings in the CPM lane (A0923-CPM-001..008).

Campaign: AUDIT-2026-09-23, session 5 (WP-CPM), base 19173728 (v1.0.294). AUDIT + PLAN ONLY: the
audit changed nothing under ``src/``; these tests are the evidence a fixing PR inherits.

Every test asserts the CORRECT behaviour and is marked ``xfail(strict=True, raises=...)`` with the
exception observed red-first on the audited tree, so the suite stays green while the defect exists:

  * XFAIL  -- the defect is still present (the expected state until it is fixed).
  * XPASS  -- the defect is gone. Under ``strict=True`` an XPASS FAILS the run and names the test:
    that is the signal. The fixing PR removes that test's marker in the same commit, and the test
    stays behind as the permanent regression pin.
  * FAILED with an exception other than the marker's ``raises`` -- a precondition moved (every
    precondition is a ``pytest.fail``, never an ``assert``, so a broken setup can never pass for
    the expected xfail) or the defect changed shape. Investigate; do not re-mark.

Inputs are already-committed goldens (non-CUI build references); MS Project's stored values are
read from the raw XML with ElementTree, independently of the importer under test. No fixture file
is added; an autouse fixture refuses every non-loopback connect and name lookup.
Drop-in path: ``tests/audit/``. Run: ``pytest tests/audit/test_audit_20260923_cpm.py -rxX``.
"""

from __future__ import annotations

import datetime as dt
import gzip
import re
import socket
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.cpm import compute_cpm, datetime_to_offset, offset_to_datetime
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.web.app import SessionState, create_app

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests" / "fixtures" / "golden"
NS = "{http://schemas.microsoft.com/project}"

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


def _stored_finish(raw: bytes) -> dt.datetime:
    """MS Project's own project FinishDate, read from the raw MSPDI -- not through the importer."""
    node = ET.fromstring(raw).find(NS + "FinishDate")
    if node is None or not node.text:
        pytest.fail("precondition: the golden carries no <FinishDate>")
    return dt.datetime.fromisoformat(node.text.strip())


def _visible(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-001: every page that prints the schedule-logic (CPM) project finish renders "
        "offset_to_datetime(project_finish) on the project axis and ignores "
        "CPMResult.project_finish_wall, so Hard_File_updated3 shows 12/11/2026 where MS Project "
        "stores 2026-12-12 17:00 and the engine's own wall reads 2026-12-12 17:00"
    ),
)
def test_a0923_cpm_001_the_displayed_cpm_finish_is_the_engines_true_finish() -> None:
    """A0923-CPM-001 · CPM · T1.

    Claim: at 19173728, ``tests/fixtures/golden/fuse_hardfile/Hard_File_updated3.mspdi.xml.gz``
    uploaded to the app shows its schedule-logic finish as 12/11/2026 on ``/path``, "Friday,
    December 11, 2026" on ``/briefing`` and "2026-12-11" on ``/brief``; MS Project's stored
    FinishDate is 2026-12-12T17:00 (Saturday: UID 146's crew works Saturdays) and the engine's
    own ``CPMResult.project_finish_wall`` is 2026-12-12 17:00.

    Authority: A1 -- MS Project's stored ``<FinishDate>`` (line 12 of the decompressed golden),
    which equals the latest stored task Finish (44 of 44 corpus files). A2 --
    ``engine/cpm.py:291-295``: ``project_finish_wall`` is "The true wall-clock instant of the
    network finish when an off-calendar task's finish is not exactly representable on the project
    axis ... ``None`` when every task follows the project calendar -- ``offset_to_datetime
    (project_finish)`` is then exact"; ``docs/PARITY-REPORT.md:253`` records this file's CPM
    finish as "exact". The engine is right; 22 presentation sites throw the right answer away.
    """
    raw = gzip.decompress(
        (GOLDEN / "fuse_hardfile" / "Hard_File_updated3.mspdi.xml.gz").read_bytes()
    )
    stored = _stored_finish(raw)
    sch = parse_mspdi_text(raw.decode("utf-8"))
    cpm = compute_cpm(sch)
    if cpm.project_finish_wall != stored:
        pytest.fail(
            f"precondition: the engine's wall {cpm.project_finish_wall} no longer reproduces MS "
            f"Project's stored finish {stored} -- the finding's premise moved"
        )
    axis = offset_to_datetime(sch.project_start, cpm.project_finish, sch.calendar)
    if axis.date() == stored.date():
        pytest.fail("precondition: the axis rendering now agrees with the stored date")

    client = TestClient(create_app(SessionState()))
    up = client.post("/upload", files={"files": ("Hard_File_updated3.mspdi.xml", raw, "text/xml")})
    if up.status_code != 200:
        pytest.fail(f"precondition: upload answered {up.status_code}")
    path = _visible(client.get("/path").text)
    briefing = _visible(client.get("/briefing").text)
    brief = _visible(client.get("/brief").text)
    shown = {
        "/path": ("12/12/2026" in path, "12/11/2026" in path),
        "/briefing": ("December 12, 2026" in briefing, "December 11, 2026" in briefing),
        "/brief": ("finish of 2026-12-12" in brief, "finish of 2026-12-11" in brief),
    }
    wrong = {route: v for route, v in shown.items() if not v[0] or v[1]}
    assert not wrong, (
        f"the CPM finish shown is not MS Project's / the engine's {stored:%Y-%m-%d %H:%M} "
        f"(route: (true date shown, axis date shown)) {wrong}"
    )


# --- A0923-CPM-002 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py, and on nothing else:
#   imports    datetime as dt, gzip, xml.etree.ElementTree as ET, pytest,
#              compute_cpm and offset_to_datetime (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Input: the committed, non-CUI golden tests/fixtures/golden/fuse_ltf/Large_Test_File.mspdi.xml.gz
# (read with gzip). No new fixture file.


def _a0923_cpm_002_task(root: ET.Element, uid: int) -> ET.Element:
    """The raw ``<Task>`` element with this UID -- read with ElementTree, not the importer."""
    for el in root.iter(NS + "Task"):
        if (el.findtext(NS + "UID") or "").strip() == str(uid):
            return el
    pytest.fail(f"precondition: the golden has no <Task> with UID {uid}")


def _a0923_cpm_002_split(root: ET.Element, uid: int) -> list[tuple[dt.datetime, dt.datetime]]:
    """The empty (no-Value / zero) Type-1 blocks lying BETWEEN two worked blocks of the task's
    bookings -- MS Project's recorded split -- read with ElementTree. Precondition: every
    booking of the task is the unassigned-work placeholder (ResourceUID < 0), so nobody works
    the gaps."""
    blocks: list[tuple[dt.datetime, dt.datetime, bool]] = []
    for a in root.iter(NS + "Assignment"):
        if (a.findtext(NS + "TaskUID") or "").strip() != str(uid):
            continue
        if int((a.findtext(NS + "ResourceUID") or "0").strip()) >= 0:
            pytest.fail(f"precondition: UID {uid} now carries a real resource booking")
        for tp in a.findall(NS + "TimephasedData"):
            if (tp.findtext(NS + "Type") or "").strip() != "1":
                continue
            value = (tp.findtext(NS + "Value") or "").strip()
            start = dt.datetime.fromisoformat((tp.findtext(NS + "Start") or "").strip())
            finish = dt.datetime.fromisoformat((tp.findtext(NS + "Finish") or "").strip())
            blocks.append((start, finish, value not in ("", "PT0H0M0S")))
    blocks.sort()
    worked = [i for i, block in enumerate(blocks) if block[2]]
    if len(worked) < 2:
        pytest.fail(f"precondition: UID {uid}'s placeholder booking records no split")
    return [(s, f) for i, (s, f, w) in enumerate(blocks) if not w and worked[0] < i < worked[-1]]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-002: the importer drops MS Project's unassigned-work placeholder booking "
        "(ResourceUID -65535) and with it the only record of an unresourced task's split, so "
        "Large_Test_File UID 7262 finishes 2025-04-03 17:00 with 313,680 min of total float "
        "where MS Project stores 2025-04-08 17:00 and 311,760"
    ),
)
def test_a0923_cpm_002_a_split_recorded_on_the_unassigned_placeholder_delays_the_task() -> None:
    """A0923-CPM-002 · CPM · T1.

    Claim: at 19173728, ``tests/fixtures/golden/fuse_ltf/Large_Test_File.mspdi.xml.gz`` UID 7262
    (unstarted, no resource) via ``compute_cpm(parse_mspdi_text(...))`` yields early finish
    2025-04-03 17:00 and total float 313,680 min; MS Project's stored values in the same file are
    Finish 2025-04-08 17:00 and TotalSlack 311,760 min (3,117,600 tenths). The task's only
    booking is MS Project's unassigned-work placeholder (ResourceUID -65535), whose time-phased
    work records three whole working days with no work (2025-02-25, 03-24, 03-31) inside the
    288 h. ``importers/mspdi.py:1224`` (``... or resource_uid < 0: continue``) discards that
    booking before its pieces are read, so ADR-0491's split leg is never formed and the task
    runs contiguously. The float is 4 working days high: 3 from 7262's own gaps on the forward
    side plus 1 from downstream UID 7265's placeholder gap (2025-04-14) on the backward side.

    Authority: A1 -- MS Project's own stored values, decompressed golden: Task UID 7262
    (line 271074) ``<Start>2025-02-12T08:00:00`` (271087), ``<Finish>2025-04-08T17:00:00``
    (271088), ``<Duration>PT288H0M0S`` (271089), ``<TotalSlack>3117600`` (271106),
    ``<LevelingDelay>0`` (271117); Assignment UID 22102 ``<ResourceUID>-65535`` (554277),
    Type-1 blocks PT64H / empty 02-25 / PT144H / empty 03-24 / PT32H / empty 03-31 / PT48H
    (554296-554344). Hand arithmetic (calendar 3, Mon-Fri 08-12/13-17, its only exception in
    the window 2025-02-17): 02-12..04-08 holds 39 working days = 36 worked (64+144+32+48 =
    288 h) + 3 gap days, so the finish is 04-08 17:00; a contiguous 36 days from 02-12 08:00
    ends 04-03 17:00, the engine's figure. A2 -- ``engine/cpm.py:856-858`` (ADR-0491): "A window
    nobody works is the TASK's split -- MS Project's Duration excludes it, so the leg must add
    it"; on a task with no resource, nobody works the gap by construction.

    Independence: the Finish / TotalSlack / TimephasedData were written by MS Project into the
    save Fuse analysed (the golden's PROVENANCE.json); they are read here with ElementTree, not
    through the importer or engine under test. Census (44-file corpus: 15 goldens + 29 intake
    conversions): the same mechanism leaves UIDs 7262, 7265 and 5376 inexact on every
    Large_Test_File save and 5376 on every Large_Test_File2 save (9 of 44 files); honouring the
    placeholder split moves 46 finishes toward the stored values (all 46 then exact) and none
    away.
    """
    raw = gzip.decompress((GOLDEN / "fuse_ltf" / "Large_Test_File.mspdi.xml.gz").read_bytes())
    root = ET.fromstring(raw)
    el = _a0923_cpm_002_task(root, 7262)
    premise = {
        "Start": "2025-02-12T08:00:00",
        "Finish": "2025-04-08T17:00:00",
        "Duration": "PT288H0M0S",
        "TotalSlack": "3117600",
        "PercentComplete": "0",
        "LevelingDelay": "0",
        "ConstraintType": "0",
        "CalendarUID": (root.findtext(NS + "CalendarUID") or "").strip(),
    }
    stored = {k: (el.findtext(NS + k) or "").strip() for k in premise}
    if stored != premise:
        pytest.fail(f"precondition: MS Project's stored UID 7262 fields moved: {stored}")
    gaps = _a0923_cpm_002_split(root, 7262)
    days = (dt.date(2025, 2, 25), dt.date(2025, 3, 24), dt.date(2025, 3, 31))
    if gaps != [
        (dt.datetime.combine(d, dt.time(8)), dt.datetime.combine(d, dt.time(17))) for d in days
    ]:
        pytest.fail(f"precondition: the placeholder's recorded split is no longer {days}: {gaps}")
    stored_finish = dt.datetime.fromisoformat(stored["Finish"])
    stored_tf_tenths = int(stored["TotalSlack"])

    sch = parse_mspdi_text(raw.decode("utf-8"))
    task = next((t for t in sch.tasks if t.unique_id == 7262), None)
    if task is None or task.duration_minutes != 288 * 60:
        pytest.fail("precondition: the importer no longer reads UID 7262 as 288 working hours")
    timing = compute_cpm(sch).timings[7262]
    # the start is not in dispute: the (early_start + 1)-th working minute BEGINS one minute
    # before offset_to_datetime renders its end -- the start-role instant of early_start
    start = offset_to_datetime(
        sch.project_start, timing.early_start + 1, sch.calendar
    ) - dt.timedelta(minutes=1)
    if start != dt.datetime.fromisoformat(stored["Start"]):
        pytest.fail(f"precondition: the engine's early start {start} is not the stored Start")
    finish = timing.early_finish_wall or offset_to_datetime(
        sch.project_start, timing.early_finish, sch.calendar
    )
    assert (finish, timing.total_float * 10) == (stored_finish, stored_tf_tenths), (
        f"UID 7262: engine early finish {finish:%Y-%m-%d %H:%M} / total float "
        f"{timing.total_float} min; MS Project stores {stored_finish:%Y-%m-%d %H:%M} / "
        f"{stored_tf_tenths / 10:g} min -- the split on its unassigned-work placeholder booking "
        f"({', '.join(f'{s:%m-%d}' for s, _ in gaps)}) is not honoured"
    )


# --- A0923-CPM-003 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py, and on nothing else:
#   imports    datetime as dt, gzip, xml.etree.ElementTree as ET, pytest,
#              compute_cpm and offset_to_datetime (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Input: the committed, non-CUI golden tests/fixtures/golden/fuse_ltf/Large_Test_File.mspdi.xml.gz
# (read with gzip). No new fixture file.


def _a0923_cpm_003_fields(root: ET.Element, uid: int, keys: tuple[str, ...]) -> dict[str, str]:
    """The raw stored fields of one ``<Task>`` -- read with ElementTree, not the importer."""
    for el in root.iter(NS + "Task"):
        if (el.findtext(NS + "UID") or "").strip() == str(uid):
            return {k: (el.findtext(NS + k) or "").strip() for k in keys}
    pytest.fail(f"precondition: the golden has no <Task> with UID {uid}")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-003: an FF predecessor's late finish and free float ignore the successor's "
        "stored leveling delay, so Large_Test_File UID 5314 (FF -> leveled UID 5316) reads late "
        "finish 2028-06-14 11:54, total float 227,757 and free float 9,361 min where MS Project "
        "stores 2028-05-30 11:53, 222,475.3 and 4,080"
    ),
)
def test_a0923_cpm_003_an_ff_predecessor_of_a_leveled_task_owns_none_of_its_delay() -> None:
    """A0923-CPM-003 · CPM · T1.

    Claim: at 19173728, ``tests/fixtures/golden/fuse_ltf/Large_Test_File.mspdi.xml.gz`` UID 5314
    (unstarted; its only successor link is FF, lag 0, to UID 5316, which stores a
    15.0-elapsed-day LevelingDelay) via ``compute_cpm(parse_mspdi_text(...))`` yields late
    finish 2028-06-14 11:54, total float 227,757 min and free float 9,361 min; MS Project's
    stored values in the same file are LateFinish 2028-05-30 11:53 (= 5316's LateFinish less its
    delay), TotalSlack 222,475.3 min and FreeSlack 4,080 min. The engine subtracts a successor's
    delay from START-type needs and anchors (``_succ_ls_wall``, ADR-0474; ``_succ_free_start_wall``,
    ADR-0522) but not on the FF branch (``engine/cpm.py:3059-3060`` ``_succ_lf_wall``;
    ``cpm.py:3219-3220`` ``_succ_early_finish_wall``). Verifier's narrowing: witnessed for FF
    only -- the corpus holds no SF link into a leveled successor (SF UNVERIFIED) -- and the
    integer-minute engine can reach the stored 222,475.3 only to within a minute; the 5,281-min
    excess is the defect. ADR-0522's QC-3 row ("the delay belongs on FINISH-type anchors too |
    refuted ... The backward-pass mirror ... is right") is the documented premise this falsifies:
    its "+7 low" were these same 5314 rows landing low on an early-date residual since removed.

    Authority: A1 -- MS Project's own stored values, decompressed golden: Task 5314 (line 119482)
    ``<EarlyFinish>2026-08-19T16:57:42`` (119512), ``<LateFinish>2028-05-30T11:53:00`` (119514),
    ``<FreeSlack>40800`` (119517), ``<TotalSlack>2224753`` (119518); Task 5316 (line 119704)
    ``<EarlyFinish>2026-09-16T11:58:48`` (119734), ``<LateFinish>2028-06-14T11:54:06`` (119736),
    ``<LevelingDelay>216011`` (119751), ``<LevelingDelayFormat>8`` (elapsed days, 119752),
    ``<PredecessorLink>`` 5314 ``<Type>0`` (FF) ``<LinkLag>0`` (119759-119762). Hand
    arithmetic: 216011 tenths = 21,601.1 min = 15 d 00:01:06 elapsed; 2028-06-14 11:54:06 less
    it = 2028-05-30 11:53:00, 5314's stored LateFinish to the second (checked below from the
    stored values alone); free: 2026-09-16 11:58:48 less the delay = 09-01 11:57:42, and
    calendar 68 (Mon-Fri 08-12/13-17) holds 2.3 + 8 x 480 + 237.7 = 4,080.0 working minutes
    from 5314's EarlyFinish to it = the stored FreeSlack. The same rule reproduces the other
    two distinct saves of this link (Large_Test_File2, Large_Test_File_Leveled) to the second.

    Independence: MS Project wrote the LateFinish / TotalSlack / FreeSlack / LevelingDelay values
    into three committed saves; they are read here with ElementTree and checked by arithmetic
    on the stored values, never by the engine's own backward pass.
    """
    raw = gzip.decompress((GOLDEN / "fuse_ltf" / "Large_Test_File.mspdi.xml.gz").read_bytes())
    root = ET.fromstring(raw)
    keys = ("PercentComplete", "EarlyFinish", "LateFinish", "TotalSlack", "FreeSlack")
    pred = _a0923_cpm_003_fields(root, 5314, (*keys, "ConstraintType"))
    succ = _a0923_cpm_003_fields(root, 5316, (*keys, "LevelingDelay", "LevelingDelayFormat"))
    if (pred["PercentComplete"], pred["ConstraintType"], pred["LateFinish"]) != (
        "0",
        "0",
        "2028-05-30T11:53:00",
    ) or (pred["TotalSlack"], pred["FreeSlack"]) != ("2224753", "40800"):
        pytest.fail(f"precondition: MS Project's stored UID 5314 fields moved: {pred}")
    if (succ["PercentComplete"], succ["LevelingDelay"], succ["LevelingDelayFormat"]) != (
        "0",
        "216011",
        "8",
    ):
        pytest.fail(f"precondition: UID 5316 no longer stores the 15-elapsed-day delay: {succ}")
    links = [
        (
            (t.findtext(NS + "UID") or "").strip(),
            (pl.findtext(NS + "Type") or "").strip(),
            (pl.findtext(NS + "LinkLag") or "").strip(),
        )
        for t in root.iter(NS + "Task")
        for pl in t.findall(NS + "PredecessorLink")
        if (pl.findtext(NS + "PredecessorUID") or "").strip() == "5314"
    ]
    if links != [("5316", "0", "0")]:
        pytest.fail(f"precondition: UID 5314's successors are no longer one FF lag-0 link: {links}")
    delay = dt.timedelta(seconds=int(succ["LevelingDelay"]) * 6)  # tenths of a minute, elapsed
    stored_lf = dt.datetime.fromisoformat(pred["LateFinish"])
    succ_lf = dt.datetime.fromisoformat(succ["LateFinish"])
    if succ_lf - delay != stored_lf:
        pytest.fail(
            "precondition: MS Project's stored 5314 LateFinish is not 5316's less its delay"
        )

    sch = parse_mspdi_text(raw.decode("utf-8"))
    timings = compute_cpm(sch).timings
    t_pred, t_succ = timings[5314], timings[5316]

    def wall(w: dt.datetime | None, offset: int) -> dt.datetime:
        return w or offset_to_datetime(sch.project_start, offset, sch.calendar)

    # the rest of the network is not in dispute: the successor's own late finish and the
    # predecessor's early finish are MS Project's to the minute
    if wall(t_succ.late_finish_wall, t_succ.late_finish) != succ_lf.replace(second=0):
        pytest.fail(f"precondition: the engine's UID 5316 late finish moved: {t_succ}")
    pred_ef = dt.datetime.fromisoformat(pred["EarlyFinish"]).replace(second=0)
    if wall(t_pred.early_finish_wall, t_pred.early_finish) != pred_ef:
        pytest.fail(f"precondition: the engine's UID 5314 early finish moved: {t_pred}")
    lf = wall(t_pred.late_finish_wall, t_pred.late_finish)
    stored_tf_tenths, stored_ff_tenths = int(pred["TotalSlack"]), int(pred["FreeSlack"])
    got = (lf, t_pred.free_float * 10, abs(t_pred.total_float * 10 - stored_tf_tenths) <= 10)
    assert got == (stored_lf, stored_ff_tenths, True), (
        f"UID 5314 (FF -> UID 5316, delay {delay}): engine late finish {lf:%Y-%m-%d %H:%M}, "
        f"total float {t_pred.total_float}, free float {t_pred.free_float} min; MS Project "
        f"stores {stored_lf:%Y-%m-%d %H:%M}, {stored_tf_tenths / 10:.1f} (to within a minute) and "
        f"{stored_ff_tenths / 10:.1f} -- the successor's leveling delay is counted as this task's "
        f"float"
    )


# --- A0923-CPM-004 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py, and on nothing else:
#   imports    datetime as dt, gzip, xml.etree.ElementTree as ET, typing.Any, pytest,
#              compute_cpm (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Inputs: the committed, non-CUI goldens tests/fixtures/golden/fuse_hardfile/Hard_File,
# Hard_File_updated and Hard_File_updated3 .mspdi.xml.gz (read with gzip). No new fixture file.

#: (golden, UID, MS Project's stored LateFinish, its line in the decompressed XML) -- the four
#: unstarted multi-booking activities on which the primary-leg snap and MS Project disagree.
_A0923_CPM_004_WITNESSES = (
    ("Hard_File.mspdi.xml.gz", 398, "2026-10-21T06:59:00", 10540),
    ("Hard_File_updated.mspdi.xml.gz", 398, "2026-10-21T06:59:00", 10794),
    ("Hard_File_updated3.mspdi.xml.gz", 188, "2026-12-12T17:00:00", 4209),
    ("Hard_File_updated3.mspdi.xml.gz", 385, "2026-09-30T07:00:00", 9856),
)
#: Controls: unstarted multi-booking activities the engine ALREADY reproduces (its primary leg
#: happens to be the leg MS Project's late finish sits on). A "fix" that breaks them is wrong.
_A0923_CPM_004_CONTROLS = (
    ("Hard_File.mspdi.xml.gz", 200, "2026-08-23T10:00:00", 4768),
    ("Hard_File_updated3.mspdi.xml.gz", 398, "2026-10-26T08:00:00", 12590),
)


def _a0923_cpm_004_stored(root: ET.Element, uid: int) -> tuple[dt.datetime, int]:
    """MS Project's stored ``<LateFinish>`` of task ``uid`` and the number of its
    ``<Assignment>`` elements -- read with ElementTree, never through the importer (the model
    carries no late dates). Preconditions: the task exists, has NOT started (no
    ``<ActualStart>``, ``<PercentComplete>`` 0) and carries at least two bookings (a multi-leg
    execution plan), so the ADR-0474 decision-3 snap is the code the check reaches."""
    for el in root.iter(NS + "Task"):
        if (el.findtext(NS + "UID") or "").strip() != str(uid):
            continue
        if (el.findtext(NS + "ActualStart") or "").strip():
            pytest.fail(f"precondition: UID {uid} now carries an ActualStart (started)")
        if (el.findtext(NS + "PercentComplete") or "0").strip() != "0":
            pytest.fail(f"precondition: UID {uid} is no longer 0 % complete")
        lf = (el.findtext(NS + "LateFinish") or "").strip()
        if not lf:
            pytest.fail(f"precondition: UID {uid} carries no stored <LateFinish>")
        bookings = sum(
            1
            for a in root.iter(NS + "Assignment")
            if (a.findtext(NS + "TaskUID") or "").strip() == str(uid)
        )
        if bookings < 2:
            pytest.fail(f"precondition: UID {uid} no longer carries two or more bookings")
        return dt.datetime.fromisoformat(lf), bookings
    pytest.fail(f"precondition: the golden has no <Task> with UID {uid}")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-004: the multi-leg backward pass snaps an unstarted task's late-finish need "
        "back on the primary leg's calendar only (cpm.py:3078, ADR-0474 decision 3), so "
        "Hard_File UID 398 reads late finish 2026-10-20 17:00 where MS Project stores "
        "2026-10-21 06:59 (and 3 more unstarted activities likewise); the need itself is exact"
    ),
)
def test_a0923_cpm_004_an_unstarted_multi_leg_late_finish_is_ms_projects_stored_instant() -> None:
    """A0923-CPM-004 · CPM · T2.

    Claim (verifier's narrowed claim): at 19173728 the multi-leg backward pass snaps the
    late-finish need back on ``plan[0]`` only -- ``engine/cpm.py:3078``
    ``lf_w = _snap_back_to_working(min(finish_needs), plan[0][0], tod0)`` -- so four unstarted
    multi-booking activities read ``TaskTiming.late_finish_wall`` one snap early:
    Hard_File and Hard_File_updated UID 398 2026-10-20 17:00 (stored 2026-10-21 06:59),
    Hard_File_updated3 UID 188 2026-12-11 17:00 (stored 2026-12-12 17:00, a Saturday only the
    24-hour crew works) and UID 385 2026-09-29 17:00 (stored 2026-09-30 07:00, a 16-hour crew's
    instant). The engine's NEED equals the stored value on every witness; only the snap onto the
    primary (Standard) leg moves it. On the 44-file corpus the class is 10 instances of 4 distinct
    activities (6 goldens + 4 .mpp saves), every one unstarted; only ``late_finish_wall`` moves
    (total float, late start, critical flag and project finish are unchanged), and it is read
    only by the parity ``lf_exact`` census. The ONE started discriminating instance
    (04_24Hour_Calendar.mpp UID 17) goes the other way -- the primary snap matches there -- so
    the correct rule is not "union of all legs" for every task (see the fix sketch).

    Authority: A1 -- MS Project's own stored ``<LateFinish>`` in the committed goldens (line
    numbers of the decompressed XML): Hard_File.mspdi.xml.gz:10540
    ``<LateFinish>2026-10-21T06:59:00</LateFinish>`` (UID 398); Hard_File_updated.mspdi.xml.gz:10794
    ``<LateFinish>2026-10-21T06:59:00</LateFinish>`` (UID 398); Hard_File_updated3.mspdi.xml.gz:4209
    ``<LateFinish>2026-12-12T17:00:00</LateFinish>`` (UID 188) and :9856
    ``<LateFinish>2026-09-30T07:00:00</LateFinish>`` (UID 385). A2 -- the premise of the decision
    the code implements, ADR-0474 (title: "MS Project's stored dates as the oracle") decision 3:
    "the late finish is the tightest need snapped back to a FINISH instant on the primary leg".

    Oracle independence: the stored values were computed and written by MS Project; the
    importer and the model never read ``<LateFinish>`` (this test reads it with ElementTree).
    Controls in the same test: two unstarted multi-booking activities the engine already
    reproduces (Hard_File UID 200, updated3 UID 398) must stay exact.

    Not asserted (UNVERIFIED oracle): the booking-order sensitivity of the same rule (reversing
    a task's ``<Assignment>`` elements moves Hard_File UID 200 to 2026-08-21 17:00) -- MS
    Project's value on a reordered file is inferred from MSPDI UID semantics, not observed.
    """
    goldens: dict[str, tuple[ET.Element, Any]] = {}

    def engine_lf(name: str, uid: int) -> tuple[dt.datetime, dt.datetime | None]:
        if name not in goldens:
            raw = gzip.decompress((GOLDEN / "fuse_hardfile" / name).read_bytes())
            goldens[name] = (
                ET.fromstring(raw),
                compute_cpm(parse_mspdi_text(raw.decode("utf-8"))).timings,
            )
        root, timings = goldens[name]
        stored, _ = _a0923_cpm_004_stored(root, uid)
        if uid not in timings:
            pytest.fail(f"precondition: the engine returned no timing for {name} UID {uid}")
        return stored, timings[uid].late_finish_wall

    for name, uid, text, line in _A0923_CPM_004_CONTROLS:
        stored, got = engine_lf(name, uid)
        if stored != dt.datetime.fromisoformat(text):
            pytest.fail(f"precondition: {name}:{line} no longer stores {text} for UID {uid}")
        if got != stored:
            pytest.fail(
                f"precondition (control): {name} UID {uid} late finish {got} no longer equals "
                f"MS Project's stored {stored} -- the harness or the fix is wrong"
            )

    wrong = {}
    for name, uid, text, line in _A0923_CPM_004_WITNESSES:
        stored, got = engine_lf(name, uid)
        if stored != dt.datetime.fromisoformat(text):
            pytest.fail(f"precondition: {name}:{line} no longer stores {text} for UID {uid}")
        if got is None:
            pytest.fail(f"precondition: {name} UID {uid} is no longer on the wall path")
        if got != stored:
            wrong[f"{name} UID {uid}"] = (f"{got:%Y-%m-%d %H:%M}", f"{stored:%Y-%m-%d %H:%M}")
    assert not wrong, (
        "an unstarted multi-leg activity's late finish is not MS Project's stored LateFinish "
        f"(engine, stored): {wrong}"
    )


# --- A0923-CPM-005 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py, and on nothing else:
#   imports    datetime as dt, gzip, xml.etree.ElementTree as ET, typing.Any, pytest,
#              compute_cpm (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Inputs: the committed, non-CUI goldens tests/fixtures/golden/fuse_hardfile/Hard_File_updated
# and Hard_File_updated3_24hr .mspdi.xml.gz (read with gzip), each with ONE <PredecessorLink>
# added in memory. No new fixture file.

#: MSPDI ``PredecessorLink/Type`` codes (Microsoft Learn, "Type Element (Multiple Parents)").
_A0923_CPM_005_TYPE = {"FS": "1", "SF": "2", "SS": "3"}
#: (golden, milestone A, its FS0 successor B, B's FS0 successor C, the redundant link types added
#: A -> C). A is zero-duration; A -FS0-> B -FS0-> C already exists in the file.
_A0923_CPM_005_WITNESSES = (
    ("Hard_File_updated.mspdi.xml.gz", 260, 274, 264, ("SS",)),
    ("Hard_File_updated3_24hr.mspdi.xml.gz", 410, 13, 7, ("SS", "SF")),
)


def _a0923_cpm_005_task(root: ET.Element, uid: int) -> ET.Element:
    """The raw ``<Task>`` element with this UID -- read with ElementTree, not the importer."""
    for el in root.iter(NS + "Task"):
        if (el.findtext(NS + "UID") or "").strip() == str(uid):
            return el
    pytest.fail(f"precondition: the golden has no <Task> with UID {uid}")


def _a0923_cpm_005_links_fs0(root: ET.Element, pred: int, succ: int) -> bool:
    """True iff the file itself links ``pred -FS lag 0-> succ``."""
    return any(
        (pl.findtext(NS + "PredecessorUID") or "").strip() == str(pred)
        and (pl.findtext(NS + "Type") or "").strip() == "1"
        and (pl.findtext(NS + "LinkLag") or "0").strip() == "0"
        for pl in _a0923_cpm_005_task(root, succ).findall(NS + "PredecessorLink")
    )


def _a0923_cpm_005_with_link(raw: bytes, pred: int, succ: int, kind: str) -> str:
    """The same project with ONE extra lag-0 ``<PredecessorLink>`` ``pred -kind-> succ``."""
    root = ET.fromstring(raw)
    link = ET.SubElement(_a0923_cpm_005_task(root, succ), NS + "PredecessorLink")
    for tag, value in (
        ("PredecessorUID", str(pred)),
        ("Type", _A0923_CPM_005_TYPE[kind]),
        ("CrossProject", "0"),
        ("LinkLag", "0"),
        ("LagFormat", "7"),
    ):
        ET.SubElement(link, NS + tag).text = value
    return ET.tostring(root, encoding="unicode")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-005: a lag-0 SS/SF link from a non-carried zero-duration task into a wall-path "
        "successor reads the milestone's START-role rendering (the next working morning, "
        "cpm.py:2474), so a transitively redundant SS0 260->264 on Hard_File_updated moves 264 "
        "from 10-06 01:00 to 10-06 08:00 and the project finish from 11-05 12:00 to 11-05 17:15"
    ),
)
def test_a0923_cpm_005_a_redundant_lag0_start_link_from_a_milestone_moves_nothing() -> None:
    """A0923-CPM-005 · CPM · T1.

    Claim: at 19173728, ``tests/fixtures/golden/fuse_hardfile/Hard_File_updated.mspdi.xml.gz``
    with ONE added ``<PredecessorLink>`` 260 -SS0-> 264 -- transitively redundant, because
    260 -FS0-> 274 -FS0-> 264 is already in the file -- yields via ``compute_cpm`` 264's
    ``early_start_wall`` 2026-10-06 08:00 / ``early_finish_wall`` 2026-10-07 16:00 and
    ``project_finish_wall`` 2026-11-05 17:15 (``project_finish`` 41520 -> 41760); on
    Hard_File_updated3_24hr, 410 -SS0-> 7 moves 7 to 2026-11-16 08:00 and the project finish to
    2026-11-21 08:00, and 410 -SF0-> 7 to 2026-11-21 00:00. Mechanism: ``_pred_start_wall``
    (``engine/cpm.py:2469-2474``) renders a non-carried project-axis predecessor's start as
    ``_offset_to_wall(ps, early_start[p], cal, role="start")``; for a zero-duration task at an
    exact working-day multiple that is the NEXT working morning, while the same task's finish
    (``role="finish"``, the FS path) is the evening before -- a milestone that starts after it
    finishes. Latent on the committed corpus (0 exposed links of 11,979 + 21,609); fires on any
    such added link.

    Authority: A1 -- MS Project's stored instants in the committed goldens, read with
    ElementTree: Hard_File_updated UID 260 ``<Start>`` = ``<Finish>`` 2026-10-05T17:00:00
    (zero duration), UID 264 ``<Start>2026-10-06T01:00:00`` ``<Finish>2026-10-07T09:00:00``,
    project ``<FinishDate>2026-11-05T12:00:00`` (line 12); Hard_File_updated3_24hr UID 410
    2026-11-13T17:00:00, UID 7 ``<Start>2026-11-14T01:00:00`` ``<Finish>2026-11-14T09:00:00``,
    ``<FinishDate>2026-11-19T01:00:00`` (line 15). Codes: Microsoft Learn "Type Element
    (Multiple Parents)", https://learn.microsoft.com/office-project/xml-data-interchange/type-element-multiple-parents?view=project-client-2016
    (retrieved 2026-09-25): PredecessorLink Type "2 | SF (start-to-finish)", "3 | SS
    (start-to-start)". Semantics: Microsoft Learn "Create a work breakdown structure (WBS)",
    https://learn.microsoft.com/dynamics365/project-operations/project-management/create-wbs#task-dependencies
    (retrieved 2026-09-25): SS "Task B (successor) can start only with or after the start of
    task A (predecessor)"; SF "Task B (successor) can finish only after the start task A
    (predecessor)". A2 -- ``engine/cpm.py:696-697``
    (``span_start_datetime``): "A **zero-duration instant** (milestone) has no beginning distinct
    from the instant itself" (ADR-0348).

    Oracle independence: no MS Project behaviour beyond its stored instants is needed. A -FS0->
    B -FS0-> C already implies ES_C >= EF_B >= ES_B >= EF_A = ES_A, so a lag-0 SS (or SF)
    A -> C is redundant by definition and cannot move anything under any consistent semantics;
    the expectation is the file's own stored dates, which the unmodified solve reproduces
    (checked here as a precondition), and the FS0 twin of the added link (a control) moves
    nothing today.
    """
    moved: dict[str, tuple[str, ...]] = {}
    for name, a, b, c, kinds in _A0923_CPM_005_WITNESSES:
        raw = gzip.decompress((GOLDEN / "fuse_hardfile" / name).read_bytes())
        root = ET.fromstring(raw)
        a_el, c_el = _a0923_cpm_005_task(root, a), _a0923_cpm_005_task(root, c)
        a_start = dt.datetime.fromisoformat((a_el.findtext(NS + "Start") or "").strip())
        if a_start != dt.datetime.fromisoformat((a_el.findtext(NS + "Finish") or "").strip()):
            pytest.fail(f"precondition: {name} UID {a} is no longer a zero-duration instant")
        c_start = dt.datetime.fromisoformat((c_el.findtext(NS + "Start") or "").strip())
        c_finish = dt.datetime.fromisoformat((c_el.findtext(NS + "Finish") or "").strip())
        finish = dt.datetime.fromisoformat((root.findtext(NS + "FinishDate") or "").strip())
        if not (_a0923_cpm_005_links_fs0(root, a, b) and _a0923_cpm_005_links_fs0(root, b, c)):
            pytest.fail(f"precondition: {name} no longer chains {a} -FS0-> {b} -FS0-> {c}")
        if not a_start <= c_start:
            pytest.fail(f"precondition: {name} UID {a} no longer starts before UID {c}")

        def solve(text: str, c: int = c) -> tuple[Any, ...]:
            res = compute_cpm(parse_mspdi_text(text))
            tc = res.timing(c)
            return (tc.early_start_wall, tc.early_finish_wall, res.project_finish_wall)

        base = solve(raw.decode("utf-8"))
        if base != (c_start, c_finish, finish):
            pytest.fail(
                f"precondition: unmodified {name} no longer reproduces MS Project's stored "
                f"UID {c} start/finish and FinishDate: {base} vs {(c_start, c_finish, finish)}"
            )
        twin = solve(_a0923_cpm_005_with_link(raw, a, c, "FS"))
        if twin != base:
            pytest.fail(f"precondition (control): the FS0 twin {a} -> {c} now moves {twin}")

        for kind in kinds:
            got = solve(_a0923_cpm_005_with_link(raw, a, c, kind))
            if got != base:
                moved[f"{name} +{kind}0 {a}->{c}"] = tuple(f"{x:%Y-%m-%d %H:%M}" for x in got)
    assert not moved, (
        "a transitively redundant lag-0 start link from a milestone moved the successor off MS "
        f"Project's stored instants ((start, finish, project finish) with the link): {moved}"
    )


# --- A0923-CPM-006 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py, and on nothing else:
#   imports    datetime as dt, pytest,
#              compute_cpm and offset_to_datetime (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi)
#   fixture    the module-level autouse _air_gapped
# Input: an inline MSPDI document built below (no fixture file, nothing CUI).

_A0923_CPM_006_BLOCKS = (
    "<WorkingTimes><WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime>"
    "</WorkingTime><WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime>"
    "</WorkingTime></WorkingTimes>"
)


def _a0923_cpm_006_mspdi(saturday_by_week: bool) -> str:
    """Project calendar Standard, Mon-Fri 08:00-12:00 + 13:00-17:00, StartDate Fri 2026-12-18
    08:00. ``saturday_by_week=False`` (the defect input): Saturday 2026-12-19 is worked through a
    ``DayWorking=1`` ``<Exception>`` carrying the calendar's OWN two blocks. ``True`` (the
    control): Saturdays are worked by the weekly pattern, no exception. T1: 2 days (PT16H), no
    predecessor. T2: the identical task plus a 1-minute ``<LevelingDelay>`` (10 tenths of a
    minute, format 8 = elapsed minutes)."""
    last = 7 if saturday_by_week else 6  # MSPDI DayType: 1 = Sunday .. 7 = Saturday
    days = "".join(
        f"<WeekDay><DayType>{d}</DayType><DayWorking>{int(2 <= d <= last)}</DayWorking>"
        + (_A0923_CPM_006_BLOCKS if 2 <= d <= last else "")
        + "</WeekDay>"
        for d in range(1, 8)
    )
    exceptions = (
        ""
        if saturday_by_week
        else "<Exceptions><Exception><EnteredByOccurrences>0</EnteredByOccurrences><TimePeriod>"
        "<FromDate>2026-12-19T00:00:00</FromDate><ToDate>2026-12-19T23:59:00</ToDate>"
        "</TimePeriod><Occurrences>1</Occurrences><Name>Worked Saturday</Name><Type>1</Type>"
        f"<DayWorking>1</DayWorking>{_A0923_CPM_006_BLOCKS}</Exception></Exceptions>"
    )
    return (
        '<Project xmlns="http://schemas.microsoft.com/project"><Name>a0923-cpm-006</Name>'
        "<StartDate>2026-12-18T08:00:00</StartDate><CalendarUID>1</CalendarUID>"
        "<Calendars><Calendar><UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>"
        f"<BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{days}</WeekDays>{exceptions}"
        "</Calendar></Calendars><Tasks>"
        "<Task><UID>1</UID><Name>T1</Name><Duration>PT16H0M0S</Duration>"
        "<DurationFormat>7</DurationFormat></Task>"
        "<Task><UID>2</UID><Name>T2</Name><Duration>PT16H0M0S</Duration>"
        "<DurationFormat>7</DurationFormat><LevelingDelay>10</LevelingDelay>"
        "<LevelingDelayFormat>8</LevelingDelayFormat></Task>"
        "</Tasks></Project>"
    )


def _a0923_cpm_006_finishes(saturday_by_week: bool) -> tuple[dt.datetime, ...]:
    """(T1 finish, T2 finish, project finish) as the engine's own instants: the wall instant
    where the engine carries one, else the project-axis rendering of the offset -- exactly the
    reading the parity census and the pages apply to a task's early finish."""
    sch = parse_mspdi_text(_a0923_cpm_006_mspdi(saturday_by_week))
    if not saturday_by_week and sch.calendar.working_days != (dt.date(2026, 12, 19),):
        pytest.fail(
            f"precondition: the importer no longer keeps the worked Saturday on the project "
            f"calendar (working_days={sch.calendar.working_days})"
        )
    if sch.tasks_by_id[2].leveling_delay_minutes != 1:
        pytest.fail("precondition: T2 no longer carries its 1-minute leveling delay")
    res = compute_cpm(sch)

    def rendered(wall: dt.datetime | None, offset: int) -> dt.datetime:
        return wall or offset_to_datetime(sch.project_start, offset, sch.calendar)

    t1, t2 = res.timings[1], res.timings[2]
    return (
        rendered(t1.early_finish_wall, t1.early_finish),
        rendered(t2.early_finish_wall, t2.early_finish),
        rendered(res.project_finish_wall, res.project_finish),
    )


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-006: the CPM fast path ignores a DayWorking=1 exception on the project calendar "
        "while the wall path honours it, so a 2-day task from Fri 2026-12-18 08:00 finishes Mon "
        "12-21 17:00 (worked Saturday skipped) and the identical task with a 1-minute leveling "
        "delay finishes Mon 12-21 08:01 -- a delay moves the finish EARLIER"
    ),
)
def test_a0923_cpm_006_a_worked_exception_day_is_worked_by_every_task_on_its_calendar() -> None:
    """A0923-CPM-006 · CPM · T1.

    Claim: at 19173728, an MSPDI whose project calendar (Standard, Mon-Fri 08-12/13-17) carries a
    ``DayWorking=1`` ``<Exception>`` on Saturday 2026-12-19 with the calendar's own
    ``WorkingTimes``, StartDate Fri 2026-12-18 08:00, yields via ``parse_mspdi_text`` +
    ``compute_cpm`` a 2-day task (T1) finishing Mon 2026-12-21 17:00 on the integer fast path,
    while the identical task with a 1-minute ``LevelingDelay`` (T2, routed to the wall path on
    the SAME project calendar since ADR-0474 decision 2) finishes Mon 2026-12-21 08:01 -- earlier
    than the undelayed task -- and the project finish reads Mon 17:00. Two readings of one
    calendar in one solve: the fast-path rulers (``_count_working_days_r`` :468,
    ``_advance_working_days_r`` :580, ``datetime_to_offset`` :519, ``offset_to_datetime`` :633)
    count weekdays minus holidays only; the wall helpers read ``_Ruler.is_worked`` (:417-419),
    which honours the extra. Latent on the committed corpus (11 of 44 files carry a
    project-calendar extra; 0 computed spans cross one); fires on any task spanning one.

    Authority: A1 -- the MSPDI schema on Microsoft Learn (retrieved 2026-09-25): "DayWorking
    Element (Calendar)", https://learn.microsoft.com/office-project/xml-data-interchange/dayworking-element-calendar?view=project-client-2016
    -- "Indicates whether the specified date or day type is a working day" / "1 True, working
    day"; "Exception Element", https://learn.microsoft.com/office-project/xml-data-interchange/exception-element?view=project-client-2016
    -- WorkingTimes: "The collection of working times that define the time worked on the working
    day". Hand arithmetic on that calendar: T1 = Fri 08-12, 13-17 (480) + Sat 08-12, 13-17 (480)
    = 960 -> Sat 2026-12-19 17:00. T2 = Fri 08:01 -> 479 on Fri + 480 on Sat + 1 on Mon -> Mon
    2026-12-21 08:01 (the engine's wall path reproduces this to the minute). Project finish =
    max = Mon 08:01. Monotonicity needs no oracle: a delay added to an early start cannot yield
    an earlier early finish on the same calendar and duration. A2 (premise now false) --
    ``src/schedule_forensics/model/calendar.py:117-118``: "Used only by the driving-slack parity
    path so the broader engine's single-calendar model (ADR-0028) is unchanged";
    ``docs/adr/0118-driving-slack-per-task-calendars.md:55-57``: "The broader engine (CPM,
    DCMA/EVM metrics) keeps the ADR-0028 single project-calendar, single-block model".

    Oracle independence: the expected instants are hand arithmetic on the input's own declared
    calendar per Microsoft's schema; the engine is not consulted for them. The exception carries
    the calendar's OWN blocks, so the held item "a working exception's own hours" (ADR-0503) is
    not touched. Control in the same test: the same Saturday worked by the WEEKLY pattern gives
    the hand values today (the harness can pass).
    """
    sat_17 = dt.datetime(2026, 12, 19, 17, 0)
    mon_0801 = dt.datetime(2026, 12, 21, 8, 1)
    control = _a0923_cpm_006_finishes(saturday_by_week=True)
    if control != (sat_17, mon_0801, mon_0801):
        pytest.fail(
            f"precondition (control): a Saturday worked by the weekly pattern no longer gives "
            f"the hand values (T1, T2, project) = {control}"
        )

    t1, t2, project = _a0923_cpm_006_finishes(saturday_by_week=False)
    wrong = {
        name: f"{got:%a %Y-%m-%d %H:%M} (hand {want:%a %Y-%m-%d %H:%M})"
        for name, got, want in (
            ("T1 (fast path)", t1, sat_17),
            ("T2 (+1 min delay, wall path)", t2, mon_0801),
            ("project finish", project, mon_0801),
        )
        if got != want
    }
    if t2 < t1:
        wrong["monotonicity"] = f"the 1-minute delay moved the finish EARLIER: {t2} < {t1}"
    assert not wrong, f"a worked exception day on the project calendar is read two ways: {wrong}"


# --- A0923-CPM-007 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    datetime as dt, pytest,
#              compute_cpm and offset_to_datetime (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi)
#   ALSO NEEDS datetime_to_offset on the header's ``from schedule_forensics.engine.cpm import``
#              line (the style reference imports only compute_cpm and offset_to_datetime):
#              ``from schedule_forensics.engine.cpm import compute_cpm, datetime_to_offset,
#              offset_to_datetime``
#   fixture    the module-level autouse _air_gapped
# Input: inline MSPDI text (built below). No fixture file; nothing CUI.

#: MS Project's Standard day, Mon-Fri 08:00-12:00 + 13:00-17:00, as minutes-from-midnight blocks.
_A0923_CPM_007_BLOCKS = ((480, 720), (780, 1020))


def _a0923_cpm_007_mspdi(start_hour: int) -> str:
    """One MSPDI project on the Standard calendar, starting Monday 2025-01-06 at ``start_hour``:
    A (2d, no logic); T3 (1h, no logic); T2 (1 elapsed day, FS after T3)."""
    times = "".join(
        f"<WorkingTime><FromTime>{s // 60:02d}:{s % 60:02d}:00</FromTime>"
        f"<ToTime>{e // 60:02d}:{e % 60:02d}:00</ToTime></WorkingTime>"
        for s, e in _A0923_CPM_007_BLOCKS
    )
    days = "".join(
        f"<WeekDay><DayType>{d}</DayType><DayWorking>{int(2 <= d <= 6)}</DayWorking>"
        + (f"<WorkingTimes>{times}</WorkingTimes>" if 2 <= d <= 6 else "")
        + "</WeekDay>"
        for d in range(1, 8)
    )

    def task(uid: int, name: str, duration: str, fmt: int, pred: int | None = None) -> str:
        link = (
            f"<PredecessorLink><PredecessorUID>{pred}</PredecessorUID><Type>1</Type>"
            "<LinkLag>0</LinkLag><LagFormat>7</LagFormat></PredecessorLink>"
            if pred is not None
            else ""
        )
        return (
            f"<Task><UID>{uid}</UID><Name>{name}</Name><Duration>{duration}</Duration>"
            f"<DurationFormat>{fmt}</DurationFormat>{link}</Task>"
        )

    return (
        '<Project xmlns="http://schemas.microsoft.com/project"><Name>origin</Name>'
        f"<StartDate>2025-01-06T{start_hour:02d}:00:00</StartDate><CalendarUID>1</CalendarUID>"
        "<Calendars><Calendar><UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>"
        f"<BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{days}</WeekDays></Calendar></Calendars>"
        "<Tasks>"
        + task(1, "A", "PT16H0M0S", 7)
        + task(3, "T3", "PT1H0M0S", 5)
        + task(2, "T2", "PT24H0M0S", 8, pred=3)
        + "</Tasks></Project>"
    )


def _a0923_cpm_007_is_worked(instant: dt.datetime) -> bool:
    """Is the minute beginning at ``instant`` working time on the declared calendar?"""
    tod = instant.hour * 60 + instant.minute
    return instant.weekday() < 5 and any(s <= tod < e for s, e in _A0923_CPM_007_BLOCKS)


def _a0923_cpm_007_walk(start: dt.datetime, worked: int) -> dt.datetime:
    """THE ORACLE, independent of the engine: the instant at which the ``worked``-th working
    minute after ``start`` ENDS, counted minute by minute over the declared WorkingTimes."""
    t = start
    while worked > 0:
        if _a0923_cpm_007_is_worked(t):
            worked -= 1
        t += dt.timedelta(minutes=1)
    return t


def _a0923_cpm_007_count(start: dt.datetime, target: dt.datetime) -> int:
    """THE ORACLE's inverse: working minutes of the declared WorkingTimes in ``[start, target)``."""
    n, t = 0, start
    while t < target:
        n += _a0923_cpm_007_is_worked(t)
        t += dt.timedelta(minutes=1)
    return n


def _a0923_cpm_007_mismatches(start_hour: int) -> dict[str, str]:
    """Engine vs the minute-walk oracle, for the project starting at ``start_hour``."""
    sch = parse_mspdi_text(_a0923_cpm_007_mspdi(start_hour))
    ps, cal = sch.project_start, sch.calendar
    if ps != dt.datetime(2025, 1, 6, start_hour):
        pytest.fail(f"precondition: the importer moved the legal start {start_hour:02d}:00 to {ps}")
    if cal.day_segments != _A0923_CPM_007_BLOCKS or cal.working_minutes_per_day != 480:
        pytest.fail(
            f"precondition: the declared day is no longer 08-12 / 13-17 x 480 min "
            f"({cal.day_segments}, {cal.working_minutes_per_day})"
        )
    res = compute_cpm(sch)
    a, t3, t2 = res.timings[1], res.timings[3], res.timings[2]
    if (a.early_finish, t3.early_finish) != (960, 60):
        pytest.fail(
            f"precondition: A / T3 consume {a.early_finish} / {t3.early_finish} working minutes, "
            "not 960 / 60"
        )
    t3_finish = offset_to_datetime(ps, t3.early_finish, cal)
    if t3_finish != _a0923_cpm_007_walk(ps, 60):
        pytest.fail(f"precondition: the start day itself is misread (T3 finishes {t3_finish})")
    tue_0830 = dt.datetime(2025, 1, 7, 8, 30)
    want = {
        "offset 480 -> wall": _a0923_cpm_007_walk(ps, 480),
        "Tue 08:30 -> offset": _a0923_cpm_007_count(ps, tue_0830),
        "A (2d) finish": _a0923_cpm_007_walk(ps, 960),
        "T2 (1ed FS after T3) finish": _a0923_cpm_007_walk(ps, 60) + dt.timedelta(days=1),
        "project finish": max(_a0923_cpm_007_walk(ps, 960), t3_finish + dt.timedelta(days=1)),
    }
    got: dict[str, object] = {
        "offset 480 -> wall": offset_to_datetime(ps, 480, cal),
        "Tue 08:30 -> offset": datetime_to_offset(ps, tue_0830, cal),
        "A (2d) finish": offset_to_datetime(ps, a.early_finish, cal),
        "T2 (1ed FS after T3) finish": t2.early_finish_wall,
        "project finish": res.project_finish_wall
        or offset_to_datetime(ps, res.project_finish, cal),
    }
    bad = {k: f"{got[k]} (oracle {want[k]})" for k in want if got[k] != want[k]}
    if t2.early_start < t3.early_finish:
        bad["FS order"] = f"T2 ES {t2.early_start} < its FS predecessor T3's EF {t3.early_finish}"
    breaks = [
        k
        for k in range(0, 1441, 30)
        if datetime_to_offset(ps, offset_to_datetime(ps, k, cal), cal) != k
    ]
    if breaks:
        bad["round trip (ADR-0312)"] = (
            f"datetime_to_offset(offset_to_datetime(k)) != k for {breaks}"
        )
    return bad


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-007: an MSPDI whose StartDate is 09:00 on a declared 08-12/13-17 calendar "
        "gets a lossy working-minute axis: offset 480 reads Mon 17:00 (not Tue 09:00), Tue 08:30 "
        "reads 480 (not 450), a 2d task finishes Tue 17:00 (not Wed 09:00) and the elapsed FS "
        "successor T2 starts before T3 finishes and ends Tue 09:00 (not Tue 10:00)"
    ),
)
def test_a0923_cpm_007_a_mid_block_project_start_keeps_a_lossless_working_minute_axis() -> None:
    """A0923-CPM-007 · CPM · T1 (latent: no committed input starts inside a declared block).

    Claim: at 19173728, an MSPDI whose project calendar declares MS Project's Standard day
    (08:00-12:00 + 13:00-17:00, Mon-Fri) and whose ``<StartDate>`` is Monday 2025-01-06 09:00 --
    a start ADR-0312 keeps UNCHANGED (540 + 480 <= 1440) and imports with no note -- is laid out
    on a lossy axis: ``offset_to_datetime(ps, 480)`` = Mon 17:00, ``datetime_to_offset(ps, Tue
    08:30)`` = 480, the round trip ``datetime_to_offset(offset_to_datetime(k)) == k`` breaks at
    k = 450, 480, 930, ..., a 2-day task A renders its finish Tue 17:00, and the 1-elapsed-day
    successor T2 of the 60-minute T3 gets ES 0 < T3's EF 60 and finishes Tue 09:00. The oracle
    requires Tue 09:00, 450, no break, Wed 09:00, ES >= 60 and Tue 10:00. The same network on an
    08:00 start (origin 0) matches the oracle on every check -- run first, as a precondition.

    Authority: A2 -- ``src/schedule_forensics/engine/cpm.py:3-4``: "The internal time axis is
    **integer working minutes**, measured as an offset from ``Schedule.project_start``." and
    ``cpm.py:621-622``: "Inverse of :func:`datetime_to_offset` on the working-time grid";
    ``docs/adr/0523-the-project-axis-is-working-minutes-in-both-directions-r-77-closed.md:101-104``:
    "The intraday term is measured RELATIVE to the project start's own worked position. ADR-0312's
    importer precondition bounds only `start_tod + minutes_per_day <= 1440` and, inside that
    domain, `anchored_project_start` returns the start UNCHANGED — a 09:00 start on an 8-hour day
    is legal and untouched." (bold markup omitted); ADR-0312's Context table names the round
    trip ``== k`` as the invariant its precondition protects. A1 -- the file's own declared
    WorkingTimes, counted minute by minute; MSPDI ``DurationFormat`` (retrieved 2026-09-25,
    re-read 2026-09-26) at
    https://learn.microsoft.com/office-project/xml-data-interchange/durationformat-element?view=project-client-2016
    -- 5 = h, 7 = d, 8 = ed, and "Elapsed time counts all time". Hand arithmetic:
    480 from Mon 09:00 = Mon 09-12 (180) + 13-17 (240) + Tue 08-09 (60) -> Tue 09:00; Tue 08:30 =
    420 + 30 = 450; A = 960 -> Wed 09:00; T3 -> Mon 10:00, T2 = + 24 h -> Tue 10:00.

    Independence: every expected value comes from ``_a0923_cpm_007_walk`` /
    ``_a0923_cpm_007_count``, a minute-by-minute walk over the WorkingTimes this test itself
    declares; no engine or importer helper produces an expectation. Mechanism (verifier seam
    attribution): two seams -- the public pair's per-day origin clamp/saturation
    (``datetime_to_offset`` / ``offset_to_datetime``) and ``_offset_to_wall``, which reads the
    segments absolute (origin ignored) and hands the wall-path successor T2 a predecessor finish
    one origin early.
    """
    control = _a0923_cpm_007_mismatches(8)
    if control:
        pytest.fail(
            f"precondition: the 08:00 (origin 0) control disagrees with the oracle {control}"
        )
    bad = _a0923_cpm_007_mismatches(9)
    assert not bad, f"a 09:00 start inside the 08-12 block is laid out on a lossy axis: {bad}"


# --- A0923-CPM-008 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py, and on nothing else:
#   imports    datetime as dt, gzip, xml.etree.ElementTree as ET, pytest,
#              compute_cpm and offset_to_datetime (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Inputs: inline MSPDI text (built below), and the committed, non-CUI golden
# tests/fixtures/golden/fuse_ltf/Large_Test_File.mspdi.xml.gz read with gzip + ElementTree (MS
# Project's stored roll-up, the oracle). No new fixture file; nothing CUI.

#: One network row: (UID, OutlineNumber, WBS, duration hours, is summary, FS predecessor UID).
_A0923Cpm008Row = tuple[int, str, str, int, bool, int | None]


def _a0923_cpm_008_mspdi(rows: tuple[_A0923Cpm008Row, ...]) -> str:
    """An MSPDI project on MS Project's Standard calendar (Mon-Fri 08-12 / 13-17), starting
    Monday 2026-03-02 08:00; every duration is in days (DurationFormat 7), every link FS/0."""
    times = (
        "<WorkingTimes><WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime>"
        "</WorkingTime><WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime>"
        "</WorkingTime></WorkingTimes>"
    )
    days = "".join(
        f"<WeekDay><DayType>{d}</DayType><DayWorking>{int(2 <= d <= 6)}</DayWorking>"
        + (times if 2 <= d <= 6 else "")
        + "</WeekDay>"
        for d in range(1, 8)
    )
    tasks = "".join(
        f"<Task><UID>{uid}</UID><Name>T{uid}</Name><WBS>{wbs}</WBS>"
        f"<OutlineNumber>{outline}</OutlineNumber><OutlineLevel>{outline.count('.') + 1}"
        f"</OutlineLevel><Summary>{int(summary)}</Summary><Duration>PT{hours}H0M0S</Duration>"
        "<DurationFormat>7</DurationFormat>"
        + (
            f"<PredecessorLink><PredecessorUID>{pred}</PredecessorUID><Type>1</Type>"
            "<LinkLag>0</LinkLag><LagFormat>7</LagFormat></PredecessorLink>"
            if pred is not None
            else ""
        )
        + "</Task>"
        for uid, outline, wbs, hours, summary, pred in rows
    )
    return (
        '<Project xmlns="http://schemas.microsoft.com/project"><Name>summary-logic</Name>'
        "<StartDate>2026-03-02T08:00:00</StartDate><CalendarUID>1</CalendarUID>"
        "<Calendars><Calendar><UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>"
        f"<BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{days}</WeekDays></Calendar></Calendars>"
        f"<Tasks>{tasks}</Tasks></Project>"
    )


def _a0923_cpm_008_cases(wbs_follows_outline: bool) -> dict[str, tuple[_A0923Cpm008Row, ...]]:
    """Three summary-logic networks. With ``wbs_follows_outline`` the children carry MS Project's
    default WBS (= the outline number, the CONTROL); without it they carry a user-defined WBS
    that departs from the outline, as 836 committed summaries in the Large Test File family do.
    Hand-computed early starts (Standard day, 480 min):
      successor    S (1.6.2.2) = L1 1d -> L2 2d; X FS after S: S rolls up to Wed 17:00, X ES 1440.
      predecessor  P 2d -> FS -> summary S2; both children must wait: C1/C2 ES 960 (Wed).
      overlap      S3 = C1 1d + C2 3d (Wed 17:00); W 5d is NOT a child (outline 2) but its WBS
                   sits under S3's; X FS after S3 -> ES 1440 (Thu), not after W."""
    ok = wbs_follows_outline
    return {
        "successor": (
            (10, "1", "1.6.2.2", 24, True, None),
            (11, "1.1", "1.6.2.2.1" if ok else "B.OZ619.AAL.11", 8, False, None),
            (12, "1.2", "1.6.2.2.2" if ok else "B.OZ619.AAL.11", 16, False, 11),
            (13, "2", "1.6.2.3", 8, False, 10),
        ),
        "predecessor": (
            (20, "1", "1", 16, False, None),
            (21, "2", "2", 8, True, 20),
            (22, "2.1", "2.1" if ok else "Q.77", 8, False, None),
            (23, "2.2", "2.2" if ok else "Q.78", 8, False, None),
        ),
        "overlap": (
            (30, "1", "1.2", 24, True, None),
            (31, "1.1", "1.2.1", 8, False, None),
            (32, "1.2", "1.2.2" if ok else "Z.9", 24, False, None),
            (33, "2", "2" if ok else "1.2.7", 40, False, None),
            (34, "3", "3", 8, False, 30),
        ),
    }


#: Hand-computed early start of each checked leaf (working minutes from Mon 2026-03-02 08:00).
_A0923_CPM_008_WANT = {
    "successor": {13: 1440},
    "predecessor": {22: 960, 23: 960},
    "overlap": {34: 1440},
}


def _a0923_cpm_008_mismatches(wbs_follows_outline: bool) -> dict[str, str]:
    bad: dict[str, str] = {}
    for name, rows in _a0923_cpm_008_cases(wbs_follows_outline).items():
        sch = parse_mspdi_text(_a0923_cpm_008_mspdi(rows))
        kept = {t.unique_id: (t.outline_number, t.wbs, t.is_summary) for t in sch.tasks}
        written = {uid: (outline, wbs, summary) for uid, outline, wbs, _, summary, _ in rows}
        if kept != written:
            pytest.fail(f"precondition: {name}: the importer no longer keeps {written} ({kept})")
        links = {(r.predecessor_id, r.successor_id) for r in sch.relationships}
        wanted = {(pred, uid) for uid, *_, pred in rows if pred is not None}
        if links != wanted:
            pytest.fail(f"precondition: {name}: the importer's links are {links}, not {wanted}")
        res = compute_cpm(sch)
        for uid, es in _A0923_CPM_008_WANT[name].items():
            got = res.timings[uid].early_start
            if got != es:
                shown = offset_to_datetime(
                    sch.project_start, res.timings[uid].early_finish, sch.calendar
                )
                bad[f"{name}: UID {uid}"] = (
                    f"ES {got}, finish {shown:%a %Y-%m-%d %H:%M} (hand ES {es})"
                )
    return bad


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-008: logic on a summary is lowered onto its WBS-prefix leaves, not its outline "
        "children, so a summary whose children carry a user-defined WBS loses the link (X runs "
        "Mon 03-02, not Thu 03-05) or gains a spurious driver (X runs Mon 03-09) with no warning"
    ),
)
def test_a0923_cpm_008_summary_logic_follows_the_outline_children_not_the_wbs_code() -> None:
    """A0923-CPM-008 · CPM · T1 (latent: no committed file carries logic on a summary).

    Claim: at 19173728, an MSPDI in which a summary task (OutlineNumber 1, WBS '1.6.2.2') has two
    outline children (1.1 = 1d; 1.2 = 2d FS after 1.1) carrying the user-defined WBS
    'B.OZ619.AAL.11' -- the shape of the committed Large_Test_File golden's summary UID 6402 --
    and a task X (1d) linked FS from that summary yields, via parse_mspdi_text + compute_cpm
    (``engine/summary_logic.py`` ``lower_summary_relationships``), X at ES 0, finishing Mon
    2026-03-02 17:00: the link is lowered onto zero WBS-prefix leaves and silently dropped; X must
    run Thu 2026-03-05 08:00-17:00 (ES 1440). The same WBS-prefix rule also stops a predecessor on
    a summary from delaying outline children whose WBS departs from it (C1/C2 ES 0, not 960), and
    attaches a NON-child whose WBS sits under the summary's as a spurious driver (X ES 2400, Mon
    03-09, not 1440). The identical networks with MS Project's default WBS (= the outline) give the
    hand values -- run first, as a precondition.

    Authority: A1 -- MS Project's stored roll-up in the committed golden
    ``tests/fixtures/golden/fuse_ltf/Large_Test_File.mspdi.xml.gz`` (decompressed): summary UID
    6402 (line 162427) carries ``<WBS>1.6.2.2</WBS>`` (162436), ``<OutlineNumber>1.6.2.2
    </OutlineNumber>`` (162437) and ``<Finish>2024-12-27T17:00:00</Finish>`` (162441) = the
    Finish of its OUTLINE leaf UID 5652 (``<WBS>B.OZ619.AAL.11</WBS>`` 163714, ``<OutlineNumber>
    1.6.2.2.1.5</OutlineNumber>`` 163715, ``<Finish>2024-12-27T17:00:00</Finish>`` 163719); no leaf
    of that file has a WBS under '1.6.2.2.' -- re-read below as a precondition. Corpus census
    (verifier, raw ElementTree): on the 836 summaries whose WBS and outline leaf sets differ,
    stored Finish = latest outline leaf on 836/836, latest WBS-prefix leaf on 419/836. MSPDI
    schema (retrieved 2026-09-25, re-read 2026-09-26): OutlineNumber "Indicates the exact
    position of a task in the outline" at
    https://learn.microsoft.com/office-project/xml-data-interchange/outlinenumber-element?view=project-client-2016
    and WBS "By default, the WBS code is the task's outline number" (user-definable) at
    https://learn.microsoft.com/office-project/xml-data-interchange/wbs-element?view=project-client-2016
    A2 --
    ``src/schedule_forensics/engine/summary_logic.py:5-7``: "a predecessor on a summary delays
    **every child** of that summary, and a summary's successor is driven by the summary's roll-up
    **finish** (its latest child)." The decision's premise is false at HEAD:
    ``docs/adr/0043-logic-on-summary-tasks.md:34-36`` "The model carries no parent/outline field,
    so WBS is the available — and, on the reference file, correct — hierarchy signal", while
    ``model/task.py:83-86`` carries ``outline_number`` from ``<OutlineNumber>``.

    Independence: the expected starts are hand-computed from the durations and links written
    here, and the rule they encode (a summary is its outline) is MS Project's own stored
    roll-up, read from committed bytes with ElementTree -- no importer or engine code produces
    an expectation.
    """
    raw = gzip.decompress((GOLDEN / "fuse_ltf" / "Large_Test_File.mspdi.xml.gz").read_bytes())
    fields = ("OutlineNumber", "WBS", "Summary", "Finish")
    stored = {
        (el.findtext(NS + "UID") or "").strip(): {
            k: (el.findtext(NS + k) or "").strip() for k in fields
        }
        for el in ET.fromstring(raw).iter(NS + "Task")
    }
    s6402 = stored.get("6402")
    if s6402 is None or s6402["Summary"] != "1" or s6402["WBS"] != "1.6.2.2":
        pytest.fail(f"precondition: the golden's summary UID 6402 moved ({s6402})")
    leaves = [t for t in stored.values() if t["Summary"] == "0"]
    outline_leaves = [t for t in leaves if t["OutlineNumber"].startswith("1.6.2.2.")]
    wbs_leaves = [t for t in leaves if t["WBS"].startswith("1.6.2.2.")]
    latest = max((dt.datetime.fromisoformat(t["Finish"]) for t in outline_leaves), default=None)
    if wbs_leaves or latest != dt.datetime.fromisoformat(s6402["Finish"]):
        pytest.fail(
            f"precondition: MS Project's stored roll-up of UID 6402 ({s6402['Finish']}) is no "
            f"longer its latest outline leaf ({latest}) with no WBS-prefix leaf ({len(wbs_leaves)})"
        )
    control = _a0923_cpm_008_mismatches(wbs_follows_outline=True)
    if control:
        pytest.fail(
            f"precondition: with WBS = outline the lowering misses the hand values {control}"
        )
    bad = _a0923_cpm_008_mismatches(wbs_follows_outline=False)
    assert not bad, f"summary logic lowered by WBS prefix, not by the outline: {bad}"
