# Polaris² (Schedule Forensics) — installer downloads

Give the recipient **one** file matching their machine and OS, plus this README:

| Tier | For a machine with | Local AI model | Windows | Linux | macOS |
|------|--------------------|----------------|---------|-------|-------|
| 1 | 16 GB RAM, no discrete GPU | `llama3.2:3b` (or skip AI at the prompt) | `install-tier1.ps1` | `install-tier1.sh` | `install-tier1.command` |
| 2 | 64 GB RAM + discrete GPU | `llama3.1:8b` | `install-tier2.ps1` | `install-tier2.sh` | `install-tier2.command` |
| 3 | 128 GB RAM + discrete GPU | `llama3.3:70b` (~43 GB download) | `install-tier3.ps1` | `install-tier3.sh` | `install-tier3.command` |

**To install — Windows:** right-click the file → **Run with PowerShell** (or
`powershell -ExecutionPolicy Bypass -File install-tierN.ps1`).
**Linux:** `bash install-tierN.sh`. **macOS:** double-click the `.command` file (or
`bash install-tierN.command`). The installer checks what is already present and installs only
what is missing: Python 3.11+ → the tool in its own private environment (embedded in the file — no
internet needed for the tool itself) → the MPXJ converter that native `.mpp` import needs (copied
from a repo checkout if you have one beside the file, otherwise downloaded, ~17 MB, and SHA-256
verified against a manifest baked into the installer) → optional Java 17 (also native `.mpp` only)
→ optional Ollama + the tier's AI model. It finishes by creating the Desktop and Start-Menu
shortcut — a single **Polaris²** icon on Windows (the app stops itself on Quit),
**Start**/**Stop** launchers on Linux and macOS — an uninstaller, and a first-run README.
Nothing optional can abort the install: a failed Java, converter, or model download is
reported plainly and the rest still completes.

**If the machine is offline** (or the converter download is blocked), native `.mpp` support can
still be installed by hand: on the repository page use the green **Code → Download ZIP**, extract
it, and run the installer from inside the extracted folder — it carries `tools/mpxj` and will copy
it across. A converter from an earlier install is always kept, never overwritten or deleted.

**Privacy / data sovereignty:** the installed tool binds `127.0.0.1` only — schedule data never
leaves the machine. Internet is used only during installation, for public prerequisites (Python,
Java, the MPXJ converter, Ollama and the AI model). On an air-gapped machine set
`SF_MPXJ_OFFLINE=1` to suppress the converter download, or put a copy of `tools/mpxj` beside the
installer (or point `SF_MPXJ_HOME` at one) and it is used instead of the network.

## Updating an install you already have

**An installer file embeds one exact version of the tool and never consults the repository** —
re-running a file that has been sitting in your Downloads reinstalls the version it was built
with, no matter what has shipped since (this is by design: the install works offline). To
update:

1. **Re-download the latest installer** for your tier and OS from the current release — do not
   re-run an old file.
2. Run it exactly like a first install. It reuses everything already present (Python, Java, the
   converter, the model) and replaces only the tool in its private environment; your settings
   and shortcuts are kept, and a converter from an earlier install is never touched.
3. **Check what you are running:** the installer's first banner line prints the version it
   embeds (`Polaris² (Schedule Forensics) installer — vX.Y.Z — Tier …`), and the same version is visible
   after install in the tool itself.

If the banner does not print a version at all, the file predates v1.0.219 — it is old; download
a fresh one.

**Uninstall:** Start Menu → Polaris² → *Uninstall Polaris²* (removes the app
and shortcuts; leaves Python/Java/Ollama, with the `ollama rm` command noted for the model).

*Verified: the Linux installer's full lifecycle (install → serve → stop → uninstall) is
executed in CI on every installer change, and the Windows installers are parsed + smoke-run on a
real Windows runner (`.github/workflows/installer-smoke.yml`).*

*Built from `tools/installer/` — regenerate after a tool release with
`python -m build --wheel --outdir dist/wheel && python tools/installer/build_installers.py dist/wheel/*.whl`.
A repo test enforces that the three tiers share an identical body and embed the current version.*
