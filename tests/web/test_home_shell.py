"""Home / Import screen shell (Mission Ops slice 1 — PROLOGUE · LOAD).

The '/' page gains the prototype screen header (kicker + complete-sentence takeaway + lede)
and the panel contract (headline strip, ⤓/⛶ tools, provenance chips) WITHOUT losing any
pre-existing element — the never-remove law is asserted here alongside the new shell, and the
--bgfx atmosphere amendments (attachment longhand, apollo scanline folded into the token) are
pinned so a refactor can't silently re-break them. Pure presentation — no engine numbers."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

EXAMPLE = (
    Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/examples/house_build.json"
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _load_example(client: TestClient) -> None:
    client.post(
        "/upload",
        files={"files": ("house_build.json", EXAMPLE.read_bytes(), "application/json")},
        follow_redirects=False,
    )


# ── (a) screen header: kicker + complete-sentence takeaway, both states ────────────────────


def test_empty_state_has_kicker_and_sentence_takeaway(client: TestClient) -> None:
    home = client.get("/").text
    assert "PROLOGUE · LOAD" in home
    assert 'class="page-takeaway"' in home
    assert "Load a schedule to begin" in home  # the empty-state sentence
    assert "nothing you load ever leaves this machine" in home
    assert "page-lede" in home


def test_loaded_state_takeaway_carries_the_number_in_the_sentence(client: TestClient) -> None:
    _load_example(client)
    home = client.get("/").text
    assert "PROLOGUE · LOAD" in home
    assert "1 version loaded from house_build.json" in home
    assert "computed, never typed" in home
    # the loaded-versions panel shell: headline strip + the two tools (▦ omitted — the
    # table IS the data) + the panel-level export URL panelkit.js follows
    assert "LOADED VERSIONS" in home and "1 FILE" in home
    assert "data-sf-excel" in home and "data-sf-big" in home
    assert 'data-export="/export/xlsx/ribbon"' in home
    assert "/static/panelkit.js" in home


# ── (b) provenance chips are i18n-inert (filenames/dates must never be translated) ─────────


def test_prov_chip_is_rendered_and_i18n_inert(client: TestClient) -> None:
    _load_example(client)
    home = client.get("/").text
    assert "<span class=prov-chip data-no-i18n>SOURCE: house_build.json · DD " in home


def test_dashboard_js_health_card_chip_is_i18n_inert(client: TestClient) -> None:
    js = client.get("/static/dashboard.js").text
    assert "prov-chip" in js and "data-no-i18n" in js


def test_panelkit_toolbar_vocabulary(client: TestClient) -> None:
    js = client.get("/static/panelkit.js").text
    for marker in (
        "data-sf-big",
        "data-sf-data",
        "data-sf-excel",
        "⛶ SHRINK",
        "▦ HIDE DATA",
        "aria-pressed",
        "addEventListener",
    ):
        assert marker in js, marker


# ── (c) never-remove law: every pre-existing element survives the new shell ────────────────


def test_legacy_elements_all_survive_empty_state(client: TestClient) -> None:
    home = client.get("/").text
    assert "id=dropzone" in home and "id=pickBtn" in home and "id=pickFolderBtn" in home
    assert 'class="notice warn"' in home or "id=uploadNotice" in home
    assert "id=loadOverlay" in home and "load-spinner" in home
    assert "class=role-strip" in home  # the role picker strip (ADR-0255)
    assert "class=hero" in home  # the legacy hero keeps rendering under the new header
    assert "id=exampleForm" in home and "/static/home.js" in home


def test_legacy_elements_all_survive_loaded_state(client: TestClient) -> None:
    _load_example(client)
    home = client.get("/").text
    assert "id=dashboardHealth" in home and "/static/dashboard.js" in home
    assert "Schedule health" in home
    # the loaded-schedules table row actions, all four of them
    for action in ("Open report", "Card", "WBS", "Save .json"):
        assert action in home, action
    assert "id=dropzone" in home  # the dropzone stays available for adding more versions


# ── (d) --bgfx amendments: attachment longhand + apollo scanline folded into the token ─────


def test_base_css_uses_background_attachment_longhand(client: TestClient) -> None:
    css = client.get("/static/base.css").text
    assert "background:var(--bgfx,var(--bg));" in css
    assert "background-attachment:fixed" in css
    # the buggy shorthand (fixed bound to the final color layer only) must not come back
    assert "var(--bgfx,var(--bg)) fixed" not in css


def test_apollo_scanline_lives_in_the_bgfx_token(client: TestClient) -> None:
    css = client.get("/static/sf-themes.css").text
    apollo = css.split("html[data-theme=apollo]", 1)[1]
    # the scanline is now a --bgfx layer (stacked with the radial glow)…
    assert "--bgfx:repeating-linear-gradient" in apollo
    assert "radial-gradient" in apollo.split("--bgfx:", 1)[1].split(";", 1)[0]
    # …and the higher-specificity body rule that clobbered the glow is gone (a comment may
    # still NAME the old rule; only the declaration form would re-break the layering)
    assert "background-image:" not in css


def test_all_four_views_define_bgfx(client: TestClient) -> None:
    css = client.get("/static/sf-themes.css").text
    for theme in ("console", "daylight", "apollo", "jarvis"):
        block = css.split(f"html[data-theme={theme}]", 1)[1]
        assert "--bgfx:" in block, theme
