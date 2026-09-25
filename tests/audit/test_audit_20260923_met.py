"""Executable reproducers for the AUDIT-2026-09-23 findings in the MET lane (A0923-MET-001..002).

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

A0923-MET-001 builds its versions inline from model objects (the verifier's own set, hand-derived
figures in the test); A0923-MET-002 reads the already-committed golden
``tests/fixtures/golden/fuse_ltf/Large_Test_File2.mspdi.xml.gz`` (non-CUI build reference). No
fixture file is added; an autouse fixture refuses every non-loopback connect and name lookup.
Drop-in path: ``tests/audit/``. Run: ``pytest tests/audit/test_audit_20260923_met.py -rxX``.
"""

from __future__ import annotations

import datetime as dt
import gzip
import re
import socket
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.engine.margin_dashboard import compute_margin_dashboard
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

REPO = Path(__file__).resolve().parents[2]

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


# --------------------------------------------------------------------------------------------
# A0923-MET-001 (T1): margin erosion / carry-forward mix margin-to-target and -to-project-finish
# --------------------------------------------------------------------------------------------
_DAY = 480
_START = dt.datetime(2026, 1, 5, 8, 0)
_M = 3  # the target milestone's UniqueID


def _version(status: str, pre_m: float, with_m: bool) -> tuple[str, Schedule, CPMResult]:
    """Design 20d -> MARGIN pre-M -> [Milestone M] -> Build 30d -> MARGIN reserve 70d -> finish.

    Hand arithmetic (effective margin = how far the finish pulls in when every margin task is
    zeroed): to M = ``pre_m`` wd; without M the tool measures to the project finish = pre_m + 70.
    """

    def task(uid: int, name: str, days: float, *, milestone: bool = False) -> Task:
        return Task(
            unique_id=uid, name=name, duration_minutes=int(days * _DAY), is_milestone=milestone
        )

    def fs(pred: int, succ: int) -> Relationship:
        return Relationship(predecessor_id=pred, successor_id=succ, type=RelationshipType.FS)

    tasks = [
        task(1, "Design", 20),
        task(2, "Schedule MARGIN: pre-M", pre_m),
        task(5, "Build", 30),
        task(6, "Schedule MARGIN: project reserve", 70),
        task(7, "Project complete", 0, milestone=True),
    ]
    rels = [fs(1, 2), fs(5, 6), fs(6, 7)]
    if with_m:
        tasks.insert(2, task(_M, "Milestone M", 0, milestone=True))
        rels += [fs(2, _M), fs(_M, 5)]
    else:
        rels += [fs(2, 5)]
    sch = Schedule(
        name=status,
        source_file=f"v_{status}.mpp",
        project_start=_START,
        status_date=dt.datetime.fromisoformat(f"{status}T17:00"),
        tasks=tuple(tasks),
        relationships=tuple(rels),
    )
    return sch.source_file or status, sch, compute_cpm(sch)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-MET-001: the margin dashboard fits one erosion slope through versions measured "
    "to the target and to the project finish (target absent) and carries a plan measured on one "
    "basis into a version measured on the other: 39.13 wd/month and a zero date before the "
    "as-of date vs 1.09 / 2026-11-09, and an 88.75% 'consumed' corrective trigger",
)
def test_a0923_met_001_margin_trend_and_plan_never_span_two_measurement_bases() -> None:
    """Claim: at 8c71c639, versions where target milestone M (UID 3) is absent from v1 give,
    via compute_margin_dashboard(target_uid=3), an erosion of 39.13 wd/month and a zero-margin
    date 2026-03-27 (before the latest status date 2026-03-30, at which 8 wd remain) because v1 is
    measured to the project finish (80 wd) and the fit spans both bases (the target-resolved
    versions alone give 1.09 wd/month, 2026-11-09); the two-version carry-forward plans v2 from
    v1's project-finish margin (80 wd) against v2's margin to M (9 wd): 71 wd 'consumed', 88.75%,
    corrective_action True; the reverse case (M deleted in v3) gives a negative erosion rate.

    Authority: docs/STATE/AUDIT-2026-07-14.md:75-76 "If the target exists in some versions and is
    absent (deleted/renamed) in others, the series mixes margin-to-target with
    margin-to-project-finish." and :81-83 "fit the erosion only over versions that share one basis
    (e.g. only those where the target resolved), and disclose when versions were excluded; or
    surface a "mixed basis" warning." The module's own rule for its sibling basis,
    src/schedule_forensics/engine/margin_dashboard.py:158-160 "a single slope through mixed bases
    would be a fabricated number (Law 2), so the tool discloses the basis change instead." and
    docs/adr/0245-orchestrated-audit-remediation.md:46-49 "the `consumed`/`planned`/
    `corrective-action` carry-forward now also refuses the cross-basis subtraction".

    Tier: T1 (not LAW-1; latent in the committed corpus; nothing disclosed on /margin). The
    2026-07-14 audit's NEW-2, never registered.
    """
    v1 = _version("2026-02-02", 10, with_m=False)
    v2 = _version("2026-03-02", 9, with_m=True)
    v3 = _version("2026-03-30", 8, with_m=True)
    mixed = compute_margin_dashboard([v1, v2, v3], target_uid=_M)
    rows = [(m.target_name, m.effective_margin_wd) for m in mixed.months]
    if rows != [(None, 80.0), ("Milestone M", 9.0), ("Milestone M", 8.0)]:
        pytest.fail(f"precondition: per-version margins are the hand values, got {rows}")
    one_basis = compute_margin_dashboard([v2, v3], target_uid=_M)
    if (one_basis.erosion_wd_per_month, one_basis.zero_margin_date) != (1.09, "2026-11-09"):
        pytest.fail("precondition: the one-basis fit matches the hand fit 1.09 / 2026-11-09")
    to_finish = compute_margin_dashboard([v1, v2], target_uid=None).months[1]
    if (to_finish.consumed_wd, to_finish.corrective_action) != (1.0, False):
        pytest.fail("precondition: on one basis (project finish) v2 consumed 1.0 wd, no trigger")

    problems = []
    fitted = (mixed.erosion_wd_per_month, mixed.zero_margin_date)
    if fitted not in {(None, None), (one_basis.erosion_wd_per_month, one_basis.zero_margin_date)}:
        problems.append(
            f"erosion {fitted[0]} wd/month, zero-margin {fitted[1]} fitted across both bases "
            "(latest status 2026-03-30); the target-resolved versions give 1.09 / 2026-11-09"
        )
    v2_row = compute_margin_dashboard([v1, v2], target_uid=_M).months[1]
    if v2_row.planned_margin_wd is not None or v2_row.corrective_action:
        problems.append(
            f"v2 planned {v2_row.planned_margin_wd} (v1's margin to the PROJECT FINISH) against "
            f"{v2_row.effective_margin_wd} to M: consumed {v2_row.consumed_wd} "
            f"({v2_row.consumed_pct}), corrective_action {v2_row.corrective_action}"
        )
    r1 = _version("2026-02-02", 10, with_m=True)
    r2 = _version("2026-03-02", 9, with_m=True)
    r3 = _version("2026-03-30", 8, with_m=False)
    reverse = compute_margin_dashboard([r1, r2, r3], target_uid=_M)
    kept = compute_margin_dashboard([r1, r2], target_uid=_M)
    reverse_fit = (reverse.erosion_wd_per_month, reverse.zero_margin_date)
    if reverse_fit not in {(None, None), (kept.erosion_wd_per_month, kept.zero_margin_date)}:
        problems.append(
            f"reverse case (M deleted in v3): erosion {reverse_fit[0]} wd/month, zero-margin "
            f"{reverse_fit[1]}; the target-resolved versions give {kept.erosion_wd_per_month}"
        )
    assert problems == [], "\n".join(problems)


