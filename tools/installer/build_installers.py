"""Generate the three one-file Windows installers from template.ps1 + the current wheel.

Usage (from the repo root, venv active):

    python -m build --wheel --outdir dist/wheel     # or reuse an existing wheel
    python tools/installer/build_installers.py dist/wheel/schedule_forensics-*.whl

Emits ``installer/install-tier{1,2,3}.{ps1,sh,command}`` (Windows/Linux/macOS) — per-family
identical shared bodies (test-enforced by
``tests/installer/test_installers.py``), differing only in the TIER CONFIG block. Stdlib-only.
See ``docs/PLAN/INSTALLER-SPEC.md`` for the tier definitions and the defaulted §3 answers.
"""

from __future__ import annotations

import base64
import glob
import hashlib
import re
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: Where an installer that was downloaded ON ITS OWN (no repo checkout beside it) fetches the
#: vendored MPXJ converter from. The jars are ~17 MB — embedding them would push every installer
#: past 20 MB and re-commit 200 MB on each version bump, so they are pulled at install time from
#: the public repo and verified against the SHA-256 manifest baked in below (ADR-0299).
MPXJ_DIR = ROOT / "tools" / "mpxj"

#: (file suffix, label, min RAM GB, needs GPU, ollama model, model download GB)
TIERS: tuple[tuple[str, str, int, bool, str, int], ...] = (
    ("tier1", "Tier 1 - 16 GB RAM, no discrete GPU", 16, False, "llama3.2:3b", 2),
    ("tier2", "Tier 2 - 64 GB RAM + discrete GPU", 64, True, "llama3.1:8b", 5),
    ("tier3", "Tier 3 - 128 GB RAM + discrete GPU", 128, True, "llama3.3:70b", 43),
)

_CONFIG = """\
# Defaults chosen 2026-07-02 per INSTALLER-SPEC.md SS3 (operator authorized autonomous build;
# edit these four lines freely - they are the ONLY tier-specific values in this file).
$TierLabel   = "{label}"
$MinRamGB    = {ram}
$NeedsGpu    = ${gpu}
$OllamaModel = "{model}"
$ModelDiskGB = {disk}"""


_SH_CONFIG = """\
# Defaults chosen 2026-07-02 per INSTALLER-SPEC.md SS3 (operator authorized autonomous build;
# edit these five lines freely - they are the ONLY tier-specific values in this file).
TIER_LABEL="{label}"
MIN_RAM_GB={ram}
NEEDS_GPU={gpu}
OLLAMA_MODEL="{model}"
MODEL_DISK_GB={disk}"""


def mpxj_ref() -> str:
    """The IMMUTABLE commit to fetch the converter from: the last commit that touched
    ``tools/mpxj``.

    Never a branch name. A mutable ``main`` would mean (a) every installer already in the wild
    starts failing its baked-in hashes the moment those bytes change, and (b) a PR that
    legitimately upgrades MPXJ regenerates the manifest with the NEW hashes while ``main`` still
    serves the OLD jars, so CI's no-checkout leg downloads old bytes and blocks its own upgrade
    (PR #446 review, P1). Pinning to the commit that actually contains these bytes fixes both:
    the URL and the manifest can never disagree.

    Upgrading MPXJ is therefore a deliberate two-step: **commit and push ``tools/mpxj`` first**,
    then regenerate the installers so they pin to that pushed commit. The build prints the ref it
    chose; if it is not on the remote yet, the download will 404 and the installers must be
    regenerated after the push.
    """
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", str(MPXJ_DIR)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(
            f"cannot resolve the MPXJ commit via git ({exc}) — refusing to pin a mutable ref"
        ) from exc
    if not re.fullmatch(r"[0-9a-f]{40}", out):
        raise SystemExit(f"git returned {out!r}, not a commit SHA — refusing to pin a mutable ref")
    return out


