"""ADR-0277: the DCMA milestone-scope toggle on the analysis page.

The Acumen-parity option (exclude zero-duration milestones from the Logic / SS-FF / Hard-constraint
/ High & Negative-float checks) is exposed as a per-session toggle. This pins the seam: the control
renders, the POST flips the session flag (which is part of the analysis cache signature, so the
audit re-keys), and the checkbox reflects the state — without asserting numbers a browser can't see.
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


def test_scope_redirect_is_local_only(loaded: tuple[TestClient, SessionState, str]) -> None:
    """The ``next`` redirect target is sanitised to a local path (no open redirect)."""
    client, _st, _key = loaded
    r = client.post(
        "/dcma/scope", data={"exclude_ms": "1", "next": "//evil.example/x"}, follow_redirects=False
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/"
