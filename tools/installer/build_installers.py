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
import os
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

    **Shallow clones lie about the last touch (DoD 117 — fired twice).** In a shallow clone git
    attributes the entire tree to the graft-boundary commit, so ``git log -1 -- tools/mpxj``
    resolves to whatever commit the clone was cut at (one session pinned ``79865bc``; the
    v1.0.201 build's first attempt pinned the boundary ``a100184d``). A boundary resolution is
    therefore REFUSED. The escape hatch is ``SF_MPXJ_REF=<sha>``: an operator-supplied true
    last-touch ref (from a full clone's git log, or the GitHub commits API filtered to
    ``path=tools/mpxj``), accepted only after verifying its ``tools/mpxj`` TREE is byte-identical
    to the working tree's — the property the manifest actually depends on.
    """
    override = os.environ.get("SF_MPXJ_REF", "").strip()
    if override:
        if not re.fullmatch(r"[0-9a-f]{40}", override):
            raise SystemExit(f"SF_MPXJ_REF={override!r} is not a full 40-hex commit SHA")

        def _tree(spec: str) -> str:
            proc = subprocess.run(
                ["git", "rev-parse", spec], cwd=ROOT, capture_output=True, text=True
            )
            if proc.returncode != 0:
                raise SystemExit(
                    f"cannot resolve {spec!r} in this clone — fetch the commit first "
                    f"(git fetch origin {override}); refusing an unverifiable override"
                )
            return proc.stdout.strip()

        if _tree(f"{override}:tools/mpxj") != _tree("HEAD:tools/mpxj"):
            raise SystemExit(
                f"SF_MPXJ_REF={override} carries a DIFFERENT tools/mpxj tree than the working "
                "tree the manifest is hashed from — installers built this way fail their own "
                "integrity check. Refusing."
            )
        return override
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
    git_dir = subprocess.run(
        ["git", "rev-parse", "--git-dir"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    shallow = Path(ROOT, git_dir, "shallow")
    if shallow.exists() and out in shallow.read_text(encoding="utf-8").split():
        raise SystemExit(
            f"mpxj_ref resolved to {out}, which is a shallow-clone GRAFT BOUNDARY of this "
            "repository — git attributes every path to that commit, so this is an artifact, "
            "not a measured touch of tools/mpxj. Deepen the clone past the true last touch, "
            "or set SF_MPXJ_REF=<true last-touch sha> (it is verified tree-identical here)."
        )
    return out


def _repo_slug() -> tuple[str, str]:
    """``(owner, repo)`` from pyproject's Repository URL — the repo these installers ship out of,
    so neither download base can drift from it."""
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^Repository\s*=\s*"https://github\.com/([^/"]+)/([^/"]+)"', pyproject, re.M)
    if not m:
        raise SystemExit("pyproject [project.urls] Repository not found — cannot pin the MPXJ URL")
    return m.group(1), m.group(2)


def mpxj_base_url(ref: str) -> str:
    """The ANONYMOUS raw.githubusercontent base for ``tools/mpxj`` at the immutable ``ref``.

    Works only while the repository is public; a private repository 404s every anonymous raw
    fetch (measured 2026-08-13, when the repo went private as the DISC-01 remediation and the
    installer-smoke legs went red on an unchanged code path). The installers therefore also
    carry :func:`mpxj_api_base` + the pinned ref and switch to an authenticated contents-API
    fetch whenever a token is present — see the templates' ``sf_fetch_mpxj``.
    """
    owner, repo = _repo_slug()
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/tools/mpxj"


def mpxj_api_base() -> str:
    """The GitHub contents-API base for ``tools/mpxj`` — the AUTHENTICATED download path.

    With ``Accept: application/vnd.github.raw+json`` and an ``Authorization`` header this
    serves the file bytes for private repositories too (proven byte-identical against the
    manifest for the 3 MB poi jar before shipping). The per-file URL is
    ``<base>/<relpath>?ref=<pinned sha>`` — same immutable ref, same SHA-256 manifest check.
    """
    owner, repo = _repo_slug()
    return f"https://api.github.com/repos/{owner}/{repo}/contents/tools/mpxj"


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
    ref = mpxj_ref()  # resolved ONCE — the raw base, the API ?ref= and the printout must agree
    manifest, base_url, api_base = mpxj_manifest(), mpxj_base_url(ref), mpxj_api_base()
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
                .replace("{{MPXJ_API_BASE}}", api_base)
                .replace("{{MPXJ_REF}}", ref)
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
