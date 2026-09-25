"""Executable reproducers for the AUDIT-2026-09-23 findings in the WEB lane (A0923-WEB-001..002).

Campaign: AUDIT-2026-09-23, a read-only audit of base 8c71c639 (v1.0.289). AUDIT + PLAN ONLY:
the audit changed nothing under ``src/``; these tests are the evidence a fixing PR inherits.

Every test asserts the CORRECT behaviour and is marked ``xfail(strict=True, raises=...)`` with the
exception observed red-first on the audited tree, so the suite stays green while the defect exists:

  * XFAIL  -- the defect is still present (the expected state until it is fixed).
  * XPASS  -- the defect is gone. Under ``strict=True`` an XPASS FAILS the run and names the test:
    that is the signal. The fixing PR removes that test's marker in the same commit, and the test
    stays behind as the permanent regression pin.
  * FAILED with an exception other than the marker's ``raises`` -- a precondition moved (every
    precondition is a ``pytest.fail``, never an ``assert``, so a broken setup can never pass for
    the expected xfail) or the defect changed shape. Investigate; do not re-mark.

Everything runs in-process through FastAPI's TestClient (no server, no browser): the browser half
of A0923-WEB-001 was measured in Chromium by the verifier and is pinned here on the SERVED
``home.js``. Inputs are built inline; no fixture file is added and nothing is CUI; an autouse
fixture refuses every non-loopback connect and name lookup. Drop-in path: ``tests/audit/``.
Run: ``pytest tests/audit/test_audit_20260923_web.py -rxX``.
"""

from __future__ import annotations

import json
import re
import socket
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})


