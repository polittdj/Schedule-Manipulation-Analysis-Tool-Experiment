"""Structural verification of the nine one-file installers (INSTALLER-SPEC; 3 tiers x 3 OSes).

pwsh is not available in the build container, so true Windows execution happens in the
windows-latest smoke workflow (.github/workflows/installer-smoke.yml); the Linux/macOS bash
family is additionally executed end-to-end in CI and was executed in-container during the build.
These tests verify everything verifiable statically: every tier/OS file exists, each OS family
shares an IDENTICAL body (no tier drift), tier configs match the spec, and the embedded wheel
decodes byte-for-byte to a valid zip that matches the pyproject version AND carries the web
static assets (the packaging gap the first end-to-end run caught).
"""

from __future__ import annotations

import base64
import io
import re
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TIERS = ("tier1", "tier2", "tier3")
FAMILIES = ("ps1", "sh", "command")
_END_CONFIG = "END TIER CONFIG"


def _read(tier: str, family: str) -> str:
    p = ROOT / "installer" / f"install-{tier}.{family}"
    assert p.exists(), p
    return p.read_text(encoding="utf-8-sig" if family == "ps1" else "utf-8")


def _payload_b64(text: str, family: str) -> str:
    if family == "ps1":
        m = re.search(r"\$EMBEDDED_WHEEL_B64 = @'\n(.*?)\n'@", text, re.S)
        assert m, "ps1 payload block not found"
        return re.sub(r"\s", "", m.group(1))
    m = re.search(r"# ===BEGIN WHEEL_B64===\n(.*?)# ===END WHEEL_B64===", text, re.S)
    assert m, f"{family} payload block not found"
    return re.sub(r"\s|#", "", m.group(1))


@pytest.mark.parametrize("family", FAMILIES)
def test_three_tiers_exist_with_the_specced_configs(family: str) -> None:
    expectations = {
        "tier1": ("16", "false", "llama3.2:3b"),
        "tier2": ("64", "true", "llama3.1:8b"),
        "tier3": ("128", "true", "llama3.3:70b"),
    }
    for tier, (ram, gpu, model) in expectations.items():
        text = _read(tier, family)
        config = text.split(_END_CONFIG, 1)[0]
        assert model in config, f"{tier}.{family}: model"
        assert re.search(rf"=\s*\$?{ram}\b", config), f"{tier}.{family}: RAM"
        assert re.search(rf"=\s*\$?{gpu}\b", config, re.I), f"{tier}.{family}: GPU flag"


@pytest.mark.parametrize("family", FAMILIES)
def test_shared_body_is_identical_across_tiers_no_drift(family: str) -> None:
    """Within one OS family the tiers may differ ONLY in the config block (and the header
    label) — a fix applied to one installer body but not its siblings fails here."""
    bodies = {t: _read(t, family).split(_END_CONFIG, 1)[1] for t in TIERS}
    assert bodies["tier1"] == bodies["tier2"] == bodies["tier3"]


@pytest.mark.parametrize("family", FAMILIES)
def test_embedded_wheel_decodes_byte_exact_with_static_assets(family: str) -> None:
    """The payload must decode to a CRC-valid zip of the CURRENT version that includes the
    vendored web static assets — the first Linux end-to-end run caught a wheel that installed
    but crashed at startup because web/static was never packaged."""
    text = _read("tier1", family)
    raw = base64.b64decode(_payload_b64(text, family))
    zf = zipfile.ZipFile(io.BytesIO(raw))
    assert zf.testzip() is None
    names = zf.namelist()
    assert any(n.startswith("schedule_forensics/") for n in names)
    assert sum(1 for n in names if "/web/static/" in n) >= 30, "static assets missing from wheel"
    assert any("/web/examples/" in n for n in names), "bundled example missing from wheel"

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    vm = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    assert vm and f"schedule_forensics-{vm.group(1)}" in text, "embedded wheel version drifted"


def test_all_families_embed_the_same_wheel() -> None:
    payloads = {f: _payload_b64(_read("tier1", f), f) for f in FAMILIES}
    assert payloads["ps1"] == payloads["sh"] == payloads["command"]


def test_installer_promises_match_the_tool_reality() -> None:
    """Start/Stop wiring must target things that actually exist: the launcher accepts a pinned
    port, and the app exposes POST /api/shutdown — in every OS family."""
    launcher = (ROOT / "src/schedule_forensics/launcher.py").read_text(encoding="utf-8")
    assert "port: int | None = None" in launcher
    app = (ROOT / "src/schedule_forensics/web/app.py").read_text(encoding="utf-8")
    assert '@app.post("/api/shutdown")' in app
    for family in FAMILIES:
        text = _read("tier1", family)
        assert "main(port=" in text, family
        assert "/api/shutdown" in text, family
        assert "SF_INSTALLER_SMOKE" in text, family  # the CI smoke hook exists everywhere


def test_wheel_packaging_includes_runtime_data() -> None:
    """Regression for the packaging gap itself: pyproject must declare the web data dirs."""
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.setuptools.package-data]" in pyproject
    assert "web/static/*" in pyproject and "web/examples/*" in pyproject


def test_no_cui_or_secret_shaped_content_in_installers() -> None:
    for family in FAMILIES:
        text = _read("tier1", family)
        head = text.split("WHEEL_B64", 1)[0]
        for banned in ("00_REFERENCE_INTAKE", "api_key", "token=", "Authorization:"):
            assert banned not in head, family