# --------------------------------------------------------------------------------------------
# A0923-MET-002 (T2): /analysis prints two unlabelled total floats for one activity
# --------------------------------------------------------------------------------------------
_LTF2 = REPO / "tests" / "fixtures" / "golden" / "fuse_ltf" / "Large_Test_File2.mspdi.xml.gz"
_BASIS_WORDS = re.compile(
    r"stored|recomputed|re-computed|pure-logic|logic-only|progress-aware|as-scheduled", re.I
)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-MET-002: one /analysis render of Large_Test_File2 shows UID 6444/6445/5855 at "
    "-33/-33/-34 wd in 'Top pressure points' (stored Total Slack = Acumen) and -31.81/-31.81/"
    "-32.73 in the activity grid the panel calls its data table (recomputed), neither labelled",
)
def test_a0923_met_002_one_activity_shows_one_total_float_or_both_are_labelled() -> None:
    """Claim: at 8c71c639 one /analysis render of the Large_Test_File2 golden prints two different
    total floats for the same activity — the scatter panel's 'Top pressure points' table
    (effective_total_float = the stored, progress-aware Total Slack, which Acumen Fuse reproduces)
    shows UID 6444 / 6445 at -33 wd and UID 5855 at -34 wd, while the activity grid that the same
    panel calls 'the accessible data table' shows -31.81 / -31.81 / -32.73 (recomputed CPM float)
    — and neither table states its basis (189 of 998 incomplete activities differ at whole-day
    resolution, verifier census).

    Authority: src/schedule_forensics/web/analysis.py:729 "The full activity grid above is the
    accessible data table." and :657-658 "Every figure is engine-computed here; the chart
    (scatter.js) is presentation over the same rows." with the project's one-basis precedent
    docs/adr/0220-ch01-critical-basis.md:18-19 "On a progressed file the two bases diverge sharply
    — the flagship landing chapter showed a *different* Critical count than every other chapter
    for the same file."

    Tier: T2 (not LAW-1). The two-source design is ADR-0080/0141 and is not challenged; the defect
    is the unlabelled double value. Correct = one basis in both tables, or a basis on each label.
    """
    if not _LTF2.is_file():
        pytest.fail(f"precondition: the committed golden is present at {_LTF2}")
    with gzip.open(_LTF2, "rt", encoding="utf-8") as handle:
        sch = parse_mspdi_text(handle.read(), source_file="Large_Test_File2.xml")
    state = SessionState()
    state.schedules["ltf2"] = sch
    client = TestClient(create_app(state))
    page = client.get("/analysis/ltf2").text
    if "The full activity grid above is the accessible data table." not in page:
        pytest.fail("precondition: the scatter panel names the grid as its data table")
    pressure = re.findall(r"<tr><td>(\d+)</td><td>[^<]*</td><td>-?\d+</td><td>(-?\d+)</td>", page)
    header = re.search(r"<th scope=col>Duration \(wd\)</th><th scope=col>([^<]*)</th>", page)
    if not pressure or header is None:
        pytest.fail("precondition: /analysis renders the 'Top pressure points' table")
    grid = {
        row["unique_id"]: row["total_float_days"]
        for row in client.get("/api/analysis/ltf2").json()["activities"]
    }
    column = re.search(
        r'key: "total_float_days", label: "([^"]*)"', client.get("/static/app.js").text
    )
    if column is None:
        pytest.fail("precondition: the served app.js declares the grid's total-float column")
    differ = [
        f"UID {uid}: pressure table {shown} wd, grid {grid[int(uid)]}"
        for uid, shown in pressure
        if f"{float(grid[int(uid)]):.0f}" != shown
    ]
    labelled = (
        bool(_BASIS_WORDS.search(header.group(1)))
        and bool(_BASIS_WORDS.search(column.group(1)))
        and header.group(1) != column.group(1)
    )
    problems = [] if labelled else differ
    if problems:
        problems.append(f"labels: pressure {header.group(1)!r}, grid {column.group(1)!r}")
    assert problems == [], "\n".join(problems)
