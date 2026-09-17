"""Chapter-01 "Where we stand" Critical basis (audit M3, ADR-0220).

The landing chapter counted Critical (and banded float) from PURE-LOGIC CPM float, while the
ribbon (ch 02) and ch 11 use the progress-aware effective basis (MS Project's stored Total
Slack / Critical flag first). On a progressed file that made the SAME file show a different
Critical count on ch 01 than on 02/11. These tests pin the reconciliation on real goldens: the
page's count equals the ribbon's on the base snapshot (where, since ADR-0505's carried milestone
instant, the stored basis and the pure-logic count coincide — 110 of 110 flags agree), and the
ribbon differs from the pure-logic count on the progressed updated3 snapshot (7 of 110 flags
disagree), so a regression back to raw float is caught where the two bases can still be told apart.
"""

from __future__ import annotations

import gzip
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.metrics._common import (
    effective_total_float,
    non_summary,
)
from schedule_forensics.engine.metrics.ribbon import compute_ribbon
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.web.app import SessionState, create_app

REPO = Path(__file__).resolve().parents[1]
GOLD = REPO / "fixtures" / "golden" / "fuse_hardfile"


def _sch(name: str = "Hard_File"):  # type: ignore[no-untyped-def]
    xml = gzip.decompress((GOLD / f"{name}.mspdi.xml.gz").read_bytes()).decode("utf-8")
    return parse_mspdi_text(xml)


def _pure_logic_critical(sch, cpm) -> int:  # type: ignore[no-untyped-def]
    """The old chapter-01 count: incomplete activities whose PURE-LOGIC float is <= 0."""
    return sum(
        1
        for t in non_summary(sch)
        if t.percent_complete < 100.0
        and (tm := cpm.timings.get(t.unique_id)) is not None
        and tm.total_float <= 0
    )


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    xml = gzip.decompress((GOLD / "Hard_File.mspdi.xml.gz").read_bytes())
    c.post("/upload", files={"files": ("Hard_File.mspdi.xml", xml, "text/xml")})
    return c


def _kpi(html: str, label: str) -> int:
    m = re.search(
        r"stat-value>(\d+)</div><div class=stat-label>" + re.escape(label),
        html,
    )
    assert m is not None, f"KPI {label!r} not found"
    return int(m.group(1))


def _legend_count(html: str, label: str) -> int:
    m = re.search(re.escape(label) + r" <b>(\d+)</b>", html)
    assert m is not None, f"band {label!r} not found"
    return int(m.group(1))


def test_ch01_critical_matches_the_ribbon_not_pure_logic_cpm(client: TestClient) -> None:
    page = client.get("/analysis/Hard_File").text
    ch01_critical = _kpi(page, "Critical (incomplete)")

    sch = _sch()
    cpm = compute_cpm(sch)
    ribbon_critical = compute_ribbon(sch, cpm, audit_schedule(sch, cpm)).critical

    # chapter 01 now agrees with chapter 02 (the whole point of M3)…
    assert ch01_critical == ribbon_critical
    # …and on the base snapshot the stored basis and the pure-logic count now COINCIDE: since
    # ADR-0505 (the carried milestone instant) the engine's Critical flag agrees with MS Project's
    # on 110 of 110 activities, so Hard_File can no longer witness the two bases apart (until
    # ADR-0505 it did: 108 of 110 agreed, and the counts differed). Pinned as the agreement it is.
    assert ch01_critical == _pure_logic_critical(sch, cpm)
    # …the witness that the ribbon is the STORED basis and not pure logic is the progressed
    # updated3 snapshot, where 7 of 110 flags still disagree (an odd number: the counts differ)
    sch3 = _sch("Hard_File_updated3")
    cpm3 = compute_cpm(sch3)
    ribbon3 = compute_ribbon(sch3, cpm3, audit_schedule(sch3, cpm3)).critical
    assert ribbon3 != _pure_logic_critical(sch3, cpm3)


def test_ch01_float_bands_use_effective_float(client: TestClient) -> None:
    page = client.get("/analysis/Hard_File").text
    zero_band = _legend_count(page, "0 days")

    sch = _sch()
    cpm = compute_cpm(sch)
    per_day = sch.calendar.working_minutes_per_day or 1
    eff_zero = sum(
        1
        for t in non_summary(sch)
        if t.percent_complete < 100.0
        and t.unique_id in cpm.timings
        and effective_total_float(t, cpm.timings[t.unique_id].total_float) / per_day <= 0
    )
    assert zero_band == eff_zero
