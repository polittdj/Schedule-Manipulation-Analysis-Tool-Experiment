"""Gantt standardization (operator 2026-07-09, ADR-0180): the always-visible bottom scrollbar
is a shared SFGantt primitive auto-attached to every standard Gantt scroll pane, so every
Gantt across the tool inherits it (alongside the already-shared frozen header + frozen data
columns + tier timeline). This pins the shared wiring; the interactive sync is Chromium-verified."""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "fuse_hardfile"
STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    for name in ("Hard_File_updated2", "Hard_File_updated3"):
        xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes())
        c.post("/upload", files={"files": (f"{name}.mspdi.xml", xml, "text/xml")})
    return c


def test_sticky_scrollbar_is_a_shared_gantt_primitive() -> None:
    js = (STATIC / "gantt.js").read_text(encoding="utf-8")
    # the primitive + the multi-pane attacher over every standard Gantt container class
    assert "stickyScrollbar" in js and "attachStickyScrollbars" in js
    for sel in ("#grid", ".gantt-scroll", ".path-view", ".sra-grid-scroll"):
        assert sel in js, sel
    # auto-init at load + a MutationObserver so async-built panes are caught too
    assert "MutationObserver" in js and "attachStickyScrollbars(document)" in js
    # the proxy scrollbar drives / mirrors the pane's scrollLeft
    assert "pane.scrollLeft" in js and "bar.scrollLeft" in js
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    assert ".sf-sticky-xscroll" in css and "position: fixed" in css


def test_gantt_pages_load_the_shared_gantt_primitive(client: TestClient) -> None:
    """Every Gantt-bearing page includes gantt.js (which auto-attaches the sticky scrollbar)."""
    for path in ("/analysis/Hard_File_updated3", "/path?target=411", "/driving-path?target=411"):
        assert "/static/gantt.js" in client.get(path).text, path
