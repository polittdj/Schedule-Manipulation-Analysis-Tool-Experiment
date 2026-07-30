"""Operator-visible refusal instead of a silent fabricated figure (ADR-0313, V1/V2, H3).

Three silent-failure paths on `/sra`, all of the same class — the tool proceeded with a value the
operator never supplied and said nothing:

1. an unparseable **impact magnitude** became a *locked zero* on the risk row;
2. an unparseable magnitude **cell** in the Excel round-trip took the same path, although the
   importer's own contract promises *"a missing figure is skipped and reported, never guessed"*;
3. `POST /sra/ssi/load` did an **unbounded** read and redirected in **total silence** on bad JSON,
   so a wrong file looked like a successful load that changed nothing.

Each now reports. The banner's severity is asserted too: an error rendered in the success style is
not operator-visible in the sense that matters.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import (
    _MAX_SETUP_BYTES,
    SessionState,
    _latest_solvable,
    create_app,
)

GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "project2_5"
    / "Project5.mspdi.xml"
)


@pytest.fixture
def state() -> SessionState:
    return SessionState()


@pytest.fixture
def client(state: SessionState) -> TestClient:
    c = TestClient(create_app(state))
    c.post("/upload", files={"files": ("Project5.mspdi.xml", GOLDEN.read_bytes(), "text/xml")})
    return c


def _uid(state: SessionState) -> int:
    chosen = _latest_solvable(state)
    assert chosen is not None
    _key, sch, _cpm = chosen
    return next(t.unique_id for t in sch.tasks if not t.is_summary)


def _add(client: TestClient, uid: int, *, days: str = "", pct: str = "") -> None:
    """POST WITHOUT following the redirect. `sra_import_msg` is one-shot and consumed by the next
    `/sra` render, so a followed 303 would render-and-clear the banner before the test could read
    it — the assertion would then fail for a reason that has nothing to do with the product."""
    resp = client.post(
        "/sra/risk-register",
        follow_redirects=False,
        data={
            "action": "add",
            "name": "Weather delay",
            "prob": "50",
            "affected": str(uid),
            "impact_days": days,
            "impact_pct": pct,
            "consequence": "",
        },
    )
    assert resp.status_code == 303


# --- the risk form ------------------------------------------------------------------


@pytest.mark.parametrize("bad", ["abc", "1.2.3", "5 days", "12,5", "inf", "=1+1"])
def test_an_unparseable_magnitude_refuses_the_row_and_says_so(
    client: TestClient, state: SessionState, bad: str
) -> None:
    _add(client, _uid(state), days=bad, pct="20")
    assert state.sra_risks == [], f"{bad!r} must not enter the register at all"
    page = client.get("/sra").text
    assert "Risk not added" in page
    assert 'class="notice warn" role=alert' in page, "a refusal must not render as a success"


def test_the_refusal_names_the_field_and_what_was_typed(
    client: TestClient, state: SessionState
) -> None:
    _add(client, _uid(state), days="5 days", pct="20")
    page = client.get("/sra").text
    assert "Impact (working days)" in page
    assert "5 days" in page


def test_a_valid_row_still_registers_and_reports_no_error(
    client: TestClient, state: SessionState
) -> None:
    """The regression bound — the fix must not make the ordinary path noisy."""
    _add(client, _uid(state), pct="20")
    assert len(state.sra_risks) == 1
    assert state.sra_risks[0].impact_pct == pytest.approx(20.0)
    assert state.sra_risks[0].impact_days > 0, "the absent magnitude must still DERIVE"
    page = client.get("/sra").text
    assert "Risk not added" not in page
    assert "role=alert" not in page


def test_the_banner_is_one_shot(client: TestClient, state: SessionState) -> None:
    _add(client, _uid(state), days="abc", pct="20")
    assert "Risk not added" in client.get("/sra").text
    assert "Risk not added" not in client.get("/sra").text
    assert state.sra_import_is_error is False


# --- the SSI setup upload ------------------------------------------------------------


def test_an_oversized_setup_is_refused_with_a_message(client: TestClient) -> None:
    blob = b"{" + b" " * (_MAX_SETUP_BYTES + 8) + b"}"
    client.post(
        "/sra/ssi/load",
        files={"setup": ("setup.json", blob, "application/json")},
        follow_redirects=False,
    )
    page = client.get("/sra").text
    assert "SSI setup not loaded" in page and "cap" in page
    assert 'class="notice warn" role=alert' in page


def test_unreadable_setup_json_is_reported_not_silently_ignored(client: TestClient) -> None:
    client.post(
        "/sra/ssi/load",
        files={"setup": ("setup.json", b"{not json", "application/json")},
        follow_redirects=False,
    )
    page = client.get("/sra").text
    assert "SSI setup not loaded" in page and "not readable JSON" in page
    assert 'class="notice warn" role=alert' in page


def test_setup_json_that_is_not_an_object_is_reported(client: TestClient) -> None:
    client.post(
        "/sra/ssi/load",
        files={"setup": ("setup.json", b"[1,2,3]", "application/json")},
        follow_redirects=False,
    )
    page = client.get("/sra").text
    assert "not an SSI setup object" in page


def test_a_good_setup_load_confirms_and_is_not_an_error(client: TestClient) -> None:
    body = json.dumps({"low": 0.9, "ml": 1.0, "high": 1.1}).encode()
    client.post(
        "/sra/ssi/load",
        files={"setup": ("setup.json", body, "application/json")},
        follow_redirects=False,
    )
    page = client.get("/sra").text
    assert "SSI setup loaded." in page
    assert 'class="notice ok" role=status' in page


def test_the_setup_cap_is_far_below_the_schedule_file_cap(client: TestClient) -> None:
    """Reusing the 500 MB `.mpp` bound for a setup JSON would be a cap in name only."""
    from schedule_forensics.web.app import _MAX_UPLOAD_BYTES

    assert _MAX_SETUP_BYTES < _MAX_UPLOAD_BYTES // 50
