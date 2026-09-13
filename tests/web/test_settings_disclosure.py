"""AI Settings shows only the fields of the backend in use (OR-16b, ADR-0488).

Operator directive 2026-09-12: *"I want the AI setup to be as user friendly and simple as
possible."* The page rendered every backend's rows at once — two look-alike masked secret
fields one above the other (the local server's token directly above the gateway key), Ollama's
endpoint, context window and runtime note under a gateway session. Every backend-specific row
now carries ``data-backend-only`` naming the backend(s) it belongs to; ``settings.js`` shows a
row when its backend is the primary OR the cross-check backend and hides it otherwise. The
server renders nothing hidden (no JavaScript: everything is visible, and every field is still
posted), and the always-on rows — classification, backend, model, timeout, answer mode, the
cross-check picker, Save — carry no marker.

Red first: on the pristine tree no row carries the marker.
"""

from __future__ import annotations

from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from schedule_forensics.web.settings import _settings_body


class _Owners(HTMLParser):
    """Which ``data-backend-only`` group (innermost) each named form control sits in."""

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str | None] = []
        self.owner: dict[str, str | None] = {}
        self.hidden_markers = 0
        self.groups: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "div":
            group = a.get("data-backend-only")
            if group is not None:
                self.groups.append(group)
            self.stack.append(group)
        if "hidden" in a and a.get("data-backend-only") is not None:
            self.hidden_markers += 1
        name = a.get("name")
        if name and tag in ("input", "select"):
            owners = [g for g in self.stack if g is not None]
            self.owner[name] = owners[-1] if owners else None

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self.stack:
            self.stack.pop()


def _owners(page: str) -> _Owners:
    p = _Owners()
    p.feed(page)
    return p


@pytest.fixture
def page() -> str:
    return TestClient(create_app(SessionState())).get("/settings").text


def test_every_backend_specific_row_names_its_backend(page: str) -> None:
    o = _owners(page).owner
    assert o["endpoint"] == "ollama" and o["num_ctx"] == "ollama"
    assert o["openai_endpoint"] == "openai" and o["openai_api_key"] == "openai"
    assert o["gateway_endpoint"] == "gateway"
    assert o["gateway_approved"] == "gateway" and o["gateway_api_key"] == "gateway"
    assert o["answer_max_tokens"] == "openai gateway"


def test_the_always_on_rows_carry_no_marker(page: str) -> None:
    o = _owners(page).owner
    for always in (
        "classification",
        "backend",
        "model",
        "gen_timeout",
        "qa_mode",
        "second_backend",
    ):
        assert o[always] is None, always


def test_the_server_hides_nothing_so_no_javascript_shows_everything(page: str) -> None:
    assert _owners(page).hidden_markers == 0


def test_the_ollama_runtime_note_belongs_to_the_ollama_group() -> None:
    note = '<div class="notice info">Ollama environment this machine sets: X=1</div>'
    body = _settings_body(SessionState(), runtime_note=note)
    o = _owners(body)
    assert "ollama" in o.groups
    start = body.index('data-backend-only="ollama"')
    assert body.index("Ollama environment this machine sets") > start


def test_settings_js_syncs_visibility_from_both_pickers() -> None:
    from pathlib import Path

    import schedule_forensics.web as web

    js = (Path(web.__file__).parent / "static" / "settings.js").read_text(encoding="utf-8")
    assert "data-backend-only" in js
    assert "secondBackend" in js and "backendSel" in js
    assert ".hidden" in js  # the hidden attribute, never display tricks the CSS must undo
