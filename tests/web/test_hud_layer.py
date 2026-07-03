"""HUD layer (ADR-0146): compliance drawer, explainers, JARVIS theme, live telemetry, hints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

STATIC = Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/static"
GOLD = Path(__file__).resolve().parents[2] / "tests/fixtures/golden/project2_5"


def _client_loaded() -> TestClient:
    c = TestClient(create_app(SessionState()))
    data = (GOLD / "Project5.mspdi.xml").read_bytes()
    c.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")})
    return c


def test_compliance_drawer_with_itar_notice_on_every_page() -> None:
    c = _client_loaded()
    for page in ("/", "/trend", "/settings", "/help", "/sra"):
        text = c.get(page).text
        assert "complianceDrawer" in text, page
        assert "Controlled Unclassified Information (CUI)" in text, page
        assert "22 CFR 120" in text and "15 CFR 730" in text, page  # ITAR + EAR citations
        assert "32 CFR Part 2002" in text, page  # the CUI handling rule


def test_cui_banner_still_marks_top_and_bottom() -> None:
    text = _client_loaded().get("/").text
    assert text.count("cui-banner") >= 2  # top + bottom page marking


def test_every_major_page_carries_a_decision_explainer() -> None:
    c = _client_loaded()
    for page in (
        "/",
        "/mission",
        "/ribbon",
        "/path",
        "/driving-path",
        "/evolution",
        "/trend",
        "/cei",
        "/curves",
        "/scurve",
        "/phases",
        "/forecast",
        "/evm",
        "/resources",
        "/risks",
        "/sra",
        "/brief",
        "/briefing",
        "/help",
        "/groups",
        "/settings",
    ):
        text = c.get(page).text
        assert "What am I looking at" in text, page
        assert "Decisions it informs" in text, page


def test_api_system_returns_the_full_nullable_telemetry_shape() -> None:
    c = TestClient(create_app(SessionState()))
    body = c.get("/api/system").json()
    assert set(body) >= {"cpu", "memory", "disk", "gpu", "platform", "psutil"}
    assert set(body["cpu"]) == {"percent", "cores", "temp_c"}
    assert set(body["memory"]) == {"total_gb", "used_gb", "percent"}
    assert set(body["disk"]) == {"total_gb", "used_gb", "percent"}
    assert set(body["gpu"]) == {"name", "util_percent", "mem_percent", "temp_c"}
    # in this Linux container the stdlib collectors must produce real numbers
    assert body["memory"]["total_gb"] is not None
    assert body["disk"]["percent"] is not None


def test_hud_assets_are_wired_and_local() -> None:
    c = TestClient(create_app(SessionState()))
    text = c.get("/").text
    for asset in ("/static/hud.css", "/static/sysmon.js", "/static/hints.js"):
        assert asset in text
        assert c.get(asset).status_code == 200
    # air-gap: no remote references in the new assets
    for name in ("hud.css", "sysmon.js", "hints.js"):
        content = (STATIC / name).read_text(encoding="utf-8")
        assert "http://" not in content.replace("http://127.0.0.1", "")
        assert "https://" not in content
        assert "cdn" not in content.lower()


def test_jarvis_theme_exists_and_cycles() -> None:
    theme = (STATIC / "theme.js").read_text(encoding="utf-8")
    assert '"jarvis"' in theme and "MODES" in theme
    hud = (STATIC / "hud.css").read_text(encoding="utf-8")
    assert "html[data-theme=jarvis]" in hud
    # telemetry chips + hint + explainer styling all live in the shipped stylesheet
    for cls in (".sysmon-chip", "[data-sf-hint]", "details.explain", ".compliance-drawer"):
        assert cls in hud, cls


def test_header_controls_carry_guidance_hints() -> None:
    text = TestClient(create_app(SessionState())).get("/").text
    assert "data-sf-hint" in text  # the hint layer is present on the chrome
