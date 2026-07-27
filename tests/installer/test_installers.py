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
import hashlib
import io
import re
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TIERS = ("tier1", "tier2", "tier3")
FAMILIES = ("ps1", "sh", "command")
_END_CONFIG = "END TIER CONFIG"
MPXJ_DIR = ROOT / "tools" / "mpxj"


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


def test_installers_deploy_mpxj_and_a_single_self_stopping_icon() -> None:
    """Operator 2026-07-10 (ADR-0193): (1) every deployed .mpp import failed — the wheel is
    pure Python and the 17 MB Java converter never shipped; each installer now copies the
    repo's tools/mpxj beside the venv, where the runtime walk-up discovery finds it, with an
    honest warning when the installer is run outside the checkout. (2) One desktop icon:
    'Schedule Forensics' launches pythonw directly (the app stops itself AND the local AI on
    browser close / Quit — ADR-0122); the old Start/Stop desktop icons are removed on
    upgrade and by the uninstaller."""
    tpl_ps1 = (ROOT / "tools" / "installer" / "template.ps1").read_text(encoding="utf-8")
    assert 'Join-Path (Split-Path -Parent $PSScriptRoot) "tools\\mpxj"' in tpl_ps1
    # "stays OFF" is retired (ADR-0299): the installer now reports the DEPLOYED capability,
    # so the three outcomes are enabled / stays ON (existing kept) / is OFF.
    assert "MpxjToMspdi.class" in tpl_ps1 and "native .mpp import is OFF" in tpl_ps1
    assert "native .mpp import stays OFF" not in tpl_ps1
    assert '"Schedule Forensics.lnk"' in tpl_ps1  # the ONE icon
    assert "pythonw.exe" in tpl_ps1  # launched directly (self-stopping app, no console)
    assert '"Start Schedule Forensics.lnk", "Stop Schedule Forensics.lnk"' in tpl_ps1  # cleanup
    # ADR-0300: -L dereferences (real files beside the venv, never a link into a source tree)
    # and `pwd -P` makes the self-copy skip compare PHYSICAL paths. What those two actually
    # guarantee is EXECUTED in the symlink tests below; these only catch a silent revert.
    for family in ("sh", "command"):
        tpl = (ROOT / "tools" / "installer" / f"template.{family}").read_text(encoding="utf-8")
        assert 'cp -RL "$MPXJ_SRC"' in tpl and "MpxjToMspdi.class" in tpl, family
        assert "pwd -P) || printf" in tpl, f"{family}: self-copy guard compares logical paths"
    for tier in TIERS:  # the generated installers carry all of it
        ps1 = _read(tier, "ps1")
        assert "MpxjToMspdi.class" in ps1 and '"Schedule Forensics.lnk"' in ps1
        for family in ("sh", "command"):
            text = _read(tier, family)
            assert 'cp -RL "$MPXJ_SRC"' in text, (tier, family)
            assert "pwd -P) || printf" in text, (tier, family)


# ── ADR-0299: the one-file installer must deliver .mpp support with NO repo checkout ──────


def _manifest(text: str) -> dict[str, str]:
    """The embedded ``<sha256>  <relpath>`` MPXJ manifest, as {relpath: sha}."""
    m = re.search(r"<<'SF_MPXJ_MANIFEST_EOF'\n(.*?)\nSF_MPXJ_MANIFEST_EOF", text, re.S)
    if m is None:  # the ps1 family carries it in a single-quoted here-string
        m = re.search(r"\$MpxjManifest = @'\n(.*?)\n'@", text, re.S)
    assert m, "MPXJ manifest block not found"
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if line.strip():
            sha, rel = line.split(None, 1)
            out[rel.strip()] = sha.lower()
    return out


@pytest.mark.parametrize("family", FAMILIES)
def test_mpxj_manifest_covers_every_vendored_file_with_a_matching_hash(family: str) -> None:
    """The manifest is the download's integrity contract: it must name EVERY file under
    tools/mpxj and each SHA-256 must match the bytes on disk. Touch a jar without
    regenerating and this fails — the MPXJ twin of the wheel-lockstep guard below."""
    manifest = _manifest(_read("tier1", family))
    on_disk = {
        p.relative_to(MPXJ_DIR).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in MPXJ_DIR.rglob("*")
        if p.is_file()
    }
    assert manifest == on_disk, "embedded MPXJ manifest is STALE vs tools/mpxj — regenerate"
    assert "classes/MpxjToMspdi.class" in manifest
    assert sum(1 for k in manifest if k.endswith(".jar")) >= 20, "dependency jars missing"


@pytest.mark.parametrize("family", FAMILIES)
def test_mpxj_download_url_points_at_this_repo(family: str) -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    owner_repo = re.search(r'^Repository\s*=\s*"https://github\.com/([^"]+)"', pyproject, re.M)
    assert owner_repo
    text = _read("tier1", family)
    assert f"https://raw.githubusercontent.com/{owner_repo.group(1)}/" in text
    assert "/tools/mpxj" in text


