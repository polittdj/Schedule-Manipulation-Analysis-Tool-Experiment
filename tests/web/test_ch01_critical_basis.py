"""Chapter-01 "Where we stand" Critical basis (audit M3, ADR-0220).

The landing chapter counted Critical (and banded float) from PURE-LOGIC CPM float, while the
ribbon (ch 02) and ch 11 use the progress-aware effective basis (MS Project's stored Total
Slack / Critical flag first). On a progressed file that made the SAME file show a different
Critical count on ch 01 than on 02/11. These tests pin the reconciliation on a real progressed
golden (where the two bases diverge sharply — pure-logic 90 vs effective 34), so a regression
back to raw float is caught.
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


def _sch():  # type: ignore[no-untyped-def]
    xml = gzip.decompress((GOLD / "Hard_File.mspdi.xml.gz").read_bytes()).decode("utf-8")
    return parse_mspdi_text(xml)


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
    pure_logic = sum(
        1
        for t in non_summary(sch)
        if t.percent_complete < 100.0
        and (tm := cpm.timings.get(t.unique_id)) is not None
        and tm.total_float <= 0
    )

    # chapter 01 now agrees with chapter 02 (the whole point of M3)…
    assert ch01_critical == ribbon_critical
    # …and this genuinely differs from the old pure-logic count on a progressed file
    assert ch01_critical != pure_logic


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
