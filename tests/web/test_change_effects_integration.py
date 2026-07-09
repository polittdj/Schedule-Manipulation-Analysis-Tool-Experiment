"""Integrity page per-change effects + AI counterfactual facts + nav/timeout chrome (ADR-0162).

The regression that motivated this: the AI answered "zero effect" for reverting UID 187's removed
logic on UID 155 when the engine-computed effect is +23 working days. These tests pin the fix in
both the Integrity page render and the AI fact base, plus the two chrome fixes shipped alongside.
"""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "fuse_hardfile"
STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    for name in ("Hard_File", "Hard_File_updated"):
        xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes())
        c.post("/upload", files={"files": (f"{name}.mpp.xml", xml, "text/xml")})
    return c


def test_integrity_shows_per_change_effect_on_the_target(client: TestClient) -> None:
    page = client.get("/integrity").text
    assert "change-effects" in page
    assert "Effect of each change" in page
    # the removed 188→187 link shows its computed +23 working-day effect (was hidden by removal)
    assert (
        "restore removed FS link 188&rarr;187" in page or "restore removed FS link 188→187" in page
    )
    assert "+23 wd" in page


def test_ai_facts_carry_the_computed_counterfactual_not_zero(client: TestClient) -> None:
    # target UID 155 set → the Ask-the-AI fact base gets the engine-computed effect, so the model
    # can no longer answer "zero effect" for the 188→187 logic change.
    client.get("/target?uid=155")
    from schedule_forensics.ai.qa import manipulation_forensics_facts
    from schedule_forensics.engine.cpm import compute_cpm

    state = client.app.state.session  # type: ignore[attr-defined]
    schedules = list(state.schedules.values())
    cpms = [compute_cpm(s) for s in schedules]
    facts = manipulation_forensics_facts(schedules, cpms, target_uid=155)
    joined = " ".join(f.text for f in facts)
    assert "188→187" in joined
    assert "+23 working day(s) LATER" in joined
    assert "hid that much slip" in joined


def test_nav_active_is_high_contrast_and_single_winner() -> None:
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    assert "#ffd400" in css  # yellow pill, not accent-blue-on-blue
    hints = (STATIC / "hints.js").read_text(encoding="utf-8")
    # exact-match-first, single longest-prefix winner (so /briefing no longer lights /brief)
    assert "winnerLen" in hints
    assert 'here.indexOf(href + "/")' in hints


def test_generation_timeout_defaults_to_max() -> None:
    from schedule_forensics.ai.backend import AIConfig

    assert AIConfig().gen_timeout == 3600.0


@pytest.fixture
def client23() -> TestClient:
    c = TestClient(create_app(SessionState()))
    for name in ("Hard_File_updated2", "Hard_File_updated3"):
        xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes())
        c.post("/upload", files={"files": (f"{name}.mpp.xml", xml, "text/xml")})
    return c


def test_integrity_clusters_ms_project_reschedule_artifacts(client23: TestClient) -> None:
    """Operator 2026-07-09 (ADR-0176): the 44 SNET-stamped-at-data-date constraint rows on
    updated2→updated3 are REAL file changes, but they are MS Project 'reschedule uncompleted
    work' statusing artifacts — clustered under one explanatory collapsible instead of flooding
    the change table; the one deliberate SNET (UID 261, dated 2026-09-23 ≠ the data date) stays
    in the main table."""
    page = client23.get("/integrity").text
    assert "artifact-cluster" in page
    assert "MS Project reschedule" in page
    assert "44 constraint change(s) look like the MS Project" in page
    # deliberate constraint stays in the main table with the plain now→was label
    assert "restore UID 261 constraint" in page and "now SNET 2026-09-23" in page
    # the date-only constraint move (UID 189 SNET date re-stamped) is measured, not dropped
    assert "was SNET 2026-07-31" in page


def test_integrity_exception_field_is_removed(client23: TestClient) -> None:
    """Operator 2026-07-09: 'the Exception Field makes no sense. Remove it.'"""
    page = client23.get("/integrity").text
    assert "Exception field" not in page
    assert "exception_field" not in page
    assert "hide_excepted" not in page
    # the Excel export link no longer carries the parameter either
    assert "exception_field=" not in page


def test_integrity_shows_cost_work_resource_and_added_logic_signals(client23: TestClient) -> None:
    """ADR-0176: the four new manipulation signals render on the updated2→updated3 pair —
    including the seeded history rewrites (actual cost / actual work reduced)."""
    page = client23.get("/integrity").text
    assert "had their total cost changed" in page
    assert "had recorded actual cost reduced" in page
    assert "had recorded actual work reduced" in page
    assert "resource bookings edited since the prior version" in page
    assert "logic links added since the prior version" in page
