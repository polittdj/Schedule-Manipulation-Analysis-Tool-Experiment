"""AI Settings shows only the backend in use — measured in Chromium (OR-16b, ADR-0488).

The server test pins the markers; this one pins what the page DOES with them: under a gateway
session the Ollama endpoint, the Ollama window and the local server's token are not visible and
the gateway rows are; switching the backend picker to Ollama flips them live, no save; turning
the cross-check on for the OpenAI-compatible server shows that server's rows while the primary
stays Ollama; and every hidden field is still part of the form (it posts). The gateway is
stubbed at both server surfaces (the page banner and the models probe) so nothing leaves the
machine.
"""

from __future__ import annotations

import socket
import tempfile
import threading
import time
import urllib.error
from pathlib import Path
from typing import Any

import pytest

from schedule_forensics.ai.gateway import GatewayBackend
from web.browser_chrome import chrome_kwargs

LOG = Path(tempfile.mkdtemp()) / "tx.jsonl"

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")

ENDPOINT = "https://proxy.fast.luna.nasa.gov"
THEMES = ("console", "daylight", "apollo", "jarvis")


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


def _never(url: str, data: bytes | None, timeout: float, headers: Any) -> str:
    raise urllib.error.HTTPError(url, 401, "refused", None, None)  # type: ignore[arg-type]


class _Refused(GatewayBackend):
    """The gateway as the operator photographed it: reachable, refusing the credential — the
    real class over an opener that never opens a socket, so routing, the banner and the models
    probe all see one consistent refusal and nothing leaves the machine."""

    def __init__(self, *a: Any, **k: Any) -> None:
        k["opener"] = _never
        k.setdefault("log_path", LOG)
        super().__init__(*a, **k)

    def unavailable_reason(self) -> str:
        return "server returned HTTP 401"

    def list_models(self) -> tuple[str, ...]:
        return ()


@pytest.fixture(scope="module")
def served() -> Any:
    import uvicorn
    from fastapi.testclient import TestClient

    import schedule_forensics.web.app as app_module
    import schedule_forensics.web.settings as settings_module
    from schedule_forensics.web.app import SessionState, create_app

    mp = pytest.MonkeyPatch()
    mp.setattr(settings_module, "_gateway_or_none", lambda cfg: _Refused(ENDPOINT, model="m"))
    mp.setattr(app_module, "GatewayBackend", _Refused)
    app = create_app(SessionState())
    with TestClient(app) as c:
        r = c.post(
            "/settings",
            data={
                "classification": "CLASSIFIED",
                "backend": "gateway",
                "model": "claude-opus-4.8-thinking-itar",
                "gateway_endpoint": ENDPOINT,
                "gateway_approved": "1",
                "gateway_api_key": "k" * 25,
            },
            follow_redirects=False,
        )
        assert r.status_code == 303
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    mp.undo()


_VISIBLE = """(sel) => {
  const el = document.querySelector(sel); if (!el) return null;
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.height > 0 && !el.closest('[hidden]'); }"""


def _visible(page: Any, selector: str) -> bool:
    got = page.evaluate(_VISIBLE, selector)
    assert got is not None, f"{selector} is not on the page"
    return bool(got)


@pytest.mark.parametrize("theme", THEMES)
def test_only_the_backend_in_use_is_shown_and_the_pickers_flip_it_live(
    served: str, theme: str
) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        ctx.add_init_script(f"try{{localStorage.setItem('sf-theme','{theme}')}}catch(e){{}}")
        page = ctx.new_page()
        page.goto(f"{served}/settings", wait_until="load")
        page.wait_for_selector("#backendSel")
        assert page.evaluate("() => document.documentElement.getAttribute('data-theme')") == theme
        # the gateway session: gateway rows on, the two local backends' rows off
        assert _visible(page, "select[name=gateway_endpoint]")
        assert _visible(page, "input[name=gateway_api_key]")
        assert _visible(page, "input[name=answer_max_tokens]")
        assert not _visible(page, "input[name=endpoint]")
        assert not _visible(page, "input[name=num_ctx]")
        assert not _visible(page, "input[name=openai_endpoint]")
        assert not _visible(page, "input[name=openai_api_key]")
        # the always-on rows
        for always in (
            "classification",
            "backend",
            "model",
            "gen_timeout",
            "qa_mode",
            "second_backend",
        ):
            assert _visible(page, f"[name={always}]"), always
        # the picker flips the rows live — no save, no reload
        page.select_option("#backendSel", "ollama")
        assert _visible(page, "input[name=endpoint]") and _visible(page, "input[name=num_ctx]")
        assert not _visible(page, "input[name=gateway_api_key]")
        assert not _visible(page, "input[name=answer_max_tokens]")
        # the cross-check backend counts as in use
        page.select_option("#secondBackend", "openai")
        assert _visible(page, "input[name=openai_endpoint]") and _visible(
            page, "input[name=openai_api_key]"
        )
        assert _visible(page, "input[name=answer_max_tokens]")
        page.select_option("#secondBackend", "none")
        assert not _visible(page, "input[name=openai_api_key]")
        # hidden rows are still form fields: the form posts every name the server reads
        names = page.evaluate(
            "() => [...document.querySelectorAll('form[action=\"/settings\"] [name]')]"
            ".map(e => e.name)"
        )
        for expected in (
            "endpoint",
            "openai_endpoint",
            "openai_api_key",
            "gateway_endpoint",
            "gateway_api_key",
            "num_ctx",
            "answer_max_tokens",
        ):
            assert expected in names, expected
        # hiding rows can only narrow the document: the disclosed page is never wider than the
        # same page with every row forced visible. (The page's own sideways scroll — 1,877 px in
        # console / apollo / jarvis, 1,641 in daylight at a 1,440 viewport, an over-wide <select>
        # — is the registered /settings residual, its own unit, measured here and not hidden.)
        sw_disclosed = page.evaluate("() => document.scrollingElement.scrollWidth")
        page.evaluate(
            "() => document.querySelectorAll('[data-backend-only]')"
            ".forEach(e => { e.hidden = false; })"
        )
        sw_all = page.evaluate("() => document.scrollingElement.scrollWidth")
        assert sw_disclosed <= sw_all, (sw_disclosed, sw_all)
        browser.close()
