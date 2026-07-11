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


def test_embedded_wheel_is_in_lockstep_with_the_source_tree() -> None:
    """The embedded wheel must byte-match the packaged source files (ADR-0148).

    The stuck-overlay incident: a home.js fix merged to main, but the installers still embedded
    a wheel built hours earlier — the operator reinstalled and got the OLD JS, and the
    version-string check above passed because the version hadn't been bumped. This test compares
    every packaged ``schedule_forensics/**`` file inside the embedded wheel byte-for-byte against
    ``src/schedule_forensics/**``: ANY source change to a packaged file now fails the gate until
    the wheel + installers are regenerated::

        python -m build --wheel --outdir dist/wheel
        python tools/installer/build_installers.py dist/wheel/schedule_forensics-*.whl
    """
    raw = base64.b64decode(_payload_b64(_read("tier1", "sh"), "sh"))
    zf = zipfile.ZipFile(io.BytesIO(raw))
    src_root = ROOT / "src"
    stale: list[str] = []
    compared = 0
    for name in zf.namelist():
        if not name.startswith("schedule_forensics/") or name.endswith("/"):
            continue  # dist-info / metadata are wheel-only by design
        src_file = src_root / name
        if not src_file.exists():
            stale.append(f"{name} (in wheel, gone from src)")
            continue
        if zf.read(name) != src_file.read_bytes():
            stale.append(f"{name} (content drifted)")
        compared += 1
    # and nothing packaged in src may be missing from the wheel
    wheel_names = set(zf.namelist())
    for src_file in (src_root / "schedule_forensics").rglob("*"):
        if not src_file.is_file() or "__pycache__" in src_file.parts:
            continue
        rel = src_file.relative_to(src_root).as_posix()
        if rel not in wheel_names:
            stale.append(f"{rel} (in src, missing from wheel)")
    assert compared > 50, "wheel unexpectedly small — extraction went wrong"
    assert not stale, (
        "embedded wheel is STALE vs source — regenerate with "
        "`python -m build --wheel --outdir dist/wheel && "
        "python tools/installer/build_installers.py dist/wheel/schedule_forensics-*.whl`:\n"
        + "\n".join(stale[:20])
    )


def test_ps1_find_python_survives_a_python_only_machine() -> None:
    """Operator regression 2026-07-10: with only python.exe on PATH (no py launcher),
    Find-Python's `return @($exe)` was unrolled by PowerShell into a bare string, so the
    venv invocation `$py[0]` indexed the CHARACTER 'p' and the install died. The unary
    comma keeps the 1-element array an array, and the call site re-wraps defensively
    (ADR-0191). The windows-latest smoke re-runs tier1 with the py launcher masked."""
    tpl = (ROOT / "tools" / "installer" / "template.ps1").read_text(encoding="utf-8")
    assert ",@($exe)" in tpl and ",@($exe, $flag)" in tpl
    assert "$py = @($py)" in tpl
    for tier in TIERS:  # the generated installers ship the same fix
        ps1 = _read(tier, "ps1")
        assert ",@($exe)" in ps1 and "$py = @($py)" in ps1
    smoke = (ROOT / ".github" / "workflows" / "installer-smoke.yml").read_text(encoding="utf-8")
    assert "py.cmd" in smoke  # CI masks the launcher to walk the operator's exact path


def test_ps1_java_and_python_install_need_no_admin() -> None:
    """Operator 2026-07-10: no admin rights — the winget OpenJDK MSI died at the UAC prompt
    and its failure was mis-reported as '[ok] Java 17 installed' (ADR-0192). The .ps1 now
    (1) detects existing JDKs the way the runtime does (incl. not-on-PATH machine/user
    installs), (2) on consent downloads Microsoft's PORTABLE zip into
    %LOCALAPPDATA%\\Programs\\Microsoft (user-writable; already in the runtime java scan),
    (3) reports failures honestly, (4) installs Python user-scope, and (5) warns when a
    stale foreign 'schedule-forensics' shim shadows the venv in terminals."""
    tpl = (ROOT / "tools" / "installer" / "template.ps1").read_text(encoding="utf-8")
    assert "Microsoft.OpenJDK.17" not in tpl  # the admin-gated MSI path is gone
    assert "aka.ms/download-jdk/microsoft-jdk-17-windows-x64.zip" in tpl
    assert "Expand-Archive" in tpl and 'Join-Path $env:LOCALAPPDATA "Programs\\Microsoft"' in tpl
    assert "Find-JavaNoAdmin" in tpl  # detection mirrors the runtime (not just PATH)
    assert "Java download failed" in tpl  # honest failure reporting, never a false [ok]
    assert "--scope user" in tpl  # Python fallback installs without elevation too
    assert "ModuleNotFoundError" in tpl  # the stale-shim shadow warning
    for tier in TIERS:  # the generated installers ship the same behavior
        ps1 = _read(tier, "ps1")
        assert "Microsoft.OpenJDK.17" not in ps1
        assert "aka.ms/download-jdk/microsoft-jdk-17-windows-x64.zip" in ps1
        assert "Find-JavaNoAdmin" in ps1
