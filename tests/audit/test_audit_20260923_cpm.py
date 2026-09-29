"""Executable reproducers for the AUDIT-2026-09-23 findings in the CPM lane
(A0923-CPM-001..008 · session 6: A0923-CPM-010..034).

Campaign: AUDIT-2026-09-23, session 5 (WP-CPM), base 19173728 (v1.0.294). AUDIT + PLAN ONLY: the
audit changed nothing under ``src/``; these tests are the evidence a fixing PR inherits.

Session 6 (AUDIT-2026-09-23, base 13b13f38, v1.0.294; AUDIT + PLAN ONLY -- nothing under ``src/``
changed) appended A0923-CPM-010..034 below, one merged reproducer per finding in id order, under the
same conventions; each docstring names its finder id once, for provenance. Their inputs are inline
(MSPDI text or model objects) or already-committed non-CUI goldens and exports read in place; no
fixture file is added.

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
import html
import io
import json
import re
import socket
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.ai.qa import manipulation_forensics_facts
from schedule_forensics.engine.change_effects import compute_change_effects
from schedule_forensics.engine.cpm import (
    CPMError,
    compute_cpm,
    datetime_to_offset,
    offset_to_datetime,
    offset_to_start_datetime,
)
from schedule_forensics.engine.driving_path import driving_path_between
from schedule_forensics.engine.driving_slack import compute_driving_slack
from schedule_forensics.engine.path_counterfactual import compute_path_counterfactual
from schedule_forensics.engine.path_trace import ancestors_of, subschedule_to_target
from schedule_forensics.importers.json_schedule import to_json_text
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task
from schedule_forensics.web.app import SessionState, _render_counterfactual, create_app

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


# --- A0923-CPM-010 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    datetime as dt, gzip, re, xml.etree.ElementTree as ET, pytest, TestClient,
#              compute_cpm and datetime_to_offset (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi), SessionState and create_app
#              (schedule_forensics.web.app)
#   ALSO NEEDS (add to the header on merge):
#              ``import html``
#              ``from schedule_forensics.ai.qa import manipulation_forensics_facts``
#              ``from schedule_forensics.engine.change_effects import compute_change_effects``
#              ``from schedule_forensics.engine.path_counterfactual import
#              compute_path_counterfactual``
#              ``from schedule_forensics.model.relationship import Relationship``
#              ``from schedule_forensics.model.schedule import Schedule``
#              ``from schedule_forensics.model.task import Task``
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Inputs: model objects built inline (a three-activity network, nothing CUI), and the committed,
# non-CUI goldens tests/fixtures/golden/fuse_ltf/Large_Test_File.mspdi.xml.gz and
# Large_Test_File2.mspdi.xml.gz (read with gzip). No new fixture file. Runtime about 10 s (two
# Large Test File parses + CPMs dominate).

#: The hand network (default calendar: Mon-Fri, 480 working min/day; project start Mon 2026-01-05
#: 08:00). A (UID 1) -FS0-> C (UID 3) <-FS0- B (UID 2); B 8 d unstarted, C 2 d.
_A0923_CPM_010_START = dt.datetime(2026, 1, 5, 8, 0)
_A0923_CPM_010_DAY = 480
#: A's record, MS Project's shape: worked Mon-Thu (ActualDuration 4 d), Stop Thu 17:00, Resume Fri.
_A0923_CPM_010_STOP = dt.datetime(2026, 1, 8, 17, 0)
_A0923_CPM_010_RESUME = dt.datetime(2026, 1, 9, 8, 0)
#: What every surface must print for the pair (the oracle: CPM of the UNMODIFIED prior, below).
_A0923_CPM_010_WANT: dict[str, object] = {
    "engine (cf finish, delta wd, target cf, target delta wd)": ("2026-01-20", 2, "2026-01-20", 2),
    "change effects (per-change target / project min, aggregate target / project min)": (
        960,
        960,
        960,
        960,
    ),
    "/integrity counterfactual panel": True,
    "/integrity change-effects aggregate": True,
    "/evolution takeaway + target line": True,
    "Ask-the-AI counterfactual fact": True,
}


def _a0923_cpm_010_version(label: str, days: int, *, started: bool) -> Schedule:
    """One version of the hand network; A lasts ``days``. Started: A began at the project start
    and has 4 d of actual work, so -- MS Project's identity Duration = ActualDuration +
    RemainingDuration -- its RemainingDuration is ``days - 4`` and its % complete 4 / ``days``.
    Unstarted (the control twin): no actual start, no Stop / Resume, no stored remaining."""
    rem = (days - 4) * _A0923_CPM_010_DAY
    progress: dict[str, Any] = (
        {
            "actual_start": _A0923_CPM_010_START,
            "start": _A0923_CPM_010_START,
            "stop": _A0923_CPM_010_STOP,
            "resume": _A0923_CPM_010_RESUME,
            "remaining_duration_minutes": rem,
            "percent_complete": round(400 / days, 2),
        }
        if started
        else {}
    )
    return Schedule(
        name=label,
        source_file=f"{label}.xml",
        project_start=_A0923_CPM_010_START,
        status_date=_A0923_CPM_010_STOP,
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=days * _A0923_CPM_010_DAY, **progress),
            Task(unique_id=2, name="B", duration_minutes=8 * _A0923_CPM_010_DAY),
            Task(unique_id=3, name="C", duration_minutes=2 * _A0923_CPM_010_DAY),
        ),
        relationships=(
            Relationship(predecessor_id=1, successor_id=3),
            Relationship(predecessor_id=2, successor_id=3),
        ),
    )


def _a0923_cpm_010_visible(page: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))


def _a0923_cpm_010_readings(started: bool) -> dict[str, object]:
    """Every surface's reading of the counterfactual for X (A 10 d) -> Y (A cut to 7 d), target C.

    Preconditions (the hand arithmetic, checked on the engine): X: EF_A = 1920 + 2880 = 4800,
    EF_C = 5760 (Tue 2026-01-20); Y: EF_A = 1920 + 1440 = 3360 (unstarted: 0 + 3360), EF_C =
    max(3360, 3840) + 960 = 4800 (Fri 2026-01-16), TF_A = 480 > 0 -- A leaves the path without
    completing -- and the module lists exactly that duration revert."""
    x = _a0923_cpm_010_version("v1", 10, started=started)
    y = _a0923_cpm_010_version("v2", 7, started=started)
    cx, cy = compute_cpm(x), compute_cpm(y)
    got = (cx.timings[1].early_finish, cx.project_finish, cy.timings[1].early_finish)
    if got != (4800, 5760, 3360) or (cy.project_finish, cy.timings[1].total_float) != (4800, 480):
        pytest.fail(
            f"precondition (started={started}): the engine no longer reproduces the hand "
            f"arithmetic: X EF_A / finish, Y EF_A = {got}, Y finish / TF_A = "
            f"{(cy.project_finish, cy.timings[1].total_float)}"
        )
    pc = compute_path_counterfactual(x, y, cx, cy, target_uid=3)
    if pc is None or [(r.uid, r.changes) for r in pc.reverted] != [
        (1, ("duration cut 7wd → restored 10wd",))
    ]:
        pytest.fail(f"precondition (started={started}): A is no longer the one listed revert: {pc}")
    eff = compute_change_effects(x, y, cy, target_uid=3)
    if eff is None or [(e.kind, e.citation_uids) for e in eff.per_change] != [
        ("duration_restored", (1,))
    ]:
        pytest.fail(f"precondition (started={started}): the per-change list moved: {eff}")
    one = eff.per_change[0]

    client = TestClient(create_app(SessionState()))
    st = client.app.state.session  # type: ignore[attr-defined]
    st.schedules[x.source_file] = x
    st.schedules[y.source_file] = y
    st.target_uid = 3
    pages = {route: client.get(route) for route in ("/integrity", "/evolution")}
    for route, resp in pages.items():
        if resp.status_code != 200:
            pytest.fail(f"precondition (started={started}): {route} answered {resp.status_code}")
    panel = re.search(
        r'<div class="panel counterfactual">(.*?)</div>\s*(?:<div|$)',
        pages["/integrity"].text,
        re.S,
    )
    if panel is None:
        pytest.fail(
            f"precondition (started={started}): /integrity rendered no counterfactual panel"
        )
    cf_panel = _a0923_cpm_010_visible(panel.group(1))
    integrity = _a0923_cpm_010_visible(pages["/integrity"].text)
    evolution = _a0923_cpm_010_visible(pages["/evolution"].text)
    facts = [
        f.text
        for f in manipulation_forensics_facts([x, y], [cx, cy], target_uid=3)
        if f.text.startswith("Counterfactual (changes reverted)")
    ]
    if len(facts) != 1:
        pytest.fail(f"precondition (started={started}): {len(facts)} counterfactual facts")
    return {
        "engine (cf finish, delta wd, target cf, target delta wd)": (
            pc.counterfactual_finish,
            pc.finish_delta_days,
            pc.target_counterfactual_finish,
            pc.target_delta_days,
        ),
        "change effects (per-change target / project min, aggregate target / project min)": (
            one.target_finish_delta_minutes,
            one.project_finish_delta_minutes,
            eff.aggregate_target_finish_delta_minutes,
            eff.aggregate_project_finish_delta_minutes,
        ),
        "/integrity counterfactual panel": all(
            sentence in cf_panel
            for sentence in (
                "would have been 2026-01-20 instead of the reported 2026-01-16 — 2 working "
                "day(s) of apparent recovery",
                "would have finished 2026-01-20 instead of 2026-01-16 — 2 working day(s)",
            )
        ),
        "/integrity change-effects aggregate": (
            "C would move +2 working day(s) (currently 2026-01-16)" in integrity
        ),
        "/evolution takeaway + target line": all(
            sentence in evolution
            for sentence in (
                "reverting them moves the computed finish from 2026-01-16 to 2026-01-20 (+2 "
                "working day(s) later)",
                "without the changes it would finish 2026-01-20 ( +2 working day(s) later )",
            )
        ),
        "Ask-the-AI counterfactual fact": (
            "from 2026-01-16 to 2026-01-20 (+2 working day(s))" in facts[0]
        ),
    }


def _a0923_cpm_010_minutes(iso: str) -> int:
    """An MSPDI ``PT#H#M#S`` duration in whole minutes."""
    m = re.fullmatch(r"PT(\d+)H(\d+)M(\d+)S", iso)
    if m is None:
        pytest.fail(f"precondition: {iso!r} is not a PT#H#M#S duration")
    return int(m[1]) * 60 + int(m[2])


def _a0923_cpm_010_stored(raw: bytes, uid: int) -> dict[str, str]:
    """MS Project's stored progress fields of one ``<Task>`` -- ElementTree, not the importer."""
    keys = ("ActualStart", "Duration", "ActualDuration", "RemainingDuration", "PercentComplete")
    for el in ET.fromstring(raw).iter(NS + "Task"):
        if (el.findtext(NS + "UID") or "").strip() == str(uid):
            return {k: (el.findtext(NS + k) or "").strip() for k in (*keys, "Resume")}
    pytest.fail(f"precondition: the golden has no <Task> with UID {uid}")


def _a0923_cpm_010_committed_witness() -> tuple[int | None, int]:
    """(the target line's working-day move, its lower bound) for the committed golden pair
    Large_Test_File2 (prior) -> Large_Test_File (current), target UID 5539 -- the REVERSE of the
    chronological order the pages serve, so this is an engine-level witness.

    MS Project's stored UID 5539 (read with ElementTree): started in both (ActualStart
    2023-08-23), ActualDuration PT2960H held, Duration PT7980H26M -> PT3000H and
    RemainingDuration PT5020H26M -> PT40H moving together (Duration = ActualDuration +
    RemainingDuration in both files). The module lists 5539 as reverted ('duration cut 375wd ->
    restored 997.554wd'); restored with its actual held, its remaining is MS Project's own prior
    record, 301,226 min, and ADR-0517 finishes a started activity at Resume + RemainingDuration
    with the restart never before the stored Resume -- so its counterfactual early finish lies at
    least 301,226 - 2,400 = 298,826 working minutes (623 working days, rounded) after its current
    one, whatever the other 135 reverts do to its predecessors."""
    fuse_ltf = GOLDEN / "fuse_ltf"
    raws = {
        name: gzip.decompress((fuse_ltf / f"{name}.mspdi.xml.gz").read_bytes())
        for name in ("Large_Test_File2", "Large_Test_File")
    }
    prior_s = _a0923_cpm_010_stored(raws["Large_Test_File2"], 5539)
    cur_s = _a0923_cpm_010_stored(raws["Large_Test_File"], 5539)
    ident = [
        _a0923_cpm_010_minutes(s["Duration"])
        == _a0923_cpm_010_minutes(s["ActualDuration"])
        + _a0923_cpm_010_minutes(s["RemainingDuration"])
        for s in (prior_s, cur_s)
    ]
    if (
        not all(ident)
        or prior_s["ActualStart"] != cur_s["ActualStart"]
        or not cur_s["ActualStart"]
        or (prior_s["ActualDuration"], cur_s["ActualDuration"]) != ("PT2960H0M0S",) * 2
        or (prior_s["Duration"], cur_s["Duration"]) != ("PT7980H26M0S", "PT3000H0M0S")
        or float(cur_s["PercentComplete"] or 0) >= 100
    ):
        pytest.fail(
            f"precondition: MS Project's stored UID 5539 is no longer a started duration cut with "
            f"its actual held: prior {prior_s}, current {cur_s}"
        )
    prior = parse_mspdi_text(raws["Large_Test_File2"].decode("utf-8"))
    current = parse_mspdi_text(raws["Large_Test_File"].decode("utf-8"))
    p_t, c_t = prior.tasks_by_id[5539], current.tasks_by_id[5539]
    r_prior = _a0923_cpm_010_minutes(prior_s["RemainingDuration"])
    r_cur = _a0923_cpm_010_minutes(cur_s["RemainingDuration"])
    if (p_t.duration_minutes, p_t.remaining_duration_minutes, c_t.remaining_duration_minutes) != (
        _a0923_cpm_010_minutes(prior_s["Duration"]),
        r_prior,
        r_cur,
    ) or c_t.resume != dt.datetime.fromisoformat(cur_s["Resume"]):
        pytest.fail("precondition: the importer no longer reads UID 5539's stored progress")
    pcpm, ccpm = compute_cpm(prior), compute_cpm(current)
    resume_at = datetime_to_offset(current.project_start, c_t.resume, current.calendar)
    if ccpm.timings[5539].early_finish != resume_at + r_cur:
        pytest.fail(
            "precondition: the engine no longer places UID 5539 at its stored Resume + "
            f"RemainingDuration (EF {ccpm.timings[5539].early_finish}, Resume at {resume_at})"
        )
    pc = compute_path_counterfactual(prior, current, pcpm, ccpm, target_uid=5539)
    if pc is None or not any(
        r.uid == 5539 and any(c.startswith("duration cut") for c in r.changes) for r in pc.reverted
    ):
        pytest.fail("precondition: UID 5539 is no longer listed as a reverted duration change")
    per_day = current.calendar.working_minutes_per_day
    return pc.target_delta_days, round((r_prior - r_cur) / per_day)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-010: a duration revert on a STARTED activity restores duration_minutes alone, "
        "which the CPM never reads for it (Resume + stored RemainingDuration, ADR-0517), so the "
        "listed 'duration cut 7wd → restored 10wd' is inert: the counterfactual, the per-change "
        "effect and /integrity, /evolution and the Ask fact read +0 working days for +2"
    ),
)
def test_a0923_cpm_010_a_started_activitys_restored_duration_reaches_the_counterfactual() -> None:
    """A0923-CPM-010 (finder id F-PCF-001) · CPM · T1 (latent on the served figures of committed
    data; engine-level witness).

    Claim: at 13b13f38, when an activity STARTED in both versions has its duration cut the way
    MS Project records it (Duration and RemainingDuration fall together, ActualDuration held) and
    so leaves the critical path, ``compute_path_counterfactual`` lists it as reverted ('duration
    cut 7wd → restored 10wd') but restores only ``duration_minutes``
    (``engine/path_counterfactual.py:143-144``), which ``compute_cpm`` does not read for a started
    activity -- it schedules the remaining portion at the stored Resume + the stored
    RemainingDuration (``engine/cpm.py:2784-2811``; the wall path 2621-2631; ADR-0517). The
    revert is inert: on the hand pair below the counterfactual finish reads 2026-01-16 = the
    actual finish ('+0 working day(s)', 'no change') where reverting the edit must give the
    prior version's own finish, Tue 2026-01-20, +2 working days. The per-change twin
    (``engine/change_effects.py:369-370``, ADR-0162: 'restore UID 1 duration (cut 7→10 wd)') is
    the same mechanism and reads 0 / 0 min for +960 / +960; /integrity, /evolution and the
    Ask-the-AI facts print those figures. The unstarted twin (same network, same cut, no
    progress) reads +2 on every surface today -- run first, as the control.

    Exposure (verifier's narrowing, refined by the assembler's census of the 44-file corpus, 304
    ordered same-family pairs): the exact shape is listed on 27 pairs (82 reverts), none with the
    prior's status date strictly earlier. 25 are reverse chronology, which the pages never serve
    -- e.g. the goldens Large_Test_File2 -> Large_Test_File list UIDs 5539 / 6444 / 6997 and the
    target line for 5539 reads 0 working days where its own restored remaining alone moves it
    >= 623 (checked below; restoring the remaining moves the project finish 2028-09-28 ->
    2029-03-01, +109 wd -- measured, not asserted). The other 2 share a status date
    (Large_Test_File_Leveled -> the 2026-06-22 Large_Test_File save), so ``order_versions``
    serves them in load order: /integrity and /evolution list UID 5263 ('duration raised 224wd
    → restored 223.883wd', 56 working minutes), and no displayed figure moves when the revert is
    made to reach the CPM. The served figures are therefore latent on committed data; the hand
    pair shows what they print once the cut is whole days.

    Authority: A1 (metamorphic, hand-computed) -- Y = apply(X) changes exactly A's Duration,
    RemainingDuration and % complete; reverting "exactly those changes to their prior-version
    values" (``src/schedule_forensics/engine/path_counterfactual.py:10-12``: "This module
    isolates the activities that left the path **without completing** and whose own **duration
    / logic / constraints changed**, reverts exactly those changes to their prior-version values,
    re-runs CPM, and reports what the project finish (and an optional target activity's finish)
    **would have been**.") gives back X, and CPM is deterministic, so the counterfactual finish
    is CPM(X)'s: EF_A = Resume offset 1920 + Remaining 2880 = 4800, EF_C = 4800 + 960 = 5760 =
    Tue 2026-01-20; Y's is 1920 + 1440 = 3360, EF_C = max(3360, 3840) + 960 = 4800 = Fri
    2026-01-16; +960 min = +2 working days. MS Project's identity Duration = ActualDuration +
    RemainingDuration holds on 1,149 of the 1,149 started incomplete tasks carrying all three
    fields in the 44-file corpus (raw ElementTree census, finder p09 / verifier v003), and on UID
    5539 in both committed goldens (re-read below). The module names this very edit in scope,
    ``path_counterfactual.py:5-7``: "Others leave because the activity itself was **changed** --
    its remaining duration was cut, a predecessor/successor link was removed, or a hard
    constraint was dropped"; the served /evolution intro (``web/evolution.py:837-842``) says the
    same to the analyst. A2 -- ``docs/adr/0517-every-started-activitys-remaining-work-is-
    scheduled-from-its-stored-resume-read-in-working-minutes-of-the-calendars-own-segments-r-73-
    closed.md:120``: "Every started activity finishes at `Resume + RemainingDuration`".

    Independence: the expectation is CPM run on the UNMODIFIED prior X plus hand arithmetic, and
    for the committed witness a lower bound from MS Project's stored values (ElementTree) and
    ADR-0517's rule; the counterfactual modules produce no expectation. No ADR, HELD row or
    do-not-rechase item makes a started activity's duration revert inert (ADR-0513 / 0517 discuss
    the counterfactual only for the 188→187 LOGIC revert).
    """
    control = _a0923_cpm_010_readings(started=False)
    if control != _A0923_CPM_010_WANT:
        pytest.fail(
            "precondition (control): the UNSTARTED twin no longer reads the oracle on every "
            f"surface -- the harness is wrong: {control}"
        )
    started = _a0923_cpm_010_readings(started=True)
    wrong: dict[str, object] = {
        k: f"{started[k]} (oracle {v})" for k, v in _A0923_CPM_010_WANT.items() if started[k] != v
    }
    move, bound = _a0923_cpm_010_committed_witness()
    if move is None or move < bound:
        wrong["Large_Test_File2 -> Large_Test_File, target UID 5539 (engine level)"] = (
            f"target moves {move} working day(s); its restored remaining alone moves it >= {bound}"
        )
    assert not wrong, (
        "a started activity's restored duration never reaches the counterfactual CPM "
        f"(surface: reading vs oracle): {wrong}"
    )


# --- A0923-CPM-011 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    gzip, re, xml.etree.ElementTree as ET, pytest, TestClient (fastapi.testclient),
#              compute_cpm (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi),
#              SessionState and create_app (schedule_forensics.web.app)
#   ALSO NEEDS ``from schedule_forensics.model.schedule import Schedule`` on the header (a type
#              annotation of the helpers below; the style reference does not import it)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Inputs: inline MSPDI text (built below) and the committed, non-CUI goldens
# tests/fixtures/golden/fuse_hardfile/Hard_File_updated3{,_24hr}.mspdi.xml.gz. No fixture file.

_A0923_CPM_011_BLOCKS = (
    "<WorkingTimes><WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime>"
    "</WorkingTime><WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime>"
    "</WorkingTime></WorkingTimes>"
)
_A0923_CPM_011_ALL_DAY = (
    "<WorkingTimes><WorkingTime><FromTime>00:00:00</FromTime><ToTime>00:00:00</ToTime>"
    "</WorkingTime></WorkingTimes>"
)
#: 3 elapsed days (4,320 min) in MSPDI tenths of a minute; LevelingDelayFormat 8 = elapsed days.
_A0923_CPM_011_DELAY = (
    "<LevelingDelay>43200</LevelingDelay><LevelingDelayFormat>8</LevelingDelayFormat>"
)
_A0923_CPM_011_PRIOR_STATUS = "2026-01-02T17:00:00"
_A0923_CPM_011_CURRENT_STATUS = "2026-01-05T08:00:00"


def _a0923_cpm_011_calendar(uid: int, name: str, blocks: str, days: range) -> str:
    week = "".join(
        f"<WeekDay><DayType>{d}</DayType><DayWorking>{int(d in days)}</DayWorking>"
        + (blocks if d in days else "")
        + "</WeekDay>"
        for d in range(1, 8)
    )
    return (
        f"<Calendar><UID>{uid}</UID><Name>{name}</Name><IsBaseCalendar>1</IsBaseCalendar>"
        f"<BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{week}</WeekDays></Calendar>"
    )


def _a0923_cpm_011_mspdi(status: str, a_hours: int, a_extra: str = "", b_hours: int = 64) -> str:
    """Standard calendar (UID 1, Mon-Fri 08-12/13-17) plus a "24 Hours" calendar (UID 2), start
    Mon 2026-01-05 08:00. A = "Alpha leaver" (UID 1, ``a_hours`` + ``a_extra``), B = "Bravo
    chain" (UID 2, ``b_hours``), C = "Charlie finish" (UID 3, 2d) with FS0 links A->C and B->C.
    No stored Critical / TotalSlack, so the path is the engine's own."""
    link = "<Type>1</Type><LinkLag>0</LinkLag><LagFormat>7</LagFormat>"
    return (
        '<Project xmlns="http://schemas.microsoft.com/project"><Name>f-pcf-002</Name>'
        f"<StartDate>2026-01-05T08:00:00</StartDate><StatusDate>{status}</StatusDate>"
        "<CalendarUID>1</CalendarUID><Calendars>"
        + _a0923_cpm_011_calendar(1, "Standard", _A0923_CPM_011_BLOCKS, range(2, 7))
        + _a0923_cpm_011_calendar(2, "24 Hours", _A0923_CPM_011_ALL_DAY, range(1, 8))
        + "</Calendars><Tasks>"
        f"<Task><UID>1</UID><Name>Alpha leaver</Name><Duration>PT{a_hours}H0M0S</Duration>"
        f"<DurationFormat>7</DurationFormat>{a_extra}</Task>"
        f"<Task><UID>2</UID><Name>Bravo chain</Name><Duration>PT{b_hours}H0M0S</Duration>"
        "<DurationFormat>7</DurationFormat></Task>"
        "<Task><UID>3</UID><Name>Charlie finish</Name><Duration>PT16H0M0S</Duration>"
        "<DurationFormat>7</DurationFormat>"
        f"<PredecessorLink><PredecessorUID>1</PredecessorUID>{link}</PredecessorLink>"
        f"<PredecessorLink><PredecessorUID>2</PredecessorUID>{link}</PredecessorLink>"
        "</Task></Tasks></Project>"
    )


def _a0923_cpm_011_links(sch: Schedule, uid: int) -> set[tuple[int, int, str, int]]:
    return {
        (r.predecessor_id, r.successor_id, r.type.value, r.lag_minutes)
        for r in sch.relationships
        if uid in (r.predecessor_id, r.successor_id)
    }


def _a0923_cpm_011_render(
    files: list[tuple[str, bytes]],
) -> tuple[str, list[str], list[dict[str, Any]]]:
    """Upload the pair (prior first) to a fresh app; return the /evolution "What-if: work removed
    from the critical path" panel's takeaway and its paragraphs (tag-stripped), and the latest
    snapshot's ``left_rows`` from /api/evolution (the Gantt's left-reason feed)."""
    state = SessionState()
    client = TestClient(create_app(state))
    up = client.post("/upload", files=[("files", (n, b, "text/xml")) for n, b in files])
    if up.status_code != 200:
        pytest.fail(f"precondition: upload answered {up.status_code}")
    order = [s.source_file for s in state.ordered()]
    if order != [n for n, _ in files]:
        pytest.fail(f"precondition: the loaded versions are not ordered prior -> current: {order}")
    page = client.get("/evolution")
    head = page.text.find("What-if: work removed from the critical path")
    tail = page.text.find("What-if: work added to the critical path")
    if page.status_code != 200 or not 0 <= head < tail:
        pytest.fail(f"precondition: /evolution ({page.status_code}) has no removed-work panel")
    panel = page.text[head:tail]

    def visible(fragment: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment)).strip()

    take = re.search(r"<p class=sf-take[^>]*>(.*?)</p>", panel, re.S)
    if take is None:
        pytest.fail("precondition: the removed-work panel carries no takeaway line")
    paragraphs = [visible(p) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", panel, re.S)]
    api = client.get("/api/evolution")
    if api.status_code != 200:
        pytest.fail(f"precondition: /api/evolution answered {api.status_code}")
    return visible(take.group(1)), paragraphs, api.json()["snapshots"][-1]["left_rows"]


def _a0923_cpm_011_false_attribution(
    uid: int, take: str | None, paragraphs: list[str], left_rows: list[dict[str, Any]]
) -> list[str]:
    """Every place the two surfaces call ``uid`` an UNCHANGED leaver whose float a slip elsewhere
    freed. ``take`` is checked only when ``uid`` is the pair's sole leaver (it counts, not
    names)."""
    tag = f"(UID {uid})"
    said = [
        f"what-if: {p!r}"
        for p in paragraphs
        if tag in p
        and (
            p.startswith("Gained float")
            or "not because the activity itself was altered" in p
            or "freeing this one's float" in p
        )
    ]
    counted = r"\b[1-9]\d* activit(?:y|ies) left the path by gaining float"
    if take is not None and re.search(counted, take):
        said.append(f"what-if takeaway: {take!r}")
    row = next((r for r in left_rows if r.get("uid") == uid), None)
    if row is None:
        pytest.fail(f"precondition: the /evolution Gantt no longer lists UID {uid} as left")
    if row.get("reason") == "gained_float" or "Unchanged here" in str(row.get("detail")):
        said.append(f"Gantt left-reason: {row.get('reason')!r} / {row.get('detail')!r}")
    return said


def _a0923_cpm_011_raw_task(raw: bytes, uid: int, keys: tuple[str, ...]) -> dict[str, str]:
    """The stored fields of one ``<Task>`` -- read with ElementTree, not the importer."""
    for el in ET.fromstring(raw).iter(NS + "Task"):
        if (el.findtext(NS + "UID") or "").strip() == str(uid):
            return {k: (el.findtext(NS + k) or "").strip() for k in keys}
    pytest.fail(f"precondition: the golden has no <Task> with UID {uid}")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-011: an activity that leaves the critical path because its OWN leveling delay, "
        "active flag or task calendar changed is reported on /evolution as gained float -- 'left "
        "the path because a slip elsewhere lengthened another chain ... not because the activity "
        "itself was altered' and the Gantt's 'Unchanged here' -- because the leaver classifiers "
        "compare only duration, constraint and links"
    ),
)
def test_a0923_cpm_011_a_leaver_whose_own_scheduling_input_changed_is_not_called_unchanged() -> (
    None
):
    """A0923-CPM-011 (finder id F-PCF-002) · CPM · T2.

    Claim: at 13b13f38, ``engine/path_counterfactual.py:128-138`` (the /evolution "What-if: work
    removed from the critical path" panel) and ``engine/path_evolution.py:_classify_left``
    (:300-362, the /evolution Gantt's left-reason chip) decide "changed" from duration,
    constraint and (pred, succ, type[, lag]) links only; every other scheduling input the engine
    reads for the activity falls through to "gained float". So an activity that leaves the path
    because its OWN leveling delay was cleared, it was deactivated, or it was moved to another
    task calendar -- with no other activity finishing later -- is served as "left the path
    because a slip elsewhere lengthened another chain, freeing this one's float -- not because
    the activity itself was altered" / "Nothing to revert ... 1 activity left the path by gaining
    float, not by any change to itself", and the Gantt says "Unchanged here". Live on committed
    files: Project5.mpp -> Project5_FX04_TamperDuration.mpp (UID 144, stored LevelingDelay
    57600 -> 0, project finish one day EARLIER, no stored Finish later; needs MPXJ, so not
    loaded here) and the golden pair below (UID 267, stored LevelingDelay 262200 -> 0).

    Authority: A2 (the contract) -- ``docs/adr/0048-evolution-gantt-change-attribution.md:26-28``:
    "The attribution reports the **observable change to that activity**; only when the activity
    itself is unchanged does it fall back to "slip elsewhere / gained float" — honest, never
    invented."; ``docs/adr/0062-critical-path-removal-counterfactual.md:29-30``: "**Gained
    float** — the activity is **unchanged**; it left only because a slip elsewhere made another
    chain longer."; ``engine/path_counterfactual.py:57-58``: "An activity that left the path
    while UNCHANGED — float freed up elsewhere, not a change to this activity". That the three
    fields are the activity's own scheduling inputs is the engine's own rule:
    ``docs/adr/0474-resource-calendars-and-leveling-delay-in-the-base-cpm-ms-projects-stored-dates-as-the-oracle.md:41-42``
    "**Leveling delay** is elapsed time added after the plan first admits the task ... a stored
    scheduling input"; ``engine/cpm.py:307-311``
    "inactive tasks (``is_active=False``) never enter the CPM network". A1 (the committed
    witness) -- MS Project's stored values, decompressed goldens
    ``fuse_hardfile/Hard_File_updated3.mspdi.xml.gz`` UID 267 "Develop training delivery budget"
    ``<PercentComplete>0`` (line 8368), ``<LevelingDelay>262200`` (8382), ``<Critical>1`` (8353);
    ``Hard_File_updated3_24hr.mspdi.xml.gz`` ``<PercentComplete>99`` (8363),
    ``<LevelingDelay>0`` (8379), ``<Critical>0`` (8348) -- MS Project itself says 267 left the
    critical path and that its own record was edited; /evolution calls it "not ... altered".

    Oracle independence: the inline network's early finishes are hand arithmetic (A 10d = 4,800
    working minutes; B 8d = 3,840; C = max + 960), checked as preconditions, so "A left the path"
    and "nothing finished later" do not come from the classifier under test; the committed
    witness is MS Project's raw XML. Control (a precondition): a TRUE gained-float leaver (A
    untouched, B grows 8d -> 12d) must still be served with the gained-float sentence, so the
    check accepts the sentence exactly when its premise holds. Tier T2 (misattributed cause on a
    testimony surface; the what-if figure is right for its stated duration/logic/constraint
    scope, ADR-0062). Runtime about 4 s.
    """
    prior_ef = {1: 4800, 2: 3840, 3: 5760}
    variants = {
        # field changed on A: (prior MSPDI, current MSPDI, current early finishes by hand)
        "leveling_delay_minutes": (
            _a0923_cpm_011_mspdi(_A0923_CPM_011_PRIOR_STATUS, 56, _A0923_CPM_011_DELAY),
            _a0923_cpm_011_mspdi(_A0923_CPM_011_CURRENT_STATUS, 56),
            {1: 3360, 2: 3840, 3: 4800},
        ),
        "is_active": (
            _a0923_cpm_011_mspdi(_A0923_CPM_011_PRIOR_STATUS, 80),
            _a0923_cpm_011_mspdi(_A0923_CPM_011_CURRENT_STATUS, 80, "<Active>0</Active>"),
            {2: 3840, 3: 4800},
        ),
        "calendar_uid": (
            _a0923_cpm_011_mspdi(_A0923_CPM_011_PRIOR_STATUS, 80),
            _a0923_cpm_011_mspdi(_A0923_CPM_011_CURRENT_STATUS, 80, "<CalendarUID>2</CalendarUID>"),
            {1: 1860, 2: 3840, 3: 4800},  # 4,800 min of 24-hour time: Mon 08:00 -> Thu 16:00
        ),
    }
    control = (
        _a0923_cpm_011_mspdi(_A0923_CPM_011_PRIOR_STATUS, 80),
        _a0923_cpm_011_mspdi(_A0923_CPM_011_CURRENT_STATUS, 80, b_hours=96),
        {1: 4800, 2: 5760, 3: 6720},
    )

    def premise(
        name: str, prior_text: str, current_text: str, want: dict[int, int]
    ) -> tuple[str, list[str], list[dict[str, Any]]]:
        prior, current = parse_mspdi_text(prior_text), parse_mspdi_text(current_text)
        got = [
            {u: t.early_finish for u, t in compute_cpm(s).timings.items()} for s in (prior, current)
        ]
        if got != [prior_ef, want]:
            pytest.fail(f"precondition ({name}): early finishes {got} are not the hand values")
        a0, a1 = prior.tasks_by_id[1], current.tasks_by_id[1]
        own = {f for f in type(a0).model_fields if getattr(a0, f) != getattr(a1, f)}
        if own != ({name} if name != "control" else set()):
            pytest.fail(f"precondition ({name}): A's own changed fields are {sorted(own)}")
        if _a0923_cpm_011_links(prior, 1) != _a0923_cpm_011_links(current, 1) or a1.is_complete:
            pytest.fail(f"precondition ({name}): A's links moved or A completed")
        files = [(f"a0923_cpm_011_{name}_prior.xml", prior_text.encode())]
        files.append((f"a0923_cpm_011_{name}_current.xml", current_text.encode()))
        take, paragraphs, left_rows = _a0923_cpm_011_render(files)
        if [r.get("uid") for r in left_rows] != [1]:
            pytest.fail(f"precondition ({name}): the Gantt's leavers are {left_rows}, not [A]")
        return take, paragraphs, left_rows

    # control: the sentence is served, and is true, when A is untouched and B slipped
    take, paragraphs, left_rows = premise("control", *control)
    if len(_a0923_cpm_011_false_attribution(1, take, paragraphs, left_rows)) != 3:
        pytest.fail(
            f"precondition (control): a TRUE gained-float leaver is no longer served as gained "
            f"float on both surfaces: {take!r} {paragraphs} {left_rows}"
        )

    wrong: dict[str, list[str]] = {}
    for name, (prior_text, current_text, want) in variants.items():
        take, paragraphs, left_rows = premise(name, prior_text, current_text, want)
        said = _a0923_cpm_011_false_attribution(1, take, paragraphs, left_rows)
        if name != "is_active" and "no non-completed activity left the critical path" in take:
            said.append(f"what-if takeaway drops the leaver: {take!r}")
        if said:
            wrong[f"A's own {name} changed, nothing finished later"] = said

    # the committed witness: MS Project's own save pair
    names = ("Hard_File_updated3.mspdi.xml", "Hard_File_updated3_24hr.mspdi.xml")
    raws = [gzip.decompress((GOLDEN / "fuse_hardfile" / f"{n}.gz").read_bytes()) for n in names]
    keys = ("LevelingDelay", "PercentComplete", "Critical", "Duration", "ConstraintType")
    stored = [_a0923_cpm_011_raw_task(raw, 267, keys) for raw in raws]
    if [(s["LevelingDelay"], s["PercentComplete"], s["Critical"]) for s in stored] != [
        ("262200", "0", "1"),
        ("0", "99", "0"),
    ] or (stored[0]["Duration"], stored[0]["ConstraintType"]) != (
        stored[1]["Duration"],
        stored[1]["ConstraintType"],
    ):
        pytest.fail(f"precondition: MS Project's stored UID 267 fields moved: {stored}")
    _take, paragraphs, left_rows = _a0923_cpm_011_render(list(zip(names, raws, strict=True)))
    said = _a0923_cpm_011_false_attribution(267, None, paragraphs, left_rows)
    if said:
        wrong["Hard_File_updated3 -> _24hr UID 267 (stored LevelingDelay 262200 -> 0)"] = said

    assert not wrong, (
        "an activity whose own scheduling input changed is served as an UNCHANGED leaver whose "
        f"float a slip elsewhere freed: {wrong}"
    )


# --- A0923-CPM-012 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py, plus three imports it
# does not carry yet (add them to the header on merge):
#   imports    gzip, re, xml.etree.ElementTree as ET, pytest, TestClient (fastapi.testclient),
#              compute_cpm and offset_to_datetime (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi),
#              SessionState and create_app (schedule_forensics.web.app)
#   NEW        ``import html`` (stdlib),
#              ``from schedule_forensics.model import Relationship, RelationshipType, Schedule``
#              and ``_render_counterfactual`` from schedule_forensics.web.app (re-exported there)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Inputs: the committed, non-CUI goldens tests/fixtures/golden/fuse_hardfile/Hard_File_updated,
# Hard_File_updated2 and Hard_File_updated3 .mspdi.xml.gz (read with gzip). No new fixture file.

#: A sentence that tells the analyst NO schedule time was removed by change ("no schedule time
#: here was removed by change", "no time ... removed", "nothing ... removed by change"). A
#: negation must govern the time phrase itself: "no non-completed activity left the path" -- a
#: statement of what the leaver-only instrument measured -- is not a denial and does not match.
_A0923_CPM_012_DENIAL = re.compile(
    r"\b(?:no|zero)\s+(?:\w+\s+){0,2}(?:time|slip|days?)\b[^.;]*\bremoved\b"
    r"|\bnothing\s+(?:\w+\s+){0,2}removed\s+by\s+(?:a\s+|any\s+|the\s+)?changes?\b",
    re.IGNORECASE,
)


def _a0923_cpm_012_task(root: ET.Element, uid: int) -> dict[str, str]:
    """The raw stored fields of one ``<Task>`` -- read with ElementTree, not the importer."""
    keys = ("Name", "Duration", "PercentComplete", "ActualStart", "Critical")
    for el in root.iter(NS + "Task"):
        if (el.findtext(NS + "UID") or "").strip() == str(uid):
            fields = {k: (el.findtext(NS + k) or "").strip() for k in keys}
            fields["preds"] = ",".join(
                sorted(
                    f"{(pl.findtext(NS + 'PredecessorUID') or '').strip()}"
                    f":{(pl.findtext(NS + 'Type') or '').strip()}"
                    f":{(pl.findtext(NS + 'LinkLag') or '').strip()}"
                    for pl in el.findall(NS + "PredecessorLink")
                )
            )
            return fields
    pytest.fail(f"precondition: the golden has no <Task> with UID {uid}")


def _a0923_cpm_012_finish(sch: Schedule, stored_finish: str | None = None) -> int:
    """The engine's project finish (working-minute offset). With ``stored_finish`` (MS Project's
    ``<FinishDate>``), first require the unmodified solve to reproduce it -- the oracle's
    baseline is MS Project's own finish, not merely the engine's."""
    res = compute_cpm(sch)
    if stored_finish is not None:
        wall = res.project_finish_wall or offset_to_datetime(
            sch.project_start, res.project_finish, sch.calendar
        )
        if wall.isoformat() != stored_finish:
            pytest.fail(
                f"precondition: the engine's finish {wall} no longer reproduces MS Project's "
                f"stored <FinishDate> {stored_finish} -- the oracle's baseline moved"
            )
    return res.project_finish


def _a0923_cpm_012_take(prior: tuple[str, bytes], current: tuple[str, bytes]) -> str:
    """Upload the pair into ONE fresh session and return the visible text of /evolution's
    "What-if: work removed from the critical path" takeaway (the panel's sf-take headline)."""
    client = TestClient(create_app(SessionState()))
    up = client.post(
        "/upload", files=[("files", (name, raw, "text/xml")) for name, raw in (prior, current)]
    )
    if up.status_code != 200:
        pytest.fail(f"precondition: upload answered {up.status_code}")
    page = client.get("/evolution").text
    m = re.search(
        r"<h2>What-if: work removed from the critical path.*?"
        r"<p class=sf-take data-no-i18n>(.*?)</p>",
        page,
        re.S,
    )
    if m is None:
        pytest.fail("precondition: /evolution renders no 'work removed' what-if takeaway")
    pair = re.search(
        r"between <b data-no-i18n>(.*?)</b> and <b data-no-i18n>(.*?)</b>", page[m.start() :]
    )
    if pair is None or pair.groups() != (prior[0], current[0]):
        pytest.fail(
            f"precondition: the what-if panel is not the {prior[0]} -> {current[0]} pair: "
            f"{pair.groups() if pair else None}"
        )
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))).strip()


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-012: when the leaver-only path counterfactual returns None, /evolution's "
        "what-if takeaway concludes 'no schedule time here was removed by change rather than by "
        "progress', so on Hard_File_updated -> updated2 (UID 267's duration cut, +1,395 working "
        "min) and updated2 -> updated3 (removed FS 267->278, +4,320) it denies a change the "
        "engine's own per-change revert measures"
    ),
)
def test_a0923_cpm_012_the_what_if_takeaway_never_denies_a_change_the_engine_measures() -> None:
    """A0923-CPM-012 (finder id F-PCF-003) · CPM (web/evolution.py presentation of an engine
    result) · T2.

    Claim: at 13b13f38, ``/evolution``'s "What-if: work removed from the critical path" takeaway
    -- printed whenever ``compute_path_counterfactual`` returns ``None``
    (``web/evolution.py:803-808``) -- reads "Nothing to revert between the chosen pair -- no
    non-completed activity left the critical path, so no schedule time here was removed by change
    rather than by progress." on the committed golden pairs ``Hard_File_updated -> _updated2`` and
    ``_updated2 -> _updated3``. The path counterfactual examines only activities that LEFT the
    critical set (ADR-0062 decision 1), so its ``None`` cannot support the second clause: on the
    first pair unstarted UID 267's duration was cut 1,800 -> 912 min and 267 ENTERED the path
    (MS Project's stored Critical 0 -> 1); on the second the FS link 267 -> 278 was removed while
    both ends STAYED critical (ADR-0162's own 188 -> 187 case). Reverting that ONE change on the
    later file and re-running CPM moves the project finish +1,395 and +4,320 working minutes
    (+3 / +9 wd) -- the per-change counterfactual ADR-0162 defines, which ``/integrity`` prints on
    the same pair in the same session ("restore UID 267 duration ... +3 wd"; "restore removed FS
    link 267→278 ... +9 wd"). The magnitudes are engine-derived (UNVERIFIED against an MS Project
    re-schedule, which no committed file records); the claim needs only a non-zero move.

    Authority: A2 -- ``docs/adr/0162-per-change-counterfactual-effect.md:20-22``: "The existing
    **path counterfactual** (`engine/path_counterfactual.py`) only reverts activities that *left*
    the critical/driving set after their own change. UID 187 stayed critical, so the removed
    188→187 link was never reverted and its effect never measured." and ``:36-37``: "Unlike the
    path counterfactual it does **not** gate on critical-set membership, so a change whose
    endpoints stay critical (the 188→187 case) is still measured."; ``:63``: "... so neither
    surface can report \"zero effect.\""; ``src/schedule_forensics/ai/qa.py:508-510``: "the path
    counterfactual above misses changes whose endpoints stay on the critical path (e.g. a removed
    predecessor link), so the AI, given only that, previously answered \"zero effect\" when the
    real effect is non-zero." A1 (supporting, the change is not progress) -- MS Project's stored
    fields, decompressed goldens: Hard_File_updated UID 267 ``<Duration>PT30H0M0S`` (line 7340),
    ``<Critical>0`` (7350), ``<PercentComplete>0`` (7362); Hard_File_updated2 UID 267
    ``<Duration>PT15H12M0S`` (8305), ``<Critical>1`` (8315), ``<PercentComplete>0`` (8330), UID
    278 ``<PredecessorUID>267`` FS lag 0 (8437-8440), ``<FinishDate>2026-11-06T17:00:00`` (12);
    Hard_File_updated3 UIDs 267 / 278 ``<Critical>1`` (8353 / 8455), ``<PercentComplete>0``
    (8368 / 8469), 278's only predecessor now UID 298 (8485), ``<FinishDate>2026-12-12T17:00:00``
    (12).

    Oracle independence: the contradicting figure is this test's own revert (``model_copy`` of
    the later file with the one change undone, prior values read with ElementTree) through
    ``compute_cpm`` -- not ``path_counterfactual`` (whose ``None`` drives the sentence) and not
    ``change_effects``; the unmodified solve must first reproduce MS Project's stored
    ``<FinishDate>``. Census (27 committed version pairs over the 15 goldens + 29 intake MPXJ
    conversions): the path counterfactual returns ``None`` on 14; on 5 of those one change's
    revert (``change_effects``) moves the finish later -- these two golden pairs, their two MPXJ
    twins, and intake Project2 -> Project3 (UID 33, which STAYED critical); on 5 no change moves
    it (the sentence is true there); 4 have no per-change report. Served since aef25f6d (#476,
    v1.0.121, 2026-07-28).
    """
    names = ("Hard_File_updated", "Hard_File_updated2", "Hard_File_updated3")
    raw = {
        n: gzip.decompress((GOLDEN / "fuse_hardfile" / f"{n}.mspdi.xml.gz").read_bytes())
        for n in names
    }
    root = {n: ET.fromstring(raw[n]) for n in names}
    stored_finish = {n: (root[n].findtext(NS + "FinishDate") or "").strip() for n in names}
    u1, u2, u3 = names

    # Witness 1: UID 267's duration cut, on an unstarted activity that ENTERED the path.
    before, after = _a0923_cpm_012_task(root[u1], 267), _a0923_cpm_012_task(root[u2], 267)
    got = [
        (f["Duration"], f["PercentComplete"], f["ActualStart"], f["Critical"])
        for f in (before, after)
    ]
    if got != [("PT30H0M0S", "0", "", "0"), ("PT15H12M0S", "0", "", "1")]:
        pytest.fail(f"precondition: MS Project's stored UID 267 fields moved: {got}")
    sch2 = parse_mspdi_text(raw[u2].decode("utf-8"))
    t267 = sch2.tasks_by_id.get(267)
    if t267 is None or (t267.duration_minutes, t267.remaining_duration_minutes) != (912, 912):
        pytest.fail("precondition: the importer no longer reads UID 267 as 912 min, unstarted")
    base = _a0923_cpm_012_finish(sch2, stored_finish[u2])
    restored = sch2.model_copy(
        update={
            "tasks": tuple(
                t.model_copy(update={"duration_minutes": 1800, "remaining_duration_minutes": 1800})
                if t.unique_id == 267
                else t
                for t in sch2.tasks
            )
        }
    )
    moved_1 = _a0923_cpm_012_finish(restored) - base
    if moved_1 <= 0:
        pytest.fail(f"precondition: restoring UID 267's 1,800 min moves the finish {moved_1} min")

    # Witness 2: the removed FS 267 -> 278, whose ends STAYED critical (ADR-0162's 188 -> 187).
    for uid in (267, 278):
        for n in (u2, u3):
            f = _a0923_cpm_012_task(root[n], uid)
            if (f["PercentComplete"], f["ActualStart"], f["Critical"]) != ("0", "", "1"):
                pytest.fail(f"precondition: {n} UID {uid} is no longer unstarted and critical: {f}")
    if "267:1:0" not in _a0923_cpm_012_task(root[u2], 278)["preds"].split(","):
        pytest.fail(f"precondition: {u2} no longer links 267 -FS0-> 278")
    if any(p.startswith("267:") for p in _a0923_cpm_012_task(root[u3], 278)["preds"].split(",")):
        pytest.fail(f"precondition: {u3} links 267 -> 278 again")
    sch3 = parse_mspdi_text(raw[u3].decode("utf-8"))
    if any(r.predecessor_id == 267 and r.successor_id == 278 for r in sch3.relationships):
        pytest.fail("precondition: the importer reads a 267 -> 278 link on updated3")
    base = _a0923_cpm_012_finish(sch3, stored_finish[u3])
    link = Relationship(predecessor_id=267, successor_id=278, type=RelationshipType.FS)
    moved_2 = (
        _a0923_cpm_012_finish(
            sch3.model_copy(update={"relationships": (*sch3.relationships, link)})
        )
        - base
    )
    if moved_2 <= 0:
        pytest.fail(f"precondition: restoring FS 267 -> 278 moves the finish {moved_2} min")

    moved = {(u1, u2): moved_1, (u2, u3): moved_2}
    denials = {}
    for a, b in moved:
        take = _a0923_cpm_012_take((f"{a}.mspdi.xml", raw[a]), (f"{b}.mspdi.xml", raw[b]))
        if _A0923_CPM_012_DENIAL.search(take):
            denials[f"{a} -> {b} (one revert moves the finish +{moved[(a, b)]} working min)"] = take
    # The CLASS, not only these two pairs: the None branch itself (the renderer /evolution hands
    # the path counterfactual's result to) knows only that no non-completed activity left the
    # path, so it must not conclude more. Without this, a later widening of the instrument that
    # makes these two pairs non-None would XPASS while every other None pair kept the sentence.
    none_take = re.search(
        r"<p class=sf-take data-no-i18n>(.*?)</p>", _render_counterfactual(None), re.S
    )
    if none_take is None:
        pytest.fail("precondition: _render_counterfactual(None) renders no takeaway")
    none_text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", none_take.group(1))))
    if _A0923_CPM_012_DENIAL.search(none_text):
        denials["_render_counterfactual(None), the branch every None pair reaches"] = none_text
    assert not denials, (
        "/evolution's what-if takeaway tells the analyst no schedule time was removed by change on "
        f"a pair where reverting a single change moves the project finish: {denials}"
    )


# --- A0923-CPM-013 fragment -------------------------------------------------------------------
# Merge notes -- what this fragment needs from the module header of
# tests/audit/test_audit_20260923_cpm.py:
#   imports    datetime as dt, re, pytest, TestClient (fastapi.testclient),
#              compute_cpm and offset_to_datetime (schedule_forensics.engine.cpm),
#              SessionState and create_app (schedule_forensics.web.app)
#   ALSO NEEDS (not on the header today):
#              ``import html``
#              ``from schedule_forensics.importers.json_schedule import to_json_text``
#              ``from schedule_forensics.model.relationship import Relationship``
#              ``from schedule_forensics.model.schedule import Schedule``
#              ``from schedule_forensics.model.task import Task``
#   fixture    the module-level autouse _air_gapped
# Input: model objects built inline (a three-activity network on the default calendar), served
# through /upload as the tool's own Save format. No fixture file; nothing CUI.
# Runtime: about 2 s (three two-version sessions, two pages each).

#: Mon 2026-01-05 08:00 on the default calendar (Mon-Fri, one 480-minute block from 08:00).
_A0923_CPM_013_START = dt.datetime(2026, 1, 5, 8, 0)
#: (A before, A after, B) in working minutes; C = 1060 throughout. A(1) -> C(3) FS0, B(2) -> C FS0.
_A0923_CPM_013_SUBDAY = (4800, 4000, 4600)  # the witness: reverting A's cut moves C +200 min
_A0923_CPM_013_WHOLE = (4800, 4000, 4320)  # control: the same cut, a whole-day (+480 min) move
_A0923_CPM_013_ZERO = (4800, 4400, 4800)  # control: A ties B, so reverting the cut moves nothing


def _a0923_cpm_013_version(name: str, a: int, b: int) -> Schedule:
    return Schedule(
        name="f-pcf-004",
        source_file=f"{name}.json",
        project_start=_A0923_CPM_013_START,
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=a),
            Task(unique_id=2, name="B", duration_minutes=b),
            Task(unique_id=3, name="C", duration_minutes=1060),
        ),
        relationships=(
            Relationship(predecessor_id=1, successor_id=3),
            Relationship(predecessor_id=2, successor_id=3),
        ),
    )


def _a0923_cpm_013_paragraphs(page: str) -> list[str]:
    """Every ``<p>`` of a served page as the reader sees it: tags dropped, entities decoded."""
    return [
        re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", p))).strip()
        for p in re.findall(r"<p\b[^>]*>(.*?)</p>", page, re.S)
    ]


def _a0923_cpm_013_one(paragraphs: list[str], route: str, marker: str) -> str:
    hits = [p for p in paragraphs if marker in p]
    if len(hits) != 1:
        pytest.fail(f"precondition: {route} carries {len(hits)} paragraph(s) with {marker!r}")
    return hits[0]


def _a0923_cpm_013_lines(case: tuple[int, int, int]) -> dict[str, str]:
    """Upload prior (A before) then current (A after), set Target UID 3 through the served
    route, and return the four counterfactual sentences the two pages print for the pair."""
    a_before, a_after, b = case
    client = TestClient(create_app(SessionState()))
    files = [
        ("files", (f"{sch.source_file}", to_json_text(sch).encode(), "application/json"))
        for sch in (
            _a0923_cpm_013_version(f"a0923_cpm_013_{b}_{a_after}_v1", a_before, b),
            _a0923_cpm_013_version(f"a0923_cpm_013_{b}_{a_after}_v2", a_after, b),
        )
    ]
    up = client.post("/upload", files=files, follow_redirects=False)
    if up.status_code not in (200, 303):
        pytest.fail(f"precondition: /upload answered {up.status_code}")
    tgt = client.post("/target", data={"uid": "3", "next_url": "/"}, follow_redirects=False)
    if tgt.status_code != 303:
        pytest.fail(f"precondition: /target answered {tgt.status_code}")
    evolution = _a0923_cpm_013_paragraphs(client.get("/evolution").text)
    integrity = _a0923_cpm_013_paragraphs(client.get("/integrity").text)
    return {
        "/evolution takeaway": _a0923_cpm_013_one(
            evolution, "/evolution", "reverting them moves the computed finish"
        ),
        "/evolution finish": _a0923_cpm_013_one(evolution, "/evolution", "Computed finish is "),
        "/evolution target": _a0923_cpm_013_one(evolution, "/evolution", "Target activity UID 3"),
        "/integrity target": _a0923_cpm_013_one(integrity, "/integrity", "Target UID 3 (C):"),
    }


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-013: a nonzero sub-day counterfactual move (+200 working minutes; the finish "
        "date moves Tue 2026-01-20 -> Wed 2026-01-21) reads the categorical 'no change' on "
        "/evolution's what-if takeaway, finish and target lines and on /integrity's counterfactual "
        "target line, because PathCounterfactual keeps only round(minutes / day) and the renderers "
        "map 0 to 'no change'"
    ),
)
def test_a0923_cpm_013_a_sub_day_counterfactual_move_never_reads_no_change() -> None:
    """A0923-CPM-013 (finder id F-PCF-004) · CPM · T2.

    Claim: at 13b13f38, a two-version pair on the default calendar -- A(1) -> C(3) FS0,
    B(2) -> C FS0, B = 4600 and C = 1060 working minutes, A cut 4800 -> 4000 so A leaves the path
    -- served through ``/upload`` with Target UID 3 set through ``/target``, prints on
    ``/evolution`` "reverting them moves the computed finish from 2026-01-20 to 2026-01-21 (no
    change).", "Computed finish is 2026-01-20; had these 1 change(s) not been made it would be
    2026-01-21 (no change)." and "Target activity UID 3: C finishes 2026-01-20 now; without the
    changes it would finish 2026-01-21 (no change).", and on ``/integrity`` "Target UID 3 (C):
    would have finished 2026-01-21 instead of 2026-01-20 — no change on the target." -- two
    different dates beside "no change", for a +200-working-minute move. Mechanism:
    ``PathCounterfactual`` carries only ``round(delta_minutes / per_day)``
    (``engine/path_counterfactual.py:198-199``, used at :281 and :290; no minutes field), and
    ``web/evolution.py:732-741`` (``_delta_words``: ``return "no change"`` for 0, feeding the
    takeaway :828 and the body :891 / :904) and ``web/integrity.py:703-704`` (``td == 0`` ->
    " — <b>no change</b> on the target") render 0 as the categorical word. Committed exposure
    (target lines only; every committed pair's FINISH move is 0 or whole-day): the pair
    ``tests/fixtures/golden/ssi_uid152_leveled/Large_Test_File_Leveled.mspdi.xml.gz`` ->
    ``ssi_uid152/Large_Test_File.mspdi.xml.gz`` (one Project, equal StatusDate, so LOAD order
    decides; Leveled loaded first) prints "finishes 2025-06-05 now; without the changes it would
    finish 2025-06-06 (no change)" for Target UID 5271 (+165 working minutes) and the same form
    for UID 5280 (+19); loaded the other way round it prints nothing for them.

    Authority: A2 -- ``docs/adr/0366-subday-change-effects-exact-minutes.md:31-35``: "**Render
    sub-day truthfully.** `/integrity` reads the minutes: a nonzero-minutes effect that rounds to
    0 wd renders a signed `+<1 wd` / `-<1 wd` (tone by the minutes' sign); the aggregate line
    renders `+<1 working day` the same way; [...] A true zero still reads "no effect" and
    whole-day figures keep their exact legacy text." and :39-40: ``"no effect" is reserved for a
    true zero.`` ADR-0366's decision is scoped to the change-effects family (it does not name
    ``PathCounterfactual``); this finding rests on its stated principle, which the SAME
    ``/integrity`` page applies to the SAME pair (``web/integrity.py:98``: ``# a true sub-day
    effect that rounds to 0 wd — signed, never "no effect"``; :603: ``# sub-day aggregate
    (rounds to 0) — signed, never "+0 working day(s)"``). ADR-0462
    (``docs/adr/0462-integrity-counterfactual-reports-working-days-and-names-the-finish-
    activity.md:36-38``) chose "— no change on the target" for a zero working-day delta; its
    premise that a 0-working-day delta is no change is falsified by the page itself, which prints
    two different dates beside the word. A1 -- hand arithmetic on the input: current EF_C = B + C
    = 4600 + 1060 = 5660 = 11 x 480 + 380 -> Tue 2026-01-20 14:20; the reverted network is the
    prior one, EF_C = A + C = 4800 + 1060 = 5860 = 12 x 480 + 100 -> Wed 2026-01-21 09:40; the
    true move is +200 working minutes (0.42 working day) and the finish DATE moves.

    Not part of the finding: the day ROUNDING itself (half-even, ADR-0515;
    ``tests/guards/round_site_ledger.tsv:140`` classifies this site ``whole_day``) and the Ask
    fact's labelled rounded "(+0 working day(s))" (ADR-0366 "Deliberately NOT done" keeps the
    labelled rounded form). Oracle independence: the expected move is hand arithmetic on the
    input, not the counterfactual module. Controls in the same test (preconditions): the same cut
    with a whole-day move (B = 4320, +480 min) reads "+1 working day(s)"; a TRUE zero (A ties B,
    so reverting A's cut moves nothing) still reads "no change" with the same date twice.
    """
    # A1: the engine reproduces the hand arithmetic (the finding's premise)
    a_before, a_after, b = _A0923_CPM_013_SUBDAY
    prior = _a0923_cpm_013_version("a0923_cpm_013_prior", a_before, b)
    current = _a0923_cpm_013_version("a0923_cpm_013_current", a_after, b)
    ef_prior, ef_current = compute_cpm(prior).project_finish, compute_cpm(current).project_finish
    if (ef_prior, ef_current) != (5860, 5660):
        pytest.fail(
            f"precondition: CPM no longer reproduces the hand finishes (5860, 5660): "
            f"{(ef_prior, ef_current)}"
        )
    days = {
        offset_to_datetime(_A0923_CPM_013_START, m, current.calendar).date() for m in (5860, 5660)
    }
    if days != {dt.date(2026, 1, 21), dt.date(2026, 1, 20)}:
        pytest.fail(f"precondition: the two finishes no longer fall on two dates: {days}")

    # controls: a whole-day move reads its figure; a TRUE zero still reads "no change"
    for route, line in _a0923_cpm_013_lines(_A0923_CPM_013_WHOLE).items():
        want = (
            "1 working day(s) of apparent recovery"
            if route == "/integrity target"
            else "(+1 working day(s) later)"
        )
        if want not in line or "no change" in line:
            pytest.fail(f"precondition (control, +480 min): {route} reads {line!r}")
    for route, line in _a0923_cpm_013_lines(_A0923_CPM_013_ZERO).items():
        if "no change" not in line or "2026-01-20" in line or line.count("2026-01-21") != 2:
            pytest.fail(f"precondition (control, true zero): {route} reads {line!r}")

    # the witness: a nonzero sub-day move, two different dates on every line
    lines = _a0923_cpm_013_lines(_A0923_CPM_013_SUBDAY)
    for route, line in lines.items():
        if "2026-01-20" not in line or "2026-01-21" not in line:
            pytest.fail(f"precondition: {route} no longer prints both dates: {line!r}")
    sub_day = re.compile(r"<\s*1 (?:working day|wd)|less than (?:one|1) working day")
    wrong = {
        route: line
        for route, line in lines.items()
        if "no change" in line or not sub_day.search(line)
    }
    assert not wrong, (
        "a +200-working-minute counterfactual move (finish Tue 2026-01-20 -> Wed 2026-01-21) "
        "is reported as 'no change' instead of a sub-day move (<1 working day), on "
        f"{len(wrong)} of {len(lines)} surfaces: {wrong}"
    )


# --- A0923-CPM-014 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py for:
#   imports    datetime as dt, re, pytest, TestClient (fastapi.testclient),
#              compute_cpm and offset_to_datetime (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi),
#              SessionState and create_app (schedule_forensics.web.app)
#   fixture    the module-level autouse _air_gapped
#   ALSO NEEDS ``import html`` and
#              ``from schedule_forensics.ai.qa import manipulation_forensics_facts``
#              on the header (the style reference imports neither).
# Input: inline MSPDI text (built below). No fixture file; nothing CUI.

#: MS Project's Standard day, Mon-Fri 08:00-12:00 + 13:00-17:00.
_A0923_CPM_014_BLOCKS = (
    "<WorkingTimes><WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime>"
    "</WorkingTime><WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime>"
    "</WorkingTime></WorkingTimes>"
)
#: Hand arithmetic on that calendar from Mon 2026-01-05 08:00 (see the test's docstring).
_A0923_CPM_014_B_FINISH = dt.datetime(2026, 1, 9, 17, 0)  # B: 5d = 40 working hours -> Fri 17:00
_A0923_CPM_014_E_FINISH = dt.datetime(2026, 1, 10, 8, 0)  # E: 5ed = 120 elapsed hours -> Sat 08:00
_A0923_CPM_014_NAMED = re.compile(r"the network[\u2019']s last activity, UID (\d+)")


def _a0923_cpm_014_mspdi(version: str, d_hours: int, elapsed_first: bool) -> str:
    """One MSPDI version: Standard calendar, StartDate Mon 2026-01-05 08:00, no logic.
    B (UID 2) 5 working days (DurationFormat 7); E (UID 3) 5 elapsed days (DurationFormat 8);
    D (UID 4) ``d_hours`` working hours. ``elapsed_first`` puts E before B in file order -- the
    ONLY difference between the defect input and the control."""
    days = "".join(
        f"<WeekDay><DayType>{d}</DayType><DayWorking>{int(2 <= d <= 6)}</DayWorking>"
        + (_A0923_CPM_014_BLOCKS if 2 <= d <= 6 else "")
        + "</WeekDay>"
        for d in range(1, 8)
    )

    def task(uid: int, name: str, duration: str, fmt: int) -> str:
        return (
            f"<Task><UID>{uid}</UID><ID>{uid}</ID><Name>{name}</Name>"
            f"<Duration>{duration}</Duration><DurationFormat>{fmt}</DurationFormat></Task>"
        )

    b, e = task(2, "B", "PT40H0M0S", 7), task(3, "E", "PT120H0M0S", 8)
    status = "2026-01-02T17:00:00" if version == "prior" else "2026-01-05T08:00:00"
    return (
        f'<Project xmlns="http://schemas.microsoft.com/project"><Name>{version}</Name>'
        f"<StartDate>2026-01-05T08:00:00</StartDate><StatusDate>{status}</StatusDate>"
        "<CalendarUID>1</CalendarUID><Calendars><Calendar><UID>1</UID><Name>Standard</Name>"
        "<IsBaseCalendar>1</IsBaseCalendar><BaseCalendarUID>-1</BaseCalendarUID>"
        f"<WeekDays>{days}</WeekDays></Calendar></Calendars><Tasks>"
        + (e + b if elapsed_first else b + e)
        + task(4, "D", f"PT{d_hours}H0M0S", 7)
        + "</Tasks></Project>"
    )


def _a0923_cpm_014_named(elapsed_first: bool) -> dict[str, list[int]]:
    """The UID(s) each served surface names as "the network's last activity" for the pair
    prior (D = 6d, drives the finish) -> current (D cut to 4d, leaves the path)."""
    prior_xml = _a0923_cpm_014_mspdi("prior", 48, elapsed_first)
    current_xml = _a0923_cpm_014_mspdi("current", 32, elapsed_first)
    prior, current = parse_mspdi_text(prior_xml), parse_mspdi_text(current_xml)
    b, e = current.tasks_by_id[2], current.tasks_by_id[3]
    if (b.duration_minutes, b.duration_is_elapsed, e.duration_minutes, e.duration_is_elapsed) != (
        2400,
        False,
        7200,
        True,
    ):
        pytest.fail(
            "precondition: the importer no longer reads B as 5 working days and E as 5 elapsed "
            f"days ({b.duration_minutes}/{b.duration_is_elapsed}, "
            f"{e.duration_minutes}/{e.duration_is_elapsed})"
        )
    prior_cpm, cpm = compute_cpm(prior), compute_cpm(current)
    tb, te = cpm.timings[2], cpm.timings[3]
    if not tb.early_finish == te.early_finish == cpm.project_finish:
        pytest.fail(
            "precondition: B and E no longer tie at the network finish on the working-minute "
            f"axis (B {tb.early_finish}, E {te.early_finish}, finish {cpm.project_finish})"
        )
    b_finish = tb.early_finish_wall or offset_to_datetime(
        current.project_start, tb.early_finish, current.calendar
    )
    if b_finish != _A0923_CPM_014_B_FINISH:
        pytest.fail(f"precondition: B's engine finish {b_finish} is not the hand Fri 17:00")
    if (te.early_finish_wall, cpm.project_finish_wall) != (_A0923_CPM_014_E_FINISH,) * 2:
        pytest.fail(
            "precondition: the engine no longer reproduces the hand finish Sat 2026-01-10 08:00 "
            f"(E's wall {te.early_finish_wall}, project_finish_wall {cpm.project_finish_wall})"
        )

    client = TestClient(create_app(SessionState()))
    up = client.post(
        "/upload",
        files=[
            ("files", ("prior.xml", prior_xml.encode(), "text/xml")),
            ("files", ("current.xml", current_xml.encode(), "text/xml")),
        ],
    )
    if up.status_code != 200:
        pytest.fail(f"precondition: upload answered {up.status_code}")
    page = client.get("/integrity")
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page.text)))
    sentence = re.search(r"Reverting exactly those changes and re-running CPM:[^.]*", text)
    if page.status_code != 200 or sentence is None:
        pytest.fail(
            f"precondition: /integrity ({page.status_code}) no longer carries the counterfactual "
            "sentence for this pair (D's cut is no longer reverted)"
        )
    facts = [
        f.text
        for f in manipulation_forensics_facts([prior, current], [prior_cpm, cpm])
        if f.text.startswith("Counterfactual (changes reverted)")
    ]
    if len(facts) != 1:
        pytest.fail(f"precondition: expected one Ask-the-AI counterfactual fact, got {len(facts)}")
    return {
        "/integrity": [int(u) for u in _A0923_CPM_014_NAMED.findall(sentence.group(0))],
        "Ask-the-AI fact": [int(u) for u in _A0923_CPM_014_NAMED.findall(facts[0])],
    }


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-014: when two activities tie at the network finish on the working-minute axis "
        "but finish at different instants, /integrity and the Ask-the-AI counterfactual name the "
        "FIRST in file order as 'the network's last activity' (UID 2, Fri 2026-01-09 17:00) "
        "instead of the activity carrying the engine's own project_finish_wall (UID 3, Sat "
        "2026-01-10 08:00)"
    ),
)
def test_a0923_cpm_014_the_network_last_activity_is_the_one_carrying_the_engines_finish() -> None:
    """A0923-CPM-014 (finder id F-PCF-005) · CPM · T2 (latent).

    Claim: at 13b13f38, two inline MSPDI versions on MS Project's Standard calendar (Mon-Fri
    08-12/13-17, StartDate Mon 2026-01-05 08:00, no logic) -- B (UID 2, 5d), E (UID 3, 5ed), D
    (UID 4) cut from 6d (prior) to 4d (current) -- uploaded to the app make GET /integrity say
    "the project finish (the network's last activity, UID 2 “B”) would have been ...", and the
    Ask-the-AI counterfactual fact says the same, although E finishes Sat 2026-01-10 08:00, 15
    hours after B's Fri 17:00, and the engine's own ``CPMResult.project_finish_wall`` is Sat
    08:00 (E's ``early_finish_wall``). B and E tie only on the working-minute axis (early finish
    2400 each). ``engine/path_counterfactual.py:185-195`` names the FIRST task in file order
    whose axis early finish equals the network finish; swapping only B and E in the file makes
    it name UID 3. The dates the same sentence prints (the axis date, "the reported 2026-01-09")
    are A0923-CPM-001's defect and are deliberately NOT asserted here, so either fix turns only
    its own test.

    Authority: A1 -- Microsoft Learn, "DurationFormat Element",
    https://learn.microsoft.com/office-project/xml-data-interchange/durationformat-element?view=project-client-2016
    (retrieved 2026-09-28): "Elapsed time counts all time, including non-working time specified
    in the project, resource, or task calendar." and its value table "7 | d (days)", "8 | ed
    (elapsed days)". Hand arithmetic on the input's own calendar: B = 40 working hours from Mon
    08:00 -> Fri 2026-01-09 17:00; E = 120 hours of all time -> Sat 2026-01-10 08:00; D = 32
    working hours -> Thu 2026-01-08 17:00. With no logic the latest finish is E's: E is the
    network's last activity. A2 -- the engine's own contract:
    ``src/schedule_forensics/engine/cpm.py:291-293``: "The true wall-clock instant of the network
    finish when an off-calendar task's finish is not exactly representable on the project axis
    (e.g. an elapsed task ending on a weekend)."; ``cpm.py:2863-2865``: "the true latest finish
    instant. Monotonicity of the wall→offset projection means the latest-wall task is among the
    max-offset tasks"; ``cpm.py:2871-2882`` takes ``max`` of the candidates' walls, never the
    first. ``src/schedule_forensics/engine/path_counterfactual.py:84-85``: finish_uid is "The
    activity that carries the current version's project finish — the network's last early
    finish". The served label, ``web/integrity.py:687`` / ``ai/qa.py:465``: "the network's last
    activity, UID n". (ADR-0462 decision 2 calls first-in-file-order "cpm.py's own
    finish-candidate rule"; that parenthetical can be read as naming only the candidate
    CONDITION, so this test does not rest on it -- it rests on the served label.)

    Oracle independence: the expected UID comes from hand arithmetic on the input's declared
    calendar and Microsoft's elapsed-duration rule; the engine is consulted only in
    preconditions (that it reproduces those instants and that the axis ties). Control in the
    same test: the identical pair with E first in file order names UID 3 today (the harness can
    pass). Latent on the committed corpus: 0 of 44 files have a first-in-file-order candidate
    whose finish instant is earlier than ``project_finish_wall`` (25 have axis ties, all with
    equal instants).
    """
    control = _a0923_cpm_014_named(elapsed_first=True)
    if control != {"/integrity": [3], "Ask-the-AI fact": [3]}:
        pytest.fail(
            f"precondition (control): with E first in file order the surfaces no longer name "
            f"UID 3 as the network's last activity: {control}"
        )
    named = _a0923_cpm_014_named(elapsed_first=False)
    wrong = {surface: uids for surface, uids in named.items() if uids != [3]}
    assert not wrong, (
        "the activity named as 'the network's last activity' is not the one that finishes last "
        f"(E, UID 3, Sat 2026-01-10 08:00 = project_finish_wall); surface: UIDs named {wrong}"
    )


# --- A0923-CPM-015 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py for:
#   imports    datetime as dt, gzip, re, xml.etree.ElementTree as ET, pytest,
#              TestClient (fastapi.testclient),
#              compute_cpm and offset_to_datetime (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi),
#              SessionState and create_app (schedule_forensics.web.app)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
#   ALSO NEEDS ``import json`` and
#              ``from schedule_forensics.ai.qa import manipulation_forensics_facts`` and
#              ``from schedule_forensics.engine.path_counterfactual import
#              compute_path_counterfactual`` on the header (the style reference imports none).
# Inputs: inline MSPDI text (built below); the committed, non-CUI golden
# tests/fixtures/golden/fuse_hardfile/Hard_File_updated3.mspdi.xml.gz read with gzip +
# ElementTree only (never through the importer). No fixture file; nothing CUI.

#: MS Project's Standard day, Mon-Fri 08:00-12:00 + 13:00-17:00.
_A0923_CPM_015_BLOCKS = (
    "<WorkingTimes><WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime>"
    "</WorkingTime><WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime>"
    "</WorkingTime></WorkingTimes>"
)
#: The reverted-change duration phrase: "duration cut <n><unit> → restored <n><unit>".
_A0923_CPM_015_LABEL = re.compile(
    r"duration cut (\d+(?:\.\d+)?) ?([A-Za-z]+(?: days?)?) → "
    r"restored (\d+(?:\.\d+)?) ?([A-Za-z]+(?: days?)?)"
)
#: MS Project's elapsed-day unit as it may be spelled ("ed" in the MSPDI DurationFormat table,
#: "eday(s)" in the Project UI, or in words).
_A0923_CPM_015_ELAPSED_DAY = frozenset({"ed", "eday", "edays", "elapsed day", "elapsed days"})


def _a0923_cpm_015_mspdi(version: str, a_hours: int, a_format: int) -> str:
    """One MSPDI version: Standard calendar, StartDate Mon 2026-01-05 08:00. A "Cure" (UID 2,
    ``a_hours`` hours in DurationFormat ``a_format``) and B "Formwork" (UID 3, 5d) both precede
    C "Strip" (UID 4, 1d) finish-to-start, lag 0."""
    days = "".join(
        f"<WeekDay><DayType>{d}</DayType><DayWorking>{int(2 <= d <= 6)}</DayWorking>"
        + (_A0923_CPM_015_BLOCKS if 2 <= d <= 6 else "")
        + "</WeekDay>"
        for d in range(1, 8)
    )

    def task(uid: int, name: str, duration: str, fmt: int, preds: tuple[int, ...] = ()) -> str:
        links = "".join(
            f"<PredecessorLink><PredecessorUID>{p}</PredecessorUID><Type>1</Type>"
            "<LinkLag>0</LinkLag><LagFormat>7</LagFormat></PredecessorLink>"
            for p in preds
        )
        return (
            f"<Task><UID>{uid}</UID><ID>{uid}</ID><Name>{name}</Name>"
            f"<Duration>{duration}</Duration><DurationFormat>{fmt}</DurationFormat>{links}</Task>"
        )

    status = "2026-01-02T17:00:00" if version == "prior" else "2026-01-05T08:00:00"
    return (
        f'<Project xmlns="http://schemas.microsoft.com/project"><Name>{version}</Name>'
        f"<StartDate>2026-01-05T08:00:00</StartDate><StatusDate>{status}</StatusDate>"
        "<CalendarUID>1</CalendarUID><Calendars><Calendar><UID>1</UID><Name>Standard</Name>"
        "<IsBaseCalendar>1</IsBaseCalendar><BaseCalendarUID>-1</BaseCalendarUID>"
        f"<WeekDays>{days}</WeekDays></Calendar></Calendars><Tasks>"
        + task(2, "Cure", f"PT{a_hours}H0M0S", a_format)
        + task(3, "Formwork", "PT40H0M0S", 7)
        + task(4, "Strip", "PT8H0M0S", 7, preds=(2, 3))
        + "</Tasks></Project>"
    )


def _a0923_cpm_015_labels(
    a_prior_hours: int, a_current_hours: int, a_format: int, elapsed: bool
) -> dict[str, tuple[float, str, float, str]]:
    """Cut A from ``a_prior_hours`` (prior) to ``a_current_hours`` (current); A leaves the path.
    Returns each surface's parsed reverted-change duration phrase
    (current figure, unit, prior figure, unit)."""
    prior_xml = _a0923_cpm_015_mspdi("prior", a_prior_hours, a_format)
    current_xml = _a0923_cpm_015_mspdi("current", a_current_hours, a_format)
    prior, current = parse_mspdi_text(prior_xml), parse_mspdi_text(current_xml)
    a_p, a_c = prior.tasks_by_id[2], current.tasks_by_id[2]
    got = (a_p.duration_minutes, a_p.duration_is_elapsed, a_c.duration_minutes)
    got += (a_c.duration_is_elapsed,)
    if got != (a_prior_hours * 60, elapsed, a_current_hours * 60, elapsed):
        pytest.fail(
            f"precondition: the importer no longer reads A (DurationFormat {a_format}) as "
            f"{a_prior_hours}h -> {a_current_hours}h with elapsed={elapsed}: {got}"
        )
    prior_cpm, cpm = compute_cpm(prior), compute_cpm(current)
    if 2 not in prior_cpm.critical_path or 2 in cpm.critical_path:
        pytest.fail(
            f"precondition: A no longer leaves the critical path ({prior_cpm.critical_path} -> "
            f"{cpm.critical_path})"
        )
    pc = compute_path_counterfactual(prior, current, prior_cpm, cpm)
    if pc is None or [(r.uid, r.reason) for r in pc.reverted] != [(2, "duration_cut")]:
        pytest.fail(
            "precondition: the counterfactual no longer reverts exactly A's duration cut: "
            f"{None if pc is None else [(r.uid, r.reason, r.changes) for r in pc.reverted]}"
        )
    if elapsed:
        # hand arithmetic (docstring): current Strip Mon 01-12 17:00; restored Thu 01-15 17:00
        walls = tuple(
            c.project_finish_wall
            or offset_to_datetime(s.project_start, c.project_finish, s.calendar)
            for s, c in ((prior, prior_cpm), (current, cpm))
        )
        if walls != (dt.datetime(2026, 1, 15, 17), dt.datetime(2026, 1, 12, 17)):
            pytest.fail(f"precondition: the engine no longer reproduces the hand finishes {walls}")
        if pc.finish_delta_days != 3:
            pytest.fail(
                "precondition: the counterfactual finish itself moved (the claim is ONLY the "
                f"label): delta {pc.finish_delta_days} working days, hand arithmetic 3"
            )
    labels: dict[str, str] = {"engine RevertedActivity.changes": "; ".join(pc.reverted[0].changes)}

    client = TestClient(create_app(SessionState()))
    up = client.post(
        "/upload",
        files=[
            ("files", ("prior.xml", prior_xml.encode(), "text/xml")),
            ("files", ("current.xml", current_xml.encode(), "text/xml")),
        ],
    )
    if up.status_code != 200:
        pytest.fail(f"precondition: upload answered {up.status_code}")
    page = client.get("/evolution")
    blob = re.search(
        r'<script type="application/json" id=whatifData>(.*?)</script>', page.text, re.S
    )
    if page.status_code != 200 or blob is None:
        pytest.fail(f"precondition: /evolution ({page.status_code}) no longer embeds whatifData")
    rows = [r for r in json.loads(blob.group(1))["rows"] if r.get("unique_id") == 2]
    if len(rows) != 1 or rows[0].get("duration_days") != a_current_hours * 60 / (
        1440 if elapsed else 480
    ):
        pytest.fail(
            "precondition: the /evolution what-if row for UID 2 no longer prints A's current "
            f"duration in {'elapsed' if elapsed else 'working'} days in duration_days: {rows}"
        )
    labels["/evolution whatifData change_reverted"] = str(rows[0].get("change_reverted"))
    facts = [
        f.text
        for f in manipulation_forensics_facts([prior, current], [prior_cpm, cpm])
        if f.text.startswith("Counterfactual (changes reverted)")
    ]
    if len(facts) != 1:
        pytest.fail(f"precondition: expected one Ask-the-AI counterfactual fact, got {len(facts)}")
    labels["Ask-the-AI counterfactual fact"] = facts[0]

    parsed: dict[str, tuple[float, str, float, str]] = {}
    for surface, text in labels.items():
        m = _A0923_CPM_015_LABEL.search(text)
        if m is None:
            pytest.fail(
                f"precondition: {surface} no longer carries a 'duration cut .. → restored ..' "
                f"phrase (the label changed shape -- investigate): {text!r}"
            )
        parsed[surface] = (float(m.group(1)), m.group(2), float(m.group(3)), m.group(4))
    return parsed


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-015: when an elapsed-duration activity (10 ed -> 2 ed) leaves the critical "
        "path, the counterfactual's reverted-change label divides its wall-clock minutes by the "
        "project's 480-minute working day and reads 'duration cut 6wd → restored 30wd' on "
        "/evolution (whose duration_days column beside it reads 2.0) and in the Ask-the-AI fact, "
        "instead of 2 ed -> 10 ed"
    ),
)
def test_a0923_cpm_015_an_elapsed_duration_cut_is_labelled_in_elapsed_days() -> None:
    """A0923-CPM-015 (finder id F-PCF-006) · CPM · T2 (latent).

    Claim: at 13b13f38, two inline MSPDI versions on MS Project's Standard calendar (Mon-Fri
    08-12/13-17, StartDate Mon 2026-01-05 08:00) -- A "Cure" (UID 2, DurationFormat 8) and B
    "Formwork" (UID 3, 5d) both FS0 into C "Strip" (UID 4, 1d); A is PT240H (10 ed) in the prior
    and PT48H (2 ed) in the current version, so A leaves the critical path -- make
    ``compute_path_counterfactual`` label the reverted change "duration cut 6wd → restored 30wd",
    served verbatim in GET /evolution's whatifData row for UID 2 (whose own ``duration_days``
    reads 2.0) and in the Ask-the-AI "Counterfactual (changes reverted)" fact.
    ``engine/path_counterfactual.py:94-95`` (``_wd``: ``minutes / (per_day or 1)`` + "wd") is
    called at ``:146-148`` with the wall-clock minutes of an elapsed task and the PROJECT's
    working minutes per day (480), so 14,400 elapsed minutes print as "30wd". The counterfactual
    FINISH is right (precondition: +3 working days, Mon 01-12 17:00 -> Thu 01-15 17:00); only
    the change description is on the wrong axis. Same-mechanism siblings, observed on this input
    shape but NOT asserted here (a fix of this site must not be blocked by them):
    ``engine/change_effects.py:362-363`` (``_wd_text``: "restore UID 2 duration (cut 6→30 wd)")
    and ``ai/qa.py:419-426`` (10 ed -> 8 ed on the path: "'Cure' went from 30 to 24 working
    days").

    Authority: A1 -- Microsoft Learn, "DurationFormat Element",
    https://learn.microsoft.com/office-project/xml-data-interchange/durationformat-element?view=project-client-2016
    (retrieved 2026-09-28): "Elapsed time counts all time, including non-working time specified
    in the project, resource, or task calendar. For example, if the calendar specifies Saturday
    and Sunday as non-working days, a duration of 7d is seven working days such as Monday –
    Friday and the following Monday and Tuesday. A duration of 7ed is seven elapsed days, such as
    Monday – Sunday." and its value table "7 | d (days)", "8 | ed (elapsed days)". MS Project's
    own encoding of an elapsed Duration, read here with ElementTree from the committed golden
    ``tests/fixtures/golden/fuse_hardfile/Hard_File_updated3.mspdi.xml.gz`` (decompressed):
    Task UID 146 (line 15304) ``<Start>2026-12-10T17:00:00`` (15317, a Thursday),
    ``<Finish>2026-12-12T17:00:00`` (15318, a Saturday), ``<Duration>PT48H0M0S`` (15319),
    ``<DurationFormat>8`` (15320): an elapsed Duration is wall-clock hours, 48 h = 2 ed, so the
    input's PT240H / PT48H in format 8 are 10 ed / 2 ed. Hand arithmetic: 10 ed from Mon 08:00
    ends Thu 01-15 08:00, which spans 8 working days -- "30wd" is A's duration in no unit.
    A2 -- the tool's own elapsed axis: ``src/schedule_forensics/web/evolution.py:657-659``
    (the SAME whatifData row): ``"duration_days": round(t.duration_minutes / (1440 if
    t.duration_is_elapsed else per_day), 1)``; ``src/schedule_forensics/engine/metrics/
    margin.py:161``: "an elapsed margin task's minutes are wall-clock: "5 edays" is 5 days, not
    15 (QC D21)"; ``src/schedule_forensics/model/task.py:90-91``: "MS Project elapsed durations
    ("1 eday"/"2 ewks") consume wall-clock time and ignore both the task and project calendars".

    Oracle independence: the expected figures (2 and 10 elapsed days) come from Microsoft's
    definition and MS Project's stored encoding, read without the importer; the engine is
    consulted only in preconditions. Control in the same test: the identical pair in
    DurationFormat 7 (10d -> 2d, working days) labels "duration cut 2wd → restored 10wd" on every
    surface today (the harness can pass). Latent on the committed corpus: 16 elapsed activities
    in the 44-file stored-value corpus (Hard_File family UID 146 x12, always PT48H; 24Hour
    Calendar UIDs 21/33; Jacked_Up_Schedule_1 UID 20); no pair of files changes the duration of
    an activity that is elapsed in both files.
    """  # noqa: RUF002
    raw = gzip.decompress(
        (GOLDEN / "fuse_hardfile" / "Hard_File_updated3.mspdi.xml.gz").read_bytes()
    )
    el = next(
        (
            t
            for t in ET.fromstring(raw).iter(NS + "Task")
            if (t.findtext(NS + "UID") or "").strip() == "146"
        ),
        None,
    )
    if el is None:
        pytest.fail("precondition: the golden has no <Task> with UID 146")
    stored = {k: (el.findtext(NS + k) or "").strip() for k in ("DurationFormat", "Duration")}
    span = dt.datetime.fromisoformat((el.findtext(NS + "Finish") or "").strip()) - (
        dt.datetime.fromisoformat((el.findtext(NS + "Start") or "").strip())
    )
    if stored != {"DurationFormat": "8", "Duration": "PT48H0M0S"} or span != dt.timedelta(hours=48):
        pytest.fail(
            "precondition: MS Project's stored elapsed encoding moved (UID 146 is no longer "
            f"format 8, PT48H, Finish - Start = 48 h): {stored}, {span}"
        )

    control = _a0923_cpm_015_labels(80, 16, 7, elapsed=False)
    if any(v != (2.0, "wd", 10.0, "wd") for v in control.values()):
        pytest.fail(
            "precondition (control): the working-day twin 10d -> 2d is no longer labelled "
            f"'duration cut 2wd → restored 10wd' on every surface: {control}"
        )
    labels = _a0923_cpm_015_labels(240, 48, 8, elapsed=True)
    wrong = {
        surface: v
        for surface, v in labels.items()
        if not (
            v[0] == 2.0
            and v[2] == 10.0
            and v[1] in _A0923_CPM_015_ELAPSED_DAY
            and v[3] in _A0923_CPM_015_ELAPSED_DAY
        )
    }
    assert not wrong, (
        "the reverted change of an elapsed activity (10 ed -> 2 ed) is not labelled 2 -> 10 in "
        "elapsed days -- the unit MS Project and the row's own duration_days (2.0) use; "
        f"surface: (current, unit, restored, unit) {wrong}"
    )


# --- A0923-CPM-016 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    datetime as dt, gzip, xml.etree.ElementTree as ET, typing.Any, pytest, TestClient,
#              compute_cpm (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi),
#              SessionState and create_app (schedule_forensics.web.app)
#   ALSO NEEDS ``import json`` and three model imports the header does not carry:
#              from schedule_forensics.model.relationship import Relationship, RelationshipType
#              from schedule_forensics.model.schedule import Schedule
#              from schedule_forensics.model.task import ConstraintType, Task
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Inputs: hand-built model networks (below), and the committed, non-CUI golden
# tests/fixtures/golden/ssi_uid152/ (Large_Test_File.mspdi.xml.gz read with gzip + ElementTree,
# and case.json -- SSI's exported Drag column, transcribed from the committed
# 00_REFERENCE_INTAKE/ssi/Large_Test_File_UID_152_Directional_Path_Analysis_2026-7-8-8-45-50.xlsx).
# No new fixture file; nothing CUI.

#: One working day on the default Standard calendar, in working minutes.
_A0923_CPM_016_DAY = 480
#: Monday 2026-01-05 08:00 -- every hand network starts here on the default calendar.
_A0923_CPM_016_START = dt.datetime(2026, 1, 5, 8, 0)

#: A hand network: (tasks (uid, duration days, SNET = start + N CALENDAR days or None), links (pred,
#: succ, type, lag days), target uid, hand-computed target early finish in minutes, hand-computed
#: drag in days of the asserted on-path activities). UIDs 1 / 9 are the start / finish milestones.
_A0923_CPM_016_Net = tuple[
    tuple[tuple[int, int, int | None], ...],
    tuple[tuple[int, int, str, int], ...],
    int,
    int,
    dict[int, float],
]

#: The defect inputs. Hand arithmetic (drag = the target finish pull-in when the activity's
#: remaining duration is set to 0, capped by that remaining duration -- drag.py:3-4 and Devaux):
#:   GAP     S->A1(3)->A2(3)->A3(4)->T and S->C(3) FS+3d ->D(3)->T. T = 10 d. Removing any A leaves
#:           the A chain at 7 d against the C-lag-D chain's 9 d: T = 9 d, drag 1 d each. During
#:           A2's window the C-D path sits in its lag (no overlap), so the rule serves 3 d.
#:   CONSTR  S->A(5)->M(milestone, SNET Thu 01-08 08:00 = working day 3)->B(2)->T. T = 7 d.
#:           Removing A leaves M held at day 3 by its SNET: T = 5 d, drag(A) = 2 d; drag(B) = 2 d.
#:           The governing SNET milestone has a zero-length window, so the rule serves A all 5 d.
#:   SS      S->A(10) -SS+2d-> B(10)->T. T = 12 d. Removing B: T = 2 d, drag(B) = 10 d; removing A
#:           moves nothing (B still starts 2 d after A's start), drag(A) = 0. The rule caps B by
#:           its own SS predecessor A (overlapping, 0 slack) and serves 0.
#:   LEAD    S->A(10) -FS-5d-> B(10)->T. T = 15 d. Removing B: T = 5 d, drag(B) = 10 d; the rule
#:           caps B by its own lead-linked predecessor A and serves 0. (drag(A) is not asserted:
#:           its removal value depends on whether B may start before the project start.)
_A0923_CPM_016_DEFECT: dict[str, _A0923_CPM_016_Net] = {
    "GAP": (
        (
            (1, 0, None),
            (2, 3, None),
            (3, 3, None),
            (4, 4, None),
            (5, 3, None),
            (6, 3, None),
            (9, 0, None),
        ),
        (
            (1, 2, "FS", 0),
            (2, 3, "FS", 0),
            (3, 4, "FS", 0),
            (4, 9, "FS", 0),
            (1, 5, "FS", 0),
            (5, 6, "FS", 3),
            (6, 9, "FS", 0),
        ),
        9,
        10 * _A0923_CPM_016_DAY,
        {2: 1.0, 3: 1.0, 4: 1.0},
    ),
    "CONSTR": (
        ((1, 0, None), (2, 5, None), (3, 0, 3), (4, 2, None), (9, 0, None)),
        ((1, 2, "FS", 0), (2, 3, "FS", 0), (3, 4, "FS", 0), (4, 9, "FS", 0)),
        9,
        7 * _A0923_CPM_016_DAY,
        {2: 2.0, 4: 2.0},
    ),
    "SS": (
        ((1, 0, None), (2, 10, None), (3, 10, None), (9, 0, None)),
        ((1, 2, "FS", 0), (2, 3, "SS", 2), (3, 9, "FS", 0)),
        9,
        12 * _A0923_CPM_016_DAY,
        {2: 0.0, 3: 10.0},
    ),
    "LEAD": (
        ((1, 0, None), (2, 10, None), (3, 10, None), (9, 0, None)),
        ((1, 2, "FS", 0), (2, 3, "FS", -5), (3, 9, "FS", 0)),
        9,
        15 * _A0923_CPM_016_DAY,
        {3: 10.0},
    ),
}

#: The controls -- the shapes the rule was validated on (test_ssi_drag_exact, SSI UIDs 60/61):
#:   SERIAL    S->A(4)->B(6)->T: drag(A) = 4 d, drag(B) = 6 d.
#:   PARALLEL  S->A(5), S->B(5), A->C(3), B->C, C->T: removing one of A/B leaves the other
#:             governing, drag(A) = drag(B) = 0; drag(C) = 3 d.
_A0923_CPM_016_CONTROL: dict[str, _A0923_CPM_016_Net] = {
    "SERIAL": (
        ((1, 0, None), (2, 4, None), (3, 6, None), (9, 0, None)),
        ((1, 2, "FS", 0), (2, 3, "FS", 0), (3, 9, "FS", 0)),
        9,
        10 * _A0923_CPM_016_DAY,
        {2: 4.0, 3: 6.0},
    ),
    "PARALLEL": (
        ((1, 0, None), (2, 5, None), (3, 5, None), (4, 3, None), (9, 0, None)),
        ((1, 2, "FS", 0), (1, 3, "FS", 0), (2, 4, "FS", 0), (3, 4, "FS", 0), (4, 9, "FS", 0)),
        9,
        8 * _A0923_CPM_016_DAY,
        {2: 0.0, 3: 0.0, 4: 3.0},
    ),
}

#: Large_Test_File (SSI focus 152) rows the engine serves at 36.0 / 19.0 / 10.0 d; SSI: 0.5 d each.
_A0923_CPM_016_LTF_WITNESSES = (6513, 7415, 5571)


def _a0923_cpm_016_schedule(name: str, net: _A0923_CPM_016_Net) -> Schedule:
    """The hand network as model objects on the default Standard calendar (Mon-Fri, 480/day)."""
    tasks, links, *_ = net
    built = []
    for uid, days, snet_calendar_days in tasks:
        kw: dict[str, Any] = {}
        if snet_calendar_days is not None:
            kw["constraint_type"] = ConstraintType.SNET
            kw["constraint_date"] = _A0923_CPM_016_START + dt.timedelta(days=snet_calendar_days)
        built.append(
            Task(
                unique_id=uid,
                name=f"T{uid}",
                duration_minutes=days * _A0923_CPM_016_DAY,
                is_milestone=days == 0,
                **kw,
            )
        )
    rels = tuple(
        Relationship(
            predecessor_id=p,
            successor_id=s,
            type=RelationshipType(kind),
            lag_minutes=lag * _A0923_CPM_016_DAY,
        )
        for p, s, kind, lag in links
    )
    return Schedule(
        name=name, project_start=_A0923_CPM_016_START, tasks=tuple(built), relationships=rels
    )


def _a0923_cpm_016_served(client: TestClient, name: str, target: int) -> dict[int, float | None]:
    """The Path Analysis grid's data after 'Run Drag Analysis': UID -> served ``drag_days``,
    for the rows the route marks on the driving path."""
    r = client.get(f"/api/driving/{name}?target={target}&drag=1")
    if r.status_code != 200:
        pytest.fail(f"precondition: /api/driving/{name} answered {r.status_code}")
    return {
        row["unique_id"]: row["drag_days"] for row in r.json()["rows"] if row["on_driving_path"]
    }


def _a0923_cpm_016_task(root: ET.Element, uid: int) -> ET.Element:
    """The raw ``<Task>`` element with this UID -- read with ElementTree, not the importer."""
    for el in root.iter(NS + "Task"):
        if (el.findtext(NS + "UID") or "").strip() == str(uid):
            return el
    pytest.fail(f"precondition: the golden has no <Task> with UID {uid}")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-016: compute_drag (engine/drag.py:79-93) caps an on-path activity's drag by the "
        "driving slack of any other traced activity whose CPM window overlaps, not by the target "
        "finish pull-in of removing the activity that drag.py:3-4 defines, so /api/driving?drag=1 "
        "serves Large_Test_File (focus 152) UID 6513 36.0 d where SSI and the removal give 0.5 d, "
        "and an SS/lead-linked successor 0.0 d where the removal gives 10 d"
    ),
)
def test_a0923_cpm_016_drag_is_the_finish_pull_in_of_removing_the_activity() -> None:
    """A0923-CPM-016 (finder id M-DRAGRULE) · CPM · T1.

    Claim: at 13b13f38, the Path Analysis drag figure (``GET /api/driving/{name}?target=N&drag=1``
    -> ``web/driving.py:227-230`` -> ``engine/drag.py`` ``compute_drag``; the same value feeds the
    grid's "Drag (d)" column and ``/export/{fmt}/path/{name}?drag=1``) is
    min(remaining, least driving slack of any OTHER traced activity whose pure-CPM early window
    overlaps) (``drag.py:79-93``). That is not the quantity the module defines. Over-statement when
    the governor does not overlap in time: the committed golden
    ``tests/fixtures/golden/ssi_uid152/Large_Test_File.mspdi.xml.gz`` focus 152 is served UID 6513
    36.0 d, 7415 19.0 d, 5571 10.0 d -- 33 of the 76 Path-01 rows differ from SSI's exported Drag
    (0.5 d on each of the 33) -- because every upstream pull-in is stopped after 240 working
    minutes by milestone 7451's SNET (ConstraintType 4, 2026-10-02 08:00; stored Start 12:00), a
    zero-length window the loop skips (``drag.py:87-88``); hand GAP A2 3.0 d (hand 1.0 d, a
    governor in its lag), CONSTR A 5.0 d (hand 2.0 d, an SNET milestone). Under-statement when the
    overlap is the activity's own SS / lead predecessor on the same chain (no same-chain exclusion
    despite ``drag.py:17-18``): hand SS B 0.0 d and LEAD B 0.0 d (hand 10.0 d each). Census
    (verifier + assembler): 263 unit-bearing SSI Drag rows over the 8 distinct committed
    schedule/focus pairs; the engine disagrees on 100, 89 of them this rule (88 overlap-rule, 1
    same-chain -- Large_Test_File_Leveled UID 7428, 0.0 d vs SSI 0.885 d); the removal
    definition on the engine's OWN ``compute_cpm``, capped by remaining, matches SSI on 259/263
    (76/76 on this golden).

    Authority: A2 -- ``src/schedule_forensics/engine/drag.py:3-4``: "DRAG (Devaux's Removed
    Activity Gauge) answers "if this activity's remaining work vanished, how much sooner would the
    target finish?"" and ``drag.py:17-18``: "Generally: drag = min(remaining duration, minimum
    driving slack among CONCURRENT activities not on the same serial segment), where "concurrent"
    = the CPM windows overlap." A1 -- the SSI Directional Path Tool export committed at
    ``00_REFERENCE_INTAKE/ssi/Large_Test_File_UID_152_Directional_Path_Analysis_2026-7-8-8-45-50
    .xlsx`` (sheet1, header row: D "Unique ID", H "Drag"): UIDs 6513 / 7415 / 5571 "0.5 day";
    transcribed into ``tests/fixtures/golden/ssi_uid152/case.json``
    ``ssi_drag_days_by_uid_provenance_only`` (re-read cell by cell 2026-09-28: 76/76 equal).
    Public definition: "Critical path drag", https://en.wikipedia.org/wiki/Critical_path_drag
    (retrieved 2026-09-28 as search-result text; a direct fetch is egress-blocked): "the amount of
    time by which the project completion would be pulled in by reducing a critical path
    activity's duration to zero". The hand values above are that definition worked by hand.

    Held decision screened: ADR-0158 decision 4 (``docs/adr/0158-histogram-drill-vizhints-
    uid152.md:30-38``) keeps this golden's Drag column "provenance-only, deliberately NOT gated"
    on the premise "That 0.5 is the near-path slack under an SSI measurement convention the engine
    computes as 1.0 d"; ADR-0168:37-38 adds "the engine does not compute drag". Both premises are
    falsified: the engine serves 36.0 / 19.0 / 10.0 d, not 1.0 d (the assertion below); and, as a
    precondition, the engine's OWN CPM with the activity's duration set to 0 pulls focus 152 in by
    exactly 240 min (0.5 d) -- SSI's figure is the removal quantity on this very network (7451's
    SNET hold), not an unmodelled convention.

    Oracle independence: the hand expectations are arithmetic on the networks written here; the
    committed SSI export was produced by a third-party MS Project add-on; ``compute_cpm`` is used
    only in preconditions (the hand networks' base finishes, and the premise that the engine's
    network carries SSI's 0.5 d), never to produce an expectation. Controls in the same test: a
    serial chain and the parallel-pair shape of SSI UIDs 60/61 give the hand values today.
    Runtime ~7 s (the 2,126-task golden: parse ~2 s, three extra CPM passes, one traced route).
    """
    state = SessionState()
    nets = {**_A0923_CPM_016_DEFECT, **_A0923_CPM_016_CONTROL}
    for name, net in nets.items():
        sch = _a0923_cpm_016_schedule(name, net)
        base = compute_cpm(sch).timing(net[2]).early_finish
        if base != net[3]:
            pytest.fail(f"precondition: {name}'s target finishes at {base} min, not hand {net[3]}")
        state.schedules[name] = sch

    # the committed golden: MS Project's stored SNET hold on 7451 (the mechanism), read raw
    raw = gzip.decompress((GOLDEN / "ssi_uid152" / "Large_Test_File.mspdi.xml.gz").read_bytes())
    root = ET.fromstring(raw)
    fields = ("ConstraintType", "ConstraintDate", "Start", "Milestone")
    m7451 = {k: (_a0923_cpm_016_task(root, 7451).findtext(NS + k) or "").strip() for k in fields}
    if m7451 != {
        "ConstraintType": "4",
        "ConstraintDate": "2026-10-02T08:00:00",
        "Start": "2026-10-02T12:00:00",
        "Milestone": "1",
    }:
        pytest.fail(f"precondition: milestone 7451's stored SNET hold moved: {m7451}")
    preds152 = [
        tuple((pl.findtext(NS + k) or "").strip() for k in ("PredecessorUID", "Type", "LinkLag"))
        for pl in _a0923_cpm_016_task(root, 152).findall(NS + "PredecessorLink")
    ]
    if preds152 != [("7451", "1", "0")]:
        pytest.fail(f"precondition: focus 152 is no longer driven only by 7451 FS0: {preds152}")
    case = json.loads((GOLDEN / "ssi_uid152" / "case.json").read_text(encoding="utf-8"))
    ssi = {int(u): float(d) for u, d in case["ssi_drag_days_by_uid_provenance_only"].items()}
    path = set(case["driving_path_uids"])
    if case["focus_task_uid"] != 152 or set(ssi) != path or len(path) != 76:
        pytest.fail("precondition: case.json no longer records SSI's 76-row Path-01 Drag for 152")
    if any(ssi[u] != 0.5 for u in _A0923_CPM_016_LTF_WITNESSES):
        pytest.fail("precondition: SSI's exported Drag on the witnesses is no longer 0.5 d")

    ltf = parse_mspdi_text(raw.decode("utf-8"))
    cpm = compute_cpm(ltf)
    ef = cpm.timing(152).early_finish
    pulled = {
        u: ef - compute_cpm(ltf, duration_overrides={u: 0}).timing(152).early_finish
        for u in _A0923_CPM_016_LTF_WITNESSES
    }
    if pulled != {u: _A0923_CPM_016_DAY // 2 for u in _A0923_CPM_016_LTF_WITNESSES}:
        pytest.fail(
            f"precondition: removing a witness no longer pulls the engine's own focus 152 in by "
            f"SSI's 240 min (0.5 d): {pulled} -- the finding's premise moved"
        )
    state.schedules["Large_Test_File"] = ltf

    client = TestClient(create_app(state))
    wrong: dict[str, str] = {}
    for name, net in _A0923_CPM_016_CONTROL.items():
        served = _a0923_cpm_016_served(client, name, net[2])
        got = {u: served.get(u) for u in net[4]}
        if got != net[4]:
            pytest.fail(f"precondition (control): {name} serves {got}, hand {net[4]}")
    for name, net in _A0923_CPM_016_DEFECT.items():
        served = _a0923_cpm_016_served(client, name, net[2])
        if not set(net[4]) <= set(served):
            pytest.fail(f"precondition: {name}: {sorted(net[4])} not all on the driving path")
        wrong.update(
            {
                f"{name} UID {u}": f"served {served[u]} d, hand {want} d"
                for u, want in net[4].items()
                if served[u] != want
            }
        )
    served = _a0923_cpm_016_served(client, "Large_Test_File", 152)
    if set(served) != path:
        pytest.fail("precondition: the engine no longer reproduces SSI's 76-row driving path")
    wrong.update(
        {
            f"Large_Test_File/152 UID {u}": f"served {served[u]} d, SSI {ssi[u]} d"
            for u in sorted(path)
            if served[u] != ssi[u]
        }
    )
    assert not wrong, (
        f"served drag is not the target-finish pull-in of removing the activity ({len(wrong)} "
        f"rows): {wrong}"
    )


# --- A0923-CPM-017 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    datetime as dt, gzip, re, xml.etree.ElementTree as ET, pytest, TestClient,
#              compute_cpm (schedule_forensics.engine.cpm),
#              SessionState and create_app (schedule_forensics.web.app)
#   ALSO NEEDS ``import zipfile`` and four model imports the header does not carry:
#              from schedule_forensics.model.calendar import Calendar
#              from schedule_forensics.model.relationship import Relationship, RelationshipType
#              from schedule_forensics.model.schedule import Schedule
#              from schedule_forensics.model.task import Task
#   constants  REPO, GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Inputs: hand-built model networks (below); the committed, non-CUI goldens
# tests/fixtures/golden/fuse_hardfile/Hard_File{,_updated}.mspdi.xml.gz and
# tests/fixtures/golden/ssi_hardfile_24h_uid155/Hard_File_updated{3,4_24h}.mspdi.xml.gz (gzip +
# ElementTree); and the committed SSI Directional Path exports they pair with, under
# 00_REFERENCE_INTAKE/ssi/ (read with zipfile + ElementTree -- no spreadsheet library). No new
# fixture file; nothing CUI.

#: MS Project's Standard calendar (Mon-Fri 08:00-12:00 + 13:00-17:00, 480 working minutes a day).
_A0923_CPM_017_STD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))
#: MS Project's "24 Hours" base calendar: every day, 00:00-24:00.
_A0923_CPM_017_H24 = Calendar(
    uid=2,
    name="24 Hours",
    working_minutes_per_day=1440,
    work_weekdays=(0, 1, 2, 3, 4, 5, 6),
    day_segments=((0, 1440),),
)
#: Monday 2026-01-05 08:00 -- every hand network starts here.
_A0923_CPM_017_START = dt.datetime(2026, 1, 5, 8, 0)

#: Hand networks S(1) -> A(2, 1 d) -> B(3) -> T(9), FS0, on the Standard project calendar:
#: name -> (B's Task kwargs, hand T early finish (working min), hand removal pull-in of B
#: (working min), hand drag of B (days)). Hand arithmetic:
#:   EL    B = 2 elapsed days (2,880 wall minutes, MSPDI DurationFormat 8). A runs Mon 08:00-17:00;
#:         B runs Mon 17:00 -> Wed 17:00 (every wall minute counts); T = Wed 17:00 = 960 + 480 =
#:         1,440 working minutes. Without B, T = Mon 17:00 = 480. Pull-in 960 = 2.00 d.
#:   H24   B = 1,440 minutes on the "24 Hours" task calendar (one wall day). B runs Mon 17:00 ->
#:         Tue 17:00; T = 960. Without B, T = 480. Pull-in 480 = 1.00 d.
#:   WORK  (control) B = 960 working minutes (2 d) on the project calendar: Tue + Wed, T = 1,440;
#:         pull-in 960 = 2.00 d -- the engine serves this correctly today.
_A0923_CPM_017_HAND: dict[str, tuple[dict[str, Any], int, int, float]] = {
    "EL": ({"duration_minutes": 2880, "duration_is_elapsed": True}, 1440, 960, 2.0),
    "H24": ({"duration_minutes": 1440, "calendar_uid": 2}, 960, 480, 1.0),
}
_A0923_CPM_017_CONTROL: dict[str, tuple[dict[str, Any], int, int, float]] = {
    "WORK": ({"duration_minutes": 960}, 1440, 960, 2.0),
}

#: (golden, the SSI export (focus UID 155) it pairs with, {UID: SSI's Path-01 Drag cell}).
_A0923_CPM_017_SSI = (
    (
        "fuse_hardfile/Hard_File.mspdi.xml.gz",
        "Hard_File_Path_Trace_UID_155_Directional_Path_Analysis_2026-7-8-13-30-7.xlsx",
        {146: "2 days"},
    ),
    (
        "fuse_hardfile/Hard_File_updated.mspdi.xml.gz",
        "Hard_File_Path_Updated_Trace_UID_155_Directional_Path_Analysis_2026-7-8-13-30-7.xlsx",
        {146: "2 days"},
    ),
    (
        "ssi_hardfile_24h_uid155/Hard_File_updated3.mspdi.xml.gz",
        "Hard File updated3_UID_155_Directional_Path_Analysis_2026-7-15.xlsx",
        {14: "1 day", 146: "1 day"},
    ),
    (
        "ssi_hardfile_24h_uid155/Hard_File_updated4_24h.mspdi.xml.gz",
        "Hard_File_updated4 24 hour calendar_UID_155_Directional_Path_Analysis 2026-7-15.xlsx",
        {14: "1 day", 146: "2 days"},
    ),
)

#: The raw MSPDI facts that put each witness off the project axis, read with ElementTree:
#: 146 = 2 elapsed days (DurationFormat 8, "ed"); 14 = 1 day of a "24 Hours" task calendar.
_A0923_CPM_017_RAW = {
    146: {"Duration": "PT48H0M0S", "DurationFormat": "8", "RemainingDuration": "PT48H0M0S"},
    14: {"Duration": "PT24H0M0S", "DurationFormat": "7", "RemainingDuration": "PT24H0M0S"},
}

_A0923_CPM_017_XL = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _a0923_cpm_017_hand(name: str, b: dict[str, Any]) -> Schedule:
    """S -> A(1 d) -> B -> T on the Standard project calendar, the 24-hour calendar available."""
    tasks = (
        Task(unique_id=1, name="S", duration_minutes=0, is_milestone=True),
        Task(unique_id=2, name="A", duration_minutes=480),
        Task(unique_id=3, name="B", **b),
        Task(unique_id=9, name="T", duration_minutes=0, is_milestone=True),
    )
    rels = tuple(
        Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS)
        for p, s in ((1, 2), (2, 3), (3, 9))
    )
    return Schedule(
        name=name,
        project_start=_A0923_CPM_017_START,
        calendar=_A0923_CPM_017_STD,
        calendars=(_A0923_CPM_017_STD, _A0923_CPM_017_H24),
        tasks=tasks,
        relationships=rels,
    )


def _a0923_cpm_017_pull_in(sch: Schedule, uid: int, target: int) -> int:
    """How much sooner the target finishes (working minutes) when ``uid``'s duration is 0, on the
    engine's own CPM -- drag.py:3-4's question, asked of the network directly."""
    base = compute_cpm(sch).timing(target).early_finish
    return base - compute_cpm(sch, duration_overrides={uid: 0}).timing(target).early_finish


def _a0923_cpm_017_ssi_cells(path: Path) -> dict[int, tuple[str, str]]:
    """UID -> (Trace Log Value, Drag) from SSI's export, sheet1, located by its header row."""
    if not path.is_file():
        pytest.fail(f"precondition: the committed SSI export {path.name} is missing")
    with zipfile.ZipFile(path) as z:
        shared = [
            "".join(t.text or "" for t in si.iter(_A0923_CPM_017_XL + "t"))
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(_A0923_CPM_017_XL + "si")
        ]
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    table: list[dict[str, str]] = []
    for row in sheet.iter(_A0923_CPM_017_XL + "row"):
        cells: dict[str, str] = {}
        for c in row.iter(_A0923_CPM_017_XL + "c"):
            v = c.findtext(_A0923_CPM_017_XL + "v")
            if v is None:
                continue
            col = re.match(r"[A-Z]+", c.get("r") or "")
            if col is None:
                pytest.fail(f"precondition: {path.name} has a cell without a reference")
            cells[col.group(0)] = shared[int(v)] if c.get("t") == "s" else v
        table.append(cells)
    head = {v: k for k, v in table[0].items()} if table else {}
    if not {"Unique ID", "Drag", "Trace Log Value"} <= set(head):
        pytest.fail(f"precondition: {path.name}'s header row moved: {sorted(head)}")
    return {
        int(r[head["Unique ID"]]): (r.get(head["Trace Log Value"], ""), r.get(head["Drag"], ""))
        for r in table[1:]
        if r.get(head["Unique ID"], "").isdigit()
    }


def _a0923_cpm_017_days(cell: str) -> float:
    m = re.fullmatch(r"(\d+(?:\.\d+)?) days?", cell)
    if m is None:
        pytest.fail(f"precondition: SSI Drag cell {cell!r} carries no day unit")
    return float(m.group(1))


def _a0923_cpm_017_raw_task(root: ET.Element, uid: int) -> ET.Element:
    """The raw ``<Task>`` element with this UID -- read with ElementTree, not the importer."""
    for el in root.iter(NS + "Task"):
        if (el.findtext(NS + "UID") or "").strip() == str(uid):
            return el
    pytest.fail(f"precondition: the golden has no <Task> with UID {uid}")


def _a0923_cpm_017_rows(client: TestClient, name: str, target: int) -> dict[int, dict[str, Any]]:
    """The Path Analysis grid's rows after 'Run Drag Analysis' (``drag_days`` = "Drag (d)",
    ``duration_days`` = "Duration (d)")."""
    r = client.get(f"/api/driving/{name}?target={target}&drag=1")
    if r.status_code != 200:
        pytest.fail(f"precondition: /api/driving/{name} answered {r.status_code}")
    return {row["unique_id"]: row for row in r.json()["rows"]}


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-017: compute_drag (engine/drag.py:48-54, 76-77, 99) serves an on-path "
        "activity's remaining duration in the task's OWN unit over 480, so a 2-elapsed-day "
        "activity is served Drag 6.0 d and a 1-day activity on a 24-hour calendar 3.0 d where SSI "
        "and the removal pull-in give 2.0 d / 1.0 d (Hard_File UID 146; Hard_File_updated3/4 UID "
        "14)"
    ),
)
def test_a0923_cpm_017_drag_counts_project_working_time_not_the_tasks_own_duration_unit() -> None:
    """A0923-CPM-017 (finder id F-DRAG-003) · CPM · T1.

    Claim: at 13b13f38, the Path Analysis drag figure (``GET /api/driving/{name}?target=N&drag=1``
    -> ``web/driving.py:227-230`` -> ``engine/drag.py`` ``compute_drag``; the same value feeds the
    grid's "Drag (d)" column and ``/export/{fmt}/path/{name}?drag=1``) starts from the activity's
    ``remaining_duration_minutes`` (``drag.py:48-54``, taken as the drag at ``:76-77``) and prints
    it over 480 (``:99``), with no ``duration_is_elapsed`` and no task-calendar branch. Those
    minutes are in the task's OWN duration unit: wall minutes for an elapsed duration, minutes of
    its own calendar for a task calendar. So a 2-elapsed-day activity (2,880 wall minutes) is
    served 6.0 d and a 1-day activity on a "24 Hours" task calendar (1,440 of its minutes, one
    wall day) 3.0 d. Witnesses (focus 155): Hard_File and Hard_File_updated UID 146 served 6.0 d
    beside its own Duration (d) 2.0, SSI "2 days"; Hard_File_updated3 UID 14 served 3.0 d and 146
    6.0 d, SSI "1 day" each; Hard_File_updated4_24h UID 14 served 3.0 d and 146 6.0 d, SSI
    "1 day" / "2 days". Hand S->A(1 d)->B(2 ed)->T: B served 6.0 d beside Duration (d) 2.0, hand
    2.0 d; the same network with B = 1,440 minutes on a 24-hour task calendar: served 3.0 d, hand
    1.0 d. (For the 24-hour-calendar rows the page's own Duration column also reads 3.0, so the
    row's self-contradiction is visible on the elapsed rows only; the wrong figure is the drag.)
    Census (assembler, re-derived): over the 8 committed SSI export/golden pairs, 263 SSI Path-01
    Drag cells carry a day unit; 8 of them belong to an activity whose duration is elapsed or on
    a task calendar whose working pattern differs from the project's; the engine serves a value
    different from SSI's on all 8; the six asserted below are the ones where the removal pull-in
    on the engine's own CPM equals SSI (the seventh, Hard_File_updated4_24h UID 302, a 99%-complete
    24-hour-calendar task served 0.05 d for SSI's 0, moves with the same fix; the eighth, UID 389,
    served 1.0 d for SSI's 0, is not explained by the unit and is not asserted). Corpus (44
    files, 22,105 scheduled activities): 16 elapsed activities and 39 on a 930- or 1,440-minute
    task calendar, in 15 files -- every Hard_File-family save, 24Hour_Calendar and
    Jacked_Up_Schedule_1. (A further 1,523 Large_Test_File-family activities sit on 480-minute
    task calendars of another pattern; the fix sketch moves none of their served drag at 152.)

    Authority: A1 -- the SSI Directional Path Tool exports committed under
    ``00_REFERENCE_INTAKE/ssi/`` (sheet1, header row: D "Unique ID", H "Drag", I "Trace Log
    Value"): ``Hard_File_Path_Trace_UID_155_Directional_Path_Analysis_2026-7-8-13-30-7.xlsx`` H89
    (UID 146, Path 01) "2 days"; ``Hard_File_Path_Updated_Trace_UID_155_..._2026-7-8-13-30-7
    .xlsx`` H85 (146) "2 days"; ``Hard File updated3_UID_155_Directional_Path_Analysis_2026-7-15
    .xlsx`` H92 (14) "1 day", H99 (146) "1 day"; ``Hard_File_updated4 24 hour calendar_UID_155_
    Directional_Path_Analysis 2026-7-15.xlsx`` H92 (14) "1 day", H99 (146) "2 days". The MSPDI
    schema, "DurationFormat Element",
    https://learn.microsoft.com/office-project/xml-data-interchange/durationformat-element?view=project-client-2016
    (retrieved 2026-09-28): "8 | ed (elapsed days)" and "Elapsed time counts all time, including
    non-working time specified in the project, resource, or task calendar." Hand arithmetic: the
    networks above (``_A0923_CPM_017_HAND``). A2 -- ``src/schedule_forensics/engine/drag.py:3-4``:
    "DRAG (Devaux's Removed Activity Gauge) answers "if this activity's remaining work vanished,
    how much sooner would the target finish?""; ``drag.py:12-13``: "A path activity's drag is
    capped by its **remaining** working duration"; ``docs/adr/0310-two-time-axes-and-the-labels-
    that-confuse-them.md:67-68``: "3. **An elapsed duration is measured on a 1440-minute day**,
    always, and the discriminator is `Task.duration_is_elapsed`. Any code converting a duration to
    days must branch on it." -- which ``web/driving.py:303-306`` (the same row's Duration column)
    does and ``drag.py:99`` does not.

    Held decisions screened: ADR-0516 decision 3 (the tool's own displays keep the PROJECT day as
    divisor) is not in conflict -- every project day here is 480 and the defect is the minutes
    (2,880 wall minutes used as 2,880 working minutes), not the divisor; ADR-0158:30 / ADR-0168:37
    ("the engine does not compute drag") rest on a premise the served figure falsifies; the
    "elapsed durations ... (exact)" do-not-re-chase entry measured CPM dates, which stay exact
    (the removal pull-in below is computed on them). Not a duplicate of A0923-IMP-006 (the
    importer's elapsed LINK lag -- a different field and module).

    Oracle independence: the SSI cells were produced by a third-party MS Project add-on and are read
    here with zipfile + ElementTree; the elapsed / 24-hour facts are MS Project's own stored
    fields read with ElementTree, not the importer; the hand values are arithmetic on the networks
    written here. ``compute_cpm`` is used only in preconditions -- the hand networks' finishes,
    and the premise that the engine's own network carries SSI's figure (its removal pull-in
    equals SSI on every witness) -- never to produce an expectation. Control in the same test: B
    as 2 WORKING days is served 2.0 d today. Runtime ~3 s (four ~400-task goldens uploaded and
    traced, twelve extra CPM passes).
    """
    state = SessionState()
    for name, (b, finish, pull_in, _want) in {
        **_A0923_CPM_017_HAND,
        **_A0923_CPM_017_CONTROL,
    }.items():
        sch = _a0923_cpm_017_hand(name, b)
        got = (compute_cpm(sch).timing(9).early_finish, _a0923_cpm_017_pull_in(sch, 3, 9))
        if got != (finish, pull_in):
            pytest.fail(
                f"precondition: {name} (T finish, B pull-in) = {got}, hand {(finish, pull_in)}"
            )
        state.schedules[name] = sch
    client = TestClient(create_app(state))
    for name, (_b, _f, _p, want) in _A0923_CPM_017_CONTROL.items():
        rows = _a0923_cpm_017_rows(client, name, 9)
        got_c = (rows[3]["drag_days"], rows[2]["drag_days"], rows[3]["duration_days"])
        if got_c != (want, 1.0, want):
            pytest.fail(f"precondition (control): {name} serves (B, A, B duration) = {got_c}")

    wrong: dict[str, str] = {}
    for name, (_b, _f, _p, want) in _A0923_CPM_017_HAND.items():
        rows = _a0923_cpm_017_rows(client, name, 9)
        if not rows.get(3, {}).get("on_driving_path"):
            pytest.fail(f"precondition: hand {name}'s B is not on the driving path")
        if name == "EL" and rows[3]["duration_days"] != 2.0:
            pytest.fail(
                f"precondition: the grid's Duration (d) for elapsed B is not 2.0: {rows[3]}"
            )
        if rows[3]["drag_days"] != want:
            wrong[f"hand {name} B"] = (
                f"served {rows[3]['drag_days']} d (Duration (d) {rows[3]['duration_days']}), "
                f"hand {want} d"
            )

    for golden, export, cells in _A0923_CPM_017_SSI:
        raw = gzip.decompress((GOLDEN / golden).read_bytes())
        root = ET.fromstring(raw)
        project_cal = (root.findtext(NS + "CalendarUID") or "").strip()
        cal_names = {
            (c.findtext(NS + "UID") or "").strip(): (c.findtext(NS + "Name") or "").strip()
            for c in root.iter(NS + "Calendar")
        }
        for uid in cells:
            el = _a0923_cpm_017_raw_task(root, uid)
            fields = {k: (el.findtext(NS + k) or "").strip() for k in _A0923_CPM_017_RAW[uid]}
            if fields != _A0923_CPM_017_RAW[uid]:
                pytest.fail(f"precondition: {golden} UID {uid}'s stored duration moved: {fields}")
            cal_uid = (el.findtext(NS + "CalendarUID") or "").strip()
            if uid == 14 and (cal_names.get(cal_uid) != "24 Hours" or cal_uid == project_cal):
                pytest.fail(f"precondition: {golden} UID 14 is no longer on a 24 Hours calendar")
            if uid == 146:
                span = dt.datetime.fromisoformat(
                    (el.findtext(NS + "Finish") or "").strip()
                ) - dt.datetime.fromisoformat((el.findtext(NS + "Start") or "").strip())
                if span != dt.timedelta(hours=48):
                    pytest.fail(f"precondition: {golden} UID 146 no longer spans 48 wall hours")
        ssi = _a0923_cpm_017_ssi_cells(REPO / "00_REFERENCE_INTAKE" / "ssi" / export)
        if {u: ssi.get(u) for u in cells} != {u: ("Path 01", c) for u, c in cells.items()}:
            got_cells = {u: ssi.get(u) for u in cells}
            pytest.fail(f"precondition: {export}'s Path-01 Drag cells moved: {got_cells}")

        before = set(state.schedules)
        up = client.post("/upload", files={"files": (Path(golden).name[:-3], raw, "text/xml")})
        added = set(state.schedules) - before
        if up.status_code != 200 or len(added) != 1:
            pytest.fail(f"precondition: uploading {golden} answered {up.status_code}, {added}")
        name = added.pop()
        sch = state.schedules[name]
        pulled = {u: _a0923_cpm_017_pull_in(sch, u, 155) for u in cells}
        want_min = {u: round(_a0923_cpm_017_days(c) * 480) for u, c in cells.items()}
        if pulled != want_min:
            pytest.fail(
                f"precondition: on {golden}, removing a witness no longer pulls the engine's own "
                f"focus 155 in by SSI's figure: {pulled} vs {want_min} -- the premise moved"
            )
        rows = _a0923_cpm_017_rows(client, name, 155)
        for uid, cell in cells.items():
            row = rows.get(uid)
            if row is None or not row["on_driving_path"]:
                pytest.fail(f"precondition: {golden} UID {uid} is not on the traced driving path")
            if row["drag_days"] != _a0923_cpm_017_days(cell):
                wrong[f"{name} UID {uid}"] = (
                    f"served {row['drag_days']} d (Duration (d) {row['duration_days']}), "
                    f"SSI {cell!r}"
                )
    assert not wrong, (
        f"served drag reads an elapsed / own-calendar duration as project working minutes "
        f"({len(wrong)} rows): {wrong}"
    )


# --- A0923-CPM-018 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    re, xml.etree.ElementTree as ET, pytest, TestClient (fastapi.testclient),
#              compute_cpm (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi),
#              SessionState and create_app (schedule_forensics.web.app)
#   ALSO NEEDS ``import html`` on the header (standard library; the committed header lacks it)
#   constants  REPO (the repository root), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Input: the committed, synthetic, non-CUI tests/fixtures/test_projects/TP2_Bridge_4x10_Calendar.xml
# (byte-identical to 00_REFERENCE_INTAKE/references/TP2_Bridge_4x10_Calendar.xml), used as it
# stands and with ONE inline element edit (an FNLT on UID 42). No new fixture file.

_A0923_CPM_018_TP2 = REPO / "tests" / "fixtures" / "test_projects" / "TP2_Bridge_4x10_Calendar.xml"
_A0923_CPM_018_KEY = "TP2_Bridge_4x10_Calendar"
#: the file's own <MinutesPerDay> (a 4x10 crew: Mon-Thu 07:00-12:00 + 12:30-17:30)
_A0923_CPM_018_MPD = 600
#: the hand network, every non-summary task in the file: UID -> Duration in the FILE's days
_A0923_CPM_018_DAYS = {
    11: 0, 12: 20, 13: 44, 14: 45, 15: 5, 16: 2, 21: 17, 22: 36,
    23: 33, 24: 5, 31: 25, 32: 18, 33: 10, 34: 86, 41: 5, 42: 0,
}  # fmt: skip
#: every link in the file (all FS, lag 0)
_A0923_CPM_018_LINKS = frozenset(
    {
        (11, 12), (12, 13), (13, 14), (14, 15), (14, 16), (12, 21), (21, 22), (22, 23),
        (23, 24), (12, 31), (12, 32), (12, 33), (12, 34), (15, 41), (16, 41), (24, 41),
        (31, 41), (32, 41), (33, 41), (34, 41), (41, 42),
    }
)  # fmt: skip
#: the driving path to UID 42 (hand longest path: 20 + 44 + 45 + 5 + 5 = 119 file-days)
_A0923_CPM_018_PATH = frozenset({11, 12, 13, 14, 15, 41, 42})
#: Devaux drag by hand, in file days: how far UID 42 pulls in when the activity is removed
_A0923_CPM_018_DRAG = {12: 20.0, 13: 3.0, 14: 3.0, 15: 3.0, 41: 5.0}


def _a0923_cpm_018_premise(raw: bytes) -> None:
    """Pin the hand network against the file's OWN stored fields, read with ElementTree (not
    the importer): MinutesPerDay, every non-summary Duration/DurationFormat, every link."""
    root = ET.fromstring(raw)
    if (root.findtext(NS + "MinutesPerDay") or "").strip() != str(_A0923_CPM_018_MPD):
        pytest.fail("precondition: TP2's <MinutesPerDay> is no longer 600")
    days: dict[int, int] = {}
    links: set[tuple[int, int]] = set()
    for el in root.iter(NS + "Task"):
        if (el.findtext(NS + "Summary") or "").strip() == "1":
            continue
        uid = int((el.findtext(NS + "UID") or "").strip())
        m = re.fullmatch(r"PT(\d+)H(\d+)M(\d+)S", (el.findtext(NS + "Duration") or "").strip())
        if m is None or (el.findtext(NS + "DurationFormat") or "").strip() != "7":
            pytest.fail(f"precondition: UID {uid}'s Duration is no longer whole hours in days")
        minutes = int(m.group(1)) * 60 + int(m.group(2))
        if minutes % _A0923_CPM_018_MPD:
            pytest.fail(f"precondition: UID {uid}'s {minutes} min is not whole 600-min days")
        days[uid] = minutes // _A0923_CPM_018_MPD
        for link in el.findall(NS + "PredecessorLink"):
            kind = (link.findtext(NS + "Type") or "").strip()
            lag = (link.findtext(NS + "LinkLag") or "").strip()
            if kind != "1" or lag != "0":
                pytest.fail(f"precondition: a link into UID {uid} is no longer FS lag 0")
            links.add((int((link.findtext(NS + "PredecessorUID") or "").strip()), uid))
    if days != _A0923_CPM_018_DAYS:
        pytest.fail(f"precondition: TP2's durations (file days) moved: {days}")
    if links != _A0923_CPM_018_LINKS:
        pytest.fail(f"precondition: TP2's links moved: {sorted(links)}")


def _a0923_cpm_018_with_fnlt(text: str) -> str:
    """TP2 with UID 42 (Reopen to traffic, stored Finish Wed 2026-11-04 17:30) constrained Finish
    No Later Than Mon 2026-11-02 17:30 -- MSPDI ConstraintType 7 -- and nothing else changed."""
    at = text.find("<UID>42</UID>")
    start, end = text.rfind("<Task>", 0, at), text.find("</Task>", at)
    block = text[start:end]
    if at < 0 or start < 0 or end < 0 or "<Finish>2026-11-04T17:30:00</Finish>" not in block:
        pytest.fail("precondition: TP2's UID 42 no longer stores Finish 2026-11-04T17:30:00")
    asap = "<ConstraintType>0</ConstraintType>"
    if block.count(asap) != 1:
        pytest.fail("precondition: TP2's UID 42 no longer carries exactly one ASAP constraint")
    fnlt = "<ConstraintType>7</ConstraintType><ConstraintDate>2026-11-02T17:30:00</ConstraintDate>"
    return text[:start] + block.replace(asap, fnlt) + text[end:]


def _a0923_cpm_018_served(text: str) -> tuple[str, dict[str, str], dict[int, dict[str, Any]]]:
    """Upload ``text`` into a fresh app, render ``/path`` and its grid's trace to UID 42 with
    drag: (the page-takeaway sentence, the KPI cards label -> value, grid rows by UID)."""
    client = TestClient(create_app(SessionState()))
    up = client.post(
        "/upload", files={"files": (_A0923_CPM_018_TP2.name, text.encode(), "text/xml")}
    )
    if up.status_code != 200:
        pytest.fail(f"precondition: upload answered {up.status_code}")
    page = client.get("/path")
    if page.status_code != 200:
        pytest.fail(f"precondition: /path answered {page.status_code}")
    head = re.search(r'<h1 class="page-takeaway"[^>]*>(.*?)</h1>', page.text, re.S)
    if head is None:
        pytest.fail("precondition: /path renders no page-takeaway")
    take = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", head.group(1))))
    cards = {
        html.unescape(label): html.unescape(value)
        for value, label in re.findall(
            r"<div class=stat-card><div class=stat-value>(.*?)</div>"
            r"<div class=stat-label>(.*?)</div></div>",
            page.text,
        )
    }
    if not {"Path total float", "Longest driver"} <= set(cards):
        pytest.fail(f"precondition: /path's KPI strip no longer carries both cards: {cards}")
    grid = client.get(f"/api/driving/{_A0923_CPM_018_KEY}?target=42&drag=1")
    if grid.status_code != 200:
        pytest.fail(f"precondition: /api/driving answered {grid.status_code}")
    rows = {int(r["unique_id"]): r for r in grid.json().get("rows", [])}
    return take, cards, rows


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-018: the Path Analysis surfaces turn working minutes into days with a "
        "hard-coded 480 (engine/drag.py:65, web/path.py:56 and :63) instead of the schedule's own "
        "day, so on the committed 4x10 TP2 (600 min/day) /api/driving serves Drag 25.0 / 3.75 / "
        "6.25 for 20 / 3 / 5 file-days, /path prints its 45-day longest driver as 56.25 working "
        "days, and -1,200 min of path float as -2.5 d for -2 d"
    ),
)
def test_a0923_cpm_018_path_analysis_days_are_the_schedules_own_days() -> None:
    """A0923-CPM-018 (finder id M-DAY480) · CPM · T1.

    Claim: at 13b13f38, the committed ``tests/fixtures/test_projects/TP2_Bridge_4x10_Calendar.xml``
    (project calendar "4x10 Crew", ``<MinutesPerDay>600</MinutesPerDay>``) uploaded to the app
    serves, on ``/api/driving/TP2_Bridge_4x10_Calendar?target=42&drag=1`` (the /path grid's
    "Drag (d)" column), Drag 25.0 / 3.75 / 3.75 / 3.75 / 6.25 for UIDs 12 / 13 / 14 / 15 / 41
    beside Durations (d) 20.0 / 44.0 / 45.0 / 5.0 / 5.0 -- UIDs 12 and 41 drag MORE than their
    whole duration -- where the hand drag is 20 / 3 / 3 / 3 / 5 file-days; and ``/path`` says
    "its longest single activity is Overlay & cure - EB at 56.25 working days" with the KPI
    "Longest driver 56.25 d" while the file and the same page's grid say 45. With one element
    added (FNLT Mon 2026-11-02 17:30 on UID 42) every critical activity carries -1,200 working
    minutes of total float = -2 file-days (the grid prints -2.0) and the "Path total float" card
    reads "-2.5 d" ("2.5 days of negative float"). Mechanism: ``engine/drag.py:65``
    ``per_day = MINUTES_PER_DAY`` (480, used at :99) and ``web/path.py:56`` / ``:63``
    ``/ 480.0``, where every other day figure on the page divides by the schedule's own day
    (``web/driving.py:232`` ``per_day = cal.working_minutes_per_day``). Every non-zero drag is
    x1.25 (600/480); on a 24-hour project day it is x3.

    Authority: A1 -- the file's own MSPDI fields, read with ElementTree: ``<MinutesPerDay>600``
    (line 13); UID 14 ``<Duration>PT450H0M0S`` ``<DurationFormat>7`` (lines 307-308): 27,000 /
    600 = 45 days; every Duration / link is pinned below. Hand arithmetic (FS 0 links only): the
    EB chain 12-13-14-15-41 is 20+44+45+5+5 = 119 days; 14-16 is 3 days short of 14-15, and the
    WB branch 21-22-23-24 (17+36+33+5 = 91) is 3 days short of 13-14-15 (94), so removing 13, 14
    or 15 pulls UID 42 in 3 days, removing 12 pulls it in 20, removing 41 pulls it in 5. The FNLT
    sits two 4x10 working days (Tue 11-03, Wed 11-04; no holiday after 09-07) before the stored
    Finish -- 1,200 min. A2 --
    ``docs/adr/0310-two-time-axes-and-the-labels-that-confuse-them.md:70-71``: "**A duration
    literal must not carry a hard-coded minutes-per-day.** Ordinary units resolve against the
    schedule's own `working_minutes_per_day`; elapsed units resolve at 1440." and :101-102 "any
    new hard-coded `480`/`1440` outside a `duration_is_elapsed` branch, is a contract violation
    with a citation to point at."; ``src/schedule_forensics/model/units.py:31-32``
    "A non-8-hour calendar carries its own ``working_minutes_per_day`` and is passed explicitly
    to the converters below."; ``src/schedule_forensics/engine/drag.py:12-13`` "A path
    activity's drag is capped by its **remaining** working duration".

    Independence: the expected days are the file's own stored fields and hand arithmetic on
    them; drag.py and path.py are not consulted for them. The same page's grid (Duration (d),
    total float) and the engine's minutes are preconditions, not the oracle. Not a parity claim:
    TP2 is generated by tools/make_test_projects.py; how MS Project itself displays it is
    UNVERIFIED (no MS Project export of TP2 is committed), MSPDI's MinutesPerDay /
    DurationFormat 7 make it 45 days. Exposure: 2 of the 43 committed MSPDI documents (TP2,
    twice) carry a non-480 project day; the 44-file stored-value corpus is 480 on 44 of 44.
    Runtime about 3 s.
    """
    if not _A0923_CPM_018_TP2.is_file():
        pytest.fail(f"precondition: {_A0923_CPM_018_TP2} is not committed")
    raw = _A0923_CPM_018_TP2.read_bytes()
    _a0923_cpm_018_premise(raw)
    text = raw.decode("utf-8")

    take, cards, rows = _a0923_cpm_018_served(text)
    if set(rows) != set(_A0923_CPM_018_DAYS):
        pytest.fail(f"precondition: the trace to UID 42 no longer holds all 16: {sorted(rows)}")
    grid_days = {u: rows[u]["duration_days"] for u in _A0923_CPM_018_DAYS}
    if grid_days != {u: float(d) for u, d in _A0923_CPM_018_DAYS.items()}:
        pytest.fail(f"precondition: the grid's own Duration (d) left the file's day: {grid_days}")
    on_path = {u for u, r in rows.items() if r["on_driving_path"]}
    if on_path != _A0923_CPM_018_PATH:
        pytest.fail(f"precondition: the driving path to UID 42 moved: {sorted(on_path)}")
    capping = {u: rows[u]["driving_slack_days"] for u in (16, 21, 22, 23, 24)}
    if set(capping.values()) != {3}:
        pytest.fail(f"precondition: the branches beside 13-14-15 no longer carry 3 d: {capping}")

    fnlt = _a0923_cpm_018_with_fnlt(text)
    cpm = compute_cpm(parse_mspdi_text(fnlt))
    tf = {u: cpm.timings[u].total_float for u in cpm.critical_path}
    if set(tf) != _A0923_CPM_018_PATH or set(tf.values()) != {-2 * _A0923_CPM_018_MPD}:
        pytest.fail(f"precondition: the FNLT no longer gives -1,200 min on the path: {tf}")
    take_f, cards_f, rows_f = _a0923_cpm_018_served(fnlt)
    grid_tf = {u: rows_f[u]["total_float_days"] for u in _A0923_CPM_018_PATH if u in rows_f}
    if grid_tf != dict.fromkeys(_A0923_CPM_018_PATH, -2.0):
        pytest.fail(f"precondition: the grid's own total float left the file's day: {grid_tf}")

    wrong: dict[str, object] = {}
    longest = "its longest single activity is Overlay & cure - EB at 45 working days."
    if longest not in take:
        wrong["/path take"] = take
    if cards["Longest driver"] != "45 d":
        wrong["/path card 'Longest driver' (hand 45 d)"] = cards["Longest driver"]
    if cards_f["Path total float"] != "-2 d":
        wrong["/path card 'Path total float', FNLT (hand -2 d)"] = cards_f["Path total float"]
    if "carrying 2 days of negative float" not in take_f:
        wrong["/path take, FNLT (hand 2 days of negative float)"] = take_f
    drag = {u: rows[u]["drag_days"] for u in _A0923_CPM_018_DRAG}
    if drag != _A0923_CPM_018_DRAG:
        wrong["/api/driving Drag (d)"] = {
            u: f"{drag[u]} (hand {want:g}; Duration (d) {rows[u]['duration_days']})"
            for u, want in _A0923_CPM_018_DRAG.items()
            if drag[u] != want
        }
    assert not wrong, (
        f"Path Analysis day figures are not on TP2's own {_A0923_CPM_018_MPD}-minute day "
        f"(the same page's grid is): {wrong}"
    )


# --- A0923-CPM-019 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    gzip, xml.etree.ElementTree as ET, typing.Any, pytest, TestClient
#              (fastapi.testclient), SessionState and create_app (schedule_forensics.web.app)
#   ALSO NEEDS io, json and zipfile (standard library) on the header's import lines
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden")
#   fixture    the module-level autouse _air_gapped
# Inputs: inline MSPDI text (built below); the committed, non-CUI goldens
# tests/fixtures/golden/ssi_uid152/Large_Test_File.mspdi.xml.gz + case.json (SSI's UID-152 export
# run under "Driving Slack <= 0 d") and tests/fixtures/golden/project2_5/Project5.mspdi.xml +
# tests/fixtures/golden/ssi_uid67/case.json (the gated control). No new fixture file.

#: The Path Analysis "Driving Slack <= x d" Dependency Range query (x appended); x = 0 is the
#: range SSI's own UID-67 and UID-152 exports were produced under.
_A0923_CPM_019_RANGE = "&range_mode=slack&range_days="


def _a0923_cpm_019_mspdi() -> str:
    """S (milestone) -> A (5d) -> B (5d) -> T (milestone); S -> C (8d) -> T. All FS lag 0, on
    MS Project's Standard day (Mon-Fri 08-12 / 13-17), from Monday 2026-01-05 08:00."""
    blocks = (
        "<WorkingTimes><WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime>"
        "</WorkingTime><WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime>"
        "</WorkingTime></WorkingTimes>"
    )
    days = "".join(
        f"<WeekDay><DayType>{d}</DayType><DayWorking>{int(2 <= d <= 6)}</DayWorking>"
        + (blocks if 2 <= d <= 6 else "")
        + "</WeekDay>"
        for d in range(1, 8)
    )
    tasks = ((1, "S", 0, ()), (2, "A", 40, (1,)), (3, "B", 40, (2,)), (4, "C", 64, (1,)))
    body = "".join(
        f"<Task><UID>{uid}</UID><ID>{uid}</ID><Name>{name}</Name><Duration>PT{hours}H0M0S"
        f"</Duration><DurationFormat>7</DurationFormat><Milestone>{int(hours == 0)}</Milestone>"
        + "".join(
            f"<PredecessorLink><PredecessorUID>{p}</PredecessorUID><Type>1</Type>"
            "<LinkLag>0</LinkLag><LagFormat>7</LagFormat></PredecessorLink>"
            for p in preds
        )
        + "</Task>"
        for uid, name, hours, preds in (*tasks, (9, "T", 0, (3, 4)))
    )
    return (
        '<Project xmlns="http://schemas.microsoft.com/project"><Name>drag-range</Name>'
        "<StartDate>2026-01-05T08:00:00</StartDate><CalendarUID>1</CalendarUID>"
        "<Calendars><Calendar><UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>"
        f"<BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{days}</WeekDays></Calendar></Calendars>"
        f"<Tasks>{body}</Tasks></Project>"
    )


def _a0923_cpm_019_client(filename: str, data: bytes) -> tuple[TestClient, str]:
    """A fresh app with ONE uploaded schedule, and that schedule's session key."""
    state = SessionState()
    client = TestClient(create_app(state))
    up = client.post("/upload", files={"files": (filename, data, "text/xml")})
    if up.status_code != 200 or len(state.schedules) != 1:
        pytest.fail(f"precondition: uploading {filename} answered {up.status_code}")
    return client, next(iter(state.schedules))


def _a0923_cpm_019_rows(client: TestClient, url: str) -> dict[int, dict[str, Any]]:
    """The /path grid's payload -- what path.js renders the 'Drag (d)' column from."""
    got = client.get(url)
    if got.status_code != 200:
        pytest.fail(f"precondition: {url} answered {got.status_code}")
    return {int(r["unique_id"]): r for r in got.json()["rows"]}


def _a0923_cpm_019_export_drag(client: TestClient, url: str) -> dict[int, str]:
    """The 'Drag (d)' column of the Path Analysis Excel export, by UID (read with zipfile +
    ElementTree: shared or inline strings and plain values)."""
    got = client.get(url)
    if got.status_code != 200 or got.content[:2] != b"PK":
        pytest.fail(f"precondition: {url} answered {got.status_code}, not an .xlsx")
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    book = zipfile.ZipFile(io.BytesIO(got.content))
    shared = (
        [
            "".join(t.text or "" for t in si.iter(ns + "t"))
            for si in ET.fromstring(book.read("xl/sharedStrings.xml")).iter(ns + "si")
        ]
        if "xl/sharedStrings.xml" in book.namelist()
        else []
    )
    table = []
    for row in ET.fromstring(book.read("xl/worksheets/sheet1.xml")).iter(ns + "row"):
        cells = []
        for c in row.iter(ns + "c"):
            v = c.find(ns + "v")
            if c.get("t") == "s" and v is not None and v.text is not None:
                cells.append(shared[int(v.text)])
            elif c.get("t") == "inlineStr":
                cells.append("".join(t.text or "" for t in c.iter(ns + "t")))
            else:
                cells.append((v.text or "") if v is not None else "")
        table.append(cells)
    if not table or "UID" not in table[0] or "Drag (d)" not in table[0]:
        pytest.fail(f"precondition: the export's header lost UID / Drag (d): {table[:1]}")
    uid, drag = table[0].index("UID"), table[0].index("Drag (d)")
    return {int(r[uid]): (r[drag] if len(r) > drag else "") for r in table[1:] if r}


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-019: the Path Analysis Dependency Range filter ('Driving Slack <= x d') removes "
        "rows BEFORE compute_drag caps drag by the concurrent rows it is given, so a hidden "
        "near-path branch stops capping: hand S->A(5d)->B(5d)->T || S->C(8d) serves Drag A = B = "
        "5.0 d at range 0/1 (2.0 d on the full trace, hand 2.0), and Large_Test_File focus 152 "
        "under SSI's own <= 0 d range serves 10 of 76 rows inflated (7442/7443 1.0 -> 15.0 d)"
    ),
)
def test_a0923_cpm_019_the_dependency_range_filter_does_not_change_a_shown_rows_drag() -> None:
    """A0923-CPM-019 (finder id F-DRAG-005) · CPM (web layer over engine/drag.py) · T1.

    Claim: at 13b13f38, ``web/driving.py:219-225`` (``_driving_data``) drops every traced row
    whose driving slack exceeds ``range_days`` when ``range_mode=slack`` and only THEN, at
    :226-230, hands the filtered dict to ``compute_drag(sch, results)``, whose concurrency cap
    scans only the rows it is given (``engine/drag.py:82``). A display filter therefore changes
    a network figure. Hand network S -> A (5d) -> B (5d) -> T, S -> C (8d) -> T (C's driving
    slack 2 d): ``/api/driving/{name}?target=9&drag=1`` serves Drag A = B = 2.0 d on the full
    trace and with ``range_days=2``, but 5.0 d with ``range_mode=slack&range_days=0`` or ``1``
    (C hidden); the Path Analysis Excel export (``/export/xlsx/path``) carries the same 5.0.
    Committed ``tests/fixtures/golden/ssi_uid152/Large_Test_File.mspdi.xml.gz``, focus 152, under
    the ``Driving Slack <= 0 d`` range SSI's own export was run with: 10 of the 76 shown rows'
    served Drag grows -- 903/905 5.5 -> 8.0, 1570 1.0 -> 2.0, 5571 10.0 -> 21.0, 6997 9.0 ->
    24.0, 7415 19.0 -> 20.0, 7425 15.0 -> 20.0, 7442/7443 1.0 -> 15.0, 7448 1.0 -> 3.0 -- each
    because its full-trace capper (an off-path concurrent row with 1-19 d of driving slack, e.g.
    7438 for 7442) is filtered out. The gated golden (Project5 focus 67) moves on 0 rows -- every
    cap there is another 0-slack row the filter keeps -- which is why ``test_ssi_drag_exact``
    cannot see this (checked here as a control).

    Authority: A1 -- hand arithmetic on the network above: T finishes at 10 d through A -> B;
    with A's (or B's) duration removed the A/B chain is 5 d and C's 8 d governs, so T pulls in
    10 - 8 = 2 d: drag(A) = drag(B) = 2.0 d, whichever rows the grid shows. SSI's UID-152
    export, run under the same ``Driving Slack <= 0 d`` range (``ssi_uid152/case.json:3``
    ``"Golden SSI DRIVING PATH (Driving Slack <= 0 d)"``), reports no Drag above 0.5 d on any of
    its 76 rows (``ssi_drag_days_by_uid_provenance_only``), and
    ``docs/adr/0158-histogram-drill-vizhints-uid152.md:32-34`` explains that 0.5 as a HIDDEN row:
    "That 0.5 is the near-path slack under an SSI measurement convention the engine computes as
    1.0 d (the nearest parallel branch hangs on a noon milestone)" -- SSI caps drag with a branch
    its <= 0 d range does not display. A2 -- ``engine/drag.py:3-4``: "DRAG (Devaux's Removed
    Activity Gauge) answers \"if this activity's remaining work vanished, how much sooner would
    the target finish?\"" (a property of the network); ``web/driving.py:177-178``: "``range_mode``
    \"slack\" keeps only rows with driving slack <= ``range_days`` (SSI \"Get dependencies with
    Driving Slack <= x\")" (a row filter); the drag gate ``tests/parity/test_parity_gate.py:
    262-263`` validates ``compute_drag`` on the UNFILTERED ``compute_driving_slack`` trace
    against SSI's UID-67 export, which ``ssi_uid67/case.json:3`` records as produced with
    "Dependency Range=Get dependencies with Driving Slack <= 0d".

    Not asserted: SSI's 0.5 d on Large_Test_File (ADR-0158 decision 4 holds it provenance-only;
    the engine's full-trace 1.0 there is the separate F-DRAG-001 question). Only range-invariance
    is asserted on that file, plus the hand value on the hand network.

    Independence: the hand values are arithmetic on durations written here; the Large_Test_File
    expectation is the tool's own full-trace figure for the same row (the claim is invariance,
    not a value); SSI's export and ADR-0158 are read, never produced, by this test.
    """
    # the gated control: Project5 focus 67 reproduces SSI's 20 gated values both ways
    case67 = json.loads((GOLDEN / "ssi_uid67" / "case.json").read_text())
    if "Driving Slack <= 0d" not in case67["_note"]:
        pytest.fail("precondition: the UID-67 export no longer records its <= 0 d range")
    gated = {int(u): float(d) for u, d in case67["ssi_drag_days_by_uid"].items()}
    p5 = GOLDEN / "project2_5" / "Project5.mspdi.xml"
    client, key = _a0923_cpm_019_client("Project5.mspdi.xml", p5.read_bytes())
    for q in ("", _A0923_CPM_019_RANGE + "0"):
        rows = _a0923_cpm_019_rows(client, f"/api/driving/{key}?target=67&drag=1{q}")
        served = {u: r["drag_days"] for u, r in rows.items() if r["drag_days"] is not None}
        if served != gated:
            pytest.fail(
                f"precondition (control): Project5 focus 67 {q or '(full trace)'} no longer "
                f"serves SSI's 20 gated drag values: {served}"
            )

    wrong: dict[str, object] = {}

    # the hand network
    client, key = _a0923_cpm_019_client("drag_range.xml", _a0923_cpm_019_mspdi().encode("utf-8"))
    base = f"/api/driving/{key}?target=9&drag=1"
    full = _a0923_cpm_019_rows(client, base)
    shape = {u: (r["driving_slack_days"], r["on_driving_path"]) for u, r in full.items()}
    if shape != {1: (0, True), 2: (0, True), 3: (0, True), 4: (2, False), 9: (0, True)}:
        pytest.fail(f"precondition: the hand trace is not S/A/B/T driving + C at 2 d: {shape}")
    if (full[2]["drag_days"], full[3]["drag_days"]) != (2.0, 2.0):
        pytest.fail(
            "precondition (control): the full trace no longer serves the hand drag A = B = 2.0 "
            f"({full[2]['drag_days']}, {full[3]['drag_days']})"
        )
    for days, c_shown in ((0, False), (1, False), (2, True)):
        rows = _a0923_cpm_019_rows(client, base + _A0923_CPM_019_RANGE + str(days))
        if (4 in rows) is not c_shown or not {1, 2, 3, 9} <= set(rows):
            pytest.fail(
                f"precondition: range_days={days} no longer filters rows as documented "
                f"(C shown: {4 in rows}, rows {sorted(rows)})"
            )
        got = (rows[2]["drag_days"], rows[3]["drag_days"])
        if got != (2.0, 2.0):
            wrong[f"hand /api/driving range<={days}d (A, B)"] = got
    export = f"/export/xlsx/path/{key}?target=9&drag=1"
    xl = _a0923_cpm_019_export_drag(client, export)
    if (xl.get(2), xl.get(3)) != ("2.0", "2.0"):
        pytest.fail(f"precondition (control): the full-trace export carries A, B = {xl}")
    xl = _a0923_cpm_019_export_drag(client, export + _A0923_CPM_019_RANGE + "0")
    if (xl.get(2), xl.get(3)) != ("2.0", "2.0"):
        wrong["hand /export/xlsx/path range<=0d (A, B)"] = (xl.get(2), xl.get(3))

    # the committed Large_Test_File golden, focus 152, under SSI's own <= 0 d range
    case152 = json.loads((GOLDEN / "ssi_uid152" / "case.json").read_text())
    ssi_drag = {int(u): d for u, d in case152["ssi_drag_days_by_uid_provenance_only"].items()}
    path_uids = {int(u) for u in case152["driving_path_uids"]}
    if "(Driving Slack <= 0 d)" not in case152["_note"] or set(ssi_drag) != path_uids:
        pytest.fail("precondition: the UID-152 SSI export's range / Drag column moved")
    if max(ssi_drag.values()) > 0.5:
        pytest.fail("precondition: SSI's <= 0 d export now reports a drag above 0.5 d")
    raw = gzip.decompress((GOLDEN / "ssi_uid152" / "Large_Test_File.mspdi.xml.gz").read_bytes())
    client, key = _a0923_cpm_019_client("Large_Test_File.mspdi.xml", raw)
    full = _a0923_cpm_019_rows(client, f"/api/driving/{key}?target=152&drag=1")
    ranged = _a0923_cpm_019_rows(
        client, f"/api/driving/{key}?target=152&drag=1{_A0923_CPM_019_RANGE}0"
    )
    if set(ranged) != path_uids or not set(ranged) < set(full):
        pytest.fail(
            f"precondition: the <= 0 d range no longer shows exactly SSI's {len(path_uids)} "
            f"Path-01 rows out of a larger full trace ({len(ranged)} of {len(full)})"
        )
    moved = {
        uid: (full[uid]["drag_days"], ranged[uid]["drag_days"], ssi_drag[uid])
        for uid in sorted(ranged)
        if ranged[uid]["drag_days"] != full[uid]["drag_days"]
    }
    if moved:
        wrong["Large_Test_File focus 152 range<=0d (full trace, range, SSI)"] = moved

    assert not wrong, (
        "the Dependency Range display filter changed the served Drag of a row it still shows "
        f"(hand value 2.0 d; Large_Test_File must equal its own full-trace drag): {wrong}"
    )


# --- A0923-CPM-020 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    datetime as dt, re, pytest, TestClient (fastapi.testclient), compute_cpm
#              (schedule_forensics.engine.cpm), SessionState and create_app
#              (schedule_forensics.web.app)
#   ALSO NEEDS (not on the committed header -- add them there):
#              ``from schedule_forensics.importers.json_schedule import to_json_text``
#              ``from schedule_forensics.model.relationship import Relationship``
#              ``from schedule_forensics.model.schedule import Schedule``
#              ``from schedule_forensics.model.task import Task``
#   fixture    the module-level autouse _air_gapped
# Input: a hand-built network (model objects, below) serialized to the tool's OWN Save format
# (.json) and uploaded through /upload. No fixture file; nothing CUI. Runtime: ~0.5 s (call).

#: Four parallel branches Start -> X -> Finish on the default 480-minute day: (UID, name, working
#: minutes). The hand total float of a branch is 2,400 - its duration (the longest branch, A, is
#: the critical path): A 0, B 1, C 2, D 3 working minutes. D is the control on the far side of the
#: grid's 0.01-day quantum (3 / 480 = 0.00625 d -> 0.01); B and C sit inside it (0.0021 / 0.0042 d
#: -> 0.00).
_A0923_CPM_020_BRANCHES = ((2, "A", 2400), (3, "B", 2399), (4, "C", 2398), (5, "D", 2397))
_A0923_CPM_020_START, _A0923_CPM_020_FINISH = 1, 6


def _a0923_cpm_020_schedule() -> Schedule:
    """The hand network: milestone Start, the four branches, milestone Finish; FS/0 links; no
    stored Critical flag and no stored Total Slack anywhere (a flagless source, as XER / JSON /
    hand-authored inputs are)."""
    tasks = (
        Task(unique_id=_A0923_CPM_020_START, name="Start", duration_minutes=0, is_milestone=True),
        *(
            Task(unique_id=uid, name=name, duration_minutes=minutes)
            for uid, name, minutes in _A0923_CPM_020_BRANCHES
        ),
        Task(unique_id=_A0923_CPM_020_FINISH, name="Finish", duration_minutes=0, is_milestone=True),
    )
    rels = tuple(
        Relationship(predecessor_id=_A0923_CPM_020_START, successor_id=uid)
        for uid, _, _ in _A0923_CPM_020_BRANCHES
    ) + tuple(
        Relationship(predecessor_id=uid, successor_id=_A0923_CPM_020_FINISH)
        for uid, _, _ in _A0923_CPM_020_BRANCHES
    )
    return Schedule(
        name="f-drag-006",
        source_file="a0923_cpm_020.json",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        tasks=tasks,
        relationships=rels,
    )


def _a0923_cpm_020_hand_float() -> dict[int, int]:
    """THE ORACLE, independent of the engine: each activity's total float in working minutes by
    hand arithmetic on the network above. Every branch starts at 0 and the Finish milestone waits
    for the longest one (2,400), so a branch's float is 2,400 less its own duration; Start and
    Finish lie on the longest branch's chain and carry 0."""
    longest = max(minutes for _, _, minutes in _A0923_CPM_020_BRANCHES)
    hand = {uid: longest - minutes for uid, _, minutes in _A0923_CPM_020_BRANCHES}
    hand[_A0923_CPM_020_START] = hand[_A0923_CPM_020_FINISH] = 0
    return hand


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-020: the /analysis grid, Gantt and Task-Info critical flag of a task with no "
        "stored Critical flag is computed from the float rounded to 0.01 day and multiplied back "
        "(web/state.py:1814), so an activity with 1 or 2 working minutes of CPM total float is "
        "shown critical while the CPM and the same page's 'Critical (incomplete)' KPI exclude it"
    ),
)
def test_a0923_cpm_020_a_flagless_activity_with_positive_float_is_not_shown_critical() -> None:
    """A0923-CPM-020 (finder id F-DRAG-006) · CPM · T1 (latent: 0 committed activities sit in the
    band).

    Claim: at 13b13f38, ``web/state.py:1814`` feeds ``is_effective_critical`` the grid's rounded
    day figure multiplied back -- ``is_effective_critical(task, float(fr.total_float_days) *
    per_day)``, where ``total_float_days`` is ``minutes_to_days`` quantised to 0.01 d
    ROUND_HALF_UP (4.8 working minutes on a 480-minute day) -- instead of the CPM's exact minutes
    (``fr.total_float_minutes``). For a task with NO stored Critical flag (the fallback branch:
    XER, the tool's own Save .json, hand-authored input) whose CPM total float lies in
    0 < TF < 0.005 x per_day (1 or 2 working minutes at 480), the served ``/api/analysis/{name}``
    row reads ``is_critical: true`` -- the grid row class ``crit`` (app.js:860), the Gantt bar
    ``g-bar g-crit`` (app.js:613) and Task-Info "Critical yes" (taskinfo.js:126) -- while
    ``compute_cpm`` reads ``is_critical`` False, leaves the task off ``critical_path``, and the
    SAME page's "Critical (incomplete)" KPI (``web/analysis.py:1066-1073``, exact minutes) leaves
    it out: on the network here the page shows KPI 3 beside 5 critical grid rows. Latent on the
    committed corpus: 0 of 22,118 scheduled activities (44 MSPDI goldens / intake conversions +
    tests/fixtures/xer/commercial_construction.xer + web/examples/house_build.json) lie in the
    band, even with the stored flags stripped.

    Authority: A2 -- ``src/schedule_forensics/engine/metrics/_common.py:98`` / ``:103-104`` /
    ``:107`` (the function this call site invokes): ``def is_effective_critical(task: Task,
    recomputed_total_float: float) -> bool:`` ... "When the source carried no flag, fall back to
    pure-logic CPM critical, excluding completed work (a finished activity is no forward schedule
    risk — ADR-0010 §3)." ... ``return recomputed_total_float <= 0 and is_incomplete(task)`` -- the
    RECOMPUTED CPM float, in working minutes (the sibling ``effective_total_float``, :86: "The
    total float to score a task on, in working minutes."); ``src/schedule_forensics/engine/
    float_analysis.py:9-10``: "``is_critical`` — the pure CPM property ``total_float <= 0`` (a
    property of the network logic, independent of progress);"; ``src/schedule_forensics/engine/
    cpm.py:3296`` ``is_critical=total <= 0,``. A1 -- hand arithmetic on the network built here:
    Start -> A (2,400 min) -> Finish and Start -> C (2,398 min) -> Finish, so C's total float =
    2,400 - 2,398 = 2 working minutes > 0 -> not critical (B: 1 min, likewise).

    Independence: the expected flags come from ``_a0923_cpm_020_hand_float`` (arithmetic on the
    durations written here); the engine is consulted only as a precondition that it AGREES with
    the hand floats, so the fault is isolated to the grid's lossy reconstruction. The same-page
    KPI is checked (a precondition) to equal the hand count, the contrasting witness. Controls in
    the same assertion: A (0 min, critical) and D (3 min, rounds to 0.01 d, not critical) read
    right today. Not a held decision: ADR-0150 decision 1 chose the effective (stored-first)
    basis for the grid's flag; no ADR or HELD row chooses to classify on rounded days.
    """
    sch = _a0923_cpm_020_schedule()
    hand = _a0923_cpm_020_hand_float()
    st = SessionState()
    client = TestClient(create_app(st))
    up = client.post(
        "/upload",
        files={
            "files": ("a0923_cpm_020.json", to_json_text(sch).encode("utf-8"), "application/json")
        },
    )
    if up.status_code != 200 or len(st.schedules) != 1:
        pytest.fail(f"precondition: upload answered {up.status_code}, {sorted(st.schedules)}")
    key, loaded = next(iter(st.schedules.items()))
    flags = {
        t.unique_id: (t.stored_is_critical, t.stored_total_float_minutes) for t in loaded.tasks
    }
    if any(v != (None, None) for v in flags.values()) or set(flags) != set(hand):
        pytest.fail(f"precondition: the loaded file is no longer flagless: {flags}")
    if loaded.calendar.working_minutes_per_day != 480:
        pytest.fail(
            f"precondition: the day is {loaded.calendar.working_minutes_per_day} min, not 480"
        )
    cpm = compute_cpm(loaded)
    engine = {uid: (tm.total_float, tm.is_critical) for uid, tm in cpm.timings.items()}
    if engine != {uid: (tf, tf <= 0) for uid, tf in hand.items()}:
        pytest.fail(f"precondition: the CPM no longer reproduces the hand floats: {engine}")
    if set(cpm.critical_path) != {uid for uid, tf in hand.items() if tf <= 0}:
        pytest.fail(f"precondition: the CPM critical path moved: {cpm.critical_path}")

    page = client.get(f"/analysis/{key}")
    if page.status_code != 200:
        pytest.fail(f"precondition: /analysis/{key} answered {page.status_code}")
    feed = re.search(r'id=viz data-name="([^"]*)"', page.text)
    if feed is None or feed.group(1) != key:
        pytest.fail("precondition: the page's grid no longer names this schedule as its data feed")
    shown_by = {
        "/static/app.js": (
            r'fetch\("/api/analysis/" \+ enc\)',
            r'act\.is_critical \? "g-bar g-crit"',
            r'if \(act\.is_critical\) tr\.className = "crit"',
        ),
        "/static/taskinfo.js": (r'\["Critical", act\.is_critical \? "yes" : "no"\]',),
    }
    for asset, patterns in shown_by.items():
        js = client.get(asset)
        missing = [p for p in patterns if js.status_code != 200 or not re.search(p, js.text)]
        if missing:
            pytest.fail(f"precondition: {asset} no longer shows the served flag via {missing}")
    kpi = re.search(
        r"<div class=stat-value>([^<]*)</div><div class=stat-label>Critical \(incomplete\)</div>",
        page.text,
    )
    want_count = sum(1 for tf in hand.values() if tf <= 0)
    if kpi is None or kpi.group(1) != str(want_count):
        pytest.fail(
            f"precondition: the page's Critical (incomplete) KPI is "
            f"{kpi.group(1) if kpi else None}, not the hand count {want_count}"
        )

    api = client.get(f"/api/analysis/{key}")
    if api.status_code != 200:
        pytest.fail(f"precondition: /api/analysis/{key} answered {api.status_code}")
    rows = {a["unique_id"]: a for a in api.json()["activities"] if not a["is_summary"]}
    if set(rows) != set(hand):
        pytest.fail(f"precondition: the grid's activities are {sorted(rows)}, not {sorted(hand)}")
    served = {uid: rows[uid]["is_critical"] for uid in sorted(rows)}
    want = {uid: hand[uid] <= 0 for uid in sorted(rows)}
    wrong = {
        uid: (
            f"shown critical={served[uid]} (row total_float_days {rows[uid]['total_float_days']}); "
            f"hand float {hand[uid]} min -> critical={want[uid]}"
        )
        for uid in served
        if served[uid] != want[uid]
    }
    assert not wrong and sum(served.values()) == int(kpi.group(1)), (
        f"a flagless activity's grid / Gantt / Task-Info Critical flag disagrees with its CPM "
        f"float (0 < TF < 0.005 x 480 min is read as 0.00 d x 480 = 0): {wrong}; the same page's "
        f"Critical (incomplete) KPI reads {kpi.group(1)} beside {sum(served.values())} critical "
        f"grid rows"
    )


# --- A0923-CPM-021 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py, and on nothing else:
#   imports    datetime as dt, xml.etree.ElementTree as ET, pytest, TestClient,
#              compute_cpm (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi),
#              SessionState and create_app (schedule_forensics.web.app)
#   NEW header imports the merge must add: json;
#              Relationship (schedule_forensics.model.relationship),
#              Schedule (schedule_forensics.model.schedule), Task (schedule_forensics.model.task)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Inputs: a hand-built network (model objects, below) and the committed, non-CUI goldens
# tests/fixtures/golden/project2_5/Project5.mspdi.xml and tests/fixtures/golden/ssi_uid67/case.json.
# No new fixture file.

#: Hand network S -> A (3 d) -> T (the target) -> B (4 d) -> C (2 d), every link FS lag 0.
_A0923_CPM_021_HAND = {1: ("S", 0), 2: ("A", 1440), 3: ("T", 0), 4: ("B", 1920), 5: ("C", 960)}
_A0923_CPM_021_HAND_LINKS = ((1, 2), (2, 3), (3, 4), (4, 5))


def _a0923_cpm_021_hand() -> Schedule:
    """The hand network on the default 8 h Mon-Fri calendar, starting Mon 2026-01-05 08:00."""
    tasks = tuple(
        Task(unique_id=uid, name=name, duration_minutes=minutes, is_milestone=uid in (1, 3))
        for uid, (name, minutes) in _A0923_CPM_021_HAND.items()
    )
    links = tuple(
        Relationship(predecessor_id=p, successor_id=s) for p, s in _A0923_CPM_021_HAND_LINKS
    )
    return Schedule(
        name="drag-hand",
        source_file="drag-hand.json",
        project_start=dt.datetime(2026, 1, 5, 8),
        tasks=tasks,
        relationships=links,
    )


def _a0923_cpm_021_raw_links(raw: bytes) -> set[tuple[int, int]]:
    """Every (predecessor, successor) pair of the raw ``<PredecessorLink>`` elements -- read with
    ElementTree, not the importer."""
    links: set[tuple[int, int]] = set()
    for el in ET.fromstring(raw).iter(NS + "Task"):
        uid = int((el.findtext(NS + "UID") or "").strip())
        for pl in el.findall(NS + "PredecessorLink"):
            links.add((int((pl.findtext(NS + "PredecessorUID") or "").strip()), uid))
    return links


def _a0923_cpm_021_descendants(links: set[tuple[int, int]], target: int) -> set[int]:
    """Every activity reachable forward from ``target`` over the logic links (target excluded)."""
    succ: dict[int, set[int]] = {}
    for p, s in links:
        succ.setdefault(p, set()).add(s)
    seen: set[int] = set()
    todo = [target]
    while todo:
        for nxt in succ.get(todo.pop(), set()):
            if nxt not in seen:
                seen.add(nxt)
                todo.append(nxt)
    seen.discard(target)
    return seen


def _a0923_cpm_021_pull_in(sch: Schedule, target: int, uid: int) -> float:
    """The removal oracle (Devaux's definition, independent of ``engine/drag.py``): how many
    working days sooner the TARGET finishes on ``compute_cpm`` when ``uid``'s remaining work
    vanishes (duration and remaining duration set to 0)."""
    per_day = sch.calendar.working_minutes_per_day
    task = sch.task_by_id(uid)
    gone = task.model_copy(
        update={
            "duration_minutes": 0,
            "remaining_duration_minutes": (
                0 if task.remaining_duration_minutes is not None else None
            ),
        }
    )
    removed = sch.model_copy(
        update={"tasks": tuple(gone if t.unique_id == uid else t for t in sch.tasks)}
    )
    before = compute_cpm(sch).timings[target].early_finish
    after = compute_cpm(removed).timings[target].early_finish
    return round((before - after) / per_day, 2)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-021: with Path Direction Successors or Both, /api/driving serves a non-zero "
        "Drag for the target's own descendants (compute_drag runs on the successor trace "
        "unchanged, web/driving.py:226-230) -- Project5 target 67: UID 82 25.0 d, 78 15.0, 103/104 "
        "10.0, 68 7.0, 69 2.0; hand S->A->T->B(4d)->C(2d): B 4.0, C 2.0 -- though removing any of "
        "them moves the target 0 d"
    ),
)
def test_a0923_cpm_021_a_descendant_of_the_target_carries_no_drag() -> None:
    """A0923-CPM-021 (finder id F-DRAG-008) · CPM · T1.

    Claim: at 13b13f38, ``GET /api/driving/{name}?target=N&direction=successors|both&drag=1``
    (the Path Analysis grid's "Drag (d)" column after Run Drag Analysis, and the same
    ``_driving_data`` behind ``/export/xlsx/path/{name}``) serves a non-zero Drag for activities
    that are DESCENDANTS of the target, because ``web/driving.py:226-230`` runs
    ``compute_drag(sch, results)`` on the successor (or merged) trace unchanged. On the committed
    Project5 golden, target 67 ('Pour roof slab'): UID 82 25.0 d, 78 15.0 d, 103 10.0 d,
    104 10.0 d, 68 7.0 d, 69 2.0 d; on the hand network S -> A(3d) -> T -> B(4d) -> C(2d),
    target T: B 4.0 d, C 2.0 d. Removing any of these activities' remaining work moves the target
    0.0 d, so each descendant's drag to the target is 0.

    Authority: A2 -- ``src/schedule_forensics/engine/drag.py:3-4``: 'DRAG (Devaux's Removed
    Activity Gauge) answers "if this activity's remaining work vanished, how much sooner would the
    target finish?"'. Reference tool: SSI, "Understand Critical Path Drag",
    https://www.ssitools.com/helpandsuport/ssianalysishelp/understand_critical_path_drag.htm
    (search-result text retrieved 2026-09-28; the direct fetch is blocked by the egress proxy):
    "Critical or Driving Path Drag is the amount of opportunity (measured in days) Critical or
    Driving path tasks have to accelerate the focus item if their remaining duration is set to
    zero." A1 -- hand arithmetic: T's early finish is S + A = 3 d whatever B and C do, so their
    drag to T is 0; and the removal oracle on ``compute_cpm`` (target 67 pull-in 0.0 d for each
    of the six). NOT claimed: a project-duration reading (Wikipedia "Critical path drag"); under
    it the hand values 4.0 / 2.0 would be right, while the six Project5 values stay wrong (the
    project finish is governed by UID 131's MSO chain, 0.0 d pull-in for each).

    Independence: the expected value is the target's pull-in computed by removal on
    ``compute_cpm`` -- never by ``engine/drag.py``; descendants are walked over Project5's raw
    ``<PredecessorLink>`` elements read with ElementTree. Controls, run first as
    preconditions: the predecessor trace through the same route reproduces SSI's own exported
    Drag (``ssi_uid67`` golden, 20/20); the oracle agrees with a non-zero served value (hand A
    3.0 d; Project5 target 67 in successor mode 4.0 d).
    """
    hand = _a0923_cpm_021_hand()
    raw = (GOLDEN / "project2_5" / "Project5.mspdi.xml").read_bytes()
    p5 = parse_mspdi_text(raw.decode("utf-8"))
    raw_links = _a0923_cpm_021_raw_links(raw)
    if raw_links != {(r.predecessor_id, r.successor_id) for r in p5.relationships}:
        pytest.fail("precondition: the importer no longer keeps Project5's raw <PredecessorLink>s")
    for sch in (hand, p5):
        if sch.calendar.working_minutes_per_day != 480:
            pytest.fail(f"precondition: {sch.name} is no longer on an 8 h day")
    state = SessionState()
    state.schedules["hand"] = hand
    state.schedules["Project5"] = p5
    client = TestClient(create_app(state))

    def trace(name: str, target: int, direction: str) -> list[dict[str, Any]]:
        resp = client.get(
            f"/api/driving/{name}", params={"target": target, "direction": direction, "drag": 1}
        )
        rows = resp.json().get("rows") if resp.status_code == 200 else None
        if not rows:
            pytest.fail(
                f"precondition: /api/driving/{name} {direction} answered {resp.status_code}"
            )
        return list(rows)

    # control 1: the route's predecessor-trace Drag is SSI's own export, UID for UID
    ssi = json.loads((GOLDEN / "ssi_uid67" / "case.json").read_text(encoding="utf-8"))
    want_ssi = {int(u): float(d) for u, d in ssi["ssi_drag_days_by_uid"].items()}
    got_ssi = {
        r["unique_id"]: r["drag_days"]
        for r in trace("Project5", 67, "predecessors")
        if r.get("drag_days") is not None
    }
    if got_ssi != want_ssi:
        pytest.fail(f"precondition: the predecessor Drag is no longer SSI's 20/20 ({got_ssi})")
    # control 2: hand arithmetic, and the oracle agrees with a served non-zero predecessor drag
    hand_a = {r["unique_id"]: r["drag_days"] for r in trace("hand", 3, "predecessors")}.get(2)
    oracle = {u: _a0923_cpm_021_pull_in(hand, 3, u) for u in (2, 4, 5)}
    if hand_a != 3.0 or oracle != {2: 3.0, 4: 0.0, 5: 0.0}:
        pytest.fail(
            f"precondition: hand A drag {hand_a}, removal oracle {oracle} (want A 3/B 0/C 0)"
        )
    # control 3: in successor mode the target's own served drag agrees with the oracle (4.0 d)
    t67 = {r["unique_id"]: r["drag_days"] for r in trace("Project5", 67, "successors")}.get(67)
    if t67 is None or t67 == 0 or t67 != _a0923_cpm_021_pull_in(p5, 67, 67):
        pytest.fail(f"precondition: target 67's successor-mode drag {t67} left the oracle")

    cases = (
        ("hand", hand, 3, _a0923_cpm_021_descendants(set(_A0923_CPM_021_HAND_LINKS), 3)),
        ("Project5", p5, 67, _a0923_cpm_021_descendants(raw_links, 67)),
    )
    wrong: dict[str, tuple[float, float]] = {}
    for name, sch, target, below in cases:
        for direction in ("successors", "both"):
            on_path = [
                r
                for r in trace(name, target, direction)
                if r["unique_id"] in below and r["on_driving_path"]
            ]
            if not on_path:
                pytest.fail(f"precondition: {name} {direction} reaches no on-path descendant")
            for r in on_path:
                served = r.get("drag_days")
                if served is None:
                    continue  # no drag offered for the row ("—") is also correct
                want = _a0923_cpm_021_pull_in(sch, target, r["unique_id"])
                if served != want:
                    wrong[f"{name} {direction} UID {r['unique_id']}"] = (served, want)
    assert not wrong, (
        "a descendant of the target is served a Drag its removal cannot give back to the target "
        f"(served d, target pull-in d): {wrong}"
    )


# --- A0923-CPM-022 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py plus imports it does not
# carry yet (marked NEW):
#   imports    datetime as dt, gzip, re, xml.etree.ElementTree as ET, pytest, TestClient,
#              parse_mspdi_text (schedule_forensics.importers.mspdi),
#              SessionState / create_app (schedule_forensics.web.app)
#              NEW: json; compute_driving_slack (schedule_forensics.engine.driving_slack);
#              Relationship, Schedule, ConstraintType / Task (schedule_forensics.model.*)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Inputs: the committed, non-CUI goldens fuse_hardfile/Hard_File.mspdi.xml.gz,
# ssi_uid152_leveled/Large_Test_File_Leveled.mspdi.xml.gz and ssi_uid152_leveled/case.json.
# No new fixture file.

#: the /path tooltips' promise (web/path.py:228 and :229), required verbatim on BOTH checkboxes
_A0923_CPM_022_PROMISE = (
    "on a fully-dated file the trace is unchanged, matching SSI's own output with this option on"
)


def _a0923_cpm_022_dating(raw: bytes) -> tuple[int, list[str], dict[str, str]]:
    """(activity count, undated activity UIDs, {UID: calendar name} of the activities on a calendar
    other than the project's) -- read from the raw MSPDI with ElementTree, not the importer. An
    activity is a <Task> that is not a summary, not inactive and not a null row."""
    root = ET.fromstring(raw)
    project_cal = (root.findtext(NS + "CalendarUID") or "").strip()
    cal_names = {
        (c.findtext(NS + "UID") or "").strip(): (c.findtext(NS + "Name") or "").strip()
        for c in root.iter(NS + "Calendar")
    }
    count, undated, off_calendar = 0, [], {}
    for el in root.iter(NS + "Task"):
        field = {k: (el.findtext(NS + k) or "").strip() for k in ("UID", "Summary", "Active")}
        if field["Summary"] == "1" or field["Active"] == "0":
            continue
        if (el.findtext(NS + "IsNull") or "").strip() == "1":
            continue
        count += 1
        dated = [(el.findtext(NS + k) or "").strip() for k in ("Start", "Finish")]
        if not all(dated):
            undated.append(field["UID"])
        cal = (el.findtext(NS + "CalendarUID") or "").strip()
        if cal not in ("", "-1", project_cal):
            off_calendar[field["UID"]] = cal_names.get(cal, cal)
    return count, undated, off_calendar


def _a0923_cpm_022_undated_control() -> tuple[int, int]:
    """A's driving slack to T (off, Ignore constraints ON) on an all-UNDATED network -- the half of
    the tooltip the fix must keep: A (1 d) -> T and B (1 d, SNET Wed 2026-03-04 08:00) -> T, T 1 d,
    project start Mon 2026-03-02 08:00. By hand: with the pin B runs Wed, T starts Thu, so A (done
    Mon 17:00) has Tue + Wed = 960 min of slack; with the pin stripped B runs Mon and A has 0."""
    mon = dt.datetime(2026, 3, 2, 8, 0)
    sch = Schedule(
        name="undated control",
        project_start=mon,
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=480),
            Task(
                unique_id=2,
                name="B",
                duration_minutes=480,
                constraint_type=ConstraintType.SNET,
                constraint_date=dt.datetime(2026, 3, 4, 8, 0),
            ),
            Task(unique_id=3, name="T", duration_minutes=480),
        ),
        relationships=(
            Relationship(predecessor_id=1, successor_id=3),
            Relationship(predecessor_id=2, successor_id=3),
        ),
    )
    off = compute_driving_slack(sch, 3)[1].driving_slack_minutes
    on = compute_driving_slack(sch, 3, ignore_constraints=True)[1].driving_slack_minutes
    return off, on


def _a0923_cpm_022_driving(rows: dict[int, dict[str, Any]]) -> int:
    """How many served rows sit in the DRIVING tier."""
    return sum(1 for r in rows.values() if r["tier"] == "DRIVING")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-022: either SSI-parity ignore option re-bases every link of a fully-dated "
        "multi-calendar trace onto the project calendar (driving_slack.py:319-327; "
        "ignore_constraints forces it at :261), so /api/driving on Hard_File target 155 moves "
        "13 of 96 rows (DRIVING tier 10 -> 22) and the options-ON Large_Test_File_Leveled trace "
        "matches SSI's options-ON export on 777/783 rows where the un-flagged trace matches "
        "783/783 -- against the /path tooltip 'on a fully-dated file the trace is unchanged'"
    ),
)
def test_a0923_cpm_022_an_ssi_parity_ignore_option_leaves_a_fully_dated_trace_unchanged() -> None:
    """A0923-CPM-022 (finder id F-SSI-001) · CPM · T1 (option-gated).

    Claim: at 13b13f38, on the committed FULLY-DATED Hard_File golden (110 activities, 0 undated;
    UID 14 on '24 Hours' and UID 94 on 'Standard+Sat.', both in the trace to UID 155), ticking
    either SSI-parity option on /path (``GET /api/driving/Hard_File?target=155`` with
    ``&ignore_constraints=1`` or ``&ignore_leveling=1``) changes the served trace: 13 of 96 rows'
    slack moves -- 12 activities go from 1 d to 0 d and join DRIVING (tier 10 -> 22), UID 379 goes
    42 -> 41 d -- and 3 more (229, 262, 408) change only their on-path link flags. Mechanism:
    ``engine/driving_slack.py:319-327`` (``endpoint``) skips the stored-date-on-the-successor-
    calendar measurement under ``ignore_leveling_delay`` and reads every link end on the project
    calendar, and ``:261`` forces that mode under ``ignore_constraints``. In the engine 86 of the
    96 slacks fall by exactly 180 min (0.375 d; UID 211 7,620 -> 7,440 min); the served grid
    truncates to whole days (``int()`` in ``web/driving.py:_driving_data``), so UID 211 shows 15
    both ways and only the 13 rows that cross a whole day move. The same re-basing breaks the
    options-ON SSI reference: on the fully dated Large_Test_File_Leveled (1,723 activities, 138 on
    'ZIN Project Calendar'), the trace to UID 152 with both options ON (SSI's recorded settings)
    matches the 783-row SSI export at 0.01 d on 777 rows (UIDs 5246/5247/5248/5250/5251 +1 d,
    5268 -1 d); with the options OFF it matches 783/783.

    Authority: A2 -- the product's served contract, ``src/schedule_forensics/web/path.py:228``
    (Ignore constraints title): "SSI-parity option: strips constraint pins out of the CPM
    fallback that dates otherwise-undated tasks. Tasks with stored dates keep them — on a
    fully-dated file the trace is unchanged, matching SSI's own output with this option on
    (ADR-0251)"; ``:229`` (Ignore leveling delay title): "SSI-parity option: measures link gaps on
    the project-calendar date basis (stored dates first; CPM only for undated tasks). Stored
    leveled dates still govern — on a fully-dated file the trace is unchanged, matching SSI's own
    output with this option on (ADR-0251)"; ``web/driving.py:180`` "(a fully-dated file traces
    identically; ...)"; ``docs/adr/0251-ignore-toggles-copy-truth-and-page-family-alignment.md:59``
    "a fully-dated file traces identically". A1 -- SSI's own Directional Path export for
    Large Test File Leveled, focus UID 152, all 783 driving slacks transcribed in the committed
    ``tests/fixtures/golden/ssi_uid152_leveled/case.json`` whose ``_source`` records "Predecessors;
    Ignore constraints + Ignore leveling delay ON" (also ADR-0251:30-31 'captured with SSI's OWN
    "Ignore constraints" + "Ignore leveling delay" options **ON**'). The workbook itself records no
    option settings and the committed screenshot shows the (b) <=0 d run, so options-ON for the
    783-row run is the repo's recorded premise -- UNVERIFIED from the artifact itself; the
    assertion does not depend on it, because with the un-flagged trace pinned at 783/783 as a
    precondition, "flagged == SSI" is the same statement as "flagged == un-flagged" (A2).

    Deliberate-decision screen: the project-calendar basis under the flag is documented
    (ADR-0251:21-22 context: "only **6 of 783** slacks shift ... a project-vs-per-task
    **calendar-basis** artifact"; ADR-0463 D2,
    ``docs/adr/0463-wp6-six-ledger-highs-verified-five-fixed-one-widened-to-the-whole-app.md:40``:
    "`ignore_leveling_delay` still measures every endpoint on the project axis (ADR-0251)"), but
    the decision's stated premises -- "a fully-dated file traces identically" (ADR-0251:59) and the
    options-ON export "matches the **stored-date** trace" (ADR-0251:31) -- are falsified here by
    execution: the 6 rows ``test_ssi_leveled_uid152`` tolerates as "SSI
    calendar-handoff rounding" are exactly the rows the flags move. The engine docstring
    (``driving_slack.py:243`` "On a fully-dated single-calendar file") is correctly scoped; the
    tooltips, ``_driving_data`` docstring and ADR-0251 Decision 1 drop the qualifier, and the only
    route pin (``tests/web/test_path_options.py:104``) uses the single-calendar Project5.

    Control (precondition): the fix must keep the other half of the tooltip -- on an all-undated
    hand network Ignore constraints still strips a SNET pin from the CPM fallback (A's slack
    960 -> 0 min, hand-computed), so a "fix" that simply disables the options fails here instead of
    passing.

    Independence: the promise is the product's served copy, not the code path under test; the 783
    SSI values were written by the SSI MS Project add-on and transcribed into case.json; dating
    and calendars are read with ElementTree. Census (verifier recount): 8 committed multi-calendar
    fully-dated files with an SSI oracle, 259 distinct (file, UID) rows the flags move, 442 SSI
    observations (183 workbook + 259 embedded SSI log) -- SSI == un-flagged on all 442, == flagged
    on 0; single-calendar Project5 is flag-inert.
    """
    # -- control: the option still reaches an UNDATED task's CPM fallback (tooltip, first clause) --
    if _a0923_cpm_022_undated_control() != (960, 0):
        pytest.fail(
            f"precondition: Ignore constraints no longer strips the pin from an undated task's CPM "
            f"fallback (A's slack off / on {_a0923_cpm_022_undated_control()}, hand values (960, "
            "0))"
        )

    # -- arm A: the served /path trace on the fully-dated multi-calendar Hard_File golden --------
    raw = gzip.decompress((GOLDEN / "fuse_hardfile" / "Hard_File.mspdi.xml.gz").read_bytes())
    count, undated, off_calendar = _a0923_cpm_022_dating(raw)
    if count != 110 or undated:
        pytest.fail(f"precondition: Hard_File is no longer 110 fully-dated activities: {undated}")
    if not off_calendar:
        pytest.fail("precondition: Hard_File no longer puts any activity on a non-project calendar")

    client = TestClient(create_app(SessionState()))
    up = client.post("/upload", files={"files": ("Hard_File.mspdi.xml", raw, "text/xml")})
    if up.status_code != 200:
        pytest.fail(f"precondition: upload answered {up.status_code}")
    page = client.get("/path").text
    for control in ("pathIgnoreConstraints", "pathIgnoreLeveling"):
        title = re.search(rf'id={control} type=checkbox title="([^"]*)"', page)
        if title is None or _A0923_CPM_022_PROMISE not in title.group(1):
            pytest.fail(f"precondition: /path's {control} tooltip no longer makes the promise")

    def served(extra: str = "") -> dict[int, dict[str, Any]]:
        got = client.get(f"/api/driving/Hard_File?target=155{extra}")
        if got.status_code != 200:
            pytest.fail(f"precondition: /api/driving{extra or ''} answered {got.status_code}")
        return {r["unique_id"]: r for r in got.json()["rows"]}

    base = served()
    if 155 not in base or not {int(u) for u in off_calendar} & set(base):
        pytest.fail("precondition: the trace to 155 no longer holds a non-project-calendar task")
    changed: dict[str, list[int]] = {}  # rows that differ in ANY served field
    moved: dict[str, dict[int, tuple[object, object]]] = {}  # ... of which slack / tier moved
    tiers: dict[str, tuple[int, int]] = {}
    for flag in ("ignore_constraints", "ignore_leveling"):
        flagged = served(f"&{flag}=1")
        if set(flagged) != set(base):
            pytest.fail(f"precondition: {flag} changed the trace's membership")
        rows = sorted(uid for uid in base if flagged[uid] != base[uid])
        if rows:
            changed[flag] = rows
            shown = {
                uid: tuple((r[uid]["driving_slack_days"], r[uid]["tier"]) for r in (base, flagged))
                for uid in rows
            }
            moved[flag] = {uid: (off, on) for uid, (off, on) in shown.items() if off != on}
            tiers[flag] = (_a0923_cpm_022_driving(base), _a0923_cpm_022_driving(flagged))

    # -- arm B: the options-ON SSI reference on the fully-dated Large_Test_File_Leveled -----------
    leveled = GOLDEN / "ssi_uid152_leveled"
    case = json.loads((leveled / "case.json").read_text(encoding="utf-8"))
    if "Ignore constraints + Ignore leveling delay ON" not in case.get("_source", ""):
        pytest.fail("precondition: case.json no longer records SSI's options-ON settings")
    ssi = {int(u): float(v) for u, v in case["all_dependencies_driving_slack_by_uid"].items()}
    raw_l = gzip.decompress((leveled / "Large_Test_File_Leveled.mspdi.xml.gz").read_bytes())
    count_l, undated_l, off_l = _a0923_cpm_022_dating(raw_l)
    if count_l != 1723 or undated_l or not off_l:
        pytest.fail(
            f"precondition: Large_Test_File_Leveled is no longer 1,723 fully-dated activities "
            f"with a second calendar ({count_l}, {len(undated_l)} undated, {len(off_l)} off-cal)"
        )
    sch = parse_mspdi_text(raw_l.decode("utf-8-sig", errors="replace"))
    target = int(case["focus_task_uid"])

    def off_ssi(options_on: bool) -> dict[int, tuple[float, float]]:
        """{UID: (engine d, SSI d)} for every row off SSI's export by 0.01 d or more -- SSI's
        recorded settings: predecessors, both options ON, near-path bands 10 / 20 d."""
        results = compute_driving_slack(
            sch,
            target,
            secondary_max_days=10,
            tertiary_max_days=20,
            ignore_constraints=options_on,
            ignore_leveling_delay=options_on,
        )
        if set(results) != set(ssi):
            pytest.fail("precondition: the trace to 152 no longer has SSI's 783-row membership")
        return {
            uid: (round(float(results[uid].driving_slack_days), 4), round(value, 4))
            for uid, value in sorted(ssi.items())
            if abs(float(results[uid].driving_slack_days) - value) >= 0.01
        }

    if len(ssi) != 783 or off_ssi(options_on=False):
        pytest.fail("precondition: the un-flagged trace no longer reproduces SSI's 783 rows")
    misses = off_ssi(options_on=True)

    assert not changed and not misses, (
        f"a fully-dated multi-calendar trace changes under the SSI-parity options: Hard_File "
        f"target 155 rows that differ {changed}; DRIVING tier (off, on) {tiers}; slack / tier "
        f"moved {{uid: ((days, tier) off, on)}} {moved} (the rest differ only in their on-path "
        f"link flags); Large_Test_File_Leveled options ON vs SSI's options-ON export "
        f"{{uid: (engine d, SSI d)}} {misses} ({783 - len(misses)}/783 at 0.01 d; options OFF 783)"
    )


# --- A0923-CPM-023 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    gzip, re, xml.etree.ElementTree as ET, pathlib.Path, typing.Any, pytest,
#              fastapi.testclient.TestClient, parse_mspdi_text (schedule_forensics.importers.mspdi),
#              SessionState and create_app (schedule_forensics.web.app)
#   ALSO NEEDS ``import zipfile`` and
#              ``from schedule_forensics.engine.driving_slack import compute_driving_slack``
#              on the header (the committed header imports neither)
#   constants  REPO, GOLDEN (REPO / "tests" / "fixtures" / "golden")
#   fixture    the module-level autouse _air_gapped
# Inputs: the committed, non-CUI goldens tests/fixtures/golden/fuse_hardfile/Hard_File and
# ssi_hardfile_24h_uid155/Hard_File_updated3 + Hard_File_updated4_24h (.mspdi.xml.gz), and SSI's
# own Directional Path exports of those files, committed under 00_REFERENCE_INTAKE/ssi/ (read
# with zipfile + ElementTree, never through the product). No new fixture file; nothing CUI.

_A0923_CPM_023_FOCUS = 155
_A0923_CPM_023_SSI = REPO / "00_REFERENCE_INTAKE" / "ssi"
_A0923_CPM_023_XL = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
#: uploaded file name -> (committed golden, SSI's export of that file for focus UID 155)
_A0923_CPM_023_INPUTS = {
    "Hard_File.mspdi.xml": (
        "fuse_hardfile/Hard_File.mspdi.xml.gz",
        "Hard_File_Path_Trace_UID_155_Directional_Path_Analysis_2026-7-8-13-30-7.xlsx",
    ),
    "Hard_File_updated3.mspdi.xml": (
        "ssi_hardfile_24h_uid155/Hard_File_updated3.mspdi.xml.gz",
        "Hard File updated3_UID_155_Directional_Path_Analysis_2026-7-15.xlsx",
    ),
    "Hard_File_updated4_24h.mspdi.xml": (
        "ssi_hardfile_24h_uid155/Hard_File_updated4_24h.mspdi.xml.gz",
        "Hard_File_updated4 24 hour calendar_UID_155_Directional_Path_Analysis 2026-7-15.xlsx",
    ),
}
#: SSI's displayed Driving Slack for the six negative rows of the 24-hour export (sheet1 rows
#: 40, 41, 49, 50, 51, 52) -- re-read below as a precondition.
_A0923_CPM_023_SSI_NEGATIVE = {
    178: "-8.63541666666667 day",
    179: "-8.63541666666667 day",
    180: "-8.63541666666667 day",
    181: "-8.63541666666667 day",
    188: "-12.6354166666667 day",
    189: "-12.6354166666667 day",
}


def _a0923_cpm_023_ssi_slack(xlsx: str) -> dict[int, tuple[str, float]]:
    """SSI's own Directional Path export: UID -> (the Driving Slack cell as SSI wrote it, its
    value in days). Read with zipfile + ElementTree, independently of the product."""
    path = _A0923_CPM_023_SSI / xlsx
    if not path.is_file():
        pytest.fail(f"precondition: SSI's export {xlsx} is no longer committed")
    xl = _A0923_CPM_023_XL
    with zipfile.ZipFile(path) as z:
        strings = [
            "".join(t.text or "" for t in si.iter(xl + "t"))
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(xl + "si")
        ]
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    table = []
    for row in sheet.iter(xl + "row"):
        cells: dict[str, str] = {}
        for c in row.iter(xl + "c"):
            v = c.find(xl + "v")
            ref = re.sub(r"\d", "", c.get("r") or "")
            if v is not None and v.text is not None:
                cells[ref] = strings[int(v.text)] if c.get("t") == "s" else v.text
        table.append(cells)
    col = {name: ref for ref, name in table[0].items()} if table else {}
    if "Unique ID" not in col or "Driving Slack" not in col:
        pytest.fail(f"precondition: {xlsx} has no 'Unique ID' / 'Driving Slack' header")
    out: dict[int, tuple[str, float]] = {}
    for cells in table[1:]:
        text = cells.get(col["Driving Slack"], "").strip()
        m = re.fullmatch(r"(-?\d+(?:\.\d+)?) days?", text)
        if m is None:
            pytest.fail(
                f"precondition: {xlsx} writes a Driving Slack SSI format not read: {text!r}"
            )
        out[int(cells[col["Unique ID"]])] = (text, float(m.group(1)))
    return out


def _a0923_cpm_023_bands(label: str) -> tuple[set[int], set[int]]:
    """(the activities SSI shows at 0 <= slack < 1 working day, the activities SSI shows at
    NEGATIVE slack) for one upload. The first set is exactly what a '0 days' count may hold
    (ADR-0032 D1 floors a positive sub-day slack to 0 days -- not contested here). The engine
    must reproduce both sets UID-for-UID: a precondition, because this finding is about the
    label, not the numbers."""
    golden, xlsx = _A0923_CPM_023_INPUTS[label]
    ssi = _a0923_cpm_023_ssi_slack(xlsx)
    zero = {u for u, (_, d) in ssi.items() if u != _A0923_CPM_023_FOCUS and 0 <= d < 1}
    negative = {u for u, (_, d) in ssi.items() if d < 0}
    if any(d != 0 for text, d in ssi.values() if text in ("0 days", "0 day")):
        pytest.fail(f"precondition: SSI now shows a non-zero slack as '0 days' in {xlsx}")
    sch = parse_mspdi_text(gzip.decompress((GOLDEN / golden).read_bytes()).decode("utf-8"))
    per_day = sch.calendar.working_minutes_per_day
    minutes = {
        u: r.driving_slack_minutes
        for u, r in compute_driving_slack(sch, _A0923_CPM_023_FOCUS).items()
    }
    e_zero = {u for u, m in minutes.items() if u != _A0923_CPM_023_FOCUS and 0 <= m < per_day}
    e_neg = {u for u, m in minutes.items() if m < 0}
    if (e_zero, e_neg) != (zero, negative):
        pytest.fail(
            f"precondition: the engine no longer reproduces SSI's bands on {label} (0-day band "
            f"{len(e_zero)} vs SSI {len(zero)}, negative {sorted(e_neg)} vs SSI "
            f"{sorted(negative)}) -- the finding's premise moved"
        )
    return zero, negative


def _a0923_cpm_023_render(labels: tuple[str, ...]) -> tuple[str, list[str]]:
    """Upload the goldens (oldest data date first) into one session; return the rendered
    ``/driving-path?target=155`` page and the one-click engine answer's fact texts."""
    client = TestClient(create_app(SessionState()))
    for label in labels:
        raw = gzip.decompress((GOLDEN / _A0923_CPM_023_INPUTS[label][0]).read_bytes())
        up = client.post("/upload", files={"files": (label, raw, "text/xml")})
        if up.status_code != 200:
            pytest.fail(f"precondition: uploading {label} answered {up.status_code}")
    page = client.get(f"/driving-path?target={_A0923_CPM_023_FOCUS}")
    ask = client.get("/api/driving-path", params={"uid": _A0923_CPM_023_FOCUS})
    if page.status_code != 200 or ask.status_code != 200:
        pytest.fail(
            f"precondition: /driving-path {page.status_code}, /api/driving-path {ask.status_code}"
        )
    banner = re.search(r'"dp-file-banner">Driving path computed on <b>([^<]+)</b>', page.text)
    if banner is None or banner[1] != labels[-1]:
        pytest.fail(f"precondition: the tiers panel no longer speaks for {labels[-1]} ({banner})")
    return page.text, [str(f.get("text", "")) for f in ask.json().get("facts", [])]


_A0923_CPM_023_ROW = r"<tr><td class=num>(\d+)</td><td>.*?</td><td class=num>(-?[\d.]+)</td>"


def _a0923_cpm_023_zero_day_claims(
    page: str, facts: list[str], latest: str
) -> list[tuple[str, str, int, list[tuple[int, float | None]]]]:
    """Every count the page and the one-click answer attach to '0 days' / '0d' of driving slack,
    as (surface, the version it speaks for, the count it states, the (UID, slack shown -- None
    where the surface names the UID without a value) it lists)."""
    claims: list[tuple[str, str, int, list[tuple[int, float | None]]]] = []
    for m in re.finditer(r"(\d+) activities sit at 0 days of driving slack to ", page):
        claims.append(("/driving-path tiers take", latest, int(m[1]), []))
    for m in re.finditer(
        r"Only (.+?) carries this target, .*?: (\d+) activities at 0 days\.", page
    ):
        claims.append(("/driving-path trend take", m[1], int(m[2]), []))
    for m in re.finditer(
        r"<h3>([^<]*)<span class=muted>\((\d+) &middot; 0 days\)</span></h3>"
        r"(<table.*?</table>|<p class=muted>none</p>)",
        page,
        re.S,
    ):
        rows: list[tuple[int, float | None]] = [
            (int(u), float(d)) for u, d in re.findall(_A0923_CPM_023_ROW, m[3])
        ]
        claims.append((f"/driving-path column '{m[1].strip()}'", latest, int(m[2]), rows))
    take = re.search(
        r"The driving \(0d\) tier holds (\d+) activities in (.+?), against (\d+) in (.+?) &mdash;",
        page,
    )
    if take:
        claims.append(("/driving-path trend take", take[2], int(take[1]), []))
        claims.append(("/driving-path trend take", take[4], int(take[3]), []))
    trend = page.find("Driving-slack degradation trend")
    table = re.search(r"<table class=card-table>(.*?)</table>", page[trend:], re.S)
    if trend >= 0 and table:
        heads = re.findall(r"<th scope=col>(.*?)</th>", table[1])
        col = heads.index("Driving (0d)") if "Driving (0d)" in heads else -1
        for body in re.findall(r"<tr><td>.*?</tr>", table[1]) if col >= 0 else []:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", body)
            if cells[col].isdigit():
                claims.append(("/driving-path trend 'Driving (0d)'", cells[0], int(cells[col]), []))
    for fact in facts:
        hit = re.search(
            r"comprises (\d+) activit(?:y|ies) driving it with 0 days of driving slack"
            r"(?: \(e\.g\. ([^)]*)\))?",
            fact,
        )
        if hit:
            named: list[tuple[int, float | None]] = [
                (int(u), None) for u in re.findall(r"UID (\d+)", hit[2] or "")
            ]
            claims.append(("/api/driving-path summary", latest, int(hit[1]), named))
        if "(activities with 0 days of driving slack to the focus)" in fact:
            for label, n in re.findall(
                r"(\S+) \(data date [^)]*\) (\d+) activit(?:y|ies) driving it", fact
            ):
                claims.append(("/api/driving-path series", label, int(n), []))
    return claims


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-023: /driving-path and the one-click driving-path answer count and list "
        "NEGATIVE driving slack as '0 days' ('47 activities sit at 0 days of driving slack', "
        "'Critical / driving (47 . 0 days)' listing UIDs 188/189 at -12.6, 'Driving (0d)' 47, "
        "'comprises 47 ... with 0 days (e.g. UID 178, 179, 180)') where SSI shows those six at "
        "-8.635 / -12.635 day and the 0-day band holds 41"
    ),
)
def test_a0923_cpm_023_negative_driving_slack_is_never_counted_at_0_days() -> None:
    """A0923-CPM-023 (finder id F-SSI-002) · CPM (presentation of the driving-slack tiers) · T2.

    Claim (verifier's narrowed claim, the undocumented half): at 13b13f38, with the committed
    goldens ``ssi_hardfile_24h_uid155/Hard_File_updated3`` and ``Hard_File_updated4_24h`` loaded,
    ``/driving-path?target=155`` says "47 activities sit at 0 days of driving slack to Customer
    Service Program Development COMPLETE -- the driving path itself", heads its first column
    "Critical / driving (47 · 0 days)" and lists UIDs 188/189 at -12.6 and 178-181 at -8.6 in it,
    and its trend reads "Driving (0d)" 44 -> 47 (+3, flagged as erosion); the one-click answer
    (``/api/driving-path``, the Ask panel's "Driving path" button) says the path "comprises 47
    activities driving it with 0 days of driving slack (e.g. UID 178, UID 179, UID 180)" -- the
    three it names sit at -8.6 d -- and its series defines each version's count as "activities
    with 0 days of driving slack". SSI's own export of the same file shows those six at
    -8.63541666666667 / -12.6354166666667 day; the band SSI and the engine both put at
    0 <= slack < 1 day holds 41. Mechanism: the DRIVING tier is ``slack <= 0``
    (``engine/driving_slack.py:159`` ``_classify``, ``:396`` ``on_driving_path``) and every
    surface above prints its size under a "0 days" label.

    Authority: A1 -- SSI's Directional Path export of that file,
    ``00_REFERENCE_INTAKE/ssi/Hard_File_updated4 24 hour calendar_UID_155_Directional_Path_Analysis
    2026-7-15.xlsx``, sheet1 column G 'Driving Slack': rows 40, 41, 49, 50 (UIDs 179, 180, 178,
    181) ``-8.63541666666667 day``, rows 51, 52 (UIDs 189, 188) ``-12.6354166666667 day``; SSI
    writes "0 days" only where the value is exactly 0 (42 of 42 cells). A2 -- the product's own
    copy: ``web/driving.py:595`` "{n_drv} activities sit at 0 days of driving slack to {fname}
    &mdash; the driving path itself", ``web/driving.py:540`` ``("driving", "Critical / driving",
    "0 days")``, ``web/driving.py:720`` "The driving (0d) tier holds", ``web/driving.py:742``
    "Driving (0d)", ``ai/driving_facts.py:94`` "driving it with 0 days of driving slack",
    ``ai/driving_facts.py:384`` "(activities with 0 days of driving slack to the focus)"; the
    summary's own pin, added with it in #216, is named ``tests/ai/test_driving_facts.py:39``
    ``test_summary_counts_only_zero_slack_drivers`` (its network has no negative slack); the
    tier itself is ``docs/adr/0011-m6-driving-slack-ssi-parity.md:26`` "DRIVING (slack ≤ 0)" --
    documented, and not contested: a negative slack may stay in the tier, but it is not 0 days.

    Deliberately NOT asserted: whether a POSITIVE sub-day slack belongs at "0 days" -- ADR-0032
    D1 floors it to 0 by design (``test_subday_slack_is_driving_like_ssi_displays_it``); every
    committed SSI output contradicts that decision's premise ("SSI's display axis is whole
    days"), but the operator's original 4-vs-66 file is not committed (UNVERIFIED), so the
    control below COUNTS those rows at 0 days (Hard_File UID 14 at 0.625 d, updated3 UIDs
    178-181/188/189 at 0.8625 d). Independence: every expected count comes from SSI's exports,
    read with zipfile + ElementTree; the engine is used only to prove it reproduces SSI's bands.
    """
    # control: two versions with NO negative slack. Every '0 days' COUNT surface must be
    # recognised (so the patterns read the real copy -- a reword that keeps the false count fails
    # here by name, it cannot pass) and must state SSI's 0-day band. The series' parenthetical
    # definition is checked wherever it still reads "0 days" but may be reworded (a true
    # "0 days or negative" definition is a correct fix).
    control = ("Hard_File.mspdi.xml", "Hard_File_updated3.mspdi.xml")
    zero = {label: _a0923_cpm_023_bands(label)[0] for label in control}
    page, facts = _a0923_cpm_023_render(control)
    claims = _a0923_cpm_023_zero_day_claims(page, facts, control[-1])
    wanted = {
        "/driving-path tiers take",
        "/driving-path column 'Critical / driving'",
        "/driving-path trend take",
        "/driving-path trend 'Driving (0d)'",
        "/api/driving-path summary",
    }
    if not wanted <= {c[0] for c in claims}:
        pytest.fail(
            f"precondition (control): the '0 days' surfaces read are "
            f"{sorted({c[0] for c in claims})}, not {sorted(wanted)} -- the copy moved"
        )
    off = [(s, v, n) for s, v, n, _ in claims if v not in zero or n != len(zero[v])]
    if off:
        pytest.fail(f"precondition (control): a no-negative trace mis-counts its 0-day band {off}")

    # the witness: the 24-hour-calendar update, in which six predecessors carry NEGATIVE slack
    witness = ("Hard_File_updated3.mspdi.xml", "Hard_File_updated4_24h.mspdi.xml")
    bands = {label: _a0923_cpm_023_bands(label) for label in witness}
    negative = bands[witness[-1]][1]
    ssi = _a0923_cpm_023_ssi_slack(_A0923_CPM_023_INPUTS[witness[-1]][1])
    if {u: ssi[u][0] for u in negative} != _A0923_CPM_023_SSI_NEGATIVE:
        pytest.fail(
            f"precondition: SSI's negative rows moved: { {u: ssi[u][0] for u in negative} }"
        )
    page, facts = _a0923_cpm_023_render(witness)
    start = page.find("Driving tiers to")
    panel = page[start : page.find("Driving-slack degradation trend")] if start >= 0 else ""
    shown = {int(u): float(d) for u, d in re.findall(_A0923_CPM_023_ROW, panel)}
    hidden = {u: shown.get(u) for u in negative if not shown.get(u, 0.0) < 0}
    if not panel or hidden:
        pytest.fail(f"precondition: the tiers panel no longer shows the negative rows {hidden}")

    wrong = []
    for surface, version, count, listed in _a0923_cpm_023_zero_day_claims(page, facts, witness[-1]):
        if version not in bands:
            pytest.fail(f"precondition: {surface} speaks for an unknown version {version!r}")
        band, neg = bands[version]
        bad = [(u, d) for u, d in listed if u in neg or (d is not None and d < 0)]
        if count != len(band) or bad:
            wrong.append(
                f"{surface} [{version}] says {count} at 0 days (0-day band {len(band)})"
                + (f", listing negative {bad}" if bad else "")
            )
    assert not wrong, (
        "negative driving slack is counted at '0 days' (SSI shows "
        f"{sorted(set(_A0923_CPM_023_SSI_NEGATIVE.values()))}): {wrong}"
    )


# --- A0923-CPM-024 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py, and on nothing else:
#   imports    re, xml.etree.ElementTree as ET, pytest, TestClient (fastapi.testclient),
#              SessionState / create_app (schedule_forensics.web.app)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Inputs: the committed, non-CUI goldens project2_5/Project2.mspdi.xml and Project5.mspdi.xml
# (plain XML); one in-memory edit of Project5 (UID 67 <Active>1 -> 0). No new fixture file.

_A0923_CPM_024_PANEL = "Driving-slack degradation trend"
_A0923_CPM_024_ROW = re.compile(
    r"<tr><td>([^<]*)</td><td>[^<]*</td><td class=num>([^<]*)</td><td class=num>([^<]*)</td>"
    r"<td class=num>([^<]*)</td><td class=num>(.*?)</td></tr>",
    re.S,
)


def _a0923_cpm_024_flags(raw: bytes, uid: int) -> tuple[str, str]:
    """(Summary, Active) of one <Task>, read from the raw MSPDI with ElementTree."""
    for el in ET.fromstring(raw).iter(NS + "Task"):
        if (el.findtext(NS + "UID") or "").strip() == str(uid):
            summary = (el.findtext(NS + "Summary") or "").strip()
            return summary, (el.findtext(NS + "Active") or "").strip()
    pytest.fail(f"precondition: UID {uid} is no longer a <Task> of the golden")


def _a0923_cpm_024_deactivate(raw: bytes, uid: int) -> bytes:
    """``raw`` with ONLY that task's <Active>1</Active> flipped to 0 (everything else identical)."""
    text = raw.decode("utf-8-sig")
    block = re.search(rf"<Task>\s*<UID>{uid}</UID>.*?</Task>", text, re.S)
    if block is None or block.group(0).count("<Active>1</Active>") != 1:
        pytest.fail(f"precondition: UID {uid}'s <Task> no longer carries one <Active>1</Active>")
    edited = block.group(0).replace("<Active>1</Active>", "<Active>0</Active>")
    return text.replace(block.group(0), edited, 1).encode("utf-8")


def _a0923_cpm_024_trend(
    client: TestClient, target: int
) -> tuple[str | None, dict[str, tuple[str, ...]], bool]:
    """(take text or None, {version: (driving, secondary, tertiary, delta)}, tiers panel shown) of
    /driving-path?target=... -- the panel's own take and table, tags stripped."""
    page = client.get(f"/driving-path?target={target}")
    if page.status_code != 200:
        pytest.fail(f"precondition: /driving-path?target={target} answered {page.status_code}")
    html = page.text
    tiers = "Driving tiers to" in html
    at = html.find(_A0923_CPM_024_PANEL)
    if at < 0:
        return None, {}, tiers
    take = re.search(r"<p class=sf-take data-no-i18n>(.*?)</p>", html[at:], re.S)
    table = re.search(r"<table class=card-table>(.*?)</table>", html[at:], re.S)
    if take is None or table is None:
        pytest.fail(f"precondition: the trend panel for {target} lost its take or its table")
    rows = {
        label: tuple(re.sub(r"<[^>]+>", "", cell).strip() for cell in cells)
        for label, *cells in _A0923_CPM_024_ROW.findall(table.group(1))
    }
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", take.group(1))).strip(), rows, tiers


def _a0923_cpm_024_session(files: dict[str, bytes]) -> TestClient:
    client = TestClient(create_app(SessionState()))
    for name, raw in files.items():
        up = client.post("/upload", files={"files": (name, raw, "text/xml")})
        if up.status_code != 200:
            pytest.fail(f"precondition: upload of {name} answered {up.status_code}")
    return client


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-024: /driving-path's 'Driving-slack degradation trend' swallows the KeyError "
        "compute_driving_slack raises for a target outside the logic network (summary / inactive; "
        "web/driving.py:685-686 'except (KeyError, ValueError): pass') and prints the initialised "
        "0 / 0 / 0 as measured: summary targets 2 and 10 read 'holds 0 activities ... against 0' "
        "on Project2 + Project5, and UID 67 made inactive in Project5 reads 0 against 25 with a "
        "green delta -25"
    ),
)
def test_a0923_cpm_024_an_untraceable_target_is_never_shown_as_zero_tier_counts() -> None:
    """A0923-CPM-024 (finder id F-SSI-003) · CPM · T2 (latent T1).

    Claim: at 13b13f38, with the committed goldens Project2 + Project5 loaded and a SUMMARY UID as
    the target (``GET /driving-path?target=2`` or ``10``), the 'Driving-slack degradation trend'
    panel prints Driving 0 / Secondary 0 / Tertiary 0 for BOTH versions, a delta of 0 and the take
    "The driving (0d) tier holds 0 activities in Project5.mspdi.xml, against 0 in
    Project2.mspdi.xml — the first loaded version that carries this target", while the SAME page
    omits its tiers panel for that target. No trace ran: ``compute_driving_slack`` raised
    ``KeyError`` (a summary / inactive UID is not in the logic network) and
    ``web/driving.py:685-686`` ``except (KeyError, ValueError): pass`` kept the initialised zero
    counts; the only presence test (``:673``, ``target not in sch.tasks_by_id``) passes a summary
    or inactive UID. Latent T1 shape (verifier's alternative witness, second arm here): with UID 67
    set inactive in the later version only, the panel reads "holds 0 activities in Project5...,
    against 25 in Project2" with a green ▼-25 delta -- an untraced version presented as a
    25-activity improvement. With only a target, no corridor renders (the page shows the 'Enter a
    source and a target' hint); the corridor's 'target activity absent' needs a source as well
    (verifier).

    Authority: A2 -- ``docs/adr/0306-an-absent-figure-is-not-a-zero.md:37-39`` (Decision): "A
    directional or quantitative statement is only ever made when the underlying figure is actually
    present. Where a value is absent and the tool cannot compute the truth, it says so — it does
    not guess a plausible one."; ``CLAUDE.md:214``: "Optional date/cost fields default to `None`
    meaning "the source didn't provide it" — never assume 0."; ``docs/adr/0463-wp6-six-ledger-
    highs-verified-five-fixed-one-widened-to-the-whole-app.md:57`` (Decision 6): "the target's
    presence test is the network's membership (non-summary AND active)"; the panel's own contract,
    ``src/schedule_forensics/web/driving.py:661-662``: "the count of activities at each
    driving-slack tier ... over the loaded versions". The same repo already does it right for the
    same exception one module over: ``ai/driving_facts.py:249-251`` appends the version with
    ``unreadable=True`` instead of a zero, and ``web/driving.py:519-521`` (the tiers panel on the
    same page) returns ``""``. (Read at 13b13f38, 2026-09-28.)

    Deliberate-decision screen: no ADR keeps the zeros (ADR-0113 / ADR-0351 only extract and cover
    the helper); ADR-0306 and ADR-0463 D6 require the opposite. Not HELD, not a duplicate.

    Control (precondition): a real activity target (UID 67) on the same two goldens still renders
    measured counts in both versions, so a "fix" that deletes the panel fails here instead of
    passing. Census (finder, re-derived by the assembler): 2 swallowing sites of the
    ``compute_driving_slack`` KeyError that present an untraced version as measured --
    ``web/driving.py`` ``_driving_tier_trend`` (this test) and ``web/evolution.py``'s
    ``/api/evolution?tier=`` stepper (empty tier membership per version); every summary UID of
    every committed multi-version golden reaches the first from the /driving-path form.
    """
    p2 = (GOLDEN / "project2_5" / "Project2.mspdi.xml").read_bytes()
    p5 = (GOLDEN / "project2_5" / "Project5.mspdi.xml").read_bytes()
    for name, raw in (("Project2", p2), ("Project5", p5)):
        for uid in (2, 10):
            if _a0923_cpm_024_flags(raw, uid) != ("1", "1"):
                pytest.fail(f"precondition: {name} UID {uid} is no longer an active summary")
        if _a0923_cpm_024_flags(raw, 67) != ("0", "1"):
            pytest.fail(f"precondition: {name} UID 67 is no longer an active activity")
    p5_off = _a0923_cpm_024_deactivate(p5, 67)
    if _a0923_cpm_024_flags(p5_off, 67) != ("0", "0"):
        pytest.fail("precondition: the in-memory edit did not set UID 67 inactive")

    wrong: dict[str, object] = {}
    client = _a0923_cpm_024_session({"Project2.mspdi.xml": p2, "Project5.mspdi.xml": p5})

    # -- control: a traceable target is measured in both versions (the panel must survive) -------
    _take, rows, tiers = _a0923_cpm_024_trend(client, 67)
    measured = [r for label, r in rows.items() if label.startswith("Project")]
    if (
        not tiers
        or len(measured) != 2
        or not all(r[0].isdigit() and int(r[0]) > 0 for r in measured)
    ):
        pytest.fail(f"precondition: target 67 is no longer measured in both versions {rows}")

    # -- arm A: summary targets (in the task table, outside the logic network) in both versions --
    for target in (2, 10):
        take, rows, tiers = _a0923_cpm_024_trend(client, target)
        counted = {label: r for label, r in rows.items() if any(c.isdigit() for c in r[:3])}
        if counted or (take is not None and re.search(r"\bholds 0 activities\b", take)):
            wrong[f"summary target {target}"] = {
                "take": take,
                "rows (driving, secondary, tertiary, delta)": counted,
                "tiers panel shown": tiers,
            }

    # -- arm B: the target goes inactive in the later version only ------------------------------
    client_b = _a0923_cpm_024_session(
        {"Project2.mspdi.xml": p2, "Project5_uid67_inactive.mspdi.xml": p5_off}
    )
    take, rows, tiers = _a0923_cpm_024_trend(client_b, 67)
    base = rows.get("Project2.mspdi.xml")
    if base is None or not base[0].isdigit() or int(base[0]) == 0:
        pytest.fail(f"precondition: Project2's measured row for 67 is gone {rows}")
    later = rows.get("Project5_uid67_inactive.mspdi.xml")
    if later is not None and (any(c.isdigit() for c in later[:3]) or re.search(r"\d", later[3])):
        wrong["UID 67 inactive in the later version"] = {
            "take": take,
            "rows (driving, secondary, tertiary, delta)": rows,
            "tiers panel shown": tiers,
        }

    assert not wrong, (
        f"the degradation trend prints counts for versions it never traced (compute_driving_slack "
        f"raised KeyError; the counts are the initialised zeros): {wrong}"
    )


# --- A0923-CPM-025 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py plus one import it does
# not carry yet (marked NEW):
#   imports    re, xml.etree.ElementTree as ET, pytest, TestClient (fastapi.testclient),
#              compute_cpm (schedule_forensics.engine.cpm), parse_mspdi_text
#              (schedule_forensics.importers.mspdi), SessionState / create_app (web.app)
#              NEW: CPMError (schedule_forensics.engine.cpm)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Input: the committed, non-CUI golden evm/EVM1.mspdi.xml (plain XML) with one link inserted in
# memory, and an inline summary-only MSPDI. No new fixture file.

#: the resolver's notice (web/app.py:2665-2672) up to the names it lists
_A0923_CPM_025_NOTICE = re.compile(
    r'<div class="notice err">Skipped \(network cannot be solved, or holds no schedulable '
    r"activity — see each report for the reason\): ([^<]*)</div>"
)
#: the /driving-path early-return text (web/app.py:4046-4047): an instruction to load a schedule
_A0923_CPM_025_NOTHING_LOADED = "Load a schedule to trace the driving path between two activities."
#: the six sibling HTML routes with the same empty-population early return (they name the file)
_A0923_CPM_025_SIBLINGS = (
    "/trend",
    "/volatility",
    "/performance",
    "/forecast",
    "/brief",
    "/briefing",
)

_A0923_CPM_025_SUMMARY_ONLY = (
    '<?xml version="1.0" encoding="UTF-8"?><Project xmlns="http://schemas.microsoft.com/project">'
    "<Name>S</Name><StartDate>2024-01-01T08:00:00</StartDate><Tasks>"
    "<Task><UID>0</UID><ID>0</ID><Name>S</Name><Summary>1</Summary><OutlineLevel>0</OutlineLevel>"
    "</Task><Task><UID>1</UID><ID>1</ID><Name>Phase</Name><Summary>1</Summary>"
    "<OutlineLevel>1</OutlineLevel><Start>2024-01-01T08:00:00</Start>"
    "<Finish>2024-01-01T17:00:00</Finish></Task></Tasks></Project>"
)


def _a0923_cpm_025_preds(raw: str, uid: int) -> list[str] | None:
    """The PredecessorUIDs of one non-summary <Task> (None when it is absent or a summary)."""
    for el in ET.fromstring(raw.encode("utf-8")).iter(NS + "Task"):
        if (el.findtext(NS + "UID") or "").strip() == str(uid):
            if (el.findtext(NS + "Summary") or "").strip() == "1":
                return None
            return [
                (p.findtext(NS + "PredecessorUID") or "").strip()
                for p in el.iter(NS + "PredecessorLink")
            ]
    return None


def _a0923_cpm_025_cyclic_evm1() -> str:
    """EVM1 with one extra FS link 23 -> 18 (18 already reaches 23), inserted before </Task>."""
    raw = (GOLDEN / "evm" / "EVM1.mspdi.xml").read_text(encoding="utf-8-sig")
    if _a0923_cpm_025_preds(raw, 18) != ["17"] or _a0923_cpm_025_preds(raw, 23) is None:
        pytest.fail("precondition: EVM1's UID 18 / 23 rows are no longer the activities they were")
    task = re.search(r"(<Task>\s*<UID>18</UID>.*?)(</Task>)", raw, re.S)
    if task is None:
        pytest.fail("precondition: EVM1 no longer carries a <Task> with UID 18")
    link = (
        "<PredecessorLink><PredecessorUID>23</PredecessorUID><Type>1</Type>"
        "<CrossProject>0</CrossProject><LinkLag>0</LinkLag><LagFormat>7</LagFormat>"
        "</PredecessorLink>"
    )
    return raw.replace(task.group(0), task.group(1) + link + task.group(2), 1)


def _a0923_cpm_025_client(files: dict[str, str]) -> TestClient:
    client = TestClient(create_app(SessionState()))
    for name, text in files.items():
        up = client.post("/upload", files={"files": (name, text.encode("utf-8"), "text/xml")})
        if up.status_code != 200:
            pytest.fail(f"precondition: upload of {name} answered {up.status_code}")
    return client


def _a0923_cpm_025_named(html: str) -> str:
    """The names the resolver's skipped notice lists on a page ('' when there is no notice)."""
    notice = _A0923_CPM_025_NOTICE.search(html)
    return notice.group(1) if notice else ""


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-025: when every loaded schedule is refused (a logic cycle, or no schedulable "
        "activity), GET /driving-path returns 'Load a schedule to trace the driving path between "
        "two activities.' and never names the refused file (web/app.py:4041-4048 returns before "
        "_skipped_notice), while its chrome says the page is computed from that file and the six "
        "sibling pages print 'Skipped (network cannot be solved ...): EVM1_cycle'"
    ),
)
def test_a0923_cpm_025_a_refused_population_is_named_not_reported_as_nothing_loaded() -> None:
    """A0923-CPM-025 (finder id F-SSI-004) · CPM · T4 (latent on the committed corpus, live on any
    refused upload).

    Claim: at 13b13f38, when every loaded schedule is refused by the resolver -- the committed EVM1
    golden plus one back-link 23 -> 18 (``compute_cpm`` raises ``CPMError: schedule logic contains
    a cycle``), or a file with no schedulable activity -- ``GET /driving-path`` (bare, with a
    target, with source + target, and with ``&file=``) answers "Load a schedule to trace the
    driving path between two activities." and never names the refused file, while the same page's
    chrome says "All data on this page is computed from: EVM1_cycle.mspdi.xml". Mechanism:
    ``web/app.py:4041-4048`` returns on the empty ``_solvable_versions()`` population BEFORE
    ``_skipped_notice(skipped)`` (applied at ``:4098`` only on the non-empty branch; the ``?file=``
    branch at ``:4064-4073`` is never reached). The six sibling HTML routes with the same
    empty-population early return (/trend, /volatility, /performance, /forecast, /brief,
    /briefing) print the notice naming the file and ask for an ANALYZABLE schedule.

    Authority: A2 -- ``docs/adr/0467-wp6b-the-ledger-tail-verified-by-execution-eleven-fixed-
    red-first-six-refuted.md:23`` (row CPM-04): "every multi-version resolver (...) skips a
    FILE with no schedulable activity by name (the skipped notice names it)"; the notice,
    ``src/schedule_forensics/web/app.py:2670-2671``: "Skipped (network cannot be solved, or holds
    no schedulable activity — see each report for the reason): {names}", applied by 6 of the 7
    HTML routes that early-return on an empty ``_solvable_versions()`` population; the page's own
    chrome (``web/chrome.py:696``) naming the loaded file as the page's data source. (Read at
    13b13f38, 2026-09-28.) Deliberate-decision screen: no ADR exempts /driving-path (ADR-0382
    moved the module only); not HELD, not a duplicate (A0923-WEB-001/002 are other mechanisms).

    Control (precondition): with a solvable file loaded beside the cyclic one, /driving-path
    prints the notice naming EVM1_cycle -- the naming exists and works on the non-empty branch --
    and the JSON sibling refuses loudly (``/api/driving/EVM1_cycle`` answers 422 with the cycle
    reason). Census (re-derived): 23 ``_solvable_versions()`` calls in web/app.py; 7 HTML routes
    early-return on an empty/insufficient population; 6 name the refused file; /driving-path does
    not. The committed corpus solves 44/44, so this is latent on committed files and live on any
    refused upload.
    """
    cyclic = _a0923_cpm_025_cyclic_evm1()
    sch = parse_mspdi_text(cyclic)
    if not any(r.predecessor_id == 23 and r.successor_id == 18 for r in sch.relationships):
        pytest.fail("precondition: the importer no longer carries the inserted 23 -> 18 link")
    try:
        compute_cpm(sch)
    except CPMError:
        pass
    else:
        pytest.fail("precondition: the CPM no longer refuses the cyclic EVM1")
    empty = parse_mspdi_text(_A0923_CPM_025_SUMMARY_ONLY)
    if any(not t.is_summary for t in empty.tasks):
        pytest.fail("precondition: the summary-only file now carries a schedulable activity")

    # -- control: the notice names the refused file whenever something else still solves --------
    evm1 = (GOLDEN / "evm" / "EVM1.mspdi.xml").read_text(encoding="utf-8-sig")
    mixed = _a0923_cpm_025_client({"EVM1.mspdi.xml": evm1, "EVM1_cycle.mspdi.xml": cyclic})
    if "EVM1_cycle" not in _a0923_cpm_025_named(mixed.get("/driving-path").text):
        pytest.fail(
            "precondition: /driving-path no longer names a refused file beside a solvable one"
        )
    if mixed.get("/api/driving/EVM1_cycle?target=25").status_code != 422:
        pytest.fail("precondition: /api/driving no longer refuses the cyclic file with a 422")

    wrong: dict[str, dict[str, object]] = {}
    cases = (
        ("EVM1_cycle", cyclic, ("", "?target=25", "?source=17&target=25", "?file=EVM1_cycle")),
        ("SummaryOnly", _A0923_CPM_025_SUMMARY_ONLY, ("", "?target=1", "?file=SummaryOnly")),
    )
    for key, text, shapes in cases:
        client = _a0923_cpm_025_client({f"{key}.mspdi.xml": text})
        page = client.get("/driving-path").text
        if f"All data on this page is computed from: <b>{key}.mspdi.xml</b>" not in page:
            pytest.fail(f"precondition: /driving-path's chrome no longer names {key} as its source")
        for route in [f"/driving-path{q}" for q in shapes] + list(_A0923_CPM_025_SIBLINGS):
            html = client.get(route).text
            named = _a0923_cpm_025_named(html)
            if key not in named or _A0923_CPM_025_NOTHING_LOADED in html:
                wrong.setdefault(key, {})[route] = {
                    "skipped notice names": named or None,
                    "says 'Load a schedule to trace ...'": _A0923_CPM_025_NOTHING_LOADED in html,
                }

    assert not wrong, (
        f"a page whose every loaded schedule was refused does not name the refused file (the "
        f"chrome names it as the data source; the six siblings do): {wrong}"
    )


# --- A0923-CPM-026 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py plus imports it does not
# carry yet (marked NEW):
#   imports    gzip, pytest, compute_cpm (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi)
#              NEW: driving_path_between (schedule_forensics.engine.driving_path);
#              compute_driving_slack (schedule_forensics.engine.driving_slack)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden")
#   fixture    the module-level autouse _air_gapped
# Inputs: the committed, non-CUI goldens ssi_hardfile_24h_uid155/Hard_File_updated4_24h.mspdi.xml.gz
# and fuse_hardfile/Hard_File.mspdi.xml.gz. No new fixture file.

#: (golden, source, target, the engine's driving slack in minutes) -- driving sources whose slack
#: to the target is not 0: a NEGATIVE one (-4,146 min = -8.64 d) and a POSITIVE sub-day one (479
#: min, rounded to 1.00 d before int()); both sit ON the target's driving path.
_A0923_CPM_026_WITNESSES = (
    ("ssi_hardfile_24h_uid155/Hard_File_updated4_24h.mspdi.xml.gz", 178, 155, -4146),
    ("fuse_hardfile/Hard_File.mspdi.xml.gz", 323, 321, 479),
)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-026: driving_path_between returns source_slack_days = int(driving_slack_days) "
        "for a DRIVING source too (engine/driving_path.py:114), against the field contract '0 "
        "while it drives' (:50-51): source 178 -> 155 on Hard_File_updated4_24h (drives, -4,146 "
        "min) returns -8, source 323 -> 321 on Hard_File (drives, 479 min) returns 1"
    ),
)
def test_a0923_cpm_026_a_driving_source_reports_zero_whole_days_of_slack() -> None:
    """A0923-CPM-026 (finder id F-SSI-005) · CPM · T3 (latent: no served surface prints the field
    while it drives).

    Claim: at 13b13f38, ``driving_path_between`` (``engine/driving_path.py:114``) sets
    ``DrivingPathBetween.source_slack_days = int(results[source].driving_slack_days)`` for EVERY
    connected source, including one ON the target's driving path, although the field's contract
    says the value is ``0`` while the source drives. On the committed 24-hour golden
    Hard_File_updated4_24h, source 178 -> target 155 drives (corridor of 46 activities) with a
    driving slack of -4,146 min (-8.64 d) and the field reads -8; on the committed Hard_File
    golden, source 323 -> target 321 drives with 479 min (under one working day; 2-dp rounding
    makes it 1.00 d) and the field reads +1. Verifier recount (all targets, the 36 corpus files
    of <= 400 activities): 2,237 of 41,114 driving (source, target) pairs carry a non-zero value,
    -32 .. +1 (the finder's four-focus sample was 54). Latent: ``DrivingPathSnapshot.status``
    prints the field only on the NOT-driving branch, and /driving-path?source=178&target=155
    reads "a driving path of 46 activities" -- no displayed figure is wrong today.

    Authority: A2 -- ``src/schedule_forensics/engine/driving_path.py:50-52``: "#: source's
    driving slack to target in whole working days, when connected (``0`` while it drives);
    ``None`` when not connected or an endpoint is absent." The module's own tests assert 0 for a
    driving source (``tests/engine/test_driving_path.py:47`` and ``:74``) but only on zero-slack
    constructions, so they cannot see this. (Read at 13b13f38, 2026-09-28.) Deliberate-decision
    screen: ADR-0091 (the corridor) is silent on a driving source's value; the HELD "negative
    sub-day driving-slack floor (inert)" is the ``_whole_days`` floor, a different mechanism; not
    a duplicate of A0923-CPM-023 (page labels) -- this is the engine field against its docstring.

    Control (precondition): a genuinely zero-slack driving source on the same file (256 -> 155)
    already returns 0, so the check separates a correct driving source from an incorrect one; a
    connected source OFF the path (94 -> 155, 13,920 min = exactly 29 d) keeps reading 29, so a
    "fix" that zeroes every source fails here instead of passing; each witness's premise (ON the
    driving path, non-zero engine slack) is re-read from ``compute_driving_slack`` first.
    """
    wrong: dict[str, tuple[int, int, int | None]] = {}
    for golden, source, target, minutes in _A0923_CPM_026_WITNESSES:
        raw = gzip.decompress((GOLDEN / golden).read_bytes()).decode("utf-8-sig")
        sch = parse_mspdi_text(raw)
        cpm = compute_cpm(sch)
        slack = compute_driving_slack(sch, target, cpm_result=cpm)
        if source not in slack or not slack[source].on_driving_path:
            pytest.fail(
                f"precondition: {source} is no longer on {target}'s driving path ({golden})"
            )
        if slack[source].driving_slack_minutes != minutes:
            pytest.fail(
                f"precondition: {source} -> {target} driving slack moved from {minutes} min to "
                f"{slack[source].driving_slack_minutes} ({golden})"
            )
        between = driving_path_between(sch, source, target, cpm_result=cpm)
        if not (between.connected and between.drives and between.path):
            pytest.fail(f"precondition: {source} no longer drives {target} ({golden})")
        if golden.startswith("ssi_hardfile_24h"):
            control = driving_path_between(sch, 256, target, cpm_result=cpm)
            if not control.drives or control.source_slack_days != 0:
                pytest.fail("precondition: the zero-slack driving source 256 -> 155 is not 0")
            # a connected source OFF the path keeps its whole days (13,920 min = exactly 29 d)
            off_path = driving_path_between(sch, 94, target, cpm_result=cpm)
            if off_path.drives or not off_path.connected or off_path.source_slack_days != 29:
                pytest.fail("precondition: the non-driving source 94 -> 155 no longer reads 29 d")
        if between.source_slack_days != 0:
            wrong[golden] = (source, minutes, between.source_slack_days)

    assert not wrong, (
        f"a DRIVING source reports non-zero whole days of slack (contract: 0 while it drives) "
        f"{{golden: (source, engine driving slack min, source_slack_days)}}: {wrong}"
    )


# --- A0923-CPM-027 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py, and on nothing else:
#   imports    datetime as dt, gzip, xml.etree.ElementTree as ET, pytest,
#              compute_cpm, datetime_to_offset, offset_to_datetime (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   helpers    _stored_finish (the module's own, above)
#   fixture    the module-level autouse _air_gapped
# Input: the committed, non-CUI golden tests/fixtures/golden/fuse_ltf/Large_Test_File.mspdi.xml.gz.
# No new fixture file.


#: every unstarted zero-duration activity of the golden whose stored Start IS its SNET (4) / MSO
#: (2) ConstraintDate -- MS Project stores all six at the START of the constraint day (08:00)
_A0923_CPM_027_BOUND = {
    3734: ("4", dt.datetime(2025, 3, 17, 8, 0)),  # a Monday
    5264: ("4", dt.datetime(2025, 2, 21, 8, 0)),  # carried by a wall-path driver: right today
    6077: ("4", dt.datetime(2028, 9, 29, 8, 0)),  # carries the network finish
    7184: ("4", dt.datetime(2025, 2, 28, 8, 0)),
    7547: ("4", dt.datetime(2025, 3, 14, 8, 0)),
    7550: ("2", dt.datetime(2025, 11, 13, 8, 0)),
}
#: the FNET-bound twin: MS Project stores it at the END of the day, and the engine agrees
_A0923_CPM_027_FNET = (7132, dt.datetime(2025, 3, 24, 17, 0))
#: ADR-0348's majority: unconstrained milestones MS Project stores at 17:00 that the engine renders
#: exactly today (40 on this golden) -- a fix must not re-spell them
_A0923_CPM_027_EOD_FLOOR = 40


def _a0923_cpm_027_milestones(root: ET.Element) -> dict[int, dict[str, str]]:
    """Every unstarted, scheduled zero-duration activity (raw XML, ElementTree): UID -> fields."""
    keys = ("Start", "ConstraintType", "ConstraintDate")
    out: dict[int, dict[str, str]] = {}
    for el in root.iter(NS + "Task"):
        f = {
            k: (el.findtext(NS + k) or "").strip()
            for k in ("UID", "Summary", "IsNull", "Active", "Duration", "ActualStart", *keys)
        }
        if f["Summary"] == "1" or f["IsNull"] == "1" or f["Active"] == "0" or f["UID"] in ("", "0"):
            continue
        if f["Duration"] != "PT0H0M0S" or f["ActualStart"] or not f["Start"]:
            continue
        out[int(f["UID"])] = {k: f[k] for k in keys}
    return out


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-027: a milestone whose early start is a binding SNET/MSO date and that no "
        "wall-path driver ties is spelled at the END of the previous working day, where MS "
        "Project stores the constraint day's START: Large_Test_File UID 6077 and the network "
        "finish read 2028-09-28 17:00 where MS Project stores 2028-09-29 08:00 (Monday SNET "
        "3734 reads the previous Friday)"
    ),
)
def test_a0923_cpm_027_a_start_constraint_bound_milestone_sits_at_its_constraint_start() -> None:
    """A0923-CPM-027 (finder id F-LEADS-001) · CPM · T2 (T1 reading possible -- see Tier).

    Claim (verifier's narrowed claim): at 13b13f38, ``compute_cpm(parse_mspdi_text(...))`` on
    ``tests/fixtures/golden/fuse_ltf/Large_Test_File.mspdi.xml.gz`` spells every unstarted
    zero-duration activity whose early start is set by a binding SNET / MSO date and that no
    wall-path driver ties at the finish-role rendering of that minute -- the END of the previous
    working day -- where MS Project stores the constraint's START-of-day instant: UIDs 6077,
    7184, 7547 (SNET), 7550 (MSO) and 3734 (a Monday SNET, rendered as the previous Friday 17:00),
    and ``CPMResult.project_finish_wall`` 2028-09-28 17:00 (carried from 6077) where MS Project's
    ``<FinishDate>`` is 2028-09-29 08:00 -- the same working minute (asserted as a precondition:
    the integer axis is right, only the instant's spelling is wrong). Across the 44-file corpus:
    32 instances in 6 files (the Large_Test_File family); MS Project start-of-day on 38 of 38
    such milestones, the 6 others (UID 5264) already carried right by a wall-path driver.

    NOT claimed (the verifier REFUTED it): the variance consequences ('/forecast 1 day ahead of
    the baseline', /api/dashboard finish_delta_days -1) EQUAL MS Project's own stored project
    FinishVariance (-4800 tenths = -1 working day) -- a repair must not "fix" them. NOT asserted:
    what the pages print -- with this engine half fixed alone, /path still prints 09/28/2028 through
    A0923-CPM-001's mechanism (pages render the axis date, not ``project_finish_wall``).

    Correct: each start-constraint-bound milestone's instant (its early wall, else the rendering of
    its early finish) and the network finish it carries are MS Project's stored start-of-day
    instants. Preconditions a fix must keep: the FNET-bound twin 7132 stays end-of-day (17:00,
    stored and engine), and ADR-0348's majority -- unconstrained milestones MS Project stores at
    17:00 -- stays exact (at least 40 on this golden today).

    Authority: A1 -- MS Project's stored values in the committed golden (ElementTree):
    ``<FinishDate>2028-09-29T08:00:00</FinishDate>``; UID 6077 ``<Start>`` 2028-09-29T08:00:00,
    ``<ConstraintType>4</ConstraintType>``,
    ``<ConstraintDate>2028-09-29T08:00:00</ConstraintDate>``, ``<Duration>PT0H0M0S</Duration>``;
    UIDs 3734 / 7184 / 7547 / 7550 likewise (Start == ConstraintDate at 08:00). Corroborated by
    an independent reference tool (re-read for this fragment, not asserted by it): Acumen Fuse
    v8.11.0, '00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File vs Large Test File2
    Forensic Analysis Report.xlsx', Projects Finish 47025.333 (= 2028-09-29 08:00) and Finish-sheet
    start-of-day serials for 6077 / 7550 / 7547 / 3734 / 7184. The repo's own statements:
    src/schedule_forensics/engine/cpm.py:291 ``project_finish_wall`` is "The true wall-clock
    instant of the network finish"; docs/adr/0505-a-zero-duration-task-carries-its-driving-
    predecessors-wall-instant.md:80-81 "an SNET milestone tying a crew's 23:00 ends the project at
    its own 08:00". The premises this falsifies for the start-constraint-bound subclass:
    docs/adr/0348-one-instant-two-spellings-and-the-one-that-means-a-start.md:109-110 "MS Project
    spells an instantaneous event end-of-day, so the tool does." and docs/adr/0524-a-late-start-is-
    a-start-role-instant-on-the-wall-path-too-r-69-closed.md:179-180 "The milestone spelling in
    general ... No rule in the files separates them" -- a binding SNET / MSO date separates them
    (38 / 38). docs/adr/0510-a-zero-duration-task-carries-its-late-instant-from-the-need-that-
    binds-it-the-backward-mirror.md:193-197 names this forward analogue as "NOT censused this unit
    -- **UNVERIFIED**"; ADR-0536 records it as an unverified lead.

    Why the oracle is independent: MS Project wrote the stored instants (the golden is MPXJ's
    write of the .mpp's stored fields); they are read here with ElementTree, not through the code
    under test, and Acumen Fuse (which read the .mpp itself) agrees.

    Tier: T2 -- the working minute is right (float, criticality, the -1 wd variance unaffected),
    but the instant an analyst reads is one calendar day early (three for a Monday); T1 if the
    printed calendar date is cited as the figure (the lead should tier it with A0923-CPM-001).
    """
    raw = gzip.decompress((GOLDEN / "fuse_ltf" / "Large_Test_File.mspdi.xml.gz").read_bytes())
    stored_finish = _stored_finish(raw)
    if stored_finish != dt.datetime(2028, 9, 29, 8, 0):
        pytest.fail(f"precondition: MS Project's stored FinishDate moved: {stored_finish}")
    milestones = _a0923_cpm_027_milestones(ET.fromstring(raw))
    bound = {
        uid: (f["ConstraintType"], dt.datetime.fromisoformat(f["Start"]))
        for uid, f in milestones.items()
        if f["ConstraintType"] in ("2", "4") and f["ConstraintDate"] == f["Start"]
    }
    if bound != _A0923_CPM_027_BOUND:
        pytest.fail(f"precondition: the start-constraint-bound population moved: {bound}")
    uid, fnet_stored = _A0923_CPM_027_FNET
    fnet = milestones.get(uid, {})
    if (fnet.get("ConstraintType"), fnet.get("Start")) != ("6", fnet_stored.isoformat()):
        pytest.fail(f"precondition: the FNET-bound control {uid} moved: {fnet}")

    sch = parse_mspdi_text(raw.decode("utf-8"))
    cpm = compute_cpm(sch)
    ps, cal = sch.project_start, sch.calendar

    def instant(uid: int) -> dt.datetime:
        """The engine's instant for a milestone: its early wall, else the rendering of its
        early finish (the spelling every page prints for a project-axis milestone)."""
        timing = cpm.timings[uid]
        return timing.early_finish_wall or offset_to_datetime(ps, timing.early_finish, cal)

    if datetime_to_offset(ps, stored_finish, cal) != cpm.project_finish:
        pytest.fail("precondition: the engine's integer finish is no longer MS Project's minute")
    if instant(uid) != fnet_stored:
        pytest.fail(f"precondition: FNET control {uid} reads {instant(uid)}, stored {fnet_stored}")
    eod_exact = [
        u
        for u, f in milestones.items()
        if f["ConstraintType"] in ("", "0")
        and f["Start"].endswith("T17:00:00")
        and instant(u) == dt.datetime.fromisoformat(f["Start"])
    ]
    if len(eod_exact) < _A0923_CPM_027_EOD_FLOOR:
        pytest.fail(
            f"precondition: only {len(eod_exact)} unconstrained end-of-day milestones stay exact "
            f"(ADR-0348's majority; {_A0923_CPM_027_EOD_FLOOR} today)"
        )

    problems = []
    for uid, (ct, stored) in sorted(bound.items()):
        got = instant(uid)
        if got != stored:
            problems.append(
                f"UID {uid} ({'SNET' if ct == '4' else 'MSO'}): engine {got:%a %Y-%m-%d %H:%M}; "
                f"MS Project stores {stored:%a %Y-%m-%d %H:%M}"
            )
    if cpm.project_finish_wall != stored_finish:
        problems.append(
            f"project_finish_wall {cpm.project_finish_wall}; MS Project's FinishDate "
            f"{stored_finish} (the same working minute)"
        )
    assert problems == [], "\n".join(problems)


# --- A0923-CPM-028 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py, and on nothing else:
#   imports    datetime as dt, pytest, compute_cpm (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi)
#   fixture    the module-level autouse _air_gapped
# Inputs: inline MSPDI text only. No fixture file, no Java, no network.

#: MSPDI ``PredecessorLink/Type`` codes (Microsoft Learn, "Type Element (Multiple Parents)").
_A0923_CPM_028_TYPE = {"FF": "0", "FS": "1", "SF": "2", "SS": "3"}
_A0923_CPM_028_STD = (
    "<WorkingTimes><WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime>"
    "</WorkingTime><WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime>"
    "</WorkingTime></WorkingTimes>"
)
_A0923_CPM_028_H24 = (
    "<WorkingTimes><WorkingTime><FromTime>00:00:00</FromTime><ToTime>00:00:00</ToTime>"
    "</WorkingTime></WorkingTimes>"
)
#: hand-computed (P's late finish, P's total float in working minutes of its 24-hour calendar)
_A0923_CPM_028_WANT = {
    "A": (dt.datetime(2026, 1, 9, 8, 0), 88 * 60),  # M's one late instant: Fri 08:00
    "B": (dt.datetime(2026, 1, 8, 17, 0), 73 * 60),  # M's one late instant: Thu 17:00
}


def _a0923_cpm_028_calendar(uid: int, name: str, blocks: str, every_day: bool) -> str:
    days = "".join(
        f"<WeekDay><DayType>{d}</DayType>"
        f"<DayWorking>{int(every_day or 2 <= d <= 6)}</DayWorking>"
        + (blocks if every_day or 2 <= d <= 6 else "")
        + "</WeekDay>"
        for d in range(1, 8)
    )
    return (
        f"<Calendar><UID>{uid}</UID><Name>{name}</Name><IsBaseCalendar>1</IsBaseCalendar>"
        f"<BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{days}</WeekDays></Calendar>"
    )


def _a0923_cpm_028_mspdi(case: str, p_to_m: tuple[str, ...]) -> str:
    """Q 5 d (sets the finish Fri 01-09 17:00); P 8 h on a '24 Hours' task calendar (a wall-path
    task); M a milestone after P via the lag-0 links ``p_to_m``; case A: M -FS0-> S (1 d); case B:
    M -FF0-> S (1 d) -FS0-> T (1 d). Standard project calendar, start Mon 2026-01-05 08:00."""

    def task(uid: int, name: str, hours: int, preds: tuple[tuple[int, str], ...], cal: str) -> str:
        links = "".join(
            f"<PredecessorLink><PredecessorUID>{p}</PredecessorUID>"
            f"<Type>{_A0923_CPM_028_TYPE[k]}</Type><LinkLag>0</LinkLag><LagFormat>7</LagFormat>"
            "</PredecessorLink>"
            for p, k in preds
        )
        milestone = "<Milestone>1</Milestone>" if hours == 0 else ""
        return (
            f"<Task><UID>{uid}</UID><ID>{uid}</ID><Name>{name}</Name>"
            f"<Duration>PT{hours}H0M0S</Duration><DurationFormat>7</DurationFormat>"
            f"{milestone}{cal}{links}</Task>"
        )

    tail = (
        task(4, "S", 8, ((3, "FS"),), "")
        if case == "A"
        else task(4, "S", 8, ((3, "FF"),), "") + task(5, "T", 8, ((4, "FS"),), "")
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Project xmlns="http://schemas.microsoft.com/project"><Name>mirror</Name>'
        "<StartDate>2026-01-05T08:00:00</StartDate><CalendarUID>1</CalendarUID>"
        "<MinutesPerDay>480</MinutesPerDay><Calendars>"
        + _a0923_cpm_028_calendar(1, "Standard", _A0923_CPM_028_STD, False)
        + _a0923_cpm_028_calendar(2, "24 Hours", _A0923_CPM_028_H24, True)
        + "</Calendars><Tasks>"
        + task(1, "Q", 40, (), "")
        + task(2, "P", 8, (), "<CalendarUID>2</CalendarUID>")
        + task(3, "M", 0, tuple((2, k) for k in p_to_m), "")
        + tail
        + "</Tasks></Project>"
    )


def _a0923_cpm_028_p(case: str, p_to_m: tuple[str, ...]) -> tuple[dt.datetime | None, int]:
    """(P's late_finish_wall, P's total_float) -- preconditions on the forward pass included."""
    sch = parse_mspdi_text(_a0923_cpm_028_mspdi(case, p_to_m), source_file="mirror.xml")
    if sorted(t.unique_id for t in sch.tasks) != ([1, 2, 3, 4] if case == "A" else [1, 2, 3, 4, 5]):
        pytest.fail(f"precondition: the {case} network imports whole: {sch.tasks!r}")
    res = compute_cpm(sch)
    p, m = res.timings[2], res.timings[3]
    if p.early_finish_wall != dt.datetime(2026, 1, 5, 16, 0) or m.early_start != m.early_finish:
        pytest.fail(f"precondition: case {case} {p_to_m}: P ends Mon 16:00 on its 24-h calendar")
    if res.project_finish_wall != dt.datetime(2026, 1, 9, 17, 0):
        pytest.fail(f"precondition: case {case} {p_to_m} finishes {res.project_finish_wall}")
    return p.late_finish_wall, p.total_float


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-028: a wall-path predecessor reads an un-carried milestone's ONE late instant "
        "start-role through FS/SS (_succ_ls_wall, the next morning) and finish-role through FF/SF "
        "(_succ_lf_wall, the evening before), so a 24-hour P's late finish / total float depends "
        "on the link type: a redundant FF0 moves Fri 08:00 / 5,280 to Thu 17:00 / 4,380, and an "
        "ordinary FS0 into an FF-bound milestone gives 5,280 where its FF0 twin gives 4,380"
    ),
)
def test_a0923_cpm_028_a_wall_path_predecessor_reads_a_milestones_one_late_instant() -> None:
    """A0923-CPM-028 (finder id F-LEADS-002) · CPM · T1 (latent) -- A0923-CPM-005's backward-pass
    mirror.

    Claim (verifier: REPRODUCED as stated; scope LATENT): at 13b13f38, on a hand-built MSPDI
    (Standard 08-12/13-17 project calendar; P 8 h on a '24 Hours' task calendar, a wall-path
    task; M a milestone after P; S 1 d; the finish Fri 2026-01-09 17:00 set by an independent 5 d
    task Q), ``compute_cpm`` gives P's late finish / total float by the LINK TYPE P uses to reach
    M, not by M's one late instant: case A (M -FS0-> S) P -FS0-> M Fri 08:00 / 5,280 min, plus a
    transitively redundant FF0 -> Thu 17:00 / 4,380, plus SF0 -> Fri 01:00 / 4,860, FF0 alone ->
    Thu 17:00 / 4,380; case B (M -FF0-> S -FS0-> T) the ORDINARY P -FS0-> M Fri 08:00 / 5,280
    where the FF0 twin gives Thu 17:00 / 4,380 -- 900 working minutes (15 crew hours) of float
    that cannot both be right. Mechanism: ``_succ_ls_wall`` (src/schedule_forensics/engine/
    cpm.py:2933) renders a zero-duration successor's late instant START-role (the next working
    morning) and ``_succ_lf_wall`` (cpm.py:2949) FINISH-role (the evening before) whenever
    ADR-0510's carry abstains (a milestone bound by project-calendar successors only).

    Correct: P reads M's ONE late instant whatever the lag-0 link type -- case A Fri 08:00 /
    5,280 in every variant, case B Thu 17:00 / 4,380 in every variant. Preconditions (right today,
    a fix must keep them): case A FS0 and FS0+SS0 give Fri 08:00 / 5,280; case B FF0 gives
    Thu 17:00 / 4,380 (the readings whose role happens to match M's binding need).

    Authority: the redundancy limb needs no spelling assumption -- M has zero duration, so
    LS_M = LF_M and FF0 / SF0 / SS0 from P into M impose nothing FS0 does not already impose;
    adding one cannot move P "under any consistent semantics" (the authority A0923-CPM-005's
    committed test uses forward). Case B's instant (hand arithmetic): LF_S = the end of S's last
    worked minute before LS_T Fri 08:00 = Thu 17:00, and FF0 binds LF_M <= LF_S. The repo's
    decision text: docs/adr/0510-a-zero-duration-task-carries-its-late-instant-from-the-need-that-
    binds-it-the-backward-mirror.md:39-40 "collects the instants of every need that BINDS its late
    finish: a lag-0 FS / SS successor's late start", :42-43 "a lag-0 FF / SF successor's late
    finish" and :44-45 "**The earliest wins**, MS Project's `min` over instants";
    src/schedule_forensics/engine/cpm.py:2896 "a milestone's late start IS its late finish, one
    instant". Codes: Microsoft Learn "Type
    Element (Multiple Parents)", https://learn.microsoft.com/office-project/xml-data-interchange/type-element-multiple-parents?view=project-client-2016
    (as quoted in A0923-CPM-005's committed docstring, retrieved 2026-09-25): 0 FF, 1 FS, 2 SF,
    3 SS.

    Why the oracle is independent: the expectation is hand arithmetic on a five-task input plus a
    definitional redundancy argument; the engine only runs the network. MS Project's stored value
    for exactly the case-B chain with an overnight predecessor is UNVERIFIED (no committed file
    holds one; the corpus shows milestone LateFinish == the binding FF successor's stored
    LateFinish on 11 of 11 links -- one distinct UID pair x 11 files, thin -- and == the binding
    FS/SS successor's stored LateStart on 1,004 of 1,004).

    Tier: T1, latent (0 of 44 corpus files: 30 wall-path -> lag-0 -> un-carried milestone links,
    7 on a day boundary, none moves a float) -- when it fires, a cited total float moves by up to
    15 crew hours and the critical flag can flip on well-formed input.
    """
    a_want, b_want = _A0923_CPM_028_WANT["A"], _A0923_CPM_028_WANT["B"]
    for links in (("FS",), ("FS", "SS")):
        if _a0923_cpm_028_p("A", links) != a_want:
            pytest.fail(f"precondition: case A {links} no longer {a_want}")
    if _a0923_cpm_028_p("B", ("FF",)) != b_want:
        pytest.fail(f"precondition: case B ('FF',) no longer {b_want}")

    wrong = {}
    for case, variants in (
        ("A", (("FF",), ("FS", "FF"), ("FS", "SF"))),
        ("B", (("FS",), ("FS", "FF"), ("FS", "SF"), ("FS", "SS"))),
    ):
        want = _A0923_CPM_028_WANT[case]
        for links in variants:
            lf, tf = _a0923_cpm_028_p(case, links)
            if (lf, tf) != want:
                wrong[f"case {case} P -{'+'.join(k + '0' for k in links)}-> M"] = (
                    f"LF {lf:%a %m-%d %H:%M} TF {tf}" if lf else f"LF None TF {tf}"
                )
    assert not wrong, (
        "P's late finish / total float depends on the lag-0 link type into the milestone "
        f"(want case A Fri 01-09 08:00 / 5280, case B Thu 01-08 17:00 / 4380): {wrong}"
    )


# --- A0923-CPM-029 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py, and on nothing else:
#   imports    datetime as dt, gzip, xml.etree.ElementTree as ET, pytest,
#              compute_cpm (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Input: the committed, non-CUI golden tests/fixtures/golden/fuse_ltf/Large_Test_File2.mspdi.xml.gz
# (read with gzip). No new fixture file.

#: MS Project's stored UID 5307 fields this reproducer rests on (decompressed golden, Task at line
#: 118650): FIXED_WORK, unstarted, unconstrained, no task-level delay, on calendar 68.
_A0923_CPM_029_TASK = {
    "Type": "2",
    "PercentComplete": "0",
    "ConstraintType": "0",
    "LevelingDelay": "0",
    "IgnoreResourceCalendar": "0",
    "CalendarUID": "68",
    "Start": "2026-05-15T09:22:00",
    "Finish": "2026-05-22T15:08:12",
    "Duration": "PT35H56M0S",
    "LateStart": "2026-03-26T10:42:54",
    "LateFinish": "2026-04-02T16:29:06",
    "TotalSlack": "-171991",
    "Critical": "1",
}
#: The task's ONE delayed booking (Assignment UID 20293, line 523872): crew 76, 1,608.2 working
#: minutes of its own leveling delay (tenths, format 7), ending WITH the task.
_A0923_CPM_029_BOOKING = {
    "UID": "20293",
    "ResourceUID": "76",
    "LevelingDelay": "16082",
    "LevelingDelayFormat": "7",
    "Start": "2026-05-20T13:10:12",
    "Finish": "2026-05-22T15:08:12",
}
#: ADR-0502's own absorbed witnesses in the SAME file (UID, stored Finish, stored TotalSlack
#: tenths). The absorb rule is exact on them today (to MS Project's sub-minute seconds, R-65); a
#: "fix" that moves them away -- ADR-0502's refuted "push every delay" first cut made 5266 / 5267
#: / 5270 days late -- is wrong.
_A0923_CPM_029_CONTROLS = (
    (5266, "2025-05-29T10:55:48", -117486),
    (5267, "2025-06-02T15:17:48", -117486),
    (5270, "2025-06-30T09:20:36", -117486),
    (5274, "2025-09-04T11:48:36", -117486),
)


def _a0923_cpm_029_task(root: ET.Element, uid: int) -> ET.Element:
    """The raw ``<Task>`` element with this UID -- read with ElementTree, not the importer."""
    for el in root.iter(NS + "Task"):
        if (el.findtext(NS + "UID") or "").strip() == str(uid):
            return el
    pytest.fail(f"precondition: the golden has no <Task> with UID {uid}")


def _a0923_cpm_029_calendar(root: ET.Element, uid: str) -> ET.Element:
    """The raw ``<Calendar>`` element with this UID."""
    for el in root.iter(NS + "Calendar"):
        if (el.findtext(NS + "UID") or "").strip() == uid:
            return el
    pytest.fail(f"precondition: the golden has no <Calendar> with UID {uid}")


def _a0923_cpm_029_week(
    cal: ET.Element, first: dt.date, last: dt.date
) -> dict[int, list[tuple[int, int]]]:
    """Calendar ``cal``'s weekly working pattern (MSPDI DayType 1 = Sunday .. 7 = Saturday ->
    working-second intervals of the day), read from the raw XML. Precondition: no exception of
    the calendar -- in either MSPDI encoding (a DayType-0 ``<WeekDay>`` or an ``<Exception>``)
    -- touches ``first .. last``, and it has no ``<WorkWeeks>``, so the pattern alone governs."""
    if cal.find(NS + "WorkWeeks") is not None:
        pytest.fail("precondition: calendar 68 now carries WorkWeeks")
    periods = [
        wd.find(NS + "TimePeriod")
        for wd in cal.iter(NS + "WeekDay")
        if (wd.findtext(NS + "DayType") or "").strip() == "0"
    ] + [ex.find(NS + "TimePeriod") for ex in cal.iter(NS + "Exception")]
    for tp in periods:
        if tp is None:
            pytest.fail("precondition: a calendar-68 exception carries no TimePeriod")
        lo = dt.date.fromisoformat((tp.findtext(NS + "FromDate") or "")[:10])
        hi = dt.date.fromisoformat((tp.findtext(NS + "ToDate") or "")[:10])
        if lo <= last and hi >= first:
            pytest.fail(f"precondition: a calendar-68 exception ({lo}..{hi}) touches the window")

    def secs(text: str | None) -> int:
        h, m, s = (int(x) for x in (text or "").strip().split(":"))
        return h * 3600 + m * 60 + s

    week: dict[int, list[tuple[int, int]]] = {}
    for wd in cal.iter(NS + "WeekDay"):
        day_type = int((wd.findtext(NS + "DayType") or "0").strip())
        if day_type == 0:
            continue
        week[day_type] = [
            (secs(w.findtext(NS + "FromTime")), secs(w.findtext(NS + "ToTime")) or 86400)
            for w in wd.iter(NS + "WorkingTime")
        ]
    return week


def _a0923_cpm_029_minutes(
    week: dict[int, list[tuple[int, int]]], start: dt.datetime, finish: dt.datetime
) -> float:
    """Working minutes of ``week`` between two instants, to the second -- plain arithmetic on the
    raw pattern, independent of the engine's ruler."""
    total = 0
    day = start.date()
    while day <= finish.date():
        midnight = dt.datetime.combine(day, dt.time())
        for lo, hi in week.get(day.isoweekday() % 7 + 1, []):
            a = max(midnight + dt.timedelta(seconds=lo), start)
            b = min(midnight + dt.timedelta(seconds=hi), finish)
            if b > a:
                total += int((b - a).total_seconds())
        day += dt.timedelta(days=1)
    return total / 60


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-029: ADR-0502's ratio-1.0 'absorb' branch drops a task-spanning booking's own "
        "leveling delay even where the delay outlasts the task's stored Duration, so "
        "Large_Test_File2 UID 5307 finishes 2026-05-21 14:18 with total float -16,669 min where "
        "MS Project stores 2026-05-22 15:08:12 and -17,199.1 (530 working minutes early)"
    ),
)
def test_a0923_cpm_029_a_booking_delay_that_outlasts_the_task_duration_pushes_its_finish() -> None:
    """A0923-CPM-029 (finder id F-LEADS-003) · CPM · T1.

    Claim (verifier's narrowed claim): at 13b13f38,
    ``tests/fixtures/golden/fuse_ltf/Large_Test_File2.mspdi.xml.gz`` (and the four intake
    conversions of the same save) via ``compute_cpm(parse_mspdi_text(...))`` finishes UID 5307
    (FIXED_WORK, Critical, calendar 68) at 2026-05-21 14:18 with total float -16,669 min and late
    start 2026-03-27 11:33, where MS Project stores Finish 2026-05-22T15:08:12, TotalSlack
    -17,199.1 min and LateStart 2026-03-26T10:42:54 -- 530 working minutes early / high -- because
    ``engine/cpm.py:_task_shape`` (``a.leveling_delay_minutes if ratio < 1.0 else 0``, line 986)
    zeroes the 1,608.2-minute LevelingDelay of booking 20293 (crew 76, calendar 121 = calendar 68's
    pattern). MS Project starts that booking at Start + its delay (2026-05-20 13:10:12, to the
    second) and runs it 1,078 working minutes -- the span of the task's six undelayed crews -- to
    the task's Finish; the stored Duration (2,156) is shorter than Start -> Finish (2,686.2) by
    exactly the delay's excess over that span, 530.2. The same float error carries upstream: UID
    5306 reads -16,669 where MS Project stores -17,199.1. Census (44-file stored-value corpus: 15
    goldens + 29 intake conversions): 44 task-instances carry a delayed booking on a task-spanning
    leg; on 39 the delay fits inside the task's legs and the absorb is exact to within 2 minutes;
    on 5 (UID 5307 on this golden and its four intake conversions) it outlasts them by 530 and
    every one is a day early. Pushing only those moves 162 activities per input, all toward MS
    Project (145 total floats become exact on this golden) and none away.

    The documented decision whose premise this falsifies (a HELD hypothesis; the claim stands only
    on the new evidence below). ADR-0502,
    ``docs/adr/0502-a-bookings-own-leveling-delay-is-honoured-on-that-leg-alone-on-adr-0474s-type-axis.md:46``:
    "| SPANS THE TASK (ratio 1.0) | **ABSORBED** — starts late and still ends with the task | the
    delay lies inside the span it shares with the task |", evidenced at :49-51: "The absorb half
    is not an assumption — on **16 of those 18** bookings the file's own ``Assignment/Finish``
    **IS** its ``Task/Finish``"; restated in ``engine/cpm.py:971-973``: "A leg that SPANS THE TASK
    (ratio 1.0) ABSORBS it: the delay lies inside the span it shares with the task, so the booking
    starts late and still ends with the task". Falsifying observation: booking 20293 satisfies
    ADR-0502's own test (its stored Finish IS the task's, 2026-05-22T15:08:12) yet its delay does
    NOT lie inside the span the task's Duration gives -- Start + 1,608.2 (delay) + 1,078 (the
    booking's recorded span) = 2,686.2 working minutes, 530.2 past Start + Duration (2,156). The
    equality ADR-0502 took as proof of absorption cannot tell an absorbed booking from a pushing
    one; the absorb rule is exact only where the stored Duration already contains the delay (its
    witnesses 5266 / 5267 / 5270 / 5274 in this file, held here as controls). The registered
    diagnosis of this residual ("the cross-calendar seam is registered as R-77's residual",
    ``docs/STATE/HANDOFF-ARCHIVE.md:509-510``) does not describe its head: calendar 121 is derived
    from 68 with no working time or exception of its own (checked below).

    Authority: A1 -- MS Project's own stored values, decompressed golden: Task 5307 (line 118650)
    ``<Type>2`` (118656), ``<Start>2026-05-15T09:22:00`` (118663), ``<Finish>2026-05-22T15:08:12``
    (118664), ``<Duration>PT35H56M0S`` (118665), ``<Critical>1`` (118675),
    ``<LateStart>2026-03-26T10:42:54`` (118681), ``<LateFinish>2026-04-02T16:29:06`` (118682),
    ``<TotalSlack>-171991`` (118685), ``<CalendarUID>68`` (118694), ``<LevelingDelay>0`` (118697);
    Assignment 20293 (line 523872) ``<ResourceUID>76`` (523875),
    ``<Finish>2026-05-22T15:08:12`` (523877), ``<LevelingDelay>16082`` (523881),
    ``<LevelingDelayFormat>7`` (523882), ``<Start>2026-05-20T13:10:12`` (523885); the six
    undelayed crews ``<Finish>2026-05-19T11:20:00``. Hand arithmetic on calendar 68 (Mon-Fri
    08-12 / 13-17; its exceptions end 2025-12-25): Fri 09:22 -> Wed 13:10:12 = 398 + 480 + 480 +
    240 + 10.2 = 1,608.2 = the delay; Wed 13:10:12 -> Fri 15:08:12 = 229.8 + 480 + 368.2 =
    1,078.0 = Fri 09:22 -> Tue 11:20 (the undelayed crews' span); Start -> Finish = 398 + 4 x 480 +
    368.2 = 2,686.2 = 2,156 + 530.2. All of it is recomputed below from the raw calendar.

    Independence: Finish / TotalSlack / LateStart / LevelingDelay and the booking window were
    written by MS Project into the save Fuse analysed; they are read with ElementTree and the
    working minutes counted on the raw ``<WeekDays>``, never with the engine's ruler.
    """
    raw = gzip.decompress((GOLDEN / "fuse_ltf" / "Large_Test_File2.mspdi.xml.gz").read_bytes())
    root = ET.fromstring(raw)
    el = _a0923_cpm_029_task(root, 5307)
    stored = {k: (el.findtext(NS + k) or "").strip() for k in _A0923_CPM_029_TASK}
    if stored != _A0923_CPM_029_TASK or (el.findtext(NS + "ActualStart") or "").strip():
        pytest.fail(f"precondition: MS Project's stored UID 5307 fields moved: {stored}")
    start = dt.datetime.fromisoformat(stored["Start"])
    finish = dt.datetime.fromisoformat(stored["Finish"])

    bookings = [
        a
        for a in root.iter(NS + "Assignment")
        if (a.findtext(NS + "TaskUID") or "").strip() == "5307"
    ]
    delayed = [a for a in bookings if int((a.findtext(NS + "LevelingDelay") or "0").strip())]
    got_booking = (
        {k: (delayed[0].findtext(NS + k) or "").strip() for k in _A0923_CPM_029_BOOKING}
        if len(delayed) == 1
        else None
    )
    if got_booking != _A0923_CPM_029_BOOKING:
        pytest.fail(f"precondition: UID 5307's one delayed booking moved: {got_booking}")
    peers = {
        (a.findtext(NS + "Start") or "").strip(): (a.findtext(NS + "Finish") or "").strip()
        for a in bookings
        if a is not delayed[0] and (a.findtext(NS + "Work") or "PT0H0M0S") != "PT0H0M0S"
    }
    if peers != {stored["Start"]: "2026-05-19T11:20:00"} or len(bookings) != 8:
        pytest.fail(f"precondition: UID 5307's undelayed crews no longer share one window: {peers}")
    for r in root.iter(NS + "Resource"):
        if (r.findtext(NS + "UID") or "").strip() == "76":
            if ((r.findtext(NS + "Type") or ""), (r.findtext(NS + "CalendarUID") or "")) != (
                "1",
                "121",
            ):
                pytest.fail("precondition: crew 76 is no longer a work resource on calendar 121")
            break
    else:
        pytest.fail("precondition: the golden has no <Resource> 76")
    crew = _a0923_cpm_029_calendar(root, "121")
    own = [
        ch.tag for ch in crew if ch.tag in (NS + "WeekDays", NS + "Exceptions", NS + "WorkWeeks")
    ]
    if (crew.findtext(NS + "BaseCalendarUID") or "").strip() != "68" or own:
        pytest.fail("precondition: calendar 121 is no longer calendar 68 with nothing of its own")

    # the falsifying observation, from the raw calendar alone: the delayed booking starts at the
    # task's Start + its delay and runs the undelayed crews' span to the task's Finish, which lies
    # 530.2 working minutes past Start + Duration -- the delay is NOT inside the task's span
    week = _a0923_cpm_029_week(_a0923_cpm_029_calendar(root, "68"), start.date(), finish.date())
    b_start = dt.datetime.fromisoformat(_A0923_CPM_029_BOOKING["Start"])
    delay = int(_A0923_CPM_029_BOOKING["LevelingDelay"]) / 10
    duration = 35 * 60 + 56
    measured = (
        round(_a0923_cpm_029_minutes(week, start, b_start), 1),
        round(_a0923_cpm_029_minutes(week, b_start, finish), 1),
        round(_a0923_cpm_029_minutes(week, start, dt.datetime(2026, 5, 19, 11, 20)), 1),
        round(_a0923_cpm_029_minutes(week, start, finish), 1),
    )
    if measured != (delay, 1078.0, 1078.0, 2686.2) or round(measured[3] - duration, 1) != 530.2:
        pytest.fail(
            "precondition: (Start->booking Start, booking span, undelayed span, Start->Finish) "
            f"on calendar 68 is {measured}, not (1608.2, 1078.0, 1078.0, 2686.2)"
        )

    sch = parse_mspdi_text(raw.decode("utf-8"))
    task = next((t for t in sch.tasks if t.unique_id == 5307), None)
    if task is None or task.duration_minutes != duration:
        pytest.fail("precondition: the importer no longer reads UID 5307 as 2,156 working minutes")
    if sorted(a.leveling_delay_minutes for a in task.resource_assignments)[-1:] != [1608]:
        pytest.fail("precondition: the importer no longer reads booking 20293's 1,608.2-min delay")
    timings = compute_cpm(sch).timings

    def near(got: dt.datetime | None, want: str) -> bool:
        return got is not None and abs((got - dt.datetime.fromisoformat(want)).total_seconds()) < 60

    for uid, want_finish, want_tf in _A0923_CPM_029_CONTROLS:
        c_el = _a0923_cpm_029_task(root, uid)
        if ((c_el.findtext(NS + "Finish") or ""), (c_el.findtext(NS + "TotalSlack") or "")) != (
            want_finish,
            str(want_tf),
        ):
            pytest.fail(f"precondition: MS Project's stored UID {uid} Finish/TotalSlack moved")
        c = timings[uid]
        got_finish = c.early_finish_wall
        if (
            got_finish is None
            or abs((got_finish - dt.datetime.fromisoformat(want_finish)).total_seconds()) >= 120
            or abs(c.total_float * 10 - want_tf) >= 20
        ):
            pytest.fail(
                f"precondition (control): ADR-0502's absorbed witness UID {uid} reads finish "
                f"{got_finish}, total float {c.total_float} against MS Project's {want_finish}, "
                f"{want_tf / 10:g} -- the harness or the fix is wrong"
            )

    t = timings[5307]
    # the rest of the network is not in dispute: the early start and the late finish are MS
    # Project's to the minute -- only the task's own span is short
    if t.early_start_wall != start or not near(t.late_finish_wall, stored["LateFinish"]):
        pytest.fail(f"precondition: the engine's UID 5307 early start / late finish moved: {t}")
    tf_tenths = int(stored["TotalSlack"])
    got = {
        "5307 early finish": near(t.early_finish_wall, stored["Finish"]),
        "5307 total float": abs(t.total_float * 10 - tf_tenths) <= 10,
        "5307 late start": near(t.late_start_wall, stored["LateStart"]),
        "5306 total float": abs(timings[5306].total_float * 10 - tf_tenths) <= 10,
    }
    assert all(got.values()), (
        f"UID 5307 (booking 20293 delayed {delay:g} of calendar 68): engine early finish "
        f"{t.early_finish_wall}, total float {t.total_float}, late start {t.late_start_wall} "
        f"(UID 5306 total float {timings[5306].total_float}); MS Project stores {finish}, "
        f"{tf_tenths / 10:g}, {stored['LateStart']} (5306 {tf_tenths / 10:g}), each to within a "
        f"minute -- the booking's delay outlasts the task's {duration}-minute Duration and is "
        f"absorbed instead of pushing the finish ({got})"
    )


# --- A0923-CPM-030 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    datetime as dt, re, pytest, TestClient (fastapi.testclient),
#              compute_cpm and offset_to_datetime (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi),
#              SessionState and create_app (schedule_forensics.web.app)
#   ALSO NEEDS ``from urllib.parse import quote`` and
#              ``from schedule_forensics.model.task import ConstraintType`` on the header
#   fixture    the module-level autouse _air_gapped
# Input: inline MSPDI text (built below). No fixture file; nothing CUI.

#: The summary's Start-No-Earlier-Than instant: Mon 2026-06-15 08:00 = working day 10 of the
#: project (Mon 2026-06-01 08:00 is offset 0; 480 working minutes a day) = offset 4800.
_A0923_CPM_030_SNET = "2026-06-15T08:00:00"


def _a0923_cpm_030_mspdi(snet_on: str, summary_has_predecessor: bool = True) -> str:
    """MS Project's Standard calendar (Mon-Fri 08:00-12:00 + 13:00-17:00), StartDate Mon
    2026-06-01 08:00, HonorConstraints 1. Tasks (DurationFormat 7 = days; WBS = OutlineNumber,
    so the outline and the WBS agree -- A0923-CPM-008's hierarchy question never arises):
      A  (UID 1,  outline 1)   3 d;
      S  (UID 10, outline 2)   SUMMARY, FS0 after A (unless ``summary_has_predecessor`` is False);
      C1 (UID 11, outline 2.1) 2 d;
      C2 (UID 12, outline 2.2) 1 d, FS0 after C1.
    ``snet_on`` names the task carrying SNET 2026-06-15 08:00 (ConstraintType 4): "summary" (the
    defect input), "leaf" (C1 -- the control the engine already honours) or "none"."""
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
    snet = (
        f"<ConstraintType>4</ConstraintType><ConstraintDate>{_A0923_CPM_030_SNET}</ConstraintDate>"
    )

    def task(
        uid: int,
        outline: str,
        days_: int,
        *,
        summary: bool = False,
        pred: int | None = None,
        constrained: bool = False,
    ) -> str:
        link = (
            f"<PredecessorLink><PredecessorUID>{pred}</PredecessorUID><Type>1</Type>"
            "<LinkLag>0</LinkLag><LagFormat>7</LagFormat></PredecessorLink>"
            if pred is not None
            else ""
        )
        return (
            f"<Task><UID>{uid}</UID><ID>{uid}</ID><Name>T{uid}</Name><WBS>{outline}</WBS>"
            f"<OutlineNumber>{outline}</OutlineNumber><OutlineLevel>{outline.count('.') + 1}"
            f"</OutlineLevel><Summary>{int(summary)}</Summary>"
            f"<Duration>PT{8 * days_}H0M0S</Duration><DurationFormat>7</DurationFormat>"
            f"{snet if constrained else ''}{link}</Task>"
        )

    return (
        '<Project xmlns="http://schemas.microsoft.com/project"><Name>f-edge2-001</Name>'
        "<ScheduleFromStart>1</ScheduleFromStart><StartDate>2026-06-01T08:00:00</StartDate>"
        "<CalendarUID>1</CalendarUID><HonorConstraints>1</HonorConstraints>"
        "<Calendars><Calendar><UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>"
        f"<BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{days}</WeekDays></Calendar></Calendars>"
        "<Tasks>"
        + task(1, "1", 3)
        + task(
            10,
            "2",
            3,
            summary=True,
            pred=1 if summary_has_predecessor else None,
            constrained=snet_on == "summary",
        )
        + task(11, "2.1", 2, constrained=snet_on == "leaf")
        + task(12, "2.2", 1, pred=11)
        + "</Tasks></Project>"
    )


def _a0923_cpm_030_solve(text: str) -> tuple[int, int, int, dt.datetime]:
    """(C1 early start, C2 early finish, project finish) in working minutes from the project
    start, and the project finish as the engine's own instant (wall, else the axis rendering)."""
    sch = parse_mspdi_text(text)
    res = compute_cpm(sch)
    finish = res.project_finish_wall or offset_to_datetime(
        sch.project_start, res.project_finish, sch.calendar
    )
    return res.timings[11].early_start, res.timings[12].early_finish, res.project_finish, finish


def _a0923_cpm_030_served_finish(text: str) -> str:
    """The 'computed finish ...' sentence /analysis/<key> serves for this one-file session."""
    state = SessionState()
    client = TestClient(create_app(state))
    up = client.post("/upload", files={"files": ("a0923_cpm_030.xml", text.encode(), "text/xml")})
    if up.status_code != 200 or len(state.schedules) != 1:
        pytest.fail(f"precondition: upload answered {up.status_code} ({list(state.schedules)})")
    page = client.get(f"/analysis/{quote(next(iter(state.schedules)), safe='')}")
    if page.status_code != 200:
        pytest.fail(f"precondition: /analysis answered {page.status_code}")
    visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page.text))
    shown = re.search(r"computed finish (\d\d/\d\d/\d{4})", visible)
    if shown is None:
        pytest.fail("precondition: /analysis no longer prints a 'computed finish mm/dd/yyyy'")
    return shown.group(1)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-030: a constraint on a SUMMARY task never reaches the network (compute_cpm "
        "schedules leaves only and _constraint_bounds reads only them), so a summary SNET "
        "Mon 2026-06-15 over C1 (2d) -> C2 (1d) leaves C1 at offset 1440 and the finish at "
        "2880 (/analysis 'computed finish 06/08/2026') where the subtasks must wait: 4800 / "
        "6240 (06/17/2026)"
    ),
)
def test_a0923_cpm_030_a_start_no_earlier_than_on_a_summary_holds_back_its_subtasks() -> None:
    """A0923-CPM-030 (finder id F-EDGE2-001) · CPM · T1 (latent: no committed file carries a
    constraint on a summary).

    Claim (verifier's narrowed claim): at 13b13f38 a summary task's date constraint never
    reaches its leaves. On the inline MSPDI below, summary S (UID 10, WBS = OutlineNumber 2, FS0
    after A = 3 d) carries Start-No-Earlier-Than Mon 2026-06-15 08:00 over C1 (2 d) and C2 (1 d,
    FS0 C1); ``parse_mspdi_text`` + ``compute_cpm`` yield C1 ES 1440 (Thu 06-04 08:00), C2 EF
    2880 (Mon 06-08 17:00) and project finish 2880 -- identical to the same file with no
    constraint -- and ``/analysis/<key>`` serves "computed finish 06/08/2026". Mechanism:
    ``_scheduled_tasks`` (``engine/cpm.py:306-311``) drops summaries and ``_constraint_bounds``
    (``cpm.py:2046-2108``, called at ``cpm.py:2370``) iterates only those scheduled leaves, while
    ``engine/summary_logic.py`` lowers only RELATIONSHIPS (ADR-0043). The same summary with no
    predecessor drops too (C1 ES 0, finish 1440). No import note, no log record, no finding
    names the dropped constraint.

    Authority: A1 -- Microsoft Learn, "Tasks don't schedule as expected in Microsoft Project",
    https://learn.microsoft.com/en-us/troubleshoot/microsoft-365-apps/project/tasks-not-scheduled
    (retrieved 2026-09-28), Project 2010 item 11 "Is the task a subtask?" verbatim: "If a Summary
    task (at any level) has a predecessor or a constraint, the subtask can't be scheduled any
    earlier than the summary task." (the Project 2007 list, item 11, repeats it). Hand arithmetic
    on the declared calendar (480 working minutes a day, Mon 2026-06-01 08:00 = 0, weekends off):
    A = 0..1440 (Wed 06-03 17:00); the lowered FS0 puts C1 >= 1440; the SNET is working day 10 =
    Mon 06-15 08:00 = 10 x 480 = 4800; C1 = max(1440, 4800) = 4800..5760 (Tue 06-16 17:00); C2 =
    5760..6240 (Wed 06-17 17:00); project finish 6240 = 06/17/2026, 7 working days after 2880.
    Without S's predecessor: C1 = max(0, 4800) -- the same 4800 / 6240.

    Independence: the rule is Microsoft's published description of its own scheduler and the
    expected offsets are hand arithmetic on the input written here; no engine or importer helper
    produces an expectation. Controls in the same test (preconditions): the SAME SNET on the leaf
    C1 gives 4800 / 6240 / 6240 today (the engine can reach the numbers), and with no constraint
    the summary's FS0 is lowered onto its leaves (C1 1440) -- so the hierarchy is right and the
    constraint alone is lost. Not asserted (MS Project semantics not separately sourced): the
    same mechanism also drops a summary FNET, FNLT and Deadline (verifier siblings). A vendored
    MPXJ ``MicrosoftScheduler`` also ignores the summary SNET -- a third-party reimplementation,
    recorded by the verifier as a contrary non-authoritative witness.
    """
    sch = parse_mspdi_text(_a0923_cpm_030_mspdi("summary"))
    s = next((t for t in sch.tasks if t.unique_id == 10), None)
    want_date = dt.datetime.fromisoformat(_A0923_CPM_030_SNET)
    if (
        s is None
        or not s.is_summary
        or (s.constraint_type, s.constraint_date)
        != (
            ConstraintType.SNET,
            want_date,
        )
    ):
        pytest.fail(f"precondition: the importer no longer keeps S as a SNET summary: {s}")
    kept = {(r.predecessor_id, r.successor_id) for r in sch.relationships}
    if kept != {(1, 10), (11, 12)}:
        pytest.fail(f"precondition: the importer's links are {kept}")
    wed_1700 = dt.datetime(2026, 6, 17, 17, 0)
    leaf = _a0923_cpm_030_solve(_a0923_cpm_030_mspdi("leaf"))
    if leaf != (4800, 6240, 6240, wed_1700):
        pytest.fail(f"precondition (control): the same SNET on the leaf C1 now gives {leaf}")
    bare = _a0923_cpm_030_solve(_a0923_cpm_030_mspdi("none"))
    if bare[:3] != (1440, 2880, 2880):
        pytest.fail(f"precondition (control): the summary's FS0 no longer lowers to C1: {bare}")

    got = {
        "summary SNET, FS0 after A": _a0923_cpm_030_solve(_a0923_cpm_030_mspdi("summary")),
        "summary SNET, no predecessor": _a0923_cpm_030_solve(
            _a0923_cpm_030_mspdi("summary", summary_has_predecessor=False)
        ),
    }
    wrong: dict[str, str] = {
        name: f"C1 ES {v[0]}, C2 EF {v[1]}, finish {v[2]} ({v[3]:%a %Y-%m-%d %H:%M})"
        for name, v in got.items()
        if v != (4800, 6240, 6240, wed_1700)
    }
    served = _a0923_cpm_030_served_finish(_a0923_cpm_030_mspdi("summary"))
    if served != "06/17/2026":
        wrong["/analysis"] = f"computed finish {served}"
    assert not wrong, (
        "the summary's SNET 2026-06-15 08:00 did not hold back its subtasks (hand: C1 ES 4800, "
        f"C2 EF 6240, finish 6240 = Wed 2026-06-17 17:00, 'computed finish 06/17/2026'): {wrong}"
    )


# --- A0923-CPM-031 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    pytest, TestClient (fastapi.testclient), compute_cpm (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi),
#              SessionState and create_app (schedule_forensics.web.app)
#   ALSO NEEDS ``from urllib.parse import quote`` on the header
#   fixture    the module-level autouse _air_gapped
# Input: inline MSPDI text (built below). No fixture file; nothing CUI.

#: One task row: (UID, name, Duration, DurationFormat, ConstraintType, ConstraintDate, FS pred).
_A0923Cpm031Row = tuple[int, str, str, int, int, str, int | None]

#: MSPDI ConstraintType codes (Microsoft Learn "ConstraintType Element"): 0 ASAP, 2 MSO, 3 MFO.
_A0923_CPM_031_ASAP, _A0923_CPM_031_MSO, _A0923_CPM_031_MFO = 0, 2, 3


def _a0923_cpm_031_mspdi(rows: tuple[_A0923Cpm031Row, ...]) -> str:
    """MS Project's Standard calendar (Mon-Fri 08:00-12:00 + 13:00-17:00), StartDate Mon
    2026-06-01 08:00, HonorConstraints 1 (the engine's modelled mode)."""
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
        f"<Task><UID>{uid}</UID><ID>{uid}</ID><Name>{name}</Name><Duration>{dur}</Duration>"
        f"<DurationFormat>{fmt}</DurationFormat><ConstraintType>{ctype}</ConstraintType>"
        + (f"<ConstraintDate>{cdate}</ConstraintDate>" if cdate else "")
        + (
            f"<PredecessorLink><PredecessorUID>{pred}</PredecessorUID><Type>1</Type>"
            "<LinkLag>0</LinkLag><LagFormat>7</LagFormat></PredecessorLink>"
            if pred is not None
            else ""
        )
        + "</Task>"
        for uid, name, dur, fmt, ctype, cdate, pred in rows
    )
    return (
        '<Project xmlns="http://schemas.microsoft.com/project"><Name>f-edge2-003</Name>'
        "<ScheduleFromStart>1</ScheduleFromStart><StartDate>2026-06-01T08:00:00</StartDate>"
        "<CalendarUID>1</CalendarUID><HonorConstraints>1</HonorConstraints>"
        "<Calendars><Calendar><UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>"
        f"<BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{days}</WeekDays></Calendar></Calendars>"
        f"<Tasks>{tasks}</Tasks></Project>"
    )


#: B: an unrelated 2-day task so the pinned M is not the whole project.
_A0923_CPM_031_B: _A0923Cpm031Row = (2, "B", "PT16H0M0S", 7, _A0923_CPM_031_ASAP, "", None)

#: The defect inputs: M has NO predecessor and a pin dated before (or straddling) the project
#: start. (label, M's row, M's hand (ES, EF) offsets on the project axis.)
_A0923_CPM_031_CASES: tuple[tuple[str, _A0923Cpm031Row, tuple[int, int]], ...] = (
    (
        "MSO Mon 05-25 08:00, 2 d",
        (1, "M", "PT16H0M0S", 7, _A0923_CPM_031_MSO, "2026-05-25T08:00:00", None),
        (-2400, -1440),
    ),
    (
        "MFO Tue 05-26 17:00, 2 d",
        (1, "M", "PT16H0M0S", 7, _A0923_CPM_031_MFO, "2026-05-26T17:00:00", None),
        (-2400, -1440),
    ),
    (
        "MFO Tue 06-02 17:00, 5 d (straddles the start)",
        (1, "M", "PT40H0M0S", 7, _A0923_CPM_031_MFO, "2026-06-02T17:00:00", None),
        (-1440, 960),
    ),
    (
        "MSO Mon 05-25 08:00, 48 elapsed h (wall path)",
        (1, "M", "PT48H0M0S", 6, _A0923_CPM_031_MSO, "2026-05-25T08:00:00", None),
        (-2400, -1440),
    ),
)


def _a0923_cpm_031_served(text: str) -> tuple[float, bool, str, float]:
    """(M's total_float_days, M's is_critical, DCMA-13 status, DCMA-13 value) as
    /api/analysis/<key> serves them for this one-file session."""
    state = SessionState()
    client = TestClient(create_app(state))
    up = client.post("/upload", files={"files": ("a0923_cpm_031.xml", text.encode(), "text/xml")})
    if up.status_code != 200 or len(state.schedules) != 1:
        pytest.fail(f"precondition: upload answered {up.status_code} ({list(state.schedules)})")
    resp = client.get(f"/api/analysis/{quote(next(iter(state.schedules)), safe='')}")
    if resp.status_code != 200:
        pytest.fail(f"precondition: /api/analysis answered {resp.status_code}")
    body = resp.json()
    m = next((a for a in body.get("activities", ()) if a.get("unique_id") == 1), None)
    cpli = body.get("dcma", {}).get("DCMA13")
    if m is None or not isinstance(cpli, dict) or cpli.get("name") != "CPLI":
        pytest.fail("precondition: /api/analysis no longer serves UID 1 and DCMA13 (CPLI)")
    return m["total_float_days"], m["is_critical"], cpli["status"], cpli["value"]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-031: a Must Start/Finish On pin dated before the project start on a task with "
        "no predecessor is measured against the project-start clamp (logic_es = max([0, "
        "*bounds]), cpm.py:2736-2739; the wall path's cands = [ps], :2527/:2576), so M placed "
        "exactly at its MSO Mon 05-25 (ES=LS, EF=LF) reports total float -2400 (-5.0 d served, "
        "CPLI FAIL -1.5) where Microsoft's min(LS-ES, LF-EF) is 0"
    ),
)
def test_a0923_cpm_031_an_unviolated_pin_before_the_project_start_has_zero_float() -> None:
    """A0923-CPM-031 (finder id F-EDGE2-003) · CPM · T1 (latent: no committed file pins a task
    before its project start).

    Claim (verifier's narrowed claim): at 13b13f38, on the inline MSPDI below (project start Mon
    2026-06-01 08:00, Standard calendar), task M (UID 1) with NO predecessor and a Must Start On
    Mon 2026-05-25 08:00 (2 d) -- or Must Finish On Tue 2026-05-26 17:00 (2 d) -- is placed at
    its date by ``parse_mspdi_text`` + ``compute_cpm`` (ES -2400, EF -1440, LS -2400, LF -1440,
    so min(LS-ES, LF-EF) = 0) yet reports ``total_float`` -2400; a 5 d MFO Tue 06-02 17:00
    straddling the start reports -1440; the same MSO on a 48-elapsed-hour task (the wall path)
    reports -10080. ``/api/analysis`` serves M's total float as -5.0 d and DCMA-13 CPLI "FAIL
    -1.5". Mechanism: the violation is measured against ``logic_es = max([0, *bounds])``
    (``engine/cpm.py:2736``, used at :2739) -- i.e. against the project-start CLAMP, which no
    predecessor imposes; the wall path seeds ``cands = [ps]`` (:2527) and measures at :2576.
    NOT claimed (verifier refuted it): M's ``is_critical`` / critical-path membership -- with
    the correct float 0 the engine's own rule (``total_float <= 0``, ADR-0322:78) keeps M
    critical, as MPXJ's MicrosoftScheduler does; the test asserts M stays critical.

    Authority: A1 -- Microsoft Learn, "Definition of Microsoft Project constraints",
    https://learn.microsoft.com/en-us/previous-versions/troubleshoot/microsoft-365/microsoft-365-apps/project/definition-of-project-constraints
    (retrieved 2026-09-28): "Must Finish On: Schedules the task to finish on the constraint
    date. Once selected the task will not be moveable on the timescale. EF,LF,SF=CD" and "Must
    Start On: Schedules the task to start on the constraint date. Once selected the task will
    not be movable on the timescale. ES,LS,SS=CD". Microsoft Support, "Total Slack (task
    field)", https://support.microsoft.com/en-us/office/total-slack-task-field-55dacfda-95bc-469c-9cc9-b1454b8df42c
    (retrieved 2026-09-28): "Total slack is calculated as the smaller value of the Late Finish
    minus the Early Finish field, and the Late Start minus the Early Start field." Hand
    arithmetic (480 working min/day, Mon 06-01 08:00 = 0): Mon 05-25 08:00 is 5 working days
    earlier = -2400 = ES = LS (MSO); EF = -2400 + 960 = -1440 = LF (nothing after M needs it
    sooner); total slack = min(0, 0) = 0. MFO Tue 05-26 17:00: EF = LF = -1440, ES = LS = -2400
    -> 0. MFO Tue 06-02 17:00 on 5 d: EF = LF = 960, ES = LS = -1440 -> 0. Elapsed 48 h from
    05-25 08:00: ES = LS, EF = LF -> 0. A2 -- ``engine/cpm.py:62-63``: "a pin VIOLATED by logic
    (predecessors push past the constraint) reports the violation as negative float on the
    pinned task itself"; ``docs/adr/0322-the-base-cpm-honors-per-task-calendars.md:76-78``:
    "A violated pin now carries MS Project's negative slack (Jacked 2 UID 30: exactly -2 400);
    an unviolated pin is unchanged." (the ADR's minus sign is U+2212).

    Independence: Microsoft's formulas and hand arithmetic on the input written here; the
    engine's own four dates for M are checked (precondition) to equal the hand dates, so the
    float contradicts the dates the engine itself placed. Controls in the same test
    (preconditions): the same MSO dated ON the project start gives TF 0 today, and a pin
    GENUINELY violated by a predecessor (A 5 d -FS0-> P 2 d MSO Wed 06-03 08:00) keeps its
    -1440 -- a fix may not erase real violations.
    """
    on_start = compute_cpm(
        parse_mspdi_text(
            _a0923_cpm_031_mspdi(
                (
                    (1, "M", "PT16H0M0S", 7, _A0923_CPM_031_MSO, "2026-06-01T08:00:00", None),
                    _A0923_CPM_031_B,
                )
            )
        )
    ).timings[1]
    if (on_start.early_start, on_start.total_float, on_start.is_critical) != (0, 0, True):
        pytest.fail(f"precondition (control): an MSO ON the project start now reads {on_start}")
    violated = compute_cpm(
        parse_mspdi_text(
            _a0923_cpm_031_mspdi(
                (
                    (1, "A", "PT40H0M0S", 7, _A0923_CPM_031_ASAP, "", None),
                    (2, "P", "PT16H0M0S", 7, _A0923_CPM_031_MSO, "2026-06-03T08:00:00", 1),
                    (3, "C", "PT8H0M0S", 7, _A0923_CPM_031_ASAP, "", 2),
                )
            )
        )
    ).timings[2]
    if (violated.early_start, violated.total_float) != (960, -1440):
        pytest.fail(f"precondition (control): the predecessor-violated MSO now reads {violated}")

    wrong: dict[str, str] = {}
    for label, row, (hand_es, hand_ef) in _A0923_CPM_031_CASES:
        sch = parse_mspdi_text(_a0923_cpm_031_mspdi((row, _A0923_CPM_031_B)))
        m_task = sch.tasks_by_id[1]
        if m_task.constraint_date is None or m_task.duration_is_elapsed != (row[3] == 6):
            pytest.fail(f"precondition: {label}: the importer no longer keeps M's pin / format")
        t = compute_cpm(sch).timings[1]
        dates = (t.early_start, t.early_finish, t.late_start, t.late_finish)
        if dates != (hand_es, hand_ef, hand_es, hand_ef):
            pytest.fail(f"precondition: {label}: M is no longer placed at its pin: {dates}")
        if (t.total_float, t.is_critical) != (0, True):
            wrong[label] = f"TF {t.total_float} (ES=LS {t.early_start}, EF=LF {t.early_finish})"
    served = _a0923_cpm_031_served(
        _a0923_cpm_031_mspdi((_A0923_CPM_031_CASES[0][1], _A0923_CPM_031_B))
    )
    if served != (0.0, True, "PASS", 1.0):
        wrong["/api/analysis (MSO 05-25)"] = (
            f"M total_float_days {served[0]}, critical {served[1]}, DCMA-13 CPLI {served[2]} "
            f"{served[3]}"
        )
    assert not wrong, (
        "a Must Start/Finish On pin before the project start, with no predecessor, is reported "
        f"as violated (hand: total float 0 = min(LS-ES, LF-EF), still critical): {wrong}"
    )


# --- A0923-CPM-032 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    datetime as dt, re, pytest, TestClient (fastapi.testclient),
#              compute_cpm (schedule_forensics.engine.cpm),
#              SessionState and create_app (schedule_forensics.web.app)
#   ALSO NEEDS on the header: ``from urllib.parse import quote``;
#              ``from schedule_forensics.engine.driving_slack import compute_driving_slack``;
#              ``from schedule_forensics.engine.path_trace import ancestors_of,
#              subschedule_to_target``; ``from schedule_forensics.model.calendar import Calendar``;
#              ``from schedule_forensics.model.relationship import Relationship``;
#              ``from schedule_forensics.model.schedule import Schedule``;
#              ``from schedule_forensics.model.task import Task``
#   fixture    the module-level autouse _air_gapped
# Inputs: model objects and inline MSPDI text (built below). No fixture file; nothing CUI.

#: UIDs: A (2 d) -FS0-> summary S{B 1 d, C 1 d}; C -FS0-> D (1 d). D is the focus / Target UID.
#: X (4 d, no predecessor) -FS0-> D appears only in the ``with_x`` variant.
_A0923_CPM_032_A, _A0923_CPM_032_S, _A0923_CPM_032_B, _A0923_CPM_032_C, _A0923_CPM_032_D = (
    1,
    2,
    3,
    4,
    5,
)
_A0923_CPM_032_X = 6


def _a0923_cpm_032_links(on_children: bool, with_x: bool = False) -> tuple[tuple[int, int], ...]:
    """The FS0 links. ``on_children=False`` (the defect input): A's logic sits on the SUMMARY S.
    ``True`` (the control): the identical network with A's logic written on S's children.
    ``with_x`` adds X -FS0-> D, so A reaches D with one day of driving slack, not zero."""
    a, s, b, c, d = (
        _A0923_CPM_032_A,
        _A0923_CPM_032_S,
        _A0923_CPM_032_B,
        _A0923_CPM_032_C,
        _A0923_CPM_032_D,
    )
    links = ((a, b), (a, c), (c, d)) if on_children else ((a, s), (c, d))
    return (*links, (_A0923_CPM_032_X, d)) if with_x else links


def _a0923_cpm_032_schedule(on_children: bool, with_x: bool = False) -> Schedule:
    """Undated model objects on MS Project's Standard day (08-12 / 13-17, 480 min), start Mon
    2026-03-02 08:00; the hierarchy is the WBS (= the outline), which the CPM lowering reads."""
    tasks = (
        Task(unique_id=_A0923_CPM_032_A, name="A", wbs="1", duration_minutes=960),
        Task(unique_id=_A0923_CPM_032_S, name="S", wbs="2", is_summary=True, duration_minutes=0),
        Task(unique_id=_A0923_CPM_032_B, name="B", wbs="2.1", duration_minutes=480),
        Task(unique_id=_A0923_CPM_032_C, name="C", wbs="2.2", duration_minutes=480),
        Task(unique_id=_A0923_CPM_032_D, name="D", wbs="3", duration_minutes=480),
    ) + (
        (Task(unique_id=_A0923_CPM_032_X, name="X", wbs="4", duration_minutes=1920),)
        if with_x
        else ()
    )
    return Schedule(
        name="f-meta2-001",
        project_start=dt.datetime(2026, 3, 2, 8, 0),
        calendar=Calendar(day_segments=((480, 720), (780, 1020))),
        tasks=tasks,
        relationships=tuple(
            Relationship(predecessor_id=p, successor_id=s)
            for p, s in _a0923_cpm_032_links(on_children, with_x)
        ),
    )


def _a0923_cpm_032_mspdi(on_children: bool) -> str:
    """The same network as an MS Project-shaped MSPDI: Standard calendar, WBS = OutlineNumber,
    every task carrying the Start/Finish MS Project schedules it at (A Mon-Tue, S/B/C Wed, D
    Thu 03-05 17:00 -- the CPM of the file reproduces them)."""
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
    preds: dict[int, list[int]] = {}
    for p, s in _a0923_cpm_032_links(on_children):
        preds.setdefault(s, []).append(p)
    rows = (
        (_A0923_CPM_032_A, "A", "1", 16, "2026-03-02", "2026-03-03", 0),
        (_A0923_CPM_032_S, "S", "2", 8, "2026-03-04", "2026-03-04", 1),
        (_A0923_CPM_032_B, "B", "2.1", 8, "2026-03-04", "2026-03-04", 0),
        (_A0923_CPM_032_C, "C", "2.2", 8, "2026-03-04", "2026-03-04", 0),
        (_A0923_CPM_032_D, "D", "3", 8, "2026-03-05", "2026-03-05", 0),
    )
    tasks = "".join(
        f"<Task><UID>{uid}</UID><ID>{uid}</ID><Name>{name}</Name><WBS>{wbs}</WBS>"
        f"<OutlineNumber>{wbs}</OutlineNumber><OutlineLevel>{wbs.count('.') + 1}</OutlineLevel>"
        f"<Summary>{summary}</Summary><Duration>PT{hours}H0M0S</Duration>"
        f"<DurationFormat>7</DurationFormat><Start>{start}T08:00:00</Start>"
        f"<Finish>{finish}T17:00:00</Finish><PercentComplete>0</PercentComplete>"
        + "".join(
            f"<PredecessorLink><PredecessorUID>{p}</PredecessorUID><Type>1</Type>"
            "<LinkLag>0</LinkLag><LagFormat>7</LagFormat></PredecessorLink>"
            for p in preds.get(uid, ())
        )
        + "</Task>"
        for uid, name, wbs, hours, start, finish, summary in rows
    )
    return (
        '<Project xmlns="http://schemas.microsoft.com/project"><Name>SumLogic</Name>'
        "<ScheduleFromStart>1</ScheduleFromStart><StartDate>2026-03-02T08:00:00</StartDate>"
        "<FinishDate>2026-03-05T17:00:00</FinishDate><CalendarUID>1</CalendarUID>"
        "<Calendars><Calendar><UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>"
        f"<BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{days}</WeekDays></Calendar></Calendars>"
        f"<Tasks>{tasks}</Tasks></Project>"
    )


def _a0923_cpm_032_engine(sch: Schedule, sch_x: Schedule) -> dict[str, object]:
    """What the trace and the target scope make of focus D (the engine's public entry points);
    ``sch_x`` is the same network with X -FS0-> D, where A's driving slack to D is one day."""
    slack = compute_driving_slack(sch, _A0923_CPM_032_D)
    a = slack.get(_A0923_CPM_032_A)
    a_x = compute_driving_slack(sch_x, _A0923_CPM_032_D).get(_A0923_CPM_032_A)
    scoped = compute_cpm(subschedule_to_target(sch, _A0923_CPM_032_D))
    return {
        "A in ancestors_of(D)": _A0923_CPM_032_A in ancestors_of(sch, _A0923_CPM_032_D),
        "A's driving slack to D (min), on path": (
            None if a is None else (a.driving_slack_minutes, a.on_driving_path)
        ),
        "A's driving slack to D with X also driving D (min), on path": (
            None if a_x is None else (a_x.driving_slack_minutes, a_x.on_driving_path)
        ),
        "D's early finish under the Target-UID scope": scoped.timings[
            _A0923_CPM_032_D
        ].early_finish,
    }


def _a0923_cpm_032_served(on_children: bool) -> dict[str, object]:
    """The served app on the MSPDI: /analysis with and without Target UID D, and /api/driving."""
    state = SessionState()
    client = TestClient(create_app(state))
    up = client.post(
        "/upload",
        files={"files": ("SumLogic.xml", _a0923_cpm_032_mspdi(on_children).encode(), "text/xml")},
    )
    if up.status_code != 200 or len(state.schedules) != 1:
        pytest.fail(f"precondition: upload answered {up.status_code} ({list(state.schedules)})")
    key = quote(next(iter(state.schedules)), safe="")
    concern = re.compile(r"\d+ scheduled dates? (?:is|are) not supported by logic")

    def visible(path: str) -> str:
        resp = client.get(path)
        if resp.status_code != 200:
            pytest.fail(f"precondition: {path} answered {resp.status_code}")
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", resp.text))

    untargeted = visible(f"/analysis/{key}")
    if client.post("/target", data={"uid": "5", "next_url": "/"}).status_code != 200:
        pytest.fail("precondition: POST /target uid=5 no longer lands on a page")
    targeted = visible(f"/analysis/{key}")
    rows = client.get(f"/api/driving/{key}", params={"target": 5}).json().get("rows", [])
    return {
        "untargeted concern": bool(concern.search(untargeted)),
        "targeted /analysis 'date not supported by logic' concern": bool(concern.search(targeted)),
        "/api/driving?target=5 DRIVING rows": sorted(
            r["unique_id"] for r in rows if r.get("tier") == "DRIVING"
        ),
    }


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-032: the CPM lowers logic on a summary onto its children (ADR-0043) but the "
        "driving-slack trace and the Target-UID scope read the raw links, so on A -> S{B, C}, "
        "C -> D the driving path to D omits A (TF 0, D's real driver; with a 4 d X also driving "
        "D, A's 1-day driving slack is not measured), the target-scoped D "
        "finishes at offset 960 instead of 1920, and /analysis under Target UID D raises a false "
        "'1 scheduled date is not supported by logic' concern against C"
    ),
)
def test_a0923_cpm_032_logic_on_a_summary_drives_the_trace_and_the_target_scope() -> None:
    """A0923-CPM-032 (finder id F-META2-001) · CPM · T1 (latent: no committed schedule carries logic
    on a summary).

    Claim (verifier's narrowed claim): at 13b13f38, on A (2 d) -FS0-> summary S{B 1 d, C 1 d},
    C -FS0-> D (1 d) (Standard 08-12/13-17, start Mon 2026-03-02 08:00), ``compute_cpm`` honours
    the summary's logic (A TF 0, C ES 960, D EF 1920) while ``path_trace.ancestors_of(D)`` =
    {C}, ``compute_driving_slack(target=D)`` and the served ``/api/driving/<key>?target=5`` give
    the driving path (C, D) with A absent, and ``subschedule_to_target`` keeps {C, D} and drops
    C's only predecessor -- so D's scoped finish is offset 960 (Tue 03-03 17:00), not 1920 (Thu
    03-05 17:00), and on the MS Project-shaped MSPDI the served ``/analysis`` under Target UID D
    shows "1 scheduled date is not supported by logic" citing C. Mechanism: the CPM builds its
    edges from ``lower_summary_relationships`` (ADR-0043) but ``path_trace.py``
    (``ancestors_of`` :39, ``subschedule_to_target`` :66-68) and ``driving_slack.py``'s two link
    loops (:330, :343) iterate ``schedule.relationships``. NOT asserted (verifier: separable):
    the "summary task carries logic" finding also disappears under a Target UID, because
    ``subschedule_to_target`` keeps no summary rows in ANY file (ADR-0105's population); feeding
    the trace the lowered edges does not bring it back.

    Authority: A1 -- Microsoft Learn, "Tasks don't schedule as expected in Microsoft Project",
    https://learn.microsoft.com/en-us/troubleshoot/microsoft-365-apps/project/tasks-not-scheduled
    (retrieved 2026-09-28), Project 2010 item 14: "Predecessor and Successor relationships
    assigned to summary task can affect sub task of the summary task in addition to the summary
    task(s) that are linked." and item 11: "If a Summary task (at any level) has a predecessor
    or a constraint, the subtask can't be scheduled any earlier than the summary task." Hand
    arithmetic (480 min/day): A 0..960; S's predecessor holds B and C to ES 960 (EF 1440); D
    1440..1920; backward from D: C LS 960 -> A LF 960 -> A TF 0; a slip of A moves C and D
    one-for-one, so A's driving slack to D is 0 (A drives D). Variant with X (4 d, no
    predecessor) -FS0-> D: D ES = max(C EF 1440, X EF 1920) = 1920, so C's driving slack is
    1920 - 1440 = 480 and A's (via the lowered A -> C, gap 960 - 960 = 0) is 0 + 480 = 480 --
    one working day, NOT on the driving path. (The variant gives the driving-slack link loops
    their own teeth: a trace that includes A but walks the raw links finds no in-trace
    successor for A and defaults its slack to 0, ``driving_slack.py:386``.) A2 --
    ``engine/driving_slack.py:3-4`` "Driving Slack -- how many working days it can slip before
    it would delay the focus task along its logic path"; ``engine/path_trace.py:31`` "These are
    exactly the activities that can drive the focus task (its predecessors, transitively)";
    ``path_trace.py:54`` "``schedule`` restricted to ``target_uid`` and every activity that
    drives it"; ``docs/adr/0043-logic-on-summary-tasks.md:14-15`` "MS Project honors logic on a
    summary by applying it to the summary's children"; ``docs/adr/0105-target-endpoint-and-risk-
    matrix.md:30-31`` "A task's early finish depends only on its predecessors, so the target's
    own computed finish is identical truncated or not" (falsified here: 1920 -> 960).

    Independence: Microsoft's documented rule, hand arithmetic, and the engine's OWN CPM on the
    same input (a precondition) -- never the trace under test. Controls (preconditions): the
    identical network with A's logic written on the children gives A on D's path at 0 (480 with
    X), scoped
    D EF 1920 and no false concern on the served page; without a Target UID the summary-logic
    page shows no concern either.
    """
    sch, control = _a0923_cpm_032_schedule(False), _a0923_cpm_032_schedule(True)
    sch_x, control_x = _a0923_cpm_032_schedule(False, True), _a0923_cpm_032_schedule(True, True)
    cpm = compute_cpm(sch).timings
    got_cpm = (
        cpm[_A0923_CPM_032_A].total_float,
        cpm[_A0923_CPM_032_C].early_start,
        cpm[_A0923_CPM_032_D].early_finish,
    )
    cpm_x = compute_cpm(sch_x).timings
    got_cpm_x = (cpm_x[_A0923_CPM_032_A].total_float, cpm_x[_A0923_CPM_032_D].early_start)
    if got_cpm != (0, 960, 1920) or got_cpm_x != (480, 1920):
        pytest.fail(
            f"precondition: the CPM no longer honours S's logic (A TF, C ES, D EF) {got_cpm}; "
            f"with X (A TF, D ES) {got_cpm_x}"
        )
    want: dict[str, object] = {
        "A in ancestors_of(D)": True,
        "A's driving slack to D (min), on path": (0, True),
        "A's driving slack to D with X also driving D (min), on path": (480, False),
        "D's early finish under the Target-UID scope": 1920,
    }
    got_control = _a0923_cpm_032_engine(control, control_x)
    if got_control != want:
        pytest.fail(f"precondition (control): children-logic input {got_control}")
    served_want: dict[str, object] = {
        "untargeted concern": False,
        "targeted /analysis 'date not supported by logic' concern": False,
        "/api/driving?target=5 DRIVING rows": [
            _A0923_CPM_032_A,
            _A0923_CPM_032_C,
            _A0923_CPM_032_D,
        ],
    }
    if _a0923_cpm_032_served(on_children=True) != served_want:
        pytest.fail(f"precondition (control): served children-logic {_a0923_cpm_032_served(True)}")

    got = {**_a0923_cpm_032_engine(sch, sch_x), **_a0923_cpm_032_served(on_children=False)}
    if got["untargeted concern"]:
        pytest.fail("precondition: the summary-logic page shows the concern even without a target")
    wrong = {k: f"{got[k]} (want {v})" for k, v in {**want, **served_want}.items() if got[k] != v}
    assert not wrong, (
        f"logic on summary S is honoured by the CPM but not by the driving trace / target scope: "
        f"{wrong}"
    )


# --- A0923-CPM-033 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    datetime as dt, pytest, compute_cpm (schedule_forensics.engine.cpm)
#   ALSO NEEDS on the header: ``from schedule_forensics.model.calendar import Calendar``;
#              ``from schedule_forensics.model.relationship import Relationship``;
#              ``from schedule_forensics.model.schedule import Schedule``;
#              ``from schedule_forensics.model.task import Task``
#   fixture    the module-level autouse _air_gapped
# Input: model objects built below. No fixture file; nothing CUI.

#: MS Project's Standard day as minutes-from-midnight blocks: 08:00-12:00 + 13:00-17:00.
_A0923_CPM_033_STD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))
_A0923_CPM_033_START = dt.datetime(2026, 1, 5, 8, 0)  # Monday


def _a0923_cpm_033_schedule(lag: int, delay_p: int, delay_s: int, extra: int = 0) -> Schedule:
    """P (UID 3, 279 + ``extra`` working min, elapsed leveling delay ``delay_p``) -FS+``lag``->
    S (UID 5, 480 working min, elapsed leveling delay ``delay_s``); no constraint, no deadline,
    no progress."""
    return Schedule(
        name="f-meta2-002",
        project_start=_A0923_CPM_033_START,
        calendar=_A0923_CPM_033_STD,
        calendars=(_A0923_CPM_033_STD,),
        tasks=(
            Task(
                unique_id=3, name="P", duration_minutes=279 + extra, leveling_delay_minutes=delay_p
            ),
            Task(unique_id=5, name="S", duration_minutes=480, leveling_delay_minutes=delay_s),
        ),
        relationships=(Relationship(predecessor_id=3, successor_id=5, lag_minutes=lag),),
    )


def _a0923_cpm_033_slip(lag: int, delay_p: int, delay_s: int) -> int:
    """THE ORACLE (Microsoft's Total Slack definition, measured on the FORWARD pass only): the
    largest number of working minutes P can be lengthened without moving the project finish.
    Lengthening a task cannot pull the finish earlier, so a bisection over [0, 4800] is exact."""
    base = compute_cpm(_a0923_cpm_033_schedule(lag, delay_p, delay_s)).project_finish
    lo, hi = 0, 4800
    if compute_cpm(_a0923_cpm_033_schedule(lag, delay_p, delay_s, hi)).project_finish == base:
        pytest.fail("precondition: a 10-day slip of P no longer moves the finish")
    while hi - lo > 1:  # invariant: lo keeps the finish, hi moves it
        mid = (lo + hi) // 2
        moved = compute_cpm(_a0923_cpm_033_schedule(lag, delay_p, delay_s, mid)).project_finish
        lo, hi = (mid, hi) if moved == base else (lo, mid)
    return lo


#: (label, lag, P's delay, S's delay): lagged FS links into a leveled successor from a leveled
#: (wall-path) predecessor -- the claim's network first, then the under- and over-stated twins.
_A0923_CPM_033_CASES = (
    ("claim: lag 966, P delay 2739, S delay 2333", 966, 2739, 2333),
    ("under-stated: lag 480, P delay 2739, S delay 2333", 480, 2739, 2333),
    ("over-stated: lag 1500, P delay 2739, S delay 4000", 1500, 2739, 4000),
)
#: Controls the engine gets right today: no lag; P off the wall path (no delay of its own).
_A0923_CPM_033_CONTROLS = (
    ("control: lag 0, P delay 2739, S delay 2333", 0, 2739, 2333),
    ("control: lag 966, P delay 0, S delay 2333", 966, 0, 2333),
)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-033: a lagged START-type need into a leveled successor removes the lag on the "
        "project axis FIRST and then the successor's elapsed leveling delay (cpm.py:2947, and "
        "the free-float twin via _succ_early_start_wall), the reverse of the forward pass, so P "
        "(279 min, delay 2739) -FS+966-> S (delay 2333) reads total and free float -759 and "
        "critical where it can slip 194-195 min (hand LF Wed 01-07 16:54)"
    ),
)
def test_a0923_cpm_033_a_lagged_link_into_a_leveled_successor_mirrors_the_forward_order() -> None:
    """A0923-CPM-033 (finder id F-META2-002) · CPM · T1 (latent: no committed lagged link enters a
    task-level-leveled task).

    Claim (verifier's narrowed claim): at 13b13f38, P (UID 3, 279 min, elapsed leveling delay
    2,739 min) -FS+966-> S (UID 5, 480 min, elapsed leveling delay 2,333 min), Standard 08-12/
    13-17, start Mon 2026-01-05 08:00, via ``compute_cpm`` gives P total float -759, free float
    -759, ``is_critical`` True and late finish Mon 01-05 17:00 (P's early start is Wed 01-07
    08:00), with no constraint, deadline or imposed finish. Mechanism: ``_succ_ls_wall``
    (``engine/cpm.py:2947``, the lag != 0 fallthrough) removes the lag on the project axis
    FIRST and then subtracts the ELAPSED delay from that wall instant -- the reverse of the
    forward order (lag, then delay: cpm.py:2528-2569) -- so the delay spans weekday nights
    instead of the weekend it spanned going forward; the free-float twin is
    ``_succ_free_start_wall`` (cpm.py:3181-3185) via ``_succ_early_start_wall``'s lag != 0
    branch. The class errs in both directions: lag 480 reads +201 where P can slip 680; lag 1500
    with S delay 4000 reads +960 (not critical) where P cannot slip at all.

    Distinct from the retained A0923-CPM-003 (an FF need into a leveled successor that ignores
    the delay ENTIRELY, ``_succ_lf_wall``): here the link is FS with a lag and the delay IS
    subtracted, in the wrong order; the CPM-003 fix (subtract the delay on the FF branch) leaves
    this red, and this fix leaves CPM-003's FF branch untouched.

    Authority: A1 -- Microsoft Support, "Total Slack (task field)",
    https://support.microsoft.com/en-us/office/total-slack-task-field-55dacfda-95bc-469c-9cc9-b1454b8df42c
    (retrieved 2026-09-28): "The Total Slack field contains the amount of time a task's finish
    date can be delayed without delaying the project's finish date." The oracle measures exactly
    that on the FORWARD pass (``_a0923_cpm_033_slip``), which the claim does not dispute, and the
    engine's float convention is that slip or one minute more (the lag-0 / P-undelayed controls
    read slip + 1 today). Hand arithmetic for the claim's network: P ES = Mon 08:00 + 2,739 min
    elapsed = Wed 05:39 -> Wed 08:00 (offset 960), EF 1239 (Wed 13:39); + lag 966 on the axis =
    2205 (Fri 13:45); + 2,333 min elapsed = Sun 04:38 -> S ES Mon 01-12 08:00 (2400), EF 2880.
    Backward in the mirrored order: S's late start Mon 08:00 less 2,333 min elapsed = Sat 17:07
    -> the last working instant Fri 17:00 (2400); less the lag 966 -> 1434 = Wed 16:54 = P's late
    finish; total float 1434 - 1239 = 195, free float 195 (S is P's only successor and is
    critical). A2 -- ``engine/cpm.py:147-148``: "Total float may be negative (an imposed
    finish, or a violated cap / deadline / pin)" -- none exists here; ``cpm.py:3174-3175``
    (``_succ_free_start_wall``): "The forward pass ADDS a successor's stored leveling delay to
    its early start and the backward pass SUBTRACTS it from the need it presents
    (``ls_need``)".

    Independence: the slip oracle uses only the forward pass and the project finish; the hand
    arithmetic uses only the declared calendar. MS Project's own late dates for this shape are
    UNVERIFIED (no committed save carries a lagged link into a task-level-leveled successor).
    Controls (preconditions): with lag 0, and with P carrying no delay of its own, the engine's
    float already sits in the oracle's band.
    """
    for label, lag, delay_p, delay_s in _A0923_CPM_033_CONTROLS:
        slip = _a0923_cpm_033_slip(lag, delay_p, delay_s)
        tf = compute_cpm(_a0923_cpm_033_schedule(lag, delay_p, delay_s)).timings[3].total_float
        if not slip <= tf <= slip + 1:
            pytest.fail(f"precondition ({label}): TF {tf} is outside the forward slip {slip} (+1)")

    wrong: dict[str, str] = {}
    for label, lag, delay_p, delay_s in _A0923_CPM_033_CASES:
        slip = _a0923_cpm_033_slip(lag, delay_p, delay_s)
        t = compute_cpm(_a0923_cpm_033_schedule(lag, delay_p, delay_s)).timings[3]
        bad = not slip <= t.total_float <= slip + 1 or t.is_critical != (t.total_float <= 0)
        if bad:
            wrong[label] = f"TF {t.total_float} (critical {t.is_critical}); P can slip {slip}"
    sch = _a0923_cpm_033_schedule(966, 2739, 2333)
    t = compute_cpm(sch).timings[3]
    if t.early_finish_wall != dt.datetime(2026, 1, 7, 13, 39):
        pytest.fail(
            f"precondition: P's early finish is no longer Wed 13:39 ({t.early_finish_wall})"
        )
    hand_lf, lf = dt.datetime(2026, 1, 7, 16, 54), t.late_finish_wall
    lf_ok = lf is not None and abs((lf - hand_lf).total_seconds()) <= 60
    if not (194 <= t.free_float <= 195 and lf_ok):
        wrong["claim: free float / late finish"] = (
            f"FF {t.free_float}, LF {lf} (hand FF 195, LF {hand_lf:%a %m-%d %H:%M}, +-1 min)"
        )
    assert not wrong, (
        "a lagged FS need into a leveled successor is not the forward order mirrored (total "
        f"float outside the forward-pass slip band, or free float / late finish off hand): {wrong}"
    )


# --- A0923-CPM-034 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    datetime as dt, gzip, xml.etree.ElementTree as ET, pytest,
#              compute_cpm (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi)
#   ALSO NEEDS on the header: ``offset_to_start_datetime`` on the engine.cpm import line;
#              ``from schedule_forensics.model.calendar import Calendar``;
#              ``from schedule_forensics.model.relationship import Relationship``;
#              ``from schedule_forensics.model.schedule import Schedule``;
#              ``from schedule_forensics.model.task import Task``
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Inputs: model objects built below, and the committed, non-CUI goldens
# tests/fixtures/golden/fuse_hardfile/Hard_File and Hard_File_updated .mspdi.xml.gz (read with
# gzip + ElementTree for MS Project's stored LateStart / LateFinish). No new fixture; nothing CUI.

_A0923_CPM_034_STD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))
_A0923_CPM_034_24H = Calendar(
    uid=4, name="24 Hours", working_minutes_per_day=1440, work_weekdays=(0, 1, 2, 3, 4, 5, 6)
)
_A0923_CPM_034_MON = dt.datetime(2026, 1, 5, 8, 0)

#: MS Project's stored late instants on the two committed Hard_File saves (identical in both):
#: UID -> (LateStart, LateFinish). 264 ('Create proficiency exams', a 24-hour crew booking on the
#: Standard task calendar) FS0 -> 262 (Standard, stored LateStart 2026-10-07 13:00); 274 FS0 -> 264;
#: milestone 260 FS0 -> 274.
_A0923_CPM_034_STORED = {
    264: ("2026-10-06T05:00:00", "2026-10-07T13:00:00"),
    274: ("2026-10-05T21:00:00", "2026-10-06T05:00:00"),
    260: ("2026-10-05T21:00:00", "2026-10-05T21:00:00"),
}


def _a0923_cpm_034_p(kind: str, minutes: int) -> Task:
    """P (UID 2): ``kind`` "24h" -> on the '24 Hours' task calendar; "elapsed" -> an elapsed
    duration; "project" -> on the project calendar (the control)."""
    if kind == "24h":
        return Task(unique_id=2, name="P", duration_minutes=minutes, calendar_uid=4)
    if kind == "elapsed":
        return Task(unique_id=2, name="P", duration_minutes=minutes, duration_is_elapsed=True)
    return Task(unique_id=2, name="P", duration_minutes=minutes)


def _a0923_cpm_034_solve(kind: str, p_minutes: int, q_minutes: int | None) -> tuple[Any, Any]:
    """P -FS0-> S (UID 3, 1,440 min, Standard); with ``q_minutes`` also Q (UID 4, Standard)
    -FS0-> S. Start Mon 2026-01-05 08:00 on the Standard calendar (08:00-12:00 + 13:00-17:00)."""
    tasks = [_a0923_cpm_034_p(kind, p_minutes), Task(unique_id=3, name="S", duration_minutes=1440)]
    links = [Relationship(predecessor_id=2, successor_id=3)]
    if q_minutes is not None:
        tasks.append(Task(unique_id=4, name="Q", duration_minutes=q_minutes))
        links.append(Relationship(predecessor_id=4, successor_id=3))
    res = compute_cpm(
        Schedule(
            name="f-meta2-003",
            project_start=_A0923_CPM_034_MON,
            calendar=_A0923_CPM_034_STD,
            calendars=(_A0923_CPM_034_STD, _A0923_CPM_034_24H),
            tasks=tuple(tasks),
            relationships=tuple(links),
        )
    )
    return res.timings[2], res.timings[3]


def _a0923_cpm_034_golden(name: str) -> dict[str, str]:
    """Engine vs MS Project's stored late instants for UIDs 264 / 274 / 260 on one golden."""
    raw = gzip.decompress((GOLDEN / "fuse_hardfile" / name).read_bytes())
    root = ET.fromstring(raw)
    stored: dict[int, tuple[str, str, str]] = {}
    for el in root.iter(NS + "Task"):
        ls, lf, pct = (
            (el.findtext(NS + k) or "").strip()
            for k in ("LateStart", "LateFinish", "PercentComplete")
        )
        stored[int((el.findtext(NS + "UID") or "-1").strip())] = (ls, lf, pct)
    for uid, (ls, lf) in _A0923_CPM_034_STORED.items():
        if stored.get(uid) != (ls, lf, "0"):
            pytest.fail(
                f"precondition: {name} UID {uid} no longer stores {ls} / {lf}: {stored.get(uid)}"
            )
    if stored.get(262, ("", "", ""))[0] != "2026-10-07T13:00:00":
        pytest.fail(f"precondition: {name} UID 262's stored LateStart moved: {stored.get(262)}")
    sch = parse_mspdi_text(raw.decode("utf-8"))
    timings = compute_cpm(sch).timings
    # the successor's own late start is not in dispute: 262 (project axis) is MS Project's 13:00
    ls_262 = offset_to_start_datetime(sch.project_start, timings[262].late_start, sch.calendar)
    if ls_262 != dt.datetime(2026, 10, 7, 13, 0):
        pytest.fail(f"precondition: {name} UID 262's engine late start is {ls_262}, not 13:00")
    wrong: dict[str, str] = {}
    for uid, (ls, lf) in _A0923_CPM_034_STORED.items():
        t = timings[uid]
        if t.total_float != 0:
            pytest.fail(f"precondition: {name} UID {uid} total float {t.total_float} (stored 0)")
        got = (t.late_start_wall, t.late_finish_wall)
        want = (dt.datetime.fromisoformat(ls), dt.datetime.fromisoformat(lf))
        if got != want:
            wrong[f"{name} UID {uid} (LS, LF)"] = f"{got} (stored {want})"
    return wrong


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-034: a project-axis successor's late-start need is rendered by "
        "_offset_to_wall(role='start') (cpm.py:2947; free-float twin :3168), which at an INTERNAL "
        "block boundary returns the block END -- offset 240 reads 12:00, not 13:00 -- so a 24-hour "
        "/ elapsed predecessor of a lunch-boundary successor reads LF Mon 12:00, TF -2, critical "
        "(hand 13:00, +58) and Hard_File UIDs 264/274/260 read their late walls one hour before "
        "MS Project's stored instants"
    ),
)
def test_a0923_cpm_034_a_late_start_need_at_a_block_boundary_is_the_next_block_start() -> None:
    """A0923-CPM-034 (finder id F-META2-003) · CPM · T1 latent for the float; T3 for the committed
    late-instant walls.

    Claim (verifier's narrowed claim): at 13b13f38, P (UID 2, 242 min on a '24 Hours' task
    calendar, or 242 ELAPSED min) -FS0-> S (UID 3, 1,440 min, Standard 08-12/13-17), start Mon
    2026-01-05 08:00, S's late start at offset 240: ``compute_cpm`` gives P late finish Mon
    12:00, late start 07:58 (before the 08:00 project start), total float -2, free float -2 and
    ``is_critical`` True (hand: LF 13:00, TF = FF = +58); with P ending 11:00 and S driven by Q,
    TF = FF = +60 (hand +120). Mechanism: ``_succ_ls_wall``'s offset fallback
    (``engine/cpm.py:2947``) renders the need with ``_offset_to_wall(role="start")``, which at an
    INTERNAL block boundary returns the block END (240 -> 12:00, the finish role's answer)
    although its own docstring (cpm.py:1403) says "``role="start"``: where minute ``offset``
    BEGINS" and ``offset_to_start_datetime`` (cpm.py:681-682, ADR-0523) reads 240 as 13:00; the
    free-float twin is ``_succ_early_start_wall`` (cpm.py:3168). On the committed Hard_File and
    Hard_File_updated goldens the same rendering puts UIDs 264, 274 and 260's late start / late
    finish walls one hour before MS Project's stored values (12 values here; 24 with the two
    MPXJ conversions of the intake .mpp) -- a stored-instant parity record (``late_start_wall`` /
    ``late_finish_wall`` have no consumer outside cpm.py); no committed float moves.

    OUTSIDE this test (ADR-0524, "Deliberately NOT done", ``docs/adr/0524-a-late-start-is-a-
    start-role-instant-on-the-wall-path-too-r-69-closed.md:175-178``: "The 24 late finishes in
    the mirror class ... Applying the start form to `lf_w` breaks 52 already-exact late
    finishes"): UID 264's late finish is one of those 24, and the verifier showed the fix at the
    NEED (not ``lf_w``) moves it exact with 0 already-exact values moved away. Every OTHER member
    of that residual -- in the verifier's internal-block census Large_Test_File2 UID 5288 (the
    golden and 4 conversions) and the logic-reestablished save's UID 187 (1 conversion), plus the
    remaining later-form late finishes ADR-0524 counts -- is NOT asserted here; ADR-0524's
    decision stands for them.

    Authority: A1 -- MS Project's stored values, read with ElementTree from the committed goldens
    (both saves): UID 262 (Standard) ``<LateStart>2026-10-07T13:00:00``; its predecessor UID 264
    ``<LateFinish>2026-10-07T13:00:00`` and ``<LateStart>2026-10-06T05:00:00``; UID 274
    ``<LateStart>2026-10-05T21:00:00`` ``<LateFinish>2026-10-06T05:00:00``; milestone UID 260
    ``<LateStart>`` = ``<LateFinish>`` 2026-10-05T21:00:00 -- MS Project hands a predecessor
    that works the successor's lunch the successor's 13:00, not 12:00. Hand arithmetic (the
    same rule on the minimal network): S cannot work 12:00-13:00, so it starts Mon 13:00 (offset
    240); P (24-hour axis) may finish any time up to 13:00 without moving S -> LF_P = 13:00,
    TF_P = FF_P = 13:00 - 12:02 = +58 min of P's axis; P ending 11:00 with S's late start still
    13:00 -> +120. A2 -- ``engine/cpm.py:147-148`` "Total float may be negative (an imposed
    finish, or a violated cap / deadline / pin)" (none here); ``cpm.py:681-682``: "a start takes
    the LATER form, so 240 worked minutes reads 13:00 where the finish role reads 12:00".

    Independence: the stored instants were written by MS Project and are read here with
    ElementTree; the minimal network's values are hand arithmetic. Controls (preconditions): P
    on the PROJECT calendar (12:00 and 13:00 are one working minute of its axis -> TF 0) and a
    successor late start mid-block (Q 200 min -> 11:20 -> TF +20) are right today; the
    successor's own late start (262) is MS Project's 13:00.
    """
    p, _ = _a0923_cpm_034_solve("project", 242, None)
    if (p.total_float, p.is_critical) != (0, True):
        pytest.fail(f"precondition (control): P on the project calendar now reads {p}")
    p, _ = _a0923_cpm_034_solve("24h", 180, 200)
    if (p.total_float, p.free_float, p.is_critical) != (20, 20, False):
        pytest.fail(f"precondition (control): a mid-block successor need now gives {p}")

    wrong: dict[str, str] = {}
    lf_13 = dt.datetime(2026, 1, 5, 13, 0)
    for kind in ("24h", "elapsed"):
        p, s = _a0923_cpm_034_solve(kind, 242, None)
        if (s.early_start, p.early_finish_wall) != (240, dt.datetime(2026, 1, 5, 12, 2)):
            pytest.fail(f"precondition: {kind}: S no longer starts at 240 after P's 12:02: {p} {s}")
        got = (p.late_finish_wall, p.total_float, p.free_float, p.is_critical)
        if got != (lf_13, 58, 58, False):
            wrong[f"{kind} P 242 min (LF, TF, FF, critical)"] = f"{got} (hand 13:00, 58, 58, False)"
        p, _ = _a0923_cpm_034_solve(kind, 180, 240)
        got_q = (p.total_float, p.free_float, p.is_critical)
        if got_q != (120, 120, False):
            wrong[f"{kind} P 180 min + Q (TF, FF, critical)"] = f"{got_q} (hand 120, 120, False)"
    for name in ("Hard_File.mspdi.xml.gz", "Hard_File_updated.mspdi.xml.gz"):
        wrong.update(_a0923_cpm_034_golden(name))
    assert not wrong, (
        "a project-axis successor's late-start need at an internal block boundary is rendered at "
        f"the block END, not the next block's start: {wrong}"
    )


# --- A0923-CPM-035 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py, and on nothing else:
#   imports    re, xml.etree.ElementTree as ET, pytest, TestClient (fastapi.testclient),
#              SessionState / create_app (schedule_forensics.web.app)
#   constants  REPO, GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Inputs: the committed, non-CUI fixture tests/fixtures/mspdi/commercial_construction.xml (UID 5
# 'Substantial Completion' carries <Active>0</Active>; read in place) and the committed golden
# project2_5/Project5.mspdi.xml with one in-memory edit (UID 67 <Active>1 -> 0). No new fixture
# file.

_A0923_CPM_035_FIXTURE = REPO / "tests" / "fixtures" / "mspdi" / "commercial_construction.xml"
#: the target-taking trace routes that reach web/driving.py::_driving_data -- /api/driving
#: (web/app.py:2352 driving_json) and /export/{fmt}/path (web/app.py:4785 export_path) on both of
#: its bases (the stored default and ADR-0265's basis=resolve counterfactual re-solve)
_A0923_CPM_035_ROUTES = (
    "/api/driving/{key}?target={uid}",
    "/export/xlsx/path/{key}?target={uid}",
    "/export/docx/path/{key}?target={uid}",
    "/export/xlsx/path/{key}?target={uid}&basis=resolve&ignore_leveling=1",
)


def _a0923_cpm_035_flags(raw: bytes, uid: int) -> tuple[str, str]:
    """(Summary, Active) of one <Task>, read from the raw MSPDI with ElementTree ('' = absent)."""
    for el in ET.fromstring(raw).iter(NS + "Task"):
        if (el.findtext(NS + "UID") or "").strip() == str(uid):
            summary = (el.findtext(NS + "Summary") or "").strip()
            return summary, (el.findtext(NS + "Active") or "").strip()
    pytest.fail(f"precondition: UID {uid} is no longer a <Task> of the file")


def _a0923_cpm_035_deactivate(raw: bytes, uid: int) -> bytes:
    """``raw`` with ONLY that task's <Active>1</Active> flipped to 0 (everything else identical)."""
    text = raw.decode("utf-8-sig")
    block = re.search(rf"<Task>\s*<UID>{uid}</UID>.*?</Task>", text, re.S)
    if block is None or block.group(0).count("<Active>1</Active>") != 1:
        pytest.fail(f"precondition: UID {uid}'s <Task> no longer carries one <Active>1</Active>")
    edited = block.group(0).replace("<Active>1</Active>", "<Active>0</Active>")
    return text.replace(block.group(0), edited, 1).encode("utf-8")


def _a0923_cpm_035_session(name: str, raw: bytes) -> tuple[TestClient, str]:
    """One file loaded; (client, its session key). The client does NOT re-raise server exceptions,
    so a 500 is observed as the status code the browser receives (path.js:760-767 turns a non-JSON
    500 into the bare 'Trace failed.'), not as a KeyError inside the test."""
    st = SessionState()
    client = TestClient(create_app(st), raise_server_exceptions=False)
    up = client.post("/upload", files={"files": (name, raw, "text/xml")})
    if up.status_code != 200 or len(st.schedules) != 1:
        pytest.fail(
            f"precondition: upload of {name} answered {up.status_code} {list(st.schedules)}"
        )
    (key,) = list(st.schedules)
    return client, key


def _a0923_cpm_035_unrefused(client: TestClient, url: str, uid: int) -> str | None:
    """None when ``url`` refuses target ``uid`` BY NAME the way the route refuses a missing or a
    summary UID (web/driving.py:190-204 -> 200 with rows [] and a note naming the UID; export_path
    web/app.py:4838-4840 -> 422 with that note as the error); else what it answered instead."""
    resp = client.get(url)
    if resp.status_code >= 500:
        return f"{resp.status_code} {resp.text[:40]!r}"
    if not resp.headers.get("content-type", "").startswith("application/json"):
        return (
            f"{resp.status_code} {resp.headers.get('content-type', '')!r} (a trace, not a refusal)"
        )
    body = resp.json()
    if resp.status_code == 200 and body.get("rows"):
        return f"200 with {len(body['rows'])} traced rows (an inactive task is not in the network)"
    named = body.get("note") if resp.status_code == 200 else body.get("error")
    if not isinstance(named, str) or f"UID {uid}" not in named:
        return f"{resp.status_code} without a note naming UID {uid}: {body}"
    return None


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-035: a trace target that is an INACTIVE task (the committed "
        "commercial_construction.xml UID 5; Project5 with UID 67 made inactive) answers HTTP 500 "
        "on GET /api/driving/{file}?target= and GET /export/{xlsx,docx}/path/{file}?target= on "
        "both bases -- _driving_data (web/driving.py:190-204) refuses only a missing or a summary "
        "UID and passes an inactive one to compute_driving_slack, whose ancestors_of raises "
        "KeyError (engine/path_trace.py:37) -- where the route's own contract refuses by name "
        "(200 + note / 422) and /path's client shows only 'Trace failed.'"
    ),
)
def test_a0923_cpm_035_an_inactive_trace_target_is_refused_by_name_like_a_summary() -> None:
    """A0923-CPM-035 (finder id F-FAMB-001) · CPM · T4 (in the committed tree:
    tests/fixtures/mspdi/commercial_construction.xml UID 5; latent on the 44-file corpus).

    Claim (as VERIFIED by packet P2 on both instances): at 0b45eb28 a trace target that is an
    INACTIVE task -- the committed fixture commercial_construction.xml UID 5 'Substantial
    Completion' (``<Active>0</Active>``, a dated milestone), or the committed Project5 golden with
    UID 67 set ``<Active>0</Active>`` in memory -- answers HTTP 500 'Internal Server Error' on
    ``GET /api/driving/{file}?target=<uid>`` and on ``GET /export/{xlsx,docx}/path/{file}?target=``
    on both of export_path's bases (the stored default and ``basis=resolve&ignore_leveling=1``).
    Mechanism: ``_driving_data`` (``web/driving.py:190-204``) refuses a missing UID and a summary
    UID by name and passes everything else to ``compute_driving_slack`` (``:209``), whose
    ``ancestors_of`` raises ``KeyError(<uid>)`` at ``engine/path_trace.py:37`` because
    ``_scheduled_ids`` excludes inactive tasks (traceback web/app.py:2386 driving_json ->
    web/driving.py:209 -> engine/driving_slack.py:287 -> engine/path_trace.py:37). /path's client
    (``static/path.js:760-767``) turns the non-JSON 500 into the bare status 'Trace failed.', and
    the page's default whole-schedule grid offers the inactive UID as a clickable row
    (``/api/driving`` without a target lists rows [2, 3, 4, 5] on the fixture, measured), so the 500
    is one click from the page's default view. Sibling, recorded not asserted:
    ``/export/{fmt}/driving-tiers`` catches the same KeyError and answers 422 'schedule does not
    solve' (``web/app.py:5792``) -- a mislabelled refusal (the schedule solves; the target is
    outside the network).

    Authority: A2 -- the route's own refusal contract, ``src/schedule_forensics/web/driving.py:190-
    204``: ``if target not in by_id: return {... "rows": [], "note": f"UID {target} is not in this
    schedule."}`` / ``if by_id[target].is_summary: # summary rollups are not in the logic network --
    tracing one raised before`` ``return {... "note": f"UID {target} is a summary rollup -- pick one
    of its activities instead."}``, and ``web/app.py:4838-4840``: ``rows = data.get("rows") or []``
    / ``if not rows: return JSONResponse({"error": str(data.get("note", "no path"))},
    status_code=422)``; the engine's stated population, ``engine/path_trace.py:20-25``: "Excludes
    summary rollups AND inactive tasks (``is_active=False``), mirroring ``cpm._scheduled_tasks`` and
    ``driving_slack.date_basis`` (ADR-0128: MS Project / Acumen drop inactive tasks from the
    network)"; ``docs/adr/0128-exclude-inactive-tasks.md:22-23``: "Treat an inactive task
    (`is_active=False`) the same way a summary task is treated: a **real, schedulable activity is
    one that is neither a summary nor inactive**"; ``docs/adr/0463-...:55-57`` (Decision 6, REC-02):
    "the target's presence test is the network's membership (non-summary AND active) ...
    `_driving_path_findings` treats an inactive target like a summary (nothing to trace)" -- and
    that helper does so, ``engine/recommendations.py:589-592``: ``if task is None or
    task.is_summary or not task.is_active: # summary rollups and inactive tasks are not in the logic
    network (ADR-0128) -- nothing to trace; compute_driving_slack raises KeyError for either
    (REC-02, ADR-0463)``. (Read at 0b45eb28, 2026-09-29.) Deliberate-decision screen: no ADR keeps
    a 500 (ADR-0463 D6 requires the opposite; ``tests/web/test_inactive_target_scope.py`` pins the
    SESSION target set through POST /target, not the trace's ``?target=``); not HELD, not a
    duplicate (A0923-CPM-024 is the trend panel's zero-swallowing of the same KeyError on a
    different surface with a different fix).

    Control (precondition): on the same sessions a summary UID (1) and a missing UID (99999) are
    refused by name (200, rows [], a note naming the UID) and an ACTIVE UID (4; Project5's 67
    before the edit) traces (200 with rows; the xlsx export is a file) -- so a "fix" that refuses
    every target, or one that drops the existing refusals, fails here instead of passing. Census
    (finder + verifier, re-derived): 0 of the 44 corpus files carries an inactive non-summary task
    (latent there); 1 of the tracked MSPDI documents does (this fixture); 2 of 2 target-taking
    routes that reach ``_driving_data`` answer 500.
    """
    cc = _A0923_CPM_035_FIXTURE.read_bytes()
    if _a0923_cpm_035_flags(cc, 5) != ("", "0"):
        pytest.fail(
            "precondition: commercial_construction.xml UID 5 is no longer an inactive activity"
        )
    if _a0923_cpm_035_flags(cc, 1)[0] != "1":
        pytest.fail("precondition: commercial_construction.xml UID 1 is no longer a summary")
    if _a0923_cpm_035_flags(cc, 4) != ("", ""):
        pytest.fail("precondition: commercial_construction.xml UID 4 is no longer a plain activity")
    p5 = (GOLDEN / "project2_5" / "Project5.mspdi.xml").read_bytes()
    if _a0923_cpm_035_flags(p5, 67) != ("0", "1"):
        pytest.fail("precondition: Project5 UID 67 is no longer an active activity")
    p5_off = _a0923_cpm_035_deactivate(p5, 67)
    if _a0923_cpm_035_flags(p5_off, 67) != ("0", "0"):
        pytest.fail("precondition: the in-memory edit did not set Project5 UID 67 inactive")

    # -- controls: the named refusals exist and an active target traces (the routes must survive) -
    client, key = _a0923_cpm_035_session("commercial_construction.xml", cc)
    for uid in (1, 99999):
        for route in _A0923_CPM_035_ROUTES[:2]:
            why = _a0923_cpm_035_unrefused(client, route.format(key=key, uid=uid), uid)
            if why is not None:
                pytest.fail(
                    f"precondition: UID {uid} is no longer refused by name on {route}: {why}"
                )
    active = client.get(f"/api/driving/{key}?target=4")
    if active.status_code != 200 or not active.json().get("rows"):
        pytest.fail(f"precondition: the active UID 4 no longer traces ({active.status_code})")
    if client.get(f"/export/xlsx/path/{key}?target=4").status_code != 200:
        pytest.fail("precondition: the active UID 4 no longer exports")
    client_p5, key_p5 = _a0923_cpm_035_session("Project5.mspdi.xml", p5)
    if client_p5.get(f"/api/driving/{key_p5}?target=67").status_code != 200:
        pytest.fail("precondition: Project5's UID 67 no longer traces while active")

    # -- the claim: an inactive target is refused by name, never 500 ---------------------------
    wrong: dict[str, dict[str, str]] = {}
    client_off, key_off = _a0923_cpm_035_session("Project5_uid67_inactive.mspdi.xml", p5_off)
    for label, (c, k, uid) in (
        ("commercial_construction.xml UID 5 (committed, inactive)", (client, key, 5)),
        ("Project5 UID 67 made inactive", (client_off, key_off, 67)),
    ):
        for route in _A0923_CPM_035_ROUTES:
            why = _a0923_cpm_035_unrefused(c, route.format(key=k, uid=uid), uid)
            if why is not None:
                wrong.setdefault(label, {})[route.format(key=k, uid=uid)] = why

    assert not wrong, (
        "an INACTIVE trace target is not refused by name like a missing or a summary UID (200 with "
        f"rows [] + a note / 422 with the note); the routes answered: {wrong}"
    )


# --- A0923-CPM-036 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py, and on nothing else:
#   imports    io, re, zipfile, pytest, TestClient (fastapi.testclient),
#              SessionState / create_app (schedule_forensics.web.app)
#   fixture    the module-level autouse _air_gapped
# Input: inline MSPDI text (built below). No fixture file; nothing CUI.

#: The /evolution options banner's promise (src/schedule_forensics/web/evolution.py:193-196).
_A0923_CPM_036_BANNER = "comes from the re-solved pure-logic network, not the stored schedule"


def _a0923_cpm_036_mspdi(status: str, *, leveled: bool, flags: bool, limit: int = 0) -> str:
    """MS Project's Standard calendar (Mon-Fri 08:00-12:00 + 13:00-17:00), StartDate Mon
    2025-01-06 08:00, 480 working minutes a day, 0% complete. Tasks (DurationFormat 7 = days):
      A (UID 1) 5 d;   B (UID 2) 2 d;   C (UID 3) 1 d, FS0 after A and after B.
    ``leveled`` -- B carries a 4-working-day LevelingDelay (19200 tenths of a minute, format 7)
    and the stored dates MS Project levels it to: A 01-06..01-10, B 01-10..01-13, C 01-14;
    stored Critical A 0 / B 1 / C 1, TotalSlack (tenths) A 4800 (1 wd) / B 0 / C 0.
    Not ``leveled`` -- the same network with no delay: B 01-06..01-07, C 01-13; stored Critical
    A 1 / B 0 / C 1, TotalSlack A 0 / B 14400 (3 wd) / C 0.
    ``flags`` False omits every <Critical> / <TotalSlack> (the control: no stored basis).
    ``limit`` is MS Project's CriticalSlackLimit ("tasks are critical if slack is less than or
    equal to N days"): at 1, the leveled file's A (Total Slack 1 wd) is stored Critical 1 too."""
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

    def task(
        uid: int,
        days_: int,
        start: str,
        finish: str,
        crit: int,
        slack: int,
        *,
        delay: int | None = None,
        preds: tuple[int, ...] = (),
    ) -> str:
        stored = f"<Critical>{crit}</Critical><TotalSlack>{slack}</TotalSlack>" if flags else ""
        lvl = (
            f"<LevelingDelay>{delay}</LevelingDelay><LevelingDelayFormat>7</LevelingDelayFormat>"
            if delay is not None
            else ""
        )
        links = "".join(
            f"<PredecessorLink><PredecessorUID>{p}</PredecessorUID><Type>1</Type>"
            "<LinkLag>0</LinkLag><LagFormat>7</LagFormat></PredecessorLink>"
            for p in preds
        )
        return (
            f"<Task><UID>{uid}</UID><ID>{uid}</ID><Name>{'_ABC'[uid]}</Name><Active>1</Active>"
            f"<Duration>PT{8 * days_}H0M0S</Duration><DurationFormat>7</DurationFormat>"
            f"<PercentComplete>0</PercentComplete><Start>2025-01-{start}</Start>"
            f"<Finish>2025-01-{finish}</Finish>{lvl}{stored}{links}</Task>"
        )

    if leveled:
        b = task(2, 2, "10T08:00:00", "13T17:00:00", 1, 0, delay=19200)
        a_crit, a_slack, c_day = int(limit >= 1), 4800, "14"
    else:
        b = task(2, 2, "06T08:00:00", "07T17:00:00", 0, 14400)
        a_crit, a_slack, c_day = 1, 0, "13"
    return (
        '<Project xmlns="http://schemas.microsoft.com/project"><Name>a0923-cpm-036</Name>'
        "<Title>A0923-CPM-036</Title><ScheduleFromStart>1</ScheduleFromStart>"
        f"<StartDate>2025-01-06T08:00:00</StartDate><StatusDate>{status}</StatusDate>"
        f"<MinutesPerDay>480</MinutesPerDay><CriticalSlackLimit>{limit}</CriticalSlackLimit>"
        "<CalendarUID>1</CalendarUID>"
        "<Calendars><Calendar><UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>"
        f"<BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{days}</WeekDays></Calendar></Calendars>"
        "<Tasks>"
        + task(1, 5, "06T08:00:00", "10T17:00:00", a_crit, a_slack)
        + b
        + task(3, 1, f"{c_day}T08:00:00", f"{c_day}T17:00:00", 1, 0, preds=(1, 2))
        + "</Tasks></Project>"
    )


def _a0923_cpm_036_client(v2_leveled: bool, flags: bool = True, limit: int = 0) -> TestClient:
    """A two-version session: v1 leveled; v2 leveled too, or the same network un-leveled."""
    client = TestClient(create_app(SessionState()))
    files = (
        (
            "a0923_cpm_036_v1.xml",
            _a0923_cpm_036_mspdi("2025-01-03T17:00:00", leveled=True, flags=flags, limit=limit),
        ),
        (
            "a0923_cpm_036_v2.xml",
            _a0923_cpm_036_mspdi(
                "2025-01-06T08:00:00", leveled=v2_leveled, flags=flags, limit=limit
            ),
        ),
    )
    for name, text in files:
        up = client.post("/upload", files={"files": (name, text.encode(), "text/xml")})
        if up.status_code != 200:
            pytest.fail(f"precondition: upload of {name} answered {up.status_code}")
    return client


def _a0923_cpm_036_snapshots(client: TestClient, qs: str) -> list[dict[str, Any]]:
    """/api/evolution's per-version snapshots (the stepper's feed), oldest first."""
    got = client.get("/api/evolution" + qs)
    snaps = got.json().get("snapshots") if got.status_code == 200 else None
    if not isinstance(snaps, list) or len(snaps) != 2:
        pytest.fail(
            f"precondition: /api/evolution{qs} answered {got.status_code}: {got.text[:200]}"
        )
    return snaps


def _a0923_cpm_036_bars(snap: dict[str, Any]) -> dict[int, tuple[str, str]]:
    return {r["uid"]: (r["start"], r["finish"]) for r in snap["critical_rows"]}


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-036: under the /evolution counterfactual option ignore_leveling=1 the "
        "untargeted critical path (stepper, take, entered/left, exports) is still the source "
        "file's STORED Critical flag -- _optioned_versions clears dates and the leveling delay "
        "but never stored_is_critical -- so the hand leveled network shows [2, 3] where the "
        "re-solved network the banner names is [1, 3], and two versions that re-solve "
        "identically read '1 activity entered the path and 1 left'"
    ),
)
def test_a0923_cpm_036_ignore_leveling_draws_the_re_solved_networks_critical_path() -> None:
    """A0923-CPM-036 (finder id F-FAMB-002) · CPM · T1 (option-gated; in committed corpus: 24 of
    44 stored-value corpus files show a different untargeted set under ignore_leveling=1).

    Claim (verified scope): at 0b45eb28, with the counterfactual trace option "Ignore leveling
    delay" on and no focused UID, /evolution's critical path is the source file's stored Critical
    flag drawn at the re-solved dates. On the inline pair below (A 5 d; B 2 d with a 4-working-day
    LevelingDelay; C 1 d FS0 after A and B; stored Critical A 0 / B 1 / C 1), GET
    ``/api/evolution?ignore_leveling=1`` serves critical [2, 3] in both versions with B's bar at
    the re-solved 2025-01-06..01-07 and the re-solved finish 2025-01-13 -- a path member with 3
    working days of float on the network it is drawn on. Verifier's broadening (second arm): v1
    leveled, v2 the SAME network un-leveled in the file (stored Critical A 1 / B 0 / C 1); under
    the option both versions re-solve to one identical network, yet the stepper serves
    entered [1] / left [2], the /evolution take reads "1 activity entered the path and 1 left
    over 1 update, while the finish held" and ``/export/docx/evolution?ignore_leveling=1`` lists
    "entered 1 A slack_consumed" / "left 2 B gained_float" -- a path change between identical
    re-solved networks. Mechanism: ``_optioned_versions`` (``web/evolution.py:180-187``) clears
    start / finish / leveling_delay_minutes but never ``stored_is_critical`` /
    ``stored_total_float_minutes``; ``effective_critical_set`` (``engine/path_evolution.py:55-71``)
    -> ``is_effective_critical`` (``engine/metrics/_common.py:105-106``) returns the stored flag
    whenever it is present.

    Authority: A2 -- the page's own options banner, ``src/schedule_forensics/web/evolution.py:
    192-198`` verbatim: "Trace options active: ... — every date and path on this page (including
    the animated stepper and the Excel exports) comes from the re-solved pure-logic network, not
    the stored schedule (ADR-0265: one basis per page)."; the option tooltip (``:147``):
    "Counterfactual re-solve: incomplete tasks' stored dates are cleared and the CPM recomputed
    (a 0-day leveling delay)."; ADR-0265 decision 3 already hides the stored 'Critical' column
    under the options as a stored-network figure. A1 -- hand arithmetic on that stated transform
    (480 working minutes a day, Mon 2025-01-06 08:00 = 0, weekends off): A 0..2400 (Fri 01-10
    17:00); B 0..960 (Tue 01-07 17:00); C ES max(2400, 960) = 2400 -> Mon 01-13 08:00..17:00 =
    2880. Backward: LF(A) = LF(B) = LS(C) = 2400, so TF(A) = 0, TF(B) = 2400 - 960 = 1440 = 3 wd,
    TF(C) = 0: the re-solved critical set is {1, 3} in BOTH files of either pair (0 entered,
    0 left, finish held). The stored leveled schedule (B delayed 4 wd: 1920..2880, C 2880..3360)
    has {2, 3} with A TF 1 wd -- the flags the page shows. MPXJ 16.2.0 MicrosoftScheduler
    (verifier witness) agrees: delay zeroed, "A TS=0.0h critical=true; B ... TS=24.0h
    critical=false; C ... critical=true".

    Independence: the expected set is hand arithmetic on the transform the page itself states;
    no engine helper produces it. Controls in the same test (preconditions): the SAME network
    without stored flags gives [1, 3] under the option today (the re-solve is right; only the
    stored flag overrides it); and the default page (no option) keeps the stored basis
    (ADR-0150) on the same leveled pair saved with CriticalSlackLimit 1 -- stored Critical
    A 1 / B 1 / C 1, so [1, 2, 3] where float <= 0 alone would give [2, 3] -- so a "fix" that
    drops the stored flags everywhere fails that precondition instead of passing (measured: an
    in-memory stand-in reading float only everywhere is refused there by name).
    Deliberate-decision screen: ADR-0150 chose the stored basis for the DEFAULT page; no ADR
    keeps it under the options, whose banner says the opposite. Not HELD, not a duplicate
    (CPM-022 is family A /path, the opposite symptom). Randomized probes: none.
    """
    # Controls: the default page keeps the stored basis; the flagless network re-solves right.
    default = _a0923_cpm_036_snapshots(_a0923_cpm_036_client(v2_leveled=True, limit=1), "")
    if [s["critical"] for s in default] != [[1, 2, 3], [1, 2, 3]]:
        pytest.fail(f"precondition (control): the default stored basis now reads {default}")
    control = _a0923_cpm_036_client(v2_leveled=True)
    flagless = _a0923_cpm_036_snapshots(
        _a0923_cpm_036_client(v2_leveled=True, flags=False), "?ignore_leveling=1"
    )
    if [s["critical"] for s in flagless] != [[1, 3], [1, 3]]:
        pytest.fail(f"precondition (control): the flagless re-solve now reads {flagless}")
    page = control.get("/evolution?ignore_leveling=1")
    if page.status_code != 200 or _A0923_CPM_036_BANNER not in page.text:
        pytest.fail(
            f"precondition: /evolution?ignore_leveling=1 ({page.status_code}) lost its banner"
        )

    wrong: dict[str, str] = {}
    for snap in _a0923_cpm_036_snapshots(control, "?ignore_leveling=1"):
        bars = _a0923_cpm_036_bars(snap)
        if snap["project_finish"] != "2025-01-13" or bars.get(3) != ("2025-01-13", "2025-01-13"):
            pytest.fail(f"precondition: the option no longer re-solves the dates: {snap}")
        if snap["critical"] != [1, 3]:
            wrong[f"leveled pair {snap['label']} critical"] = (
                f"{snap['critical']} bars {bars} (hand [1, 3]: B has 3 wd of float)"
            )

    mixed = _a0923_cpm_036_client(v2_leveled=False)
    for snap in _a0923_cpm_036_snapshots(mixed, "?ignore_leveling=1"):
        if snap["project_finish"] != "2025-01-13":
            pytest.fail(f"precondition: the mixed pair no longer re-solves to 01-13: {snap}")
        if (snap["critical"], snap["entered"], snap["left"]) != ([1, 3], [], []):
            wrong[f"mixed pair {snap['label']} (critical, entered, left)"] = (
                f"{(snap['critical'], snap['entered'], snap['left'])} (hand ([1, 3], [], []))"
            )
    html = mixed.get("/evolution?ignore_leveling=1").text
    take = re.search(r"frames step the critical path[^<]*", html)
    if take is None:
        pytest.fail("precondition: /evolution no longer prints the stepper take")
    if "0 activities entered the path and 0 left" not in take.group(0):
        wrong["mixed pair /evolution take"] = take.group(0)
    doc = mixed.get("/export/docx/evolution?ignore_leveling=1")
    if doc.status_code != 200:
        pytest.fail(f"precondition: /export/docx/evolution answered {doc.status_code}")
    xml = zipfile.ZipFile(io.BytesIO(doc.content)).read("word/document.xml").decode("utf-8")
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", xml))
    if "leveling delay ignored" not in text or "Critical-path changes" not in text:
        pytest.fail("precondition: the export lost its applied scope or its changes table")
    moves = re.findall(r"a0923_cpm_036_v2\.xml (?:entered|left) \d+ \w+ \w+", text)
    if moves:
        wrong["mixed pair /export/docx/evolution changes"] = "; ".join(moves)
    assert not wrong, (
        "under ignore_leveling=1 the untargeted path is the stored Critical flag, not the "
        f"re-solved pure-logic network the options banner names (hand: [1, 3], 0 entered / 0 "
        f"left): {wrong}"
    )


# --- A0923-CPM-037 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py, and on nothing else:
#   imports    json, re, pytest, TestClient (fastapi.testclient),
#              SessionState / create_app (schedule_forensics.web.app)
#   constants  REPO (the checkout root)
#   fixture    the module-level autouse _air_gapped
# Inputs: inline MSPDI text (built below), and the committed, non-CUI synthetic fixture
# tests/fixtures/xer/commercial_construction.xer read in place (its second version is derived in
# memory by moving the PROJECT row's last_recalc_date). No fixture file; nothing CUI.

#: The /evolution options banner's promise (src/schedule_forensics/web/evolution.py:193-196).
_A0923_CPM_037_BANNER = "comes from the re-solved pure-logic network, not the stored schedule"
#: The Chapter-04 stability band's embedded dataset -- the only thing volatility.js draws the
#: band's four panels from (web/evolution.py, ``_stability_panels``).
_A0923_CPM_037_VOLDATA = re.compile(
    r'<script type="application/json" id=volData>(.*?)</script>', re.S
)
#: commercial_construction.xer's PROJECT row tail (plan_end_date, last_recalc_date).
_A0923_CPM_037_XER_RECALC = b"2025-03-31 17:00\t2025-02-01 17:00"


def _a0923_cpm_037_mspdi(network: str, status: str) -> str:
    """MS Project's Standard calendar (Mon-Fri 08:00-12:00 + 13:00-17:00), StartDate Mon
    2025-01-06 08:00, 480 working minutes a day, 0% complete, and NO stored <Critical> /
    <TotalSlack> anywhere (so the effective critical set is the engine's own float <= 0 and
    A0923-CPM-036's stored-flag override is out of play). Durations in days (DurationFormat 7):
      "leveled"      A (UID 1) 5 d; B (UID 2) 2 d with a 4-working-day LevelingDelay (19200
                     tenths of a minute, format 7); C (UID 3) 1 d, FS0 after A and after B.
                     Stored (leveled) dates: A 01-06..01-10, B 01-10..01-13, C 01-14.
      "constrained"  A (UID 1) 1 d; B (UID 2) 1 d, FS0 after A, Start-No-Earlier-Than Mon
                     2025-01-13 08:00; D (UID 4) 3 d; C (UID 3) 1 d, FS0 after B and after D.
                     Stored dates: A 01-06, B 01-13, D 01-06..01-08, C 01-14."""
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

    def task(uid: int, days_: int, start: str, finish: str, extra: str = "") -> str:
        return (
            f"<Task><UID>{uid}</UID><ID>{uid}</ID><Name>{'_ABCD'[uid]}</Name><Active>1</Active>"
            f"<Duration>PT{8 * days_}H0M0S</Duration><DurationFormat>7</DurationFormat>"
            f"<PercentComplete>0</PercentComplete><Start>2025-01-{start}</Start>"
            f"<Finish>2025-01-{finish}</Finish>{extra}</Task>"
        )

    def links(*preds: int) -> str:
        return "".join(
            f"<PredecessorLink><PredecessorUID>{p}</PredecessorUID><Type>1</Type>"
            "<LinkLag>0</LinkLag><LagFormat>7</LagFormat></PredecessorLink>"
            for p in preds
        )

    if network == "leveled":
        tasks = (
            task(1, 5, "06T08:00:00", "10T17:00:00")
            + task(
                2,
                2,
                "10T08:00:00",
                "13T17:00:00",
                "<LevelingDelay>19200</LevelingDelay><LevelingDelayFormat>7</LevelingDelayFormat>",
            )
            + task(3, 1, "14T08:00:00", "14T17:00:00", links(1, 2))
        )
    else:
        tasks = (
            task(1, 1, "06T08:00:00", "06T17:00:00")
            + task(
                2,
                1,
                "13T08:00:00",
                "13T17:00:00",
                "<ConstraintType>4</ConstraintType>"
                "<ConstraintDate>2025-01-13T08:00:00</ConstraintDate>" + links(1),
            )
            + task(3, 1, "14T08:00:00", "14T17:00:00", links(2, 4))
            + task(4, 3, "06T08:00:00", "08T17:00:00")
        )
    return (
        f'<Project xmlns="http://schemas.microsoft.com/project"><Name>a0923-cpm-037-{network}'
        f"</Name><Title>A0923-CPM-037 {network}</Title><ScheduleFromStart>1</ScheduleFromStart>"
        f"<StartDate>2025-01-06T08:00:00</StartDate><StatusDate>{status}</StatusDate>"
        "<MinutesPerDay>480</MinutesPerDay><HonorConstraints>1</HonorConstraints>"
        "<CalendarUID>1</CalendarUID>"
        "<Calendars><Calendar><UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>"
        f"<BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{days}</WeekDays></Calendar></Calendars>"
        f"<Tasks>{tasks}</Tasks></Project>"
    )


def _a0923_cpm_037_client(files: dict[str, bytes]) -> TestClient:
    """One session holding ``files`` as versions of one Project; every task flagless."""
    state = SessionState()
    client = TestClient(create_app(state))
    for name, data in files.items():
        kind = "text/xml" if name.endswith(".xml") else "application/octet-stream"
        up = client.post("/upload", files={"files": (name, data, kind)})
        if up.status_code != 200:
            pytest.fail(f"precondition: upload of {name} answered {up.status_code}")
    if len(state.schedules) != len(files):
        pytest.fail(f"precondition: the session holds {list(state.schedules)}")
    flagged = [
        (key, t.unique_id)
        for key, sch in state.schedules.items()
        for t in sch.tasks
        if t.stored_is_critical is not None
    ]
    if flagged:
        pytest.fail(f"precondition: these inputs must carry no stored Critical flag: {flagged}")
    return client


def _a0923_cpm_037_sets(client: TestClient, qs: str) -> tuple[list[list[int]], list[list[int]]]:
    """(the stability band's per-version membership from the served #volData, the stepper's
    per-version critical set from /api/evolution -- the feed the page's chart host forwards)."""
    page = client.get("/evolution" + qs)
    blob = _A0923_CPM_037_VOLDATA.search(page.text) if page.status_code == 200 else None
    if blob is None:
        pytest.fail(f"precondition: /evolution{qs} ({page.status_code}) embeds no #volData band")
    if (_A0923_CPM_037_BANNER in page.text) != bool(qs):
        pytest.fail(f"precondition: /evolution{qs}'s options banner is present iff options are on")
    vol = json.loads(blob.group(1))
    n_ver = len(vol["versions"])
    if n_ver != 2:
        pytest.fail(f"precondition: the band spans {n_ver} versions, not the 2 loaded")
    band = [sorted(t["uid"] for t in vol["tasks"] if t["member"][i]) for i in range(n_ver)]
    feed = client.get("/api/evolution" + qs)
    snaps = feed.json().get("snapshots") if feed.status_code == 200 else None
    if not isinstance(snaps, list) or len(snaps) != 2:
        pytest.fail(f"precondition: /api/evolution{qs} answered {feed.status_code}: {feed.text}")
    return band, [sorted(s["critical"]) for s in snaps]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-037: under the /evolution trace options the Chapter-04 stability band "
        "(panels 1-4, the embedded #volData) is drawn from the UN-optioned _solvable_versions() "
        "population (web/app.py:3898 -> :3914 never passes it through _optioned_versions), so on "
        "a flagless leveled pair under ignore_leveling=1 the band shows [2, 3] per version where "
        "the re-solved network the page's banner names -- and the page's own stepper -- is [1, 3]"
    ),
)
def test_a0923_cpm_037_the_stability_band_shares_the_pages_trace_option_basis() -> None:
    """A0923-CPM-037 (finder id F-FAMB-003) · CPM · T2 (latent on the MSPDI corpus -- masked by
    A0923-CPM-036; exposed on an XER-built pair).

    Claim (verified scope): at 0b45eb28, with a counterfactual trace option on, /evolution's
    Chapter-04 stability band (panels 1-4; the ``#volData`` blob volatility.js draws them from)
    is computed on the UN-optioned network, beside a stepper and pair panels on the re-solved
    one. On the inline leveled pair below (no stored flags), ``GET /evolution?ignore_leveling=1``
    embeds band membership [[2, 3], [2, 3]] while ``/api/evolution?ignore_leveling=1`` (the feed
    the page's chart host forwards) serves [[1, 3], [1, 3]] = hand. Verifier's broadening: the
    same split under ``ignore_constraints=1`` on the inline constrained pair (band [[2, 3],
    [2, 3]], stepper [[3, 4], [3, 4]] = hand), and on a two-version pair built from the committed
    ``tests/fixtures/xer/commercial_construction.xer`` (band 2 members per version, stepper 1).
    Verifier's narrowing (exposure): on files carrying MS Project's stored Critical flag (every
    committed MSPDI, 0 of 44 corpus files differ) the band and stepper agree ONLY because the
    stepper reads the stored flag too (A0923-CPM-036), so this test uses flagless inputs.
    Mechanism: ``web/app.py:3875-3880`` passes only the PAIR through ``_optioned_versions``;
    ``:3898`` ``all_schedules, all_cpms, _all_skipped = _solvable_versions()`` reaches
    ``_stability_panels(all_schedules, all_cpms)`` (``:3914``) un-optioned.

    Authority: A2 -- the page's own options banner, ``src/schedule_forensics/web/evolution.py:
    193-196`` verbatim: "Trace options active: ... — every date and path on this page (including
    the animated stepper and the Excel exports) comes from the re-solved pure-logic network, not
    the stored schedule (ADR-0265: one basis per page)."; ``docs/adr/0265-family-b-basis-
    unification.md:1`` "family-B basis unification: one basis per counterfactual page". A1 --
    hand arithmetic (480 working minutes a day, Mon 2025-01-06 08:00 = 0, weekends off).
    Leveled, re-solved (delay 0, dates cleared -- the transform ``_optioned_versions`` states):
    A 0..2400, B 0..960, C ES max(2400, 960) = 2400..2880; LF(A) = LF(B) = 2400 -> TF A 0,
    B 1440 (3 wd), C 0 -> {1, 3}; un-optioned (the 4 wd delay honoured, ADR-0474): B 1920..2880,
    C 2880..3360, TF A 480 -> {2, 3}. Constrained, re-solved (SNET stripped): A 0..480, B
    480..960, D 0..1440, C 1440..1920 -> TF A = B = 480, D = C = 0 -> {3, 4}; un-optioned (B
    held to 2400): C 2880..3360, TF B 0, D 1440, A 1920 -> {2, 3}.

    Independence: the two inline arms' expected sets are hand arithmetic on the transform the
    page itself states; no engine helper produces them. The XER arm has no hand oracle -- its
    expectation is the page's own re-solved stepper (A2: one basis per page), an exposure
    witness on a committed input, not an independent value. Controls (preconditions): with no
    option the band and the stepper agree on every pair (the band is right for the un-optioned
    network, and a "fix" that re-solves the band always is refused there by name); under the
    options the stepper already serves the hand sets; every input is flagless. NOT asserted
    (recorded sibling, same basis gap): the band tiles' EXCEL export (``data-export=
    "/export/xlsx/volatility"``) is the /volatility dataset and carries no option.
    Deliberate-decision screen: ADR-0427 / ADR-0371 / ADR-0420 make the band a different
    POPULATION (all versions vs the pair) on purpose; none names a different BASIS under the
    options. Not HELD, not a duplicate (A0923-CPM-036 is the stored flag inside the optioned
    pair; its fix leaves this band un-optioned). Randomized probes: none.
    """
    xer = (REPO / "tests" / "fixtures" / "xer" / "commercial_construction.xer").read_bytes()
    if xer.count(_A0923_CPM_037_XER_RECALC) != 1:
        pytest.fail("precondition: commercial_construction.xer's PROJECT row is not as recorded")
    pairs: dict[str, tuple[TestClient, str, list[list[int]] | None]] = {
        "leveled": (
            _a0923_cpm_037_client(
                {
                    f"a0923_cpm_037_lev_v{v}.xml": _a0923_cpm_037_mspdi("leveled", s).encode()
                    for v, s in ((1, "2025-01-03T17:00:00"), (2, "2025-01-06T08:00:00"))
                }
            ),
            "?ignore_leveling=1",
            [[1, 3], [1, 3]],
        ),
        "constrained": (
            _a0923_cpm_037_client(
                {
                    f"a0923_cpm_037_con_v{v}.xml": _a0923_cpm_037_mspdi("constrained", s).encode()
                    for v, s in ((1, "2025-01-03T17:00:00"), (2, "2025-01-06T08:00:00"))
                }
            ),
            "?ignore_constraints=1",
            [[3, 4], [3, 4]],
        ),
        "commercial_construction.xer": (
            _a0923_cpm_037_client(
                {
                    "a0923_cpm_037_cc_v1.xer": xer,
                    "a0923_cpm_037_cc_v2.xer": xer.replace(
                        _A0923_CPM_037_XER_RECALC, b"2025-03-31 17:00\t2025-02-08 17:00"
                    ),
                }
            ),
            "?ignore_constraints=1",
            None,
        ),
    }

    wrong: dict[str, str] = {}
    for name, (client, qs, hand) in pairs.items():
        band0, stepper0 = _a0923_cpm_037_sets(client, "")
        if band0 != stepper0 or not all(band0):
            pytest.fail(f"precondition (control): {name} with no option: band {band0}, {stepper0}")
        if hand is not None and band0 != [[2, 3], [2, 3]]:
            pytest.fail(
                f"precondition (control): {name}'s un-optioned band is {band0} (hand [2, 3])"
            )
        band, stepper = _a0923_cpm_037_sets(client, qs)
        if stepper != (hand or stepper) or stepper == stepper0:
            pytest.fail(
                f"precondition: {name}{qs}'s stepper is {stepper} (hand {hand}; no option "
                f"{stepper0}) -- the option no longer re-solves this pair's path as recorded"
            )
        if band != stepper:
            wrong[f"{name}{qs}"] = f"band {band}, stepper {stepper} (hand {hand or 'n/a'})"
    assert not wrong, (
        "under a trace option the stability band is not on the re-solved basis the page's banner "
        f"names (the band is the un-optioned network; the stepper is re-solved): {wrong}"
    )


# --- A0923-CPM-038 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    gzip, json, re, xml.etree.ElementTree as ET, typing.Any, pytest,
#              fastapi.testclient.TestClient, compute_cpm (schedule_forensics.engine.cpm),
#              compute_driving_slack (schedule_forensics.engine.driving_slack),
#              parse_mspdi_text (schedule_forensics.importers.mspdi),
#              ConstraintType (schedule_forensics.model.task),
#              SessionState and create_app (schedule_forensics.web.app)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Inputs: inline MSPDI text (built below) and the committed, non-CUI golden
# tests/fixtures/golden/fuse_hardfile/Hard_File.mspdi.xml.gz read in place. No new fixture file.

#: The family-B "Ignore constraints" tooltip (web/driving.py:832 = web/evolution.py:145), the
#: promise this test holds the page to, required verbatim as a precondition.
_A0923_CPM_038_PROMISE = (
    "Counterfactual re-solve: every version recomputed with all date constraints removed (pure "
    "logic). Diverges from the stored schedule"
)
#: The options banner (web/evolution.py:192-199), required verbatim under the option.
_A0923_CPM_038_BANNER = "comes from the re-solved pure-logic network, not the stored schedule"
#: Hand arithmetic (docstring): {UID: (tier, driving slack in working days)} to the target C.
_A0923_CPM_038_STORED = {2: ("driving", 0.0), 4: ("secondary", 3.0), 1: ("secondary", 4.0)}
_A0923_CPM_038_RESOLVED = {4: ("driving", 0.0), 1: ("secondary", 1.0), 2: ("secondary", 1.0)}


def _a0923_cpm_038_mspdi(status: str, *, dated: bool = True) -> str:
    """MS Project's Standard calendar (Mon-Fri 08:00-12:00 + 13:00-17:00), StartDate Mon
    2025-01-06 08:00, 480 minutes a day. A (UID 1) 1 d; B (UID 2) 1 d FS0 after A, Start No
    Earlier Than Mon 2025-01-13 08:00 (ConstraintType 4); D (UID 4) 3 d; C (UID 3) 1 d FS0 after B
    and after D. With ``dated`` every task carries the Start / Finish / Critical / TotalSlack MS
    Project stores for this network (the SNET binds: B 01-13, C 01-14; TotalSlack in tenths of a
    minute, A 4 d = 19200, D 3 d = 14400); without it the file carries logic and the pin only.
    Nothing is complete; the two versions differ only in ``status`` (the StatusDate)."""
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

    def task(
        uid: int, name: str, days_: int, start: str, finish: str, slack_d: int, *pred: int
    ) -> str:
        stored = (
            f"<Start>2025-01-{start}</Start><Finish>2025-01-{finish}</Finish>"
            f"<Critical>{int(slack_d == 0)}</Critical><TotalSlack>{slack_d * 4800}</TotalSlack>"
            if dated
            else ""
        )
        pin = (
            "<ConstraintType>4</ConstraintType><ConstraintDate>2025-01-13T08:00:00</ConstraintDate>"
            if uid == 2
            else "<ConstraintType>0</ConstraintType>"
        )
        links = "".join(
            f"<PredecessorLink><PredecessorUID>{p}</PredecessorUID><Type>1</Type>"
            "<LinkLag>0</LinkLag><LagFormat>7</LagFormat></PredecessorLink>"
            for p in pred
        )
        return (
            f"<Task><UID>{uid}</UID><ID>{uid}</ID><Name>{name}</Name><Active>1</Active>"
            f"<Duration>PT{8 * days_}H0M0S</Duration><DurationFormat>7</DurationFormat>"
            f"{stored}{pin}{links}</Task>"
        )

    return (
        '<Project xmlns="http://schemas.microsoft.com/project"><Name>a0923-cpm-038</Name>'
        "<Title>a0923-cpm-038</Title><ScheduleFromStart>1</ScheduleFromStart>"
        f"<StartDate>2025-01-06T08:00:00</StartDate><StatusDate>{status}</StatusDate>"
        "<MinutesPerDay>480</MinutesPerDay><CalendarUID>1</CalendarUID>"
        "<HonorConstraints>1</HonorConstraints><Calendars><Calendar><UID>1</UID><Name>Standard"
        "</Name><IsBaseCalendar>1</IsBaseCalendar><BaseCalendarUID>-1</BaseCalendarUID>"
        f"<WeekDays>{days}</WeekDays></Calendar></Calendars><Tasks>"
        + task(1, "A", 1, "06T08:00:00", "06T17:00:00", 4)
        + task(2, "B", 1, "13T08:00:00", "13T17:00:00", 0, 1)
        + task(4, "D", 3, "06T08:00:00", "08T17:00:00", 3)
        + task(3, "C", 1, "14T08:00:00", "14T17:00:00", 0, 2, 4)
        + "</Tasks></Project>"
    )


def _a0923_cpm_038_client(files: dict[str, str | bytes]) -> TestClient:
    """One session holding ``files`` (name -> MSPDI text or bytes), every upload accepted."""
    state = SessionState()
    client = TestClient(create_app(state))
    for name, body in files.items():
        data = body.encode() if isinstance(body, str) else body
        up = client.post("/upload", files={"files": (name, data, "text/xml")})
        if up.status_code != 200:
            pytest.fail(f"precondition: uploading {name} answered {up.status_code}")
    if len(state.schedules) != len(files):
        pytest.fail(f"precondition: the session holds {list(state.schedules)}")
    return client


def _a0923_cpm_038_tiers(client: TestClient, query: str) -> tuple[dict[int, Any], str]:
    """({UID: (tier, slack d)} of the /driving-path tiers panel's embedded rows, page html)."""
    page = client.get(f"/driving-path?{query}")
    if page.status_code != 200:
        pytest.fail(f"precondition: /driving-path?{query} answered {page.status_code}")
    blob = re.search(r"id=drivingTiersData>(.*?)</script>", page.text, re.S)
    if blob is None:
        pytest.fail(f"precondition: /driving-path?{query} embeds no drivingTiersData")
    rows = json.loads(blob.group(1).replace("\\u003c", "<"))["rows"]
    return {int(r["uid"]): (r["tier"], float(r["slack"])) for r in rows}, page.text


def _a0923_cpm_038_evolution(client: TestClient, query: str) -> list[tuple[list[int], str]]:
    """[(sorted focus-path UIDs, project finish)] per version of the /evolution stepper feed."""
    got = client.get(f"/api/evolution?{query}")
    if got.status_code != 200:
        pytest.fail(f"precondition: /api/evolution?{query} answered {got.status_code}")
    return [(sorted(s["critical"]), s["project_finish"]) for s in got.json()["snapshots"]]


def _a0923_cpm_038_driving(raw: bytes, target: int, *, stated: bool) -> set[int]:
    """The engine's DRIVING tier to ``target`` (target excluded) on the file as stored, or --
    ``stated`` -- under the transform the tooltip and ADR-0251:40-41 state: every constraint
    removed and incomplete tasks' stored dates cleared, then re-solved. The transform is applied
    here by hand, not through ``_optioned_versions`` or ``strip_constraints``."""
    sch = parse_mspdi_text(raw.decode("utf-8-sig", errors="replace"))
    if stated:
        cleared = {
            "constraint_type": ConstraintType.ASAP,
            "constraint_date": None,
            "start": None,
            "finish": None,
        }
        free = tuple(t if t.is_complete else t.model_copy(update=cleared) for t in sch.tasks)
        sch = sch.model_copy(update={"tasks": free})
    rows = compute_driving_slack(sch, target, cpm_result=compute_cpm(sch))
    return {u for u, r in rows.items() if r.on_driving_path and u != target}


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-038: family B's 'Ignore constraints' alone clears no stored dates "
        "(web/evolution.py:180-187 clears them only under ignore_leveling), so on a fully-dated "
        "file /driving-path's tiers and /evolution's focus path stay the stored schedule's "
        "(B driving, D 3.0 d, A 4.0 d; path [2, 3]; Hard_File target 411 unchanged) under a "
        "tooltip and banner promising the constraint-free re-solve (D driving, A 1 d, B 1 d; "
        "path [3, 4])"
    ),
)
def test_a0923_cpm_038_ignore_constraints_alone_traces_the_constraint_free_re_solve() -> None:
    """A0923-CPM-038 (finder id F-FAMB-004) · CPM · T1 (option-gated; in the committed corpus:
    inert on 44 of 44 corpus files, Hard_File target 411 witnessed here).

    Claim (as verified by P1 and P6, P6's narrowing adopted): at 0b45eb28 the family-B trace
    option "Ignore constraints", ticked ALONE, is a no-op on a fully-dated file. On the inline
    two-version MSPDI below (binding SNET on B), ``/driving-path?target=3&ignore_constraints=1``
    serves the stored-schedule tiers -- driving {B}, D 3.0 d, A 4.0 d, the tier rows equal to the
    no-option page's -- under the options banner, and ``/api/evolution?target=3&
    ignore_constraints=1`` serves the stored focus path [2, 3] beside the re-solved finish
    2025-01-09 that only D can drive. Mechanism: ``_optioned_versions`` (web/evolution.py:180-187)
    strips the constraints but clears incomplete tasks' stored dates only ``if ignore_leveling``,
    and every family-B consumer (``compute_driving_slack`` via the stored-date-first
    ``date_basis``, engine/driving_slack.py:122-151; the evolution focus path) reads stored dates
    first, so the strip reaches only undated tasks. Same on the committed Hard_File golden (target
    411: the tier rows are the no-option rows; P6), on the tiers Excel export (P1) and on every
    ``_optioned_versions`` caller (six family-B routes).

    Authority: A2 -- the product's own served promise, web/driving.py:832 and
    web/evolution.py:145 (the "Ignore constraints" title), verbatim: "Counterfactual re-solve:
    every version recomputed with all date constraints removed (pure logic). Diverges from the
    stored schedule — and from SSI's same-named option, which keeps reporting on stored dates
    (ADR-0251)"; the banner web/evolution.py:192-199: "Trace options active: constraints ignored
    — every date and path on this page (including the animated stepper and the Excel exports)
    comes from the re-solved pure-logic network, not the stored schedule (ADR-0265: one basis per
    page)"; docs/adr/0251-ignore-toggles-copy-truth-and-page-family-alignment.md:40-41 (family B)
    "`_optioned_versions` strips constraints and **clears incomplete tasks' stored dates**, then
    re-runs CPM — a genuine re-solve". A1 -- hand arithmetic, 480 working minutes a day, Mon
    2025-01-06 08:00 start, weekends off. Stored (the SNET binds): A 01-06, B 01-13, D 01-06..01-08,
    C 01-14; driving slack to C: B 0; D = Thu 01-09, Fri 01-10, Mon 01-13 = 3 wd; A = Tue 01-07 ..
    Fri 01-10 = 4 wd (+ B's 0). Constraints removed: A 01-06, B 01-07, D 01-06..01-08, C =
    max(B, D) + 1 = 01-09; D 0; B = Wed 01-08 = 1 wd; A = 0 + B's 1 = 1 wd; driving {D}; the
    focus path to C is {C, D} = [3, 4].

    Independence: the promise is the served copy; the expected tiers are hand arithmetic on the
    input written here; the committed witness is read with ElementTree (its constraints) and its
    stated re-solve is built in this test by hand (constraints to ASAP, incomplete dates cleared),
    not through ``_optioned_versions`` or ``strip_constraints``. Controls (preconditions): the
    no-option page serves the stored hand tiers; BOTH options together (the branch that does
    clear the dates) serve exactly the constraint-free hand tiers and path, so the engine can
    reach them with the stored Critical flags present; the same network with no stored dates
    serves them under Ignore constraints alone. Not HELD, not a duplicate: no ADR decides the
    option should be inert on a dated file (ADR-0155 / 0174 / 0251 / 0265); A0923-CPM-022 is
    family A (/path) moving where it must not -- the opposite symptom on another transform.
    """
    names = ("a0923_cpm_038_v1.xml", "a0923_cpm_038_v2.xml")
    client = _a0923_cpm_038_client(
        {
            names[0]: _a0923_cpm_038_mspdi("2025-01-06T08:00:00"),
            names[1]: _a0923_cpm_038_mspdi("2025-01-06T12:00:00"),
        }
    )
    on_v1 = f"target=3&file={names[0]}"
    stored, page = _a0923_cpm_038_tiers(client, on_v1)
    title = re.search(r'name=ignore_constraints value=1[^>]*?title="([^"]*)"', page)
    if title is None or _A0923_CPM_038_PROMISE not in title.group(1):
        pytest.fail("precondition: the Ignore constraints tooltip no longer promises the re-solve")
    if stored != _A0923_CPM_038_STORED:
        pytest.fail(f"precondition: the no-option tiers are {stored}, not the stored hand tiers")
    both, _ = _a0923_cpm_038_tiers(client, on_v1 + "&ignore_constraints=1&ignore_leveling=1")
    if both != _A0923_CPM_038_RESOLVED:
        pytest.fail(f"precondition (control): both options now serve {both}")
    if _a0923_cpm_038_evolution(client, "target=3") != [([2, 3], "2025-01-14")] * 2:
        pytest.fail("precondition: the no-option /evolution focus path is not the stored [2, 3]")
    both_evo = _a0923_cpm_038_evolution(client, "target=3&ignore_constraints=1&ignore_leveling=1")
    if both_evo != [([3, 4], "2025-01-09")] * 2:
        pytest.fail(f"precondition (control): both options now give the /evolution {both_evo}")
    undated = _a0923_cpm_038_client(
        {"u.xml": _a0923_cpm_038_mspdi("2025-01-06T08:00:00", dated=False)}
    )
    if _a0923_cpm_038_tiers(undated, "target=3&ignore_constraints=1")[0] != _A0923_CPM_038_RESOLVED:
        pytest.fail("precondition (control): the option no longer re-solves an UNDATED network")

    wrong: dict[str, object] = {}
    tiers, page = _a0923_cpm_038_tiers(client, on_v1 + "&ignore_constraints=1")
    if _A0923_CPM_038_BANNER not in page:
        pytest.fail("precondition: the options banner no longer promises the re-solved network")
    if tiers != _A0923_CPM_038_RESOLVED:
        wrong["/driving-path tiers"] = tiers
    evo = _a0923_cpm_038_evolution(client, "target=3&ignore_constraints=1")
    if [path for path, _ in evo] != [[3, 4], [3, 4]]:
        wrong["/api/evolution (focus path, finish)"] = evo

    # -- the committed witness: Hard_File, target 411 (verifier P6) ------------------------------
    raw = gzip.decompress((GOLDEN / "fuse_hardfile" / "Hard_File.mspdi.xml.gz").read_bytes())
    pins = {
        (el.findtext(NS + "UID") or "").strip()
        for el in ET.fromstring(raw).iter(NS + "Task")
        if (el.findtext(NS + "ConstraintType") or "0").strip() not in ("", "0")
        and (el.findtext(NS + "PercentComplete") or "").strip() != "100"
        and (el.findtext(NS + "Summary") or "").strip() != "1"
    }
    if not {"147", "189"} <= pins:
        pytest.fail(f"precondition: Hard_File's incomplete constrained activities are {pins}")
    stored_driving = _a0923_cpm_038_driving(raw, 411, stated=False)
    stated_driving = _a0923_cpm_038_driving(raw, 411, stated=True)
    if stated_driving == stored_driving:
        pytest.fail(
            f"precondition: the stated re-solve no longer moves 411's tier {stored_driving}"
        )
    hard = _a0923_cpm_038_client({"Hard_File.mspdi.xml": raw})
    base = _a0923_cpm_038_tiers(hard, "target=411")[0]
    optioned = _a0923_cpm_038_tiers(hard, "target=411&ignore_constraints=1")[0]
    if optioned == base:
        wrong["Hard_File target 411"] = (
            f"all {len(base)} tier rows equal the no-option rows (driving "
            f"{sorted(u for u, (tier, _) in base.items() if tier == 'driving')}) where the "
            f"stated re-solve drives {sorted(stated_driving)}"
        )
    assert not wrong, (
        "'Ignore constraints' alone serves the STORED schedule under a tooltip and banner that "
        f"promise the constraint-free re-solve (hand: tiers {_A0923_CPM_038_RESOLVED}, focus "
        f"path [3, 4]): {wrong}"
    )


# --- A0923-CPM-039 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    datetime as dt, xml.etree.ElementTree as ET, pytest, TestClient, quote,
#              SessionState / create_app (schedule_forensics.web.app); GOLDEN, NS
#   fixture    the module-level autouse _air_gapped
# Inputs: inline MSPDI text built below and the committed goldens tests/fixtures/golden/evm/
# EVM2.mspdi.xml and tests/fixtures/golden/project2_5/Project5.mspdi.xml (read in place, raw bytes
# also read with ElementTree independently of the importer). No fixture file; nothing CUI.

_A0923_CPM_039_EVM2 = GOLDEN / "evm" / "EVM2.mspdi.xml"
_A0923_CPM_039_PROJECT5 = GOLDEN / "project2_5" / "Project5.mspdi.xml"
#: EVM2, focus 29: the ten on-path activities, in logic order, one serial driving chain.
_A0923_CPM_039_EVM2_CHAIN = [17, 18, 19, 20, 22, 23, 25, 26, 28, 29]
#: Project5, focus 67 (the target tests/web/test_path_options.py pins): the driving path decomposed
#: at its two genuine forks / joins only -- 58 -> {60, 61} -> 62 and 63 -> {65, 66} -> 67; the
#: non-driving 48 -> 55 link (42 working days of free float) forks nothing.
_A0923_CPM_039_P5_BRANCHES = [
    [35, 38, 39, 42, 44, 48, 49, 51, 52, 53, 55, 57, 58],
    [60],
    [61],
    [62, 63],
    [65],
    [66],
    [67],
]


def _a0923_cpm_039_mspdi(shape: str) -> str:
    """A hand network on MS Project's Standard 480-minute day (start Mon 2025-01-06 08:00), every
    task carrying the Start / Finish MS Project schedules it at, every link FS0. ``serial``: A (2 d)
    -> B (2 d) -> C (2 d) -- one driving chain [1, 2, 3]. ``redundant``: the same plus A -> C, a
    link with 2 working days of free float (A finishes Tue 01-07 17:00, C starts Fri 01-10 08:00)
    that drives nothing. ``diamond``: A -> {B, C} -> D, both legs 0 d -- a genuine fork and join.
    ``subday``: ``redundant`` with A shortened to 1.5 d (finishes Tue 01-07 12:00), so A -> B has
    half a working day of free float (0 whole days: still a driving link on SSI's day axis) and A
    -> C two and a half (2 whole days: non-driving)."""
    rows: tuple[tuple[int, str, str, str, str, tuple[int, ...]], ...]
    if shape == "diamond":
        rows = (
            (1, "A", "2025-01-06T08:00:00", "2025-01-07T17:00:00", "16", ()),
            (2, "B", "2025-01-08T08:00:00", "2025-01-09T17:00:00", "16", (1,)),
            (3, "C", "2025-01-08T08:00:00", "2025-01-09T17:00:00", "16", (1,)),
            (4, "D", "2025-01-10T08:00:00", "2025-01-13T17:00:00", "16", (2, 3)),
        )
    else:
        a_finish, a_hours = (
            ("2025-01-07T12:00:00", "12") if shape == "subday" else ("2025-01-07T17:00:00", "16")
        )
        rows = (
            (1, "A", "2025-01-06T08:00:00", a_finish, a_hours, ()),
            (2, "B", "2025-01-08T08:00:00", "2025-01-09T17:00:00", "16", (1,)),
            (
                3,
                "C",
                "2025-01-10T08:00:00",
                "2025-01-13T17:00:00",
                "16",
                (2,) if shape == "serial" else (2, 1),
            ),
        )
    tasks = "".join(
        f"<Task><UID>{uid}</UID><ID>{uid}</ID><Name>{name}</Name><Active>1</Active>"
        f"<Duration>PT{hours}H0M0S</Duration><Start>{start}</Start><Finish>{finish}</Finish>"
        + "".join(
            f"<PredecessorLink><PredecessorUID>{p}</PredecessorUID><Type>1</Type>"
            "<LinkLag>0</LinkLag><LagFormat>7</LagFormat></PredecessorLink>"
            for p in preds
        )
        + "</Task>"
        for uid, name, start, finish, hours, preds in rows
    )
    return (
        '<Project xmlns="http://schemas.microsoft.com/project"><Title>R</Title>'
        "<StartDate>2025-01-06T08:00:00</StartDate><MinutesPerDay>480</MinutesPerDay>"
        f"<Tasks>{tasks}</Tasks></Project>"
    )


def _a0923_cpm_039_served(
    name: str, data: bytes, target: int
) -> tuple[list[list[int]], dict[int, tuple[int, bool]]]:
    """Upload ``data`` to the real app and read ``/api/driving/<key>?target=N``: the served
    ``parallel_paths`` branches (UID lists, in served order) and, per traced row, (driving slack
    days, on the driving path)."""
    state = SessionState()
    client = TestClient(create_app(state))
    up = client.post("/upload", files={"files": (name, data, "text/xml")})
    if up.status_code not in (200, 303) or len(state.schedules) != 1:
        pytest.fail(f"precondition: upload of {name} answered {up.status_code}")
    key = quote(next(iter(state.schedules)), safe="")
    resp = client.get(f"/api/driving/{key}", params={"target": target})
    if resp.status_code != 200:
        pytest.fail(f"precondition: /api/driving/{key}?target={target} answered {resp.status_code}")
    payload = resp.json()
    if "parallel_paths" not in payload or not payload.get("rows"):
        pytest.fail(f"precondition: the payload carries no parallel_paths / rows: {payload}")
    rows = {
        int(r["unique_id"]): (int(r["driving_slack_days"]), bool(r["on_driving_path"]))
        for r in payload["rows"]
    }
    return [[int(u) for u in p["uids"]] for p in payload["parallel_paths"]], rows


def _a0923_cpm_039_raw_links(raw: bytes, uids: list[int]) -> dict[tuple[int, int], int]:
    """MS Project's own stored values, read from the raw MSPDI with ElementTree (not the importer):
    every link between two of ``uids`` -> the weekdays strictly between the predecessor's stored
    Finish date and the successor's stored Start date (Mon-Fri; both goldens declare one Standard
    project calendar with no exceptions and 480 minutes a day). Every such link must be FS with
    lag 0, or the precondition fails."""
    root = ET.fromstring(raw)
    tasks = {int(t.findtext(NS + "UID") or -1): t for t in root.iter(NS + "Task")}
    out: dict[tuple[int, int], int] = {}
    for uid in uids:
        for link in tasks[uid].findall(NS + "PredecessorLink"):
            pred = int(link.findtext(NS + "PredecessorUID") or -1)
            if pred not in uids:
                continue
            kind, lag = link.findtext(NS + "Type"), link.findtext(NS + "LinkLag")
            if (kind, lag) != ("1", "0"):
                pytest.fail(f"precondition: link {pred}->{uid} is not FS0 (Type {kind}, lag {lag})")
            finish = dt.datetime.fromisoformat(tasks[pred].findtext(NS + "Finish") or "")
            start = dt.datetime.fromisoformat(tasks[uid].findtext(NS + "Start") or "")
            day, between = finish.date() + dt.timedelta(days=1), 0
            while day < start.date():
                between += day.weekday() < 5
                day += dt.timedelta(days=1)
            out[(pred, uid)] = between
    return out


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-039: the 'Separate parallel paths' decomposition (web/driving.py:345-348) joins "
        "two on-path tasks through ANY logic link, so a redundant non-driving link forks and joins "
        "the chain: EVM2 target 29 serves 'Path 01 (1)' [17,18,19,20] / (2) [22] / (3) [23..29] "
        "for one serial 0-day chain (20 -> 23 has 3 working days of free float), Project5 "
        "target 67 serves 9 branches where the driving links give 7 (48 -> 55, 42 wd), and the "
        "hand chain "
        "A -> B -> C + A -> C (2 wd) serves [1] / [2] / [3]"
    ),
)
def test_a0923_cpm_039_a_non_driving_link_never_splits_a_serial_driving_chain() -> None:
    """A0923-CPM-039 (finder id F-FAMB-005) · CPM · T2 (option-gated: Output = Separate parallel
    paths; in the committed corpus -- EVM2 target 29, Project5 target 67).

    Claim (as VERIFIED by P2 and P6 -- narrowed to fake forks / joins from non-driving links,
    broadened to the Project5 golden): at 0b45eb28, ``GET /api/driving/{key}?target=N`` serves
    ``parallel_paths`` -- the on-path set decomposed at every logic link between two on-path
    tasks -- so a link that lies on the driving path's node set but carries a working day or more
    of free float is treated as a fork and a join. The committed EVM2 golden traced to UID 29 (ten
    on-path activities, every driving slack 0 d, one serial chain 17 -> 18 -> 19 -> 20 -> 22 -> 23
    -> 25 -> 26 -> 28 -> 29) serves three branches 'Path 01 (1)' [17, 18, 19, 20], 'Path 01 (2)'
    [22], 'Path 01 (3)' [23, 25, 26, 28, 29], which /path's 'Separate parallel paths' output paints
    as three headers (P6, Chromium) -- the three groups are strictly consecutive in time
    (08-14..09-13, 09-14..09-18, 09-19..10-04), never concurrent. The committed Project5 golden at
    target 67 -- the target tests/web/test_path_options.py::test_api_driving_drag_and_parallel_paths
    pins, asserting only the label prefix and the union of UIDs -- serves 9 branches where the
    driving links give 7 (the non-driving 48 -> 55 splits 48|49 and 53|55; the genuine parallel
    pairs 60/61 and 65/66 stay separate). The hand chain A -> B -> C plus a redundant A -> C link
    serves [1] / [2] / [3]. Mechanism: ``web/driving.py:345-348`` builds ``succ_in_path`` /
    ``pred_in_path`` from every ``sch.relationships`` entry whose two ends are on the path; the
    engine's per-link route slack (``driving_slack.py:365-386``: free float - lag + the successor's
    slack, the value ``on_driving_path`` is judged on) is never consulted, so the decomposition
    provably cannot tell a driving link from a non-driving one (P6: a genuinely driving second
    route and a redundant link serve identical branches). On-path membership, every driving-slack
    figure and DRAG are right; only the grouping is wrong.

    Authority: A2 (the builder's own contract) -- ``web/driving.py:183-184``: "The payload always
    carries ``parallel_paths`` -- the on-path set decomposed into its parallel branches -- so the
    client can render the SSI "Separate parallel paths" output."; ``web/driving.py:340-341``:
    "# SSI "Separate parallel paths": decompose the on-path set into serial branches -- a new
    branch starts wherever a path task is not the single continuation of the previous one";
    ``static/path.js:484-485``: "Separate parallel paths = the server's branch decomposition of
    the driving path, one header per parallel branch." A1 -- MS Project's own stored dates in the
    raw EVM2 XML: every chain link is FS0 with the successor starting the next working morning
    (20 finishes Thu 2012-09-13 17:00, 22 starts Fri 09-14 08:00 and finishes Tue 09-18 17:00, 23
    starts Wed 09-19 08:00) while 20 -> 23 (FS0) spans Fri 14, Mon 17, Tue 18 = 3 working days of
    free float, so the route 20 -> 23 carries 3 d of driving slack and is not a 0-day path: there
    is exactly one zero-slack route and no parallel branch; on Project5, 48 finishes Fri 2026-11-20
    17:00 and 55 starts Wed 2027-01-20 08:00 (42 weekdays between), every other in-path link is
    next-working-day. Hand arithmetic on the inline chain (480 min/day): A 01-06..01-07, B 01-08..
    01-09, C 01-10..01-13; B -> C and A -> B have 0 free float, A -> C has Wed 01-08 + Thu 01-09
    = 2 working days -- one chain [1, 2, 3]; with A shortened to 1.5 d (finish Tue 01-07 12:00)
    A -> B has 240 min = 0 whole days (driving, the same floor ``on_driving_path`` uses,
    ``driving_slack.py:396``) and A -> C 1,200 min = 2 whole days -- still one chain [1, 2, 3].
    SSI's own definition of "Separate parallel paths"
    is UNVERIFIED (ssitools.com and mpug.com egress-blocked 2026-09-29; no committed SSI export
    ran that output -- 93 content-sniffed workbooks carry only 'Path 01/02/03'), so the code's
    own contract is the authority (finder, both verifiers, the lead).

    Independence: MS Project's stored dates read from the raw XML (never the importer or the
    trace), hand arithmetic, and the engine's own on-path / slack rows as PRECONDITIONS -- never
    the decomposition under test. Controls (preconditions): the same hand chain without the
    redundant link serves ONE branch [1, 2, 3] (the check can pass), and a genuine diamond A ->
    {B, C} -> D serves [1] / [2] / [3] / [4] -- a fix that merged every branch would be refused by
    name, not passed.
    """
    serial, _ = _a0923_cpm_039_served(
        "a0923_cpm_039_serial.xml", _a0923_cpm_039_mspdi("serial").encode(), 3
    )
    if serial != [[1, 2, 3]]:
        pytest.fail(
            f"precondition (control): the serial hand chain no longer serves one branch {serial}"
        )
    diamond, _ = _a0923_cpm_039_served(
        "a0923_cpm_039_diamond.xml", _a0923_cpm_039_mspdi("diamond").encode(), 4
    )
    if diamond != [[1], [2], [3], [4]]:
        pytest.fail(
            f"precondition (control): the diamond no longer decomposes at its fork / join {diamond}"
        )

    evm2_raw = _A0923_CPM_039_EVM2.read_bytes()
    p5_raw = _A0923_CPM_039_PROJECT5.read_bytes()
    evm2_links = _a0923_cpm_039_raw_links(evm2_raw, _A0923_CPM_039_EVM2_CHAIN)
    p5_links = _a0923_cpm_039_raw_links(p5_raw, [u for b in _A0923_CPM_039_P5_BRANCHES for u in b])
    slack_links = (
        {k: v for k, v in evm2_links.items() if v},
        {k: v for k, v in p5_links.items() if v},
    )
    if slack_links != ({(20, 23): 3}, {(48, 55): 42}):
        pytest.fail(
            "precondition: MS Project's stored dates no longer show the one non-driving link per "
            f"golden {slack_links}"
        )
    if len(evm2_links) != 10 or len(p5_links) != 22:
        pytest.fail(
            f"precondition: the in-path link census moved ({len(evm2_links)} EVM2, "
            f"{len(p5_links)} Project5)"
        )

    hand, hand_rows = _a0923_cpm_039_served(
        "a0923_cpm_039_redundant.xml", _a0923_cpm_039_mspdi("redundant").encode(), 3
    )
    subday, subday_rows = _a0923_cpm_039_served(
        "a0923_cpm_039_subday.xml", _a0923_cpm_039_mspdi("subday").encode(), 3
    )
    evm2, evm2_rows = _a0923_cpm_039_served("EVM2.mspdi.xml", evm2_raw, 29)
    p5, p5_rows = _a0923_cpm_039_served("Project5.mspdi.xml", p5_raw, 67)
    p5_uids = sorted(u for b in _A0923_CPM_039_P5_BRANCHES for u in b)
    for label, rows, want in (
        ("hand", hand_rows, [1, 2, 3]),
        ("subday", subday_rows, [1, 2, 3]),
        ("EVM2", evm2_rows, _A0923_CPM_039_EVM2_CHAIN),
        ("Project5", p5_rows, p5_uids),
    ):
        on_path = sorted(u for u, (_days, on) in rows.items() if on)
        zero = all(rows[u][0] == 0 for u in want)
        if on_path != want or not zero:
            pytest.fail(
                f"precondition: {label}'s on-path rows moved: {on_path} (0 d: {zero}), want {want}"
            )

    wrong = {
        label: f"{got} (want {want})"
        for label, got, want in (
            ("hand A -> B -> C + redundant A -> C (2 wd free)", hand, [[1, 2, 3]]),
            ("hand A (1.5 d) -> B (0.5 wd free) -> C + A -> C (2.5 wd free)", subday, [[1, 2, 3]]),
            ("EVM2 target 29 (20 -> 23, 3 wd free)", evm2, [_A0923_CPM_039_EVM2_CHAIN]),
            ("Project5 target 67 (48 -> 55, 42 wd free)", p5, _A0923_CPM_039_P5_BRANCHES),
        )
        if got != want
    }
    assert not wrong, (
        "a non-driving link between two on-path tasks forks and joins the served 'Separate "
        "parallel paths' decomposition (one serial 0-day chain rendered as parallel branches): "
        f"{wrong}"
    )


# --- A0923-CPM-040 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py (no new import):
#   imports    html, io, json, re, xml.etree.ElementTree as ET, zipfile, pytest,
#              TestClient (fastapi.testclient), SessionState / create_app (web.app)
#   constants  GOLDEN (REPO / "tests" / "fixtures" / "golden"), NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Input: the committed, non-CUI golden project2_5/Project5.mspdi.xml (plain XML), read in place.
# The REDUCE filter is applied through the operator's own /groups form. No new fixture file.

#: the /driving-path tiers panel's embedded rows (web/driving.py:645) -- the on-screen tier table
#: (the three visible tier tables and this embed are rendered from ONE `buckets` pass, :569-571)
_A0923_CPM_040_EMBED = re.compile(
    r'<script type="application/json" id=drivingTiersData>(.*?)</script>', re.S
)
#: one visible row of a tier table (web/driving.py:551-553): UID, Activity, Slack (d)
_A0923_CPM_040_VISIBLE_ROW = re.compile(
    r"<tr><td class=num>(\d+)</td><td>[^<]*</td><td class=num>(-?\d+\.\d)</td></tr>"
)
#: the tiers panel's own Excel link (web/driving.py:578-581): target + the page's trace options
_A0923_CPM_040_TIERS_LINK = re.compile(r"/export/xlsx/driving-tiers/[^\"'<>]+")
#: the WBS value the filter drops -- the WBS of UID 35, which sits on the driving path to 67
_A0923_CPM_040_DROPPED_WBS = "5.3"


def _a0923_cpm_040_wbs_split(raw: bytes, dropped: str) -> tuple[frozenset[int], frozenset[int]]:
    """(UIDs whose <WBS> is not ``dropped``, UIDs whose <WBS> is ``dropped``), read from the raw
    MSPDI with ElementTree -- the population a REDUCE filter on WBS keeps / removes, independent
    of the importer, the filter and the engine under test."""
    kept: set[int] = set()
    gone: set[int] = set()
    for el in ET.fromstring(raw).iter(NS + "Task"):
        uid = (el.findtext(NS + "UID") or "").strip()
        wbs = (el.findtext(NS + "WBS") or "").strip()
        if not uid.isdigit():
            continue
        (gone if wbs == dropped else kept).add(int(uid))
    return frozenset(kept), frozenset(gone)


def _a0923_cpm_040_flags(raw: bytes, uid: int) -> tuple[str, str] | None:
    """(Summary, Active) of one <Task> as MS Project stored them ('' when the element is absent)."""
    for el in ET.fromstring(raw).iter(NS + "Task"):
        if (el.findtext(NS + "UID") or "").strip() == str(uid):
            return (
                (el.findtext(NS + "Summary") or "").strip(),
                (el.findtext(NS + "Active") or "").strip(),
            )
    return None


def _a0923_cpm_040_sheet(content: bytes) -> list[dict[str, str]]:
    """The first worksheet of a served xlsx as one {column letter: text} per row -- std-lib only
    (the tool writes inline strings and native numbers). A cell the writer never emitted is
    ABSENT from its row's dict, so a blank exported cell is observable as such."""
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
    for el in root.iter():
        el.tag = el.tag.rsplit("}", 1)[-1]  # strip the spreadsheetml namespace
    rows: list[dict[str, str]] = []
    for row in root.iter("row"):
        cells: dict[str, str] = {}
        for c in row.iter("c"):
            ref = re.match(r"[A-Z]+", c.get("r") or "")
            if ref is None:
                continue
            t = c.find("is/t")  # inline string
            v = c.find("v")  # native number / value
            cells[ref.group(0)] = (t.text or "") if t is not None else (v.text or "")
        rows.append(cells)
    return rows


def _a0923_cpm_040_uid_column(rows: list[dict[str, str]]) -> tuple[int, str]:
    """(index of the header row, column letter of the UID column) of an exported sheet."""
    for i, row in enumerate(rows):
        for col, text in row.items():
            if text in ("UID", "Unique ID"):
                return i, col
    pytest.fail("precondition: the exported sheet carries no UID column")


def _a0923_cpm_040_session(raw: bytes, *, filtered: bool) -> tuple[SessionState, TestClient, str]:
    """Project5 loaded in a fresh session; with ``filtered`` the operator's own REDUCE filter --
    WBS = every value the file carries except 5.3 -- applied through GET /groups."""
    st = SessionState()
    client = TestClient(create_app(st))
    up = client.post("/upload", files={"files": ("Project5.mspdi.xml", raw, "text/xml")})
    if up.status_code != 200:
        pytest.fail(f"precondition: upload of Project5 answered {up.status_code}")
    key = next(iter(st.schedules))
    if filtered:
        values = sorted(
            {
                (el.findtext(NS + "WBS") or "").strip()
                for el in ET.fromstring(raw).iter(NS + "Task")
                if (el.findtext(NS + "WBS") or "").strip()
            }
            - {_A0923_CPM_040_DROPPED_WBS}
        )
        query = "&".join(
            [
                "field=WBS",
                *(f"value0={quote(v, safe='')}" for v in values),
                "mode=reduce",
                "apply=1",
            ]
        )
        if client.get(f"/groups?{query}").status_code != 200:
            pytest.fail("precondition: /groups no longer applies a WBS reduce filter")
        if st.filter_mode != "reduce" or [f for f, _v in st.active_filter] != ["WBS"]:
            pytest.fail(
                f"precondition: the session filter is not a WBS reduce filter: "
                f"{st.filter_mode} {[f for f, _v in st.active_filter]}"
            )
    return st, client, key


def _a0923_cpm_040_tiers(
    client: TestClient, opts: str
) -> tuple[dict[int, float], dict[int, tuple[float, str | None]], str]:
    """For ``GET /driving-path?target=67{opts}``: (the on-screen tier rows uid -> slack, the rows
    of the workbook the panel's own Excel link serves uid -> (slack, Activity cell or None when
    absent), that link). The embed and the visible tables must agree (one render pass)."""
    page = client.get(f"/driving-path?target=67{opts}").text
    embed = _A0923_CPM_040_EMBED.search(page)
    if embed is None:
        pytest.fail(f"precondition: /driving-path?target=67{opts} renders no tiers panel embed")
    data = json.loads(embed.group(1).replace("\\u003c", "<"))
    panel = {int(row["uid"]): round(float(row["slack"]), 1) for row in data["rows"]}
    start, end = page.find("Driving tiers to 67"), page.find("All driving-tier activities")
    visible = {
        int(uid): round(float(slack), 1)
        for uid, slack in _A0923_CPM_040_VISIBLE_ROW.findall(page[start:end])
    }
    if start < 0 or end < 0 or visible != panel:
        pytest.fail(f"precondition: the visible tier tables and the embed differ {visible} {panel}")
    link = _A0923_CPM_040_TIERS_LINK.search(page)
    if link is None:
        pytest.fail("precondition: the tiers panel no longer carries its Excel link")
    url = html.unescape(link.group(0))
    served = client.get(url)
    if served.status_code != 200:
        pytest.fail(f"precondition: {url} answered {served.status_code}")
    rows = _a0923_cpm_040_sheet(served.content)
    header, uid_col = _a0923_cpm_040_uid_column(rows)
    cols = {text: col for col, text in rows[header].items()}
    if "Slack (d)" not in cols or "Activity" not in cols:
        pytest.fail(f"precondition: the tiers export header changed: {rows[header]}")
    exported = {
        int(float(row[uid_col])): (
            round(float(row[cols["Slack (d)"]]), 1),
            row.get(cols["Activity"]),
        )
        for row in rows[header + 1 :]
        if row.get(uid_col)
    }
    return panel, exported, url


def _a0923_cpm_040_path(client: TestClient, key: str, opts: str) -> tuple[set[int], set[int]]:
    """(the UIDs /api/driving/{key}?target=67 serves, the UIDs /export/xlsx/path/{key}?target=67
    exports) under ``opts`` (``basis=resolve`` is the export's own parameter and is not sent to
    the API, whose trace is the stored-date family-A one)."""
    api = client.get(f"/api/driving/{key}?target=67{opts.replace('&basis=resolve', '')}")
    if api.status_code != 200:
        pytest.fail(f"precondition: /api/driving answered {api.status_code}: {api.text[:120]}")
    served = client.get(f"/export/xlsx/path/{key}?target=67{opts}")
    if served.status_code != 200:
        pytest.fail(f"precondition: /export/xlsx/path answered {served.status_code}")
    rows = _a0923_cpm_040_sheet(served.content)
    header, uid_col = _a0923_cpm_040_uid_column(rows)
    exported = {
        int(float(row[uid_col]))
        for row in rows[header + 1 :]
        if re.fullmatch(r"-?\d+(\.0)?", row.get(uid_col, ""))
    }
    return {int(r["unique_id"]) for r in api.json()["rows"]}, exported


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-040: with a session REDUCE filter active, /export/{fmt}/driving-tiers and "
        "/export/{fmt}/path pair the RAW schedule with the scoped CPM (web/app.py:5785 "
        "_optioned_versions([sch], [analysis.cpm]); :4808 st.analysis_for(name, sch).cpm then "
        "_driving_data(sch, ...)), so on Project5 target 67 with WBS 5.3 (UID 35) filtered out the "
        "tiers export carries the unfiltered 32 rows where the panel shows 18 (UID 35 with a blank "
        "Activity cell) and the path export 43 rows incl. UID 35 where /api/driving serves 29"
    ),
)
def test_a0923_cpm_040_the_tiers_and_path_exports_carry_the_population_the_page_shows() -> None:
    """A0923-CPM-040 (finder id F-FAMB-007) · CPM · T2 (in committed corpus: Project5 + any
    reducing filter that cuts the trace).

    Claim (as VERIFIED -- the verifier's corrected counts): at 0b45eb28, with the committed
    Project5 golden loaded and a REDUCE filter WBS = every value except 5.3 (the WBS of UID 35,
    which sits on the driving path to 67), ``GET /export/xlsx/driving-tiers/Project5.mspdi.xml
    ?target=67`` -- the tiers panel's own Excel link -- exports 32 tier rows, exactly the UNFILTERED
    export, while the /driving-path tiers panel and its ``#drivingTiersData`` embed show 18; the
    14 export-only UIDs are 3, 19-23, 25-27, 29-31, 33 and 35, and UID 35 is exported with a BLANK
    Activity cell (the export's name lookup reads the scoped ``activity_rows`` while its row set
    does not). Under ``ignore_leveling=1``: 32 vs 18, 17 export-only UIDs (incl. 38, 39, 42, 44),
    9 / 11 / 17 on the panel but not in the export, and UID 3 at 12.0 d in the export against
    0.0 d on screen. Second site, same root cause: ``GET /export/xlsx/path/Project5?target=67``
    (the /path page's Excel; with ``basis=resolve`` the /driving-path page's full-trace link)
    exports 43 rows including the filtered-out UID 35 where ``/api/driving/Project5?target=67``
    serves 29; the same with ``ignore_leveling=1&basis=resolve``. Mechanism: ``web/app.py:5774``
    resolves the RAW schedule (``_find_schedule``) and ``:5785-5786`` passes
    ``_optioned_versions([sch], [analysis.cpm], ...)`` into ``compute_driving_slack`` (``:5791``),
    while the panel is fed the scoped pair (``:4041`` ``_solvable_versions`` -> ``:2601``
    ``st.cpm_scoped_for``; ``:4068`` for ``?file=``); ``:4808`` takes ``st.analysis_for(name,
    sch).cpm`` and ``:4825`` hands the raw ``sch`` to ``_driving_data`` (``:4818-4819`` to
    ``_optioned_versions`` under ``basis=resolve``) while ``/api/driving`` (``:2375-2380``) pairs
    ``a.scoped`` with ``a.cpm``. HIGHLIGHT mode keeps the population whole, so the split is
    REDUCE-only (and, by the same mechanism, Target-UID scope -- not asserted here).

    Authority: A2 -- the route's own contract, ``src/schedule_forensics/web/app.py:5768-5770``:
    "The export honours the same ``ignore_constraints`` / ``ignore_leveling`` trace options as
    the page, so the downloaded tier membership + slack are computed on the SAME network the
    panel shows (ADR-0174)."; ``docs/adr/0174-driving-tiers-export-trace-option-fidelity.md:35``:
    "so the **whole** exported table equals the on-screen table."; ``docs/adr/0420-a-scoped-
    analysis-paired-with-a-raw-population.md:56``: "Pass `analysis.scoped` wherever the analysis
    is paired with a population." and ``:16-17``: "A CPM solved on one task set grading a
    different task set is incoherent — tasks the solver never saw get scored by it, and the page
    states two population sizes at once."; the sibling route's own comment,
    ``src/schedule_forensics/web/app.py:2375-2377``: "pair the schedule with the SAME scope as
    its cpm: tracing the raw (unscoped) network against a scoped cpm would mix a
    filtered/target-truncated timing set onto the full task list." (Read at 0b45eb28,
    2026-09-29.) The oracle is the page's own panel / embed and ``/api/driving`` -- independent
    code paths that receive the scoped schedule -- plus the raw XML's own WBS values (the set of
    tasks a WBS filter keeps, read with ElementTree). Deliberate-decision screen (finder +
    verifier): ADRs 0095, 0169, 0174, 0186, 0251, 0265, 0381 and 0420 keep no raw-population
    export; ADR-0420 requires the opposite. Not HELD, not a duplicate.

    Control (precondition): with no filter the two exports equal the screen (tiers 32 = 32 under
    both option sets; path 43 = 43) and UID 35 is on both, so a "fix" that breaks an export fails
    by name here instead of passing. Census (finder, re-derived by the assembler): ADR-0420's
    standing AST census (``tests/web/test_scoped_population_contract.py:192-261``) reports 0
    sites at 0b45eb28 because it never descends into list / tuple literals (``[sch]``,
    ``[analysis.cpm]``) and needs the analysis bound to a name (``export_path`` takes ``.cpm``
    inline); the runtime census (``tests/web/test_scoped_pairing_census.py:187-200``) sweeps only
    parameter-less GET routes, and both exports take ``{fmt}`` / ``{name}`` and a required
    ``target``. The detector with one change -- descending into list literals -- finds exactly 1
    site in the view layer (``export_driving_tiers``); by behaviour, 2 sites.
    """
    raw = (GOLDEN / "project2_5" / "Project5.mspdi.xml").read_bytes()
    kept, gone = _a0923_cpm_040_wbs_split(raw, _A0923_CPM_040_DROPPED_WBS)
    if 35 not in gone or _a0923_cpm_040_flags(raw, 35) != ("0", "1"):
        pytest.fail("precondition: Project5 UID 35 is no longer an active activity under WBS 5.3")
    if 67 not in kept or _a0923_cpm_040_flags(raw, 67) != ("0", "1"):
        pytest.fail("precondition: Project5 UID 67 is no longer an active activity outside WBS 5.3")

    # -- control: unfiltered, both exports equal the screen and UID 35 is on the trace to 67 -----
    _st, client, key = _a0923_cpm_040_session(raw, filtered=False)
    whole: dict[str, dict[int, float]] = {}  # the unfiltered on-screen tiers, per option set
    for opts in ("", "&ignore_leveling=1"):
        panel, exported, url = _a0923_cpm_040_tiers(client, opts)
        if set(panel) != set(exported) or 35 not in panel:
            pytest.fail(
                f"precondition (control): unfiltered, {url} no longer equals the panel or UID 35 "
                f"left the tiers: panel {sorted(panel)} export {sorted(exported)}"
            )
        whole[opts] = panel
    api, exported_path = _a0923_cpm_040_path(client, key, "")
    if api != exported_path or 35 not in api:
        pytest.fail(
            f"precondition (control): unfiltered, /export/xlsx/path no longer equals /api/driving "
            f"or UID 35 left the trace: api {sorted(api)} export {sorted(exported_path)}"
        )

    # -- the operator's REDUCE filter (WBS = every value but 5.3) through /groups --------------
    _st, client, key = _a0923_cpm_040_session(raw, filtered=True)
    if "Filter active" not in client.get("/driving-path?target=67").text:
        pytest.fail("precondition: the page chrome no longer discloses the active filter")

    wrong: dict[str, dict[str, object]] = {}
    for opts in ("", "&ignore_leveling=1"):
        panel, exported, url = _a0923_cpm_040_tiers(client, opts)
        if 35 in panel or set(panel) == set(whole[opts]):
            # the filter must bite on screen: UID 35 gone and the tier table changed (under the
            # option the re-solved FILTERED network also promotes 9 / 11 / 17, so no subset test)
            pytest.fail(
                f"precondition: the filter no longer changes the tiers panel {sorted(panel)}"
            )
        only_export = sorted(set(exported) - set(panel))
        only_panel = sorted(set(panel) - set(exported))
        slack = {u: (panel[u], exported[u][0]) for u in panel.keys() & exported.keys()}
        slack = {u: v for u, v in slack.items() if v[0] != v[1]}
        outside = sorted(u for u in exported if u not in kept)
        if only_export or only_panel or slack or outside:
            wrong[f"GET {url}"] = {
                "panel rows": len(panel),
                "exported rows": len(exported),
                "only in the export": only_export,
                "only on the panel": only_panel,
                "slack (panel, export) where they differ": slack,
                "exported although filtered out": outside,
                "exported with a blank Activity cell": sorted(
                    u for u, (_s, name) in exported.items() if not name
                ),
            }
    for opts in ("", "&ignore_leveling=1&basis=resolve"):
        api, exported_path = _a0923_cpm_040_path(client, key, opts)
        outside = sorted(u for u in exported_path if u not in kept)
        if (opts == "" and exported_path != api) or outside:
            wrong[f"GET /export/xlsx/path/{key}?target=67{opts}"] = {
                "exported rows": len(exported_path),
                "/api/driving rows": len(api),
                "only in the export": sorted(exported_path - api),
                "only in /api/driving": sorted(api - exported_path),
                "exported although filtered out": outside,
            }

    assert not wrong, (
        "with a session REDUCE filter active an export carries rows the page it is exported from "
        f"never shows (the raw schedule paired with the scoped CPM, ADR-0420): {wrong}"
    )


# --- A0923-CPM-041 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    typing.Any, pytest, TestClient (fastapi.testclient), urllib.parse.quote,
#              compute_cpm (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi),
#              Schedule (schedule_forensics.model.schedule),
#              SessionState and create_app (schedule_forensics.web.app)
#   fixture    the module-level autouse _air_gapped
# Input: inline MSPDI text (built below) -- ONE hand network under four project headers. No
# fixture file; nothing CUI.

#: Working minutes per activity, chosen as WHOLE days on both an 8-hour (480) and a 10-hour
#: (600) day so that no display rounding enters: Design 4,800 / Build 9,600 / Permits 2,400.
_A0923_CPM_041_MINUTES = {11: 4800, 12: 9600, 13: 2400, 14: 0}
#: FS0 links 11->12, 11->13, 12->14, 13->14: Permits' total float is Build minus Permits.
_A0923_CPM_041_PERMITS_TF = 9600 - 2400
#: (project header MinutesPerDay, the calendar's working minutes a day): the two mismatched
#: files under test (the finder's shape and the verifier's reverse instance) and their
#: consistent twins (the control -- the day figures are right whenever the two days agree).
_A0923_CPM_041_MISMATCHED = ((480, 600), (600, 480))
_A0923_CPM_041_CONSISTENT = ((480, 480), (600, 600))


def _a0923_cpm_041_mspdi(declared: int, calendar_minutes: int) -> str:
    """MSPDI with ``<MinutesPerDay>declared</MinutesPerDay>`` (MS Project's "Hours per day"
    option times 60) over a Mon-Fri project calendar working ``calendar_minutes`` a day: 600 =
    07:00-12:00 + 13:00-18:00 (start Mon 2026-06-01 07:00), 480 = 08:00-12:00 + 13:00-17:00
    (start 08:00). Activities (DurationFormat 7 = days, unstarted, remaining = duration):
      Design  (UID 11) 4,800 min;  Build (UID 12) 9,600 min, FS0 after Design;
      Permits (UID 13) 2,400 min, FS0 after Design;  Complete (UID 14) milestone after both."""
    if calendar_minutes == 600:
        start_hour, blocks = "07", (("07:00:00", "12:00:00"), ("13:00:00", "18:00:00"))
    else:
        start_hour, blocks = "08", (("08:00:00", "12:00:00"), ("13:00:00", "17:00:00"))
    times = (
        "<WorkingTimes>"
        + "".join(
            f"<WorkingTime><FromTime>{a}</FromTime><ToTime>{b}</ToTime></WorkingTime>"
            for a, b in blocks
        )
        + "</WorkingTimes>"
    )
    days = "".join(
        f"<WeekDay><DayType>{d}</DayType><DayWorking>{int(2 <= d <= 6)}</DayWorking>"
        + (times if 2 <= d <= 6 else "")
        + "</WeekDay>"
        for d in range(1, 8)
    )

    def task(uid: int, name: str, minutes: int, *preds: int) -> str:
        links = "".join(
            f"<PredecessorLink><PredecessorUID>{p}</PredecessorUID><Type>1</Type>"
            "<LinkLag>0</LinkLag><LagFormat>7</LagFormat></PredecessorLink>"
            for p in preds
        )
        dur = f"PT{minutes // 60}H{minutes % 60}M0S"
        return (
            f"<Task><UID>{uid}</UID><ID>{uid}</ID><Name>{name}</Name><OutlineLevel>1"
            f"</OutlineLevel><Duration>{dur}</Duration><DurationFormat>7</DurationFormat>"
            f"<RemainingDuration>{dur}</RemainingDuration><PercentComplete>0</PercentComplete>"
            f"<Milestone>{int(minutes == 0)}</Milestone><Summary>0</Summary>{links}</Task>"
        )

    return (
        '<Project xmlns="http://schemas.microsoft.com/project"><Name>a0923-cpm-041</Name>'
        f"<ScheduleFromStart>1</ScheduleFromStart><StartDate>2026-06-01T{start_hour}:00:00"
        f"</StartDate><CalendarUID>1</CalendarUID><MinutesPerDay>{declared}</MinutesPerDay>"
        f"<MinutesPerWeek>{declared * 5}</MinutesPerWeek><DaysPerMonth>20</DaysPerMonth>"
        "<Calendars><Calendar><UID>1</UID><Name>ProjectCal</Name><IsBaseCalendar>1"
        f"</IsBaseCalendar><BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{days}</WeekDays>"
        "</Calendar></Calendars><Tasks>"
        + task(11, "Design", 4800)
        + task(12, "Build", 9600, 11)
        + task(13, "Permits", 2400, 11)
        + task(14, "Complete", 0, 12, 13)
        + "</Tasks></Project>"
    )


def _a0923_cpm_041_served(text: str) -> tuple[Schedule, dict[int, dict[str, Any]]]:
    """Upload ``text`` into a fresh app and read the activity rows GET /api/analysis/<key>
    serves (the /analysis grid, the Gantt, the Task Information dialog and the exports read
    them): (the loaded Schedule, rows by unique id)."""
    state = SessionState()
    client = TestClient(create_app(state))
    up = client.post("/upload", files={"files": ("a0923_cpm_041.xml", text.encode(), "text/xml")})
    if up.status_code != 200 or len(state.schedules) != 1:
        pytest.fail(f"precondition: upload answered {up.status_code} ({list(state.schedules)})")
    key = next(iter(state.schedules))
    data = client.get(f"/api/analysis/{quote(key, safe='')}")
    if data.status_code != 200:
        pytest.fail(f"precondition: /api/analysis answered {data.status_code}")
    rows = {int(r["unique_id"]): r for r in data.json().get("activities", [])}
    if set(rows) != set(_A0923_CPM_041_MINUTES):
        pytest.fail(f"precondition: /api/analysis no longer serves the four rows: {sorted(rows)}")
    return state.schedules[key], rows


def _a0923_cpm_041_day_figures(
    declared: int, calendar_minutes: int
) -> tuple[dict[str, float | None], dict[str, float]]:
    """(the served day figures, the same figures on the file's DECLARED day) for the header
    ``declared`` over a ``calendar_minutes`` calendar -- after pinning the two days the model
    carries and the engine's minutes, which are not in dispute."""
    text = _a0923_cpm_041_mspdi(declared, calendar_minutes)
    sch, rows = _a0923_cpm_041_served(text)
    cal = sch.calendar
    if (cal.working_minutes_per_day, cal.declared_minutes_per_day) != (calendar_minutes, declared):
        pytest.fail(
            f"precondition: the importer no longer carries both days for {declared}/"
            f"{calendar_minutes}: derived {cal.working_minutes_per_day}, declared "
            f"{cal.declared_minutes_per_day}"
        )
    minutes = {u: sch.tasks_by_id[u].duration_minutes for u in _A0923_CPM_041_MINUTES}
    if minutes != _A0923_CPM_041_MINUTES:
        pytest.fail(f"precondition: the imported working minutes moved: {minutes}")
    timings = compute_cpm(parse_mspdi_text(text)).timings
    tf = {u: timings[u].total_float for u in (11, 12, 13)}
    if tf != {11: 0, 12: 0, 13: _A0923_CPM_041_PERMITS_TF}:
        pytest.fail(f"precondition: the engine's own float minutes moved: {tf}")
    served: dict[str, float | None] = {}
    want: dict[str, float] = {}
    for uid, name in ((11, "Design"), (12, "Build"), (13, "Permits")):
        served[f"{name} duration_days"] = rows[uid]["duration_days"]
        served[f"{name} remaining_duration_days"] = rows[uid]["remaining_duration_days"]
        want[f"{name} duration_days"] = _A0923_CPM_041_MINUTES[uid] / declared
        want[f"{name} remaining_duration_days"] = _A0923_CPM_041_MINUTES[uid] / declared
    served["Permits total_float_days"] = rows[13]["total_float_days"]
    want["Permits total_float_days"] = _A0923_CPM_041_PERMITS_TF / declared
    return served, want


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-041: every served day figure divides by the calendar's DERIVED working day "
        "(web/state.py:1703 per_day; engine/float_analysis.py:78) and never by the file's own "
        "<MinutesPerDay> (Calendar.declared_minutes_per_day, read only by filter literals), so "
        "a file declaring 480 over a 600-minute calendar serves Build 16.0 d and Permits' total "
        "float 12.0 d for 9,600 / 7,200 minutes where the declared day and MPXJ 16.2.0 give 20 "
        "/ 15 -- the stated premise of ADR-0355:67-69 ('exactly mirroring MPXJ's split') and of "
        "ADR-0516:53-54 ('the schedule's declared day') is not what the code does"
    ),
)
def test_a0923_cpm_041_served_day_figures_read_the_files_declared_minutes_per_day() -> None:
    """A0923-CPM-041 (finder id F-DAY-003) · CPM · T2 latent -- a PREMISE finding on ADR-0516
    decision 3 / ADR-0355:67-69 (the lead's ruling, LEAD-VALIDATION.md).

    Claim (verifier P3's narrowing, adopted): at 0b45eb28 a hand MSPDI declaring
    ``<MinutesPerDay>480</MinutesPerDay>`` (MS Project's "Hours per day" option = 8) over a
    600-minute project calendar (07-12 / 13-18 Mon-Fri), loaded via ``/upload``, has every day
    figure of ``GET /api/analysis/<key>`` served on the calendar's DERIVED 600-minute day --
    here Design / Build / Permits ``duration_days`` and ``remaining_duration_days`` 8.0 / 16.0
    / 4.0 for 4,800 / 9,600 / 2,400 working minutes and Permits' ``total_float_days`` 12.0 for
    7,200 -- byte-identical to the consistent twin declaring 600, while the file's own
    MinutesPerDay gives 10 / 20 / 5 and 15. The reverse instance (600 declared over an 8-hour
    calendar) serves 10.0 / 20.0 / 5.0 and 15.0 where the declared day gives 8 / 16 / 4 and 12.
    Two producers, both documented decisions whose stated premise the code does not meet:
    ``web/state.py:1703`` ``per_day = sch.calendar.working_minutes_per_day or 480`` (the
    duration / remaining / work / lag day figures of the activity row -- ADR-0355:67-69) and
    ``engine/float_analysis.py:78`` ``per_day = schedule.calendar.working_minutes_per_day``
    (``total_float_days`` / ``free_float_days`` -- ADR-0516 decision 3).
    ``Calendar.declared_minutes_per_day`` is read by ``engine/msp_filters.py:148`` alone
    (filter literals). The engine's minutes and dates are NOT in dispute (compute_cpm gives 7,200
    on every header; MPXJ's MicrosoftScheduler dates the same); ``/analysis`` discloses
    'Working day 10 h/day (600 min)' and never the declared 8 h/day. Latent: declared == derived
    on every committed MSPDI document (71 sniffed by the finder; 44 of 44 in the corpus).

    Authority: A1 -- the file's own ``<MinutesPerDay>`` with each task's ``<Duration>`` /
    ``<DurationFormat>7</DurationFormat>``: 9,600 / 480 = 20 days (hand arithmetic). Microsoft
    Learn, 'MinutesPerDay Element' (Project XML Data Interchange): "The default number of
    minutes per day."; 'ProjectDataSet.ProjectRow.PROJ_OPT_MINUTES_PER_DAY':
    "PROJ_OPT_MINUTES_PER_DAY maps to 60 * the Hours per day option on the Calendar tab of the
    Options dialog box in Project Professional."; 'DurationFormat Element': "For an item such as
    a task, it is the format for the duration. This paired with the duration value determine the
    actual duration of the item." -- "7 | d (days)" (all three re-read by this assembler
    2026-09-29). Witness (the model ADR-0355 names): the vendored MPXJ 16.2.0
    ``UniversalProjectReader`` reads THESE inline files as Build duration=20.0d (declared 480 /
    calendar 600) and 16.0d (declared 600 / calendar 480) -- the declared day both times, as on
    the consistent twins (480 / 480 = 20.0d, 600 / 600 = 16.0d).
    A2 -- ``docs/adr/0355-four-codex-findings-on-the-duration-literal-fix-all-confirmed-all-
    hardened.md:67-69``: "**`working_minutes_per_day` remains the engine-wide day length** for
    duration→days display everywhere else; only filter LITERALS read the declared setting,
    exactly mirroring MPXJ's split between calendar time and `TimeUnitDefaultsContainer`."
    (MPXJ's ``Duration.convertUnits(DAYS, ProjectProperties)`` scales EVERY duration by the
    declared setting, so the premise falls on its own output); ``docs/adr/0516-…-r-75-
    closed.md:53-54``: "they are the tool's reading on the schedule's declared day, the
    convention MS Project's own slack display follows (its hours-per-day setting) --
    **UNVERIFIED** here" (the code reads the derived day); ``src/schedule_forensics/model/
    calendar.py:34-36``: "``declared_minutes_per_day`` is the file's own duration-scale SETTING
    and can legitimately differ from ``working_minutes_per_day`` (the calendar's derived
    dominant day length)".

    Independence: the expected days are hand arithmetic on the file's declared setting and its
    stored durations; state.py and float_analysis.py are not consulted for them. The engine's
    minutes and the consistent twins (declared == derived, right today) are preconditions, not
    the oracle. MS Project's own rendering of such a file is UNVERIFIED (no MS Project view
    export in the tree); what settles it is a Duration / Total Slack column export of a file
    whose Hours-per-day option differs from its calendar. A repair needs an ADR choosing the
    display day and naming it on the page. Runtime about 3 s.
    """
    for declared, calendar_minutes in _A0923_CPM_041_CONSISTENT:
        served, want = _a0923_cpm_041_day_figures(declared, calendar_minutes)
        if served != want:
            pytest.fail(
                f"precondition (control): a consistent file ({declared} declared over a "
                f"{calendar_minutes}-minute calendar) no longer serves its own days: {served}"
            )
    wrong: dict[str, str] = {}
    for declared, calendar_minutes in _A0923_CPM_041_MISMATCHED:
        served, want = _a0923_cpm_041_day_figures(declared, calendar_minutes)
        for key, value in served.items():
            if value != want[key]:
                wrong[f"declared {declared} / calendar {calendar_minutes}: {key}"] = (
                    f"served {value} (declared day {want[key]:g}, calendar day "
                    f"{want[key] * declared / calendar_minutes:g})"
                )
    assert not wrong, (
        "every served day figure divides by the calendar's derived working day, not by the "
        f"file's own declared MinutesPerDay (MS Project's Hours per day x 60): {wrong}"
    )


# --- A0923-CPM-042 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    gzip, zipfile, xml.etree.ElementTree as ET, pathlib.Path, typing.Any, pytest,
#              TestClient (fastapi.testclient), SessionState and create_app
#              (schedule_forensics.web.app)
#   constants  REPO, NS (the MSPDI namespace)
#   fixture    the module-level autouse _air_gapped
# Inputs: the committed, non-CUI goldens
# tests/fixtures/golden/ssi_hardfile_24h_uid155/Hard_File_updated{3,4_24h}.mspdi.xml.gz and
# tests/fixtures/mspdi/jacked_up_schedule_1.xml (MS Project's stored fields read with gzip +
# ElementTree, never through the importer), uploaded to the real app; and Acumen Fuse v8.11.0's
# own exports of those saves, committed under 00_REFERENCE_INTAKE/ (read with zipfile +
# ElementTree -- no spreadsheet library). No fixture file; nothing CUI.

_CPM_042_XL = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_CPM_042_RELS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
#: Fuse's 7/15 Analyst workbook (the rev-5 Hard_File_updated3 save + the 24-hour save).
_CPM_042_ANALYST = REPO / "00_REFERENCE_INTAKE" / "acumen_v8.11.0" / "HA296F~1.XLS"
#: Fuse's AlltheProjects Analysis Report (Jacked Up Schedule 1 among its projects).
_CPM_042_ALL = (
    REPO / "00_REFERENCE_INTAKE" / "AlltheProjects Analysis Report - Quick Add Metrics.xlsx"
)
#: MSPDI DurationFormat codes that are elapsed units (em, eh, ed, ew, emo, e%, and the estimated
#: forms) -- Microsoft's DurationFormat table.
_CPM_042_ELAPSED_FORMATS = frozenset(
    {"4", "6", "8", "10", "12", "20", "36", "38", "40", "42", "44", "52"}
)

#: (fixture under tests/fixtures, UID, MS Project's stored fields, Fuse workbook, its detail sheet,
#: Fuse's project label, Fuse's Original Duration cell, hand remaining in elapsed days).
_CPM_042_WITNESSES: tuple[tuple[str, int, dict[str, str], Path, str, str, str, float], ...] = (
    (
        "golden/ssi_hardfile_24h_uid155/Hard_File_updated3.mspdi.xml.gz",
        146,
        {
            "Duration": "PT48H0M0S",
            "DurationFormat": "8",
            "RemainingDuration": "PT48H0M0S",
            "PercentComplete": "0",
        },
        _CPM_042_ANALYST,
        "Hard_File_updated31",
        "Hard_File_updated3",
        "6",
        2.0,
    ),
    (
        "golden/ssi_hardfile_24h_uid155/Hard_File_updated4_24h.mspdi.xml.gz",
        146,
        {
            "Duration": "PT48H0M0S",
            "DurationFormat": "8",
            "RemainingDuration": "PT48H0M0S",
            "PercentComplete": "0",
        },
        _CPM_042_ANALYST,
        "Hard_File_updated4-24-hour2",
        "Hard_File_updated4 24 hour calendar",
        "6",
        2.0,
    ),
    (
        "mspdi/jacked_up_schedule_1.xml",
        20,
        {
            "Duration": "PT768H0M0S",
            "DurationFormat": "8",
            "RemainingDuration": "PT768H0M0S",
            "PercentComplete": "0",
        },
        _CPM_042_ALL,
        "Jacked-Up-Schedule-119",
        "Jacked Up Schedule 1",
        "96",
        32.0,
    ),
)


def _cpm_042_col(ref: str) -> int:
    """``"G50"`` -> 6. Fuse's writer omits ``r`` on consecutive cells and writes it only where it
    skipped a column, so a document-order reader would slide those rows."""
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


def _cpm_042_fuse_grid(book: Path, sheet: str) -> dict[int, dict[str, set[str]]]:
    """Id -> {column: every non-empty cell} over every detail grid (a header row carrying "Id",
    "Project" and "Remaining Duration") of one sheet of a committed Fuse export."""
    if not book.is_file():
        pytest.fail(f"precondition: the committed Fuse export {book.name} is missing")
    with zipfile.ZipFile(book) as z:
        shared = [
            "".join(t.text or "" for t in si.iter(_CPM_042_XL + "t"))
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(_CPM_042_XL + "si")
        ]
        rels = {
            r.get("Id"): r.get("Target") or ""
            for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        }
        targets = [
            rels.get(s.get(_CPM_042_RELS + "id"))
            for s in ET.fromstring(z.read("xl/workbook.xml")).iter(_CPM_042_XL + "sheet")
            if s.get("name") == sheet
        ]
        if len(targets) != 1 or not targets[0]:
            pytest.fail(f"precondition: {book.name} has no single sheet named {sheet!r}")
        target = str(targets[0])
        root = ET.fromstring(z.read(target if target.startswith("xl/") else "xl/" + target))
    grid: dict[int, dict[str, set[str]]] = {}
    head: dict[str, int] | None = None
    for row in root.iter(_CPM_042_XL + "row"):
        vals: list[str | None] = []
        for c in row.iter(_CPM_042_XL + "c"):
            ref = c.get("r")
            if ref is not None:
                vals.extend([None] * (_cpm_042_col(ref) - len(vals)))
            v = c.findtext(_CPM_042_XL + "v")
            vals.append(None if v is None else (shared[int(v)] if c.get("t") == "s" else v))
        if {"Id", "Project", "Remaining Duration"} <= set(vals):
            head = {
                k: vals.index(k)
                for k in ("Id", "Project", "Original Duration", "Remaining Duration")
                if k in vals
            }
            continue
        uid = vals[head["Id"]] if head is not None and head["Id"] < len(vals) else None
        if head is None or uid is None or not uid.isdigit():
            head = None
            continue
        cells = grid.setdefault(int(uid), {})
        for k, i in head.items():
            if i < len(vals) and vals[i] not in (None, ""):
                cells.setdefault(k, set()).add(str(vals[i]))
    if not grid:
        pytest.fail(f"precondition: {book.name} sheet {sheet!r} carries no Id/Remaining grid")
    return grid


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-042: web/state.py:1775 serves an ELAPSED activity's remaining duration over the "
        "project's 480-minute day (no duration_is_elapsed branch, unlike duration_days two lines "
        "above), so the unstarted 2-ed UID 146 (Hard_File_updated3 / updated4_24h) reads "
        "remaining_duration_days 6.0 beside duration_days 2.0 and Jacked_Up_Schedule_1's 32-ed "
        "UID 20 reads 96.0 beside 32.0, where Acumen Fuse's Remaining Duration shows 2 and 32"
    ),
)
def test_a0923_cpm_042_an_elapsed_activitys_remaining_duration_is_served_in_elapsed_days() -> None:
    """A0923-CPM-042 (finder id F-DAY-004) · CPM · T1 (in committed corpus).

    Claim: at 0b45eb28, ``_activity_rows`` serves ``remaining_duration_days`` as
    ``_days(task.remaining_duration_minutes)`` (``src/schedule_forensics/web/state.py:1775``;
    ``_days`` at ``:1744-1745`` divides by the project's ``working_minutes_per_day``, ``:1703``)
    with no ``duration_is_elapsed`` branch, while ``duration_days`` on the same row (``:1772-1773``)
    divides an elapsed duration by 1440. So an elapsed activity's remaining duration is served at
    480/1440 = 3x on every committed witness: the unstarted UID 146 of
    ``tests/fixtures/golden/ssi_hardfile_24h_uid155/Hard_File_updated3.mspdi.xml.gz`` and
    ``.../Hard_File_updated4_24h.mspdi.xml.gz`` (2 ed) reads 6.0 beside ``duration_days`` 2.0;
    UID 20 of ``tests/fixtures/mspdi/jacked_up_schedule_1.xml`` (32 ed) reads 96.0 beside 32.0.
    The row is served by ``GET /api/analysis/{name}`` and read verbatim by the Task Information
    dialog ("Remaining duration", ``web/static/taskinfo.js:118``), the UNRESTRICTED Ask-the-AI data
    table the model computes from ("Rem(d)", ``web/app.py:2723``), the SSI grid rows that copy it
    (``web/ssi.py:262``) and any ``/export/{fmt}/activities/{name}?cols=remaining_duration_days``
    (no UI drill offers that column -- verifier-narrowed). Not claimed: ``baseline_duration_days``
    (the two authorities disagree: Fuse's Baseline Duration shows 6, ADR-0518), non-elapsed
    activities on a task calendar (the row's own ``duration_days`` reads the project day too), and
    the sibling producers that divide by the project day themselves (``web/ssi.py:270-276``
    "remaining_days"; ``web/app.py:8507-8518`` / ``:8561-8580``, the SRA templates).

    Authority: A1 -- Acumen Fuse v8.11.0's own displayed cells, read here with zipfile +
    ElementTree: ``00_REFERENCE_INTAKE/acumen_v8.11.0/HA296F~1.XLS`` sheets "Hard_File_updated31"
    (75 grid rows for Id 146) and "Hard_File_updated4-24-hour2" (87 rows): every one reads
    Remaining Duration "2" (Original Duration "6"); ``00_REFERENCE_INTAKE/AlltheProjects Analysis
    Report - Quick Add Metrics.xlsx`` sheet "Jacked-Up-Schedule-119" (12 rows for Id 20): Remaining
    Duration "32" (Original Duration "96"). MS Project's own encoding, read with ElementTree: UID
    146 ``<Duration>PT48H0M0S`` ``<DurationFormat>8`` ``<RemainingDuration>PT48H0M0S``
    ``<PercentComplete>0``; UID 20 ``PT768H0M0S`` / ``8`` / ``PT768H0M0S`` / ``0``. Microsoft
    Learn, "DurationFormat Element",
    https://learn.microsoft.com/office-project/xml-data-interchange/durationformat-element?view=project-client-2016
    (re-read 2026-09-29): "8 | ed (elapsed days)"; "Elapsed time counts all time, including
    non-working time specified in the project, resource, or task calendar." Hand arithmetic:
    2,880 / 1,440 = 2; 46,080 / 1,440 = 32. A2 -- ``docs/adr/0310-two-time-axes-and-the-labels-
    that-confuse-them.md:67-68``: "3. **An elapsed duration is measured on a 1440-minute day**,
    always, and the discriminator is `Task.duration_is_elapsed`. Any code converting a duration to
    days must branch on it."; ``tests/parity/test_fuse_duration_fields_oracle.py:16-17``:
    "**Remaining Duration** divides by 1440 for an elapsed activity (146: 2,880 → **2**; Jacked Up
    Schedule 1's UID 20: 46,080 → **32**, not 96)".

    Held decisions screened: ADR-0516 decision 3 holds five whole-day FLOAT sentences on the project
    day and ADR-0518 decision 5 holds Float Ratio's axis -- neither is the activity row's remaining
    duration; ADR-0518 records that Fuse's ORIGINAL / BASELINE fields ignore the elapsed flag (6,
    96), which is why the precondition below reads the Original cell beside the Remaining one.
    Siblings, separate classes: A0923-CPM-015 (the counterfactual's reverted-change label) and
    A0923-CPM-017 (drag of an elapsed remaining) -- same unit mix-up, different sites and sketches.

    Oracle independence: every expected figure is Fuse's displayed cell or MS Project's stored
    field, read without the importer; the app is consulted only for the served rows. Control in
    the same test: every other Fuse Remaining Duration cell on the three sheets whose activity is
    non-summary, non-elapsed and on the project calendar (no task calendar of its own) equals the
    served ``remaining_duration_days`` rounded half-to-even to whole days, as Fuse rounds (the
    reader and the harness can pass; a fix that divided every row by 1440 would fail it).
    Runtime ~3 s (three uploads).
    """
    state = SessionState()
    client = TestClient(create_app(state))
    wrong: dict[str, str] = {}
    compared = 0
    for rel, uid, stored, book, sheet, label, fuse_original, hand in _CPM_042_WITNESSES:
        path = REPO / "tests" / "fixtures" / rel
        raw = path.read_bytes()
        if path.suffix == ".gz":
            raw = gzip.decompress(raw)
        root = ET.fromstring(raw)
        project_cal = (root.findtext(NS + "CalendarUID") or "").strip()
        tasks = {(t.findtext(NS + "UID") or "").strip(): t for t in root.iter(NS + "Task")}
        el = tasks.get(str(uid))
        if el is None:
            pytest.fail(f"precondition: {rel} has no <Task> with UID {uid}")
        fields = {k: (el.findtext(NS + k) or "").strip() for k in stored}
        if fields != stored:
            pytest.fail(f"precondition: {rel} UID {uid}'s stored elapsed fields moved: {fields}")

        grid = _cpm_042_fuse_grid(book, sheet)
        cells = grid.get(uid, {})
        want_cells = {
            "Project": {label},
            "Original Duration": {fuse_original},
            "Remaining Duration": {f"{hand:g}"},
        }
        if {k: cells.get(k) for k in want_cells} != want_cells:
            pytest.fail(
                f"precondition: {book.name} sheet {sheet!r} no longer shows Id {uid} as "
                f"{want_cells}: {cells}"
            )

        before = set(state.schedules)
        up = client.post(
            "/upload", files={"files": (path.name.removesuffix(".gz"), raw, "text/xml")}
        )
        added = set(state.schedules) - before
        if up.status_code != 200 or len(added) != 1:
            pytest.fail(f"precondition: uploading {rel} answered {up.status_code}, {added}")
        name = added.pop()
        got = client.get(f"/api/analysis/{name}")
        if got.status_code != 200:
            pytest.fail(f"precondition: /api/analysis/{name} answered {got.status_code}")
        rows: dict[int, dict[str, Any]] = {r["unique_id"]: r for r in got.json()["activities"]}
        row = rows.get(uid)
        if row is None or (row["duration_is_elapsed"], row["duration_days"]) != (True, hand):
            pytest.fail(
                f"precondition: {name} UID {uid} is no longer served elapsed with duration_days "
                f"{hand} (the same row's own 1440 branch): {row}"
            )

        # control: the project-day rows of the same sheet agree with Fuse today
        for other, other_cells in grid.items():
            t = tasks.get(str(other))
            shown = other_cells.get("Remaining Duration")
            served = rows.get(other, {}).get("remaining_duration_days")
            if t is None or shown is None or served is None or other == uid:
                continue
            if (
                (t.findtext(NS + "Summary") or "").strip() == "1"
                or (t.findtext(NS + "DurationFormat") or "").strip() in _CPM_042_ELAPSED_FORMATS
                or (t.findtext(NS + "CalendarUID") or "-1").strip() not in ("-1", project_cal)
            ):
                continue
            compared += 1
            if {str(round(served))} != shown:
                pytest.fail(
                    f"precondition (control): {name} UID {other} (project day, not elapsed) is "
                    f"served remaining {served} where Fuse shows {shown} -- the harness moved"
                )

        if row["remaining_duration_days"] != hand:
            wrong[f"{name} UID {uid}"] = (
                f"served remaining_duration_days {row['remaining_duration_days']} beside "
                f"duration_days {row['duration_days']} (elapsed); Fuse Remaining Duration "
                f"{sorted(cells['Remaining Duration'])}, hand {hand}"
            )
    if compared < 50:
        pytest.fail(f"precondition (control): only {compared} project-day Fuse cells compared")
    assert not wrong, (
        "an elapsed activity's remaining duration is served over the project's working day, not "
        f"in elapsed days as its own duration_days and Acumen Fuse present it: {wrong}"
    )


# --- A0923-CPM-043 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    datetime as dt, pytest, TestClient (fastapi.testclient), quote (urllib.parse),
#              compute_cpm (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi),
#              Calendar (schedule_forensics.model.calendar),
#              SessionState and create_app (schedule_forensics.web.app)
#   fixture    the module-level autouse _air_gapped
# The header needs NO edit: the engine's three PRIVATE day-walkers are imported inside
# _cpm_043_walkers(), so a later rename fails this one test (ImportError, not the marker's
# AssertionError) instead of failing the whole module's collection.
# Inputs: model objects and inline MSPDI text (built below). No fixture file; nothing CUI.

#: MS Project's Standard calendar: Mon-Fri 08:00-12:00 + 13:00-17:00 (480 working min a day).
_CPM_043_STD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))
_CPM_043_MON = dt.datetime(2026, 1, 5, 8, 0)  # Monday: the project start and A's early start


def _cpm_043_walkers() -> tuple[Any, Any, Any]:
    """(``_shift_worked_days``, ``_advance_wall``, ``_retreat_wall``) from engine/cpm.py."""
    from schedule_forensics.engine.cpm import (
        _advance_wall,
        _retreat_wall,
        _shift_worked_days,
    )

    return _shift_worked_days, _advance_wall, _retreat_wall


def _cpm_043_walk(day: dt.date, n: int, weekdays: frozenset[int]) -> dt.date:
    """The oracle: the ``n``-th worked day after (n > 0) / before (n < 0) ``day``, counting
    ``day`` as position 0, by stepping ONE day at a time over the declared working weekdays (no
    holidays, no exceptions on these calendars). Imports nothing from the engine."""
    step = 1 if n > 0 else -1
    cur, left = day, abs(n)
    while left:
        cur += dt.timedelta(days=step)
        if cur.weekday() in weekdays:
            left -= 1
    return cur


def _cpm_043_sweep(shift: Any, working_start: bool) -> list[str]:
    """``_shift_worked_days`` against the per-day walk on a Mon-Fri and a Mon-Sat 8-hour calendar,
    from every day of Sat 2026-01-03 .. Fri 2026-01-16 whose weekday is (``working_start``) or is
    not a working weekday, for n = -15..-1 and 1..15. Returns the mismatches."""
    bad: list[str] = []
    for weekdays in ((0, 1, 2, 3, 4), (0, 1, 2, 3, 4, 5)):
        cal = Calendar(day_segments=((480, 720), (780, 1020)), work_weekdays=weekdays)
        days = frozenset(weekdays)
        for i in range(14):
            day = dt.date(2026, 1, 3) + dt.timedelta(days=i)
            if (day.weekday() in days) != working_start:
                continue
            for n in (*range(-15, 0), *range(1, 16)):
                got, want = shift(cal, day, n), _cpm_043_walk(day, n, days)
                if got != want:
                    bad.append(
                        f"{len(weekdays)}-day week {day:%a %m-%d} {n:+d}: {got} (hand {want})"
                    )
    return bad


def _cpm_043_mspdi(day_types: tuple[int, ...], a_hours: int) -> str:
    """Project calendar Standard (UID 1, Mon-Fri 08-12/13-17), start Mon 2026-01-05 08:00. Task
    calendar UID 2 works 00:00-24:00 (MSPDI 00:00:00 -> 00:00:00) on ``day_types`` (MSPDI
    DayType: 1 = Sunday .. 7 = Saturday). A (UID 1, ``a_hours``) -FS0-> C (UID 2, 24 h), both on
    calendar 2."""

    def week(working: tuple[int, ...], blocks: tuple[tuple[str, str], ...]) -> str:
        out = []
        for d in range(1, 8):
            times = "".join(
                f"<WorkingTime><FromTime>{a}</FromTime><ToTime>{b}</ToTime></WorkingTime>"
                for a, b in blocks
            )
            out.append(
                f"<WeekDay><DayType>{d}</DayType><DayWorking>{int(d in working)}</DayWorking>"
                + (f"<WorkingTimes>{times}</WorkingTimes>" if d in working else "")
                + "</WeekDay>"
            )
        return "".join(out)

    def calendar(uid: int, name: str, days: str) -> str:
        return (
            f"<Calendar><UID>{uid}</UID><Name>{name}</Name><IsBaseCalendar>1</IsBaseCalendar>"
            f"<BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{days}</WeekDays></Calendar>"
        )

    def task(uid: int, name: str, hours: int, pred: int | None) -> str:
        link = (
            f"<PredecessorLink><PredecessorUID>{pred}</PredecessorUID><Type>1</Type>"
            "<LinkLag>0</LinkLag><LagFormat>7</LagFormat></PredecessorLink>"
            if pred is not None
            else ""
        )
        return (
            f"<Task><UID>{uid}</UID><ID>{uid}</ID><Name>{name}</Name>"
            f"<Duration>PT{hours}H0M0S</Duration><DurationFormat>7</DurationFormat>"
            f"<CalendarUID>2</CalendarUID>{link}</Task>"
        )

    standard = week((2, 3, 4, 5, 6), (("08:00:00", "12:00:00"), ("13:00:00", "17:00:00")))
    all_day = week(day_types, (("00:00:00", "00:00:00"),))
    return (
        '<Project xmlns="http://schemas.microsoft.com/project"><Name>a0923-cpm-043</Name>'
        "<ScheduleFromStart>1</ScheduleFromStart><StartDate>2026-01-05T08:00:00</StartDate>"
        "<MinutesPerDay>480</MinutesPerDay><CalendarUID>1</CalendarUID><Calendars>"
        + calendar(1, "Standard", standard)
        + calendar(2, "24 hours", all_day)
        + "</Calendars><Tasks>"
        + task(1, "A", a_hours, None)
        + task(2, "C", 24, 1)
        + "</Tasks></Project>"
    )


def _cpm_043_solve(day_types: tuple[int, ...], a_hours: int) -> tuple[Any, Any]:
    """(A's timing, C's timing) from parse_mspdi_text + compute_cpm."""
    sch = parse_mspdi_text(_cpm_043_mspdi(day_types, a_hours))
    cal2 = next((c for c in sch.calendars if c.uid == 2), None)
    want_days = tuple(sorted((d + 5) % 7 for d in day_types))  # MSPDI 1=Sun -> weekday() 6
    if cal2 is None or (tuple(sorted(cal2.work_weekdays)), cal2.working_minutes_per_day) != (
        want_days,
        1440,
    ):
        pytest.fail(f"precondition: the importer no longer reads calendar 2 as 24 h {want_days}")
    res = compute_cpm(sch)
    return res.timings[1], res.timings[2]


def _cpm_043_served_float(text: str) -> float:
    """A's total_float_days on /api/analysis/<key> for a one-file session."""
    state = SessionState()
    client = TestClient(create_app(state))
    up = client.post("/upload", files={"files": ("a0923_cpm_043.xml", text.encode(), "text/xml")})
    if up.status_code != 200 or len(state.schedules) != 1:
        pytest.fail(f"precondition: upload answered {up.status_code} ({list(state.schedules)})")
    got = client.get(f"/api/analysis/{quote(next(iter(state.schedules)), safe='')}")
    if got.status_code != 200:
        pytest.fail(f"precondition: /api/analysis answered {got.status_code}")
    row = next((a for a in got.json().get("activities", []) if a.get("unique_id") == 1), None)
    if row is None or not isinstance(row.get("total_float_days"), int | float):
        pytest.fail(f"precondition: /api/analysis no longer serves A's total_float_days: {row}")
    return float(row["total_float_days"])


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-043: the fast day-walkers' week jump (_advance_working_days_r / "
        "_retreat_working_days_r, reached through _shift_worked_days_r, engine/cpm.py:1375-1381) "
        "started on a weekday the calendar never works lands on that same non-working weekday "
        "when n is a multiple of the working days per week: _shift_worked_days(Standard, Sat "
        "2026-01-03, +5) = Sat 01-10 (hand Fri 01-09), and a 112 h task on a 24x5 calendar "
        "reads late start Sat 2026-01-03 08:00 and total float -480 (/api/analysis -1.0 d) "
        "where hand arithmetic gives Mon 01-05 08:00 and 0"
    ),
)
def test_a0923_cpm_043_a_day_walk_from_a_non_working_weekday_lands_on_the_nth_worked_day() -> None:
    """A0923-CPM-043 (finder id F-CALG-001) · CPM · T1 (latent: 0 committed instances).

    Claim (verifier P4's scope, adopted): at 0b45eb28 the no-extras branch of
    ``_shift_worked_days_r`` (``engine/cpm.py:1375-1381``) hands its start day to the week-jump
    walkers ``_advance_working_days_r`` / ``_retreat_working_days_r`` (``cpm.py:580-611`` /
    ``:1327-1357``); from a start day whose WEEKDAY the calendar never works, with ``|n|`` a
    multiple of the working days per week, the jump lands on that same non-working weekday one or
    more weeks on. From a working start day it is exact. ``_advance_wall`` (``cpm.py:1726``) and
    ``_retreat_wall`` (``cpm.py:1753``) inherit it: Sat 01-03 10:00 + 2,000 min on Standard ->
    Sat 01-10 09:20 (hand Fri 01-09 09:20); Sun 01-11 12:00 - 2,280 -> Sun 01-04 10:00 (hand Mon
    01-05 10:00). End to end (inline MSPDI below; task calendar 00:00-24:00 Mon-Fri, whose
    Friday end is spelled Sat 00:00): A 112 h -FS0-> C 24 h, start Mon 2026-01-05 08:00 ->
    ``compute_cpm`` gives A late start Sat 2026-01-03 08:00 (before the project start, on a
    non-working day), total float -480 and ``/api/analysis`` total_float_days -1.0. The
    verifier's broadening: A 232 h on the same calendar (-480, LS Sat 01-03 08:00) and A 136 h
    on a 00:00-24:00 Mon-Sat calendar (-480, LS SUNDAY 01-04 08:00).

    Authority: A2 -- the helper's own contract, ``engine/cpm.py:1361-1362``: "The ``n``-th
    worked day after (``n>0``) / before (``n<0``) ``day`` on ``cal``, counting ``day`` itself as
    position 0." and ``cpm.py:1368-1369``: "The week-jump counts weekdays over the half-open
    traversed span, so a non-working start day is handled exactly."; ``cpm.py:1707`` /
    ``:1734``: "Consume ``minutes >= 0`` of working time on ``cal`` forward / backward from
    ``wall``." A1 -- Microsoft, "Total Slack (task field)" (support.microsoft.com, re-read
    2026-09-29 via the Microsoft Learn fetch tool): "Total slack is calculated as the smaller
    value of the Late Finish minus the Early Finish field, and the Late Start minus the Early
    Start field." Hand arithmetic on the declared calendars (the oracle): A = 6,720 working min
    from Mon 08:00 = Mon 08-24 (960) + Tue-Fri 4 x 1,440 -> EF Fri 01-09 24:00; C starts at the
    next working instant Mon 01-12 00:00 and is last, so LS_C = Mon 01-12 00:00 and LF_A is the
    same grid point as Fri 24:00 (Sat/Sun carry no working time); retreating 6,720 from Fri
    24:00 gives Fri, Thu, Wed, Tue (5,760) + Monday's last 960 = Mon 01-05 08:00 = ES_A, so
    TF_A = min(0, 0) = 0. 232 h: two working weeks' worth, the same Mon 08:00 and 0; 136 h on
    Mon-Sat: Mon 16 h + Tue-Sat 5 x 24 h -> EF Sat 24:00, the same Mon 08:00 and 0. Helpers:
    Sat 01-03 +5 worked days = Mon5 Tue6 Wed7 Thu8 Fri9; Sat 10:00 + 2,000 = Mon-Thu 1,920 + 80
    from Fri 08:00 -> 09:20; Sun 01-11 12:00 - 2,280 = Fri-Tue 1,920 + Monday's last 360 (13-17
    = 240, 10-12 = 120) -> Mon 10:00. ``cpm.py:147-148``: float may be negative for "an imposed
    finish, or a violated cap / deadline / pin" -- none here.

    Independence: the sweep's oracle ``_cpm_043_walk`` steps one day at a time over the declared
    weekdays and imports nothing from the engine; the end-to-end values are hand arithmetic and
    Microsoft's definition. Controls (preconditions): from WORKING start days the same helpers
    and the same sweep are exact today; A's forward pass and C's own dates are right; the same
    network with A 88 h (4 working days -- not a multiple of 5) or on a 00:00-24:00 SEVEN-day
    calendar (no non-working weekday) gives LS Mon 08:00 and TF 0 today.
    """
    shift, advance, retreat = _cpm_043_walkers()
    controls = {
        "shift Mon 01-05 +5": (shift(_CPM_043_STD, dt.date(2026, 1, 5), 5), dt.date(2026, 1, 12)),
        "advance Fri 01-09 17:00 +2000": (
            advance(dt.datetime(2026, 1, 9, 17, 0), 2000, _CPM_043_STD, 480),
            dt.datetime(2026, 1, 16, 9, 20),
        ),
        "retreat Mon 01-12 08:00 -2280": (
            retreat(dt.datetime(2026, 1, 12, 8, 0), 2280, _CPM_043_STD, 480),
            dt.datetime(2026, 1, 5, 10, 0),
        ),
    }
    moved = {k: v for k, v in controls.items() if v[0] != v[1]}
    if moved:
        pytest.fail(
            f"precondition (control): a walk from a working day is no longer exact: {moved}"
        )
    sweep_control = _cpm_043_sweep(shift, working_start=True)
    if sweep_control:
        pytest.fail(f"precondition (control): working-start sweep mismatches {sweep_control[:3]}")
    controls_e2e: tuple[tuple[tuple[int, ...], int], ...] = (
        ((2, 3, 4, 5, 6), 88),
        ((1, 2, 3, 4, 5, 6, 7), 112),
    )
    for day_types, hours in controls_e2e:
        a, _ = _cpm_043_solve(day_types, hours)
        if (a.late_start_wall, a.total_float) != (_CPM_043_MON, 0):
            pytest.fail(f"precondition (control): {hours} h on days {day_types} now gives {a}")

    wrong: dict[str, str] = {}
    helpers = {
        "_shift_worked_days(Standard, Sat 01-03, +5)": (
            shift(_CPM_043_STD, dt.date(2026, 1, 3), 5),
            dt.date(2026, 1, 9),
        ),
        "_shift_worked_days(Standard, Sun 01-11, -5)": (
            shift(_CPM_043_STD, dt.date(2026, 1, 11), -5),
            dt.date(2026, 1, 5),
        ),
        "_advance_wall(Sat 01-03 10:00, 2000, Standard)": (
            advance(dt.datetime(2026, 1, 3, 10, 0), 2000, _CPM_043_STD, 480),
            dt.datetime(2026, 1, 9, 9, 20),
        ),
        "_retreat_wall(Sun 01-11 12:00, 2280, Standard)": (
            retreat(dt.datetime(2026, 1, 11, 12, 0), 2280, _CPM_043_STD, 480),
            dt.datetime(2026, 1, 5, 10, 0),
        ),
    }
    wrong.update({k: f"{got} (hand {want})" for k, (got, want) in helpers.items() if got != want})
    sweep = _cpm_043_sweep(shift, working_start=False)
    if sweep:
        wrong["per-day sweep from non-working start days"] = f"{len(sweep)} wrong, e.g. {sweep[:2]}"
    witnesses: dict[str, tuple[tuple[int, ...], int, dt.datetime]] = {
        "24x5, A 112 h": ((2, 3, 4, 5, 6), 112, dt.datetime(2026, 1, 12, 0, 0)),
        "24x5, A 232 h": ((2, 3, 4, 5, 6), 232, dt.datetime(2026, 1, 19, 0, 0)),
        "24x6 Mon-Sat, A 136 h": ((2, 3, 4, 5, 6, 7), 136, dt.datetime(2026, 1, 12, 0, 0)),
    }
    for name, (day_types, hours, c_start) in witnesses.items():
        a, c = _cpm_043_solve(day_types, hours)
        if (a.early_start_wall, c.early_start_wall, c.late_start_wall, c.total_float) != (
            _CPM_043_MON,
            c_start,
            c_start,
            0,
        ):
            pytest.fail(f"precondition: {name}: the forward pass or C moved: {a} {c}")
        if (a.late_start_wall, a.total_float) != (_CPM_043_MON, 0):
            wrong[f"{name}: A (late start, total float)"] = (
                f"{a.late_start_wall:%a %Y-%m-%d %H:%M}, {a.total_float} (hand Mon 2026-01-05 "
                "08:00, 0)"
            )
    served = _cpm_043_served_float(_cpm_043_mspdi((2, 3, 4, 5, 6), 112))
    if served != 0.0:
        wrong["/api/analysis 24x5 A 112 h: total_float_days"] = f"{served} (hand 0.0)"
    assert not wrong, (
        "a day walk that starts on a weekday the calendar never works does not land on the n-th "
        f"worked day, so a zero-float activity reads negative float: {wrong}"
    )


# --- A0923-CPM-044 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    datetime as dt, pytest, typing.Any,
#              compute_cpm (schedule_forensics.engine.cpm),
#              Calendar (schedule_forensics.model.calendar),
#              Relationship, RelationshipType (schedule_forensics.model.relationship),
#              Schedule (schedule_forensics.model.schedule), Task (schedule_forensics.model.task)
#   fixture    the module-level autouse _air_gapped
# Input: model objects built below. No fixture file; nothing CUI.

#: MS Project's Standard day as minutes-from-midnight blocks: 08:00-12:00 + 13:00-17:00.
_A0923_CPM_044_STD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))
_A0923_CPM_044_24H = Calendar(
    uid=4, name="24 Hours", working_minutes_per_day=1440, work_weekdays=(0, 1, 2, 3, 4, 5, 6)
)
_A0923_CPM_044_MON = dt.datetime(2026, 1, 5, 8, 0)  # Monday
_A0923_CPM_044_REL = {
    "FS": RelationshipType.FS,
    "FF": RelationshipType.FF,
    "SF": RelationshipType.SF,
}

#: One network: (P's axis "24h" / "elapsed" / "project", the P -> S link type, its lag, P's
#: minutes, R's minutes (SF rows: R -FS0-> P places P's start) or None, Q's minutes).
_A0923Cpm044Net = tuple[str, str, int, int, int | None, int]


def _a0923_cpm_044_task(kind: str, uid: int, name: str, minutes: int) -> Task:
    """``kind`` "24h" -> on the '24 Hours' task calendar; "elapsed" -> an elapsed duration;
    "project" -> on the project (Standard) calendar."""
    if kind == "24h":
        return Task(unique_id=uid, name=name, duration_minutes=minutes, calendar_uid=4)
    if kind == "elapsed":
        return Task(unique_id=uid, name=name, duration_minutes=minutes, duration_is_elapsed=True)
    return Task(unique_id=uid, name=name, duration_minutes=minutes)


def _a0923_cpm_044_solve(net: _A0923Cpm044Net, extra: int = 0) -> Any:
    """Q (UID 4, Standard) -FS0-> S (UID 3, 480 min, Standard); P (UID 2) -``rel``+``lag``-> S;
    on SF rows R (UID 5, P's axis) -FS0-> P. ``extra`` lengthens P (or R, on SF rows) -- the
    slip of P's finish (or start). No constraint, deadline, pin, delay or progress anywhere."""
    kind, rel, lag, p_min, r_min, q_min = net
    tasks = [
        _a0923_cpm_044_task(kind, 2, "P", p_min + (0 if r_min is not None else extra)),
        Task(unique_id=3, name="S", duration_minutes=480),
        Task(unique_id=4, name="Q", duration_minutes=q_min),
    ]
    links = [
        Relationship(predecessor_id=4, successor_id=3),
        Relationship(
            predecessor_id=2, successor_id=3, type=_A0923_CPM_044_REL[rel], lag_minutes=lag
        ),
    ]
    if r_min is not None:
        tasks.append(_a0923_cpm_044_task(kind, 5, "R", r_min + extra))
        links.append(Relationship(predecessor_id=5, successor_id=2))
    return compute_cpm(
        Schedule(
            name="f-twin-001",
            project_start=_A0923_CPM_044_MON,
            calendar=_A0923_CPM_044_STD,
            calendars=(_A0923_CPM_044_STD, _A0923_CPM_044_24H),
            tasks=tuple(tasks),
            relationships=tuple(links),
        )
    )


def _a0923_cpm_044_slip(net: _A0923Cpm044Net) -> int:
    """THE ORACLE (Microsoft's Total Slack definition, measured on the FORWARD pass only): the
    largest slip of P (minutes on P's own axis) that leaves the project finish AND S's early
    finish unchanged, offset and wall. S is P's only successor and finishes the project, so the
    same number is P's free slack. Lengthening a task cannot pull a finish earlier, so a
    bisection over [0, 4800] is exact."""

    def key(extra: int) -> tuple[object, ...]:
        res = _a0923_cpm_044_solve(net, extra)
        s = res.timings[3]
        return (res.project_finish, res.project_finish_wall, s.early_finish, s.early_finish_wall)

    base = key(0)
    lo, hi = 0, 4800
    if key(hi) == base:
        pytest.fail(f"precondition ({net}): a 4,800-minute slip of P no longer moves the finish")
    while hi - lo > 1:  # invariant: lo keeps the finish, hi moves it
        mid = (lo + hi) // 2
        lo, hi = (mid, hi) if key(mid) == base else (lo, mid)
    return lo


#: (label, network, hand slip, hand late instant of P -- LF for FF rows, LS for SF rows -- or
#: None where only the SIGN is asserted): the claim's cells, as the verifier reproduced them.
_A0923_CPM_044_CASES: tuple[tuple[str, _A0923Cpm044Net, int, dt.datetime | None], ...] = (
    (
        "FF+480, P 600 min on 24 Hours (need on a DAY boundary)",
        ("24h", "FF", 480, 600, None, 480),
        840,
        dt.datetime(2026, 1, 6, 8, 0),
    ),
    (
        "FF+480, P 600 ELAPSED min (need on a DAY boundary)",
        ("elapsed", "FF", 480, 600, None, 480),
        840,
        dt.datetime(2026, 1, 6, 8, 0),
    ),
    (
        "FF+720, P 242 min on 24 Hours (need on the LUNCH boundary)",
        ("24h", "FF", 720, 242, None, 480),
        58,
        dt.datetime(2026, 1, 5, 13, 0),
    ),
    (
        "FF+720, P 242 ELAPSED min (need on the LUNCH boundary)",
        ("elapsed", "FF", 720, 242, None, 480),
        58,
        dt.datetime(2026, 1, 5, 13, 0),
    ),
    (
        "SF+720, R 242 puts P's start Mon 12:02 (need on the LUNCH boundary)",
        ("24h", "SF", 720, 60, 242, 480),
        58,
        dt.datetime(2026, 1, 5, 13, 0),
    ),
    (
        "SF+480, R 600 puts P's start Mon 18:00 (need on a DAY boundary; sign only)",
        ("24h", "SF", 480, 60, 600, 480),
        840,
        None,
    ),
)
#: Controls the engine gets right today (label, network, hand slip = total float): P on the
#: PROJECT calendar; a need MID-block (13:20); the same day-boundary need offset reached through
#: an FS link (the start-role rendering); and a lag-0 FF from the same wall-path P.
_A0923_CPM_044_CONTROLS: tuple[tuple[str, _A0923Cpm044Net, int], ...] = (
    ("control: FF+720, P 242 min on Standard", ("project", "FF", 720, 242, None, 480), 0),
    ("control: FF+700, P 242 min on 24 Hours (need 13:20)", ("24h", "FF", 700, 242, None, 480), 78),
    ("control: FS+480, P 600 min on 24 Hours, Q 960", ("24h", "FS", 480, 600, None, 960), 840),
    ("control: FF+0, P 600 min on 24 Hours", ("24h", "FF", 0, 600, None, 480), 1380),
)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-044: a LAGGED FF / SF need from a wall-path predecessor is rendered by "
        "_offset_to_wall(role='finish') (cpm.py:2954; free-float twin :3204), the EARLIER "
        "spelling of the offset the forward pass reads at its LATER spelling, so P (600 min on "
        "a 24-hour calendar or elapsed) -FF+480-> S reads total and free float -60 and critical "
        "where it can slip 840 (hand LF Tue 08:00); on the lunch boundary -2 for +58"
    ),
)
def test_a0923_cpm_044_a_lagged_ff_or_sf_need_at_a_boundary_is_its_later_spelling() -> None:
    """A0923-CPM-044 (finder id F-TWIN-001) · CPM · T1 (latent: the one lagged FF from a
    wall-path predecessor in the 44-file corpus is non-binding; 0 activities move).

    Claim (as verified by P5): at 0b45eb28, P (UID 2, 600 min on a '24 Hours' task calendar, or
    600 ELAPSED min) -FF+480-> S (UID 3, 480 min, Standard 08-12/13-17) with Q (UID 4, 480 min)
    -FS0-> S, start Mon 2026-01-05 08:00, no constraint / deadline / pin, via ``compute_cpm``
    gives P total float -60, free float -60, ``is_critical`` True and late finish Mon 01-05
    17:00 (P's early finish is Mon 18:00; its late start 07:00 is before the project start);
    P may finish as late as Tue 01-06 08:00 without moving S or the project finish (+840). On
    the LUNCH boundary (P 242 min -FF+720-> S) it reads -2, LF 12:00, where P may slip 58 (LF
    13:00); a lagged SF link (the need anchors P's START) reads -2 for +58 on the lunch
    boundary and -60 on the day boundary. Mechanism: ``_succ_lf_wall``'s fallthrough
    (``engine/cpm.py:2954``) and its free-float twin ``_succ_early_finish_wall``
    (``cpm.py:3204``) render a LAGGED finish-type need with ``_offset_to_wall(role="finish")``
    -- the EARLIEST wall spelling of the offset (end of the previous day / end of the morning
    block) -- while the forward pass projects P's instant onto the same offset from its LATEST
    spelling (Mon 18:00 and Tue 08:00 are both offset 480 of the Standard axis; 12:02 and
    13:00 both 240). The FS twin (the start role, ``cpm.py:2947``) is already right on the day
    boundary in the same network (the control reads +840).

    Scope (verifier P5's narrowing, adopted): for the SF day-boundary cell the +840 rests on the
    engine's forward pass and hand arithmetic only; MPXJ 16.2.0's MicrosoftScheduler (a
    non-authoritative reimplementation) gives +780 there, so that cell asserts the SIGN only
    (positive float, not critical). MPXJ gives exactly +840 and +58 for the FF cells. Lag-0 FF
    is NOT affected (1380 = the forward-pass slip; a control here).

    Distinct from A0923-CPM-034 (the START role returning a block END at an INTERNAL boundary,
    ``cpm.py:2947`` / ``:3168``): here the site picks the FINISH role, and the day-boundary
    half cannot be reached by CPM-034's fix (``_snap_start_role`` on the start-role rendering
    leaves every cell here red). Distinct from A0923-CPM-028 (a lag-0 link into an un-carried
    milestone; its fix abstains on any lagged need) and A0923-CPM-033 (a lagged START-type
    need into a leveled successor).

    Authority: A1 -- Microsoft Support, "Total Slack (task field)",
    https://support.microsoft.com/en-us/office/total-slack-task-field-55dacfda-95bc-469c-9cc9-b1454b8df42c
    (retrieved 2026-09-29 by the finder): "The Total Slack field contains the amount of time a
    task's finish date can be delayed without delaying the project's finish date." and
    "Negative slack indicates that there is not enough time scheduled for the task and is
    usually caused by constraint dates." The oracle (``_a0923_cpm_044_slip``) measures exactly
    that on the FORWARD pass, which the claim does not dispute; the engine's float convention
    is that slip or one minute more. Hand arithmetic under the documented lag rule
    (``engine/cpm.py:18-20``: "Cross-calendar link **lag** is applied on the PROJECT axis
    (documented approximation ..."): P finishes Mon 18:00 (non-working on Standard) -> the
    480-min lag counts from Tue 08:00 -> Tue 17:00 = S's own finish; P finishing Tue 08:00 ->
    Tue 17:00 (S unmoved); Tue 08:01 -> Wed 08:01 (S delayed) => LF_P = Tue 08:00, TF on P's
    24-hour axis = 14 h = 840 (free float the same: S is P's only successor). Lunch: P 12:02
    (void on Standard) -> the lag counts from 13:00, +720 -> Tue 17:00; P may finish up to
    13:00 -> +58. A2 -- ``engine/cpm.py:147-148``: "**Total float may be negative** (an
    imposed finish, or a violated cap / deadline / pin)." -- none exists here.

    Independence: the slip oracle uses only the forward pass (project finish and S's early
    finish); the hand values use only the declared calendars and the documented lag rule; no
    backward-pass output produces an expectation. MS Project's own values for this shape are
    UNVERIFIED by observation (no committed save carries a binding lagged FF / SF from a
    wall-path predecessor); an MS Project recalculation of the 3-task input would settle them.
    Controls (preconditions): P on the project calendar (0), a mid-block need (78), the FS
    start-role twin (840) and a lag-0 FF (1380) already sit in the oracle's band; the forward
    slips equal the hand values.
    """
    for label, net, hand in _A0923_CPM_044_CONTROLS:
        slip = _a0923_cpm_044_slip(net)
        tf = _a0923_cpm_044_solve(net).timings[2].total_float
        if slip != hand or not slip <= tf <= slip + 1:
            pytest.fail(f"precondition ({label}): TF {tf}, forward slip {slip} (hand {hand})")

    wrong: dict[str, str] = {}
    for label, net, hand, late in _A0923_CPM_044_CASES:
        slip = _a0923_cpm_044_slip(net)
        if slip != hand:
            pytest.fail(f"precondition ({label}): the forward pass lets P slip {slip}, not {hand}")
        p = _a0923_cpm_044_solve(net).timings[2]
        got = (p.total_float, p.free_float, p.is_critical)
        if late is None:  # verifier-narrowed: the sign only
            if not (p.total_float > 0 and p.free_float > 0 and not p.is_critical):
                wrong[label] = f"(TF, FF, critical) {got}; P can slip {slip} (positive, False)"
            continue
        wall = p.late_finish_wall if net[1] == "FF" else p.late_start_wall
        in_band = all(slip <= f <= slip + 1 for f in (p.total_float, p.free_float))
        if not in_band or p.is_critical or wall != late:
            wrong[label] = (
                f"(TF, FF, critical) {got}, late {'finish' if net[1] == 'FF' else 'start'} "
                f"{wall}; P can slip {slip} (hand {late:%a %m-%d %H:%M}, not critical)"
            )
    assert not wrong, (
        "a lagged FF / SF need from a wall-path predecessor is rendered at the EARLIER spelling "
        f"of the boundary the forward pass reads at the LATER one: {wrong}"
    )


# --- A0923-CPM-045 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    html, io, re, zipfile, pytest, TestClient (fastapi.testclient),
#              compute_cpm (schedule_forensics.engine.cpm),
#              parse_mspdi_text (schedule_forensics.importers.mspdi),
#              SessionState and create_app (schedule_forensics.web.app)
#   the engine entry point under test, ``compute_path_evolution``
#              (schedule_forensics.engine.path_evolution), is imported inside
#              ``_a0923_cpm_045_engine`` so the fragment runs exactly as appended (the module
#              header does not import it); the integrator may hoist it into the header.
#   fixture    the module-level autouse _air_gapped
# Input: inline MSPDI text (built below), two versions. No fixture file; nothing CUI.

#: UIDs: A (2 d -> 5 d) -FS0-> summary S{B 1 d, C 1 d}; C -FS0-> D (1 d); X (5 d) -FS0-> D.
#: C is the unchanged activity whose entry onto the critical path is attributed; D is the focus
#: (Target UID 5) whose "driving path to focus" list is read.
(
    _A0923_CPM_045_A,
    _A0923_CPM_045_S,
    _A0923_CPM_045_B,
    _A0923_CPM_045_C,
    _A0923_CPM_045_D,
    _A0923_CPM_045_X,
) = (1, 2, 3, 4, 5, 6)

#: What every surface must say of C -- the engine's OWN sentence on the children-logic control
#: (``path_evolution.py:285-288``, A's early finish Tue 03-03 -> Fri 03-06 = +3 calendar days) --
#: and list for D: D plus its transitive predecessors on the CPM's lowered edges.
_A0923_CPM_045_WANT_DETAIL = (
    "Unchanged here — became critical when upstream 'A' (UID 1) finished 3d later, consuming "
    "this activity's float."
)
_A0923_CPM_045_WANT_PATH = [_A0923_CPM_045_A, _A0923_CPM_045_C, _A0923_CPM_045_D, _A0923_CPM_045_X]


def _a0923_cpm_045_mspdi(a_days: int, on_children: bool, status: str) -> str:
    """One version as an MS Project-shaped MSPDI: Standard calendar (Mon-Fri 08-12 / 13-17),
    start Mon 2026-03-02 08:00, WBS = OutlineNumber (the hierarchy the ADR-0043 lowering reads),
    no stored dates, ``status`` as the data date that orders the versions. ``on_children=False``
    (the defect input): A's logic sits on the SUMMARY S. ``True`` (the control): the identical
    network with A's logic written on S's children B and C -- exactly the edge set the CPM
    lowers the summary link to."""
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
    a, s, b, c, d, x = (
        _A0923_CPM_045_A,
        _A0923_CPM_045_S,
        _A0923_CPM_045_B,
        _A0923_CPM_045_C,
        _A0923_CPM_045_D,
        _A0923_CPM_045_X,
    )
    links = (((a, b), (a, c)) if on_children else ((a, s),)) + ((c, d), (x, d))
    preds: dict[int, list[int]] = {}
    for p, q in links:
        preds.setdefault(q, []).append(p)
    rows = (
        (a, "A", "1", 8 * a_days, 0),
        (s, "S", "2", 8, 1),
        (b, "B", "2.1", 8, 0),
        (c, "C", "2.2", 8, 0),
        (d, "D", "3", 8, 0),
        (x, "X", "4", 40, 0),
    )
    tasks = "".join(
        f"<Task><UID>{uid}</UID><ID>{uid}</ID><Name>{name}</Name><WBS>{wbs}</WBS>"
        f"<OutlineNumber>{wbs}</OutlineNumber><OutlineLevel>{wbs.count('.') + 1}</OutlineLevel>"
        f"<Summary>{summary}</Summary><Duration>PT{hours}H0M0S</Duration>"
        "<DurationFormat>7</DurationFormat><PercentComplete>0</PercentComplete>"
        + "".join(
            f"<PredecessorLink><PredecessorUID>{p}</PredecessorUID><Type>1</Type>"
            "<LinkLag>0</LinkLag><LagFormat>7</LagFormat></PredecessorLink>"
            for p in preds.get(uid, ())
        )
        + "</Task>"
        for uid, name, wbs, hours, summary in rows
    )
    return (
        '<Project xmlns="http://schemas.microsoft.com/project"><Name>EvoSum</Name>'
        "<ScheduleFromStart>1</ScheduleFromStart><StartDate>2026-03-02T08:00:00</StartDate>"
        f"<StatusDate>{status}</StatusDate><CalendarUID>1</CalendarUID>"
        "<Calendars><Calendar><UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>"
        f"<BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{days}</WeekDays></Calendar></Calendars>"
        f"<Tasks>{tasks}</Tasks></Project>"
    )


def _a0923_cpm_045_pair(on_children: bool) -> tuple[str, str]:
    """The two versions, oldest first: v1 (A 2 d, data date Mon 03-02) and v2 (A 5 d, data date
    Tue 03-03) -- only A's duration changes, so the UNCHANGED C enters the critical path."""
    return (
        _a0923_cpm_045_mspdi(2, on_children, "2026-03-02T08:00:00"),
        _a0923_cpm_045_mspdi(5, on_children, "2026-03-03T08:00:00"),
    )


def _a0923_cpm_045_engine(
    on_children: bool,
) -> tuple[dict[str, object], dict[int, tuple[int, int, int]], int]:
    """The engine's own reading of the pair: C's entered-reason detail from
    ``compute_path_evolution`` (untargeted -- the effective critical set), v2's CPM (ES, EF, TF)
    per activity and v1's C total float (the preconditions that the CPM honours S's logic)."""
    from schedule_forensics.engine.path_evolution import compute_path_evolution

    v1, v2 = _a0923_cpm_045_pair(on_children)
    s1, s2 = parse_mspdi_text(v1), parse_mspdi_text(v2)
    c1, c2 = compute_cpm(s1), compute_cpm(s2)
    snap = compute_path_evolution([s1, s2], [c1, c2]).snapshots[1]
    if _A0923_CPM_045_C not in snap.entered:
        pytest.fail(f"precondition: C did not enter the critical path (entered {snap.entered})")
    detail = next(ch.detail for ch in snap.entered_changes if ch.uid == _A0923_CPM_045_C)
    return (
        {"engine: C's entered reason detail": detail},
        {uid: (t.early_start, t.early_finish, t.total_float) for uid, t in c2.timings.items()},
        c1.timings[_A0923_CPM_045_C].total_float,
    )


def _a0923_cpm_045_served(on_children: bool) -> dict[str, object]:
    """The served app on the same two files: the stepper's feed ``/api/evolution?target=5``
    (C's reason detail and the "driving path to focus" list ``path_to_target`` of both
    snapshots), the ``/evolution`` page (which embeds that feed for whatif.js / path_evolution.js
    -- the dash is JSON-escaped there, so the sentence is matched without it) and the
    ``/export/xlsx/evolution`` workbook (C's reason cell, an inline string)."""
    state = SessionState()
    client = TestClient(create_app(state))
    names = ("EvoSum_v1.xml", "EvoSum_v2.xml")
    for name, text in zip(names, _a0923_cpm_045_pair(on_children), strict=True):
        up = client.post("/upload", files={"files": (name, text.encode(), "text/xml")})
        if up.status_code != 200:
            pytest.fail(f"precondition: upload of {name} answered {up.status_code}")
    if list(state.schedules) != ["EvoSum_v1", "EvoSum_v2"]:
        pytest.fail(f"precondition: loaded {list(state.schedules)}")
    feed = client.get("/api/evolution", params={"target": str(_A0923_CPM_045_D)})
    if feed.status_code != 200:
        pytest.fail(f"precondition: /api/evolution?target=5 answered {feed.status_code}")
    snaps = feed.json()["snapshots"]
    c_rows = [r for r in snaps[-1]["critical_rows"] if r.get("uid") == _A0923_CPM_045_C]
    if len(snaps) != 2 or len(c_rows) != 1:
        pytest.fail(f"precondition: {len(snaps)} snapshots; C rows on the last one: {c_rows}")
    page = client.get("/evolution")
    if page.status_code != 200:
        pytest.fail(f"precondition: /evolution answered {page.status_code}")
    page_text = html.unescape(page.text)
    book = client.get("/export/xlsx/evolution")
    if book.status_code != 200:
        pytest.fail(f"precondition: /export/xlsx/evolution answered {book.status_code}")
    with zipfile.ZipFile(io.BytesIO(book.content)) as z:
        sheets = "".join(
            z.read(n).decode("utf-8", "replace")
            for n in z.namelist()
            if n.startswith("xl/worksheets/")
        )
    # Only C enters unchanged, so exactly one ``slack_consumed`` sentence (either of the two
    # shapes at path_evolution.py:285-296) is expected in the workbook.
    sentence = re.compile(r"Unchanged here — (?:became critical|float consumed)[^<]*")
    slack_cells = sorted(set(sentence.findall(html.unescape(sheets))))
    return {
        "/api/evolution?target=5: C's reason detail": c_rows[0].get("detail"),
        "/api/evolution?target=5: path_to_target (v1)": snaps[0].get("path_to_target"),
        "/api/evolution?target=5: path_to_target (v2)": snaps[1].get("path_to_target"),
        "/evolution: the embedded feed (names upstream A, names sibling B)": (
            "became critical when upstream 'A' (UID 1) finished 3d later" in page_text,
            "largest: 'B' UID 3" in page_text,
        ),
        "/export/xlsx/evolution: C's reason cell(s)": slack_cells,
    }


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-045: the CPM lowers logic on a summary onto its children (ADR-0043) but the "
        "evolution reason walk (path_evolution._predecessors) and the 'driving path to focus' "
        "list (_evolution_data.path_to_target) walk the RAW links, so on A -FS0-> S{B, C}, "
        "C -> D, X -> D where only A lengthens (2 d -> 5 d) the unchanged C's reason names its "
        "sibling B (\"largest: 'B' UID 3, +5d\") instead of its upstream driver A, and "
        "path_to_target(D) is [4, 5, 6] without A -- on the engine, /api/evolution, /evolution "
        "and /export/xlsx/evolution"
    ),
)
def test_a0923_cpm_045_logic_on_a_summary_reaches_the_evolution_reason_and_the_focus_path() -> None:
    """A0923-CPM-045 (finder id F-TWIN-002) · CPM · T2 (latent: 0 summary-touching links in the
    44-file corpus and in the 42 tracked MSPDI documents; no figure changes -- a misattribution
    and a filter that hides a true driver).

    Claim (as verified by P5): at 0b45eb28, two MSPDI versions (Standard 08-12 / 13-17, start
    Mon 2026-03-02 08:00, WBS = outline) of A (UID 1) -FS0-> summary S (UID 2){B (3) 1 d, C (4)
    1 d}, C -FS0-> D (5) 1 d, X (6) 5 d -FS0-> D, where only A's duration changes (2 d -> 5 d)
    so that the UNCHANGED C enters the critical path, yield -- on the engine's
    ``compute_path_evolution``, on ``/api/evolution?target=5``, on the ``/evolution`` page's
    embedded feed and in ``/export/xlsx/evolution`` -- C's reason "Unchanged here — float
    consumed by slippage elsewhere (largest: 'B' UID 3, +5d)." (its SIBLING B, which has no
    logic to C) and, under Target UID 5, ``path_to_target`` = [4, 5, 6] without A on BOTH
    snapshots, while ``compute_cpm`` schedules A as C's driver (v2: C ES 2400 = A EF 2400, A
    TF 0). Mechanism: ``engine/path_evolution.py:156-161`` ``_predecessors`` (``:159 for r in
    schedule.relationships``) and ``web/evolution.py:971-983`` ``path_to_target`` (``:979 for r
    in schedules[idx].relationships``) iterate the RAW links instead of the CPM's ADR-0043
    lowered edge set (``summary_logic.lower_summary_relationships``, which gives A -> C) --
    A0923-CPM-032's root cause at two further sites. Verifier precisions: the ``/evolution``
    page carries the sentence in its served JSON (drawn client-side by ``whatif.js:179``
    'Detail' and ``path_evolution.js:358`` ``setOf(snap.path_to_target)``), not in the
    server-rendered text (no Chromium render: the visible cell is UNVERIFIED); and under a
    target the stepper's ``entered`` set comes from CPM-032's raw-link driving trace (A absent)
    -- NOT asserted here (that class's reproducer owns it); C's reason is the same with or
    without a target.

    Authority: A2 -- the repository's own contract, independent of the walk under test:
    ``engine/path_evolution.py:217-219`` "The transitive predecessor of ``uid`` with the largest
    positive early-finish slip, as ``(slip_days, predecessor_uid)`` — the upstream activity
    whose slippage most plausibly consumed ``uid``'s float."; ``:170-171`` "``cur_preds`` maps
    successor → its direct predecessors in the current version (to walk an activity's driving
    chain)"; ``:277-279`` "Name that slip (its driving chain first, then the largest slip
    anywhere)"; ``web/evolution.py:972-974`` "the activities that DRIVE it in version ``idx`` —
    the target plus its transitive predecessors — so the \\"driving path to focus\\" filter can
    scope the Gantt"; ``docs/adr/0043-logic-on-summary-tasks.md:14-15`` "MS Project honors logic
    on a summary by applying it to the summary's children". A1 -- Microsoft Learn, "Tasks don't
    schedule as expected in Microsoft Project", Project 2010 item 14, as quoted by
    A0923-CPM-032 (not re-fetched): "Predecessor and Successor relationships assigned to
    summary task can affect sub task of the summary task in addition to the summary task(s)
    that are linked." Hand arithmetic (480 min/day, Mon 03-02 08:00 = 0): v1 A 0..960; the
    lowered A -> B / A -> C hold B, C to 960..1440 (Wed 03-04); X 0..2400; D = max(1440, 2400)
    .. 2880 (Mon 03-09) -> C TF 960, X and D critical. v2 A 0..2400 (Fri 03-06); B, C
    2400..2880 (Mon 03-09); D 2880..3360 (Tue 03-10) -> A TF 0, C TF 0, D TF 0; B and X TF 480.
    Early-finish slips in calendar days: A Tue 03-03 -> Fri 03-06 = +3; B and C +5. C's driving
    chain on the lowered edges is {A} -> "upstream 'A' (UID 1) finished 3d later"; on the raw
    links C has no predecessor, so the fallback names the largest slip anywhere: B, +5d.

    Independence: the expectation is the engine's OWN reading of the same network with A's
    logic written on B and C (the control -- byte-for-byte the CPM's lowered edge set), never
    the walk under test; the CPM figures of both spellings are identical (a precondition). NOT
    asserted: the targeted ``entered`` set (CPM-032), the "summary task carries logic" finding,
    and ``path_evolution._links_touching`` (logic added / removed attribution on raw links -- a
    further sibling, not probed).
    """
    engine_claim, cpm_claim, v1_c_tf_claim = _a0923_cpm_045_engine(on_children=False)
    engine_ctrl, cpm_ctrl, v1_c_tf_ctrl = _a0923_cpm_045_engine(on_children=True)
    want_cpm = {
        _A0923_CPM_045_A: (0, 2400, 0),
        _A0923_CPM_045_B: (2400, 2880, 480),
        _A0923_CPM_045_C: (2400, 2880, 0),
        _A0923_CPM_045_D: (2880, 3360, 0),
        _A0923_CPM_045_X: (0, 2400, 480),
    }
    if cpm_claim != want_cpm or cpm_ctrl != want_cpm or (v1_c_tf_claim, v1_c_tf_ctrl) != (960, 960):
        pytest.fail(
            "precondition: the CPM no longer honours S's logic as the children-logic spelling "
            f"(v2 ES, EF, TF) summary-logic {cpm_claim} children-logic {cpm_ctrl}; v1 C TF "
            f"{(v1_c_tf_claim, v1_c_tf_ctrl)}"
        )
    want: dict[str, object] = {
        "engine: C's entered reason detail": _A0923_CPM_045_WANT_DETAIL,
        "/api/evolution?target=5: C's reason detail": _A0923_CPM_045_WANT_DETAIL,
        "/api/evolution?target=5: path_to_target (v1)": _A0923_CPM_045_WANT_PATH,
        "/api/evolution?target=5: path_to_target (v2)": _A0923_CPM_045_WANT_PATH,
        "/evolution: the embedded feed (names upstream A, names sibling B)": (True, False),
        "/export/xlsx/evolution: C's reason cell(s)": [_A0923_CPM_045_WANT_DETAIL],
    }
    got_control = {**engine_ctrl, **_a0923_cpm_045_served(on_children=True)}
    if got_control != want:
        pytest.fail(f"precondition (control): children-logic input {got_control}")

    got = {**engine_claim, **_a0923_cpm_045_served(on_children=False)}
    wrong = {k: f"{got[k]} (want {v})" for k, v in want.items() if got[k] != v}
    assert not wrong, (
        "logic on summary S is honoured by the CPM (C ES 2400 = A EF, A TF 0) but not by the "
        f"evolution reason walk / the driving-path-to-focus list: {wrong}"
    )


# --- A0923-CPM-046 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py, and on nothing else:
#   imports    datetime as dt, pytest, compute_cpm (schedule_forensics.engine.cpm),
#              Calendar (schedule_forensics.model.calendar),
#              Relationship, RelationshipType (schedule_forensics.model.relationship),
#              Schedule (schedule_forensics.model.schedule), Task (schedule_forensics.model.task)
#   fixture    the module-level autouse _air_gapped
# Input: model objects built below. No fixture file, no Java, no network; nothing CUI.

#: MS Project's Standard day as minutes-from-midnight blocks: 08:00-12:00 + 13:00-17:00.
_A0923_CPM_046_STD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))
_A0923_CPM_046_24H = Calendar(
    uid=4, name="24 Hours", working_minutes_per_day=1440, work_weekdays=(0, 1, 2, 3, 4, 5, 6)
)
_A0923_CPM_046_MON = dt.datetime(2026, 1, 5, 8, 0)  # Monday; P runs Mon 08:00-17:00
_A0923_CPM_046_REL = {
    "FS": RelationshipType.FS,
    "SS": RelationshipType.SS,
    "FF": RelationshipType.FF,
    "SF": RelationshipType.SF,
}


def _a0923_cpm_046_at(day: int, hour: int) -> dt.datetime:
    """January ``day`` 2026 at ``hour``:00 (Mon 5 is the project start)."""
    return dt.datetime(2026, 1, day, hour, 0)


#: (claim link, its lag, the axis-equal twin link, its lag, hand S start (day, hour), hand S
#: finish (day, hour), hand project finish offset). P is 480 contiguous minutes of the project
#: axis, so P.start + (480 + L) == P.finish + L: SS+(480+L) is FS+L and SF+(480+L) is FF+L.
#: S is the last activity, so its finish is also the project finish instant.
_A0923_CPM_046_PAIRS = (
    ("SS", 960, "FS", 480, (6, 17), (7, 1), 960),
    ("SF", 960, "FF", 480, (6, 9), (6, 17), 960),
    ("SS", 480, "FS", 0, (5, 17), (6, 1), 480),
    ("SF", 480, "FF", 0, (5, 9), (5, 17), 480),
    ("SS", 1440, "FS", 960, (7, 17), (8, 1), 1440),
)
#: The out-of-sequence REMAINING-work tail (S started Mon 08:00, Resume Mon 12:00, 240 min
#: remaining): (claim link, lag, twin link, lag, hand S finish (day, hour), hand finish offset).
_A0923_CPM_046_TAIL = (
    ("SS", 960, "FS", 480, (6, 21), 960),
    ("SF", 960, "FF", 480, (6, 17), 960),
)


def _a0923_cpm_046_solve(kind: str, rel: str, lag: int, started: bool = False) -> tuple[Any, Any]:
    """P (UID 2, 480 min, project calendar) -``rel``+``lag``-> S (UID 3, 480 min): ``kind``
    "24h" -> S on the '24 Hours' task calendar; "elapsed" -> an elapsed duration; "project" ->
    S on the project calendar (the fast-path control). ``started``: S began Mon 08:00 (actual),
    Resume Mon 12:00, 240 min remaining at 50 %. Returns (S's timing, the CPMResult)."""
    extra: dict[str, Any] = (
        {
            "actual_start": _A0923_CPM_046_MON,
            "resume": dt.datetime(2026, 1, 5, 12, 0),
            "remaining_duration_minutes": 240,
            "percent_complete": 50.0,
        }
        if started
        else {}
    )
    if kind == "24h":
        s = Task(unique_id=3, name="S", duration_minutes=480, calendar_uid=4, **extra)
    elif kind == "elapsed":
        s = Task(unique_id=3, name="S", duration_minutes=480, duration_is_elapsed=True, **extra)
    else:
        s = Task(unique_id=3, name="S", duration_minutes=480, **extra)
    res = compute_cpm(
        Schedule(
            name="f-twin-003",
            project_start=_A0923_CPM_046_MON,
            calendar=_A0923_CPM_046_STD,
            calendars=(_A0923_CPM_046_STD, _A0923_CPM_046_24H),
            tasks=(Task(unique_id=2, name="P", duration_minutes=480), s),
            relationships=(
                Relationship(
                    predecessor_id=2,
                    successor_id=3,
                    type=_A0923_CPM_046_REL[rel],
                    lag_minutes=lag,
                ),
            ),
        )
    )
    p = res.timings[2]
    if (p.early_start, p.early_finish) != (0, 480):
        pytest.fail(f"precondition: P no longer runs offsets 0..480 (Mon 08:00-17:00): {p}")
    return res.timings[3], res


def _a0923_cpm_046_walls(kind: str, rel: str, lag: int) -> tuple[Any, ...]:
    """(S start wall, S finish wall, project finish offset, project finish wall)."""
    s, res = _a0923_cpm_046_solve(kind, rel, lag)
    return (s.early_start_wall, s.early_finish_wall, res.project_finish, res.project_finish_wall)


def _a0923_cpm_046_tail(kind: str, rel: str, lag: int) -> tuple[Any, ...]:
    """(S finish wall, project finish offset, project finish wall) for the started S."""
    s, res = _a0923_cpm_046_solve(kind, rel, lag, started=True)
    if s.early_start_wall != _A0923_CPM_046_MON:
        pytest.fail(f"precondition: the started S no longer starts at its actual: {s}")
    return (s.early_finish_wall, res.project_finish, res.project_finish_wall)


def _a0923_cpm_046_fmt(got: tuple[Any, ...]) -> str:
    return " / ".join(f"{g:%a %m-%d %H:%M}" if isinstance(g, dt.datetime) else str(g) for g in got)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-046: a LAGGED SS / SF forward bound into a wall-path successor is rendered "
        "_offset_to_wall(role='start') (cpm.py:2539 / :2552; out-of-sequence tail twins :2648 / "
        ":2661) -- the NEXT morning at a whole-day offset -- where the axis-equal FS / FF bound "
        "renders role='finish', so P (480 min, Standard) -SS+960-> S (24 h) starts S Wed 08:00 "
        "and finishes the project at 1380 / Wed 16:00 where FS+480 gives Tue 17:00 -> Wed 01:00 "
        "/ 960; SF+960 finishes S Wed 08:00 where FF+480 finishes it Tue 17:00"
    ),
)
def test_a0923_cpm_046_a_lagged_ss_or_sf_bound_at_a_boundary_is_its_earlier_spelling() -> None:
    """A0923-CPM-046 (finder id F-TWIN-003) · CPM · T1 (latent: 0 lagged SS / SF links into a
    wall-path successor in the 44-file corpus) -- the forward mirror of A0923-CPM-044.

    Claim (verifier P5: REPRODUCED, broadened by three encoding pairs): at 0b45eb28, P (UID 2,
    480 min, Standard 08-12/13-17, Mon 2026-01-05 08:00-17:00) linked to S (UID 3, 480 min on a
    '24 Hours' task calendar, or 480 elapsed min), via ``compute_cpm``: SS+960 starts S Wed
    01-07 08:00 and finishes it Wed 16:00 (project finish 1380 / Wed 16:00) where the
    axis-equivalent FS+480 starts it Tue 01-06 17:00 and finishes it Wed 01:00 (960); SF+960
    finishes S Wed 08:00 where FF+480 finishes it Tue 17:00; likewise SS+480 vs FS+0 (Tue
    08:00 vs Mon 17:00), SF+480 vs FF+0 and SS+1440 vs FS+960 -- every lagged SS / SF bound at
    a whole-day multiple lands 15 h (900 min) later than its twin. The same pairs agree on a
    project-calendar S (fast path) and at a mid-block lag (SS+300 = FS-180, Mon 14:00).
    Mechanism: the wall-path forward pass renders a LAGGED SS / SF bound with
    ``_offset_to_wall(role="start")`` (``engine/cpm.py:2539``, ``:2552``; the out-of-sequence
    remaining-work twins ``:2648``, ``:2661``) -- at an exact working-day multiple the NEXT
    morning -- while the lagged FS / FF bounds use ``role="finish"`` (``:2533``, ``:2546``; the
    previous evening). The assembler also executed the tail twins (not in the verifier's
    executed scope): a started S (actual Mon 08:00, Resume Mon 12:00, 240 min remaining)
    finishes Wed 12:00 under SS+960 where FS+480 finishes it Tue 21:00, and Wed 08:00 under
    SF+960 where FF+480 finishes it Tue 17:00.

    Correct: each claim encoding schedules S exactly as its axis-equal twin and as the hand
    arithmetic below. Preconditions (right today, a fix must keep them): every twin
    encoding (FS / FF) equals the hand arithmetic; a project-calendar S reads the same offsets
    under both encodings; a mid-block lag (SS+300 and FS-180) starts S Mon 14:00.

    Authority: A2 -- the engine's own documented lag axis, independent of the four rendering
    lines under test: src/schedule_forensics/engine/cpm.py:18-20 "Cross-calendar link **lag**
    is applied on the PROJECT axis (documented approximation — both oracle files carry only
    zero lags; MS Project's own lag calendar on cross-calendar links is unpinned until an oracle
    exists)." -- so P.finish + 480 and P.start + 960 are ONE axis quantity (P is 480 contiguous
    working minutes); cpm.py:1400-1403 (``_offset_to_wall``): "``role="finish"``: the instant
    where minute ``offset`` ENDS … ``role="start"``: where minute ``offset`` BEGINS — an exact
    multiple lands at the NEXT working day's first block start"; cpm.py:2526 "the pure
    logic+constraint early start, as a wall instant on the task's calendar" -- the EARLIEST
    instant meeting the bounds. docs/adr/0322-the-base-cpm-honors-per-task-calendars.md:68-70
    "Cross-calendar link **lag** stays on the project axis — a documented approximation (both
    oracles carry only zero lags; MSP's lag calendar is unpinned until an oracle exists)."
    Definitional equivalence: FS+L and SS+(480+L) impose the same constraint on S when P is
    480 contiguous minutes of the lag's axis, so they must schedule S identically (the
    redundant/equivalent-link form A0923-CPM-005 / -028 use). Hand arithmetic: Mon 08:00 + 960
    Standard working minutes = Mon 17:00 (480) + Tue 08:00-17:00 (480) -> the 960th minute ENDS
    Tue 17:00; a 24-hour crew starts then and finishes Wed 01:00 (projecting to offset 960);
    finish-type: S finishes Tue 17:00, starts Tue 09:00. The started tail restarts at Tue 17:00
    (after its Resume Mon 12:00) and ends 240 min later, Tue 21:00.

    Why the oracle is independent: hand arithmetic on the declared calendar under the engine's
    documented lag convention; the engine only runs the network (its fast path already treats
    the pairs as equal). The equivalence is exact only under that convention, which ADR-0322
    records as unpinned; MPXJ 16.2.0's MicrosoftScheduler (non-authoritative; lag on the
    SUCCESSOR's 24-h calendar) also never places SS / SF after FS / FF (verifier P5). MS
    Project's own dates for this shape are UNVERIFIED (no committed save carries a lagged SS /
    SF into a wall-path successor); an MS Project save of P -SS+2d-> S (24 Hours) and its
    FS+1d twin would settle it.

    Tier: T1, latent (corpus: 11 lagged SS / SF links, 0 into a wall-path successor; 0 lagged
    SF anywhere) -- when it fires, a wall-path successor's dates and the project finish move by
    up to 15 wall hours (one project working day on the axis) with the link encoding alone.
    """
    at = _a0923_cpm_046_at
    for kind in ("24h", "elapsed"):
        for _rel, _lag, twin, tlag, start, finish, off in _A0923_CPM_046_PAIRS:
            got = _a0923_cpm_046_walls(kind, twin, tlag)
            if got != (at(*start), at(*finish), off, at(*finish)):
                pytest.fail(f"precondition: {kind} {twin}+{tlag} is no longer hand: {got}")
        for _rel, _lag, twin, tlag, finish, off in _A0923_CPM_046_TAIL:
            got = _a0923_cpm_046_tail(kind, twin, tlag)
            if got != (at(*finish), off, at(*finish)):
                pytest.fail(f"precondition: {kind} started {twin}+{tlag} is no longer hand: {got}")
        mid = {_a0923_cpm_046_walls(kind, r, g)[:2] for r, g in (("SS", 300), ("FS", -180))}
        if mid != {(at(5, 14), at(5, 22))}:
            pytest.fail(f"precondition (control): {kind} mid-block SS+300 / FS-180 gives {mid}")
    for rel, lag, twin, tlag, *_hand in _A0923_CPM_046_PAIRS:
        fast = set()
        for r, g in ((rel, lag), (twin, tlag)):
            s, res = _a0923_cpm_046_solve("project", r, g)
            fast.add((s.early_start, s.early_finish, s.early_start_wall, res.project_finish))
        if len(fast) != 1:
            pytest.fail(f"precondition (control): project-calendar S {rel}+{lag} / {twin}: {fast}")

    wrong: dict[str, str] = {}
    for kind in ("24h", "elapsed"):
        for rel, lag, twin, tlag, start, finish, off in _A0923_CPM_046_PAIRS:
            hand = (at(*start), at(*finish), off, at(*finish))
            got = _a0923_cpm_046_walls(kind, rel, lag)
            if got != hand:
                wrong[f"{kind} S {rel}+{lag} (start / finish / finish offset / its wall)"] = (
                    f"{_a0923_cpm_046_fmt(got)} (the {twin}+{tlag} twin and hand: "
                    f"{_a0923_cpm_046_fmt(hand)})"
                )
        for rel, lag, twin, tlag, finish, off in _A0923_CPM_046_TAIL:
            hand = (at(*finish), off, at(*finish))
            got = _a0923_cpm_046_tail(kind, rel, lag)
            if got != hand:
                wrong[f"{kind} started S {rel}+{lag} (finish / finish offset / its wall)"] = (
                    f"{_a0923_cpm_046_fmt(got)} (the {twin}+{tlag} twin and hand: "
                    f"{_a0923_cpm_046_fmt(hand)})"
                )
    assert not wrong, (
        "a lagged SS / SF bound at a whole-day offset schedules a wall-path successor later than "
        f"its axis-equal FS / FF twin (the earliest spelling of the same offset): {wrong}"
    )


# --- A0923-CPM-047 fragment -------------------------------------------------------------------
# Relies on the module header of tests/audit/test_audit_20260923_cpm.py:
#   imports    datetime as dt, pytest, typing.Any,
#              compute_cpm, offset_to_datetime, offset_to_start_datetime
#              (schedule_forensics.engine.cpm), Calendar (model.calendar),
#              Relationship, RelationshipType (model.relationship), Schedule (model.schedule),
#              Task (model.task)
#   fixture    the module-level autouse _air_gapped
# Input: model objects built below. No fixture file; nothing CUI.

#: MS Project's Standard day as minutes-from-midnight blocks: 08:00-12:00 + 13:00-17:00.
_A0923_CPM_047_STD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))
_A0923_CPM_047_24H = Calendar(
    uid=4, name="24 Hours", working_minutes_per_day=1440, work_weekdays=(0, 1, 2, 3, 4, 5, 6)
)
_A0923_CPM_047_MON = dt.datetime(2026, 1, 5, 8, 0)  # Monday
_A0923_CPM_047_REL = {k: RelationshipType[k] for k in ("SS", "SF", "FS")}


def _a0923_cpm_047_solve(
    kind: str, rel: str, q_minutes: int, p_minutes: int, s_minutes: int
) -> tuple[Any, Any]:
    """Q (UID 1, ``q_minutes``, Standard) -FS0-> P (UID 2, ``p_minutes``, Standard) -``rel``0->
    S (UID 3, ``s_minutes``): ``kind`` "24h" -> S on the '24 Hours' task calendar; "elapsed" ->
    an elapsed duration. Start Mon 2026-01-05 08:00 on the Standard project calendar. Returns
    the timings of P and S."""
    if kind == "24h":
        s = Task(unique_id=3, name="S", duration_minutes=s_minutes, calendar_uid=4)
    else:
        s = Task(unique_id=3, name="S", duration_minutes=s_minutes, duration_is_elapsed=True)
    res = compute_cpm(
        Schedule(
            name="f-twin-004",
            project_start=_A0923_CPM_047_MON,
            calendar=_A0923_CPM_047_STD,
            calendars=(_A0923_CPM_047_STD, _A0923_CPM_047_24H),
            tasks=(
                Task(unique_id=1, name="Q", duration_minutes=q_minutes),
                Task(unique_id=2, name="P", duration_minutes=p_minutes),
                s,
            ),
            relationships=(
                Relationship(predecessor_id=1, successor_id=2),
                Relationship(predecessor_id=2, successor_id=3, type=_A0923_CPM_047_REL[rel]),
            ),
        )
    )
    return res.timings[2], res.timings[3]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-CPM-047: a lag-0 SS / SF bound from a project-axis predecessor is rendered by "
        "_pred_start_wall with _offset_to_wall(role='start') (cpm.py:2474), which at an "
        "INTERNAL block boundary returns the block END, so a 24-hour / elapsed successor SS0 "
        "after P (the engine's own P start Mon 13:00) runs 12:00 -> 20:00 with TF 960 (hand "
        "13:00 -> 21:00, 900) and SF0 finishes at 12:00, before P starts (hand 13:00, TF 1380)"
    ),
)
def test_a0923_cpm_047_a_lag0_ss_sf_bound_at_a_block_boundary_is_the_next_block_start() -> None:
    """A0923-CPM-047 (finder id F-TWIN-004) · CPM · T1 (latent: the corpus's 11 lag-0 SS links
    from a project-axis predecessor into a wall-path successor all start mid-block; 0 SF).

    Claim (verifier P5's scope, reproduced as stated): at 0b45eb28, Q (UID 1, 240 min) -FS0-> P
    (UID 2, 480 min, Standard 08-12/13-17) -SS0-> S (UID 3, 480 min on a '24 Hours' task
    calendar, or 480 ELAPSED min), start Mon 2026-01-05 08:00: ``compute_cpm`` gives S Mon 12:00
    -> 20:00, total float 960, while the engine's own rendering of P's start
    (``offset_to_start_datetime``, offset 240) is Mon 13:00 -- S starts an hour before its SS0
    predecessor; with SF0 (S 120 min) S runs 10:00 -> 12:00 and finishes before P starts.
    Mechanism: ``_pred_start_wall``'s offset fallback (``engine/cpm.py:2474``) renders a
    project-axis predecessor's early start with ``_offset_to_wall(role="start")``, which at an
    INTERNAL block boundary returns the block END (240 -> 12:00, the finish role's answer) --
    A0923-CPM-034's rendering fault at a FORWARD-pass site that CPM-034's census listed as
    outside its claim (its fix at ``_succ_ls_wall`` / ``_succ_early_start_wall`` leaves this red).

    Authority: A2 -- the engine's own contracts, independent of the call site under test:
    ``engine/cpm.py:1403`` (``_offset_to_wall``): "``role="start"``: where minute ``offset``
    BEGINS"; ``cpm.py:681-682`` (``offset_to_start_datetime``, ADR-0523): "a start takes the
    LATER form, so 240 worked minutes reads 13:00 where the finish role reads 12:00";
    ``cpm.py:1293-1294`` (``_tod_at_worked_start``): "MS Project spells a start with the later
    form on 309 of 439 and a finish with the earlier form on 496 of 502 (ADR-0523)". A1 (the
    link definition) -- Microsoft Learn, "Create a work breakdown structure (WBS)", Task
    dependencies,
    https://learn.microsoft.com/dynamics365/project-operations/project-management/create-wbs
    (retrieved 2026-09-29): "Start-to-start (SS) | Task B (successor) can start only with or
    after the start of task A (predecessor)"; "Start-to-Finish (SF) | Task B (successor) can
    finish only after the start task A (predecessor)". Hand arithmetic: Q 08:00-12:00; P cannot
    work 12:00-13:00, so P starts 13:00 and finishes Tue 12:00 (the project finish); SS0 -> S
    13:00 -> 21:00, TF = Mon 21:00 -> Tue 12:00 = 15 h = 900 min of S's axis; SF0 (S 120) ->
    S's finish >= 13:00 -> S 11:00 -> 13:00 (after the 08:00 project start), TF = 23 h = 1380.

    Independence: the oracle is the engine's own start rendering of P plus the link definition
    and hand arithmetic -- none is produced by ``_pred_start_wall``. Alternative witness
    (verifier P5, non-authoritative): MPXJ 16.2.0's MicrosoftScheduler places S 13:00 -> 21:00,
    TS 15.0 h (SS0) and 11:00 -> 13:00 (SF0). MS Project's own output for this shape is
    UNVERIFIED (no committed save carries it). Controls (preconditions): P starting mid-block
    (11:20) and on a day boundary (Tue 08:00) give the hand answer today; a ZERO-duration P at
    the lunch boundary keeps its one instant -- ``cpm.py:696-698`` (``span_start_datetime``):
    "A **zero-duration instant** (milestone) has no beginning distinct from the instant itself,
    and MS Project spells it with the end-of-day form" -- so its SS0 successor starts where its
    FS0 twin does (12:00; MPXJ's MicrosoftScheduler agrees: P 12:00, S 12:00 -> 20:00 under both
    links); a repair that snaps every start (zero-duration included) moves that control and
    fails here by name (A0923-CPM-005, U25, owns the zero-duration start).
    """
    mon = _A0923_CPM_047_MON
    _, s = _a0923_cpm_047_solve("24h", "SS", 200, 480, 480)
    mid = (mon.replace(hour=11, minute=20), mon.replace(hour=19, minute=20))
    if (s.early_start_wall, s.early_finish_wall) != mid:
        pytest.fail(f"precondition (control): P starting mid-block (11:20) now gives S {s}")
    _, s = _a0923_cpm_047_solve("24h", "SS", 480, 480, 480)
    tue = dt.datetime(2026, 1, 6, 8, 0)
    if (s.early_start_wall, s.early_finish_wall) != (tue, tue.replace(hour=16)):
        pytest.fail(f"precondition (control): P starting on a day boundary now gives S {s}")
    for kind in ("24h", "elapsed"):
        p, s_ss = _a0923_cpm_047_solve(kind, "SS", 240, 0, 480)
        _p, s_fs = _a0923_cpm_047_solve(kind, "FS", 240, 0, 480)
        instant = offset_to_datetime(mon, p.early_start, _A0923_CPM_047_STD)
        got = (s_ss.early_start_wall, s_fs.early_start_wall, instant)
        if got != (mon.replace(hour=12),) * 3:
            pytest.fail(
                f"precondition (control): {kind}: a zero-duration P at the lunch boundary no "
                f"longer bounds S at its one instant 12:00 (SS0, FS0 twin, P's instant): {got}"
            )

    wrong: dict[str, str] = {}
    hand = {
        "SS": (mon.replace(hour=13), mon.replace(hour=21), 900),
        "SF": (mon.replace(hour=11), mon.replace(hour=13), 1380),
    }
    for kind in ("24h", "elapsed"):
        for rel, s_minutes in (("SS", 480), ("SF", 120)):
            p, s = _a0923_cpm_047_solve(kind, rel, 240, 480, s_minutes)
            p_start = offset_to_start_datetime(mon, p.early_start, _A0923_CPM_047_STD)
            if (p.early_start, p_start, p.total_float) != (240, mon.replace(hour=13), 0):
                pytest.fail(
                    f"precondition: {kind} {rel}0: P no longer starts at offset 240 = Mon 13:00 "
                    f"(the engine's own start rendering) on the critical path: {p} {p_start}"
                )
            got = (s.early_start_wall, s.early_finish_wall, s.total_float)
            if got != hand[rel]:
                wrong[f"{kind} {rel}0 S (ES, EF, TF)"] = (
                    f"{got} (P starts {p_start:%a %H:%M}; hand {hand[rel]})"
                )
    assert not wrong, (
        "a lag-0 SS / SF bound from a predecessor that starts on an internal block boundary is "
        f"read at the block END, before the predecessor starts: {wrong}"
    )
