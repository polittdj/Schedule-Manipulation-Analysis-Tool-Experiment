"""Unrestricted Ask must feed the model the NEWEST analyzable version's activity table.

``/api/ask`` builds its facts from the newest version (``build_workbook_fact_sheet`` +
``driving_path_facts(schedules[-1], cpms[-1], …)``) but resolved the raw activity table for
UNRESTRICTED mode (ADR-0361) by matching ``s.name == newest.name`` over ``st.schedules``.
Successive updates of one project carry the SAME ``Schedule.name`` — that is what makes them
versions of it — so ``next(...)`` returned the FIRST match, i.e. the OLDEST file.

The model was therefore handed facts from the newest version and per-activity data from the
oldest, and unrestricted mode is the one mode that is deliberately **ungated** (no figure
check), so nothing downstream could catch a figure computed off the stale table.

Identity is the KEY, never the name — the same rule ``Task.unique_id`` follows in the model
layer, and the reason ``ordered_versions()`` hands keys back at all.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.web.app as app_mod
from schedule_forensics.importers.json_schedule import parse_json_text
from schedule_forensics.web.app import SessionState, create_app

EXAMPLE = (
    Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/examples/house_build.json"
)
MARKER = "Roofing NEWEST-VERSION-MARKER"


def _versions() -> tuple[str, str]:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    old = json.loads(json.dumps(raw))
    old["status_date"] = "2026-02-02T17:00:00"
    new = json.loads(json.dumps(raw))
    new["status_date"] = "2026-03-02T17:00:00"
    for t in new["tasks"]:
        if t.get("unique_id") == 5:
            t["name"] = MARKER
    return json.dumps(old), json.dumps(new)


@pytest.fixture
def st() -> SessionState:
    old, new = _versions()
    state = SessionState()
    state.schedules["may"] = parse_json_text(old)
    state.schedules["jun"] = parse_json_text(new)
    state.ai_config = dataclasses.replace(state.ai_config, qa_mode="unrestricted")
    return state


def test_the_two_versions_share_a_name_and_order_newest_last(st: SessionState) -> None:
    """Guard the guard: the defect needs same-named versions AND a known newest, or the
    assertion below proves nothing."""
    assert st.schedules["may"].name == st.schedules["jun"].name
    keys = [k for k, _ in st.ordered_versions()]
    assert keys == ["may", "jun"], f"ordered oldest-first expected, got {keys}"
    assert MARKER in {t.name for t in st.schedules["jun"].tasks}
    assert MARKER not in {t.name for t in st.schedules["may"].tasks}


def test_unrestricted_ask_feeds_the_newest_versions_activity_table(
    st: SessionState, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, str | None] = {}
    original = app_mod.answer_question

    def spy(backend, facts, question, *, mode="strict", data_block=None):  # type: ignore[no-untyped-def]
        captured["block"] = data_block
        return original(backend, facts, question, mode=mode, data_block=data_block)

    # patched on web.app: that is the module whose code CALLS it (_ask_response)
    monkeypatch.setattr(app_mod, "answer_question", spy)

    client = TestClient(create_app(st))
    resp = client.post("/api/ask", data={"question": "Summarise the schedule."})
    assert resp.status_code == 200, resp.text

    block = captured.get("block")
    assert block, "unrestricted mode must attach an activity data block"
    assert MARKER in block, (
        "unrestricted Ask fed the model an OLDER version's activity table while its facts came "
        "from the newest — resolved by name instead of by key"
    )