@pytest.mark.parametrize("tier", TIERS)
@pytest.mark.parametrize("family", FAMILIES)
def test_mpxj_support_is_not_gated_on_a_repo_checkout(tier: str, family: str) -> None:
    """THE REGRESSION (ADR-0299). The operator has no clone: they download ONE installer into
    ~/Downloads and run it. The old lookup was `<installer dir>/../tools/mpxj`, which resolved
    to ~/tools/mpxj, so native .mpp import was silently left OFF and the run still printed
    DONE. Every installer must now carry a download fallback and verify what it fetches."""
    text = _read(tier, family)
    assert "SF_MPXJ_OFFLINE" in text, "no air-gap opt-out"
    assert "raw.githubusercontent.com" in text, "no download fallback — checkout-only again"
    lowered = text.lower()
    assert "sha-256 verified" in lowered or "sha256" in lowered, "download is unverified"
    assert "run the installer from the repository checkout" not in text, "checkout-only advice"


def _mpxj_block(family: str) -> str:
    text = _read("tier1", family)
    start = text.index("# --- 3b. vendored MPXJ")
    return text[start : text.index("\n# --- 4.", start)]


def _run_mpxj_block(tmp_path: Path, *, script_dir: Path, env: dict[str, str]) -> str:
    """Execute the REAL shipped 3b block standalone (stubbed ok/warn), no venv, no network.

    Runs with cwd set to an EMPTY directory on purpose: ``$PWD/tools/mpxj`` is one of the four
    candidates, so running from the repo root would silently satisfy every scenario from the
    developer's own checkout and the test would prove nothing.
    """
    harness = script_dir / "mpxj_block.sh"
    harness.write_text(
        "set -euo pipefail\n"
        'ok(){ echo "[ok] $*"; }\n'
        'warn(){ echo "[!!] $*"; }\n'
        f'INSTALL_ROOT="{tmp_path / "root"}"\n' + _mpxj_block("sh") + "\n",
        encoding="utf-8",
    )
    neutral = tmp_path / "neutral"
    neutral.mkdir(exist_ok=True)
    proc = subprocess.run(
        ["bash", str(harness)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=neutral,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(tmp_path), **env},
    )
    return proc.stdout + proc.stderr


def _installed(tmp_path: Path) -> Path:
    """Pre-deploy a converter where an EARLIER install would have left it."""
    cls = tmp_path / "root" / "tools" / "mpxj" / "classes" / "MpxjToMspdi.class"
    cls.parent.mkdir(parents=True, exist_ok=True)
    cls.write_bytes(b"stub")
    return cls


def test_mpxj_block_deploys_a_local_copy_without_touching_the_network(tmp_path: Path) -> None:
    """The checkout/offline-media path still wins — and short-circuits the download."""
    script_dir = tmp_path / "media"
    (script_dir / "tools" / "mpxj" / "classes").mkdir(parents=True)
    (script_dir / "tools" / "mpxj" / "classes" / "MpxjToMspdi.class").write_bytes(b"stub")
    out = _run_mpxj_block(tmp_path, script_dir=script_dir, env={"SF_MPXJ_OFFLINE": "1"})
    assert "[ok]" in out and "native .mpp import enabled" in out, out
    assert (tmp_path / "root" / "tools" / "mpxj" / "classes" / "MpxjToMspdi.class").exists()


def test_an_upgrade_reports_the_converter_it_already_has(tmp_path: Path) -> None:
    """THE OPERATOR'S INCIDENT (MPXJ-CAPABILITY-REPORT.md scenario C). Re-running the downloaded
    installer over an existing install found no source and printed "native .mpp import stays OFF"
    on a machine where the converter was demonstrably present and .mpp import WORKED. The
    installer described its own copy step instead of the capability of the tool it had just
    installed — on a testimony tool, a false claim about your own capability is a correctness
    defect. What is printed must agree with what ``_mpxj_home()`` will find."""
    script_dir = tmp_path / "downloads"
    script_dir.mkdir()
    cls = _installed(tmp_path)
    out = _run_mpxj_block(tmp_path, script_dir=script_dir, env={"SF_MPXJ_OFFLINE": "1"})
    assert "stays ON" in out, out
    assert "is OFF" not in out, "claimed OFF while a working converter was installed"
    assert cls.exists(), "an upgrade destroyed the existing converter"