@pytest.fixture(autouse=True)
def _air_gapped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-test state dirs, and no way off the machine: a non-loopback connect or any name lookup
    other than a loopback literal raises before a packet is sent."""
    for var in ("SF_SETTINGS_DIR", "SF_AI_LOG_DIR", "SF_CACHE_DIR"):
        monkeypatch.setenv(var, str(tmp_path / var))
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect

    def getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
        name = host.decode() if isinstance(host, bytes) else host
        if name is not None and str(name) not in _LOOPBACK:
            raise OSError(f"air-gapped test: name lookup of {name!r} refused")
        return real_getaddrinfo(host, *args, **kwargs)

    def connect(self: socket.socket, address: Any) -> None:
        if isinstance(address, tuple) and str(address[0]) not in _LOOPBACK:
            raise OSError(f"air-gapped test: connect to {address!r} refused")
        real_connect(self, address)

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", connect)


_PLAN = json.dumps(
    {
        "name": "Folder plan",
        "project_start": "2026-01-05T08:00:00",
        "calendars": [{"name": "Standard", "hours_per_day": 8}],
        "tasks": [
            {"unique_id": 1, "name": "Design", "duration_minutes": 2400},
            {"unique_id": 2, "name": "Build", "duration_minutes": 4800},
        ],
        "relationships": [{"predecessor_id": 1, "successor_id": 2, "type": "FS"}],
    }
).encode("utf-8")


def _folder_parts(others: int) -> list[tuple[str, tuple[str, bytes, str]]]:
    """One schedule plus ``others`` non-schedule files — a picked folder, as home.js posts it."""
    parts = [("files", ("plan.json", _PLAN, "application/json"))]
    parts += [
        ("files", (f"notes-{i:04d}.pdf", b"%PDF-1.4 not a schedule", "application/pdf"))
        for i in range(others)
    ]
    return parts


# --------------------------------------------------------------------------------------------
# A0923-WEB-001 (T4): a >1000-file upload is refused 400 and home.js navigates away silently
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-WEB-001: POST /upload with more than 1000 file parts answers 400 'Too many "
    "files. Maximum number of files is 1000.' (Starlette's multipart default) and home.js never "
    "reads resp.ok before navigating to '/', so the refused ingest is silent",
)
def test_a0923_web_001_a_large_folder_upload_loads_or_fails_loudly() -> None:
    """Claim: at 8c71c639 POST /upload with 1001 file parts (here one schedule plus 1000
    non-schedule files, a picked folder) answers 400 {"detail": "Too many files. Maximum number of
    files is 1000."} with nothing loaded, and home.js's upload() navigates to '/' without reading
    the response status, so the operator sees the unchanged dashboard and no message (Chromium:
    pick and drop, verifier); a 1000-part batch loads.

    Authority: docs/adr/0225-grouped-ingestion-and-portfolio.md:21-24 "Operator rules
    (confirmed): loose files group by document Title; **a folder — any nesting depth — is exactly
    one Project named by its top folder**, every schedule beneath it a version (sub-folders are
    just filing and are ignored); **no file-count cap**." and README.md:69-70 "the dashboard
    tells you exactly what loaded and what failed (no silent failures)."

    Tier: T4 (not LAW-1). Correct = the batch loads (no cap), or the refusal reaches the operator
    (home.js reads the status before it navigates); the browser half is pinned on the served JS.
    """
    control_state = SessionState()
    control = TestClient(create_app(control_state))
    ok = control.post(
        "/upload", files=_folder_parts(999), data={"file_meta": "[]"}, headers={"X-SF-Ajax": "1"}
    )
    if ok.status_code != 200 or len(control_state.schedules) != 1:
        pytest.fail(f"precondition: a 1000-part folder batch loads its schedule ({ok.status_code})")
    state = SessionState()
    client = TestClient(create_app(state))
    resp = client.post(
        "/upload", files=_folder_parts(1000), data={"file_meta": "[]"}, headers={"X-SF-Ajax": "1"}
    )
    js = client.get("/static/home.js").text
    start = js.find("fetch('/upload'")
    navigate = js.find("window.location", start)
    if start < 0 or navigate < 0:
        pytest.fail("precondition: the served home.js POSTs /upload by fetch, then navigates")
    reads_status = re.search(r"\bresp\.(?:ok|status)\b", js[start:navigate]) is not None
    loaded = resp.status_code == 200 and len(state.schedules) == 1
    problems = []
    if not loaded and not reads_status:
        problems.append(
            f"/upload answered {resp.status_code} {resp.text[:80]!r} with "
            f"{len(state.schedules)} loaded, and home.js navigates without reading resp.ok/status"
        )
    assert problems == [], "\n".join(problems)


# --------------------------------------------------------------------------------------------
# A0923-WEB-002 (T4): a malformed AI endpoint 500s two routes and makes the launch fail
# --------------------------------------------------------------------------------------------
_DEFAULT_ENDPOINT = "http://127.0.0.1:11434"
_MALFORMED = ("http://[", "http://a\uff20127.0.0.1:11434", "http://[::1:11434")


@pytest.mark.xfail(
    strict=True,
    raises=ValueError,
    reason="A0923-WEB-002: net_guard.is_local_http_endpoint lets urlparse's ValueError escape "
    "('Invalid IPv6 URL', NFKC netloc), so a settings file carrying 'http://[' makes create_app() "
    "raise, and POST /settings and GET /api/ai/models answer 500",
)
def test_a0923_web_002_a_malformed_endpoint_falls_back_instead_of_raising(
    tmp_path: Path,
) -> None:
    """Claim: at 8c71c639 an endpoint urllib.parse cannot split ('http://[', a fullwidth-@
    netloc, the typo 'http://[::1:11434') makes net_guard.is_local_http_endpoint RAISE ValueError
    instead of returning False: a hand-edited ai-settings.json carrying it makes create_app() (the
    desktop-launch path) raise, and POST /settings and GET /api/ai/models?kind=ollama answer 500.

    Authority: docs/adr/0404-persistent-ai-settings.md:37-42 "3. **Loading is a trust boundary.**
    The file is operator-editable state, so loading re-applies the POST sanitizers: ...
    non-loopback local endpoints fall back to defaults, ... Missing or corrupt files yield pure
    defaults — a launch never fails on settings."

    Tier: T4 (not LAW-1: every raising path fails closed). Sibling not asserted: POST /language
    500s on a malformed Referer (web/app.py:7941).
    """
    settings = tmp_path / "SF_SETTINGS_DIR" / "ai-settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    problems: list[str] = []
    for bad in _MALFORMED:
        settings.write_text(
            json.dumps({"schema": 1, "backend": "ollama", "endpoint": bad}), encoding="utf-8"
        )
        endpoint = create_app().state.session.ai_config.endpoint  # the launch path
        if endpoint != _DEFAULT_ENDPOINT:
            problems.append(f"launch with {bad!r} kept endpoint {endpoint!r}")
    client = TestClient(create_app(SessionState()))
    for bad in _MALFORMED:
        saved = client.post("/settings", data={"endpoint": bad}, follow_redirects=False)
        if saved.status_code != 303:
            problems.append(f"POST /settings endpoint={bad!r} -> {saved.status_code}")
        probe = client.get("/api/ai/models", params={"kind": "ollama", "endpoint": bad})
        if probe.status_code != 200 or probe.json().get("reachable") is not False:
            problems.append(f"GET /api/ai/models endpoint={bad!r} -> {probe.status_code}")
    assert problems == [], "\n".join(problems)
