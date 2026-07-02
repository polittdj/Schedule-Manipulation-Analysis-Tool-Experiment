# Schedule Forensics — installer downloads

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
internet needed for the tool itself) → optional Java 17 (native `.mpp` only) → optional Ollama +
the tier's AI model. It finishes by creating **Start Schedule Forensics** and **Stop Schedule
Forensics** icons on the Desktop and Start Menu, an uninstaller, and a first-run README.

**Privacy / data sovereignty:** the installed tool binds `127.0.0.1` only — schedule data never
leaves the machine. Internet is used only during installation, for public prerequisites.

**Uninstall:** Start Menu → Schedule Forensics → *Uninstall Schedule Forensics* (removes the app
and shortcuts; leaves Python/Java/Ollama, with the `ollama rm` command noted for the model).

*Verified: the Linux installer's full lifecycle (install → serve → stop → uninstall) is
executed in CI on every installer change, and the Windows installers are parsed + smoke-run on a
real Windows runner (`.github/workflows/installer-smoke.yml`).*

*Built from `tools/installer/` — regenerate after a tool release with
`python -m build --wheel --outdir dist/wheel && python tools/installer/build_installers.py dist/wheel/*.whl`.
A repo test enforces that the three tiers share an identical body and embed the current version.*
