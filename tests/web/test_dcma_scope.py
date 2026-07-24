"""ADR-0280: the single Acumen-parity DCMA toggle on the analysis page.

The Acumen-parity mode (baselined population, whole-day float, Baseline-Cost/Work resources,
stored-float CPLI, two-term BEI) is exposed as one per-session toggle that supersedes the former
milestone-scope + CPLI checkboxes. This pins the seam: the control + its explanation render, the
POST flips the session flag (which is part of the analysis cache signature, so the audit re-keys),
and the checkbox reflects state — without asserting numbers a browser can't see.
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


def test_parity_toggle_renders_flips_the_flag_and_reflects_state(
    loaded: tuple[TestClient, SessionState, str],
) -> None:
    client, st, key = loaded
    page = client.get(f"/analysis/{key}")
    assert page.status_code == 200
    assert 'action="/dcma/scope"' in page.text  # the toggle form is on the page
    assert "Acumen" in page.text and "parity" in page.text  # the control + its explanation
    assert "When to use" in page.text  # the example-driven explanatory panel
    # ADR-0287: parity is ON by default so a fresh session reconciles with Acumen Fuse out of the
    # box; the box therefore renders checked, and the scope signature already carries A=1.
    assert st.dcma_acumen_parity is True
    assert st._scope_signature() == "A=1"
    assert "value=1 checked" in page.text  # the input itself, not the prose

    # unchecking (no parity field posted) clears it -> the pure-logic / forensic view
    r = client.post("/dcma/scope", data={"next": f"/analysis/{key}"})
    assert r.status_code == 200  # followed the 303 back to the analysis page
    assert st.dcma_acumen_parity is False
    # the flag is part of the analysis cache signature so a toggle can't serve a stale audit
    assert st._scope_signature() == ""
    assert "value=1 checked" not in client.get(f"/analysis/{key}").text

    # re-enabling flips it back (funnels through set_dcma_acumen_parity)
    client.post("/dcma/scope", data={"parity": "1", "next": f"/analysis/{key}"})
    assert st.dcma_acumen_parity is True
    assert st._scope_signature() == "A=1"


def test_scope_redirect_is_local_only(loaded: tuple[TestClient, SessionState, str]) -> None:
    """The ``next`` redirect target is sanitised to a local path (no open redirect)."""
    client, _st, _key = loaded
    r = client.post(
        "/dcma/scope", data={"parity": "1", "next": "//evil.example/x"}, follow_redirects=False
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/"
