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
internet needed for the tool itself) → the MPXJ converter that native `.mpp` import needs (copied
from a repo checkout if you have one beside the file, otherwise downloaded, ~17 MB, and SHA-256
verified against a manifest baked into the installer) → optional Java 17 (also native `.mpp` only)
→ optional Ollama + the tier's AI model. It finishes by creating the Desktop and Start-Menu
shortcut — a single **Schedule Forensics** icon on Windows (the app stops itself on Quit),
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

**Uninstall:** Start Menu → Schedule Forensics → *Uninstall Schedule Forensics* (removes the app
and shortcuts; leaves Python/Java/Ollama, with the `ollama rm` command noted for the model).

*Verified: the Linux installer's full lifecycle (install → serve → stop → uninstall) is
executed in CI on every installer change, and the Windows installers are parsed + smoke-run on a
real Windows runner (`.github/workflows/installer-smoke.yml`).*

*Built from `tools/installer/` — regenerate after a tool release with
`python -m build --wheel --outdir dist/wheel && python tools/installer/build_installers.py dist/wheel/*.whl`.
A repo test enforces that the three tiers share an identical body and embed the current version.*
