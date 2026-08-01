"""OR-06 — a fresh launch / session wipe invalidates the per-page selection memory.

Operator bug (verbatim intent): a fresh open of the deployed tool showed fields populated
from PREVIOUS sessions (e.g. a Target UID from a project never loaded), even after
wipe-then-Quit. Mechanism: ADR-0186's ``sf-qs:``/``sf-ui:`` layers live in browser
localStorage, which survives server quit/wipe by design — nothing invalidated them.

The fix: every page serves ``<meta name=sf-launch>`` (per-process nonce + wipe
generation); ``persist.js`` clears the page-memory layers (and the per-page
column-picker keys) when the served token differs from the one it stored — and ONLY
then, so ADR-0186's within-session memory and the global prefs (theme / UI scale /
Timescale) are untouched.
"""

from __future__ import annotations

import re
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web import state as state_mod
from schedule_forensics.web.app import SessionState, create_app

STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"
CHROME_DIR = Path("/opt/pw-browsers")

_META = re.compile(r'<meta name=sf-launch content="([^"]+)">')


def _token(html: str) -> str:
    m = _META.search(html)
    assert m, "page is missing the <meta name=sf-launch> launch token"
    return m.group(1)


def test_every_page_serves_the_launch_token_and_it_is_stable_within_a_session() -> None:
    st = SessionState()
    client = TestClient(create_app(st))
    first = _token(client.get("/").text)
    assert first == st.launch_token
    assert _token(client.get("/settings").text) == first  # stable across pages/requests
    assert first.startswith(f"{state_mod._LAUNCH_NONCE}.")


def test_wipe_rotates_the_launch_token() -> None:
    st = SessionState()
    client = TestClient(create_app(st))
    before = _token(client.get("/").text)
    client.post("/session/wipe", follow_redirects=False)  # one-shot banner stays unconsumed
    after = _token(client.get("/").text)
    assert after != before
    assert after == st.launch_token


def test_persist_js_carries_the_launch_guard() -> None:
    js = (STATIC / "persist.js").read_text(encoding="utf-8")
    assert 'meta[name="sf-launch"]' in js
    # clears exactly the page-memory layers (plus page keys) — never the global prefs
    assert '"sf-qs:"' in js and '"sf-ui:"' in js
    assert 'ls.setItem("sf-launch", token)' in js
    # the guard must run BEFORE the query-string replay, or a stale ?target= replays once
    assert js.index('meta[name="sf-launch"]') < js.index("layer 1: query-string memory")


# ---- behavioral proof in a real browser --------------------------------------------------

_chrome = sorted(CHROME_DIR.glob("chromium-*/chrome-linux/chrome")) if CHROME_DIR.exists() else []


@pytest.fixture()
def served() -> Any:
    """The real app on a real port (persist.js needs a browser, not TestClient)."""
    import uvicorn

    st = SessionState()
    app = create_app(st)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 15
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started, "uvicorn did not start"
    yield f"http://127.0.0.1:{port}", st
    server.should_exit = True


@pytest.mark.skipif(not _chrome, reason=f"bundled chromium not under {CHROME_DIR}")
def test_stale_launch_clears_page_memory_and_live_launch_keeps_it(served: Any) -> None:
    """Both halves of OR-06 in one browser session: selections stored under a PREVIOUS
    launch token are cleared on the next load (the operator's stale Target UID can never
    resurface), while selections stored under the CURRENT token survive a reload
    (ADR-0186's within-session memory) — and the global theme preference survives both."""
    from playwright.sync_api import sync_playwright

    base, _st = served
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(_chrome[-1]))
        page = browser.new_page()
        page.goto(base + "/", wait_until="domcontentloaded")

        # simulate the PREVIOUS session: stale page memory + a stale launch marker + a theme
        page.evaluate(
            "() => { localStorage.setItem('sf-qs:/sra', '?target=6077');"
            ' localStorage.setItem(\'sf-ui:/sra\', \'{"#staleField":{"v":"6077"}}\');'
            " localStorage.setItem('sf-findings-drill-cols', 'stale');"
            # ADR-0332: story progress is CROSS-page, so the two per-page prefixes above never
            # matched it — and its entries are chapter data-routes, which for the analysis
            # chapter resolve to "/analysis/<the operator's filename>". A schedule name from a
            # previous project therefore sat in browser storage indefinitely and tinted a
            # brand-new session's progress strip.
            " localStorage.setItem('sf-story-visited', '[\"/analysis/SecretProject.mpp\"]');"
            " localStorage.setItem('sf-theme', 'daylight');"
            # a preference that must SURVIVE: muting the ADR-0328 boot hum is an operator choice,
            # not session state, and a sweep that un-mutes it every launch is a regression.
            " localStorage.setItem('sf-hum-mute', '1');"
            " localStorage.setItem('sf-launch', 'deadbeef.0'); }"
        )
        page.reload(wait_until="domcontentloaded")
        remaining = page.evaluate(
            "() => [localStorage.getItem('sf-qs:/sra'), localStorage.getItem('sf-ui:/sra'),"
            " localStorage.getItem('sf-findings-drill-cols'),"
            " localStorage.getItem('sf-theme'), localStorage.getItem('sf-launch'),"
            " localStorage.getItem('sf-story-visited'), localStorage.getItem('sf-hum-mute')]"
        )
        assert remaining[0] is None, "stale sf-qs survived a new launch"
        assert remaining[1] is None, "stale sf-ui survived a new launch"
        assert remaining[2] is None, "stale column-picker key survived a new launch"
        assert remaining[3] == "daylight", "global theme pref must NOT be cleared"
        # NOT `is None`: the guard clears the key, and then story.js — running on this same load —
        # legitimately re-records the chapter being viewed right now. The property that matters is
        # that nothing from the PREVIOUS project remains, so assert on the content.
        assert "SecretProject" not in (remaining[5] or ""), (
            f"a previous project's filename survived in sf-story-visited: {remaining[5]!r}"
        )
        assert remaining[6] == "1", "the boot-hum mute is a PREFERENCE and must not be cleared"
        live_token = remaining[4]
        assert live_token and live_token != "deadbeef.0"

        # same launch: memory recorded NOW must survive a reload (ADR-0186 intact)
        page.evaluate("() => localStorage.setItem('sf-qs:/sra', '?target=42')")
        page.reload(wait_until="domcontentloaded")
        kept = page.evaluate("() => localStorage.getItem('sf-qs:/sra')")
        assert kept == "?target=42", "within-session page memory must survive a reload"
        browser.close()