def test_a_re_run_never_destroys_the_installed_converter(tmp_path: Path) -> None:
    """The destructive edge that widening the search opens (mutation-verified in the report and
    again here): with ``SF_MPXJ_HOME`` pointing AT the installed copy, the copy step would clear
    the destination and then copy from the thing it just deleted. The self-copy skip is the only
    thing standing between a re-run and the operator's only converter."""
    script_dir = tmp_path / "downloads"
    script_dir.mkdir()
    cls = _installed(tmp_path)
    out = _run_mpxj_block(
        tmp_path,
        script_dir=script_dir,
        env={"SF_MPXJ_OFFLINE": "1", "SF_MPXJ_HOME": str(cls.parent.parent)},
    )
    assert cls.exists(), "SF_MPXJ_HOME == destination deleted the only converter"
    assert "stays ON" in out, out


def test_a_symlinked_source_cannot_destroy_the_installed_converter(tmp_path: Path) -> None:
    """ADR-0300 — Codex P1 on #447, reproduced against the SHIPPED block before it was fixed.

    The test above passes ``SF_MPXJ_HOME`` as the destination's own spelling, which a LOGICAL
    ``pwd`` compares equal. Point it at a **symlink** to the same directory and the two spellings
    differ, the self-copy skip never fires, and the block selects the link as its source — then
    ``rm -rf``s the real converter and copies the now-dangling link back in its place, printing
    ``native .mpp import enabled``. Both rules the block states for itself broken at once, in the
    direction that costs the operator data *and* lies about it. ``pwd -P`` compares physical
    paths, so the skip fires and the upgrade is correctly reported as a no-op.
    """
    script_dir = tmp_path / "downloads"
    script_dir.mkdir()
    cls = _installed(tmp_path)
    link = tmp_path / "linked-mpxj"
    link.symlink_to(cls.parent.parent, target_is_directory=True)
    out = _run_mpxj_block(
        tmp_path,
        script_dir=script_dir,
        env={"SF_MPXJ_OFFLINE": "1", "SF_MPXJ_HOME": str(link)},
    )
    assert cls.exists(), "a symlinked SF_MPXJ_HOME destroyed the only converter"
    assert not (tmp_path / "root" / "tools" / "mpxj").is_symlink(), (
        "the converter directory was replaced by a symlink"
    )
    assert "stays ON" in out, out
    assert "enabled" not in out, "claimed a fresh deploy while nothing was actually copied"


def test_a_symlinked_source_deploys_real_files_not_a_link(tmp_path: Path) -> None:
    """``cp -RL``. When the source genuinely is elsewhere but reached through a link, what lands
    beside the venv must be REAL files: a link into a tree that later moves, unmounts or is
    cleaned up would leave the deployed tool with a converter that silently vanishes."""
    script_dir = tmp_path / "downloads"
    script_dir.mkdir()
    real = tmp_path / "elsewhere" / "mpxj" / "classes"
    real.mkdir(parents=True)
    (real / "MpxjToMspdi.class").write_bytes(b"stub")
    link = tmp_path / "linked-source"
    link.symlink_to(real.parent, target_is_directory=True)
    out = _run_mpxj_block(
        tmp_path,
        script_dir=script_dir,
        env={"SF_MPXJ_OFFLINE": "1", "SF_MPXJ_HOME": str(link)},
    )
    assert "native .mpp import enabled" in out, out
    deployed = tmp_path / "root" / "tools" / "mpxj"
    assert not deployed.is_symlink(), "deployed a symlink instead of the converter itself"
    cls = deployed / "classes" / "MpxjToMspdi.class"
    assert cls.is_file() and not cls.is_symlink(), "converter class is not a real file"


def test_a_failed_download_leaves_an_existing_install_untouched(tmp_path: Path) -> None:
    """A download that cannot reach the host must never cost the operator a working converter:
    the fetch stages into a temp dir and is swapped in only once every byte verifies."""
    script_dir = tmp_path / "downloads"
    script_dir.mkdir()
    cls = _installed(tmp_path)
    out = _run_mpxj_block(  # unroutable proxy => every fetch fails
        tmp_path,
        script_dir=script_dir,
        env={"http_proxy": "http://127.0.0.1:1", "https_proxy": "http://127.0.0.1:1"},
    )
    assert cls.exists(), "a failed download destroyed the installed converter"
    assert "stays ON" in out or "enabled" in out, out
    assert not (tmp_path / "root" / "tools" / ".mpxj-incoming").exists(), "staging dir left behind"


def test_mpxj_block_fails_honestly_when_it_cannot_get_the_converter(tmp_path: Path) -> None:
    """No local copy, nothing installed, no download allowed => an explicit OFF statement and NO
    false [ok], no half-written converter tree, and a remedy the operator can actually follow
    (they have no clone, so "run it from the checkout" was never actionable)."""
    script_dir = tmp_path / "downloads"
    script_dir.mkdir()
    out = _run_mpxj_block(tmp_path, script_dir=script_dir, env={"SF_MPXJ_OFFLINE": "1"})
    assert "native .mpp import is OFF" in out, out
    assert "native .mpp import enabled" not in out, out
    assert "Download ZIP" in out, "the remedy must be one the operator can actually follow"
    assert not (tmp_path / "root" / "tools" / "mpxj").exists()


