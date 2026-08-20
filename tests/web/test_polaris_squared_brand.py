"""The program is named Polaris² (operator 2026-08-20, ADR-0436).

"Change the name of the program to be Polaris (squared) — like to the exponent or power
of 2." The DISPLAYED name on every surface becomes POLARIS² (U+00B2, so it renders in
window titles, terminal banners, Word/Excel exports and .lnk names alike): the masthead
wordmark gains a hand-set worm-style superscript-2 glyph (the wordmark is SVG strokes, not
text — ADR-0175), the page/boot titles, the FastAPI app title, the export titles, the
launcher's console lines, and the installer banners/shortcuts all carry it. INTERNAL
identities deliberately do not change: the ``schedule_forensics`` package, the CLI entry
point, the install directory and the venv path stay — renaming those buys nothing and
breaks upgrades-in-place (the ADR records the boundary).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "tools" / "installer"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def test_masthead_wordmark_carries_the_superscript_two(client: TestClient) -> None:
    body = client.get("/").text
    # the accessible name and hover title say POLARIS² (the SVG letters are aria-hidden)
    assert (
        'aria-label="POLARIS² —' in body
        or 'aria-label="POLARIS² &mdash;' in body
        or ('aria-label="POLARIS² ' in body)
    )
    # the hand-set superscript-2 stroke glyph is drawn, and the canvas widened to hold it
    assert "brand-sup2" in body
    assert 'viewBox="0 0 382 72"' in body


def test_page_titles_are_suffixed_polaris_squared(client: TestClient) -> None:
    assert "<title>Dashboard — POLARIS²</title>" in client.get("/").text


def test_boot_screen_title_is_polaris_squared(client: TestClient) -> None:
    assert "Launch Sequence — POLARIS²" in client.get("/launch").text


def test_fastapi_app_title_is_polaris_squared() -> None:
    app = create_app(SessionState())
    assert app.title == "POLARIS²"


def test_installer_templates_lead_with_the_new_name() -> None:
    """All three template families print the Polaris² banner (the per-file rendered-banner
    test in tests/installer/test_installers.py proves the GENERATED installers carry it
    with their embedded version — this pin covers the source the generator reads)."""
    for name in ("template.ps1", "template.sh", "template.command"):
        text = (TEMPLATES / name).read_text(encoding="utf-8")
        assert "Polaris² (Schedule Forensics) installer — v{{WHEEL_VERSION}}" in text, name
