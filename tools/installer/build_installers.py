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
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

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


def build(wheel: Path) -> list[Path]:
    b64 = base64.b64encode(wheel.read_bytes()).decode("ascii")
    wrapped = "\n".join(textwrap.wrap(b64, 120))
    commented = "\n".join("# " + line for line in wrapped.splitlines())
    out_dir = ROOT / "installer"
    out_dir.mkdir(exist_ok=True)
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