def test_a_failed_model_download_neither_aborts_the_install_nor_claims_success(
    tmp_path: Path,
) -> None:
    """ADR-0299. The AI step is documented as optional ("the tool runs fully without it"), but
    under ``set -euo pipefail`` a failing ``ollama pull`` aborted the whole installer right
    here — before the launchers, uninstaller and README were written, so the operator was left
    with a venv and no way to start the tool. It must warn and carry on."""
    text = _read("tier1", "sh")
    start = text.index("# --- 4. Ollama")
    block = text[start : text.index("\n# --- 5.", start)].replace(
        "read -r -p \"    Install Ollama + pull '$OLLAMA_MODEL' "
        '(~${MODEL_DISK_GB} GB download)? [Y/n] " ans || ans="n"',
        "true",
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "ollama"  # present, but every pull fails (disk full / daemon down)
    stub.write_text('#!/bin/sh\n[ "$1" = pull ] && { echo boom >&2; exit 1; }\nexit 0\n')
    stub.chmod(0o755)
    harness = tmp_path / "ai.sh"
    harness.write_text(
        "set -euo pipefail\n"
        'step(){ echo "==> $*"; }\nok(){ echo "[ok] $*"; }\nwarn(){ echo "[!!] $*"; }\n'
        'SMOKE=0\nOLLAMA_MODEL="m"\nMODEL_DISK_GB=5\nans="y"\n'
        + block
        + "\necho REACHED_LAUNCHERS\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["bash", str(harness)],
        capture_output=True,
        text=True,
        timeout=120,
        env={"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(tmp_path)},
    )
    out = proc.stdout + proc.stderr
    assert "REACHED_LAUNCHERS" in out, f"a failed model pull aborted the install:\n{out}"
    assert proc.returncode == 0, out
    assert "Model download failed" in out, out
    assert "[ok] Model ready" not in out, "claimed a model it never got"


@pytest.mark.parametrize("family", FAMILIES)
def test_the_converter_url_is_pinned_to_an_immutable_commit(family: str) -> None:
    """PR #446 review (P1). The manifest is generated from the LOCAL ``tools/mpxj`` bytes, so a
    mutable ``main`` in the URL guarantees an eventual disagreement between what an installer
    fetches and what its baked-in hashes expect:

    * every installer already in the wild starts failing the moment those bytes change on main;
    * a PR that legitimately upgrades MPXJ regenerates the manifest with the NEW hashes while
      main still serves the OLD jars — so CI's no-checkout leg downloads old bytes, fails the
      hash check, and blocks its own upgrade.

    Pinning to the commit that actually contains these bytes makes the two unable to disagree.
    """
    text = _read("tier1", family)
    m = re.search(r"raw\.githubusercontent\.com/[^/\s\"]+/[^/\s\"]+/([^/\s\"]+)/tools/mpxj", text)
    assert m, "no MPXJ raw URL found"
    ref = m.group(1)
    assert re.fullmatch(r"[0-9a-f]{40}", ref), f"MPXJ URL pinned to mutable ref {ref!r}"


@pytest.mark.parametrize("tier", TIERS)
def test_no_probe_or_optional_step_can_abort_the_windows_install(tier: str) -> None:
    """ADR-0299, found by the new windows no-checkout CI leg.

    While ``$ErrorActionPreference = "Stop"``, a native program writing ANYTHING to stderr raises
    a TERMINATING error even when it succeeded. ``java -version`` prints its banner on stderr, so
    the Java *detection* step killed the whole install before the shortcut, uninstaller and
    README were created — on any machine with java on PATH. It stayed invisible because the CI
    steps that ran the installer ended with another command, which reset ``$LASTEXITCODE``.
    ``winget`` and ``ollama pull`` stream progress to stderr and had the same exposure, which
    would have aborted an install at a step documented as optional.

    Every such call must go through ``Invoke-SfNative`` (softens the preference, always restores
    it, lets the caller judge the exit code).
    """
    ps1 = _read(tier, "ps1")
    assert "function Invoke-SfNative" in ps1, "the stderr-safety helper is gone"
    assert "finally { $ErrorActionPreference = $prevEap }" in ps1, "preference not restored"
    for risky in ("java -version", "winget install", "ollama pull"):
        for line in ps1.splitlines():
            if line.strip().startswith("#"):
                continue
            # only real INVOCATIONS count — the same words appear inside operator-facing advice
            # strings ("...run: ollama pull <model>"), which cannot abort anything.
            code = re.sub(r'"[^"]*"', "", line)
            if risky in code:
                assert "Invoke-SfNative" in line, f"{risky!r} can abort the install: {line.strip()}"
