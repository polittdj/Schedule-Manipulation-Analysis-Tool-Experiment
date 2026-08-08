"""/briefing is memoised per epoch (audit P1, ADR-0368).

The deterministic Executive Briefing was rebuilt on EVERY request — a full DCMA audit + findings
pass (each audit embedding the DCMA-12 delay-injection CPM re-solve), twice over until
``build_briefing`` handed its audit to ``recommend()`` — by all of /briefing, Mission Control
and the briefing exports. ``SessionState.briefing_for`` now builds it at most once per
(scope epoch, report day, loaded set). The guards: a warm render is BYTE-IDENTICAL to the cold
one, the build ran once, and a parity toggle re-keys the epoch (never a stale audit verdict).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    for name in ("Project2", "Project5"):
        data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
        r = c.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
        assert r.status_code == 200
    return c


def _count_builds(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Count real briefing builds at the module that CALLS build_briefing for the memo —
    ``web.state`` (the phase-1 split lesson: patch the caller's binding, not the origin)."""
    import schedule_forensics.web.state as state_mod

    calls: list[int] = []
    real = state_mod.build_briefing

    def counting(*a: Any, **k: Any) -> Any:
        calls.append(1)
        return real(*a, **k)

    monkeypatch.setattr(state_mod, "build_briefing", counting)
    return calls


def test_briefing_builds_once_and_warm_render_is_byte_identical(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _count_builds(monkeypatch)
    cold = client.get("/briefing").text
    warm = client.get("/briefing").text
    assert cold == warm  # the ADR-0368 guard: the memo changes COST, never a byte of output
    assert len(calls) == 1  # built once; the warm render served the memo
    # Mission Control and the export read the SAME memo — no further builds
    assert client.get("/").status_code == 200
    assert client.get("/export/xlsx/briefing").status_code == 200
    assert len(calls) == 1


def test_parity_toggle_rekeys_the_briefing_epoch(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _count_builds(monkeypatch)
    client.get("/briefing")
    assert len(calls) == 1
    # flipping Acumen-parity OFF changes the scope signature → the memo must NOT be served
    r = client.post("/dcma/scope", data={"next": "/briefing"}, follow_redirects=False)
    assert r.status_code in (302, 303)
    client.get("/briefing")
    assert len(calls) == 2
    # …and back ON re-keys again (single-entry memo: a flip always rebuilds, never staleness)
    client.post("/dcma/scope", data={"parity": "1", "next": "/briefing"}, follow_redirects=False)
    client.get("/briefing")
    assert len(calls) == 3


def test_changed_upload_invalidates_the_memo_but_identical_reupload_dedupes(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _count_builds(monkeypatch)
    client.get("/briefing")
    assert len(calls) == 1
    # a byte-identical re-upload is hash-deduped (ADR-0259): the session is untouched, the
    # loaded objects are the SAME, and the memo legitimately survives (the honest twin)
    data = (GOLDEN / "Project5.mspdi.xml").read_bytes()
    assert (
        client.post(
            "/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")}
        ).status_code
        == 200
    )
    client.get("/briefing")
    assert len(calls) == 1
    # a CHANGED file (same name, different bytes) re-imports → new Schedule objects → the
    # identity check must force a rebuild, never serve the stale document
    changed = data.replace(b"</Project>", b"<!-- revised --></Project>", 1)
    assert changed != data
    assert (
        client.post(
            "/upload", files={"files": ("Project5.mspdi.xml", changed, "text/xml")}
        ).status_code
        == 200
    )
    client.get("/briefing")
    assert len(calls) == 2
