"""Ask-the-AI must keep the ENGINE's driving-path facts when a session filter is active.

``ai/driving_facts.py`` exists for one reason, stated in its own module docstring: a small local
model "keeps getting 'what is the driving path to UID X?' wrong, because multi-hop path + slack
traversal over hundreds of activities is exactly what a small LLM is unreliable at", so the engine
computes the answer and injects it as CITED facts. If those facts silently disappear, the model is
left doing the traversal itself — the exact failure the module was written to prevent — and the
figure gate can only discard (strict) or flag (annotate) whatever it invents.

``/api/ask/{name}`` and the single-file branch of ``/api/ask`` passed the RAW session schedule
alongside ``analysis.cpm``, which is solved on the SCOPED population (``_Analysis.scoped``,
ADR-0263). With a filter active the raw network still references tasks the scoped CPM has no
timing for, so ``compute_driving_slack`` raises ``KeyError`` and ``driving_path_summary``'s
``except (KeyError, ValueError)`` swallows it and returns ``()`` — silently, with a 200.

The oracle is DIFFERENTIAL and the product supplies it: ``/api/driving-path`` already pairs
``a.scoped`` with ``a.cpm`` (its own comment cites ADR-0263), and ``/api/ask``'s multi-version
branch already goes through ``_solvable_versions`` → ``cpm_scoped_for``. So with two files loaded
and a filter on, the two Ask panels answered the SAME question with contradictory evidence.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.importers.json_schedule import parse_json_text
from schedule_forensics.web.app import SessionState, create_app

EXAMPLE = (
    Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/examples/house_build.json"
)
#: UID 5 ("Roofing") is a Normal activity, so it SURVIVES the reduce filter — the facts about it
#: must survive too. UID 8 ("Inspection") is the lone milestone the filter removes.
FOCUS_UID = 5
QUESTION = f"What is the driving path to UID {FOCUS_UID}?"
_RAW_TASKS, _SCOPED_TASKS = 9, 8


def _state(n_files: int = 1) -> SessionState:
    st = SessionState()
    text = EXAMPLE.read_text(encoding="utf-8")
    for i in range(n_files):
        st.schedules[f"v{i}"] = parse_json_text(text)
    return st


def _filter(st: SessionState) -> None:
    st.set_filter([("Activity Type", "Normal")])
    st.set_filter_mode("reduce")


def _driving_facts(client: TestClient, route: str) -> list[str]:
    resp = client.post(route, data={"question": QUESTION})
    assert resp.status_code == 200, resp.text
    facts = resp.json().get("facts") or []
    texts = [f if isinstance(f, str) else str(f.get("text", f)) for f in facts]
    return [t for t in texts if "driving path to" in t.lower() or "near-driving" in t.lower()]


def test_the_filter_actually_narrows_this_fixture() -> None:
    """Guard the guard: every assertion below is vacuous if the filter does not bite."""
    st = _state()
    raw = st.schedules["v0"]
    assert len(raw.tasks) == _RAW_TASKS
    assert st.scope(raw) is raw, "unfiltered scope() must be the identity"
    _filter(st)
    assert len(st.scope(raw).tasks) == _SCOPED_TASKS
    assert FOCUS_UID in {t.unique_id for t in st.scope(raw).tasks}, "focus must stay IN scope"


@pytest.mark.parametrize("route", ["/api/ask/v0", "/api/ask"])
def test_unfiltered_ask_carries_the_engine_driving_path_facts(route: str) -> None:
    """Baseline. If THIS fails the fixture/question/intent parsing is wrong, not the product —
    which is what makes the filtered failure below a red for the RIGHT reason."""
    client = TestClient(create_app(_state()))
    assert _driving_facts(client, route), f"{route}: no engine driving-path facts even UNFILTERED"


@pytest.mark.parametrize("route", ["/api/ask/v0", "/api/ask"])
def test_filtered_ask_still_carries_the_engine_driving_path_facts(route: str) -> None:
    st = _state()
    _filter(st)
    client = TestClient(create_app(st))
    assert _driving_facts(client, route), (
        f"{route}: the engine's driving-path facts vanished under a filter — the model is now "
        "left to traverse the network itself, which is what driving_facts.py exists to prevent"
    )


def test_the_two_ask_panels_agree_under_a_filter() -> None:
    """The product's own oracle: with 2 files loaded, /api/ask uses the (correctly scoped)
    multi-version branch while /api/ask/{name} used the raw one. Same session, same question,
    contradictory evidence."""
    st = _state(2)
    _filter(st)
    client = TestClient(create_app(st))
    per_file = _driving_facts(client, "/api/ask/v0")
    workbook = _driving_facts(client, "/api/ask")
    assert workbook, "control: the multi-version branch is the CORRECT one and must carry facts"
    assert per_file, (
        "the two Ask panels disagree under a filter: /api/ask carries the engine's "
        f"driving-path facts ({len(workbook)}) and /api/ask/{{name}} carries none"
    )
