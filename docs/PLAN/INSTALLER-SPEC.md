# SPEC / MEMORY — One-file distributable installers (three RAM/GPU tiers)

**Status:** captured to memory at the operator's request (2026-06-27). **Not built yet** — the operator
will say "go" and answer §3 before any installer file is created. This document is the durable record so
any future session can build it on command.

## 1. The requirement (operator's words, paraphrased)

Produce a **single downloadable file** the operator can hand to another person that, from one run:

1. **Verifies** whether the machine already has the needed programs / runtimes / files.
2. **Installs only what's missing** (and does not reinstall what's already present).
3. Installs **the tool + its local web UI** and any other software required to run it.
4. Creates a **desktop icon to start** the app **and to turn it off** (stop).
5. Adds any other standard-practice helper an end user would want (uninstaller, Start-Menu entries,
   a README/first-run note).

Provide **three versions**, differing by the local-AI model they set up (the RAM/GPU tiers gate the
local Ollama model size):

| Version | Target machine | Local AI model (proposed; confirm per §3) |
|---------|----------------|--------------------------------------------|
| **Tier 1** | 16 GB RAM, **no** external GPU | CPU-friendly small model (`llama3.2:3b`) — or offline/no-AI (NullBackend) only |
| **Tier 2** | 64 GB RAM, GPU ≥ operator's | mid model (`llama3.1:8b` or `qwen2.5:14b`) |
| **Tier 3** | 128 GB RAM, GPU ≥ operator's | large model (`llama3.3:70b` quantized) |

## 2. What each installer does (planned, Windows assumed — confirm OS in §3)

- **Prereq checks (then install only if missing):**
  - Python 3.11+ (the tool requires `>=3.11`).
  - The `schedule-forensics` package into its **own venv** (from a bundled wheel or the repo).
  - Java 17 — **optional**, only needed to read native `.mpp` (auto-detect; offer to install).
  - Ollama + the tier's model — for Tier 2/3 (Tier 1 optional). Skipped entirely if the operator
    chooses offline/no-AI.
- **Shortcuts:** Desktop + Start-Menu **"Start Schedule Forensics"** (runs `schedule-forensics`, which
  binds `127.0.0.1` and opens the browser) and **"Stop Schedule Forensics"** (graceful shutdown).
- **Uninstaller** + a first-run README.
- **Law-1 posture:** the deployed tool stays **offline at runtime** (loopback only; the AI is local). The
  *only* network use is **at install time** to fetch prerequisites — never at runtime. If an air-gapped
  target is required, use the offline-bundle option (§3.3).

### Build approach by OS (one self-contained file, no separate build step)
- **Windows (most likely):** a single `install-tierN.ps1` (double-clickable via a tiny `.cmd` shim) using
  `winget`/official installers for Python/Ollama; or compile an Inno Setup / NSIS script to one `.exe`
  (needs a Windows box to compile — the `.ps1` route needs none).
- **macOS:** a single `install-tierN.command` (Homebrew or official pkgs).
- **Linux:** a single `install-tierN.sh` (distro package manager + official Ollama script).

The scripts will be **readable, prerequisite-checking, and fail-safe** (check-before-install, no hidden
downloads, pinned official sources). They cannot be end-to-end tested inside this Linux build container —
first real run is on the operator's / recipient's machine.

## 3. OPEN — answer these with "go" before building (they materially change the build)

1. **Recipient OS?** Windows / macOS / Linux. ("Desktop icon", "turn off the project" reads as Windows.)
2. **Operator's GPU model + VRAM?** The tiers say "same or better card as I have" — needed to pin the
   Tier 2/3 model sizes (e.g. "RTX 4090, 24 GB").
3. **Install-time internet?** (A) small **online** installer that downloads Python/Ollama/model during
   install [normal], or (B) large **offline** bundle that ships everything [air-gapped target, multi-GB].
4. **Include the local AI at all?** The tool runs fully without it (offline NullBackend — no AI prose).
   Confirm Ollama + a per-tier model should be auto-installed (that's what the RAM/GPU split is for).

## 4. Build trigger

When the operator says "go" (with §3 answered), create the three installer files (named per tier),
plus a short distributable README, on a branch + draft PR. Keep installer scripts out of the CUI guard's
way (they are plain text). Do not bundle any CUI/reference data into a distributable.