def mpxj_base_url() -> str:
    """The raw.githubusercontent base for ``tools/mpxj``, derived from pyproject's Repository URL
    so the installers cannot drift from the repo they ship out of, and pinned to an immutable
    commit (see :func:`mpxj_ref`)."""
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^Repository\s*=\s*"https://github\.com/([^/"]+)/([^/"]+)"', pyproject, re.M)
    if not m:
        raise SystemExit("pyproject [project.urls] Repository not found — cannot pin the MPXJ URL")
    owner, repo = m.group(1), m.group(2)
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{mpxj_ref()}/tools/mpxj"


def mpxj_manifest() -> str:
    """``<sha256>  <relative/path>`` for every vendored MPXJ file, sorted for reproducibility.

    Both the checksum AND the file list are pinned: an installer downloads exactly this set and
    refuses anything whose bytes differ, so a moved/replaced jar fails loudly instead of silently
    installing a converter that is not the one this build was tested against.
    """
    if not (MPXJ_DIR / "classes" / "MpxjToMspdi.class").exists():
        raise SystemExit(f"{MPXJ_DIR} has no compiled converter — run tools/mpxj/setup.sh first")
    lines: list[str] = []
    for path in sorted(p for p in MPXJ_DIR.rglob("*") if p.is_file()):
        rel = path.relative_to(MPXJ_DIR).as_posix()
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {rel}")
    return "\n".join(lines)


def build(wheel: Path) -> list[Path]:
    b64 = base64.b64encode(wheel.read_bytes()).decode("ascii")
    wrapped = "\n".join(textwrap.wrap(b64, 120))
    commented = "\n".join("# " + line for line in wrapped.splitlines())
    out_dir = ROOT / "installer"
    out_dir.mkdir(exist_ok=True)
    manifest, base_url = mpxj_manifest(), mpxj_base_url()
    print(f"MPXJ pinned to {base_url}")
    written: list[Path] = []
    families = (
        ("template.ps1", "install-{s}.ps1", _CONFIG, "utf-8-sig", "\r\n", "{{WHEEL_B64}}", wrapped),
        (
            "template.sh",
            "install-{s}.sh",
            _SH_CONFIG,
            "utf-8",
            "\n",
            "{{WHEEL_B64_COMMENTED}}",
            commented,
        ),
        (
            "template.command",
            "install-{s}.command",
            _SH_CONFIG,
            "utf-8",
            "\n",
            "{{WHEEL_B64_COMMENTED}}",
            commented,
        ),
    )
    for tmpl_name, out_pattern, config_tmpl, enc, nl, payload_key, payload in families:
        template = (ROOT / "tools" / "installer" / tmpl_name).read_text(encoding="utf-8")
        for suffix, label, ram, gpu, model, disk in TIERS:
            config = config_tmpl.format(
                label=label, ram=ram, gpu=str(gpu).lower(), model=model, disk=disk
            )
            body = (
                template.replace("{{TIER_LABEL}}", label)
                .replace("{{TIER_SUFFIX}}", suffix)
                .replace("{{TIER_CONFIG}}", config)
                .replace("{{WHEEL_NAME}}", wheel.name)
                .replace("{{MPXJ_BASE_URL}}", base_url)
                .replace("{{MPXJ_MANIFEST}}", manifest)
                .replace(payload_key, payload)
            )
            out = out_dir / out_pattern.format(s=suffix)
            out.write_text(body, encoding=enc, newline=nl)
            if out.suffix in (".sh", ".command"):
                out.chmod(0o755)
            written.append(out)
            print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size / 1024:.0f} KB)")
    return written


if __name__ == "__main__":
    pattern = sys.argv[1] if len(sys.argv) > 1 else "dist/wheel/schedule_forensics-*.whl"
    matches = sorted(glob.glob(str(ROOT / pattern))) or sorted(glob.glob(pattern))
    if not matches:
        sys.exit(f"no wheel matches {pattern!r} — run: python -m build --wheel --outdir dist/wheel")
    build(Path(matches[-1]))
