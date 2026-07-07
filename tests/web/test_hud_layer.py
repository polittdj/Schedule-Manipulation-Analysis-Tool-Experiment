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


# ── ADR-0147: telemetry that actually works on the operator's machine ─────────────────────


def test_api_system_is_never_cached() -> None:
    """The dock polls every 2s — a heuristically-cached response would freeze the readouts."""
    r = TestClient(create_app(SessionState())).get("/api/system")
    assert r.headers.get("cache-control") == "no-store"


def test_cpu_percent_becomes_real_from_the_second_sample() -> None:
    """Delta-based CPU%: first sample is 0.0 by design, the second is a real percentage."""
    from schedule_forensics.web import system

    system._prev_cpu = None  # reset module state
    first = system._cpu_percent()
    second = system._cpu_percent()
    if system.psutil is None:
        assert first == 0.0
    assert second is not None and 0.0 <= second <= 100.0


def test_dock_defaults_on_in_every_theme() -> None:
    """ADR-0147: the readouts must be visible without hunting for a toggle; only an explicit
    'off' preference hides them (the old behavior was JARVIS-only default-on)."""
    js = (STATIC / "sysmon.js").read_text(encoding="utf-8")
    assert 'pref() !== "off"' in js
    wanted_body = js.split("function wanted")[1].split("}")[0]
    assert '"jarvis"' not in wanted_body  # no longer theme-gated


def test_nvidia_smi_parse_is_per_field_tolerant() -> None:
    """A '[N/A]' field (common on laptop GPUs) must not blank the whole GPU card."""
    from schedule_forensics.web.system import parse_nvidia_smi_line

    full = parse_nvidia_smi_line("NVIDIA GeForce RTX 3080, 37, 2048, 10240, 61")
    assert full == {
        "name": "NVIDIA GeForce RTX 3080",
        "util_percent": 37.0,
        "mem_percent": 20.0,
        "temp_c": 61.0,
    }
    partial = parse_nvidia_smi_line("Quadro T1000, [N/A], 512, 4096, [N/A]")
    assert partial["name"] == "Quadro T1000"
    assert partial["util_percent"] is None and partial["temp_c"] is None
    assert partial["mem_percent"] == 12.5
    junk = parse_nvidia_smi_line("")
    assert junk == {"name": None, "util_percent": None, "mem_percent": None, "temp_c": None}


def test_vm_stat_parser_computes_used_bytes() -> None:
    """macOS memory fallback: (active + wired + compressed) x reported page size."""
    from schedule_forensics.web.system import parse_vm_stat_used_bytes

    out = (
        "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
        "Pages free:                              100000.\n"
        "Pages active:                            200000.\n"
        "Pages inactive:                          150000.\n"
        "Pages wired down:                         50000.\n"
        "Pages occupied by compressor:             25000.\n"
    )
    assert parse_vm_stat_used_bytes(out) == (200000 + 50000 + 25000) * 16384
    assert parse_vm_stat_used_bytes("garbage") is None


def test_windows_collectors_degrade_cleanly_off_windows() -> None:
    """The ctypes/Win32 paths must return the nullable shape (never raise) on non-Windows."""
    from schedule_forensics.web import system

    assert system._win_cpu_percent() is None
    assert system._win_memory() == {"total_gb": None, "used_gb": None, "percent": None}


def test_slow_probe_cache_feeds_gpu_and_temp() -> None:
    """GPU + CPU-temp are served from the background probe cache; the snapshot never blocks on
    a subprocess. On Linux the probe thread should land a real thermal reading quickly when the
    platform exposes one at all."""
    import time

    from schedule_forensics.web import system

    snap = system.snapshot()  # starts the probe thread
    assert set(snap["gpu"]) == {"name", "util_percent", "mem_percent", "temp_c"}
    has_thermal_zone = any(
        z.startswith("thermal_zone") for z in _safe_listdir("/sys/class/thermal")
    )
    if has_thermal_zone and system._probe_cpu_temp() is not None:
        deadline = time.time() + 8
        while time.time() < deadline and system.snapshot()["cpu"]["temp_c"] is None:
            time.sleep(0.2)
        assert system.snapshot()["cpu"]["temp_c"] is not None


def _safe_listdir(path: str) -> list[str]:
    import os

    try:
        return os.listdir(path)
    except OSError:
        return []
