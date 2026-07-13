"""Session-wide target UID, the four-view theme system (ADR-0195), and the 20-file batch cap."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.importers import MAX_FILES
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
EXAMPLE = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "schedule_forensics"
    / "web"
    / "examples"
    / "house_build.json"
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


# ---- light / dark theme ----


def test_every_page_carries_theme_controls_and_script(client: TestClient) -> None:
    page = client.get("/").text
    assert 'src="/static/theme.js?v=' in page  # cache-busted (ADR-0148)
    assert 'href="/static/sf-themes.css?v=' in page  # the four-view tokens (ADR-0195)
    assert "id=themeToggle" in page
    assert "id=themeSelect" in page  # the View dropdown
    for view in ("console", "daylight", "apollo", "jarvis"):
        assert f"<option value={view}>" in page, view


def test_theme_js_persists_and_applies_data_theme(client: TestClient) -> None:
    js = client.get("/static/theme.js").text
    assert "localStorage" in js and "sf-theme" in js
    assert 'setAttribute("data-theme"' in js


def test_console_is_the_default_view_and_legacy_saves_migrate(client: TestClient) -> None:
    """ADR-0195: the tool opens in the CONSOLE view (dark mission control) by default.
    Legacy saves migrate — "light" becomes "daylight", "dark" becomes "console" — and the
    view NEVER follows the OS setting (an explicit operator choice, identical everywhere)."""
    js = client.get("/static/theme.js").text
    assert 'saved === "light"' in js and '"daylight"' in js  # light -> daylight
    assert 'saved === "dark"' in js and '"console"' in js  # dark -> console
    assert "prefers-color-scheme" not in js


def test_sf_themes_css_defines_all_four_views(client: TestClient) -> None:
    """ADR-0195: sf-themes.css carries the complete token set for every view, including the
    header chrome tokens the command banner reads (base.css keeps :root as no-JS fallback)."""
    css = client.get("/static/sf-themes.css").text
    for view in ("console", "daylight", "apollo", "jarvis"):
        assert f"html[data-theme={view}]" in css, view
    assert css.count("--header-bg:") >= 4
    assert css.count("--header-ink:") >= 4
    assert css.count("--header-line:") >= 4
    assert css.count("--grid-dot:") >= 4  # the dotted chart reading grid re-themes too


def test_base_css_defines_the_light_palette(client: TestClient) -> None:
    css = client.get("/static/base.css").text
    assert "html[data-theme=light]" in css  # legacy fallback block (superseded by daylight)
    # no hard-coded page colors left outside the variable blocks: spot-check the
    # surfaces that used to be fixed-dark
    assert "background:var(--header-bg)" in css
    assert "color:var(--btn-ink)" in css


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH (local-gate tool)")
def test_theme_switcher_migration_and_toggle_execute_under_node() -> None:
    """ADR-0195: EXECUTE theme.js (not just substring-pin it) — the legacy-save migration,
    the four-view select, and the daylight<->last-dark toggle round-trip."""
    harness = Path(__file__).parent / "js" / "theme_switch_harness.mjs"
    proc = subprocess.run(
        [str(shutil.which("node")), str(harness)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"harness failed:\n{proc.stdout}\n{proc.stderr}"


def test_svg_charts_route_theme_variables_via_style(client: TestClient) -> None:
    for asset in ("cei.js", "trend.js"):
        js = client.get(f"/static/{asset}").text
        assert 'indexOf("var(")' in js  # the svgEl helper themes fill/stroke live
        assert "var(--ink)" in js


# ---- session-wide target UID ----


def test_set_target_redirects_back_and_prefills_everywhere(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    r = client.post("/target", data={"uid": "143", "next_url": "/trend"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/trend"
    # the report page shows the target panel and pre-fills the trace box
    page = client.get("/analysis/Project2").text
    assert "Target activity" in page and 'value="143"' in page
    # the trend page focuses automatically (no ?target= needed)
    page = client.get("/trend").text
    assert "Focus activity UID 143" in page
    # compare shows the target's movement between the two versions
    page = client.get("/compare").text
    assert "Focus activity UID 143" in page and "Computed finish moved" in page


def test_measure_to_uid_box_focuses_any_activity(client: TestClient) -> None:
    """Operator item 3: the header 'Measure to' control keeps the milestone dropdown and adds a
    UID box that measures to ANY activity by UniqueID (a non-milestone, or a UID only in an older
    version). The dropdown unions milestones across versions; the box covers everything else."""
    _upload(client, "Project5")
    home = client.get("/").text
    # the UID box + Set button render on every page (via the header)
    assert "sf-uid-form" in home and 'placeholder="any UID' in home and ">Set<" in home
    # any UID absent from the milestone dropdown is still accepted, shown as a custom target
    client.post("/target", data={"uid": "999999", "next_url": "/"})
    assert 'value="999999" selected>UID 999999 (custom)' in client.get("/").text
    # the milestone dropdown remains available (Project finish = the whole schedule)
    assert "Project finish (whole schedule)" in home


def test_target_form_returns_to_current_page_and_reaches_card_and_wbs(client: TestClient) -> None:
    """The header Target-UID form shipped next_url hardcoded to '/', so setting a target always
    bounced to the dashboard — looking like nothing changed. target.js now keeps you on the
    current page, and the target is reflected on the card + WBS pages (they ignored it before)."""
    _upload(client, "Project5")
    tjs = client.get("/static/target.js")
    assert tjs.status_code == 200
    assert "next_url" in tjs.text and "location.pathname" in tjs.text  # rewrites to current page
    assert 'src="/static/target.js?v=' in client.get("/").text  # every page (cache-busted)
    assert "name=next_url" in client.get("/analysis/Project5").text  # the field target.js drives
    # with a target set, the card and WBS pages now show its focus panel
    client.post("/target", data={"uid": "143", "next_url": "/"})
    assert "Target activity" in client.get("/card/Project5").text
    assert "Target activity" in client.get("/wbs/Project5").text


def test_explicit_blank_target_overrides_the_session_target(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    client.post("/target", data={"uid": "143", "next_url": "/"})
    # the Focus form submitted blank (the old 422 crash) clears focus for that view only
    r = client.get("/trend?target=")
    assert r.status_code == 200
    assert "Focus activity UID" not in r.text


def test_blank_or_invalid_uid_clears_the_target(client: TestClient) -> None:
    _upload(client, "Project2")
    client.post("/target", data={"uid": "143", "next_url": "/"})
    client.post("/target", data={"uid": "  ", "next_url": "/"})
    assert "Target activity" not in client.get("/analysis/Project2").text
    client.post("/target", data={"uid": "143", "next_url": "/"})
    client.post("/target", data={"uid": "abc", "next_url": "/"})
    assert "Target activity" not in client.get("/analysis/Project2").text


def test_target_absent_from_a_version_degrades_gently(client: TestClient) -> None:
    _upload(client, "Project2")
    client.post("/target", data={"uid": "999999", "next_url": "/"})
    page = client.get("/analysis/Project2").text
    assert "does not contain UniqueID 999999" in page


def test_target_endpoint_truncates_the_analyzed_population() -> None:
    """Setting a Target UID makes it the analysis ENDPOINT: every metric/visual is restricted to
    that activity + its drivers (work beyond it is omitted), and a banner says so on every page."""
    st = SessionState()
    c = TestClient(create_app(st))
    data = (GOLDEN / "project2_5" / "Project2.mspdi.xml").read_bytes()
    c.post("/upload", files={"files": ("Project2.mspdi.xml", data, "text/xml")})
    raw = next(iter(st.schedules.values()))
    full = sum(1 for t in raw.tasks if not t.is_summary)

    c.post("/target", data={"uid": "143", "next_url": "/"})
    scoped = st.scope(raw)
    kept = sum(1 for t in scoped.tasks if not t.is_summary)
    assert 1 <= kept < full  # truncated to UID 143 + its drivers
    assert any(t.unique_id == 143 for t in scoped.tasks)  # the target itself is retained
    page = c.get("/analysis/Project2").text
    assert "Analysis endpoint: UID 143" in page and "omitted" in page  # banner on the page

    # clearing the target restores the full population and drops the banner everywhere
    c.post("/target", data={"uid": "", "next_url": "/"})
    assert sum(1 for t in st.scope(raw).tasks if not t.is_summary) == full
    assert "Analysis endpoint:" not in c.get("/analysis/Project2").text


def test_endpoint_banner_warns_when_target_missing(client: TestClient) -> None:
    _upload(client, "Project2")
    client.post("/target", data={"uid": "999999", "next_url": "/"})
    page = client.get("/analysis/Project2").text
    assert "Endpoint UID 999999 not found" in page  # nothing truncated; the UID is flagged


def test_target_redirect_never_leaves_the_app(client: TestClient) -> None:
    for evil in ("//evil.example", "http://evil.example/x", "javascript:alert(1)"):
        r = client.post("/target", data={"uid": "1", "next_url": evil}, follow_redirects=False)
        assert r.headers["location"] == "/"


def test_wipe_clears_the_target(client: TestClient) -> None:
    _upload(client, "Project2")
    client.post("/target", data={"uid": "143", "next_url": "/"})
    client.post("/session/wipe")
    _upload(client, "Project2")
    assert "Target activity" not in client.get("/analysis/Project2").text


# ---- the 20-file batch cap ----


def test_upload_accepts_up_to_twenty_and_names_the_overflow(client: TestClient) -> None:
    data = EXAMPLE.read_bytes()
    files = [("files", (f"v{i}.json", data, "application/json")) for i in range(MAX_FILES + 1)]
    page = client.post("/upload", files=files).text
    assert f"1 file(s) beyond the {MAX_FILES}-file batch cap" in page
    assert f"Loaded {MAX_FILES}:" in page
