"""Both Ask surfaces answer "the driving path for UID X **for each version**" (OR-11a).

The operator asked it of a 32-version workbook and got one version's answer. Two surfaces carried
the same defect and neither said so:

* ``POST /api/ask`` (multi-version) called ``driving_path_facts(schedules[-1], cpms[-1], text)``;
* ``GET /api/driving-path`` with no ``scope`` fell to ``schedules[-1], cpms[-1]``.

Measured on the pre-fix tree with 32 versions loaded: ONE driving-path fact, citing ONE file. The
model was not failing to answer — it had never been given 31 of the 32 versions to answer from.

The fixture re-wires the path between versions while holding the focus's own computed finish, so
a series that recomputed nothing would be visibly wrong rather than merely thin.
"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient

from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

_START = dt.datetime(2025, 1, 6, 8, 0)
_DAY = 480
FOCUS = 90


def _fs(p: int, s: int) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS)


def _version(label: str, sd: dt.datetime, a: int, b: int, c: int) -> Schedule:
    """A(a) -> B(b) -> FOCUS and C(c) -> FOCUS: whichever chain is longer drives the focus."""
    return Schedule(
        name="prog",
        source_file=label,
        project_start=_START,
        status_date=sd,
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=a * _DAY),
            Task(unique_id=2, name="B", duration_minutes=b * _DAY),
            Task(unique_id=3, name="C", duration_minutes=c * _DAY),
            Task(unique_id=FOCUS, name="Ready to Ship", duration_minutes=5 * _DAY),
        ),
        relationships=(_fs(1, 2), _fs(2, FOCUS), _fs(3, FOCUS)),
    )


def _session() -> SessionState:
    """Two versions: driven by A->B, then re-wired so C drives — same focus finish."""
    st = SessionState()
    st.schedules["v1"] = _version("v1.mpp", dt.datetime(2025, 1, 6, 8, 0), 10, 10, 1)
    st.schedules["v2"] = _version("v2.mpp", dt.datetime(2025, 2, 3, 8, 0), 5, 5, 20)
    return st


def _single() -> SessionState:
    st = SessionState()
    st.schedules["v1"] = _version("v1.mpp", dt.datetime(2025, 1, 6, 8, 0), 10, 10, 1)
    return st


QUESTION = f"What is the driving path to UID {FOCUS} in each version?"


def _blob(facts: list[dict[str, object]]) -> str:
    return " ".join(str(f["text"]) for f in facts)


# --- POST /api/ask ---------------------------------------------------------------------------


def test_the_workbook_ask_carries_a_driving_path_for_every_version() -> None:
    """THE regression, at the surface the operator used."""
    body = TestClient(create_app(_session())).post("/api/ask", data={"question": QUESTION}).json()
    blob = _blob(body["facts"])
    assert "v1.mpp" in blob and "v2.mpp" in blob, blob
    assert "2 activities" in blob and "1 activity" in blob, blob


def test_the_series_reaches_the_analyst_not_only_the_model() -> None:
    """``facts`` in the payload is what the panel SHOWS. A pinned fact survives both caps, so
    the series must be visible without a model active — the engine's own answer."""
    body = TestClient(create_app(_session())).post("/api/ask", data={"question": QUESTION}).json()
    assert body["answer"] is None  # no model configured in this session
    assert any("DRIVING-PATH SERIES" in str(f["text"]) for f in body["facts"]), body["facts"]


def test_a_question_without_driving_intent_gets_no_series() -> None:
    body = (
        TestClient(create_app(_session()))
        .post("/api/ask", data={"question": "how is the programme performing overall?"})
        .json()
    )
    assert not any("DRIVING-PATH SERIES" in str(f["text"]) for f in body["facts"])


# --- GET /api/driving-path -------------------------------------------------------------------


def test_the_deterministic_button_answers_for_every_version() -> None:
    """The engine-only path (no AI) is the one an exhibit is built from, so it must cover the
    same population the question names."""
    body = TestClient(create_app(_session())).get(f"/api/driving-path?uid={FOCUS}").json()
    assert "v1.mpp" in body["answer"] and "v2.mpp" in body["answer"], body["answer"]
    assert "2 activities" in body["answer"] and "1 activity" in body["answer"]


def test_a_scoped_request_still_answers_for_that_one_file() -> None:
    """Naming a scope means "this file" and must stay exactly that — no series."""
    body = TestClient(create_app(_session())).get(f"/api/driving-path?uid={FOCUS}&scope=v1").json()
    assert "DRIVING-PATH SERIES" not in body["answer"]
    assert "driving slack" in body["answer"]


def test_a_single_version_session_is_unchanged() -> None:
    """One file is not a series; the pre-OR-11a answer is the whole answer."""
    body = TestClient(create_app(_single())).get(f"/api/driving-path?uid={FOCUS}").json()
    assert "DRIVING-PATH SERIES" not in body["answer"]
    assert "driving slack" in body["answer"] and body["facts"]


def test_an_unknown_uid_is_still_reported_as_absent_not_as_an_empty_series() -> None:
    body = TestClient(create_app(_session())).get("/api/driving-path?uid=99999999").json()
    assert "not a scheduled activity" in body["answer"]
    assert body["facts"] == []
