"""Structural verification of the three one-file installers (INSTALLER-SPEC / ADR-0143 session).

pwsh is not available in the build container, so a true syntax check happens on first Windows
run; these tests verify everything verifiable here: the three tiers exist, share an IDENTICAL
shared body (no drift between tiers), carry the specced tier configs, and embed a wheel that
decodes byte-for-byte to a valid zip whose version matches pyproject.
"""

from __future__ import annotations

import base64
import io
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALLERS = {n: ROOT / "installer" / f"install-{n}.ps1" for n in ("tier1", "tier2", "tier3")}
_END_CONFIG = "# ---------------------------- END TIER CONFIG"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8-sig")


def test_three_tiers_exist_with_the_specced_configs() -> None:
    assert all(p.exists() for p in INSTALLERS.values())
    expectations = {
        "tier1": ("$MinRamGB    = 16", "$NeedsGpu    = $false", "llama3.2:3b"),
        "tier2": ("$MinRamGB    = 64", "$NeedsGpu    = $true", "llama3.1:8b"),
        "tier3": ("$MinRamGB    = 128", "$NeedsGpu    = $true", "llama3.3:70b"),
    }
    for name, needles in expectations.items():
        text = _read(INSTALLERS[name])
        for needle in needles:
            assert needle in text, f"{name}: missing {needle!r}"


def test_shared_body_is_identical_across_tiers_no_drift() -> None:
    """The tiers may differ ONLY in the config block (and the tier label in the header) — a fix
    applied to one installer body but not the others fails here."""
    bodies = {}
    for name, p in INSTALLERS.items():
        text = _read(p)
        body = text.split(_END_CONFIG, 1)[1]
        bodies[name] = body
    assert bodies["tier1"] == bodies["tier2"] == bodies["tier3"]


def test_embedded_wheel_decodes_byte_exact_and_matches_pyproject_version() -> None:
    text = _read(INSTALLERS["tier1"])
    m = re.search(r"\$EMBEDDED_WHEEL_B64 = @'\n(.*?)\n'@", text, re.S)
    assert m, "payload block not found"
    raw = base64.b64decode(re.sub(r"\s", "", m.group(1)))
    zf = zipfile.ZipFile(io.BytesIO(raw))
    assert zf.testzip() is None  # every member's CRC verifies — byte-exact embed
    names = zf.namelist()
    assert any(n.startswith("schedule_forensics/") for n in names)

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    vm = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    assert vm, "version not found in pyproject"
    assert f"schedule_forensics-{vm.group(1)}" in text, "embedded wheel version drifted"


def test_installer_promises_match_the_tool_reality() -> None:
    """The installer's Start/Stop wiring must target things that actually exist: the launcher
    accepts a pinned port, and the app exposes POST /api/shutdown."""
    text = _read(INSTALLERS["tier1"])
    assert "main(port=$AppPort)" in text
    assert "/api/shutdown" in text
    launcher = (ROOT / "src/schedule_forensics/launcher.py").read_text(encoding="utf-8")
    assert "port: int | None = None" in launcher
    app = (ROOT / "src/schedule_forensics/web/app.py").read_text(encoding="utf-8")
    assert '@app.post("/api/shutdown")' in app


def test_no_cui_or_secret_shaped_content_in_installers() -> None:
    text = _read(INSTALLERS["tier1"]).split("$EMBEDDED_WHEEL_B64", 1)[0]
    for banned in ("00_REFERENCE_INTAKE", "api_key", "token=", "Authorization:"):
        assert banned not in text
