"""Every ⤓ EXCEL button on every page is wired, and every wire answers (ADR-0360).

The design law (rank 3) says the ⤓ renders ONLY when the panel carries a ``data-export`` URL
to an existing endpoint — "never a dead link". Nothing enforced it: a builder that passed
``export_title`` without attaching the attribute shipped a silently dead button, and a wired
URL that 4xx'd shipped a dead click. This sweep renders every parameterless GET page on a
five-version load and asserts both halves, panel by panel.

The click feedback is pinned too: some exports run a model server-side (the SRA workbook was
measured at 140 s before its run-reuse fix), and ``panelkit.js`` must keep the button honestly
in PREPARING state for the wait instead of doing nothing visible at all.
"""

from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

REPO = Path(__file__).resolve().parents[2]
FIX = REPO / "tests" / "fixtures" / "test_projects"
STATIC = REPO / "src" / "schedule_forensics" / "web" / "static"


class _PanelWalk(HTMLParser):
    """Every .panel with a [data-sf-excel] button → (title, data-export-or-None)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[list[object]] = []  # [is_panel, data_export, title, has_excel]
        self.out: list[tuple[str, str | None]] = []
        self._h2_depth: int | None = None
        self._h2 = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "div":
            cls = (a.get("class") or "").split()
            self.stack.append([("panel" in cls), a.get("data-export"), None, False])
        elif tag == "h2" and self.stack:
            self._h2_depth = len(self.stack)
            self._h2 = ""
        elif tag == "button" and "data-sf-excel" in a:
            for fr in reversed(self.stack):
                if fr[0]:
                    fr[3] = True
                    if a.get("data-export"):
                        fr[1] = fr[1] or a.get("data-export")
                    break

    def handle_data(self, data: str) -> None:
        if self._h2_depth is not None:
            self._h2 += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2" and self._h2_depth is not None:
            for fr in reversed(self.stack):
                if fr[0] and fr[2] is None:
                    fr[2] = self._h2.strip()[:70]
                    break
            self._h2_depth = None
        elif tag == "div" and self.stack:
            fr = self.stack.pop()
            if fr[0] and fr[3]:
                self.out.append((str(fr[2] or "?"), fr[1] if isinstance(fr[1], str) else None))


@pytest.fixture(scope="module")
def loaded() -> TestClient:
    c = TestClient(create_app(SessionState()))
    paths = [FIX / f"TP4_DataCenter_v{i}.xml" for i in range(1, 6)]
    files = [("files", (p.name, p.read_bytes(), "text/xml")) for p in paths]
    meta = json.dumps(
        [
            {"rel": f"TP4/{p.name}", "mtime": 1_700_000_000_000 + i * 86_400_000}
            for i, p in enumerate(paths)
        ]
    )
    assert c.post("/upload", files=files, data={"file_meta": meta}).status_code == 200
    return c


def _pages(client: TestClient) -> list[str]:
    app = client.app
    out = set()
    for r in app.routes:  # type: ignore[attr-defined]
        path = getattr(r, "path", "")
        methods = getattr(r, "methods", None) or set()
        if (
            "GET" in methods
            and "{" not in path
            and not path.startswith(("/api", "/export", "/download", "/static"))
        ):
            out.add(path)
    return sorted(out)


def test_no_page_ships_an_excel_button_without_a_data_export_wire(loaded: TestClient) -> None:
    dead: list[str] = []
    for page in _pages(loaded):
        r = loaded.get(page)
        if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
            continue
        walker = _PanelWalk()
        walker.feed(r.text)
        dead += [f"{page}: {title!r}" for title, url in walker.out if not url]
    assert not dead, (
        "panels render a ⤓ EXCEL button with no data-export wire — the click silently does "
        f"nothing (the rank-3 'never a dead link' law): {dead}"
    )


def test_every_wired_export_url_answers(loaded: TestClient) -> None:
    checked: set[str] = set()
    broken: list[str] = []
    for page in _pages(loaded):
        r = loaded.get(page)
        if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
            continue
        walker = _PanelWalk()
        walker.feed(r.text)
        for title, url in walker.out:
            if not url or url in checked:
                continue
            checked.add(url)
            rr = loaded.get(url)
            if rr.status_code != 200:
                broken.append(f"{page}: {title!r} -> {url} = {rr.status_code}")
    assert checked, "the sweep found no wired exports at all — the walker is broken, fix IT"
    assert not broken, f"wired ⤓ EXCEL URLs that do not answer 200: {broken}"


def test_panelkit_gives_immediate_feedback_and_a_navigation_fallback() -> None:
    """The ADR-0360 click contract: busy-guarded PREPARING state, blob download on success,
    plain navigation on ANY failure (so nothing regresses if fetch is unavailable)."""
    src = (STATIC / "panelkit.js").read_text(encoding="utf-8")
    assert "⤓ PREPARING…" in src
    assert "data-sf-busy" in src
    assert "window.location.href = url" in src, "the fallback navigation must survive"
    assert "URL.createObjectURL" in src and "revokeObjectURL" in src
