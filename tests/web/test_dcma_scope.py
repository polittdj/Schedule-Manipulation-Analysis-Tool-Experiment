"""ADR-0277 / ADR-0279: the DCMA Acumen-parity toggles on the analysis page.

Two per-session Acumen-parity options share one form: the milestone scope (ADR-0277 — exclude
zero-duration milestones from Logic / SS-FF / Hard-constraint / Negative-float) and the stored-float
CPLI (ADR-0279 — CPLI from the stored Total Slack + stored finish). This pins the seams: the
controls render, each POST flips its session flag (each flag is part of the analysis cache
signature, so the audit re-keys), and the checkboxes reflect state — without asserting numbers a
browser can't see.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


@pytest.fixture
def loaded() -> tuple[TestClient, SessionState, str]:
    st = SessionState()
    client = TestClient(create_app(st))
    data = (GOLDEN / "project2_5" / "Project5.mspdi.xml").read_bytes()
    assert (
        client.post(
            "/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")}
        ).status_code
        == 200
    )
    key = next(iter(st.schedules))
    return client, st, key


def test_toggle_renders_flips_the_flag_and_reflects_state(
    loaded: tuple[TestClient, SessionState, str],
) -> None:
    client, st, key = loaded
    page = client.get(f"/analysis/{key}")
    assert page.status_code == 200
    assert 'action="/dcma/scope"' in page.text  # the toggle form is on the page
    assert "Acumen milestone scope" in page.text
    assert st.dcma_exclude_milestones is False  # default off (prior behaviour / golden parity)

    # enabling it flips the session flag (funnels through set_dcma_exclude_milestones)
    r = client.post("/dcma/scope", data={"exclude_ms": "1", "next": f"/analysis/{key}"})
    assert r.status_code == 200  # followed the 303 back to the analysis page
    assert st.dcma_exclude_milestones is True
    # the flag is part of the analysis cache signature so a toggle can't serve a stale audit
    assert st._scope_signature() == "M=1"
    assert "checked" in client.get(f"/analysis/{key}").text

    # unchecking (no exclude_ms field posted) clears it again
    client.post("/dcma/scope", data={"next": f"/analysis/{key}"})
    assert st.dcma_exclude_milestones is False
    assert st._scope_signature() == ""


def test_cpli_stored_float_toggle_flips_flag_and_signature(
    loaded: tuple[TestClient, SessionState, str],
) -> None:
    """ADR-0279: the stored-float CPLI checkbox renders, flips its own session flag + scope
    signature (``C=1``), and composes with the milestone toggle (both on → ``M=1``+``C=1``)."""
    client, st, key = loaded
    page = client.get(f"/analysis/{key}")
    assert "Acumen CPLI (stored float)" in page.text  # the second control is on the page
    assert st.dcma_cpli_stored_float is False

    # enabling CPLI alone flips its flag and adds C=1 (milestone stays off)
    r = client.post("/dcma/scope", data={"cpli_stored": "1", "next": f"/analysis/{key}"})
    assert r.status_code == 200
    assert st.dcma_cpli_stored_float is True and st.dcma_exclude_milestones is False
    assert st._scope_signature() == "C=1"

    # both on: the form submits both fields together → both flags, both signature parts
    client.post(
        "/dcma/scope",
        data={"exclude_ms": "1", "cpli_stored": "1", "next": f"/analysis/{key}"},
    )
    assert st.dcma_exclude_milestones is True and st.dcma_cpli_stored_float is True
    assert st._scope_signature() == "M=1\x1fC=1"

    # unchecking both (neither field posted) clears them
    client.post("/dcma/scope", data={"next": f"/analysis/{key}"})
    assert st.dcma_cpli_stored_float is False and st.dcma_exclude_milestones is False
    assert st._scope_signature() == ""


def test_scope_redirect_is_local_only(loaded: tuple[TestClient, SessionState, str]) -> None:
    """The ``next`` redirect target is sanitised to a local path (no open redirect)."""
    client, _st, _key = loaded
    r = client.post(
        "/dcma/scope", data={"exclude_ms": "1", "next": "//evil.example/x"}, follow_redirects=False
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/"
