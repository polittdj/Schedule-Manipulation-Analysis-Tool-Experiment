"""Presentation-bug batch (audit PR 2): M2 KPI sentinel, L1 workbench NA, L2 population mix, L10.

These are display-only fixes — no metric math changes. Each test pins the corrected rendering:
a missing KPI and an unmeasurable workbench cell both show "—" (not "&amp;mdash;" / "0.00"),
"What changed" counts one population, and the chapter-01 Gantt legend uses theme tokens.
"""

from __future__ import annotations

import datetime as dt
import gzip
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import (
    SessionState,
    _stat_cards,
    _what_changed_header,
    create_app,
)

REPO = Path(__file__).resolve().parents[1]
GOLD = REPO / "fixtures" / "golden" / "fuse_hardfile"
APP_SRC = REPO.parent / "src" / "schedule_forensics" / "web" / "app.py"
DAY = 480


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    xml = gzip.decompress((GOLD / "Hard_File.mspdi.xml.gz").read_bytes())
    c.post("/upload", files={"files": ("Hard_File.mspdi.xml", xml, "text/xml")})
    return c


# ---------------------------------------------------------------- M2: KPI sentinel double-escape


def test_stat_card_missing_value_renders_em_dash_not_the_escaped_entity() -> None:
    html = _stat_cards([("BEI (throughput)", "—")])
    assert "—" in html
    # the bug: html.escape("&mdash;") == "&amp;mdash;" reached the flagship KPI strips
    assert "&amp;mdash;" not in html
    assert "&mdash;" not in html


def test_no_mdash_entity_sentinel_values_remain_in_app_source() -> None:
    # regression guard: a quoted "&mdash;"/'&mdash;' value would double-escape through _e again
    src = APP_SRC.read_text(encoding="utf-8")
    assert '"&mdash;"' not in src
    assert "'&mdash;'" not in src


# ---------------------------------------------------------------- L1: workbench NA renders "—"


def test_workbench_cells_carry_applicable_and_flag_genuine_na(client: TestClient) -> None:
    data = client.get("/api/workbench").json()
    family = {m["id"]: m["family"] for m in data["metrics"]}
    saw_na = False
    for mid, per_version in data["cells"].items():
        for cell in per_version.values():
            assert isinstance(cell["applicable"], bool)  # the flag the grid/export read
            if family[mid] == "DCMA-14" and cell["status"] == "NA":
                assert cell["applicable"] is False  # unmeasurable → "—", not placeholder 0
                saw_na = True
            if family[mid] != "DCMA-14":
                assert cell["applicable"] is True  # informational extras keep their real value
    assert saw_na, "fixture expected to carry at least one unscored (NA) DCMA metric"


# -------------------------------------------------------------- L2: one population for What changed


def _t(uid: int, *, active: bool = True) -> Task:
    return Task(unique_id=uid, name=f"T{uid}", duration_minutes=5 * DAY, is_active=active)


def _sched(tasks: tuple[Task, ...]) -> Schedule:
    return Schedule(name="S", project_start=dt.datetime(2026, 1, 5, 8, 0), tasks=tasks)


def test_what_changed_counts_one_population_with_an_inactive_task_present() -> None:
    prior = _sched((_t(1), _t(2), _t(3)))
    # current: 1/2/3 unchanged + an ADDED, INACTIVE task 4 (deactivation is a tracked change,
    # so diff_versions counts it — the "Unchanged" total must reconcile with THAT population)
    current = _sched((_t(1), _t(2), _t(3), _t(4, active=False)))
    html = _what_changed_header(prior, current, compute_cpm(prior), compute_cpm(current))
    assert "Added <b>1</b>" in html
    # 4 non-summary, minus 1 added, minus 0 changed = 3 unchanged. The old code used the
    # active-only total (3) and reported 2 -- the population mix the audit flagged.
    assert "Unchanged <b>3</b>" in html
    assert "Unchanged <b>2</b>" not in html


# ---------------------------------------------------------------- L10: Gantt legend uses tokens


def test_ch01_gantt_legend_uses_theme_tokens_not_hardcoded_hex(client: TestClient) -> None:
    key = client.get("/api/dashboard").json()["cards"][-1]["key"]
    body = client.get(f"/analysis/{key}").text
    for token in ("background:var(--ok)", "background:var(--warn)", "background:var(--bad)"):
        assert token in body
    for hexes in ("#2e7d32", "#f9a825", "#c62828", "#9e9e9e"):
        assert hexes not in body  # would never recolor in apollo/jarvis
