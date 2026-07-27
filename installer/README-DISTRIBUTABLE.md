# Schedule Forensics — installer downloads

Give the recipient **one** file matching their machine and OS, plus this README. That single file
carries the whole Python tool; only native `.mpp` import needs the extra step described below.

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
the tier's AI model. It finishes by creating an uninstaller, a first-run README, and the launch
icons — on Windows a single **Schedule Forensics** icon (the app stops itself and the local AI on
browser close or Quit); on Linux/macOS a **Start Schedule Forensics** / **Stop Schedule Forensics**
pair in the app menu.

**Native `.mpp` files need one extra step.** The 17 MB Java converter is deliberately *not* embedded
in the installer — it lives in the repository at `tools/mpxj`. To enable native `.mpp` import,
download the repository ZIP (green **Code** button → **Download ZIP**), extract it, and run
`installer/install-tierN.*` **from inside the extracted folder**; the installer copies the converter
beside the tool. Without it everything else works and `.mpp` files can still be analysed by
exporting MSPDI XML from MS Project. Upgrading an existing install keeps whatever converter is
already deployed, and the installer says which of the two you have.

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
